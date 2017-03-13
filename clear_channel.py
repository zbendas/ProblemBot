import json
from slackclient import SlackClient

with open("settings.json") as settings_file:
    settings = json.loads(settings_file.read())

BOT_ID = settings["bot_id"]
API_KEY = settings["api"]
GENERAL_CHANNEL = settings["general_channel"]
USER_CHANNELS = settings["user_channels"]
ADMIN_CHANNELS = settings["admin_channels"]


slack_client = SlackClient(API_KEY)

if __name__ == "__main__":
    if input("Clear all bot messages from channels? ") == "y":
        print("Deleting user channel messages.")
        for USER_CHANNEL in USER_CHANNELS:
            history = slack_client.api_call("channels.history", channel=USER_CHANNEL)
            for item in history["messages"]:
                if item["type"] == "message":
                    if ("username" in item and item["username"] == "bot")\
                            or ("user" in item and item["user"] == BOT_ID):
                        slack_client.api_call("chat.delete", channel=USER_CHANNEL, ts=item["ts"])
        print("Deleting admin channel messages.")
        for ADMIN_CHANNEL in ADMIN_CHANNELS:
            history = slack_client.api_call("channels.history", channel=ADMIN_CHANNEL)
            for item in history["messages"]:
                if item["type"] == "message":
                    if ("username" in item and item["username"] == "bot")\
                            or ("user" in item and item["user"] == BOT_ID):
                        slack_client.api_call("chat.delete", channel=ADMIN_CHANNEL, ts=item["ts"])
        print("Deleting general channel messages.")
        history = slack_client.api_call("channels.history", channel=GENERAL_CHANNEL)
        for item in history["messages"]:
            if item["type"] == "message":
                if ("username" in item and item["username"] == "bot") or ("user" in item and item["user"] == BOT_ID):
                    slack_client.api_call("chat.delete", channel=GENERAL_CHANNEL, ts=item["ts"])
    else:
        print("Aborting.")
