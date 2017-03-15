import json
import time
import random
import datetime as dt
import re as regex
from slackclient import SlackClient

with open("settings.json") as settings_file:
    settings = json.loads(settings_file.read())

# Establish settings
BOT_ID = settings["bot_id"]
API_KEY = settings["api"]
GENERAL_CHANNEL = settings["general_channel"]
USER_CHANNELS = settings["user_channels"]
USER_GROUPS = settings["user_groups"]
ADMIN_CHANNELS = settings["admin_channels"]
ADMIN_GROUPS = settings["admin_groups"]

# Constants
AT_BOT = "<@" + BOT_ID + ">"
ALL_CLEAR = ["No issues!", "Nothing going on!", "No problems!", "Nothing's broken!", "Not much happening today!"]

# Instantiate client
slack_client = SlackClient(API_KEY)

# Instantiate working variable
working = {"dirty": False, "channel": "", "timestamp": "", "text": ""}
list_of_messages = []


class Message:
    def __init__(self, chnnl, tmstmp, txt):
        self.channel, self.timestamp, self.text = chnnl, tmstmp, txt
        self.dirty = False

    def __str__(self):
        return "Channel: " + self.channel + ", TS: " + self.timestamp + ", Text: " + self.text


def post_to_general(pending=working):
    prepend = ":rotating_light::rotating_light::rotating_light:\n" \
              "The University is currently experiencing the following issue:\n```" + pending["text"] + "```"
    api_result = slack_client.api_call("chat.postMessage", channel=GENERAL_CHANNEL, text=prepend, as_user=True)
    message = Message(api_result["channel"], api_result["ts"], pending["text"])
    list_of_messages.append(message)
    slack_client.api_call("pins.add", channel=GENERAL_CHANNEL, timestamp=api_result["ts"])
    return


def handle_command(slack_command, slack_user, slack_channel, item_timestamp, pending=working):
    response = "Couldn't understand you. No problem posted. Please try again or send `!problem help` for tips."
    # Play with this regex here: https://regex101.com/r/3UZNxU/3
    to_be_posted = regex.search(r"(?:^post +)((?:\"|')(.*)(?:\"|')) *"
                                r"((?:<#)(\w*)(?:\|(\w*)>))?", slack_command, regex.IGNORECASE)
    allow_command = regex.search(r"(?:^allow)", slack_command, regex.IGNORECASE)
    deny_command = regex.search(r"(?:^deny) *((?:\")(.*)(?:\"))?", slack_command, regex.IGNORECASE)
    close_command = regex.search(r"(?:^close +)(\d+)", slack_command, regex.IGNORECASE)
    update_command = regex.search(r"(?:^update +)(\d) +((?:\"|')(.*)(?:\"|'))", slack_command, regex.IGNORECASE)
    list_command = regex.search(r"(?:^list)", slack_command, regex.IGNORECASE)
    help_command = regex.search(r"(?:^help)", slack_command, regex.IGNORECASE)
    # Easy and tangible reaction to acknowledge that a problem has been seen by the bot
    slack_client.api_call("reactions.add", name="rotating_light", channel=slack_channel, timestamp=item_timestamp)
    if not pending["dirty"]:
        pending["channel"], pending["timestamp"] = slack_channel, item_timestamp
        if to_be_posted:
            pending["dirty"] = True
            try:
                pending["text"] = to_be_posted.group(2)
            except AttributeError:
                print("No regex match found! Something may be wrong!")
                pending["text"], pending["dirty"] = "", False
    # Post a problem
    if to_be_posted:
        if (slack_channel in ADMIN_CHANNELS) or (slack_channel in ADMIN_GROUPS):
            # Admin requests are automatically approved
            prepend = "Posting the following:\n```" + pending["text"] + "```"
            for USER_CHANNEL in USER_CHANNELS:
                slack_client.api_call("channels.setTopic", channel=USER_CHANNEL,
                                      topic=(":rotating_light: " + pending["text"] + " :rotating_light:"))
            for USER_GROUP in USER_GROUPS:
                slack_client.api_call("groups.setTopic", channel=USER_GROUP,
                                      topic=(":rotating_light: " + pending["text"] + " :rotating_light:"))
            # Notify admin channel that problem was posted
            for ADMIN_CHANNEL in ADMIN_CHANNELS:
                slack_client.api_call("chat.postMessage", channel=ADMIN_CHANNEL, text=prepend, as_user=True)
            for ADMIN_GROUP in ADMIN_GROUPS:
                slack_client.api_call("chat.postMessage", channel=ADMIN_GROUP, text=prepend, as_user=True)
            slack_client.api_call("reactions.add", name="ok",
                                  channel=pending["channel"], timestamp=pending["timestamp"])
            post_to_general()
            pending["dirty"] = False
        else:
            slack_client.api_call("reactions.add", name="question", channel=pending["channel"],
                                  timestamp=pending["timestamp"])
            prepend = "<@" + slack_user + "> has requested that the following problem be posted:\n```" + \
                      pending["text"] + "```\n\n`Allow` or `Deny`?"
            try:
                target_group = to_be_posted.group(4)
            except AttributeError:
                # No targeted group
                target_group = None
            # Makes sure that the targeted group is an admin channel. If not, this will post in all admin channels.
            if target_group and (target_group in ADMIN_CHANNELS):
                # Send message to target group
                slack_client.api_call("chat.postMessage", channel=target_group, text=prepend, as_user=True)
            else:
                for ADMIN_CHANNEL in ADMIN_CHANNELS:
                    slack_client.api_call("chat.postMessage", channel=ADMIN_CHANNEL, text=prepend, as_user=True)
                for ADMIN_GROUP in ADMIN_GROUPS:
                    slack_client.api_call("chat.postMessage", channel=ADMIN_GROUP, text=prepend, as_user=True)
    # Approve a posting
    elif allow_command and (slack_channel in ADMIN_CHANNELS or slack_channel in ADMIN_GROUPS):
        # Problem will be posted
        confirmation = "Problem has been posted."
        slack_client.api_call("chat.postMessage", channel=slack_channel, text=confirmation, as_user=True)
        approval = "The following problem has been posted in <#" + GENERAL_CHANNEL + ">:\n```" + pending["text"] + "```"
        for ADMIN_CHANNEL in ADMIN_CHANNELS:
            # Don't double up on sending confirmation/approval
            if ADMIN_CHANNEL != slack_channel:
                slack_client.api_call("chat.postMessage", channel=ADMIN_CHANNEL, text=approval, as_user=True)
        for ADMIN_GROUP in ADMIN_GROUPS:
            # Don't double up on sending confirmation/approval
            if ADMIN_GROUP != slack_channel:
                slack_client.api_call("chat.postMessage", channel=ADMIN_GROUP, text=approval, as_user=True)
        # Set the topic in the user channels
        for USER_CHANNEL in USER_CHANNELS:
            slack_client.api_call("channels.setTopic", channel=USER_CHANNEL,
                                  topic=":rotating_light: " + pending["text"] + " :rotating_light:")
        for USER_GROUP in USER_GROUPS:
            slack_client.api_call("groups.setTopic", channel=USER_GROUP,
                                  topic=":rotating_light: " + pending["text"] + " :rotating_light:")
        # Go back to the problem and remove its :question:
        slack_client.api_call("reactions.remove", name="question",
                              channel=pending["channel"], timestamp=pending["timestamp"])
        slack_client.api_call("reactions.add", name="ok", channel=pending["channel"], timestamp=pending["timestamp"])
        post_to_general()
        pending["dirty"] = False
    # Deny a posting
    elif deny_command and (slack_channel in ADMIN_CHANNELS or slack_channel in ADMIN_GROUPS):
        # Problem won't be posted
        denial = "Problem will not be posted."
        try:
            reason = deny_command.group(2)
        except AttributeError:
            reason = None
        prepend = "This posting:\n```" + pending["text"] + "```\nhas been rejected."
        if reason:
            prepend += "\nThis reason was given:\n```" + reason + "```\n"
        for ADMIN_CHANNEL in ADMIN_CHANNELS:
            slack_client.api_call("chat.postMessage", channel=ADMIN_CHANNEL, text=denial, as_user=True)
        for ADMIN_GROUP in ADMIN_GROUPS:
            slack_client.api_call("chat.postMessage", channel=ADMIN_GROUP, text=denial, as_user=True)
        # Go back to the problem and remove its :question:
        slack_client.api_call("reactions.remove", name="question",
                              channel=pending["channel"], timestamp=pending["timestamp"])
        slack_client.api_call("reactions.add", name="no_entry_sign",
                              channel=pending["channel"], timestamp=pending["timestamp"])
        slack_client.api_call("chat.postMessage", channel=pending["channel"], text=prepend, as_user=True)
        pending["dirty"] = False
    # List open postings
    elif list_command and (slack_channel in ADMIN_CHANNELS or slack_channel in ADMIN_GROUPS):
        # List currently posted problems
        prepend = "Currently, these issues are posted:\n```"
        counter = 1
        if len(list_of_messages) > 0:
            for message in list_of_messages:
                prepend += str(counter) + ")\t" + message.text + "\t" + \
                           dt.datetime.fromtimestamp(float(message.timestamp)).strftime('%H:%M %p, %m-%d-%Y') + "\n"
                counter += 1
        else:
            prepend += "No pending issues."
        prepend += "```"
        # Send this list only to the channel requesting it
        slack_client.api_call("chat.postMessage", channel=slack_channel, text=prepend, as_user=True)
    # Close a posting
    elif close_command and (slack_channel in ADMIN_CHANNELS or slack_channel in ADMIN_GROUPS):
        index_to_close = None
        try:
            index_to_close = close_command.group(1)
        except AttributeError:
            print("Nothing to close.")
        if index_to_close:
            response = "Problem #" + index_to_close + " closed."
            to_close = list_of_messages[int(index_to_close) - 1]  # -1 adjust for human indexing
            # Un-pin from channel
            unpinned = slack_client.api_call("pins.remove", channel=to_close.channel, timestamp=to_close.timestamp)
            # If the pin was not properly removed, do not continue. Alert the user.
            if unpinned["ok"]:
                # Thread closing message
                slack_client.api_call("chat.postMessage", channel=to_close.channel,
                                      thread_ts=to_close.timestamp, reply_broadcast=True,
                                      text="This problem has been closed.", as_user=True)
                del list_of_messages[int(index_to_close) - 1]
                # If there are still problems, update the topic of the user channel
                if len(list_of_messages) > 0:
                    for USER_CHANNEL in USER_CHANNELS:
                        slack_client.api_call("channels.setTopic", channel=USER_CHANNEL,
                                              topic=":rotating_light: " + list_of_messages[-1].text +
                                                    " :rotating_light:")
                    for USER_GROUP in USER_GROUPS:
                        slack_client.api_call("groups.setTopic", channel=USER_GROUP,
                                              topic=":rotating_light: " + list_of_messages[-1].text +
                                                    " :rotating_light:")
                elif len(list_of_messages) == 0:
                    for USER_CHANNEL in USER_CHANNELS:
                        slack_client.api_call("channels.setTopic", channel=USER_CHANNEL,
                                              topic=random.choice(ALL_CLEAR))
                    for USER_GROUP in USER_GROUPS:
                        slack_client.api_call("groups.setTopic", channel=USER_GROUP,
                                              topic=random.choice(ALL_CLEAR))
                for ADMIN_CHANNEL in ADMIN_CHANNELS:
                    slack_client.api_call("chat.postMessage", channel=ADMIN_CHANNEL, text=response, as_user=True)
            else:
                slack_client.api_call("chat.postMessage", channel=slack_channel,
                                      text="This problem could not be closed. Please try again in a moment.",
                                      as_user=True)
    # Update a posting
    elif update_command and (slack_channel in ADMIN_CHANNELS or slack_channel in ADMIN_GROUPS):
        index_to_update = None
        update_text = None
        try:
            index_to_update = update_command.group(1)
        except AttributeError:
            print("Nothing to update.")
        try:
            update_text = update_command.group(3)
        except AttributeError:
            print("No update text given.")
        if index_to_update and update_text:
            response = "Problem #" + index_to_update + " updated with:\n```" + update_text + "```"
            to_update = list_of_messages[int(index_to_update) - 1]  # -1 to adjust for human indexing
            prepend = "The following update has been posted:\n```"
            prepend += update_command.group(3) + "```"
            # Thread the update message on
            slack_client.api_call("chat.postMessage", channel=to_update.channel,
                                  thread_ts=to_update.timestamp, reply_broadcast=True, text=prepend, as_user=True)
            # Notify sending channel of posting
            slack_client.api_call("chat.postMessage", channel=slack_channel, text=response, as_user=True)
    elif help_command:
        response = "Invoke any of these commands using `!problem` or `@problem-bot`:\n" \
                   "`help`: Posts this help.\n" \
                   "`post \"...\"`: Submits a problem posting for approval.\n" \
                   "`post \"...\" #channel`: Submits a problem to a specific channel for approval.\n"
        if slack_channel in ADMIN_CHANNELS:
            response += "\n*Admin-only commands:*\n" \
                        "`allow`: Approves problem to be posted to the users' channel.\n" \
                        "`deny`: Denies a problem being posted to the users' channel.\n" \
                        "`list`: Lists all pinned problems.\n" \
                        "`update # \"...\"`: Updates a problem with the specified text.\n" \
                        "`close #`: Closes problem according to its list number."
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
        print("Grabbing currently posted problems!")
        api_response = slack_client.api_call("pins.list", channel=GENERAL_CHANNEL)
        for item in reversed(api_response["items"]):
            if item["type"] == "message" and item["message"]["user"] == BOT_ID:
                text = regex.search(r"(?:```)(.*)(?:```)", item["message"]["text"], regex.IGNORECASE).group(1)
                list_of_messages.append(Message(GENERAL_CHANNEL, item["message"]["ts"], text))
        while True:
            command, user, channel, timestamp = parse_slack_output(slack_client.rtm_read())
            if command and user and channel:
                handle_command(command, user, channel, timestamp)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed! Check API key and Bot ID!")
