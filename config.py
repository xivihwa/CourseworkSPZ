"""
System configuration for hard disk simulation
"""
# Hard disk characteristics (all times stored internally as milliseconds)
DISK_TRACKS = 10000              # Number of tracks
SECTORS_PER_TRACK = 500          # Sectors per track
TRACK_SEEK_TIME = 0.5            # Time to move one track (ms)
EDGE_SEEK_TIME = 10.0            # Time to move to edge (ms)
RPM = 7500                       # Rotation speed (RPM)

# Calculated values
ROTATION_LATENCY = ((60 * 1000) / RPM) / 2  # Average rotation latency (ms)
SECTOR_RW_TIME = ((60 * 1000) / RPM) / SECTORS_PER_TRACK  # Sector read/write time (ms)
TOTAL_SECTORS = DISK_TRACKS * SECTORS_PER_TRACK  # Total sectors

# System characteristics (times in ms)
BUFFER_COUNT = 5                # Number of buffers in cache
SYSCALL_READ_TIME = 0.15         # System call read time (ms)
SYSCALL_WRITE_TIME = 0.15        # System call write time (ms)
INTERRUPT_HANDLER_TIME = 0.05    # Interrupt handler time (ms)
TIME_QUANTUM = 20                # Process time quantum (ms)
PROCESS_READ_TIME = 7            # Data processing time after read (ms)
PROCESS_WRITE_TIME = 7           # Data preparation time before write (ms)

# LFU algorithm characteristics
LFU_LEFT_SEGMENT_MAX = 4         # Maximum buffers in left segment
LFU_MIDDLE_SEGMENT_MAX = 3       # Maximum buffers in middle segment

# LOOK algorithm characteristics
LOOK_MAX_SAME_TRACK = 5          # Maximum consecutive accesses to same track

# FLOOK algorithm characteristics
FLOOK_PROCESS_FORWARD = True     # Processing direction (True - forward, False - backward)

# Output / tracing settings
VERBOSE = False                   # Keep detailed aggregated prints
SHOW_BUFFER_STATE = True         # Show buffer cache state in aggregated summary
SHOW_QUEUE_STATE = True          # Show queue state in aggregated messages

# NEW: Detailed step-by-step trace (like instructor)
DETAILED_TRACE = True            # If True - print per-iteration trace
TIME_UNIT_MICROSECONDS = True    # If True - detailed trace prints in microseconds (us)
