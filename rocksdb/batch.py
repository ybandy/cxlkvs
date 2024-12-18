import os
import re
import subprocess
from pathlib import Path


ROCKSDB_PATH = Path('rocksdb_photon')
DB_BENCH_PATH = ROCKSDB_PATH.joinpath('build')

SSD_PATH = ''
NUM_KEYS = 1000000000

CXL_NODEMASK = (1 << 2) | (1 << 3)
CXL_SET_LATENCY_PATH = '~/set_latency.sh'


def change_num_cores(num_cores):
    env_file = ROCKSDB_PATH.joinpath('include', 'rocksdb', 'env.h')
    with open(env_file, 'rt') as f:
        data = f.read()

    data = re.sub('static PhotonEnv instance\(\d+, photon::INIT_EVENT_IOURING\);',
                  'static PhotonEnv instance(%d, photon::INIT_EVENT_IOURING);' % num_cores,
                  data)

    with open(env_file, 'wt') as f:
        f.write(data)

    cmd = 'cmake --build build -t db_bench -j `nproc`'
    subprocess.run(cmd, shell=True, executable='/bin/bash', cwd=ROCKSDB_PATH)


def run_benchmark(workload, num_cores, num_threads, use_cxl, latency=0):

    job_id = workload + '_core%d_threads%d' % (num_cores, num_threads)
    if(use_cxl):
        job_id += '_cxl%d' % latency
        nodemask = CXL_NODEMASK
    else:
        job_id += '_dram'
        nodemask = 1
    output_path = Path('log', job_id).absolute()

    env = os.environ.copy()
    env['OUTPUT_DIR'] = str(output_path)
    env['DB_DIR'] = str(Path(SSD_PATH, 'data'))
    env['WAL_DIR'] = str(Path(SSD_PATH, 'wal'))
    env['NUM_KEYS'] = str(NUM_KEYS)
    env['COMPRESSION_TYPE'] = 'none'
    env['USE_O_DIRECT'] = '1'
    env['READ_RANDOM_ZIPF_EXPONENT'] = '0.99'
    env['DURATION'] = '180'
    env['USE_CXL'] = str(nodemask)
    env['CXL_LATENCY'] = str(latency)
    env['CXL_SET_LATENCY_PATH'] = CXL_SET_LATENCY_PATH
    env['CACHE_SIZE'] = str(32 * 1024 * 1024 * 1024)
    env['CACHE_NUMSHARDBITS'] = '10'
    env['NUM_THREADS'] = str(num_threads)
    env['WRITE_BUFFER_SIZE_MB'] = '4096'

    output_path.mkdir(parents=True, exist_ok=True)
    cmd = 'ulimit -n 10000 && ../tools/benchmark.sh ' + workload
    subprocess.run(cmd, shell=True, executable='/bin/bash', env=env, cwd=DB_BENCH_PATH)


NUM_CORES_LIST = [1, 2, 4, 8, 16]
NUM_THREADS_PER_CORE_LIST = [16, 32, 64, 128]
LATENCY_LIST = [0, 1000, 2000, 3000, 4000, 5000, 10000]


# read-only
for num_cores in NUM_CORES_LIST:
    change_num_cores(num_cores)
    for num_threads_per_core in NUM_THREADS_PER_CORE_LIST:
        num_threads = num_threads_per_core * num_cores
        run_benchmark('readrandom', num_cores, num_threads, use_cxl=False)
        for latency in LATENCY_LIST:
            run_benchmark('readrandom', num_cores, num_threads, True, latency)

# read-write-mix
if(num_cores != 16):
    num_cores = 16
    change_num_cores(num_cores)
for num_threads in [1024, 2048]:
    run_benchmark('readrandomwriterandom', num_cores, num_threads, use_cxl=False)
    for latency in LATENCY_LIST:
        run_benchmark('readrandomwriterandom', num_cores, num_threads, True, latency)

