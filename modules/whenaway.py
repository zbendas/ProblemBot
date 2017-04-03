import logging
import problembot


module_logger = logging.getLogger("problembot.whenaway")


def debuggable(func):
    def decorated_function(*original_args, **original_kwargs):
        module_logger.debug("Entering " + func.__name__)
        return_value = func(*original_args, **original_kwargs)
        module_logger.debug("Exiting " + func.__name__)
        return return_value
    return decorated_function


@debuggable
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
    return problembot.post_to_admin(text)
