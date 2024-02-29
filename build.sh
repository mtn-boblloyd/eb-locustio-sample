echo $TYPE

source ~/.bashrc
cd /var/app/current
if [ "$TYPE" == "controller" ]; then
    python -m locust -f /var/app/current/websocket_server/locustfile.py --tags load_test --host ws://localhost:10100 -u 100 -r 10 --login-schema http --http-port 11000 --operator-port 11200 --headless --master -P 8088 --master-bind-port 5556
else
    python --version
fi