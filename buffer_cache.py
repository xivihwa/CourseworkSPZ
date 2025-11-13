"""
Buffer cache management algorithm - LFU with three segments
"""
import config

class Buffer:
    """Buffer for storing sector content"""
    def __init__(self, buffer_id):
        self.buffer_id = buffer_id
        self.sector = None
        self.is_dirty = False
        self.counter = 0
        self.segment = None
        
    def __repr__(self):
        status = "DIRTY" if self.is_dirty else "CLEAN"
        return f"Buf#{self.buffer_id}(sec={self.sector}, cnt={self.counter}, {status}, seg={self.segment})"


class LFUBufferCache:
    """
    LFU algorithm (least frequently used) with three segments.
    Segments: left (recent), middle (medium), right (rare).
    """
    
    def __init__(self, size=config.BUFFER_COUNT):
        self.size = size
        self.left_max = config.LFU_LEFT_SEGMENT_MAX
        self.middle_max = config.LFU_MIDDLE_SEGMENT_MAX
        
        self.buffers = [Buffer(i) for i in range(size)]
        
        self.left_segment = []
        self.middle_segment = []
        self.right_segment = []
        
        self.free_buffers = list(self.buffers)
        
        self.sector_to_buffer = {}
        
        self.hits = 0
        self.misses = 0
        
    def find_buffer(self, sector):
        """Finds buffer with specified sector"""
        return self.sector_to_buffer.get(sector)
    
    def access_buffer(self, sector, is_write=False, trace_func=None):
        """
        Access buffer with specified sector.
        Returns (buffer, is_hit, need_disk_read)
        If trace_func provided, will call it with trace messages.
        """
        buffer = self.find_buffer(sector)
        
        if buffer:
            self.hits += 1
            old_segment = buffer.segment
            self._move_to_left(buffer)
            
            if is_write:
                buffer.is_dirty = True
            
            if trace_func:
                trace_func(f"CACHE: Buffer ({buffer.buffer_id}:{sector}) found in cache (segment={old_segment})")
            
            return buffer, True, False
        else:
            self.misses += 1
            if trace_func:
                trace_func(f"CACHE: Buffer for sector {sector} not found in cache")
                trace_func(f"CACHE: Get free buffer")
            
            buffer = self._get_free_buffer(trace_func=trace_func)
            
            if buffer.sector is not None:
                old_sector = buffer.sector
                if old_sector in self.sector_to_buffer:
                    del self.sector_to_buffer[old_sector]
                if trace_func:
                    trace_func(f"CACHE: Buffer {buffer.buffer_id} evicted (old sector {old_sector})")
            
            buffer.sector = sector
            buffer.counter = 1
            buffer.is_dirty = is_write
            self.sector_to_buffer[sector] = buffer
            
            self.left_segment.insert(0, buffer)
            buffer.segment = 'left'
            self._rebalance_segments()
            
            if trace_func:
                trace_func(f"CACHE: MISS: sector {sector}, loading to buffer {buffer.buffer_id}")
            
            return buffer, False, not is_write
    
    def _move_to_left(self, buffer):
        """Moves buffer to beginning of left segment.
        According to the variant: increase counter only if buffer was moved from middle or right.
        """
        old_segment = buffer.segment
        
        if buffer in self.left_segment:
            self.left_segment.remove(buffer)
        elif buffer in self.middle_segment:
            self.middle_segment.remove(buffer)
        elif buffer in self.right_segment:
            self.right_segment.remove(buffer)
        
        if old_segment in ('middle', 'right'):
            buffer.counter += 1
        
        self.left_segment.insert(0, buffer)
        buffer.segment = 'left'
        self._rebalance_segments()
    
    def _rebalance_segments(self):
        """Balances segments according to limits"""
        while len(self.left_segment) > self.left_max:
            buffer = self.left_segment.pop()
            buffer.segment = 'middle'
            self.middle_segment.insert(0, buffer)
        
        while len(self.middle_segment) > self.middle_max:
            buffer = self.middle_segment.pop()
            buffer.segment = 'right'
            self.right_segment.insert(0, buffer)
    
    def _get_free_buffer(self, trace_func=None):
        """Gets free buffer or evicts one (prefer clean ones from right segment)"""
        if self.free_buffers:
            buffer = self.free_buffers.pop(0)
            buffer.segment = None
            if trace_func:
                trace_func(f"CACHE: Using free buffer {buffer.buffer_id}")
            return buffer

        if self.right_segment:
            clean_buffers = [b for b in self.right_segment if not b.is_dirty]
            if clean_buffers:
                min_counter = min(b.counter for b in clean_buffers)
                for b in self.right_segment:
                    if (not b.is_dirty) and b.counter == min_counter:
                        buffer = b
                        break
                self.right_segment.remove(buffer)
                buffer.segment = None
                if trace_func:
                    trace_func(f"CACHE: Evicting clean: {buffer}")
                return buffer
            else:
                min_counter = min(b.counter for b in self.right_segment)
                candidate = None
                for b in self.right_segment:
                    if b.counter == min_counter:
                        candidate = b
                        break
                buffer = candidate
                self.right_segment.remove(buffer)
                buffer.segment = None
                if trace_func:
                    trace_func(f"CACHE: Evicting dirty (no clean available): {buffer}")
                return buffer

        if self.middle_segment:
            buffer = self.middle_segment.pop()
            buffer.segment = None
            if trace_func:
                trace_func(f"CACHE: Evicting from middle: {buffer}")
            return buffer

        if self.left_segment:
            buffer = self.left_segment.pop()
            buffer.segment = None
            if trace_func:
                trace_func(f"CACHE: Evicting from left: {buffer}")
            return buffer

        raise Exception("No available buffers!")
    
    def get_state(self):
        """Returns current cache state"""
        return {
            'left': [str(b) for b in self.left_segment],
            'middle': [str(b) for b in self.middle_segment],
            'right': [str(b) for b in self.right_segment],
            'free': len(self.free_buffers),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        }
    
    def get_detailed_state(self):
        """Returns cache state in detailed format for tracing"""
        left_buffers = []
        for b in self.left_segment:
            status = "DIRTY" if b.is_dirty else "CLEAN"
            left_buffers.append(f"({b.buffer_id}:{b.sector},{status})")
        
        middle_buffers = []
        for b in self.middle_segment:
            status = "DIRTY" if b.is_dirty else "CLEAN"
            middle_buffers.append(f"({b.buffer_id}:{b.sector},{status})")
        
        right_buffers = []
        for b in self.right_segment:
            status = "DIRTY" if b.is_dirty else "CLEAN"
            right_buffers.append(f"({b.buffer_id}:{b.sector},{status})")
        
        return {
            'left': left_buffers,
            'middle': middle_buffers,
            'right': right_buffers
        }
    
    def print_state(self):
        """Prints current cache state"""
        state = self.get_state()
        print(f"\n  [CACHE STATE]")
        print(f"    Left segment ({len(self.left_segment)}/{self.left_max}): {state['left']}")
        print(f"    Middle segment ({len(self.middle_segment)}/{self.middle_max}): {state['middle']}")
        print(f"    Right segment ({len(self.right_segment)}): {state['right']}")
        print(f"    Free buffers: {state['free']}")
        print(f"    Statistics: Hits={state['hits']}, Misses={state['misses']}, Hit Rate={state['hit_rate']:.2%}")

    def get_dirty_buffers(self):
        """Return list of currently dirty buffers"""
        return [b for b in self.buffers if b.is_dirty]
    
    def remove_buffer_from_cache(self, buffer, trace_func=None):
        """Remove buffer from cache and free it (used in flush)"""
        if buffer.sector in self.sector_to_buffer:
            del self.sector_to_buffer[buffer.sector]
        for seg in (self.left_segment, self.middle_segment, self.right_segment):
            if buffer in seg:
                seg.remove(buffer)
        buffer.segment = None
        buffer.sector = None
        buffer.counter = 0
        buffer.is_dirty = False
        self.free_buffers.append(buffer)
        if trace_func:
            trace_func(f"CACHE: Buffer ({buffer.buffer_id}) removed from cache and freed")