import json
import time
import logging
import random
import datetime as dt
import re as regex
from slackclient import SlackClient


logger = logging.getLogger(__name__)

console_logger = logging.StreamHandler()
console_logger.setLevel(logging.DEBUG)

console_formatter = logging.Formatter('%(asctime)s > %(levelname)s (%(name)s): \"%(message)s\"', "%H:%M:%S")
console_logger.setFormatter(console_formatter)

file_logger = logging.FileHandler("problembot.log")
file_logger.setLevel(logging.WARNING)

file_formatter = logging.Formatter('%(levelname)s (%(name)s): \"%(message)s\" at %(asctime)s')
file_logger.setFormatter(file_formatter)

logger.addHandler(console_logger)
logger.addHandler(file_logger)

try:
    with open("settings.json") as settings_file:
        settings = json.loads(settings_file.read())
except IOError or OSError:
    # File doesn't exist, create blank one instead
    logger.setLevel(logging.DEBUG)
    logger.warning("No settings file found! Loading empty settings!")
    settings = {}

if settings["logging_level"].upper() == "DEBUG":
    logger.setLevel(logging.DEBUG)
elif settings["logging_level"].upper() == "INFO":
    logger.setLevel(logging.INFO)
elif settings["logging_level"].upper() == "WARNING":
    logger.setLevel(logging.WARNING)
elif settings["logging_level"].upper() == "ERROR":
    logger.setLevel(logging.ERROR)
else:
    logger.setLevel(logging.WARNING)
    logger.warning("Logging level set incorrectly. Defaulting to WARNING. Please check your settings.json.")

if settings["modules"]["knowledgelinker"]:
    from modules import knowledgelinker
    if settings["module_settings"]["knowledgelinker"]["kb_word"] == "":
        settings["module_settings"]["knowledgelinker"]["kb_word"] = "kb"
if settings["modules"]["whenaway"]:
    from modules import whenaway
    destination_channel = None


def debuggable(func):
    def decorated_function(*original_args, **original_kwargs):
        logger.debug("Entering " + func.__name__)
        return_value = func(*original_args, **original_kwargs)
        logger.debug("Exiting " + func.__name__)
        return return_value
    return decorated_function


class Memoize:
    def __init__(self, func):
        self.__name__ = func.__name__
        self.func = func
        self.expire = dt.datetime.now() + dt.timedelta(hours=1)
        self.cache = {}

    def __call__(self, *args):
        if dt.datetime.now() > self.expire:
            # If cache is greater than an hour old, clear it to prevent stale responses, then reset expiry timer
            self.cache = {}
            self.expire = dt.datetime.now() + dt.timedelta(hours=1)
            logger.info("Clearing the function response cache for %s", self.func.__name__)
        try:
            return self.cache[args]
        except KeyError:
            self.cache[args] = self.func(*args)
            return self.cache[args]


# Establish settings
API_KEY = settings["api"]
BOT_ID = settings["bot_id"]
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
working = {"dirty": False, "channel": "", "timestamp": "", "text": "", "regex": None}
list_of_messages = []


class Message:
    def __init__(self, chnnl, tmstmp, txt):
        self.channel, self.timestamp, self.text = chnnl, tmstmp, txt
        self._dirty = None
        self.dirty = False

    def __str__(self):
        return "Channel: " + self.channel + ", TS: " + self.timestamp + ", Text: " + self.text

    @property
    def dirty(self):
        return self._dirty

    @dirty.setter
    def dirty(self, value):
        if value is not True and value is not False:
            raise TypeError("Argument must be boolean.")
        else:
            self._dirty = value

    @dirty.deleter
    def dirty(self):
        self._dirty = False


class Command(object):
    def __init__(self, mode, re):
        self._type = None
        self.type = mode
        self.regex = re

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        if value is None:
            self._type = None
            return
        passed_in = value.lower()
        if passed_in == "post":
            self._type = passed_in
        elif passed_in == "allow":
            self._type = passed_in
        elif passed_in == "deny":
            self._type = passed_in
        elif passed_in == "list":
            self._type = passed_in
        elif passed_in == "update":
            self._type = passed_in
        elif passed_in == "close":
            self._type = passed_in
        elif passed_in == "help":
            self._type = passed_in
        else:
            self._type = None

    @type.deleter
    def type(self):
        del self._type


def post_message(message, destination):
    return slack_client.api_call("chat.postMessage", channel=destination, text=message, as_user=True)


def post_rich_message(message, attachments, destination):
    return slack_client.api_call("chat.postMessage", channel=destination, text=message,
                                 attachments=attachments, as_user=True)


def post_to_general(pending=working):
    attachments = [
        {
            "fallback": pending["text"],
            "color": "#ff4f4f",
            "fields": [
                {
                    "title": "The University is experiencing the following issue:",
                    "value": pending["text"],
                    "short": False
                }
            ],
            "ts": pending["timestamp"]
        },
        {
            "fallback": "Divider",
            "text": "---------------"
        },
        {
            "fallback": "Additional information",
            "color": "#bf5700",
            "text": "For additional information, see <https://ut.service-now.com/utss/alertlist.do|ITS Alerts Page>"
        }
    ]
    api_result = post_rich_message("", attachments, GENERAL_CHANNEL)
    message = Message(api_result["channel"], api_result["ts"], pending["text"])
    list_of_messages.append(message)
    return pin(api_result["ts"], GENERAL_CHANNEL, "+")


def post_to_admin(message):
    for ADMIN_CHANNEL in ADMIN_CHANNELS:
        post_message(message, ADMIN_CHANNEL)
    for ADMIN_GROUP in ADMIN_GROUPS:
        post_message(message, ADMIN_GROUP)


def thread_reply(message, destination, thread_parent, broadcast=False):
    return slack_client.api_call("chat.postMessage", channel=destination, thread_ts=thread_parent,
                                 text=message, reply_broadcast=broadcast, as_user=True)


def react(emoji, destination, ts, flag):
    flag = flag.lower()
    if flag == "a" or flag == "+":
        return slack_client.api_call("reactions.add", name=emoji, channel=destination, timestamp=ts)
    elif flag == "r" or flag == "-":
        return slack_client.api_call("reactions.remove", name=emoji, channel=destination, timestamp=ts)
    else:
        raise ValueError("Flag argument can only be + or -")


def change_topic(topic, destination, flag):
    flag = flag.lower()
    if flag == "c":
        return slack_client.api_call("channels.setTopic", channel=destination, topic=topic)
    elif flag == "g":
        return slack_client.api_call("groups.setTopic", channel=destination, topic=topic)
    else:
        raise ValueError("Flag argument can be only c or g")


def set_user_topics(topic):
    for USER_CHANNEL in USER_CHANNELS:
        change_topic(":rotating_light: " + topic + " :rotating_light:", USER_CHANNEL, "c")
    for USER_GROUP in USER_GROUPS:
        change_topic(":rotating_light: " + topic + " :rotating_light:", USER_GROUP, "g")


def clear_user_topics():
    for USER_CHANNEL in USER_CHANNELS:
        change_topic(random.choice(ALL_CLEAR), USER_CHANNEL, "c")
    for USER_GROUP in USER_GROUPS:
        change_topic(random.choice(ALL_CLEAR), USER_GROUP, "g")


def pin(ts, destination, flag):
    flag = flag.lower()
    if flag == "a" or flag == "+":
        return slack_client.api_call("pins.add", channel=destination, timestamp=ts)
    elif flag == "r" or flag == "-":
        return slack_client.api_call("pins.remove", channel=destination, timestamp=ts)
    else:
        raise ValueError("Flag argument can be only + or -")


@debuggable
@Memoize
def find_group(group_name):
    groups = slack_client.api_call("groups.list", exclude_archived=True)["groups"]
    for group in groups:
        if group_name == group["name"]:
            return group["id"], group["name"]
    logger.warning("No group \"%s\" found!", group_name)
    return None, None


def parse_regex(in_text):
    # Play with this regex here: https://regex101.com/r/3UZNxU/6
    to_be_posted = regex.search(r"(?:^post +)((?:[\"'])(.*)(?:[\"'])) *"
                                r"((?:(?:<#)(\w*)(?:\|(\w*)>))|#(\S+))?", in_text, regex.IGNORECASE | regex.DOTALL)
    allow_command = regex.search(r"(?:^allow)", in_text, regex.IGNORECASE | regex.DOTALL)
    deny_command = regex.search(r"(?:^deny) *((?:[\"'])(.*)(?:[\"']))?", in_text, regex.IGNORECASE | regex.DOTALL)
    close_command = regex.search(r"(?:^close +)(\d+)", in_text, regex.IGNORECASE | regex.DOTALL)
    update_command = regex.search(r"(?:^update +)(\d) +((?:[\"'])(.*)(?:[\"']))", in_text,
                                  regex.IGNORECASE | regex.DOTALL)
    list_command = regex.search(r"(?:^list)", in_text, regex.IGNORECASE)
    help_command = regex.search(r"(?:^help)", in_text, regex.IGNORECASE)
    if to_be_posted:
        return Command("post", to_be_posted)
    elif allow_command:
        return Command("allow", allow_command)
    elif deny_command:
        return Command("deny", deny_command)
    elif close_command:
        return Command("close", close_command)
    elif update_command:
        return Command("update", update_command)
    elif list_command:
        return Command("list", list_command)
    elif help_command:
        return Command("help", help_command)
    else:
        logger.warning("Could not parse the following user input: " + in_text)
        return Command(None, regex.search("", ""))


@debuggable
def handle_command(slack_command, slack_user, slack_channel, item_timestamp, pending=working):
    response = "Couldn't understand you. No problem posted. Please try again or send `!problem help` for tips."
    # Parse user input
    # Regex objects can be accessed via command[0]
    command = parse_regex(slack_command)
    # Easy and tangible reaction to acknowledge that a problem has been seen by the bot
    react("rotating_light", slack_channel, item_timestamp, "+")
    # Determine whether or not message is coming from an admin
    in_admin = slack_channel in ADMIN_CHANNELS or slack_channel in ADMIN_GROUPS
    if not pending["dirty"]:
        pending["channel"], pending["timestamp"] = slack_channel, item_timestamp
        # If user is attempting to post problem
        if command.type == "post":
            pending["dirty"] = True
            try:
                pending["text"] = command.regex.group(2)
                pending["regex"] = command.regex
            except AttributeError:
                logger.warning("No regex match found! Something may be wrong!")
                pending["text"], pending["dirty"], pending["regex"] = "", False, None
    # Post a problem
    if command.type == "post":
        make_post(slack_user, in_admin, pending, command)
    # Approve a posting
    elif command.type == "allow" and in_admin:
        # Problem will be posted
        post_allow(pending, slack_channel)
    # Deny a posting
    elif command.type == "deny" and in_admin:
        # Problem won't be posted
        post_deny(command, pending)
    # List open postings
    elif command.type == "list" and in_admin:
        post_list(slack_channel)
    # Close a posting
    elif command.type == "close" and in_admin:
        post_close(command, slack_channel)
    # Update a posting
    elif command.type == "update" and in_admin:
        post_update(command, slack_channel)
    elif command.type == "help":
        post_help(slack_channel, in_admin)
    else:
        post_message(response, slack_channel)


@debuggable
def make_post(slack_user, in_admin, pending, command):
    if settings["modules"]["whenaway"]:
        global destination_channel
    if in_admin:
        # Admin requests are automatically approved
        prepend = "Posting the following:\n```" + pending["text"] + "```"
        # Change user topics
        set_user_topics(pending["text"])
        # Notify admin channel that problem was posted
        post_to_admin(prepend)
        react("ok", pending["channel"], pending["timestamp"], "+")
        post_to_general()
        pending["dirty"] = False
    else:
        react("question", pending["channel"], pending["timestamp"], "+")
        prepend = "<@" + slack_user + "> has requested that the following problem be posted:\n```" + \
                  pending["text"] + "```\n\n`Allow` or `Deny`?"
        try:
            target_channel = command.regex.group(4)
        except AttributeError:
            # No targeted channel
            logger.info("Post had no targeted channel.")
            target_channel = None
        try:
            target_group = command.regex.group(6)
        except AttributeError:
            # No target group
            logger.info("Post had no targeted group.")
            target_group = None
        # Makes sure that the targeted channel is an admin channel. If not, this will post in all admin channels.
        if target_channel and (target_channel in ADMIN_CHANNELS or target_channel in ADMIN_GROUPS):
            # Send message to target channel
            if settings["modules"]["whenaway"]:
                success, destination_channel = whenaway.post_if_present(prepend, target_channel)
            else:
                post_message(prepend, target_channel)
        elif target_group:
            target_id, target_group = find_group(target_group)
            if target_group and target_id and (target_id in ADMIN_CHANNELS or target_id in ADMIN_GROUPS):
                # Send message to target group
                if settings["modules"]["whenaway"]:
                    success, destination_channel = whenaway.post_if_present(prepend, target_id)
                else:
                    post_message(prepend, target_id)
            else:
                post_to_admin(prepend)
        else:
            post_to_admin(prepend)


@debuggable
def post_allow(pending, slack_channel):
    confirmation = "Problem has been posted."
    post_message(confirmation, slack_channel)
    approval = "The following problem has been posted in <#" + GENERAL_CHANNEL + ">:\n```" + pending["text"] + "```"
    for ADMIN_CHANNEL in ADMIN_CHANNELS:
        # Don't double up on sending confirmation/approval
        if ADMIN_CHANNEL != slack_channel:
            post_message(approval, ADMIN_CHANNEL)
    for ADMIN_GROUP in ADMIN_GROUPS:
        # Don't double up on sending confirmation/approval
        if ADMIN_GROUP != slack_channel:
            post_message(approval, ADMIN_GROUP)
    # Set the topic in user channels
    set_user_topics(pending["text"])
    # Go back to the problem and remove its :question:
    react("question", pending["channel"], pending["timestamp"], "-")
    react("ok", pending["channel"], pending["timestamp"], "+")
    post_to_general()
    pending["dirty"] = False


@debuggable
def post_deny(command, posting):
    denial = "Problem will not be posted."
    try:
        reason = command.regex.group(2)
    except AttributeError:
        reason = None
    prepend = "This posting:\n```" + posting["text"] + "```\n has been rejected."
    if reason:
        prepend += "\nThis reason was given:\n```" + reason + "```\n"
    if posting["regex"]:
        target_channel = posting["regex"].group(4)  # Find the channel this was targeted to
        target_group = find_group(posting["regex"].group(6))[0]  # Find the group this was targeted to
        logger.debug("Targeted channel/group: " + str(target_channel) + "/" + str(target_group))
        if settings["modules"]["whenaway"]:
            global destination_channel
            post_message(denial, destination_channel)
        else:
            if target_channel and (target_channel in ADMIN_CHANNELS):
                post_message(denial, target_channel)
            elif target_group and (target_group in ADMIN_GROUPS):
                post_message(denial, target_group)
            else:
                post_to_admin(denial)
    # Go back to problem and remove its :question:
    react("question", posting["channel"], posting["timestamp"], "-")
    react("no_entry_sign", posting["channel"], posting["timestamp"], "+")
    post_message(prepend, posting["channel"])
    posting["dirty"] = False


@debuggable
def post_list(slack_channel):
    # List currently posted problems
    prepend = ""
    counter = 1
    if len(list_of_messages) > 0:
        prepend = "Currently, these issues are posted:\n```"
        for message in list_of_messages:
            prepend += str(counter) + ")\t" + message.text + "\t" + \
                       dt.datetime.fromtimestamp(float(message.timestamp)).strftime('%H:%M %p, %m-%d-%Y') + "\n"
            counter += 1
        prepend += "```"
    else:
        prepend += "No pending issues."
    # Send this list only to the channel requesting it
    post_message(prepend, slack_channel)


@debuggable
def post_close(command, slack_channel):
    index_to_close = None
    try:
        index_to_close = command.regex.group(1)
    except AttributeError:
        logger.warning("Unable to find problem index to close. Command text: %s", command)
    if index_to_close:
        response = "Problem #" + index_to_close + " closed."
        to_close = list_of_messages[int(index_to_close) - 1]  # -1 adjust for human indexing
        # Un-pin from channel
        unpinned = pin(to_close.timestamp, to_close.channel, "-")
        # If the pin was not properly removed, do not continue. Alert the user.
        if unpinned["ok"]:
            # Thread closing message
            thread_reply("This problem has been closed.", to_close.channel, to_close.timestamp, broadcast=True)
            del list_of_messages[int(index_to_close) - 1]
            # If there are still problems, update the topic of the user channel
            if len(list_of_messages) > 0:
                set_user_topics(list_of_messages[-1].text)
            elif len(list_of_messages) == 0:
                clear_user_topics()
            post_to_admin(response)
        else:
            post_message("This problem could not be closed. Please try again in a moment.", slack_channel)


@debuggable
def post_update(command, slack_channel):
    index_to_update = None
    update_text = None
    try:
        index_to_update = command.regex.group(1)
    except AttributeError:
        logger.warning("Unable to find problem index to update. Command text: %s", command)
    try:
        update_text = command.regex.group(3)
    except AttributeError:
        logger.warning("No update text was provided. Command text: %s", command)
    if index_to_update and update_text:
        response = "Problem #" + index_to_update + " updated with:\n```" + update_text + "```"
        to_update = list_of_messages[int(index_to_update) - 1]  # -1 to adjust for indexing
        prepend = "The following update has been posted:\n```"
        prepend += update_text + "```"
        # Thread the update message
        thread_reply(prepend, to_update.channel, to_update.timestamp, broadcast=True)
        # Notify sending channel of posting
        post_message(slack_channel, response)


@debuggable
def post_help(slack_channel, is_admin):
    response = "Invoke any of these commands using `!problem` or `@problem-bot`:\n" \
               "`help`: Posts this help.\n" \
               "`post \"...\"`: Submits a problem posting for approval.\n" \
               "`post \"...\" #channel`: Submits a problem to a specific channel for approval.\n"
    if is_admin:
        response += "\n*Admin-only commands:*\n" \
                    "`allow`: Approves problem to be posted to the users' channel.\n" \
                    "`deny`: Denies a problem being posted to the users' channel.\n" \
                    "`list`: Lists all pinned problems.\n" \
                    "`update # \"...\"`: Updates a problem with the specified text.\n" \
                    "`close #`: Closes problem according to its list number.\n" \
                    "\nMore information can be found at https://github.com/zbendas/ProblemBot"
    post_message(response, slack_channel)


def parse_slack_output(slack_rtm_output):
    """
    Determines how to route the incoming message from the RTM hose
    :param slack_rtm_output:
    :return: Returns 5 values: unparsed text, Slack user, Slack channel, timestamp of message received, module flag
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and output['text'].startswith('!problem') and output['user'] != BOT_ID:
                return output['text'].split("!problem")[1].strip(), output['user'], output['channel'], output['ts'], "p"
            elif output and 'text' in output and output['text'].startswith(AT_BOT) and output['user'] != BOT_ID:
                return output['text'].split(AT_BOT)[1].strip(), output['user'], output['channel'], output['ts'], "p"
            elif settings["modules"]["knowledgelinker"]:
                if output and 'text' in output and output['user'] != BOT_ID and knowledgelinker.scan(output['text']):
                    return knowledgelinker.grab(output), output['user'], output['channel'], output['ts'], "kl"
    return None, None, None, None, None

if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1  # 1 second firehose delay
    if slack_client.rtm_connect():
        logger.info("Problem-Bot connected and running!")
        logger.info("Grabbing currently posted problems!")
        api_response = slack_client.api_call("pins.list", channel=GENERAL_CHANNEL)
        for item in reversed(api_response["items"]):
            if item["type"] == "message" and item["message"]["user"] == BOT_ID:
                if item["message"]["text"] is not "":
                    text = regex.search(r"(?:```)(.*)(?:```)", item["message"]["text"], regex.IGNORECASE).group(1)
                    list_of_messages.append(Message(GENERAL_CHANNEL, item["message"]["ts"], text))
                elif item["message"]["attachments"] is not []:
                    text = item["message"]["attachments"][0]["fields"][0]["value"]
                    list_of_messages.append(Message(GENERAL_CHANNEL, item["message"]["ts"], text))
        while True:
            unparsed_command, user, channel, timestamp, module_flag = parse_slack_output(slack_client.rtm_read())
            if unparsed_command and user and channel and module_flag == "p":
                handle_command(unparsed_command, user, channel, timestamp)
            if unparsed_command and user and channel and module_flag == "kl":
                knowledgelinker.send(unparsed_command, user, channel)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        logger.error("Connection failed! Check API key and Bot ID!")
