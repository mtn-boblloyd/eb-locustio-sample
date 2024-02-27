#!/bin/bash
python3.10.exe -m locust -f websocket_client/locustfile.py --tags=load_test --headless --users=9996 --host=ws://localhost:10000 -r=250 --login-schema=http --http-port=11000 --operator-port=11200
