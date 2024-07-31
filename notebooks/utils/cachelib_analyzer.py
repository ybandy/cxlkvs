import numpy as np
from collections import defaultdict

from .cachelib_parser import CacheLibParser


def get_stats(base_path, filename, num_cores_list, num_threads_list):
    stats_dict = {}
    for num_cores in num_cores_list:
        stats_dict[num_cores] = {}
        for num_threads in num_threads_list:
            parser = CacheLibParser()
            stats = parser.parse(base_path.joinpath(filename % (num_cores, num_threads)))
            stats_dict[num_cores][num_threads] = stats
    return stats_dict



def _mean_stats(stats, key, base):
    return np.mean(np.array(stats[key][base-20:base-5]))

def get_throughput_and_latency(dram_stats, cxl_stats, cxl_latency_change_times, p_list):
    
    throughput_dict = defaultdict(list)
    get_latency_dict = defaultdict(list)

    max_throughput_list = []
    max_throughput = 0
    for num_threads, stats in dram_stats.items():
        throughput = _mean_stats(stats, 'cache_gets', 0) / 60
        throughput_dict[num_threads].append(throughput)
        d = {}
        for p in p_list:
            get_latency = _mean_stats(stats, 'find_p%d' % p, 0)
            d['latency_p%d' % p] = get_latency
        get_latency_dict[num_threads].append(d)
        max_throughput = max(max_throughput, throughput)
    max_throughput_list.append(max_throughput)

    for change_time in cxl_latency_change_times:
        max_throughput = 0
        for num_threads, stats in cxl_stats.items():
            t = change_time[num_threads]
            throughput = _mean_stats(stats, 'cache_gets', t) / 60
            throughput_dict[num_threads].append(throughput)
            d = {}
            for p in p_list:
                get_latency = _mean_stats(stats, 'find_p%d' % p, t)
                d['latency_p%d' % p] = get_latency
            get_latency_dict[num_threads].append(d)
            max_throughput = max(max_throughput, throughput)
        max_throughput_list.append(max_throughput)

    return max_throughput_list, throughput_dict, get_latency_dict
