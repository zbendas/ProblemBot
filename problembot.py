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


def handle_command(slack_command, slack_user, slack_channel, item_timestamp):
    response = "Couldn't understand you. No problem posted. Please try again or send `!problem help` for tips."
    # Play with this regex here: https://regex101.com/r/3UZNxU/2
    to_be_posted = regex.search(r"(?:^post +)((?:\"|')(.*)(?:\"|'))", slack_command, regex.IGNORECASE)
    deny_command = regex.search(r"(?:^deny)\w*?", slack_command, regex.IGNORECASE)
    allow_command = regex.search(r"(?:^allow)\w*?", slack_command, regex.IGNORECASE)
    help_command = regex.search(r"(?:^help)", slack_command, regex.IGNORECASE)
    # Easy and tangible reaction to acknowledge that a problem has been seen by the bot
    slack_client.api_call("reactions.add", name="rotating_light", channel=slack_channel, timestamp=item_timestamp)
    slack_client.api_call("reactions.add", name="question", channel=slack_channel, timestamp=item_timestamp)
    # Create pending dict after acknowledge, so that parsed messages are traceable, even when they're mistakes.
    pending = {"channel": slack_channel, "timestamp": item_timestamp, "text": to_be_posted.group(2)}
    if pending["text"]:
        if slack_channel == ADMIN_CHANNEL:
            # Admin requests are automatically approved
            prepend = "Posting the following:\n```" + pending["text"] + "```"
            slack_client.api_call("channels.setTopic", channel=USER_CHANNEL, text=pending["text"])
            # Notify admin channel that problem was posted
            slack_client.api_call("chat.postMessage", channel=ADMIN_CHANNEL, text=prepend)
        else:
            prepend = "<@" + slack_user + "> has requested that the following problem be posted:\n```" + \
                      pending["text"] + "```\n\n`Allow` or `Deny?`"
            slack_client.api_call("chat.postMessage", channel=ADMIN_CHANNEL, text=prepend, as_user=True)
    elif allow_command and slack_channel == ADMIN_CHANNEL:
        # Problem will be posted
        approval = "Problem posted."
        slack_client.api_call("chat.postMessage", channel=ADMIN_CHANNEL, text=approval, as_user=True)
        # Set the topic in the user channel
        slack_client.api_call("channels.setTopic", channel=USER_CHANNEL, topic=pending["text"])
        # Go back to the problem and remove its :question:
        slack_client.api_call("reactions.remove", name="question",
                              channel=pending["channel"], timestamp=pending["timestamp"])
        slack_client.api_call("reactions.add", name="ok", channel=pending["channel"], timestamp=pending["timestamp"])
    elif deny_command and slack_channel == ADMIN_CHANNEL:
        # Problem won't be posted
        denial = "Problem will not be posted."
        slack_client.api_call("chat.postMessage", channel=ADMIN_CHANNEL, text=denial, as_user=True)
        # Go back to the problem and remove its :question:
        slack_client.api_call("reactions.remove", name="question",
                              channel=pending["channel"], timestamp=pending["timestamp"])
        slack_client.api_call("reactions.add", name="no_entry_sign",
                              channel=pending["channel"], timestamp=pending["timestamp"])
    elif help_command:
        response = "These are the commands available:\n" \
                   "`help`: Posts this help.\n" \
                   "`!problem \"...\"`: Submits a problem posting for approval.\n"
        if slack_channel == ADMIN_CHANNEL:
            response += "\nAdmin-only commands:\n" \
                        "`allow`: Approves problem to be posted to the users' channel.\n" \
                        "`deny`: Denies a problem being posted to the users' channel."
        slack_client.api_call("chat.postMessage", channel=slack_channel, text=response, as_user=True)
    else:
        slack_client.api_call("chat.postMessage", channel=slack_channel, text=response, as_user=True)


def parse_slack_output(slack_rtm_output):
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and output['text'].startswith('!problem') and output['user'] != BOT_ID:
                return output['text'].split("!problem")[1].strip(), output['user'], output['channel'], output['ts']
            elif output and 'text' in output and output['text'].startswith(AT_BOT) and output['user'] != BOT_ID:
                return output['text'].split(AT_BOT)[1].strip(), output['user'], output['channel'], output['ts']
    return None, None, None, None

if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1  # 1 second firehose delay
    if slack_client.rtm_connect():
        print("Problem-Bot connected and running!")
        while True:
            command, user, channel, timestamp = parse_slack_output(slack_client.rtm_read())
            if command and user and channel:
                handle_command(command, user, channel, timestamp)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed! Check API key and Bot ID!")
