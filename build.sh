#!/bin/bash
set -xe

echo $TYPE

source ~/.bashrc
if [ "$TYPE" == "controller" ]; then
    echo "source ~/.bashrc && cd /var/app/current && python -m locust -f ./http_client/locustfile.py --tags load_test" > application
else
    echo "source ~/.bashrc && python --version" > application
fi

chmod 755 application
