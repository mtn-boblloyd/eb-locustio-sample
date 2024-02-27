import time
import gevent
from common import USERS, RUNNING
from locust import events
from locust.runners import STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP, WorkerRunner
from pragma_player import PragmaPlayer

@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument("--social-port", type=str, default="11000", help="Port number to access social http requests")
    parser.add_argument("--show-responses", action="store_true", default=False, help="Show the responses from Pragma on the standard output")
    parser.add_argument("--user-file", type=str, default="users.txt", help="File to read a list of users from.  They should already be created.")

@events.init.add_listener
# def on_locust_init(environment, **_kwargs):
def init(environment, **_kwargs):
    if not isinstance(environment.runner, WorkerRunner):
        gevent.spawn(checker, environment)

@events.test_start.add_listener
def on_test_start(environment, **_kwargs):
    try:
        with open(environment.parsed_options.user_file, "r") as user_file:
            users_list = user_file.read().splitlines()
        if len(users_list) < environment.runner.target_user_count:
            raise AttributeError("The requested number of users is less than the available user name list, please check the number of users and try again.")
        for user in users_list:
            USERS.append(user)
    except AttributeError as e:
        print("The requested number of users is less than the available user name list, please check the number of users and try again.")
        environment.runner.quit()
        raise

def checker(environment):
    while not environment.runner.state in [STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP]:
        for run in RUNNING:
            data = RUNNING.get(run)
            run_time = time.time() - data.get('start-time')
            timeout = data.get('timeout')
            if run_time > data.get('timeout'):
                print(f"Function timed out!")    
                environment.runner.quit()
                raise TimeoutError("Process timed out during run call!")
        time.sleep(1)
        if not RUNNING:
            print("All threads are exited!  Closing process now.")
            environment.runner.quit()