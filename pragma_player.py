import random
import ujson as json
import common
import time
import base64
import gevent
import gevent.event
from common import USERS, RUNNING, INVITE_CODES, PARTY_ROLES, REGION_PINGS
from locust import User, task, between, events, tag
from pragma import Pragma
import pragma_operator
from websocket_client.pragma_websocket_user import PragmaWSUser
from locust_plugins.users.socketio import SocketIOUser

class PragmaGenericPlayer():
    def __init__(self):
        self.last_received = 0
        self.social_id = None
        self.invite_code = None
        self.party_role = "Solo"
        self.invite_count = 0
        # for some reason locust sometimes spawns too many users (may be a debug only issue)
        if len(USERS) > 0:
            self.social_id =USERS.pop()
        else:
            print(f'No ID available for Pragma Player! (skippping)')
        if len(PARTY_ROLES) > 0:
            self.party_role = PARTY_ROLES.pop()
            if self.party_role == "Host2":
                self.invite_count = 1
            if self.party_role == "Host3":
                self.invite_count = 2
            #print(f"{self.social_id} assigned role of {self.party_role}")
        if len(REGION_PINGS) > 0:
            self.region_ping = str(REGION_PINGS.pop())
        else:
            self.region_ping = str(50)
        self.headers = {
            # "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.social_token = None
    
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

class PragmaPlayer(User, PragmaGenericPlayer):
    wait_time = between(1,5)

    def __init__(self, environment):
        print("PragmaPlayer init")
        super().__init__(environment)
        self.host = environment.host
        self.script_vars = {"social_id": self.social_id}
        self.social_port = environment.parsed_options.social_port
        self.show_responses = environment.parsed_options.show_responses
    
    # @events.test_start.add_listener
    # def on_start(self):
    #     print(f"Logging in user : {self.social_id}")
    #     # print(self.social_id)
    #     uri = "v1/account/authenticateorcreatev2"
    #     data = {
    #         "providerId":1, 
    #         "providerToken": "{\"accountId\":\"" + self.social_id +"\",\"displayName\":\"" + self.social_id + "\"}",
    #         "gameShardId":"00000000-0000-0000-0000-000000000001"
    #     }
    #     response = Pragma(self.host).call(uri, data, self.headers)
    #     json_response = json.loads(response.text)
    #     self.social_token = json_response['pragmaTokens']['pragmaSocialToken']
    #     # print(f"User Social Token : {self.social_token}")
    #     self.headers["Authorization"] = f"Bearer {self.social_token}"

    # @task(2)
    def get_display_name(self):
        uri = "v1/rpc"
        data = {
            "requestId": 1,
            "type": "AccountRpc.GetDisplayNameForPragmaPlayerIdV1Request",
            "payload": {
                "pragmaPlayerId": self.social_id
            }
        }
        Pragma(self.host).call(uri, data, self.headers)

    @tag('load_test')
    @task
    def load_test_script(self):
        print(f"Running load test for user {self.social_id}")
        script = None
        with open('script.json', 'r') as file:
            script = json.load(file)
        
        self.call(script=script)


    @tag('smoke')
    @task
    def get_all(self):
        uri = "v1/rpc"
        data = {
            "requestId": 1,
            "type": "AccountRpc.GetPragmaAccountOverviewsOperatorV1Request",
            "payload": {
                "filter": {
                    "accountTagIds": [],
                    "excludedAccountTagIds": [],
                    "playerGroupIds": [],
                    "excludedPlayerGroupIds": [],
                    "idProviders": [],
                    "searchEmailVerified": "DISABLED",
                    "idProviderAccountId": "",
                    "pragmaSocialId": "",
                    "emailAddress": "",
                    "idProviderDisplayNameSearch": {
                        "idProvider": "UNUSED",
                        "fullDisplayName": ""
                    },
                    "pragmaFullDisplayName": ""
                }
            }
        }
        Pragma(self.host).call(uri, data, self.headers)
    
    def call(self, **kwargs):
        script = kwargs.get('script')

        for call in script.get('script'):
            if call.get('name') == "exit":
                print(f"Finished running this user {self.social_id}, so stop the greenlet")
                self.stop()
                break
                
            timeout = 10
            if call.get('acceptable-timeout'):
                timeout = int(call.get('acceptable-timeout'))
            with common.manual_report(call.get('name')):
                print(f"{self.social_id} - {call.get('name')}")
                RUNNING[self] = {'timeout': timeout, 'start-time': time.time()}
                # Do variable replacement in the request body
                str_body = json.dumps(call.get('body'))
                str_body = self.parse_script_line(str_body, self.script_vars)
                json_body = json.loads(str_body)

                # Do variable replacement in the headers
                str_headers = json.dumps(call.get('headers'))
                str_headers = self.parse_script_line(str_headers, self.script_vars)
                json_headers = json.loads(str_headers)
                
                host = self.host
                if call.get('port'):
                    if call.get('port') == "social":
                        port = self.social_port
                        provided_port = self.host.split(":")[-1]
                        host = self.host.replace(provided_port, port)
                # Start the timer, we should only wait the number of seconds in the script
                try:
                    response = Pragma(host).call(uri=call.get('uri'), body=json_body, headers=json_headers)
                    response_json = json.loads(response.text)
                    if response_json.get('serviceError'):
                        print(json.dumps(response_json, indent=4))
                        raise RuntimeError("Failed during Pragma call due to a service error.  Please check the response and make any corrections.")
                except RuntimeError as e:
                    print("Failed during Pragma call, removing process from execution.")
                    del RUNNING[self]
                    self.stop()
                    raise

                if self.show_responses:
                    print(f"Response from {self.social_id} script call {call.get('name')} : ")
                    print(json.dumps(response_json, indent=4))
                
                # Handle any requested return values in the script
                if call.get('return'):
                    for property in call.get('return'):
                        path = call.get('return').get(property)
                        return_value = self.get_return_value(response_json, path)
                        self.script_vars[property] = return_value
                del RUNNING[self]
    
class PragmaWSPlayer(PragmaWSUser, PragmaGenericPlayer):
    wait_time = between(1,5)

    def __init__(self, environment):
        self.connected = False
        self.provided_schema = environment.host.split("://")[0]
        self.provided_port = environment.host.split(":")[-1]
        self.login_schema = environment.parsed_options.login_schema
        self.http_port = environment.parsed_options.http_port
        self.show_responses = environment.parsed_options.show_responses
        self.mmr_test = environment.parsed_options.mmr_test
        self.matchmaking_script = environment.parsed_options.matchmaking_script
        self.is_disconnected = False
        if (environment.parsed_options.num_matches_min < environment.parsed_options.num_matches_max):
            self.num_matches = random.randrange(environment.parsed_options.num_matches_min, environment.parsed_options.num_matches_max)
        else:
            self.num_matches = environment.parsed_options.num_matches_min
        self.wait_between_matches_min = environment.parsed_options.wait_between_matches_min
        self.wait_between_matches_max = environment.parsed_options.wait_between_matches_max

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
        self.player_id = None
        self.notify_result = gevent.event.Event()
    
    def on_start(self):
        if not self.social_id:
            return
        #print(f"Logging in player {self.social_id}")
        uri = "v1/account/authenticateorcreatev2"
        data = {
            "providerId":1, 
            "providerToken": "{\"accountId\":\"" + self.social_id +"\",\"displayName\":\"" + self.social_id + "\"}",
            "gameShardId":"00000000-0000-0000-0000-000000000001"
        }
        host = self.host.replace(self.provided_schema, self.login_schema).replace(self.provided_port, self.http_port)
        response = Pragma(host).call(uri, data, self.http_headers)
        json_response = json.loads(response.text)
        print(f"Authenticated {self.social_id}")
        self.social_token = json_response['pragmaTokens']['pragmaSocialToken']
        self.game_token = json_response['pragmaTokens']['pragmaGameToken']
        if len(self.game_token):
            elements = self.game_token.split('.')
            game_data = json.loads(base64.b64decode(elements[1]+'=='))
            self.player_id = game_data["pragmaPlayerId"]

    def process_message_by_type(self, type, message_data):
        match type:
            case "GameDataRpc.GetLoginDataV2Response":
                ext_data = message_data["response"]["payload"]["loginData"]["ext"]
                crew_data = ext_data.get("crewData")
                if crew_data and "crewId" in crew_data:
                    self.crew_id = crew_data["crewId"]
            case "PartyRpc.CreateV1Response":
                if self.party_role != "Joiner":
                    payload_data = message_data["response"]["payload"]
                    party_data = payload_data.get("party")
                    if party_data and "inviteCode" in party_data:
                        self.invite_code = party_data["inviteCode"]
                        for i in range(self.invite_count):
                            INVITE_CODES.append(self.invite_code)

    @tag('load_test')
    @task
    def load_test_script(self):
        if not self.social_id:
            return
        script = None
        with open('websocket_script.json', 'r') as file:
            script = json.load(file)
        try:
            self.call(script=script)

            print(f"completed login: {self.social_id}")

            with open(self.matchmaking_script,'r') as file:
                script = json.load(file)

            for i in range(self.num_matches):
                self.call(script=script)
                if self.wait_between_matches_min < self.wait_between_matches_max:
                    self.sleep_with_heartbeat(random.randrange(self.wait_between_matches_min, self.wait_between_matches_max))
                else:
                    self.sleep_with_heartbeat(self.wait_between_matches_min)
            print(f"completed {self.num_matches} matches: {self.social_id}")
        finally:
            self.stop()
            if self in RUNNING:
                del RUNNING[self]

    def call(self, **kwargs):
        script = kwargs.get('script')
        script_vars = {"social_id": self.social_id, "playerGameToken": self.game_token, "player_id": self.player_id, "region_ping": self.region_ping}
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
            if call.get('roles'):
                if self.party_role not in call.get('roles'):
                    continue
            if call.get('acceptable-timeout'):
                timeout = int(call.get('acceptable-timeout'))

            if call_name == "exit":
                break
            if call_name == "add_player_to_matchmaking":
                pragma_operator.OPERATOR.add_player_to_match(None, self.player_id)
                continue
            if call_name == "join party":
                while True:
                    if len(INVITE_CODES) > 0:
                        #print("Received invite code")
                        script_vars["inviteCode"] = INVITE_CODES.pop()
                        break
                    else:
                        #print(f"No invite code. Code length is {len(INVITE_CODES)}")
                        self.sleep_with_heartbeat(5)
            if call_name == "wait":

                success_type = call.get("success")
                failure_type = call.get("failure")

                elapsed_time = (time.time() - start_time)

                successful = False

                waited_time = 0

                while True:
                    if failure_type and failure_type in self.notifications:
                        #print(f"Recieved failure notification: waited: {waited_time} {failure_type}")
                        #if failure_type == "GameInstanceRpc.GameInstanceStartFailureV1Notification":
                            #pragma_operator.OPERATOR.add_player_to_match(None, self.player_id)
                        del self.notifications[failure_type]
                        sucesssful = True
                        break
                    if success_type and success_type in self.notifications:
                        successful = True
                        #print(f"Received success notification: waited: {waited_time} {success_type} ")
                        if success_type == "GameInstanceRpc.AddedToGameV1Notification":
                            notification = self.notifications[success_type]
                            game_instance_id = notification["notification"]["payload"]["gameInstanceId"]
                            if self.mmr_test:
                                print(f"Received AddedToGameV1Notification for {self.social_id} after waiting for {time.time() - start_time}")
                            #pragma_operator.OPERATOR.add_player_to_match(game_instance_id, self.player_id)
                        elif success_type == "PartyRpc.PartyDetailsV1Notification":
                            notification = self.notifications[success_type]
                            partyMembers = notification["notification"]["payload"]["party"]["partyMembers"]
                            #print(f"Party notification received. Current member count: {len(partyMembers)}")
                            if len(partyMembers) <= self.invite_count:
                                del self.notifications[success_type]
                                continue
                            #else:
                                #print("Party full. Continuing.")
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
            with common.manual_report(call.get('name')):
                RUNNING[self] = {'timeout': timeout, 'start-time': time.time()}
                # Do variable replacement in the request body
                body_json = call.get('body')
                body = self.stringize_element(body_json, script_vars)
                headers = self.listize_element(call.get('headers') | self.ws_headers, script_vars)


                if "type" in body_json:
                    call_name = f"{call_name} : {body_json['type']}"

                ws_url = f"{self.host}/{call.get('uri')}"

                self.send(body, call_name)

                elapsed_time = (time.time() - start_time)
                waited_time = self.wait_for_result(timeout)

                if call.get('return'):
                    for property in call.get('return'):
                        path = call.get('return').get(property)
                        return_value = self.get_return_value(self.my_value, path)
                        script_vars[property] = return_value

                if (elapsed_time >= timeout) and not self.my_value:
                    raise TimeoutError(f"Websocket call {call.get('name')} failed with a timeout!")
    
    def on_message(self, message):
        super().on_message(message) # handle in the User first
        if message is None:
            self.last_received = time.time()
            self.my_value = message
            self.is_disconnected = True
            self.notify_result.set()
            return
        message = json.loads(message)
        name = self.get_name_from_json(message)
        if self.show_responses:
            print(f"Response from {self.social_id} script call {name} : ")
            print(json.dumps(message, indent=4))
        self.process_message_by_type(name, message)
        if message.get("response"):
            self.my_value = message
        if message.get("notification"):
            self.notifications[name] = message
        self.last_received = time.time()
        self.notify_result.set()

