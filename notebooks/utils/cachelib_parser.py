import re
import datetime
from collections import defaultdict


class CacheLibParser:

    def __init__(self):
        self.stats = defaultdict(list)


    def _parse_items(self, lines, pattern, item_names, mode):
        if(not isinstance(item_names, list)):
            item_names = [item_names]

        match_count = 0
        for line in lines:
            m = re.search(pattern, line)
            if(m is not None):
                if(match_count >= len(item_names)):
                    raise Exception('too many matches')
                name = item_names[match_count]
                if(mode == 'int'):
                    val = int(m.group(1).replace(',', ''))
                elif(mode == 'float'):
                    val = float(m.group(1))
                else:
                    raise Exception('unsupported mode: %s' % mode)
                self.stats[name].append(val)
                match_count += 1

        #if(match_count < len(item_names)):
        #    raise Exception('too few matches')
        # zero-fill missing values instead of raising exception
        for i in range(match_count, len(item_names)):
            self.stats[item_names[i]].append(0)


    def parse_int_items(self, lines, pattern, item_names):
        int_pattern = '^' + pattern + '\s*:\s*([\d\,]+)'
        self._parse_items(lines, int_pattern, item_names, 'int')


    def parse_float_items(self, lines, pattern, item_names):
        float_pattern = '^' + pattern + '\s*:\s*(-?[\d\.]+)'
        self._parse_items(lines, float_pattern, item_names, 'float')


    def parse_per_min_stats(self, lines):
        self.parse_int_items(lines, 'Items in RAM', 'item_ram')
        self.parse_int_items(lines, 'Items in NVM', 'item_nvm')
        self.parse_int_items(lines, 'Alloc Attempts', 'alloc')
        self.parse_int_items(lines, 'Evict Attempts', 'evict')
        self.parse_int_items(lines, 'RAM Evictions', 'evict_ram')

        self.parse_int_items(lines, 'Cache Gets', ['cache_gets_total', 'cache_gets'])
        self.parse_float_items(lines, 'Hit Ratio', ['hit_total', 'hit'])
        self.parse_float_items(lines, 'RAM Hit Ratio', ['hit_ram_total', 'hit_ram'])
        self.parse_float_items(lines, 'NVM Hit Ratio', ['hit_nvm_total', 'hit_nvm'])

        self.parse_float_items(lines, 'Cache Find API latency p50', 'find_p50')
        self.parse_float_items(lines, 'Cache Find API latency p90', 'find_p90')
        self.parse_float_items(lines, 'Cache Find API latency p99', 'find_p99')
        self.parse_float_items(lines, 'Cache Find API latency p999', 'find_p999')
        self.parse_float_items(lines, 'Cache Find API latency p9999', 'find_p9999')
        self.parse_float_items(lines, 'Cache Find API latency p99999', 'find_p99999')
        self.parse_float_items(lines, 'Cache Find API latency p999999', 'find_p999999')
        self.parse_float_items(lines, 'Cache Find API latency p100', 'find_p100')


    def parse(self, filename):
        self.filename = filename
        with open(filename, 'rt') as f:
            lines = f.readlines()

        line_indices = []
        first = True
        for i, line in enumerate(lines):
            m = re.search('^([\d\:]+)\s+([\d\.]+)M ops completed\. Hit Ratio\s+(-?[\d\.]+)%\s+\(RAM\s+(-?[\d\.]+)%\,\s+NVM\s+(-?[\d\.]+)%\)', line)
            if(m is not None):
                today = datetime.date.today()
                dt = datetime.datetime.combine(today, datetime.time.fromisoformat(m.group(1)))
                if(first):
                    base_time = dt.timestamp()
                    first = False
                dif_time = dt.timestamp() - base_time
                while(dif_time < 0):
                    dif_time += 24 * 60 * 60 # one day in seconds
                self.stats['time'].append(dif_time / 60.0)  # in minutes
                line_indices.append(i)
        line_indices.append(len(lines))

        for i in range(len(line_indices) - 1):
            s = line_indices[i]
            e = line_indices[i+1]
            self.parse_per_min_stats(lines[s:e])

        return self.stats



if(__name__ == '__main__'):
    import sys
    if(len(sys.argv) < 2):
        print(sys.argv[0] + ' log.stats')
        exit(0)

    parser = CacheLibParser()
    stats = parser.parse(sys.argv[1])
    for i in range(5):
        print('------')
        for k, v in stats.items():
            print(k, v[i])
