#!/bin/bash
set -xe

echo $TYPE

whoami

echo "checking if pyenv is already set up in webapp."
cat /home/webapp/.bashrc | grep PYENV_ROOT
if [ "$(cat /home/webapp/.bashrc | grep PYENV_ROOT)" == "" ]; then
    curl https://pyenv.run | bash;
    echo "Inside pyenv bashrc setup"
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> /home/webapp/.bashrc
    echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> /home/webapp/.bashrc
    echo 'export PATH="$PYENV_ROOT/shims:$PATH"' >> /home/webapp/.bashrc
    echo 'eval "$(pyenv init -)"' >> /home/webapp/.bashrc
fi

echo "checking if python version 3.10.4 is already installed"
ls /home/webapp/.pyenv/versions/3.10.4
if [ -d /home/webapp/.pyenv/versions/3.10.4/ ]; then
    echo "Inside python install..."
    source ~/.bashrc
    eval "$(pyenv init -)"
    source ~/.bashrc && pyenv install 3.10.4 && pyenv global 3.10.4
    source ~/.bashrc && python -m pip install locust==2.16.1 locust-plugins==4.0.0 paho-mqtt==1.6.1 websocket-client==1.6.2 ujson
fi

echo "Done with webapp user configuration, building the application file."

if [ "$TYPE" == "controller" ]; then
    echo "source ~/.bashrc && cd /var/app/current && python -m locust -f ./http_client/locustfile.py --tags load_test" > application
else
    echo "source ~/.bashrc && python --version" > application
fi

cat application

chmod 755 application