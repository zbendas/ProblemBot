import json
import time
import re as regex
from slackclient import SlackClient

with open("settings.json") as settings_file:
    settings = json.loads(settings_file.read())

# Establish settings
BOT_ID = settings["bot_id"]
API_KEY = settings["api"]
USER_CHANNEL = settings["user_channel"]
ADMIN_CHANNEL = settings["admin_channel"]

# Constants
AT_BOT = "<@" + BOT_ID + ">"

# Instantiate client
slack_client = SlackClient(API_KEY)


def handle_command(slack_command, slack_user, slack_channel):
    response = "Couldn't understand you. No problem posted. Please try again or send `!problem help` for tips."
    slack_client.api_call("chat.postMessage", channel=slack_channel, text=response, as_user=True)


def parse_slack_output(slack_rtm_output):
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and output['text'].startswith('!problem') and output['user'] != BOT_ID:
                return output['text'].split("!problem")[1].strip(), output['user'], output['channel']
            elif output and 'text' in output and output['text'].startswith(AT_BOT) and output['user'] != BOT_ID:
                return output['text'].split(AT_BOT)[1].strip(), output['user'], output['channel']
    return None, None, None

if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1  # 1 second firehose delay
    if slack_client.rtm_connect():
        print("Problem-Bot connected and running!")
        while True:
            command, user, channel = parse_slack_output(slack_client.rtm_read())
            if command and user and channel:
                handle_command(command, user, channel)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed! Check API key and Bot ID!")
