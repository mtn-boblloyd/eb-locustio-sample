#!/bin/bash
set -xe

echo $TYPE

whoami

echo "checking if pyenv is already set up in webapp."
if [ ! -d /home/webapp/.pyenv ]; then
    echo "Inside pyenv bashrc setup"
    curl https://pyenv.run | bash
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> /home/webapp/.bashrc
    echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> /home/webapp/.bashrc
    echo 'export PATH="$PYENV_ROOT/shims:$PATH"' >> /home/webapp/.bashrc
    echo 'eval "$(pyenv init -)"' >> /home/webapp/.bashrc
fi

echo "checking if python version 3.10.4 is already installed"
if [ ! -d /home/webapp/.pyenv/versions/3.10.4/ ]; then
    echo "Inside python install..."
    source ~/.bashrc
    eval "$(pyenv init -)"
    source ~/.bashrc && pyenv install 3.10.4 && pyenv global 3.10.4
    source ~/.bashrc && python -m pip install locust==2.16.1 locust-plugins==4.0.0 paho-mqtt==1.6.1 websocket-client==1.6.2 ujson
fi

echo "Done with webapp user configuration, building the application file."

if [ "$TYPE" == "server-controller" ]; then
    echo "source ~/.bashrc && cd /var/app/current && python -m locust -f websocket_server/locustfile.py --tags load_test --host ws://$PRAGMA_HOST:11200 -u 200 -r 10 --login-schema http --http-port 11000 --operator-port 11200 --master -P 8089 --master-bind-port 5556 --operator-host https://$PRAGMA_HOST:11200 --login-schema https --http-port 11000 --operator-port 11200" > application
elif [ "$TYPE" == "client-controller" ]; then
    echo "source ~/.bashrc && cd /var/app/current && python -m locust -f websocket_client/locustfile.py --tags load_test --host ws://$PRAGMA_HOST:11200 -u 200 -r 10 --login-schema http --http-port 11000 --operator-port 11200 --master -P 8089 --master-bind-port 5556 --matchmaking-script configs/websocket_matchmaking_full.json --operator-host https://$PRAGMA_HOST:11200 --login-schema https --http-port 11000 --operator-port 11200" > application
elif [ "$TYPE" == "server-worker" ]; then
    echo "source ~/.bashrc && cd /var/app/current && python -m locust -f websocket_server/locustfile.py --tags load_test --host ws://$PRAGMA_HOST:11200 -u 200 -r 10 --login-schema http --http-port 11000 --operator-port 11200 --worker --master-host spectre-pragma-load-test-controller-server.us-west-1.elasticbeanstalk.com --master-bind-port 5556 --operator-host https://$PRAGMA_HOST:11200 --login-schema https --http-port 11000 --operator-port 11200" > application
elif [ "$TYPE" == "server-worker" ]; then
    echo "source ~/.bashrc && cd /var/app/current && python -m locust -f websocket_client/locustfile.py --tags load_test --host ws://$PRAGMA_HOST:11200 -u 200 -r 10 --login-schema http --http-port 11000 --operator-port 11200 --worker --master-host spectre-pragma-load-test-controller-client.us-west-1.elasticbeanstalk.com --master-bind-port 5556 --matchmaking-script configs/websocket_matchmaking_full.json --operator-host https://$PRAGMA_HOST:11200 --login-schema https --http-port 11000 --operator-port 11200" > application
else
    echo "Something is wrong, and the type is not matched!"
    exit 1
fi

cat application

chmod 755 application