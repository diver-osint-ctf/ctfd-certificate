#!/bin/bash

SCRIPT_DIR=$(dirname "$0")
cd "$SCRIPT_DIR"

CTFD_DIR=~/Desktop/CTFd

# 古いプラグインディレクトリを削除
rm -rf $CTFD_DIR/CTFd/plugins/ctfd-certificate

# 新しいプラグインをコピー
cp -r ../ctfd-certificate $CTFD_DIR/CTFd/plugins/ctfd-certificate

pushd $CTFD_DIR

# Install python dependencies
# Install system dependencies for WeasyPrint
docker-compose exec -T ctfd apt-get update
docker-compose exec -T ctfd apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libglib2.0-0

docker-compose exec -T ctfd pip install -r /opt/CTFd/CTFd/plugins/ctfd-certificate/requirements.txt

docker-compose restart

popd

echo "deploy complete"