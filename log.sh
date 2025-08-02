CTFD_DIR=~/Desktop/CTFd

pushd $CTFD_DIR

docker-compose logs | tail -n 100

popd