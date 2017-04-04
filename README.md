# ProblemBot
A bot designed to help track outages and problems by creating pinned messages in Slack!

## What ProblemBot Does
ProblemBot is designed to be used in a chat interface via the [Slack API](http://api.slack.com/) for Python. The bot can manage multiple channels, designating some as "user" channels and some as "admin" channels, as well as keep track of a "general" channel where he can post and pin specific problems.

## Some Requirements
In order to get off the ground, ProblemBot has to be told exactly how to direct messages, i.e., what channels are for users, for admins, and which channel is the general channel. Additionally, he'll need a Slack api key and a Slack user ID.
These should all be collected into a `settings.json` file. This `.json` should be structured as follows:
```json
{
 "api": "XXXX",
 "bot_id": "XXXX",
 "logging_level": "XXXX"
 "modules": {
  "knowledgelinker": false,
  "whenaway": false
 },
 "general_channel": "XXXX",
 "user_channels": [
   "XXXX"],
 "user_groups": [
   "XXXX"],
 "admin_channels": [
   "XXXX"],
 "admin_groups": [
   "XXXX"]
}
```
This `settings.json` file will be loaded using Python's built-in `json` library and parsed using `json.loads()` to establish an internal dictionary of these values. The `create_settings.py` program can be used to create a basic `settings.json` file that should allow ProblemBot to get off the ground, but the file can, of course, be edited by hand for specific needs.

*Without this file, ProblemBot will crash!*

## Paging ProblemBot
ProblemBot takes several plaintext commands via the Slack message stream. He'll check the message feed every second,
determining whether or not he's been called, then perform whatever action he's been told to perform.

To call ProblemBot, mention him using Slack's `@user` functionality or start your message with `!problem`

## ProblemBot Commands
### In particular, he can perform the following actions at a user's request:
#### Post
ProblemBot can suggest that a problem be posted to the general channel, alerting all users within that channel to an issue.
This has several modes of operation, all accessible through variations on the `post` command:
* `post "..."` (from user channel): Sends a message to all admin channels requesting that the message in quotes be posted
  * The text entered between `"` will be posted exactly as it appears; there will be no spelling nor grammar correction
  * This will post to *every* admin channel. It should be used sparingly, if possible, to cut down message frequency!
* `post "..."` (from admin channel): Immediately posts a problem to the general channel
  * This usage bypasses the need for a posting to be approved or denied
  * As above, no spelling nor grammar correction will be applied to the message
  * This will notify *every* admin channel that a problem was posted
* `post "..." #channel` (from user channel): Sends a message to the specified channel, if it is an admin channel, requesting
that the message in quotes be posted
  * If the `#channel` isn't an admin channel, this will act exactly as `post "..."`
  * This usage allows users to specify exactly who they need to approve a message
  * As above, no spelling nor grammar correction will be applied to the message
  * This usage will not message every admin channel, only the specified admin channel
#### Help
ProblemBot can post a condensed version of this readme to the invoking channel.
* `help`: Posts a version of this readme. The commands it provides will be context-sensitive. If invoked in a user channel,
it will only post commands available to users. If invoked in an admin channel, it will post all commands available to both
admins and to users.
  
### All of the following are admin-only commands. If these are invoked in user channels, they will be ignored.
#### Allow a post
ProblemBot will validate that a problem should be posted, then complete the posting process.
This command can be used as follows:
* `allow`: Approves the suggested problem, posting it to the general channel
  * In the approving channel, this will post a short confirmation message
  * In all other admin channels, posts an alert stating that the problem has been posted
  * In all users channels, sets the channel topic to the problem text
#### Deny a post, with or without a reason
ProblemBot will invalidate a suggested problem, going no further with the posting process.
This command can be used as follows:
* `deny`: Denies the suggested problem
* `deny "reason"`: Denies the suggested problem, then notifies the sender of the reason for the denial
  * No spelling nor grammar correction will be applied to the text between `"`
#### List all posted problems
ProblemBot will provide a numbered and timestamped list of the currently posted problems. These problems are listed
chronologically from oldest to newest. The numbers printed next to each problem can be used as identifiers in the `update` and
`close` commands.
* `list`: Prints the current list of problems
#### Update a posted problem with further information
ProblemBot will post a reply to the message thread where the specified problem is pinned. This thread reply will be broadcast
to the channel, to serve as an alert. The entire thread will be visible in the channel details as a pinned item.
* `update # "..."`: Updates the specified problem with the text provided. This text is posted as a new threaded reply to
the problem's original posting.
  * No spelling nor grammar correction will be applied to the text between `"`
#### Close out a problem
ProblemBot will unpin and announce the resolution of a specified problem. The thread reply will be broadcast to the channel,
to serve as an alert. This will also reset the channel topic in all user channels back to the next most recent problem or
to an all-clear message if there are no further issues.
* `close #`: Closes the specified problem and resets the channel topics of the user channels

## Modules
ProblemBot ships with a few extra features that can be enabled on a per-installation basis via the `settings.json` file. More information can be found on these modules in the `modules/README.md` file.
