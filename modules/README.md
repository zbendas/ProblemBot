# ProblemBot Modules
This README serves to discuss the modules currently available with ProblemBot!

## Modules
* knowledgelinker.py
* whenaway.py

### knowledgelinker.py
KnowledgeLinker allows for the easy linking of knowledge base articles from an outside web source. When ProblemBot sees a file
that contains a keyword, it will reply with a URL (taken from the `url` key in `settings.json`) appended with the knowledge
base keyword (taken from the `kb_word` key in `settings.json`) and all subsequent, continuous numbers will be
considered part of the desired knowledge base article number. This match will include the keyword. For example, if
the `kb_word` is "kb", and is followed by "1234567", the URL linked to will be `url`/"kb1234567".

### whenaway.py
WhenAway determines, when a `post` message is sent to a specific channel/group, whether or not the any of the members of that 
Slack channel or group are currently active. If no members are active, it will decline to post the message to that specific
channel/group. Instead, it will behave as though no channel/group was specified, sending the post proposal as wide as it can.
