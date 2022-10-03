
from birdy.twitter import UserClient
import twittertokens

use_aeroplanes_api=False

client = UserClient(twittertokens.CONSUMER_KEY,twittertokens.CONSUMER_SECRET,
                    twittertokens.ACCESS_TOKEN,twittertokens.ACCESS_TOKEN_SECRET)

def tweet(text):
    response=''
    try:
        response = client.api.statuses.update.post(status=text)
    except Exception as e:
        print(e)
        print("failed to tweet : retry\n")
        try:
            response = client.api.statuses.update.post(status=text)
            print("tweet retry ok\n")
        except Exception as e:
            print(e)
            print("failed to tweet a second time\n")
    return response
