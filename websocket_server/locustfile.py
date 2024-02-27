import gevent
import time
from common import USERS, RUNNING
from locust import events
from locust.runners import STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP, STATE_INIT, WorkerRunner
from pragma_operator import PragmaOperator
from pragma_server import PragmaWSServer
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
    parser.add_argument("--show-responses", action="store_true", default=False, help="Show the responses from Pragma on the standard output")
    parser.add_argument("--match-duration-min", type=int, default=30, help="Minimum duration in seconds for a given match before end. (Rounded to nearest 10 for KeepAlive calls)")
    parser.add_argument("--match-duration-max", type=int, default=30, help="Maximum duration in seconds for a given match before end. (Rounded to nearest 10 for KeepAlive calls)")

@events.init.add_listener
# def on_locust_init(environment, **_kwargs):
def init(environment, **_kwargs):
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
    print(f"Server count: {environment.runner.target_user_count}")

def checker(environment):
    while not environment.runner.state in [STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP, STATE_INIT]:
        gevent.sleep(5)
        if environment.runner.stats.total.num_failures > 0:
            print("Failed to run a test, quitting!")
            environment.runner.quit()
        if not RUNNING:
            print("All threads are exited!  Closing process now.")
            environment.runner.quit()
