import ujson as json
import random
import uuid
import time
from pragma import Pragma

PLAYERS_PER_MATCH = 6
MATCHES_IN_PROGRESS = {}

OPERATOR = None

class PragmaOperator:

    def __init__(self, **kwargs):
        global OPERATOR
        OPERATOR = self
        self.game_token = None
        self.social_token = None
        self.host = kwargs.get("host")
        self.partner_host = kwargs.get("partner_host")
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}
        self.authenticateorcreatev2 = "v1/account/authenticateorcreatev2"
        self.rpc = "v1/rpc"
        self.authenticate()
        self.end_game_count = 1

    def authenticate(self):
        data = {"providerId":1, 
                "providerToken": "{\"accountId\":\"test01\",\"displayName\":\"test01\"}",
                "gameShardId":"00000000-0000-0000-0000-000000000001"}
        response = Pragma(self.host).call(self.authenticateorcreatev2, data, self.headers)
        
        json_response = json.loads(response.text)
        self.game_token = json_response['pragmaTokens']['pragmaGameToken']
        self.social_token = json_response['pragmaTokens']['pragmaSocialToken']

    def authenticate_partner(self):
        data = {
            "requestId": 1,
            "type": "AccountRpc.CreatePartnerTokenV1Request",
            "payload": {
                "gameShardId": "00000000-0000-0000-0000-000000000001"
            }
        }
        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {self.social_token}"
        response = Pragma(self.host).call(self.rpc, data, headers)
        json_response = json.loads(response.text)
        self.partner_game_token = json_response["response"]["payload"]["pragmaPartnerGameToken"]

    def add_player_to_match(self, game_instance_id, player_id):
        in_progress = MATCHES_IN_PROGRESS.get(game_instance_id)
        if not in_progress:
            in_progress = MATCHES_IN_PROGRESS[game_instance_id] = [player_id]
            return
        in_progress.append(player_id)
        if len(in_progress) < PLAYERS_PER_MATCH:
            return
        del MATCHES_IN_PROGRESS[game_instance_id]
        self.send_end_game(game_instance_id, in_progress)

    def send_end_game(self, game_instance_id, player_ids):
        if game_instance_id == None:
            game_instance_id = str(uuid.uuid4())
        player_game_results = []
        end_game_data = {
            "requestId": 1,
            "type": "GameInstanceRpc.EndGameV1Request",
            "payload": {
                "gameInstanceId" : game_instance_id,
                "playerGameResults": player_game_results
            }
        }
        for player_id in player_ids:
            player_xp = random.randrange(10,100)
            player_headshots = random.randrange(0,5)
            player_game_result = {
                "playerId": player_id,
                "ext": {
                    "events": {
                        "playerstat.headshots": player_headshots,
                        "playerstat.xp": player_xp
                    }
                }
            }
            player_game_results.append(player_game_result)
        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {self.partner_game_token}"
        start_time = time.time()
        response = Pragma(self.partner_host).call(self.rpc, end_game_data, headers)
        json_response = json.loads(response.text)
        # TODO: track properly with locust stats
        print(f"sent end game for {game_instance_id} : response time: {(time.time() - start_time)/1000}s")
        self.end_game_count +=1

def __main__(*args):
    PragmaOperator().authenticate()

if __name__ == "__main__":
    __main__()
