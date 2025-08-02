#!/bin/bash

SCRIPT_DIR=$(dirname "$0")
cd "$SCRIPT_DIR"

CTFD_DIR=~/Desktop/CTFd

yes | cp -r ./ctfd_certificate $CTFD_DIR/CTFd/plugins/ctfd_certificate

pushd $CTFD_DIR

docker-compose restart

popd

echo "deploy complete"