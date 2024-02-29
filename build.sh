#!/bin/bash
set -xe

echo $TYPE

source ~/.bashrc
if [ "$TYPE" == "controller" ]; then
    echo "source /root/.bashrc && cd /var/app/current && python -m locust -f locustfile.py --tags load_test --host ws://localhost:10100 -u 100 -r 10 --login-schema http --http-port 11000 --operator-port 11200 --headless --master -P 8088 --master-bind-port 5556" > application
else
    echo "source /root/.bashrc && python --version" > application
fi

chmod 755 application
