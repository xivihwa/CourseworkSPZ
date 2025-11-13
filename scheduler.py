"""
Disk I/O scheduling algorithms
"""
import config

class DiskScheduler:
    """Base scheduler class"""
    def __init__(self, name):
        self.name = name
        self.queue = []
        
    def add_request(self, request):
        """Adds request to queue"""
        self.queue.append(request)
        
    def get_next_request(self, current_track):
        """Returns next request for execution"""
        raise NotImplementedError
    
    def has_requests(self):
        """Checks if there are requests in queue"""
        return len(self.queue) > 0
    
    def get_snapshot(self):
        """Return textual snapshot of queue for trace printing"""
        return [str(r) for r in self.queue]
    
    def __repr__(self):
        return f"{self.name} (queue size: {len(self.queue)})"


class FIFOScheduler(DiskScheduler):
    """
    FIFO Algorithm (First In First Out)
    """
    
    def __init__(self):
        super().__init__("FIFO")
        
    def get_next_request(self, current_track):
        """Returns first request from queue"""
        if self.queue:
            request = self.queue.pop(0)
            if config.VERBOSE and config.SHOW_QUEUE_STATE:
                print(f"  [{self.name}] Selected request: {request}")
            return request
        return None


class LOOKScheduler(DiskScheduler):
    """
    LOOK Algorithm (Elevator algorithm)
    """
    
    def __init__(self):
        super().__init__("LOOK")
        self.direction_forward = True  # True = forward, False = backward
        self.same_track_count = 0
        self.last_track = None
        
    def get_next_request(self, current_track):
        """Returns next request according to LOOK algorithm"""
        if not self.queue:
            return None
        
        self.queue.sort(key=lambda r: r.track)
        
        candidate = None
        
        if self.direction_forward:
            candidates = [r for r in self.queue if r.track >= current_track]
            if candidates:
                candidate = min(candidates, key=lambda r: r.track)
        else:
            candidates = [r for r in self.queue if r.track <= current_track]
            if candidates:
                candidate = max(candidates, key=lambda r: r.track)
        
        if not candidate:
            if self.direction_forward:
                candidate = min(self.queue, key=lambda r: r.track)
            else:
                candidate = max(self.queue, key=lambda r: r.track)
            
            self.direction_forward = not self.direction_forward
            if config.VERBOSE and config.SHOW_QUEUE_STATE:
                direction = "FORWARD" if self.direction_forward else "BACKWARD"
                print(f"  [{self.name}] Direction changed to {direction}")
        
        if self.last_track == candidate.track:
            self.same_track_count += 1
            if self.same_track_count >= config.LOOK_MAX_SAME_TRACK:
                self.queue.remove(candidate)
                self.same_track_count = 0
                return self.get_next_request(current_track)
        else:
            self.same_track_count = 1
            self.last_track = candidate.track
        
        self.queue.remove(candidate)
        
        if config.VERBOSE and config.SHOW_QUEUE_STATE:
            direction = "FORWARD" if self.direction_forward else "BACKWARD"
            print(f"  [{self.name}] Selected request: {candidate}, direction: {direction}")
        
        return candidate


class FLOOKScheduler(DiskScheduler):
    """
    FLOOK Algorithm (Frozen LOOK) — two queues (active/incoming).
    """
    
    def __init__(self):
        super().__init__("FLOOK")
        self.active_queue = []
        self.incoming_queue = []
        self.direction_forward = config.FLOOK_PROCESS_FORWARD
        
    def add_request(self, request):
        """Adds request to incoming queue"""
        self.incoming_queue.append(request)
        
    def has_requests(self):
        """Checks for requests"""
        return len(self.active_queue) > 0 or len(self.incoming_queue) > 0
    
    def get_next_request(self, current_track):
        """Returns next request according to FLOOK algorithm"""
        if not self.active_queue:
            if not self.incoming_queue:
                return None
            self.active_queue = list(self.incoming_queue)
            self.incoming_queue = []
            self.active_queue.sort(key=lambda r: r.track)
            if config.VERBOSE and config.SHOW_QUEUE_STATE:
                print(f"  [{self.name}] Queue swap, new active queue: {len(self.active_queue)} requests")
        
        candidate = None
        
        if self.direction_forward:
            candidates = [r for r in self.active_queue if r.track >= current_track]
            if candidates:
                candidate = min(candidates, key=lambda r: r.track)
            else:
                if self.active_queue:
                    candidate = min(self.active_queue, key=lambda r: r.track)
                    self.direction_forward = not self.direction_forward
        else:
            candidates = [r for r in self.active_queue if r.track <= current_track]
            if candidates:
                candidate = max(candidates, key=lambda r: r.track)
            else:
                if self.active_queue:
                    candidate = max(self.active_queue, key=lambda r: r.track)
                    self.direction_forward = not self.direction_forward
        
        if candidate:
            self.active_queue.remove(candidate)
            if config.VERBOSE and config.SHOW_QUEUE_STATE:
                direction = "FORWARD" if self.direction_forward else "BACKWARD"
                print(f"  [{self.name}] Selected request: {candidate}, direction: {direction}")
                print(f"         Active queue: {len(self.active_queue)}, Incoming queue: {len(self.incoming_queue)}")
        
        return candidate
    
    def get_snapshot(self):
        """Return snapshot showing active & incoming queues"""
        active = [str(r) for r in self.active_queue]
        incoming = [str(r) for r in self.incoming_queue]
        return {"active": active, "incoming": incoming}


def create_scheduler(algorithm_name):
    """Factory for creating scheduler"""
    schedulers = {
        'FIFO': FIFOScheduler,
        'LOOK': LOOKScheduler,
        'FLOOK': FLOOKScheduler
    }
    
    if algorithm_name not in schedulers:
        raise ValueError(f"Unknown algorithm: {algorithm_name}")
    
    return schedulers[algorithm_name]()
