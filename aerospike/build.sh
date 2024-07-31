#!/bin/bash

set -x -e


# build Aerospike server
git clone https://github.com/ybandy/aerospike-server
pushd aerospike-server
git checkout cxlkvs_v1.0
git submodule update --init

git clone https://github.com/pmodels/argobots.git modules/argobots
pushd modules/argobots
git checkout v1.2rc1
popd

git clone https://github.com/axboe/liburing.git modules/liburing
pushd modules/liburing
git checkout liburing-2.4
popd

make USE_ARGOBOTS=1 USE_CHECKPOINT=0
make init
popd


# build Aerospike benchmark
git clone https://github.com/aerospike/aerospike-benchmark
pushd aerospike-benchmark
git checkout 2.0.0

# force log output
sed -i -z 's/if (any_records)/if (true)/2' src/main/latency_output.c

# https instead of git
sed -i -e 's/git@github.com:/https:\/\/github.com\//g' .gitmodules
git submodule update --init --recursive

# enable inline SSD
sed -i 's/p->allow_inline_ssd = false;/p->allow_inline_ssd = true;/' modules/c-client/src/include/aerospike/as_policy.h

make EVENT_LIB=libuv
popd
