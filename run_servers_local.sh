#!/bin/bash

python3.10.exe -m locust -f websocket_server/locustfile.py --tags load_test --host ws://localhost:10100 -u 500 -r 10 --login-schema http --http-port 11000 --operator-port 11200 --headless
