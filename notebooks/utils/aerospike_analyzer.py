import re
from collections import defaultdict

from .aerospike_parser import parse


def parse_logs(log_file_list, mem_latency_list):
    log_dict = defaultdict(list)
    for log_file in log_file_list:
        m = re.search('act-(\d+).log', log_file.name)
        if(m is None):
            print('error parsing log filename:', log_file.name)
            exit(1)
        server_threads = int(m.group(1))
        data = parse(log_file)
        cur_batch_read = 0
        mem_latency_idx = -1
        for d in data:
            if(d['read'] is not None and d['async'] == 'false'):
                if(d['batch_read'] == 1 and cur_batch_read != 1):
                    mem_latency_idx += 1
                    cur_mem_latency = mem_latency_list[mem_latency_idx]
                cur_batch_read = d['batch_read']
                d['server_threads'] = server_threads
                log_dict[cur_mem_latency].append(d)
    return log_dict


def analyze_given_mem_latency_and_batch(data, mem_latency, batch):

    runs_with_varing_server_and_client_threads = []
    for d in data[mem_latency]:
        if(d['batch_read'] == batch and d['batch_write'] == batch):
            runs_with_varing_server_and_client_threads.append(d)

    rd_latency_dict = {}
    wr_latency_dict = {}
    throughput_dict = {}
    max_throughput = 0
    max_server_threads = 0
    max_client_threads = 0
    for d in runs_with_varing_server_and_client_threads:
        s_th = d['server_threads']
        c_th = d['client_threads']

        if(c_th not in rd_latency_dict):
            rd_latency_dict[c_th] = {}
        rd_latency_dict[c_th][s_th] = d['read']

        if(c_th not in wr_latency_dict):
            wr_latency_dict[c_th] = {}
        wr_latency_dict[c_th][s_th] = d['write']

        throughput = 0
        for mode in ['read', 'write']:
            if(d[mode] is not None):
                throughput += d[mode]['num_ops'] * d['batch_%s' % mode] / d[mode]['runtime']

        if(c_th not in throughput_dict):
            throughput_dict[c_th] = {}
        throughput_dict[c_th][s_th] = throughput

        if(max_throughput < throughput):
            max_throughput = throughput
            max_server_threads = s_th
            max_client_threads = c_th
        
    return max_throughput, max_server_threads, max_client_threads, throughput_dict, rd_latency_dict, wr_latency_dict
