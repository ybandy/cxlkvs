BENCHMARK=../aerospike-benchmark/target/asbench
K=20000000
VALUE_SIZE=1470
NS=bar
HOST="127.0.0.1"
THREADS_LIST="128 256 384 512"
TRIGGER_PRE_COMMAND=""
TRIGGER_POST_COMMAND=""

while getopts "k:v:t:p:P:" opt; do
  case $opt in
  k) K=$OPTARG;;
  v) VALUE_SIZE=$OPTARG;;
  t) THREADS_LIST="$OPTARG";;
  p) TRIGGER_PRE_COMMAND="$OPTARG";;
  P) TRIGGER_POST_COMMAND="$OPTARG";;
  *) exit 1;;
  esac
done

OPTS="-h $HOST -p 3000 -n $NS -k $K -o S$VALUE_SIZE -T 10000 --connect-timeout 10000"
OPTS="$OPTS --output-period 100000 --max-conns-per-node 8192"

ulimit -n 200000

wait_busy_queues() {
  for ns in $*; do
    while echo namespace/$ns | netcat -W 1 $HOST 3003 | tr ';' '\n' | grep -q '\.write_q=[1-9]'; do
      sleep 10
    done
    while echo namespace/$ns | netcat -W 1 $HOST 3003 | tr ';' '\n' | grep -q '\.defrag_q=[1-9]'; do
      sleep 10
    done
  done
}

scaling_governor=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
if [ "$scaling_governor" != performance ]; then
  echo scaling_governor is not performance
  exit 1
fi

if [ -n "$TRIGGER_PRE_COMMAND" ]; then
  $TRIGGER_PRE_COMMAND
fi

for THREADS in 256; do
time $BENCHMARK $OPTS -w I --threads $THREADS
wait_busy_queues $NS
done

# make defrag happen
for THREADS in 256; do
    batch_sub_write_success=0
    while [ $batch_sub_write_success -lt $((K * 2)) ]; do
        time $BENCHMARK $OPTS -w RU,0 --batch-write-size 10 -t 300 --threads $THREADS
        batch_sub_write_success=`echo namespace/$ns | netcat -W 1 $HOST 3003 | tr ';' '\n' | grep '^batch_sub_write_success=' | awk -F= '{ print $2 }'`
        wait_busy_queues $NS
    done
done

OPTS="$OPTS -latency -t 30"

for cxl_latency in 500 1000 2000 3000 4000 5000 10000; do

if [ -n "$TRIGGER_POST_COMMAND" ]; then
  $TRIGGER_POST_COMMAND $cxl_latency
fi

RU=50

for THREADS in $THREADS_LIST; do
time $BENCHMARK $OPTS -w RU,$RU --batch-read-size 10 --batch-write-size 10 --threads $THREADS
wait_busy_queues $NS
done

done # for cxl_latency

if [ -n "$TRIGGER_POST_COMMAND" ]; then
  $TRIGGER_POST_COMMAND 1
fi
