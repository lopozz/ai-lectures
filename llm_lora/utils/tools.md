---
puppeteer:
  format: "A4"
  waitUntil: "networkidle0"
  printBackground: true

toc:
  depth_from: 1
  depth_to: 6
  ordered: true
---

<div align="center">
  <h1 style="margin-bottom: 4px;">Tool Definitions</h1>
  <div style="font-size: 24px; font-weight: 600; margin-top: 0;">
    Technical Requirements Document
  </div>
</div>

[TOC]



# Tool Definitions

## The application
The app turns YouTube videos into atomic notes, organized in three levels:
**collection** → **video** → **note**. A video belongs to one collection; a note belongs to one video
and points to a moment (timestamp) in it.

The model can call 10 functions:

| level | function | argument(s) | user intent | result |
|---|---|---|---|---|
| collection | `create_collection` | `name` | make a new group for videos | an empty collection is created |
| collection | `open_collection` | `collection` | see the videos in a collection | the list of its videos |
| collection | `delete_collection` | `collection` | remove a collection and its content | collection, videos and notes deleted (after confirmation) |
| video | `open_video` | `video` | see the notes of a video | the list of its notes |
| video | `move_video` | `video`, `collection` (destination) | put a video in another collection | the video changes collection |
| video | `delete_video` | `video` | remove a video and its notes | video and notes deleted (after confirmation) |
| note | `search_notes` | `query` | find notes on a topic, without knowing which one | a list of matching notes |
| note | `open_note` | `note` | see one specific note | that note is opened |
| note | `play_note` | `note` | watch where a concept is explained | the video plays from the note's timestamp |
| note | `delete_note` | `note` | remove one note | the note is deleted (after confirmation) |

The exact tool below are given with every example.

## Collection level

### `create_collection`
- **User intent**: make a new, empty group for videos on a topic
- **Result**: a new collection is created and shown (empty)
- **Argument**: `name`: the name of the new collection
- **Examples**: *"create a collection called roman history"*, *"new collection guitar lessons"*, *"make a collection for italian cooking"*
- **Failure response**:
  - name already used: *"You already have a collection called 'roman history'."*

### `open_collection`
- **User intent**: see what videos are in a collection
- **Result**: the list of videos in that collection
- **Argument**: `collection`: the name of the collection
- **Examples**: *"open the fine tuning collection"*, *"show me my speech models collection"*, *"what videos do i have in astronomy"*
- **Failure response**:
  - not found: *"I couldn't find a collection called 'astronomy'."*
  - several matches: shows the matching collections to choose from

### `delete_collection`
- **User intent**: remove a whole collection, with all its videos and notes
- **Result**: after confirmation, the collection and everything in it are deleted
- **Argument**: `collection`: the name of the collection
- **Examples**: *"delete the old tests collection"*, *"remove the collection chess openings"*
- **Failure response**:
  - not found: *"I couldn't find a collection called 'old tests'."*
  - several matches: shows the matching collections to choose from
  - user does not confirm: *"Okay, nothing was deleted."*

## Video level

### `open_video`
- **User intent**: see the notes extracted from one video
- **Result**: the list of notes of that video, each with its timestamp
- **Argument**: `video`: the title of the video
- **Examples**: *"open the lora explained video"*, *"show me the notes from whisper paper review"*, *"go to the video black holes explained"*
- **Failure response**:
  - not found: *"I couldn't find a video called 'lora explained'."*
  - several matches: shows the matching videos to choose from

### `move_video`
- **User intent**: put a video in a different collection
- **Result**: the video now belongs to the destination collection
- **Arguments**: `video`: the title of the video; `collection`: the **destination** collection
- **Examples**: *"move the lora explained video to speech models"*, *"put sourdough bread at home in italian cooking"*
- **Failure response**:
  - video not found: *"I couldn't find a video called 'lora explained'."*
  - collection not found: *"There's no collection called 'speech models'."*
  - already there: *"'lora explained' is already in speech models."*

### `delete_video`
- **User intent**: remove a video and all its notes
- **Result**: after confirmation, the video and its notes are deleted
- **Argument**: `video`: the title of the video
- **Examples**: *"delete the lora explained video"*, *"remove the video how gps works"*
- **Failure response**:
  - not found: *"I couldn't find a video called 'how gps works'."*
  - several matches: shows the matching videos to choose from
  - user does not confirm: *"Okay, nothing was deleted."*

## Note level

### `search_notes`
- **User intent**: find or browse what I have on a topic, without knowing which note
- **Result**: a **list** of matching notes, possibly from many videos and collections
- **Argument**: `query`: the topic or keywords
- **Examples**: *"find notes about taxes"*, *"search for backpropagation"*, *"show me all the notes on gravity"*, *"what do i have about sourdough"*
- **Failure response**:
  - no results: *"I didn't find any notes about 'taxes'."*

### `open_note`
- **User intent**: see one specific note I already have in mind
- **Result**: that **single** note is opened (concept, explanation, timestamp)
- **Argument**: `note`: the concept or title of the note
- **Examples**: *"open the note about compound interest"*, *"show me the note on kv cache"*, *"bring up the note about the punic wars"*
- **Failure response**:
  - not found: *"I couldn't find a note about 'compound interest'."*
  - several matches: shows the matching notes to choose from

### `play_note`
- **User intent**: watch the moment in the video where a concept is explained
- **Result**: the source video plays from the note's timestamp
- **Argument**: `note`: the concept or title of the note
- **Examples**: *"play the part about attention"*, *"take me to where it talks about kv cache"*, *"jump to the part on dough hydration"*
- **Failure response**:
  - not found: *"I couldn't find a note about 'attention'."*
  - several matches: shows the matching notes to choose from
  - video unavailable (offline or removed from YouTube): *"I can't play that video right now."*

### `delete_note`
- **User intent**: remove a single note
- **Result**: after confirmation, the note is deleted; the video and its other notes stay
- **Argument**: `note`: the concept or title of the note
- **Examples**: *"delete the note about rank"*, *"remove the note on beam search"*
- **Failure response**:
  - not found: *"I couldn't find a note about 'rank'."*
  - several matches: shows the matching notes to choose from
  - user does not confirm: *"Okay, nothing was deleted."*

# Dataset Generation Policy

## Test Set

## Purpose
This test set measures how well a small on-device model (FunctionGemma 270M) turns a transcribed
voice command into the right function call, or correctly makes **no call**.
It is used to compare the base model and the fine-tuned model under the same conditions.


## Labeling conventions
1. **Utterances look like ASR transcripts**: English, lowercase, no punctuation.
2. **Arguments are copied as the user said them, without leading articles**:
   "open the lora explained video" → `video="lora explained"`.
3. **Argument values are lowercase.**
4. **Objects are always named explicitly.** No utterance refers to an object with
   "this", "that", "it", "the last" or "the latest".
5. **At most one call per utterance.**
6. **No call** when a required argument is missing, when the requested action is not one of the
   10 functions, or when the request is not a command for this app.
   The gold output is then a fixed text: `"I can't do that."`.
7. **Every example has exactly one correct label.** If a reasonable person could disagree on the
   label, the example is removed, not relabeled.

## Categories

### Call Expected

**`simple`**: a clear command for one function, with all required arguments named explicitly.

| subcategory | definition | example |
|---|---|---|
| `direct` | the command as an imperative | "open the lora explained video" |
| `question` | the command phrased as a question | "can you show me the notes from the lora explained video" |

### No Call Expected

**`missing_arg`**: a supported action, but a required value is missing; calling would mean inventing it.

| function | missing argument | examples |
|---|---|---|
| `create_collection` | `name` | "create a collection", "can you make a new collection" |
| `open_collection` | `collection` | "open a collection", "show me the collection" |
| `delete_collection` | `collection` | "delete a collection", "can you remove the collection" |
| `open_video` | `video` | "open a video", "show me the notes of the video" |
| `move_video` | `video` | "move a video to speech models", "put the video in speech models" |
| `move_video` | `collection` | "move the lora explained video", "can you move lora explained to another collection" |
| `move_video` | both | "move a video", "can you move a video somewhere else" |
| `delete_video` | `video` | "delete a video", "remove the video" |
| `search_notes` | `query` | "find notes", "can you search my notes" |
| `open_note` | `note` | "open a note", "show me the note" |
| `play_note` | `note` | "play a note", "take me to the part" |
| `delete_note` | `note` | "delete a note", "can you remove the note" |

Each function's examples are split evenly between `direct` and `question` forms, like the `simple` category.

**`not_supported`**: a command about collections, videos or notes, for an action the app does not have.

| subcategory | definition | example |
|---|---|---|
| `missing_action` | an action that no function performs | "rename the lora explained video", "share the note about kv cache" |
| `ui_only` | an action done in the UI, not by voice | "add a new video to speech models" |
| `bulk` | the action applies to many objects at once | "delete all the notes about taxes" |

<!-- **`out_of_scope`**: not a command for this app.

| subcategory | definition | example |
|---|---|---|
| `content_question` | asks for an answer about the content, not an action | "what does the lora explained video say about learning rates" |
| `chit_chat` | conversational turns | "thanks that's all", "never mind" |
| `other_app` | a command meant for another app | "set an alarm for seven", "call mom" | -->

At least half of the no-call examples in each category must be **near-misses**: requests that look
like a valid command (same verbs, same object types, real names) but must not trigger a call.

## Quantities

| part | examples |
|---|---|
| `simple`: 10 functions × 50 (25 `direct` + 25 `question`) | 500 |
| `missing_arg` | 50 |
| `not_supported` | 50 |
| **total** | **600** |


## Names (slot values)
- Four pools: collection names, video titles, note concepts, search queries.
- Names come from **many domains** (machine learning, cooking, history, finance, music, science, sport, ...).
- Test names are **never used in the training set**, and test phrasings (templates) are **never used in training**.
- A name must not make the label ambiguous (e.g. a video titled like a command).

## Format
One row per example, with these columns:

| column | content |
|---|---|
| `id` | unique id, e.g. `test-00042` |
| `messages` | the user turn and the gold assistant turn: `tool_calls` for a call, `content` for no call |
| `tools` | the 10 tool schemas, as a JSON string |
| `category` | `simple`, `missing_arg`, `not_supported`, `out_of_scope` |


## Future work

Not covered in this version of the test set; to be added later.

**Call expected**
- **Context references**: objects named by context instead of by name ("this video", "the last video i added"), with `@current` / `@latest` as argument values.
- **Parallel**: one function called several times in one command
  ("delete the notes about rank and attention" → `delete_note(note="rank")`, `delete_note(note="attention")`).
- **Multiple**: several functions are available, and the model must choose the right one.
- **Parallel + multiple**: several different functions called in one command
  ("create a collection called speech models and move whisper paper review to it" → `create_collection(...)`, `move_video(...)`).

**No call expected**
- **`out_of_scope`** category: questions about the content, chit-chat, and commands meant for other apps.
- **Structured no-call outputs**: fixed labels (`missing_argument`, `not_supported`, `out_of_scope`) or a `cannot_execute` tool, so the app knows why no call was made. The base model ignored the `cannot_execute` tool, so this requires training.

**Input conditions**
- **ASR noise**: fillers, repetitions, self-corrections, recognition errors on names.
- **Languages other than English** (Italian first).



<!-- ### Gold answer for no-call examples (draft, to be decided)

When no call is expected, the gold assistant turn contains **text instead of a function call**.
The exact text is not decided yet. Options under consideration:

| option | gold answer | trade-off |
|---|---|---|
| A. one fixed sentence | `"I can't do that."` for every no-call example | simplest to learn; the app can't tell *why* there was no call |
| B. one fixed sentence per situation | a short question naming what is missing, or `"I can't do that yet."` for `not_supported` | the app knows what to ask; still a small, closed set of sentences |
| C. empty answer | the model only ends its turn | cheapest; no information for the app |

Draft of the sentences for option B:

| situation | gold answer |
|---|---|
| `create_collection` without a name | "What should I call the collection?" |
| a collection is missing (`open_collection`, `delete_collection`) | "Which collection?" |
| a video is missing (`open_video`, `delete_video`, `move_video`) | "Which video?" |
| `move_video` without the destination | "Which collection should I move it to?" |
| `move_video` with both arguments missing | "Which video, and to which collection?" |
| `search_notes` without a query | "What should I search for?" |
| a note is missing (`open_note`, `play_note`, `delete_note`) | "Which note?" |
| `not_supported` | "I can't do that yet." |

Whatever option is chosen:
- the answer is always taken from a **fixed, closed set** of sentences;
- the answer **never repeats names** from the utterance;
- every message shown to the user remains under the app's control.

**Evaluation of no-call examples**
- **Main metric:** the model makes **no call**. Correct regardless of the text it writes.
- **Secondary metric:** the text **exactly matches** the gold answer (meaningful only for options A and B). -->