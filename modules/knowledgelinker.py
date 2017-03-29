import re as regex
import problembot


def scan(text):
    if regex.search(r"(kb\d{7,})", text, regex.IGNORECASE):
        return True
    else:
        return False


def grab(output):
    result = regex.search(r"(kb\d{7,})", output['text'], regex.IGNORECASE)
    if result.group(1):
        return result.group(1)
    else:
        return None


def send(text, user, channel):
    url_structure = problembot.settings["url"]
    article = text.upper()
    url = url_structure + article
    full_text = "<@" + user + ">: " + url
    return problembot.post_message(full_text, channel)

if __name__ == "__main__":
    print("This module is not meant to be run separately. Please run problembot.py instead, and enable the "
          "\"knowledge\" function in your settings.json")
