"""
Hard disk operation simulation system
Produces both:
 - detailed trace (like instructor) when config.DETAILED_TRACE = True
 - aggregated summary (always)
"""
import config
from disk import HardDisk, DiskRequest
from buffer_cache import LFUBufferCache
from scheduler import create_scheduler

class System:
    """Simulation system"""
    
    _request_counter = 0
    
    def __init__(self, scheduler_name='FIFO'):
        self.current_time = 0.0
        self.disk = HardDisk()
        self.cache = LFUBufferCache()
        self.scheduler = create_scheduler(scheduler_name)
        self.processes = []
        self.ready_queue = []
        self.current_process = None
        self.blocked_processes = {}
        
        self.total_syscall_time = 0.0
        self.total_interrupt_time = 0.0
        self.total_process_time = 0.0
        self.completed_processes = 0
        self.pending_disk_operations = []
    
    def _fmt_time(self, ms):
        """Format time with apostrophe grouping for thousands"""
        if config.TIME_UNIT_MICROSECONDS:
            us = int(round(ms * 1000.0))
            formatted = f"{us:,}".replace(",", "'")
            return f"{formatted} us"
        else:
            if ms >= 1000:
                formatted_ms = f"{ms:,.0f}".replace(",", "'")
                return f"{formatted_ms} ms"
            else:
                return f"{ms:.2f} ms"
    
    def _trace(self, msg):
        """Print trace messages only if detailed tracing enabled"""
        if config.DETAILED_TRACE:
            print(msg)
    
    def _print_cache_state(self):
        """Prints current cache state in detailed trace format"""
        if not config.DETAILED_TRACE:
            return
        
        detailed_state = self.cache.get_detailed_state()
        self._trace(f"CACHE: Buffer cache LFU (three segments):")
        self._trace(f"    Left segment {detailed_state['left']}")
        self._trace(f"    Middle segment {detailed_state['middle']}")
        self._trace(f"    Right segment {detailed_state['right']}")
    
    def _print_settings_trace(self):
        """Print simulation settings in trace style"""
        if not config.DETAILED_TRACE:
            return
        print()
        print("Settings:")
        def t(v_ms):
            if config.TIME_UNIT_MICROSECONDS:
                return f"{int(round(v_ms*1000))}"
            else:
                return f"{v_ms:.2f}"
        print(f"    syscall_read_time   {t(config.SYSCALL_READ_TIME)}")
        print(f"    syscall_write_time  {t(config.SYSCALL_WRITE_TIME)}")
        print(f"    disk_intr_time      {int(round(config.INTERRUPT_HANDLER_TIME*1000)) if config.TIME_UNIT_MICROSECONDS else config.INTERRUPT_HANDLER_TIME}")
        print(f"    quantum_time        {int(config.TIME_QUANTUM*1000) if config.TIME_UNIT_MICROSECONDS else config.TIME_QUANTUM}")
        print(f"    before_writing_time {int(config.PROCESS_WRITE_TIME*1000) if config.TIME_UNIT_MICROSECONDS else config.PROCESS_WRITE_TIME}")
        print(f"    after_reading_time  {int(config.PROCESS_READ_TIME*1000) if config.TIME_UNIT_MICROSECONDS else config.PROCESS_READ_TIME}")
        print()
        print(f"    buffers_num         {self.cache.size}")
        print()
        print(f"    tracks_num          {config.DISK_TRACKS}")
        print(f"    sectors_per_track   {config.SECTORS_PER_TRACK}")
        print(f"    track_seek_time     {int(config.TRACK_SEEK_TIME*1000) if config.TIME_UNIT_MICROSECONDS else config.TRACK_SEEK_TIME}")
        print(f"    rewind_seek_time    {int(config.EDGE_SEEK_TIME*1000) if config.TIME_UNIT_MICROSECONDS else config.EDGE_SEEK_TIME}")
        print()
        print(f"    rotation_delay_time {int(config.ROTATION_LATENCY*1000) if config.TIME_UNIT_MICROSECONDS else config.ROTATION_LATENCY}")
        print(f"    sector_access_time  {int(config.SECTOR_RW_TIME*1000) if config.TIME_UNIT_MICROSECONDS else config.SECTOR_RW_TIME}")
        print()
    
    def add_process(self, process):
        """Adds process to system"""
        self.processes.append(process)
        self.ready_queue.append(process)
        process.state = 'READY'
        process.ready_since = self.current_time
        if process.start_time is None:
            process.start_time = self.current_time
        self._trace(f"SCHEDULER: Process `{process.name}` was added")
        if config.DETAILED_TRACE:
            ops_preview = ", ".join([f"{{'{('w' if p else 'r')}',{s}}}" for s, p in zip(process.sector_sequence, process.read_write_pattern)])
            self._trace(f"    {{{ops_preview}, }}")
    
    def run_simulation(self):
        """Starts simulation"""
        self._trace("")
        print(f"\n{'='*80}")
        print(f"SIMULATION START")
        print(f"Scheduling algorithm: {self.scheduler.name}")
        print(f"Buffer cache algorithm: LFU with three segments")
        print(f"Number of processes: {len(self.processes)}")
        print(f"{'='*80}\n")
        
        self._print_settings_trace()
        
        max_iterations = 1000000
        iteration_count = 0
        
        while self._has_active_processes() and iteration_count < max_iterations:
            iteration_count += 1
            
            self._trace(f"SCHEDULER: {self._fmt_time(self.current_time)} (NEXT ITERATION)")

            self._process_pending_interrupts()

            if not self.current_process and self.ready_queue:
                self.current_process = self.ready_queue.pop(0)
                self.current_process.state = 'RUNNING'
                self.current_process.remaining_quantum = config.TIME_QUANTUM
                
                if self.current_process.ready_since is not None:
                    wait_time = self.current_time - self.current_process.ready_since
                    self.current_process.total_wait_time += wait_time
                    self.current_process.ready_since = None
                
                if config.VERBOSE:
                    print(f"\n[TIME {self.current_time:.2f} ms] Starting process: {self.current_process}")
                if config.DETAILED_TRACE:
                    self._trace(f"SCHEDULER: User mode for process `{self.current_process.name}`")
            
            if self.current_process:
                self._execute_process()
            
            if self.scheduler.has_requests() and not self.pending_disk_operations:
                self._process_disk_queue()
            
            if not self.current_process and not self.ready_queue and self.blocked_processes:
                if self.pending_disk_operations:
                    next_interrupt_time = min(t for t, r in self.pending_disk_operations)
                    if next_interrupt_time > self.current_time:
                        self.current_time = next_interrupt_time
                elif self.scheduler.has_requests():
                    self._process_disk_queue()
                else:
                    self.current_time += 1.0
            
            if iteration_count >= max_iterations:
                print(f"\n[WARNING] Maximum iterations reached ({max_iterations})")
                break
        
        if config.DETAILED_TRACE:
            self._trace("SCHEDULER: Flushing buffer cache")
        self._flush_cache_if_needed()
        
        self._print_final_statistics()
    
    def _has_active_processes(self):
        """Checks if there are active processes"""
        for p in self.processes:
            if p.state != 'FINISHED':
                return True
        return False
    
    def _process_pending_interrupts(self):
        """Process all interrupts that should occur at current_time"""
        while self.pending_disk_operations:
            interrupts_now = [
                (t, r) for t, r in self.pending_disk_operations 
                if abs(t - self.current_time) < 0.0001
            ]
            
            if not interrupts_now:
                break
            
            for t, request in interrupts_now:
                self._handle_disk_interrupt(request)
                self.pending_disk_operations.remove((t, request))
    
    def _advance_time_with_interrupts(self, duration):
        """
        Advance time by duration, handling disk interrupts that occur during this period.
        Returns the actual time advanced (may be less than duration if interrupted).
        """
        if self.current_process is None:
            self.current_time += duration
            return duration, False
        
        time_used = 0.0
        remaining_time = duration
        process = self.current_process
        
        while remaining_time > 0.0001:
            next_interrupt_time = None
            next_interrupt_request = None
            
            for completion_time, request in self.pending_disk_operations:
                time_until_interrupt = completion_time - self.current_time
                if 0 < time_until_interrupt <= remaining_time + 0.0001:
                    if next_interrupt_time is None or completion_time < next_interrupt_time:
                        next_interrupt_time = completion_time
                        next_interrupt_request = request
            
            time_until_quantum_exhausted = process.remaining_quantum
            
            if next_interrupt_time is not None:
                time_to_interrupt = next_interrupt_time - self.current_time
                
                segment_time = min(time_to_interrupt, time_until_quantum_exhausted, remaining_time)
                
                self.current_time += segment_time
                process.remaining_quantum -= segment_time
                time_used += segment_time
                remaining_time -= segment_time
                
                if abs(self.current_time - next_interrupt_time) < 0.0001:
                    self._handle_disk_interrupt(next_interrupt_request)
                    self.pending_disk_operations.remove((next_interrupt_time, next_interrupt_request))
                    
                    if self.current_process != process:
                        return time_used, True
                
                if process.remaining_quantum <= 0.0001:
                    return time_used, True
                    
            else:
                segment_time = min(remaining_time, time_until_quantum_exhausted)
                
                self.current_time += segment_time
                process.remaining_quantum -= segment_time
                time_used += segment_time
                remaining_time -= segment_time
                
                if process.remaining_quantum <= 0.0001:
                    return time_used, True
        
        return time_used, False

    def _handle_disk_interrupt(self, request):
        """Handle completion of a disk I/O operation (interrupt handler)"""
        if config.DETAILED_TRACE:
            self._trace(f"\n>>> DISK INTERRUPT at {self._fmt_time(self.current_time)} <<<")
            self._trace(f"SCHEDULER: Disk interrupt handler was invoked for request {request.request_id}")
        
        self.current_time += config.INTERRUPT_HANDLER_TIME
        self.total_interrupt_time += config.INTERRUPT_HANDLER_TIME
        
        if self.current_process is not None:
            self.current_process.remaining_quantum -= config.INTERRUPT_HANDLER_TIME
        
        request.time_completed = self.current_time
        
        cache_buffer = self.cache.find_buffer(request.sector)
        if cache_buffer and request.is_write:
            cache_buffer.is_dirty = False
            if config.DETAILED_TRACE:
                self._trace(f"  [CACHE] Buffer {cache_buffer.buffer_id} (sector {cache_buffer.sector}) marked CLEAN after write")
        
        if config.DETAILED_TRACE:
            self._print_cache_state()
        
        if request.process_id in self.blocked_processes:
            blocked_request, time_blocked = self.blocked_processes[request.process_id]
            del self.blocked_processes[request.process_id]
            
            for p in self.processes:
                if p.pid == request.process_id:
                    p.state = 'READY'
                    p.waiting_for_io = False
                    p.io_request = None
                    p.ready_since = self.current_time
                    
                    io_time = self.current_time - time_blocked
                    p.total_io_time += io_time
                    
                    self.ready_queue.append(p)
                    
                    if config.DETAILED_TRACE:
                        self._trace(f"         Process {p.name} UNBLOCKED, I/O time: {self._fmt_time(io_time)}")
                    if config.VERBOSE:
                        print(f"         Process {p.name} UNBLOCKED, I/O time: {io_time:.2f} ms")
                    break
    
    def _execute_process(self):
        """Executes current process (single quantum or until blocked)"""
        process = self.current_process
        
        if not process.has_more_work():
            process.state = 'FINISHED'
            process.finish_time = self.current_time
            self.completed_processes += 1
            
            if config.VERBOSE:
                print(f"[TIME {self.current_time:.2f} ms] Process {process.name} COMPLETED")
                print(f"         Progress: {process.get_progress():.1f}%")
            if config.DETAILED_TRACE:
                self._trace(f"SCHEDULER: Process {process.name} COMPLETED")
            self.current_process = None
            return
        
        sector, is_write = process.get_next_sector_operation()
        op_name = "WRITE" if is_write else "READ"
        
        if config.VERBOSE:
            print(f"\n[TIME {self.current_time:.2f} ms] Process {process.name} executing {op_name} sector {sector}")
        if config.DETAILED_TRACE:
            self._trace(f"SCHEDULER: Process `{process.name}` invoked {op_name.lower()}() for sector {sector}")
            self._trace(f"SCHEDULER: Kernel mode (syscall) for process `{process.name}`")
        
        syscall_time = config.SYSCALL_WRITE_TIME if is_write else config.SYSCALL_READ_TIME
        
        actual_syscall_time, was_interrupted = self._advance_time_with_interrupts(syscall_time)
        
        process.total_cpu_time += actual_syscall_time
        self.total_syscall_time += actual_syscall_time
        
        if config.DETAILED_TRACE:
            self._trace(f"... worked for {self._fmt_time(actual_syscall_time)} in system call, request buffer cache")
        
        if self.current_process is None or self.current_process != process:
            return
        
        if was_interrupted or process.remaining_quantum <= 0.0001:
            process.state = 'READY'
            process.ready_since = self.current_time
            self.ready_queue.append(process)
            self.current_process = None
            if config.DETAILED_TRACE:
                self._trace(f"SCHEDULER: Time quantum exhausted for process `{process.name}` (during syscall)")
            return
        
        buffer, is_hit, need_disk_read = self.cache.access_buffer(
            sector, is_write, 
            trace_func=self._trace if config.DETAILED_TRACE else None
        )
        
        if config.DETAILED_TRACE:
            self._print_cache_state()
        
        if need_disk_read or (is_write and not is_hit):
            System._request_counter += 1
            request = DiskRequest(
                System._request_counter,
                sector,
                is_write,
                process.pid,
                self.current_time
            )
            
            self.scheduler.add_request(request)
            if config.DETAILED_TRACE:
                b = buffer
                self._trace(f"DRIVER: Buffer ({b.buffer_id}:{b.sector}) scheduled for I/O ({'WRITE' if is_write else 'READ'})")
                try:
                    if hasattr(self.scheduler, 'get_snapshot'):
                        snap = self.scheduler.get_snapshot()
                        if isinstance(snap, dict):
                            active = snap.get('active', [])
                            incoming = snap.get('incoming', [])
                            self._trace(f"DRIVER: Device strategy {self.scheduler.name}:")
                            self._trace(f"    Active queue {active}")
                            self._trace(f"    Incoming queue {incoming}")
                        else:
                            self._trace(f"DRIVER: Device strategy {self.scheduler.name}:")
                            self._trace(f"    Schedule queue {snap}")
                    else:
                        self._trace(f"DRIVER: Device strategy {self.scheduler.name}:")
                        self._trace(f"    Schedule queue {self.scheduler.get_snapshot()}")
                except Exception:
                    pass
                
                direct_time, edge_zero, edge_last, chosen = self.disk.get_seek_options(request.track)
                d = f"{int(round(direct_time*1000)):,}".replace(",", "'")
                e = f"{int(round(edge_zero*1000)):,}".replace(",", "'")
                best_edge = min(edge_zero, edge_last)
                be = f"{int(round(best_edge*1000)):,}".replace(",", "'")
                if best_edge < direct_time:
                    self._trace(f"DRIVER: Best move decision for tracks {self.disk.current_track} => ({b.buffer_id}:{b.sector}) (next buffer in queue)")
                    self._trace(f"    direct move time {d} us, move time with rewind {be} us")
                else:
                    self._trace(f"DRIVER: Best move decision for tracks {self.disk.current_track} => ({b.buffer_id}:{b.sector}) (next buffer in queue)")
                    self._trace(f"    not to move, that is 0 us")            
            process.state = 'BLOCKED'
            process.waiting_for_io = True
            process.io_request = request
            self.blocked_processes[process.pid] = (request, self.current_time)
            
            if config.DETAILED_TRACE:
                self._trace(f"SCHEDULER: Block process `{process.name}`")
                predicted = (self.disk.calculate_seek_time(request.track)
                            + config.ROTATION_LATENCY + config.SECTOR_RW_TIME + config.INTERRUPT_HANDLER_TIME)
                self._trace(f"SCHEDULER: Next interrupt from disk will be at {self._fmt_time(self.current_time + predicted)}")
            
            self.current_process = None
        else:
            process_time = config.PROCESS_WRITE_TIME if is_write else config.PROCESS_READ_TIME
            
            if config.DETAILED_TRACE:
                self._trace(f"... data in cache, processing for {self._fmt_time(process_time)}")
            
            actual_process_time, was_interrupted = self._advance_time_with_interrupts(process_time)
            
            process.total_cpu_time += actual_process_time
            self.total_process_time += actual_process_time
            
            if self.current_process is None or self.current_process != process:
                return
            
            if was_interrupted or process.remaining_quantum <= 0.0001:
                process.state = 'READY'
                process.ready_since = self.current_time
                self.ready_queue.append(process)
                self.current_process = None
                
                if config.VERBOSE:
                    print(f"         Time quantum exhausted for process {process.name}")
                if config.DETAILED_TRACE:
                    self._trace(f"SCHEDULER: Time quantum exhausted for process `{process.name}`")
    
    def _process_disk_queue(self):
        """
        Start processing a disk request if disk is idle.
        The actual completion will be handled by interrupt during _advance_time_with_interrupts.
        """
        if self.pending_disk_operations:
            return
        
        if not self.scheduler.has_requests():
            return
        
        request = self.scheduler.get_next_request(self.disk.current_track)
        if not request:
            return
        
        if config.DETAILED_TRACE:
            self._trace(f"\nSCHEDULER: {self._fmt_time(self.current_time)} (STARTING DISK I/O)")
        
        seek_time = self.disk.calculate_seek_time(request.track)
        self.disk.total_seek_time += seek_time
        
        rotational_latency = config.ROTATION_LATENCY
        self.disk.total_rotational_latency += rotational_latency
        
        transfer_time = config.SECTOR_RW_TIME
        self.disk.total_transfer_time += transfer_time
        
        total_disk_time = seek_time + rotational_latency + transfer_time
        
        self.disk.current_track = request.track
        self.disk.completed_requests += 1
        
        if config.DETAILED_TRACE:
            self._trace(f"  [DISK] Starting {request}")
            self._trace(f"         Seek time: {seek_time:.2f} ms, Rotation latency: {rotational_latency:.2f} ms, "
                       f"Transfer: {transfer_time:.2f} ms")
            self._trace(f"         Total time: {total_disk_time:.2f} ms, Current track: {self.disk.current_track}")
            self._trace(f"         Interrupt will occur at {self._fmt_time(self.current_time + total_disk_time)}")
        
        completion_time = self.current_time + total_disk_time
        self.pending_disk_operations.append((completion_time, request))
    
    def _flush_cache_if_needed(self):
        """Flush dirty buffers (write-back) at simulation end"""
        dirty = self.cache.get_dirty_buffers()
        if not dirty:
            if config.DETAILED_TRACE:
                self._trace("CACHE: No dirty buffers to flush")
            return
        
        if config.DETAILED_TRACE:
            self._trace(f"CACHE: Flushing {len(dirty)} dirty buffers")
        
        for b in dirty:
            System._request_counter += 1
            request = DiskRequest(System._request_counter, b.sector, True, -1, self.current_time)
            self.scheduler.add_request(request)
            if config.DETAILED_TRACE:
                self._trace(f"CACHE: Buffer ({b.buffer_id}:{b.sector}) scheduled for I/O (WRITE)")
        
        while self.scheduler.has_requests():
            self._process_disk_queue()
            if self.pending_disk_operations:
                next_time = min(t for t, r in self.pending_disk_operations)
                self.current_time = next_time
                self._process_pending_interrupts()
        
        for b in list(dirty):
            self.cache.remove_buffer_from_cache(b, trace_func=self._trace if config.DETAILED_TRACE else None)
    
    def _print_final_statistics(self):
        """Prints final statistics"""
        print(f"\n{'='*80}")
        print(f"SIMULATION COMPLETED")
        print(f"{'='*80}")
        
        disk_stats = self.disk.get_statistics()
        print(f"\n[DISK STATISTICS]")
        print(f"  Completed requests: {disk_stats['completed_requests']}")
        print(f"  Average seek time: {disk_stats['avg_seek_time']:.2f} ms")
        print(f"  Average rotational latency: {disk_stats['avg_rotational_latency']:.2f} ms")
        print(f"  Average transfer time: {disk_stats['avg_transfer_time']:.2f} ms")
        print(f"  Total disk time: {disk_stats['total_time']:.2f} ms")
        
        cache_state = self.cache.get_state()
        print(f"\n[CACHE STATISTICS]")
        print(f"  Hits: {cache_state['hits']}")
        print(f"  Misses: {cache_state['misses']}")
        print(f"  Hit rate: {cache_state['hit_rate']:.2%}")
        
        print(f"\n[SYSTEM STATISTICS]")
        print(f"  Total simulation time: {self.current_time:.2f} ms")
        print(f"  Total system call time: {self.total_syscall_time:.2f} ms")
        print(f"  Total interrupt handler time: {self.total_interrupt_time:.2f} ms")
        print(f"  Total process execution time: {self.total_process_time:.2f} ms")
        
        print(f"\n[PROCESS STATISTICS]")
        for p in self.processes:
            if p.finish_time is not None and p.start_time is not None:
                total_time = p.finish_time - p.start_time
                if total_time <= 0:
                    continue
                print(f"  {p.name}:")
                print(f"    Total time: {total_time:.2f} ms")
                print(f"    CPU time: {p.total_cpu_time:.2f} ms ({p.total_cpu_time/total_time*100:.1f}%)")
                print(f"    I/O time: {p.total_io_time:.2f} ms ({p.total_io_time/total_time*100:.1f}%)")
                print(f"    Wait time: {p.total_wait_time:.2f} ms ({p.total_wait_time/total_time*100:.1f}%)")
                print(f"    Progress: {p.get_progress():.1f}%")
        
        if config.SHOW_BUFFER_STATE:
            self.cache.print_state()
    
    def reset(self):
        """Resets system to initial state"""
        self.current_time = 0.0
        self.disk = HardDisk()
        self.cache = LFUBufferCache()
        self.ready_queue = []
        self.current_process = None
        self.blocked_processes = {}
        self.pending_disk_operations = []
        
        for p in self.processes:
            p.reset()
            self.ready_queue.append(p)
        
        self.total_syscall_time = 0.0
        self.total_interrupt_time = 0.0
        self.total_process_time = 0.0
        self.completed_processes = 0
        System._request_counter = 0