import random
import uuid
import ujson as json
import common
import time
import base64
import gevent
import gevent.event
from common import RUNNING
from locust import User, task, between, events, tag
from pragma import Pragma
import pragma_operator
from websocket_client.pragma_websocket_user import PragmaWSUser

class PragmaGenericServer():
    def __init__(self):
        self.server_id = str(uuid.uuid4())
        self.headers = {
            # "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def parse_script_line(self, line, variables):
        if not "{{" in line or not "}}" in line:
            return line
        while "{{" in line:
            variable_name = line.split("{{", 1)[1].split("}}", 1)[0]
            variable_value = variables.get(variable_name)
            line = line.replace("{{" + variable_name + "}}", variable_value)
        return line

    def get_return_value(self, response, return_request):
        _response = response
        for path in return_request:
            _response = _response.get(path)
        return _response
    
class PragmaWSServer(PragmaWSUser, PragmaGenericServer):
    wait_time = between(1,5)

    def __init__(self, environment):
        self.connected = False
        self.last_received = 0
        self.provided_schema = environment.host.split("://")[0]
        self.provided_port = environment.host.split(":")[-1]
        self.login_schema = environment.parsed_options.login_schema
        self.http_port = environment.parsed_options.http_port
        self.show_responses = environment.parsed_options.show_responses
        # We ask the user to provide min and max duration in seconds, which we translate to how many 10s KeepAlive loops we perform
        self.min_keepalive_repeats = round(environment.parsed_options.match_duration_min / 10)
        self.max_keepalive_repeats = round(environment.parsed_options.match_duration_max / 10)
        self.rpc = "v1/rpc"
        self.players = []

        super().__init__(environment)
        self.http_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.ws_headers = {
            "Connection": "Upgrade",
            "Upgrade": "websocket",
            "Sec-WebSocket-Version": "13",
            "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits",
            "Accept": "application/json"
        }
        self.host = environment.host
        self.notifications = {}
        self.game_instance_id = None
        self.notify_result = gevent.event.Event()
    
    def on_start(self):
        self.partner_game_token = pragma_operator.OPERATOR.partner_game_token

    def process_message_by_type(self, type, message_data):
        match type:
            case "GameInstanceRpc.GetGameStartDataV1Response":
                #Fetch the player list for the game instance
                player_list = message_data['response']['payload']['gameStart']['players']
                for player in player_list:
                    self.players.append(player['playerId'])

    @tag('load_test')
    @task
    def load_test_script(self):
        script = None
        with open('websocket_server_script.json', 'r') as file:
            script = json.load(file)
        try:
            #Currently repeats its logic to stand ready as a server after each match
            while(True):
                self.call(script=script)
        finally:
            self.stop()
            if self in RUNNING:
                del RUNNING[self]

    def call(self, **kwargs):
        script = kwargs.get('script')

        script_vars = {"serverId": self.server_id, "partnerGameToken": self.partner_game_token}
        self.my_value = None

        for call in script.get('script'):
            call_name = call.get('name')
            
            # If we're not connected yet then connect now, we'll keep using the same connection for all the calls
            if not self.connected:
                headers = self.listize_element(call.get('headers') | self.ws_headers, script_vars)
                ws_url = f"{self.host}/{call.get('uri')}"
                self.connect(ws_url, headers)
                self.connected = True

            start_time = time.time()
            timeout = 10
            repeat = 0
            if call.get('acceptable-timeout'):
                timeout = int(call.get('acceptable-timeout'))
            if call_name == "keep game alive":
                if (self.min_keepalive_repeats < self.max_keepalive_repeats):
                    repeat = random.randrange(self.min_keepalive_repeats, self.max_keepalive_repeats)
                else:
                    repeat = self.min_keepalive_repeats
            if call_name == "exit":
                break
            if call_name == "connect players":
                #Prep the player list
                for i in range(len(self.players)):
                    script_vars[f"playerId{i}"] = self.players[i]
            if call_name == "end game":
                #prepare the player results
                for i in range(len(self.players)):
                    player_xp = random.randrange(10,100)
                    player_headshots = random.randrange(0,5)
                    script_vars[f"playerHeadshots{i}"] = str(player_headshots)
                    script_vars[f"playerXp{i}"] = str(player_xp)
            if call_name == "wait":

                success_type = call.get("success")
                failure_type = call.get("failure")

                elapsed_time = (time.time() - start_time)

                successful = False

                waited_time = 0

                while True:
                    if failure_type and failure_type in self.notifications:
                        #print(f"Recieved failure notification: waited: {waited_time} {failure_type}")
                        del self.notifications[failure_type]
                        sucesssful = True
                        break
                    if success_type and success_type in self.notifications:
                        successful = True
                        #print(f"Received success notification: waited: {waited_time} {success_type} ")
                        del self.notifications[success_type]
                        break
                    elapsed_time = (time.time() - start_time)
                    if elapsed_time >= timeout:
                        raise TimeoutError(f"Websocket waiting for notification {call_name} successType:{success_type} failureType:{failure_type} failed with a timeout! slept: {waited_time} ")
                    wait_left = timeout - elapsed_time
                    waited_time = self.wait_for_result(wait_left)

                if successful:
                    continue
                else:
                    break

            # TODO: Something causes this to not yield after the block for most of the calls, which messes up the response time tracking for most of the calls
            # We need some of these calls to loop indefinitely (ReportCapacity)
            while True:
                with common.manual_report(call.get('name')):
                        if call_name == "keep game alive":
                            #Sleep before we ping again
                            gevent.sleep(10)
                        RUNNING[self] = {'timeout': timeout, 'start-time': time.time()}
                        # Do variable replacement in the request body
                        body_json = call.get('body')
                        body = self.stringize_element(body_json, script_vars)
                        headers = self.listize_element(call.get('headers') | self.ws_headers, script_vars)


                        if "type" in body_json:
                            call_type = f"{call_name} : {body_json['type']}"

                        ws_url = f"{self.host}/{call.get('uri')}"

                        self.send(body, call_type)

                        elapsed_time = (time.time() - start_time)
                        waited_time = self.wait_for_result(timeout)

                        if call.get('return'):
                            for property in call.get('return'):
                                path = call.get('return').get(property)
                                return_value = self.get_return_value(self.my_value, path)
                                script_vars[property] = return_value

                        if (elapsed_time >= timeout) and not self.my_value:
                            raise TimeoutError(f"Websocket call {call.get('name')} failed with a timeout!")
                        
                        if call_name == "end game":
                            #Clean up after the match is done
                            self.players = []
                            self.game_instance_id = 0
                        
                        if call_name == "report capacity":
                            #Check to see if we got a gameInstanceId, otherwise continue to loop
                            try:
                                game_instance_ids = self.my_value['response']['payload']['gameInstanceIds']
                            #This is to catch an odd issue where we saw a KeyError indicating that payload contained no gameInstanceIds
                            except KeyError:
                                print(self.my_value)
                                raise
                            if game_instance_ids:
                                self.game_instance_id = game_instance_ids[0]
                                script_vars["gameInstanceId"] = self.game_instance_id
                                break
                            else:
                                gevent.sleep(1)
                        else: 
                            if repeat > 0:
                                repeat -= 1
                            else:
                                break
    
    def on_message(self, message):
        super().on_message(message) # handle in the User first
        message = json.loads(message)
        name = self.get_name_from_json(message)
        if self.show_responses:
            print(f"Response from server {self.server_id} script call {name} : ")
            print(json.dumps(message, indent=4))
        self.process_message_by_type(name, message)
        if message.get("response"):
            self.my_value = message
        if message.get("notification"):
            self.notifications[name] = message
        self.last_received = time.time()
        self.notify_result.set()
