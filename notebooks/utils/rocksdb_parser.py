import re
from pathlib import Path


class RocksDBParser:

    def _get_op_latency(string_list, percentile):
        for s in string_list:
            k, v = s.split(':')
            if(int(k) == percentile):
                return float(v)
        return None

    def _parse_file(file, test_name):
        throughput = 0
        p50 = 0
        p90 = 0
        p99 = 0
        with open(file, 'rt') as f:
            for line in f:
                if(line.startswith(test_name)):
                    m = re.search(r'(\d+)\s+ops\/sec', line)
                    if(m is None):
                        print('no throughput found: ', line.strip())
                    else:
                        throughput = int(m[1])

                if(line.startswith('Percentiles')):
                    str_list = line.strip().split('P')[2:]
                    p50 = RocksDBParser._get_op_latency(str_list, 50)
                    p90 = RocksDBParser._get_op_latency(str_list, 90)
                    p99 = RocksDBParser._get_op_latency(str_list, 99)

        return throughput, p50, p90, p99

    def _parse(log_dir):
        stats = {}

        for f in Path(log_dir).iterdir():
            m = re.match(r'(\S+)_core(\d+)_threads(\d+)_dram', f.name)
            if(m is not None):
                test = m[1]
                num_cores = int(m[2])
                num_threads = int(m[3])
                latency = 0

            m = re.match(r'(\S+)_core(\d+)_threads(\d+)_cxl(\d+)', f.name)
            if(m is not None):
                test = m[1]
                num_cores = int(m[2])
                num_threads = int(m[3])
                latency = int(m[4])
                if(latency == 0):
                    latency = 500

            log_file = f.joinpath('benchmark_%s.t%d.log' % (test, num_threads))
            th, p50, p90, p99 = RocksDBParser._parse_file(log_file, test)
            d = {'throughput': th, 'latency_p50': p50, 'latency_p90': p90, 'latency_p99': p99}

            if(test not in stats):
                stats[test] = {}
            if(num_cores not in stats[test]):
                stats[test][num_cores] = {}
            if(latency not in stats[test][num_cores]):
                stats[test][num_cores][latency] = {}
            
            stats[test][num_cores][latency][num_threads] = d

        return stats


    def __init__(self, log_dir):
        self.stats = RocksDBParser._parse(log_dir)

    def get_test_names(self):
        return list(self.stats.keys())
    
    def get_num_cores_list(self, test):
        return sorted(list(self.stats[test].keys()))

    def get_latency_list(self, test, num_cores):
        return sorted(list(self.stats[test][num_cores].keys()))

    def get_num_threads_list(self, test, num_cores, latency):
        if(latency in self.stats[test][num_cores]):
            return sorted(list(self.stats[test][num_cores][latency].keys()))
        else:
            return []

    def get_perf(self, test, num_cores, latency, num_threads):
        return self.stats[test][num_cores][latency][num_threads]

    def get_max_throughput(self, test, num_cores, latency):
        max_throughput = 0
        for num_threads in self.get_num_threads_list(test, num_cores, latency):
            perf = self.get_perf(test, num_cores, latency, num_threads)
            max_throughput = max(max_throughput, perf['throughput'])
        return max_throughput


if(__name__ == '__main__'):
    import sys
    if(len(sys.argv) != 2):
        print(sys.argv[0] + ' log_path')
        exit(0)
    p = RocksDBParser(sys.argv[1])
    for test in p.get_test_names():
        print('workload:', test)
        for num_cores in p.get_num_cores_list(test):
            print('  # cores:', num_cores)
            for latency in p.get_latency_list(test, num_cores):
                print('    latency: %d nsec' % latency)
                max_throughput = 0
                num_threads_best = 0
                for num_threads in p.get_num_threads_list(test, num_cores, latency):
                    perf = p.get_perf(test, num_cores, latency, num_threads)
                    print('      %4.d threads: %7.d ops/sec (p50: %7.2f, p90: %7.2f, p99: %7.2f usec)'
                          % (num_threads, perf['throughput'], perf['latency_p50'], perf['latency_p90'], perf['latency_p99']))

                    if(max_throughput < perf['throughput']):
                        max_throughput = perf['throughput']
                        num_threads_best = num_threads
                print('    max throughput: %7.d ops/sec (at %d threads)' % (max_throughput, num_threads_best))
                print('')
