#!/bin/bash
set -xe

echo $TYPE

source ~/.bashrc
cd /var/app/staging
mkdir -p bin
if [ "$TYPE" == "controller" ]; then
    echo "ced /var/app/current && python -m locust -f locustfile.py --tags load_test --host ws://localhost:10100 -u 100 -r 10 --login-schema http --http-port 11000 --operator-port 11200 --headless --master -P 8088 --master-bind-port 5556" > bin/application
else
    echo "python --version" > bin/application
fi

chmod 755 bin/application
