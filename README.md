# pragma-load-test
Load testing using Python + Locust to run load-test scripts against Pragma

## Installation
Make sure you install version 3.10 or lower, 3.11 has removed support for some of the legacy generator based coroutine objects

Run pip to install the requirements defined in the `requirements.txt` file:
```
python -m pip install -r requirements.txt
```


## Usage

First you will need to generate some load test users. Users are created by default named `test_user_0, test_user_1, ...` For different naming conventions, please use the `--starting-id` and `--user-id-prefix` command line arguments.

Local:

```
python create_players.py --host http://localhost:11200 --number 500
```

To run the tests in a headless mode, to get a response, run this command:

```
python -m locust -f websocket_client/locustfile.py --tags load_test --headless --host ws://localhost:10000 -u 9996 -r 100 --login-schema http --http-port 11000 --operator-port 11200
```

Matchmaking test:
To run a matchmaking test, you will need to run both the websocket_client and websocket_server, as the latter emulates calls made by the game server for matchmaking. It is recommended that you wait until all users are spawned for the websocket_server before initiating websocket_client.

Additionally, it is recommended that your local instance of Pragma is configured to use "pragma.matchcapacity.NoopCapacityProvider" since the server behavior is being simulated.

For ideal behavior, please ensure that the number of users spawned by websocket_server is 1/6 the number of users spawned by websocket_client. This ensures that each match of 6 users should have a guaranteed server to play on when they are matched together.

Both scripts can be launched using `server-client-webui.bat`. This will launch both scripts with seperate WebUI instances at http://localhost:8088/ (server script) and http://localhost:8089/ (client script), where configurations can be adjusted prior to start of test.

You can also run the scripts manually from the command line, in order to run one or both of the scripts headless.
```
python -m locust -f websocket_server/locustfile.py --tags load_test --host ws://localhost:10100 -u 100 -r 10 --login-schema http --http-port 11000 --operator-port 11200 --headless

python -m locust -f websocket_client/locustfile.py --tags load_test --host ws://localhost:10000 -u 600 -r 12 --login-schema http --http-port 11000 --operator-port 11200 --matchmaking-script "configs/websocket_matchmaking_full.json"
```

Distributed load:
In order to scale up load beyond what a single script instance can support, you will need to make use of the --master / --worker configuration for the scripts, utilizing the following additional parameters:
* `-P 8088` Designates the port for the WebUI (Defaults to 8089) Useful to coordinate the server script alongside the client script.
* `--master` Designates this script instance as a Master. It will not run any clients, but will distribute the load among all workers connected to it.
* `--master-bind-port 5556` Designates the port for the Master script to listen on (Defaults to 5557). Will match with any workers who connect to that port.
* `--worker` Designates this script instance as a Worker. It must have access to all local python files, but will only run tests using the distributed load coordinated by its connected master.
* `--master-port 5556` Designates the port that the worker expects to connect to the Master through (Defaults to 5557). Must match an existing use of master-bind-port, or use default.
* `--master-host X.X.X.X` Designates the hostname/IP of the master to connect to (Defaults to 127.0.0.1) Not needed when both worker and master on the same machine.
For more details, see https://docs.locust.io/en/stable/running-distributed.html
Load will be distributed evenly among all connected workers.
Example cmdlines to use for local workers and masters for both Matchmaking scripts in tandem (with as many Worker scripts run as needed). According to Locust documentation, overall script count should not exceed cores on a machine for maximum performance. WebUI will be spun up at http://localhost:8088/ (server script) and http://localhost:8089/ (client script)
NOTE: Due to how command line parameters are only propogated out from Master after test-start, targeting a locally deployed Pragma may result in issues during test startup for the workers. If that occurs, please locally change the default value for `login-schema` in both locustfiles to `http`.
```
python -m locust -f websocket_server/locustfile.py --tags load_test --host ws://localhost:10100 -u 200 -r 10 --login-schema http --http-port 11000 --operator-port 11200 --master -P 8088 --master-bind-port 5556
python -m locust -f websocket_server/locustfile.py --tags load_test --host ws://localhost:10100 --login-schema http --http-port 11000 --operator-port 11200 --headless --worker --master-port 5556

python -m locust -f websocket_client/locustfile.py --tags load_test --host ws://localhost:10000 -u 1200 -r 12 --login-schema http --http-port 11000 --operator-port 11200 --matchmaking-script "configs/websocket_matchmaking_full.json" --master --master-bind-port 5557 -P 8089
python -m locust -f websocket_client/locustfile.py --tags load_test --host ws://localhost:10000 --login-schema http --http-port 11000 --operator-port 11200 --worker --master-port 5557
```

Live:
Make sure you're connected to the correct VPN to talk to the portal

Create users:
```
python create_players.py --host https://live.internal.spectre.tacshooter.systems:11200 --player-host=https://live.spectre.tacshooter.systems:11000  --number 10000
```

Load test:
```
python -m locust -f websocket_client/locustfile.py --tags load_test --headless --host wss://live.spectre.tacshooter.systems:10000 --operator-host https://live.internal.spectre.tacshooter.systems:11200 -u 9996 -r 25 --login-schema https --http-port 11000 --operator-port 11200
```

Troubleshooting:

If you get a bunch of service errors during login you may need to force create the users (sometimes they are found during the create_players script but need to be re-created)

Add the "--force-create True" flag:

```
python3.10.exe create_players.py --host http://localhost:11200 --number 10000 --force-create True
```

### Configurations

General Command Line Arguments:
* `-f websocket_client\locustfile.py` - the name of the initial locustfile to start.
* `--tags load_test` - This will run the load_test tagged tests, allows us to group different tests together and choose which ones to run
* `--headless` - Tells locust not to spin up the WebUI client, and to exit when all processes are complete or an exception is raised.
* `--host http://localhost:11200` - The host name to run tests against.  This should be the scheme, hostname, and port.
* `--login-schema`- The schema used for the login server. Must be http or https. (Usually the former for local, the latter for live)
* `--http-port` - Port number to access http requests (Default to 11000)
* `--operator-port` - Port number for operator http access (Default to 11200)
* `--partner-port` - Port number for partner http access (Default to 10100)
* `-u 10` - How many users to run the load tests with
* `-r 10` - How many users to spawn at a time, does not have to match the number of users
* `--show-responses` - Show the responses from Pragma on the standard output.

Command Line Arguments for Websocket_Client:
* `--num-matches-min` - Minimum number of matches for each user to play. (Default 4)
* `--num-matches-max` - Maximum number of matches for each user to play. (Default 4)
* `--num-parties-of-3` - Number of parties of size 3 to form. (Default 0)
* `--num-parties-of-2` - Number of parties of size 2 to form. (Default 0)
* `--matchmaking-script` - json script to use for matchmaking cycle. (Default script goes through full matchmaking flow and relies on running alongside Websocket_Server)
* `--wait-between-matches-min` - Minimum wait in seconds between the conclusion of one match and re-entering matchmaking (default 30)
* `--wait-between-matches-max` - Maximum wait in seconds between teh conclusion of one match and re-entering matchmaking (default 120)
* `--user-id-prefix` - Prefix for the username of accounts to use for test (Default test_user_)
* `--starting-id` - Starting id for used accounts to increment up from (Default 0)

Command Line Arguments for Websocket_Server:
* `--match-duration-min` - Minimum duration in seconds for a given match before end. (Default 30, increase if more realistic game times are required)
* `--match-duration-max` - Maximum duration in seconds for a given match before end. (Default 30, increase if more realistic game times are required)


### Headed Mode
To run with a WebUI, run this command:

```
python -m locust -f .\http_client\locustfile.py --tags load_test
```

This will start a webclient at <http://localhost:8089> and you can set the number of users, spawn rate, and host name there, and get reports about the tests executing.

## Workflow
The general workflow of the Load Tests are as follows:

1. Load the locustfile.py script
2. Process `init` events with listeners (only the `init` method in `locustfile.py` meets this criteria)
3. Proxcess `test_start` events with listeners (the `on_test_start` in `locustfile.py`)
4. This creates the `User` objects defined in `pragma_player.py` and executes the `__init__` method there
5. This also creates the user in Pragma (we can pull this if we want, providing a list of users later)
6. When invoked by the WebUI, or the automatically by the headless mode, begin tests
7. For each test object (`User` type in our case), execute the `on_start` method
8. This logs our user in and retrieves the `pragmaSocialToken` (we can change this to retrieve the game token as well)
9. Executes `@task` methods which interpret the `script.json` file
10. For each element in `script.json`, there is a timeout, if the call takes more than the timeout, an exception is raised and the process stop.

## Script Files
Script files are defined as such:

```
{
    "script": [
        {
            "name": "login",
            "uri": "v1/account/authenticateorcreatev2",
            "body": "{\"providerId\": 1, \"providerToken\": \"{\\\"accountId\\\":\\\"{{social_id}}\\\",\\\"displayName\\\":\\\"{{social_id}}\\\"}\", \"gameShardId\":\"00000000-0000-0000-0000-000000000001\"}",
            "headers": "{\"Content-Type\":\"application/json\", \"Accept\": \"application/json\"}",
            "return": {"playerSocialToken": ["pragmaTokens","pragmaSocialToken"]},
            "acceptable-timeout": "60"
        },
        {
            "name": "exit"
        }
    ]
}
```

* name: The name of the step in the script, used for reporting
* uri: The URI to reach in Pragma
* body: The data sent to pragma, as a string (note the excessive slashes, this enables proper quoting for the json-as-a-string)
* headers: Any headers necessary for the call to be made, may include authentication data
* return: A json block of variables to be returned.  See below for more details
* acceptable-timeout: The maximum time we should wait for this process to return.

### Variables
Variables can be injected into load test scripts with macros that look like this:
```
"{\"providerId\": 1, \"providerToken\": \"{\\\"accountId\\\":\\\"{{social_id}}\\\",\\\"displayName\\\":\\\"{{social_id}}\\\"}\", \"gameShardId\":\"00000000-0000-0000-0000-000000000001\"}"
```

In this case, the value of the variable `social_id` will be inserted into the line wherever `{{social_id}}` exists.  This allows for dynamic calls to Pragma without hardcoding scripts.

### Returns
To get data back from a Pragma call, and use it in a later script step, we load the data into an environment variable as needed.  This is defined in a json block like so:

```
{
    "playerSocialToken": [
        "pragmaTokens",
        "pragmaSocialToken"
    ]
}
```

In this case, `playerSocialToken` is the variable we will store the value into.  `pragmaTokens` and `pragmaSocialToken` are the layered values in the returned json from the call that we will look in, for the value.  It is interpreted as `response_json['pragmaTokens']['pragmaSocialToken']`.

### Exit
The last line in the call should be the exit call.  It is formatted like so:
```
        {
            "name": "exit"
        }
```

Simply having the `name` of `exit` will tell the load test scripts that the script is finished, and to exit the runner for this user.
