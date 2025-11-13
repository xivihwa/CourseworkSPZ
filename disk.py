"""
Hard disk model
"""
import config

class DiskRequest:
    """Hard disk request"""
    def __init__(self, request_id, sector, is_write, process_id, time_created):
        self.request_id = request_id
        self.sector = sector
        self.track = sector // config.SECTORS_PER_TRACK
        self.is_write = is_write
        self.process_id = process_id
        self.time_created = time_created
        self.time_completed = None
        
    def __repr__(self):
        op = "WRITE" if self.is_write else "READ"
        return f"Request#{self.request_id}({op}, sector={self.sector}, track={self.track}, proc={self.process_id})"


class HardDisk:
    """Hard disk model"""
    def __init__(self):
        self.current_track = 0
        self.total_seek_time = 0.0
        self.total_rotational_latency = 0.0
        self.total_transfer_time = 0.0
        self.completed_requests = 0
        
    def calculate_seek_time(self, target_track):
        """Calculates track seek time"""
        direct_distance = abs(target_track - self.current_track)
        direct_time = direct_distance * config.TRACK_SEEK_TIME
        
        edge_time_to_zero = config.EDGE_SEEK_TIME + target_track * config.TRACK_SEEK_TIME
        edge_time_to_last = config.EDGE_SEEK_TIME + (config.DISK_TRACKS - 1 - target_track) * config.TRACK_SEEK_TIME
        
        seek_time = min(direct_time, edge_time_to_zero, edge_time_to_last)
        return seek_time
    
    def get_seek_options(self, target_track):
        """Return direct/edge options (ms) and chosen"""
        direct_distance = abs(target_track - self.current_track)
        direct_time = direct_distance * config.TRACK_SEEK_TIME
        edge_time_to_zero = config.EDGE_SEEK_TIME + target_track * config.TRACK_SEEK_TIME
        edge_time_to_last = config.EDGE_SEEK_TIME + (config.DISK_TRACKS - 1 - target_track) * config.TRACK_SEEK_TIME
        chosen = min(direct_time, edge_time_to_zero, edge_time_to_last)
        return direct_time, edge_time_to_zero, edge_time_to_last, chosen
    
    def execute_request(self, request, current_time, trace_func=None):
        """Executes disk request and returns time taken (ms)"""
        seek_time = self.calculate_seek_time(request.track)
        self.total_seek_time += seek_time
        
        rotational_latency = config.ROTATION_LATENCY
        self.total_rotational_latency += rotational_latency
        
        transfer_time = config.SECTOR_RW_TIME
        self.total_transfer_time += transfer_time
        
        total_time = seek_time + rotational_latency + transfer_time
        
        self.current_track = request.track
        self.completed_requests += 1
        
        if trace_func:
            trace_func(f"  [DISK] Executing {request}")
            trace_func(f"         Seek time: {seek_time:.2f} ms, Rotation latency: {rotational_latency:.2f} ms, "
                       f"Transfer: {transfer_time:.2f} ms")
            trace_func(f"         Total time: {total_time:.2f} ms, Current track: {self.current_track}")
        
        return total_time
    
    def get_statistics(self):
        """Returns disk operation statistics"""
        if self.completed_requests == 0:
            return {
                'completed_requests': 0,
                'avg_seek_time': 0.0,
                'avg_rotational_latency': 0.0,
                'avg_transfer_time': 0.0,
                'total_time': 0.0
            }
        
        return {
            'completed_requests': self.completed_requests,
            'avg_seek_time': self.total_seek_time / self.completed_requests,
            'avg_rotational_latency': self.total_rotational_latency / self.completed_requests,
            'avg_transfer_time': self.total_transfer_time / self.completed_requests,
            'total_time': self.total_seek_time + self.total_rotational_latency + self.total_transfer_time
        }
