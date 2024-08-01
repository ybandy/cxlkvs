# SSD-Based Key-Value Stores on Microsecond-Latency CXL Memory

We study the possibility of displacing most of in-memory data structures of SSD-based KV stores
from the host DRAM to CXL memory with microsecond-level latency, and still achieving competitive KV throughputs.

This repository contains code to evaluate the following three pieces of software.
* Microbenchmark
* [Modified Aerospike](https://github.com/ybandy/aerospike-server)
* [Modified CacheLib](https://github.com/ybandy/CacheLib)

## Hardware Requirements

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
