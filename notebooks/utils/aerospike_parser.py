import sys
import re
from datetime import datetime


def _parse_items(lines, pattern, mode):

    match = False
    for line in lines:
        m = re.search(pattern, line)
        if(m is not None):
            if(match):
                raise Exception('too many matches')
            else:
                match = True

            if(mode == 'int'):
                val = int(m.group(1).replace(',', ''))
            elif(mode == 'float'):
                val = float(m.group(1))
            else:
                val = m.group(1)

    if(not match):
        raise Exception('no match')
    return val


def _parse_int_items(lines, pattern):
    int_pattern = '^\s*' + pattern + '\s*:\s*([\d\,]+)'
    return _parse_items(lines, int_pattern, 'int')

def _parse_bool_items(lines, pattern):
    bool_pattern = '^\s*' + pattern + '\s*:\s*(false|true)'
    return _parse_items(lines, bool_pattern, 'bool')


def _parse_op_stats(mode, lines):
    d = {}
    match = False
    for line in lines:
        m = re.search(rf'^hdr:\s*{mode}\s+([\d\-T\:Z]+)\s+(.+)', line)
        if(m is not None):
            if(match):
                raise Exception('too many matches')
            else:
                match = True

            dt_str = m[1]
            d['timestamp'] = datetime.fromisoformat(dt_str[:-1])

            t, op, l, h, p50, p90, p99, p999, p9999 = m[2].split(',')
            d['runtime'] = int(t)
            d['num_ops'] = int(op)
            d['latency_min'] = int(l)
            d['latency_max'] = int(h)
            d['latency_p50'] = int(p50)
            d['latency_p90'] = int(p90)
            d['latency_p99'] = int(p99)
            d['latency_p999'] = int(p999)
            d['latency_p9999'] = int(p9999)

    if(match):
        return d
    else:
        return None


def _parse_workload(lines):
    d = {}
    d['batch_write'] = _parse_int_items(lines, 'batch-write-size')
    d['batch_read'] = _parse_int_items(lines, 'batch-read-size')
    d['client_threads'] = _parse_int_items(lines, 'threads')
    d['async'] = _parse_bool_items(lines, 'async')
    d['write'] = _parse_op_stats('write', lines)
    d['read'] = _parse_op_stats('read', lines)
    return d


def parse(filename):
    with open(filename, 'rt') as f:
        lines = f.readlines()

    line_indices = []
    for i, line in enumerate(lines):
        m = re.search('^hosts:', line)
        if(m is not None):
            line_indices.append(i)
    line_indices.append(len(lines))

    stats = []
    for i in range(len(line_indices) - 1):
        s = line_indices[i]
        e = line_indices[i+1]
        ret = _parse_workload(lines[s:e])
        stats.append(ret)

    return stats


if(__name__ == '__main__'):
    if(len(sys.argv) < 2):
        print(sys.argv[0] + ' log_file')
        exit(0)

    stats = parse(sys.argv[1])
    print(len(stats), 'records')
    for i, s in enumerate(stats):
        print('workload %2.2d: batch W %d, batch R %d, threads %d, async %s' % (i, s['batch_write'], s['batch_read'], s['client_threads'], s['async']))
        for mode in ['read', 'write']:
            print(' ', mode)
            d = s[mode]
            if(d is None):
                continue
            for k, v in d.items():
                print('   ', k, v)
            t = d['runtime'] / (d['num_ops'] * s['batch_%s' % mode])
            print('    * per-op time: %.1f usec' % (t * 1e6))
            print('    * throughput : %.1f kops/sec' % (1e-3 / t))
