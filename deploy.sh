#!/bin/bash

FILE=$(dirname $0)
cd $FILE/..

CTFD_DIR=~/Desktop/CTFd

yes | cp -r $FILE/ctfd-certificate $CTFD_DIR/CTFd/plugins/ctfd-certificate

pushd $CTFD_DIR

docker-compose restart

popd

echo "deploy complete"