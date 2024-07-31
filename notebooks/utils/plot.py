import numpy as np
import matplotlib.pyplot as plt

from .model import *


def plot_throughputs(mem_latency_list, throughput_list, top, color, title, filename):
    figsize = plt.rcParams['figure.figsize']
    plt.figure(figsize=(figsize[0]*2//3, figsize[1]*2//3))
    xlabels = []
    y = []
    for lat, t in zip(mem_latency_list, throughput_list):
        if(lat > 1000 and lat % 1000 == 500):
            continue
        elif(lat > 15000):
            continue
        elif(lat == 0):
            xlabels.append('DRAM\n0.1')
        else:
            xlabels.append('CXL\n%.1f' % (lat / 1000))
        y.append(t * 1e-6)
    x = np.arange(len(y))
    plt.bar(x, y, width=0.5, color=color)
    plt.xticks(ticks=x, labels=xlabels)
    plt.xlabel('Memory latency [usec]')
    plt.ylabel('Throughput [Mops/sec]')
    plt.ylim(top=top)
    plt.title(title)
    plt.savefig(filename + '.pdf', bbox_inches='tight')
    plt.show()



def plot_with_models(latency_list, througput_list,
                     num_chases, memory_time, io_time_pre, io_time_post,
                     switch_time, num_prefetches,
                     eval_label, title, filename, pos=1, normalize=True):

    MODEL_LIST = [
        (OpTimeModelWorst(switch_time, num_prefetches),         'worst', '#72f0ff', '#56b4e9', '//'),
        (OpTimeModelProbabilistic(switch_time, num_prefetches), 'prob',  '#00d299', '#009e73', None),
        (OpTimeModelBest(switch_time, num_prefetches),          'best',  '#ffd400', '#e69f00', '\\\\'),
    ]

    perf_dict = {}

    figsize = plt.rcParams['figure.figsize']
    plt.figure(figsize=(figsize[0], figsize[1]*2//3))

    x = np.arange(len(latency_list))

    n = len(MODEL_LIST) + 1
    width = 0.8 / n

    for i in range(n):
        if(i == pos):
            perf = througput_list
            label = eval_label
            color = '#9400d3'
            edgecolor = color
            hatch = None
        else:
            perf = []
            for latency in latency_list:
                m = MODEL_LIST[i if(i < pos) else i-1]
                if(latency == 0):
                    latency = 100
                t = m[0].reciprocal_throughput(num_chases, memory_time,
                                               io_time_pre, io_time_post, latency)
                perf.append(1e9 / t)
            label = 'Model (%s)' % m[1]
            color = m[2]
            edgecolor = m[3]
            hatch = m[4]

        if(normalize):
            perf = np.array(perf) / perf[0]

        plt.bar(x + width * (i - n/2 + 0.5), perf, width=width * 0.7, label=label,
                color=color, edgecolor=edgecolor, hatch=hatch)
        perf_dict[label] = list(perf)

    xlabels = []
    for lat in latency_list:
        if(lat == 0):
            xlabels.append('DRAM\n0.1')
        else:
            xlabels.append('CXL\n%.1f' % (lat / 1000))

    plt.xticks(ticks=x, labels=xlabels)
    plt.xlabel('Memory latency [usec]')
    plt.ylabel('Normalized throughput')
    plt.legend(bbox_to_anchor=(1, 0), loc='lower left')
    plt.title(title)
    plt.savefig(filename + '.pdf', bbox_inches='tight')
    plt.show()

    return perf_dict



def plot_core_scaling(num_cores_list, throughput_dict, title):
    plt.figure()
    for lat, t in throughput_dict.items():
        if(lat == 0):
            label = 'DRAM 0.1'
        else:
            label = 'CXL %.1f' % (lat / 1000)
        plt.plot(num_cores_list, np.array(t) * 1e-6, 'o-', label=label)
    plt.xlabel('Number of CPU cores')
    plt.ylabel('Throughput [Mops/sec]')
    plt.legend()
    plt.title(title)
    plt.show()



def plot_latencies(mem_latency_list, op_latency_list, p_list, batch, title, filename):
    figsize = plt.rcParams['figure.figsize']
    plt.figure(figsize=(figsize[0]*4//5, figsize[1]*2//3))

    xlabels = []
    for ml in mem_latency_list:
        if(ml > 1000 and ml % 1000 == 500):
            continue
        elif(ml > 15000):
            continue
        if(ml == 0):
            xlabels.append('DRAM\n0.1')
        else:
            xlabels.append('CXL\n%.1f' % (ml / 1000))

    x = np.arange(len(xlabels))
    n = len(p_list)
    width = 0.7 / len(p_list)

    COLOR_LIST = [(0.74, 0.74, 0.13), (0.41, 0.53, 0.1), (0.07, 0.33, 0.07)]

    for i, p in enumerate(p_list):
        y = []
        for ml, opl in zip(mem_latency_list, op_latency_list):
            if(ml > 1000 and ml % 1000 == 500):
                continue
            elif(ml > 15000):
                continue
            y.append(opl['latency_p%d' % p] / batch)
        plt.bar(x + (i - n/2 + 0.5) * width, y, width=width * 0.8, label='P%d' % p,
                color=COLOR_LIST[i])
        
    plt.xticks(ticks=x, labels=xlabels)
    plt.xlabel('Memory latency [usec]')
    plt.ylabel('Operation latency [usec]')
    plt.legend(bbox_to_anchor=(1, 0), loc='lower left')
    plt.title(title)
    plt.savefig(filename + '.pdf', bbox_inches='tight')
    plt.show()
