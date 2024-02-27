import gevent
import time
from common import USERS, RUNNING, PARTY_ROLES
from locust import events
from locust.runners import STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP, STATE_INIT, WorkerRunner, MasterRunner
from pragma_operator import PragmaOperator
from pragma_player import PragmaWSPlayer
from pragma import Pragma

DEBUG_GEVENT_DELAYS = False

# Get warnings / stacktraces if something appears to be blocking
if DEBUG_GEVENT_DELAYS:
    g_config = gevent.config
    g_config.monitor_thread = True
    g_config.max_blocking_time = 0.5

@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument("--operator-host", type=str, default=None, help="The host to use for accessing the operator when different from the main server (e.g. live.internal.etc ). Must be http or https.")
    parser.add_argument("--login-schema", type=str, default="https", help="The schema to use for the login server.  Must be http or https.")
    parser.add_argument("--http-port", type=str, default="11000", help="Port number to access http requests")
    parser.add_argument("--operator-port", type=str, default="11200", help="Port number for operator http access")
    parser.add_argument("--partner-port", type=str, default="10100", help="Port number for partner http access")
    parser.add_argument("--num-matches-min", type=int, default=4, help="Minimum number of matches for each user to play. User will play a value between min and max, inclusive.")
    parser.add_argument("--num-matches-max", type=int, default=4, help="Maximum number of matches for each user to play. User will play a value between min and max, inclusive.")
    parser.add_argument("--num-parties-of-3", type=int, default=0, help="Number of parties of size 3 to form.")
    parser.add_argument("--num-parties-of-2", type=int, default=0, help="Number of parties of size 2 to form.")
    parser.add_argument("--matchmaking-script", type=str, default="configs/websocket_matchmaking_full.json", help="json script to use for matchmaking cycle (default goes through full matchmaking flow)")
    parser.add_argument("--wait-between-matches-min", type=int, default=30, help="Minimum wait in seconds between the conclusion of one match and re-entering matchmaking.")
    parser.add_argument("--wait-between-matches-max", type=int, default=120, help="Maximum wait in seconds between the conclusion of one match and re-entering matchmaking.")
    parser.add_argument("--show-responses", action="store_true", default=False, help="Show the responses from Pragma on the standard output")
    parser.add_argument("--user-id-prefix", type=str, default="test_user_", help="Prefix for username of created accounts. (default: test_user_)")
    parser.add_argument("--starting-id", type=int, default=0, help="Starting id for created accounts to increment up from. (default: 0)")
    parser.add_argument("--mmr-test", action="store_true", default=False, help="Output time spent in queue when receiving match to console (Used for MMR Test Cases). Gating behind argument to reduce noise.")


# Fired when the worker receives a message of type 'user_list'
def setup_user_list(environment, msg, **kwargs):
    for user in msg.data:
        #print(f"User recieved: {user}")
        USERS.append(user)
    print(f"User count for worker: {len(USERS)}")
    environment.runner.send_message("acknowledge_users", f"Thanks for the users!")

def setup_party_role_list(environment, msg, **kwargs):
    party_count = 0
    for role in msg.data:
        if "Host" in role:
            party_count += 1
        PARTY_ROLES.append(role)
    print(f"Total party count for worker: {party_count}")
    environment.runner.send_message("acknowledge_users", f"Thanks for the party roles!")

# Fired when the master receives a message of type 'acknowledge_users'
def on_acknowledge(msg, **kwargs):
    print(msg.data)

@events.init.add_listener
# def on_locust_init(environment, **_kwargs):
def init(environment, **_kwargs):
    if not isinstance(environment.runner, MasterRunner):
        environment.runner.register_message('user_list', setup_user_list)
        environment.runner.register_message('party_role_list', setup_party_role_list)
    if not isinstance(environment.runner, WorkerRunner):
        environment.runner.register_message('acknowledge_users', on_acknowledge) 
    provided_schema = environment.host.split("://")[0]
    provided_port = environment.host.split(":")[-1]
    login_schema = environment.parsed_options.login_schema
    http_port = environment.parsed_options.http_port
    operator_host = environment.parsed_options.operator_host
    if not operator_host:
        operator_host = environment.host
        operator_port = environment.parsed_options.operator_port
        operator_host = operator_host.replace(provided_schema, login_schema).replace(provided_port, operator_port)

    partner_port = environment.parsed_options.partner_port
    partner_host = environment.host.replace(provided_schema, login_schema).replace(provided_port, partner_port)

    operator = PragmaOperator(host=operator_host,partner_host=partner_host)
    operator.authenticate_partner()

    if not isinstance(environment.runner, WorkerRunner):
        gevent.spawn(checker, environment)

@events.test_start.add_listener
def on_test_start(environment, **_kwargs):
    if not isinstance(environment.runner, WorkerRunner):
        try:
            USERS.clear()
            USERS.extend([f"{environment.parsed_options.user_id_prefix}{i}" for i in range(environment.parsed_options.starting_id, environment.parsed_options.starting_id + environment.runner.target_user_count)])
            print(f'Users count: {len(USERS)}')
            if isinstance(environment.runner, MasterRunner):
                worker_count = environment.runner.worker_count
                chunk_size = int(len(USERS) / worker_count)
                party2_remaining = environment.parsed_options.num_parties_of_2
                party2_chunk_size = int(party2_remaining / worker_count)
                party3_remaining = environment.parsed_options.num_parties_of_3
                party3_chunk_size = int(party3_remaining / worker_count)
                
                for i, worker in enumerate(environment.runner.clients):
                    start_index = i * chunk_size

                    if i + 1 < worker_count:
                        end_index = start_index + chunk_size
                        party2_count = party2_chunk_size
                        party2_remaining -= party2_chunk_size
                        party3_count = party3_chunk_size
                        party3_remaining -= party3_chunk_size
                    else:
                        end_index = len(USERS)
                        party2_count = party2_remaining
                        party3_count = party3_remaining

                    data = USERS[start_index:end_index]
                    environment.runner.send_message("user_list", data, worker)

                    for j in range(party2_count):
                        PARTY_ROLES.extend(["Host2", "Joiner"])
                    for j in range(party3_count):
                        PARTY_ROLES.extend(["Host3", "Joiner", "Joiner"])

                    data = PARTY_ROLES
                    environment.runner.send_message("party_role_list", data, worker)
                    PARTY_ROLES.clear()
            else:
                for i in range(environment.parsed_options.num_parties_of_2):
                    PARTY_ROLES.extend(["Host2", "Joiner"])
                for i in range(environment.parsed_options.num_parties_of_3):
                    PARTY_ROLES.extend(["Host3", "Joiner", "Joiner"])
        except AttributeError as e:
            print("The requested number of users is less than the available user name list, please check the number of users and try again.")
            environment.runner.quit()
            raise

def checker(environment):
    while not environment.runner.state in [STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP, STATE_INIT]:
        gevent.sleep(5)
        if environment.runner.stats.total.num_failures > 0:
            print("Failed to run a test, quitting!")
            environment.runner.quit()
        if not RUNNING:
            print("All threads are exited!  Closing process now.")
            environment.runner.quit()
