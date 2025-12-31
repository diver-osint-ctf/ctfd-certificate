PLUGINS_PATH=${1:-"/opt/CTFd/CTFd/plugins"}

# Install python dependencies
# Install system dependencies for WeasyPrint
docker compose exec -T ctfd apt-get update
docker compose exec -T ctfd apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libglib2.0-0

docker compose exec -T ctfd pip install -r $PLUGINS_PATH/ctfd-certificate/requirements.txt
