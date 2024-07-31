#!/bin/bash

git clone https://github.com/pmodels/argobots.git
pushd argobots
git checkout v1.2rc1
./autogen.sh
./configure
make
popd

git clone https://github.com/axboe/liburing.git
pushd liburing
git checkout liburing-2.4
./configure
make
popd

make -C src
