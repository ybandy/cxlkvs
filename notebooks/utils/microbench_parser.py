import json
from collections import defaultdict


class MicrobenchParser:

    PERF_KEYS = {
        'time',
        'p50',
        'p90',
        'p99',
        'p999',
        'p9999',
        'p99999',
    }

    def _cast(key, value):
        if(key in MicrobenchParser.PERF_KEYS):
            return float(value)
        elif(key == 'filename'):
            return value
        else:
            return int(value)


    def __init__(self, filenames):
        self.data = []
        for file in filenames:
            with open(file, 'r') as f:
                self.data += json.load(f)
        self._parse()

    def _parse(self):
        self.key_set = set()
        self.val_set_dict = defaultdict(set)
        for test in self.data: #.values():
            for k, v in test.items():
                v = MicrobenchParser._cast(k, v)
                self.key_set.add(k)
                if(k not in MicrobenchParser.PERF_KEYS):
                    self.val_set_dict[k].add(v)

    def get_keys(self):
        return self.key_set

    def get_values(self, key):
        return sorted(list(self.val_set_dict[key]))

    def get_perf(self, spec_dict, perf_key, var_key):
        if(perf_key not in MicrobenchParser.PERF_KEYS):
            raise Exception('%s is not a performance key' % perf_key)
        if(not isinstance(var_key, list)):
            var_key = [var_key]
        perf_list = []
        for test in self.data: #.values(): # each microbench run
            is_match = True
            for k, v in test.items(): # check if this run is what we are looking for
                v = MicrobenchParser._cast(k, v)
                if(k != perf_key and k not in var_key
                   and k in spec_dict and spec_dict[k] != v):
                    is_match = False
                    break
            if(is_match):
                perf_list.append(float(test[perf_key]))
        return perf_list


    def get_throughputs(self, latency_list,
                        num_chases, memory_time,
                        io_time_pre, io_time_post):
        spec = {}
        for key in self.get_keys():
            if(key not in self.PERF_KEYS):
                spec[key] = self.get_values(key)[0]

        spec['num_chases'] = num_chases
        spec['memory_time'] = memory_time
        spec['io_time_pre'] = io_time_pre
        spec['io_time_post'] = io_time_post
        spec['prefetch_mode'] = 1

        throughput_list = []
        for latency in latency_list:
            spec['latency'] = latency
            times = self.get_perf(spec, 'time', 'num_threads')
            count = spec['count']
            throughput_list.append(count / min(times))
        return throughput_list
