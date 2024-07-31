#!/bin/bash

CACHELIB_DIR=CacheLib
CONFIG=bh-test.json
NAME=mytest
#PERF_RECORD="perf record -F 99 -a -g --call-graph dwarf"
#PERF_RECORD="perf record -a"

CACHE_CONFIG_NAVY_DIRECT=true
CACHE_CONFIG_DELAY_NSEC=0
CACHE_CONFIG_MEMBIND_NODES="\"0\""
CACHE_CONFIG_NVM_CACHE_SIZE_MB=400000
TEST_CONFIG_NUM_THREADS=1
TEST_CONFIG_NUM_FIBERS=10
CACHEBENCH_ARGS="--timeout_seconds 0 --report_ac_memory_usage_stats human_readable"
NUM_KEYS_LIST="10000000"
NUM_OPS=100000000


while [[ $# -gt 0 ]]; do
	source $1
	shift
done

scaling_governor=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
if [ "$scaling_governor" != performance ]; then
	echo scaling_governor is not performance
	exit 1
fi

if [ -n "$PERF_RECORD" ]; then
	sudo sysctl -w kernel.kptr_restrict=0
	sudo sysctl -w kernel.perf_event_paranoid=-1
fi

set -x -e

LOG_DIR=$CACHELIB_DIR-log

CACHELIB_DIR_PATH=$(realpath $CACHELIB_DIR)
LOG_DIR_PATH=$(realpath $LOG_DIR)
CONFIG_PATH=$(realpath $CONFIG)

mkdir -p $LOG_DIR
pushd $CACHELIB_DIR

for keys in $NUM_KEYS_LIST; do
	for ops in $NUM_OPS; do
	for sigmaFactor in 1.0; do
		sed "s/\"numKeys\".*/\"numKeys\" : $keys,/" $CONFIG_PATH |
		sed "s/\"numOps\".*/\"numOps\" : $ops,/" |
		sed "s/\"sigmaFactor\".*/\"sigmaFactor\" : $sigmaFactor,/" |
		sed "s/\"navyTryBlocking\".*/\"navyTryBlocking\" : $CACHE_CONFIG_NAVY_DIRECT,/" |
		sed "s/\"prefetchDelayNSec\".*/\"prefetchDelayNSec\" : $CACHE_CONFIG_DELAY_NSEC,/" |
		sed "s/\"memBindNodes\".*/\"memBindNodes\" : $CACHE_CONFIG_MEMBIND_NODES/" |
		sed "s/\"nvmCacheSizeMB\".*/\"nvmCacheSizeMB\" : $CACHE_CONFIG_NVM_CACHE_SIZE_MB,/" |
		sed "s/\"numThreads\".*/\"numThreads\" : $TEST_CONFIG_NUM_THREADS,/" |
		sed "s/\"numFibers\".*/\"numFibers\" : $TEST_CONFIG_NUM_FIBERS,/" > $LOG_DIR_PATH/$NAME-$keys-$ops-$sigmaFactor.json
		rm -rf /tmp/mem-tier/
		if [ -n "$PERF_RECORD" ]; then
			$PERF_RECORD -D 30000 -o $LOG_DIR_PATH/$NAME-$keys-$ops-$sigmaFactor.perf.data -- sleep 60 &
		fi
		env LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$CACHELIB_DIR_PATH/opt/cachelib/lib \
		./opt/cachelib/bin/cachebench --json_test_config $LOG_DIR_PATH/$NAME-$keys-$ops-$sigmaFactor.json \
			--report_api_latency \
			--progress_stats_file $LOG_DIR_PATH/$NAME-$keys-$ops-$sigmaFactor.stats \
			$CACHEBENCH_ARGS |
			tee $LOG_DIR_PATH/$NAME-$keys-$ops-$sigmaFactor.log
		wait
	done
	done
done
popd
