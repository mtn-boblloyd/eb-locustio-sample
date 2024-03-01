#!/bin/bash
set -xe

echo $TYPE

su webapp <<_

curl https://pyenv.run | bash;
pyenv install 3.10.4 && pyenv global 3.10.4
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> /home/webapp/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> /home/webapp/.bashrc
echo 'export PATH="$PYENV_ROOT/shims:$PATH"' >> /home/webapp/.bashrc
echo 'eval "$(pyenv init -)"' >> /home/webapp/.bashrc

source ~/.bashrc 
eval "$(pyenv init -)" 
python -m pip install locust==2.16.1 locust-plugins==4.0.0 paho-mqtt==1.6.1 websocket-client==1.6.2 ujson
_

if [ "$TYPE" == "controller" ]; then
    echo "source ~/.bashrc && cd /var/app/current && python -m locust -f ./http_client/locustfile.py --tags load_test" > application
else
    echo "source ~/.bashrc && python --version" > application
fi

chmod 755 application
