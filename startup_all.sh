PRAGMA_HOST=${1:-"dev.internal.spectre.mountaintop.pragmaengine.com"}
SERVER_WORKER_COUNT=${2:-1}
CLIENT_WORKER_COUNT=${3:-1}
WORKER_NODE_TYPE=${4:-t2.micro}

eb init --keyname mtn_aws --platform "Corretto 21 running on 64bit Amazon Linux 2023" --region us-west-1 spectre-lt

eb create --cname spectre-lt-server-control --envvars TYPE=server-controller,PRAGMA_HOST=$PRAGMA_HOST --instance_type t2.micro --platform "Corretto 21 running on 64bit Amazon Linux 2023" -im 1 -ix 1 spectre-lt-controller-server
eb create --cname spectre-lt-server-worker --envvars TYPE=server-worker,PRAGMA_HOST=$PRAGMA_HOST --instance_type $WORKER_NODE_TYPE --platform "Corretto 21 running on 64bit Amazon Linux 2023" -im $SERVER_WORKER_COUNT -ix $SERVER_WORKER_COUNT spectre-lt-worker-server 

eb create --cname spectre-lt-client-control --envvars TYPE=client-controller,PRAGMA_HOST=$PRAGMA_HOST --instance_type t2.micro --platform "Corretto 21 running on 64bit Amazon Linux 2023"  -im 1 -ix 1 spectre-lt-controller-client
eb create --cname spectre-lt-client-worker --envvars TYPE=client-worker,PRAGMA_HOST=$PRAGMA_HOST --instance_type $WORKER_NODE_TYPE --platform "Corretto 21 running on 64bit Amazon Linux 2023" -im $CLIENT_WORKER_COUNT -ix $CLIENT_WORKER_COUNT spectre-lt-worker-client