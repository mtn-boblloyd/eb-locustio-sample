# Copyright 2015-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file
# except in compliance with the License. A copy of the License is located at
#
#    http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is distributed on an "AS IS"
# BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under the License.

locust-master: /bin/bash -c "cd /var/app/staging && exec python -m locust -f /var/app/staging/websocket_server/locustfile.py --tags load_test --host ws://localhost:10100 -u 100 -r 10 --login-schema http --http-port 11000 --operator-port 11200 --headless --master -P 8088 --master-bind-port 5556"
# locust-follower: /bin/bash -c "exec /usr/local/bin/locust -f /var/app/staging/locustfile.py --port=9876 --slave --master-host=$(<.masterIP)"