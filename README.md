# SSD-Based Key-Value Stores on Microsecond-Latency CXL Memory

We study the possibility of displacing most of in-memory data structures of SSD-based KV stores
from the host DRAM to CXL memory with microsecond-level latency, and still achieving competitive KV throughputs.

This repository contains code to evaluate the following three pieces of software.
* Microbenchmark
* [Modified Aerospike](https://github.com/ybandy/aerospike-server)
* [Modified CacheLib](https://github.com/ybandy/CacheLib)


## System Requirements

The code assumes that
* Long latency memory is exposed as separate NUMA nodes from the host DRAM
* Latency of the memory can be adjusted

The computational environment we tested is as follows.
We use CXL-enabled CPUs and FPGAs, and the FPGAs work as CXL memory with adjustable latency.

|Part     |Specifications |
|---------|---------------|
|CPU 0/1  |2 of Intel Xeon Gold 6430 (32 cores/CPU, 2.10 GHz) |
|DRAM     |DDR5 4800 MHz 512 GB (32 GB × 8 ch./CPU) |
|CXL      |2 of Intel Agilex 7 FPGA I-Series Dev. Kit (128 GB) |
|SSD      |4 of Intel Optane 900P 480 GB NVMe (1.92 TB) |
|OS       |Ubuntu 22.04.4 LTS, Linux kernel 6.5.0 |


## System Setup

1. Setup long latency memory as NUMA nodes

   This depends on your environment, and the memory does not necessarily need to be CXL memory.
   The latency of the memory needs to be adjustable and the code assumes that a script for setting latency is provided at home.
   ```
   ~/set_latency.sh <latency_nsec>
   ```
   
1. Add the user to disk group

   This is to give permission for the user to write to block devices.
   ```
   usermod -aG disk $USER
   ```

1. Enable SSD polling

   ```
   for i in 5a 5b 5c 5d; do echo 0000:$i:00.0 > unbind; done
   echo 24 >  /sys/module/nvme/parameters/poll_queues
   for i in 5a 5b 5c 5d; do echo 0000:$i:00.0 > bind; done
   ```
   Note that you need to change the PCIe device ID (such as 0000:5a:00.0) according to your environment.
   
1. Disable simultaneous multithreading (SMT)

   Add `nosmt` to `GRUB_CMDLINE_LINUX_DEFAULT` in /etc/default/grub, run `update-grub`, and reboot.
   Alternatively, one could also disable it in the BIOS settings.

1. Disable hardware prefetching

   In the case of Intel CPUs, run:
   ```
   sudo wrmsr --all 0x1a4 0x2f
   ```
   
1. Set CPUFreq Governor to performance

   ```
   sudo cpupower frequency-set -g performance
   ```

## Microbenchmark

1. Build

   ```
   cd microbench
   ./build.sh
   ```

1. Run

   ```
   python3 batch.py
   ```
   This will run the microbenchmark with various combinations of parameters.

1. Check results

   Open and run Jupyter Notebook `notebooks/microbench.ipynb`


## Modified Aerospike

1. Build

   ```
   cd aerospike
   ./build.sh
   ```

1. Edit the server config

   Edit `aerospike-server/as/etc/aerospike_dev.conf` according to your environment.

   * Specify SSDs (`device`)
     
     Using device symbolic links is recommended over direct specification such as `/dev/nvme0n1`, as the latter can change upon reboot.
     ```
     device /dev/disk/by-id/nvme-INTEL_SSDPE21D480GA_PHM28090019Q480BGN
     device /dev/disk/by-id/nvme-INTEL_SSDPE21D480GA_PHM2813300BX480BGN
     device /dev/disk/by-id/nvme-INTEL_SSDPE21D480GA_PHM28134000W480BGN
     device /dev/disk/by-id/nvme-INTEL_SSDPE21D480GA_PHM2813400GC480BGN
     ```
     
   * Specify the number of CPU cores (`service-xstreams`)
     
     {1, 2, 4, 8, 16} in our evaluation
     
   * Specify which NUMA node memory to use (`node-mask`)
     
     For instance, in an environment with
     * Node 0: host DRAM (CPU 0)
     * Node 1: host DRAM (CPU 1)
     * Node 2: CXL memory device 0
     * Node 3: CXL memory device 1
     
     Node mask will be 1 (= 1 << 0) for the host DRAM, and 12 (= 1 << 2 | 1 << 3) for the (interleaved) CXL memory devices.

1. Select a benchmark config file and edit it as necessary

   The naming convention is `run-act-<type>-<memory>-<N>core.conf`, where

   * `<type>`: `ro` for read-only workload, `rw` for read-write-mix workload
   * `<memory>`: `dram` for DRAM, `cxl` for CXL memory
   * `<N>`: the number of CPU cores
  
   `SERVER_CPU_LIST` and `CLIENT_CPU_LIST` may need to be edited so that servers work on CPU 0 and clients on CPU 1.

1. Run the selected benchmark

   ```
   nohup bash run-act.sh run-act-<type>-<memory>-<N>core.conf &
   ```
   `nohup` is recommended because each benchmark can take hours.

1. Check the results

   Open and run Jupyter Notebook `notebooks/aerospike.ipynb`
