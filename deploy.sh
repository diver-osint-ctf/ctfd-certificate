#!/bin/bash

SCRIPT_DIR=$(dirname "$0")
cd "$SCRIPT_DIR"

CTFD_DIR=~/Desktop/CTFd

# 古いプラグインディレクトリを削除
rm -rf $CTFD_DIR/CTFd/plugins/ctfd_certificate

# 新しいプラグインをコピー
cp -r ./ctfd_certificate $CTFD_DIR/CTFd/plugins/ctfd_certificate

pushd $CTFD_DIR

docker-compose restart

popd

echo "deploy complete"