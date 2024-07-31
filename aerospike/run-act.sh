KEYS=20000000
VALUE_SIZE=1470
SERVER_DIR=aerospike-server
SERVER_CPU_LIST=0-17
CLIENT_CPU_LIST=18-35
SERVER_THREADS_LIST="32"
CLIENT_THREADS_LIST="64"
TRIGGER_PRE_COMMAND=""
TRIGGER_POST_COMMAND=""
ACT=act.sh

while [[ $# -gt 0 ]]; do
  source $1
  shift
done

if [ -z "$LOGDIR" ]; then
  LOGDIR=$SERVER_DIR-log
fi

mkdir -p $LOGDIR

ulimit -n 200000

# fio --name=trim --filename=/dev/md0 --rw=trim --bs=3G
pushd $SERVER_DIR
make stop
popd
sleep 60

for service_threads in $SERVER_THREADS_LIST; do
  sed -i.bak "s/service-threads .*/service-threads $service_threads/" $SERVER_DIR/as/etc/aerospike_dev.conf
  cp $SERVER_DIR/as/etc/aerospike_dev.conf $LOGDIR/act-$service_threads.conf

  pushd $SERVER_DIR
  taskset -c $SERVER_CPU_LIST make start &
  popd
  sleep 60

  taskset -c $CLIENT_CPU_LIST bash $ACT -k $KEYS -v $VALUE_SIZE -t "$CLIENT_THREADS_LIST" -p "$TRIGGER_PRE_COMMAND" -P "$TRIGGER_POST_COMMAND" 2>&1 | tee $LOGDIR/act-$service_threads.log

  pushd $SERVER_DIR
  make stop
  popd
  sleep 60
done

