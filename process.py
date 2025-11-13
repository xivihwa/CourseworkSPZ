"""
User process model
"""
import random
import config

class Process:
    """User process"""
    
    _id_counter = 0
    
    def __init__(self, name, sector_sequence, read_write_pattern=None):
        """
        Args:
            name: process name
            sector_sequence: list of sectors to access
            read_write_pattern: list of booleans (True = write, False = read)
        """
        Process._id_counter += 1
        self.pid = Process._id_counter
        self.name = name
        self.sector_sequence = sector_sequence
        
        if read_write_pattern is None:
            self.read_write_pattern = [random.choice([True, False]) 
                                       for _ in sector_sequence]
        else:
            self.read_write_pattern = read_write_pattern
        
        self.current_index = 0
        self.state = 'READY'  # READY, RUNNING, BLOCKED, FINISHED
        self.remaining_quantum = config.TIME_QUANTUM
        self.waiting_for_io = False
        self.io_request = None
        self.total_cpu_time = 0.0
        self.total_wait_time = 0.0
        self.total_io_time = 0.0
        self.start_time = None
        self.finish_time = None
        self.ready_since = None
        
    def has_more_work(self):
        """Checks if there is more work"""
        return self.current_index < len(self.sector_sequence)
    
    def get_next_sector_operation(self):
        """Returns next sector and operation (is_write)"""
        if not self.has_more_work():
            return None, None
        
        sector = self.sector_sequence[self.current_index]
        is_write = self.read_write_pattern[self.current_index]
        self.current_index += 1
        
        return sector, is_write
    
    def get_progress(self):
        """Returns execution progress in percentage"""
        if len(self.sector_sequence) == 0:
            return 100.0
        return (self.current_index / len(self.sector_sequence)) * 100
    
    def reset(self):
        """Resets process to initial state"""
        self.current_index = 0
        self.state = 'READY'
        self.remaining_quantum = config.TIME_QUANTUM
        self.waiting_for_io = False
        self.io_request = None
        self.total_cpu_time = 0.0
        self.total_wait_time = 0.0
        self.total_io_time = 0.0
        self.start_time = None
        self.finish_time = None
        self.ready_since = None
    
    def __repr__(self):
        return f"Process(pid={self.pid}, name={self.name}, state={self.state}, progress={self.get_progress():.1f}%)"


def create_sample_processes():
    """Creates example processes for testing"""
    processes = []
    
    # SIMPLE TEST
    # processes.append(Process("P1", [100, 600], [False, True]))
    # processes.append(Process("P2", [200, 700], [False, True]))    
    
    # LARGE TEST
    
    # Process 1: Sequential reading
    processes.append(Process(
        name="Sequential Reader",
        sector_sequence=list(range(1000, 1020)),
        read_write_pattern=[False] * 20 
    ))
    
    # Process 2: Random accesses across disk
    random_sectors = [random.randint(0, config.TOTAL_SECTORS - 1) for _ in range(25)]
    processes.append(Process(
        name="Random Access",
        sector_sequence=random_sectors,
        read_write_pattern=[random.choice([True, False]) for _ in range(25)]
    ))
    
    # Process 3: Local accesses
    base_sector = 5000
    local_sectors = [max(0, min(base_sector + random.randint(-30, 30), config.TOTAL_SECTORS-1)) for _ in range(18)]
    processes.append(Process(
        name="Local Access",
        sector_sequence=local_sectors,
        read_write_pattern=[False] * 12 + [True] * 6
    ))
    
    # Process 4: Sequential writing
    processes.append(Process(
        name="Sequential Writer",
        sector_sequence=list(range(2000, 2016)),
        read_write_pattern=[True] * 16
    ))
    
    # Process 5: Two distant areas alternating
    sectors_area1 = list(range(500, 515))
    sectors_area2 = list(range(9500, 9515))
    alternating_sectors = [s for pair in zip(sectors_area1, sectors_area2) for s in pair]
    processes.append(Process(
        name="Two-Area Access",
        sector_sequence=alternating_sectors[:20],
        read_write_pattern=[False, True] * 10
    ))
    
    # Process 6: Reverse sequential
    processes.append(Process(
        name="Reverse Sequential",
        sector_sequence=list(range(8000, 7985, -1)),
        read_write_pattern=[False] * 15
    ))
    
    # Process 7: Jump pattern
    jump_pattern = []
    for i in range(10):
        jump_pattern.append(1000 + i * 200)
        jump_pattern.append(9000 - i * 200)
    processes.append(Process(
        name="Jump Pattern",
        sector_sequence=jump_pattern,
        read_write_pattern=[random.choice([True, False]) for _ in range(20)]
    ))
    
    # Process 8: Repeated accesses
    repeated = [3000, 3001, 3000, 3002, 3001, 3000, 3003, 3002, 3001, 3000]
    processes.append(Process(
        name="Repeated Access",
        sector_sequence=repeated,
        read_write_pattern=[False] * 10
    ))
        
    return processes