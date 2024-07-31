import sys
import os
import re
import json
import subprocess
from pathlib import Path


NUM_THREADS_LIST = [32, 64, 128]
NUM_CHASES_LIST = [10, 15]
MEMORY_TIME_LIST = [1, 3, 5]
LATENCY_LIST = [500, 1000, 2000, 3000, 4000, 5000, 10000]
IO_TIME_PRE_LIST = [0, 1000, 2000]
IO_TIME_POST_LIST = [0, 1000, 2000]


CHAIN_SIZE = 1024 * 1024 * 1024  # 1 billion pointers, 64 GiB
ACCESS_SIZE = 4096
COUNT = 1000 * 1000
NUM_XSTREAMS = 1
IO_MODE = 1

LOG_DIR = 'log'



def write_param_file(param_file, count, num_xstreams, io_mode,
                     prefetch_mode_list,
                     num_chases_list, memory_time_list,
                     io_time_pre_list, io_time_post_list,
                     latency_list, num_threads_list):

    with open(param_file, 'wt') as f:
        for prefetch_mode in prefetch_mode_list:
            for latency in latency_list:
                for num_chases in num_chases_list:
                    for memory_time in memory_time_list:
                        for io_time_pre in io_time_pre_list:
                            for io_time_post in io_time_post_list:
                                for num_threads in num_threads_list:
                                    f.write('%d %d %d %d %d %d %d %d %d %d\n' % (count,
                                                                                 num_threads,
                                                                                 num_xstreams,
                                                                                 latency,
                                                                                 num_chases,
                                                                                 memory_time,
                                                                                 io_time_pre,
                                                                                 io_time_post,
                                                                                 io_mode,
                                                                                 prefetch_mode))

def parse_output(log_file, filename, chain_size, access_size):
    results = []
    with open(log_file, 'rt') as f:
        for line in f:
            m = re.search(r'param\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', line)
            if(m is not None):
                count = int(m.group(1))
                num_threads = int(m.group(2))
                num_xstreams = int(m.group(3))
                latency = int(m.group(4))
                num_chases = int(m.group(5))
                memory_time = int(m.group(6))
                io_time_pre = int(m.group(7))
                io_time_post = int(m.group(8))
                io_mode = int(m.group(9))
                prefetch_mode = int(m.group(10))
                continue

            m = re.search(r'^elapsed time\s+=\s+([\d\.]+)\s+sec', line)
            if(m is not None):
                elapsed_time = m.group(1)
                continue

            m = re.search(r'^op latency\s+=\s+([\d\.]+),\s+([\d\.]+),\s+([\d\.]+),\s+([\d\.]+),\s+([\d\.]+),\s+([\d\.]+)\s+usec', line)
            if(m is not None):
                p50 = m.group(1)
                p90 = m.group(2)
                p99 = m.group(3)
                p999 = m.group(4)
                p9999 = m.group(5)
                p99999 = m.group(6)
                continue

            m = re.search(r'^average num peeks per IO\s+=\s+([\d\.]+)', line)
            if(m is not None):
                num_peeks = m.group(1)

                d = {}
                d['filename'] = filename
                d['chain_size'] = chain_size
                d['access_size'] = access_size
                d['count'] = count
                d['num_threads'] = num_threads
                d['num_xstreams'] = num_xstreams
                d['latency'] = latency
                d['num_chases'] = num_chases
                d['memory_time'] = memory_time
                d['io_time_pre'] = io_time_pre
                d['io_time_post'] = io_time_post
                d['io_mode'] = io_mode
                d['prefetch_mode'] = prefetch_mode
                d['time'] = elapsed_time
                d['p50'] = p50
                d['p90'] = p90
                d['p99'] = p99
                d['p999'] = p999
                d['p9999'] = p9999
                d['p99999'] = p99999
                d['num_peeks'] = num_peeks
                results.append(d)

    return results



def run_benchmark(param_file, log_file,
                  filename, chain_size, access_size, count, num_xstreams, io_mode,
                  latency_list, num_threads_list, num_chases_list, memory_time_list,
                  io_time_pre_list, io_time_post_list, prefetch_mode_list):

    write_param_file(param_file, count, num_xstreams, io_mode,
                     prefetch_mode_list,
                     num_chases_list, memory_time_list,
                     io_time_pre_list, io_time_post_list,
                     latency_list, num_threads_list)

    if(latency_list[0] == 0):
        if(len(latency_list) > 1):
            print('DRAM benchmark must have latency_list = [0]')
            exit(0)
        use_cxl = 0  # DRAM
    else:
        use_cxl = 1  # CXL
    cmd = './src/main %s %d %d %d %s' % (filename,
                                         chain_size,
                                         access_size,
                                         use_cxl,
                                         param_file)

    cpu_ids = '1'  # skip core 0 to avoid interrupts
    if(num_xstreams > 1):
        cpu_ids = '1-%d' % num_xstreams

    cmd = 'taskset -c %s %s 2>&1 | tee %s' % (cpu_ids, cmd, log_file)
    print(cmd)
    env = os.environ.copy()
    env_var = 'LD_LIBRARY_PATH'
    lib_path = './argobots/src/.libs'
    if(env_var not in env or env[env_var] == ''):
        env[env_var] = lib_path
    else:
        env[env_var] += ':' + lib_path
    subprocess.run(cmd, shell=True, executable='/bin/bash', env=env)

    results = parse_output(log_file, filename, chain_size, access_size)
    return results


if(__name__ == '__main__'):

    if(len(sys.argv) < 2):
        print('%s <block_device_name>' % sys.argv[0])
        exit(1)
    FILENAME = sys.argv[1]

    log_path = Path(LOG_DIR)
    log_path.mkdir()


    results_dram = run_benchmark(log_path.joinpath('param_dram.txt'),
                                 log_path.joinpath('log_dram.txt'),
                                 FILENAME, CHAIN_SIZE, ACCESS_SIZE, COUNT, NUM_XSTREAMS, IO_MODE,
                                 [0], NUM_THREADS_LIST, NUM_CHASES_LIST, MEMORY_TIME_LIST,
                                 IO_TIME_PRE_LIST, IO_TIME_POST_LIST, [0, 1])

    with open(log_path.joinpath('dram.json'), 'w') as f:
        json.dump(results_dram, f, indent=4)

    results_cxl  = run_benchmark(log_path.joinpath('param_cxl.txt'),
                                 log_path.joinpath('log_cxl.txt'),
                                 FILENAME, CHAIN_SIZE, ACCESS_SIZE, COUNT, NUM_XSTREAMS, IO_MODE,
                                 LATENCY_LIST, NUM_THREADS_LIST, NUM_CHASES_LIST, MEMORY_TIME_LIST,
                                 IO_TIME_PRE_LIST, IO_TIME_POST_LIST, [1])
    
    with open(log_path.joinpath('cxl.json'), 'w') as f:
        json.dump(results_cxl, f, indent=4)


    calib_pause  = run_benchmark(log_path.joinpath('param_pause.txt'),
                                 log_path.joinpath('log_pause.txt'),
                                 FILENAME, 2, ACCESS_SIZE, COUNT, 1, 0,
                                 [0], [1], [1], [1000],
                                 [0], [0], [0])

    calib_pause2 = run_benchmark(log_path.joinpath('param_pause2.txt'),
                                 log_path.joinpath('log_pause2.txt'),
                                 FILENAME, CHAIN_SIZE, ACCESS_SIZE, COUNT, 1, 0,
                                 [0], [1], NUM_CHASES_LIST, MEMORY_TIME_LIST,
                                 [0], [0], [0])

    calib_pause3 = run_benchmark(log_path.joinpath('param_pause3.txt'),
                                 log_path.joinpath('log_pause3.txt'),
                                 FILENAME, CHAIN_SIZE, ACCESS_SIZE, COUNT, 1, 0,
                                 [0], NUM_THREADS_LIST, NUM_CHASES_LIST, MEMORY_TIME_LIST,
                                 [0], [0], [1])

    calib_io     = run_benchmark(log_path.joinpath('param_io.txt'),
                                 log_path.joinpath('log_io.txt'),
                                 FILENAME, CHAIN_SIZE, ACCESS_SIZE, COUNT, 1, 1,
                                 [0], NUM_THREADS_LIST + [1, 2], [0], [0],
                                 [0], [0], [0])

    calib_pref   = run_benchmark(log_path.joinpath('param_pref.txt'),
                                 log_path.joinpath('log_pref.txt'),
                                 FILENAME, CHAIN_SIZE, ACCESS_SIZE, 1000, 1, 0,
                                 [50000, 100000], NUM_THREADS_LIST, [1000], [0],
                                 [0], [0], [1])

    with open(log_path.joinpath('calib.json'), 'w') as f:
        json.dump(calib_pause + calib_pause2 + calib_pause3 + calib_io + calib_pref, f, indent=4)
