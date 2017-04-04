# ProblemBot Modules
This README serves to discuss the modules currently available with ProblemBot!

## Modules
* knowledgelinker.py
* whenaway.py

### knowledgelinker.py
KnowledgeLinker allows for the easy linking of knowledge base articles from an outside web source. When ProblemBot sees a file
that contains a keyword, it will reply with a URL (taken from the `url` key in `settings.json`) appended with the knowledge
base keyword. This keyword is currently limited to "KBnnnnnnn", but will be expanded to be configurable in future versions.

### whenaway.py
WhenAway determines, when a `post` message is sent to a specific channel/group, whether or not the any of the members of that 
Slack channel or group are currently active. If no members are active, it will decline to post the message to that specific
channel/group. Instead, it will behave as though no channel/group was specified, sending the post proposal as wide as it can.
