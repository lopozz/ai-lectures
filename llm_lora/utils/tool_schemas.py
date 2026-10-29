def tool(name, description, properties, required):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }

COLLECTION_ARG = {"type": "string", "description": "Name of the collection as said by the user"}
VIDEO_ARG = {"type": "string", "description": "Title of the video as said by the user"}
NOTE_ARG = {"type": "string", "description": "Concept or title of the note as said by the user"}

# fmt: off
TOOLS = [
    # --- collection level
    tool("create_collection", "Creates a new empty collection of videos.",
         {"name": {"type": "string", "description": "Name of the new collection"}}, ["name"]),
    tool("open_collection", "Opens a collection and shows the videos it contains.",
         {"collection": COLLECTION_ARG}, ["collection"]),
    tool("delete_collection", "Deletes a collection, together with all its videos and notes.",
         {"collection": COLLECTION_ARG}, ["collection"]),

    # --- video level
    tool("open_video", "Opens a video and shows the notes extracted from it.",
         {"video": VIDEO_ARG}, ["video"]),
    tool("move_video", "Moves a video to another collection.",
         {"video": VIDEO_ARG,
          "collection": {"type": "string", "description": "Name of the destination collection"}},
         ["video", "collection"]),
    tool("delete_video", "Deletes a video, together with all the notes extracted from it.",
         {"video": VIDEO_ARG}, ["video"]),

    # --- note level
    tool("search_notes", "Searches notes by content, across all videos.",
         {"query": {"type": "string", "description": "Words or concept to search for"}}, ["query"]),
    tool("open_note", "Opens a single note.",
         {"note": NOTE_ARG}, ["note"]),
    tool("play_note", "Plays the source video of a note, starting from the moment where the note's concept appears.",
         {"note": NOTE_ARG}, ["note"]),
    tool("delete_note", "Deletes a single note.",
         {"note": NOTE_ARG}, ["note"]),
]
# fmt: on
