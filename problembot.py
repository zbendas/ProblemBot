import json
import re as regex
from slackclient import SlackClient

with open("settings.json") as settings_file:
    settings = json.loads(settings_file)

# Establish settings
BOT_ID = settings["bot_id"]
API_KEY = settings["api"]

# Constants
AT_BOT = "<@" + BOT_ID + ">"

# Instantiate client
slack_client = SlackClient(API_KEY)
