#!/bin/bash


set -x -e


git clone https://github.com/ybandy/CacheLib.git
pushd CacheLib
git checkout cxlkvs_v1.0

git clone https://github.com/axboe/liburing.git build-liburing
pushd build-liburing
git checkout liburing-2.4
./configure --prefix=$(realpath ..)/opt/cachelib
make
make install
popd

./contrib/build.sh -B -v
# fix fbthrift bug
sed -i '/server\/CPUConcurrencyController\.cpp/a server/IOUringUtil.cpp' cachelib/external/fbthrift/thrift/lib/cpp2/CMakeLists.txt
# enable iopoll
sed -i '/params_\.flags |= IORING_SETUP_CQSIZE/a \ \ params_.flags |= IORING_SETUP_IOPOLL;' cachelib/external/folly/folly/experimental/io/IoUring.cpp
# https instead of git
sed -i -e 's/git@github.com:/https:\/\/github.com\//g' .gitmodules

./contrib/build.sh -j -v -O -S
popd
