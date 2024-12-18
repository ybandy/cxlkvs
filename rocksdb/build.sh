#!/usr/bin/bash

git clone https://github.com/axboe/liburing.git
pushd liburing
git checkout liburing-2.4
./configure
make
popd

git clone https://github.com/cameron314/concurrentqueue.git
pushd concurrentqueue
git checkout v1.0.4
popd

URING_ROOT_DIR=`realpath liburing`

git clone https://github.com/ybandy/rocksdb.git rocksdb_photon
pushd rocksdb_photon
git checkout cxlkvs_v1.0

cmake -B build -D INIT_PHOTON_IN_ENV=on -D WITH_LZ4=off -D WITH_SNAPPY=off -D CMAKE_BUILD_TYPE=Release -D FAIL_ON_WARNINGS=off -D WITH_NUMA=on -D PHOTON_ENABLE_URING=on -D URING_ROOT_DIR=$URING_ROOT_DIR -D ENABLE_PREFETCH=on

cmake --build build -t db_bench -j `nproc`

popd
