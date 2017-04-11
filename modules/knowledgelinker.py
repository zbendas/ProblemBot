import re as regex
import logging
import problembot


module_logger = logging.getLogger("problembot.knowledgelinker")


def debuggable(func):
    def decorated_function(*original_args, **original_kwargs):
        module_logger.debug("Entering " + func.__name__)
        return_value = func(*original_args, **original_kwargs)
        module_logger.debug("Exiting " + func.__name__)
        return return_value
    return decorated_function


@debuggable
def scan(text):
    if regex.search(r"(?:^| +)(" + problembot.settings["module_settings"]["knowledgelinker"]["kb_word"]
                    + "\d+)", text, regex.IGNORECASE):
        return True
    else:
        return False


@debuggable
def grab(output):
    result = regex.search(r"(?:^| +)(" + problembot.settings["module_settings"]["knowledgelinker"]["kb_word"] + "\d+)",
                          output['text'], regex.IGNORECASE)
    if result.group(1):
        return result.group(1)
    else:
        return None


@debuggable
def send(text, user, channel):
    url_structure = problembot.settings["url"]
    article = text.upper()
    url = url_structure + article
    full_text = "<@" + user + ">: " + url
    return problembot.post_message(full_text, channel)

if __name__ == "__main__":
    print("This module is not meant to be run separately. Please run problembot.py instead, and enable the "
          "\"knowledgelinker\" module in your settings.json")
