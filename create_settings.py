import json


settings = {"api": "",
            "bot_id": "",
            "general_channel": "",
            "user_channels": [],
            "user_groups": [],
            "admin_channels": [],
            "admin_groups": []}

if __name__ == "__main__":
    try:
        # Follow this branch if there is no existing settings file
        with open("settings.json", "x") as settings_file:
            settings["api"] = input("Enter your Slack API key: ")
            settings["bot_id"] = input("Enter the Slack user ID of the intended bot user: ")
            settings["general_channel"] = input("Enter the Slack channel ID where alerts should be pinned: ")
            unparsed_u_channels = input("Enter the Slack channel IDs of your users' channels, "
                                        "separated by commas and spaces: ")
            settings["user_channels"] = unparsed_u_channels.split(", ")
            unparsed_u_groups = input("Enter the Slack group IDs of your users' groups, "
                                      "separated by commas and spaces: ")
            settings["user_groups"] = unparsed_u_groups.split(", ")
            unparsed_a_channels = input("Enter the Slack channel IDs of your admins' channels "
                                        "separated by commas and spaces: ")
            settings["admin_channels"] = unparsed_a_channels.split(", ")
            unparsed_a_groups = input("Enter the Slack group IDs of your admins' groups "
                                      "separated by commas and spaces: ")
            settings["admin_groups"] = unparsed_a_groups.split(", ")
            # Dump to fresh settings.json file
            json.dump(settings, settings_file)
    except FileExistsError:
        with open("settings.json", "w+") as settings_file:
            try:
                settings = json.loads(settings_file.read())
            except json.decoder.JSONDecodeError:
                pass
            if settings["api"] == "":
                settings["api"] == input("Enter your Slack API key: ")
            else:
                print("Your Slack API key is: " + str(settings["api"]))
            if settings["bot_id"] == "":
                settings["bot_id"] == input("Enter the Slack user ID of the intended bot user: ")
            else:
                print("The Slack user ID of your bot user is: " + str(settings["bot_id"]))
            if settings["general_channel"] == "":
                settings["general_channel"] = input("Enter the Slack channel ID where alerts should be pinned: ")
            else:
                print("The channel where your alerts will go is: " + str(settings["general_channel"]))
            if not settings["user_channels"]:
                unparsed_u_channels = input("Enter the Slack channel IDs of your users' channels, "
                                            "separated by commas and spaces: ")
                settings["user_channels"] = unparsed_u_channels.split(", ")
            else:
                print("The channels designated for your users are: " +
                      ", ".join(str(channel) for channel in settings["user_channels"]))
            if not settings["user_groups"]:
                unparsed_u_groups = input("Enter the Slack group IDs of your users' groups, "
                                          "separated by commas and spaces: ")
                settings["user_groups"] = unparsed_u_groups.split(", ")
            else:
                print("The groups designated for your users are: " +
                      ", ".join(str(group) for group in settings["user_groups"]))
            if not settings["admin_channels"]:
                unparsed_a_channels = input("Enter the Slack channel IDs of your admins' channels "
                                            "separated by commas and spaces: ")
                settings["admin_channels"] = unparsed_a_channels.split(", ")
            else:
                print("The channels designated for your admins are: " +
                      ", ".join(str(channel) for channel in settings["admin_channels"]))
            if not settings["admin_groups"]:
                unparsed_a_groups = input("Enter the Slack group IDs of your admins' groups "
                                          "separated by commas and spaces: ")
                settings["admin_groups"] = unparsed_a_groups.split(", ")
            else:
                print("The groups designated for your admins are: " +
                      ", ".join(str(group) for group in settings["admin_groups"]))
            # Dump to fresh settings.json file
            json.dump(settings, settings_file)
