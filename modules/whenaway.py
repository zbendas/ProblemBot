import datetime as dt
import logging
import problembot


module_logger = logging.getLogger("problembot.whenaway")

defaulting_channel = problembot.settings["module_settings"]["whenaway"]["defaulting_channel"]


def debuggable(func):
    def decorated_function(*original_args, **original_kwargs):
        module_logger.debug("Entering " + func.__name__)
        return_value = func(*original_args, **original_kwargs)
        module_logger.debug("Exiting " + func.__name__)
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
            module_logger.info("Clearing the function response cache for %s", self.func.__name__)
        try:
            return self.cache[args]
        except KeyError:
            self.cache[args] = self.func(*args)
            return self.cache[args]


@debuggable
@Memoize
def get_users(slack_channel):
    response = problembot.slack_client.api_call("channels.info", channel=slack_channel)
    # response["ok"] will be False if slack_channel was actually a group, as channels.info cannot check group info
    # In that case, we'll instead move into the groups.info call, which can see that information
    if not response["ok"]:
        response = problembot.slack_client.api_call("groups.info", channel=slack_channel)
        try:
            response["group"]["members"].remove(problembot.BOT_ID)
        except ValueError:
            module_logger.warning("Unable to remove this bot from list of group users.")
        module_logger.debug("Group members: " + str(response["group"]["members"]))
        return response["group"]["members"]
    else:
        try:
            response["channel"]["members"].remove(problembot.BOT_ID)
        except ValueError:
            module_logger.warning("Unable to remove this bot from list of channel users.")
        module_logger.debug("Channel members: " + str(response["channel"]["members"]))
        return response["channel"]["members"]


@debuggable
def determine_away(slack_user):
    response = problembot.slack_client.api_call("users.getPresence", user=slack_user)
    if response["presence"] == "away":
        is_away = True
    else:
        is_away = False
    return is_away


@debuggable
def post_if_present(text, slack_channel):
    users = get_users(slack_channel)
    for user in users:
        if not determine_away(user):
            return problembot.post_message(text, slack_channel)
    return problembot.post_message(text, defaulting_channel)
