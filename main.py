"""
Main file for running hard disk simulation
"""
import time
from process import create_sample_processes
from system import System
import config

def run_single_simulation(scheduler_name, processes):
    """Runs simulation with specified scheduler"""
    print(f"\n{'='*80}")
    print(f"RUNNING SIMULATION WITH {scheduler_name} SCHEDULER")
    print(f"{'='*80}")
    
    system = System(scheduler_name)
    
    for process in processes:
        system.add_process(process)
    
    start_time = time.time()
    system.run_simulation()
    end_time = time.time()
    
    print(f"\nReal execution time: {end_time - start_time:.2f} seconds")
    
    return system

def compare_algorithms():
    """Compares FIFO, LOOK, FLOOK"""
    print("HARD DISK SCHEDULING ALGORITHMS COMPARISON")
    print("LFU Buffer Cache with Three Segments")
    print("=" * 60)
    
    results = {}
    
    for algorithm in ['FIFO', 'LOOK', 'FLOOK']:
        print(f"\n{'='*80}")
        print(f"TESTING {algorithm} ALGORITHM")
        print(f"{'='*80}")
        
        test_processes = create_sample_processes()
        
        system = run_single_simulation(algorithm, test_processes)
        
        disk_stats = system.disk.get_statistics()
        cache_stats = system.cache.get_state()
        
        results[algorithm] = {
            'total_time': system.current_time,
            'disk_time': disk_stats['total_time'],
            'avg_seek_time': disk_stats['avg_seek_time'],
            'cache_hit_rate': cache_stats['hit_rate'],
            'completed_requests': disk_stats['completed_requests']
        }
    
    print(f"\n{'='*80}")
    print(f"ALGORITHM COMPARISON RESULTS")
    print(f"{'='*80}")
    
    print(f"\n{'Algorithm':<10} {'Total Time':<12} {'Disk Time':<12} {'Avg Seek':<12} {'Hit Rate':<12} {'Requests':<10}")
    print(f"{'-'*80}")
    
    for algo in ['FIFO', 'LOOK', 'FLOOK']:
        r = results[algo]
        print(f"{algo:<10} {r['total_time']:<12.2f} {r['disk_time']:<12.2f} "
              f"{r['avg_seek_time']:<12.2f} {r['cache_hit_rate']:<12.2%} {r['completed_requests']:<10}")
    
    print(f"\n{'='*80}")
    print(f"PERFORMANCE ANALYSIS")
    print(f"{'='*80}")
    
    best_algo = min(results.keys(), key=lambda x: results[x]['total_time'])
    print(f"\nBest overall performance: {best_algo} ({results[best_algo]['total_time']:.2f} ms)")
    
    best_seek = min(results.keys(), key=lambda x: results[x]['avg_seek_time'])
    print(f"Best seek performance: {best_seek} ({results[best_seek]['avg_seek_time']:.2f} ms average seek time)")
    
    best_cache = max(results.keys(), key=lambda x: results[x]['cache_hit_rate'])
    print(f"Best cache performance: {best_cache} ({results[best_cache]['cache_hit_rate']:.2%} hit rate)")

def main():
    """Main function (interactive menu)"""
    print("HARD DISK SIMULATION SYSTEM")
    print("Variant 2: LFU with three segments, FIFO, LOOK, FLOOK")
    print("=" * 60)
    print("NOTE: For detailed step-by-step trace, open config.py and set DETAILED_TRACE = True")
    
    while True:
        print(f"\nMain Menu:")
        print(f"1. Run single simulation with FIFO")
        print(f"2. Run single simulation with LOOK") 
        print(f"3. Run single simulation with FLOOK")
        print(f"4. Compare all algorithms (RECOMMENDED)")
        print(f"5. Configure system parameters (see config.py)")
        print(f"6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == '1':
            processes = create_sample_processes()
            run_single_simulation('FIFO', processes)
            
        elif choice == '2':
            processes = create_sample_processes()
            run_single_simulation('LOOK', processes)
            
        elif choice == '3':
            processes = create_sample_processes()
            run_single_simulation('FLOOK', processes)
            
        elif choice == '4':
            compare_algorithms()
            
        elif choice == '5':
            print(f"\nCurrent configuration (config.py):")
            print(f"  Disk tracks: {config.DISK_TRACKS}")
            print(f"  Sectors per track: {config.SECTORS_PER_TRACK}")
            print(f"  Buffer count: {config.BUFFER_COUNT}")
            print(f"  LFU left segment: {config.LFU_LEFT_SEGMENT_MAX}")
            print(f"  LFU middle segment: {config.LFU_MIDDLE_SEGMENT_MAX}")
            print(f"  Verbose output: {config.VERBOSE}")
            print(f"  Detailed trace: {config.DETAILED_TRACE}")
            print(f"\nEdit values directly in config.py to change them.")
            
        elif choice == '6':
            print("See you!")
            break
            
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()
