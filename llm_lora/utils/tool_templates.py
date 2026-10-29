# Phrasings for the TEST set, keyed as in tools.md. Slots are named after the
# function argument they fill ({name}, {collection}, {video}, {note}, {query}),
# so a slot value is also the gold argument value.
# Utterances look like ASR transcripts: lowercase, no punctuation.

# fmt: off

# function -> form -> templates. The gold call is the function with the slot values as arguments.
SIMPLE = {
    "create_collection": {
        "direct": [
            "create a collection called {name}", "make a new collection called {name}", "new collection {name}",
            "start a collection named {name}", "create a new collection named {name}", "add a collection called {name}",
        ],
        "question": [
            "can you create a collection called {name}", "could you make a new collection called {name}",
            "can you start a collection named {name}", "would you create a new collection called {name}",
            "can i get a new collection called {name}", "can you make me a collection for {name}",
        ],
    },
    "open_collection": {
        "direct": [
            "open the {collection} collection", "show me my {collection} collection", "go to the {collection} collection",
            "open my {collection} collection", "show the videos in {collection}",
        ],
        "question": [
            "can you open the {collection} collection", "could you show me my {collection} collection",
            "what videos do i have in {collection}", "can you show me what is in the {collection} collection",
            "can you take me to the {collection} collection",
        ],
    },
    "delete_collection": {
        "direct": [
            "delete the {collection} collection", "remove the {collection} collection", "get rid of the {collection} collection",
            "delete my {collection} collection", "erase the {collection} collection",
        ],
        "question": [
            "can you delete the {collection} collection", "could you remove the {collection} collection",
            "would you get rid of my {collection} collection", "can you erase the {collection} collection",
            "can you please delete the {collection} collection",
        ],
    },
    "open_video": {
        "direct": [
            "open the {video} video", "show me the notes from the {video} video", "go to the {video} video",
            "open the video {video}", "show the notes of the {video} video",
        ],
        "question": [
            "can you open the {video} video", "can you show me the notes from the {video} video",
            "could you take me to the {video} video", "can you show me the notes of the {video} video",
            "could you open the video {video}",
        ],
    },
    "move_video": {
        "direct": [
            "move the {video} video to {collection}", "put the {video} video in {collection}",
            "move {video} to the {collection} collection", "send the {video} video to {collection}",
            "put {video} in the {collection} collection",
        ],
        "question": [
            "can you move the {video} video to {collection}", "could you put the {video} video in {collection}",
            "can you move {video} to the {collection} collection", "would you send the {video} video to {collection}",
            "can you put {video} into {collection}",
        ],
    },
    "delete_video": {
        "direct": [
            "delete the {video} video", "remove the {video} video", "get rid of the {video} video",
            "delete the video {video}", "erase the {video} video",
        ],
        "question": [
            "can you delete the {video} video", "could you remove the {video} video",
            "would you get rid of the {video} video", "can you delete the video {video}",
            "can you erase the {video} video",
        ],
    },
    "search_notes": {
        "direct": [
            "find notes about {query}", "search for {query}", "show me all the notes on {query}",
            "search my notes for {query}", "look up notes about {query}",
        ],
        "question": [
            "what do i have about {query}", "can you find notes about {query}", "can you search my notes for {query}",
            "can you show me notes on {query}", "could you look up notes about {query}",
        ],
    },
    "open_note": {
        "direct": [
            "open the note about {note}", "show me the note on {note}", "bring up the note about {note}",
            "open my note on {note}", "pull up the note about {note}",
        ],
        "question": [
            "can you open the note about {note}", "could you show me the note on {note}",
            "can you bring up the note about {note}", "can you pull up my note on {note}",
            "would you open the note on {note}",
        ],
    },
    "play_note": {
        "direct": [
            "play the part about {note}", "take me to the part about {note}", "jump to the part on {note}",
            "play the note on {note}", "go to the part about {note}",
        ],
        "question": [
            "can you play the part about {note}", "could you take me to the part on {note}",
            "can you jump to the part about {note}", "can you play the note on {note}",
            "would you play the part on {note}",
        ],
    },
    "delete_note": {
        "direct": [
            "delete the note about {note}", "remove the note on {note}", "get rid of the note about {note}",
            "erase the note on {note}", "delete my note about {note}",
        ],
        "question": [
            "can you delete the note about {note}", "could you remove the note on {note}",
            "can you get rid of the note about {note}", "would you erase the note on {note}",
            "can you delete my note on {note}",
        ],
    },
}
SIMPLE_PER_FORM = 25  # per function and form: 10 functions x (25 direct + 25 question) = 500

# (function, missing argument) -> form -> templates. Only the argument that is
# present gets a slot, so most templates have none (3 per form are enough for
# the quotas below).
MISSING_ARG = {
    ("create_collection", "name"): {
        "direct": ["create a collection", "make a new collection", "start a new collection"],
        "question": ["can you make a new collection", "could you create a collection", "can you start a new collection"],
    },
    ("open_collection", "collection"): {
        "direct": ["open a collection", "show me the collection", "open my collection"],
        "question": ["can you open a collection", "could you show me the collection", "can you open the collection"],
    },
    ("delete_collection", "collection"): {
        "direct": ["delete a collection", "remove the collection", "delete the collection"],
        "question": ["can you remove the collection", "could you delete a collection", "can you delete the collection"],
    },
    ("open_video", "video"): {
        "direct": ["open a video", "show me the notes of the video", "open the video"],
        "question": ["can you open a video", "could you show me the notes of the video", "can you open the video"],
    },
    ("move_video", "video"): {
        "direct": ["move a video to {collection}", "put the video in {collection}", "move the video to the {collection} collection"],
        "question": ["can you move a video to {collection}", "could you put the video in {collection}", "can you move the video to {collection}"],
    },
    ("move_video", "collection"): {
        "direct": ["move the {video} video", "move the {video} video to another collection", "put the {video} video somewhere else"],
        "question": ["can you move the {video} video", "can you move {video} to another collection", "could you put the {video} video somewhere else"],
    },
    ("move_video", "both"): {
        "direct": ["move a video", "move a video somewhere else", "put a video in another collection"],
        "question": ["can you move a video", "can you move a video somewhere else", "could you put a video in another collection"],
    },
    ("delete_video", "video"): {
        "direct": ["delete a video", "remove the video", "delete the video"],
        "question": ["can you delete a video", "could you remove the video", "can you delete the video"],
    },
    ("search_notes", "query"): {
        "direct": ["find notes", "search my notes", "look up my notes"],
        "question": ["can you search my notes", "could you find some notes", "can you look up my notes"],
    },
    ("open_note", "note"): {
        "direct": ["open a note", "show me the note", "open the note"],
        "question": ["can you open a note", "could you show me the note", "can you open the note"],
    },
    ("play_note", "note"): {
        "direct": ["play a note", "take me to the part", "play the part"],
        "question": ["can you play a note", "could you take me to the part", "can you play the part"],
    },
    ("delete_note", "note"): {
        "direct": ["delete a note", "remove the note", "delete the note"],
        "question": ["can you delete a note", "could you remove the note", "can you delete the note"],
    },
}
# 50 in total; the extra examples go to the two move_video cases with a value present
MISSING_ARG_QUOTA = {case: 4 for case in MISSING_ARG}
MISSING_ARG_QUOTA[("move_video", "video")] = 5
MISSING_ARG_QUOTA[("move_video", "collection")] = 5

# subcategory -> templates. Templates with a slot carry real names (near-misses).
NOT_SUPPORTED = {
    "missing_action": [
        "rename the {video} video", "rename my {collection} collection", "share the note about {note}",
        "share the {video} video", "export the {collection} collection", "download the {video} video",
        "edit the note about {note}", "duplicate the {collection} collection", "archive the {collection} collection",
        "translate the note about {note}", "sync my library", "back up my library",
    ],
    "ui_only": [
        "add a new video to {collection}", "add a video to the {collection} collection", "upload a video to {collection}",
        "import a playlist into {collection}", "paste a youtube link into {collection}", "add a new video from youtube",
    ],
    "bulk": [
        "delete all the notes about {query}", "move every video to {collection}",
        "delete all the videos in the {collection} collection", "delete every note in the {video} video",
        "move all the videos to the {collection} collection", "open every note about {note}",
        "delete all my collections", "delete all my notes",
    ],
}
NOT_SUPPORTED_QUOTA = {"missing_action": 20, "ui_only": 15, "bulk": 15}

# fmt: on
