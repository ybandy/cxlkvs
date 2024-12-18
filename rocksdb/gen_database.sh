DB_BENCH_PATH=./rocksdb_photon/build

SSD_PATH=
export NUM_KEYS=1000000000

export JOB_ID=gen
export OUTPUT_DIR=`realpath ${JOB_ID}`
export DB_DIR=${SSD_PATH}/data
export WAL_DIR=${SSD_PATH}/wal
export COMPRESSION_TYPE=none
export USE_O_DIRECT=1


mkdir -p ${OUTPUT_DIR}
rm -rf DB_DIR WAL_DIR

pushd ${DB_BENCH_PATH}

ulimit -n 10000
../tools/benchmark.sh filluniquerandom

popd
