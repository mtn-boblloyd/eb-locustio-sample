import argparse
import os
import ujson as json
from types import SimpleNamespace
from pragma_operator import PragmaOperator
from pragma import Pragma

USERS = []

parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="http://localhost:11200", help="URL to the Pragma service to run against, should be the operator HTTP endpoint")
parser.add_argument("--player-host", type=str, default="http://localhost:11000", help="URL to the Pragma service to run against, should be the operator HTTP endpoint")
parser.add_argument("--number", type=int, help="Number of users to create.")
parser.add_argument("--user-id-prefix", type=str, default="test_user_", help="Prefix for username of created accounts. (default: test_user_)")
parser.add_argument("--starting-id", type=int, default=0, help="Starting id for created accounts to increment up from. (default: 0)")
parser.add_argument("--force-create", type=bool, default=False, help="Re-create the user even if they already exist")
args = parser.parse_args()

OPERATOR = PragmaOperator(host=args.host)

LOAD_TEST_GROUP_NAME = "loadtest"
LOAD_TEST_GROUP_DESC = "group for loadtest users"

operator_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {OPERATOR.social_token}"
}

uri = "v1/rpc"
player_social_token = None

def pragma_req(body, override_headers=None):
    req_headers = override_headers
    if not req_headers:
        req_headers = operator_headers
    response = Pragma(args.host).call(uri=uri, body=body, headers=req_headers)
    json_response = json.loads(response.text)
    return json_response

def deep_get(dct, dotted_path, default=None):
    for key in dotted_path.split('.'):
        try:
            dct = dct[key]
        except KeyError:
            return default
    return dct

def get_social_ids(user_ids, player_identities_map):
    social_ids = []
    missing_accounts = []

    for user_id in user_ids:
        existing_user = player_identities_map.get(user_id)
        social_id = None

        if existing_user:
            social_id = existing_user["pragmaSocialId"]

        if social_id:
            social_ids.append(social_id)
        else:
            missing_accounts.append(user_id)
    return (social_ids, missing_accounts)

class PragmaPlayerSession:

    def __init__(self):
        self.player_social_token = None
        self.player_session_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def set_social_token(self, social_token):
        self.player_social_token = social_token
        self.player_session_headers["Authorization"] = f"Bearer {self.player_social_token}"

    def get_load_test_users_social_ids(self, user_ids):
        if not self.player_social_token:
            login_test01_player_req = {"providerId":1, 
            "providerToken": "{\"accountId\":\"test01\",\"displayName\":\"test01\"}",
            "gameShardId":"00000000-0000-0000-0000-000000000001"}

            response = Pragma(args.player_host).call(uri="v1/account/authenticateorcreatev2", body=login_test01_player_req, headers=self.player_session_headers)
            json_response = json.loads(response.text)

            player_social_token = deep_get(json_response,"pragmaTokens.pragmaSocialToken")
            self.set_social_token(player_social_token)

        provider_queries = [
            {
                "idProviderType": 1,
                "providerAccountId": user_id
            }
            for user_id in user_ids
        ]

        get_social_ids_req = {
            "requestId": 1,
            "type": "AccountRpc.GetPragmaPlayerIdsForProviderIdsV2Request",
            "payload": {
                "gameShardId": "00000000-0000-0000-0000-000000000001",
                "providerAccountIds": provider_queries
            }
        }

        response = Pragma(args.player_host).call(uri=uri, body=get_social_ids_req, headers=self.player_session_headers)
        json_response = json.loads(response.text)

        player_identities = deep_get(json_response,"response.payload.playerIdentities")

        if player_identities is None:
            return None
        entry = player_identities[0]

        player_identities_map = {element["idProviderAccounts"][0]["accountId"]:element for element in player_identities}

        return player_identities_map

user_ids = [f"{args.user_id_prefix}{i}" for i in range(args.starting_id, args.starting_id + args.number)]

player_session = PragmaPlayerSession()

player_identities_map = player_session.get_load_test_users_social_ids(user_ids)

if args.force_create or player_identities_map is None:
    missing_accounts = user_ids
    social_ids = []
else:
    social_ids, missing_accounts = get_social_ids(user_ids, player_identities_map)

if missing_accounts:
        for account_id in missing_accounts:
            create_account_req = {
                "requestId": 1,
                "type": "AccountRpc.CreateAccountWithUnsafeProviderV2Request",
                "payload": {
                    "newAccounts": [
                        {
                            "id": account_id,
                            "displayName": account_id
                        },
                    ],
                    "gameShardId": "00000000-0000-0000-0000-000000000001"
                }
            }
            json_response = pragma_req(create_account_req)
        player_identities_map = player_session.get_load_test_users_social_ids(user_ids)
        social_ids, missing_accounts = get_social_ids(user_ids, player_identities_map)

if len(player_identities_map) != len(user_ids):
    print(f"unmatched # of accounts {len(player_identities_map)} from requested {len(user_ids)}")

# Now add the users to the group
get_groups_req = {
    "requestId": 1,
    "type": "AccountRpc.ViewPlayerGroupsOperatorV1Request",
    "payload": {}
}
json_response = pragma_req(get_groups_req)

groups = deep_get(json_response,"response.payload.playerGroups")

group_id = ""

group = next((item for item in groups if item["name"] == LOAD_TEST_GROUP_NAME), None)

if group:
    group_id = group["playerGroupId"]
elif not group:
    add_group_req = {
        "requestId": 1,
        "type": "AccountRpc.CreatePlayerGroupOperatorV1Request",
        "payload": {
            "name": LOAD_TEST_GROUP_NAME,
            "description": LOAD_TEST_GROUP_DESC 
        }
    }
    json_response = pragma_req(add_group_req)
    group_id = deep_get(json_response,"response.payload.playerGroup.playerGroupId")

if not group_id:
    print("No group id! Failed to add accounts to group")
if group_id:
    add_users_to_group_req = {
        "requestId": 1,
        "type": "AccountRpc.AddAccountsToPlayerGroupOperatorV1Request",
        "payload": {
            "playerGroupId": group_id,
            "pragmaSocialIds": social_ids
        }
    }
    json_response = pragma_req(add_users_to_group_req)
    print("Setup complete!")    

print("user setup complete!")
