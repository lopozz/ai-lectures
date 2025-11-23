This repository contains multiple independent lectures, all having data science as common denominator. 

Each lecture includes a presentation stored as a `whiteboard.excalidraw` file. To view it, open the file in the free online editor at https://excalidraw.com/ and drag-and-drop the `.excalidraw` file into the canvas.

Some lecture folders also include code; each of these is a standalone project with its own `pyproject.toml` and `uv.lock` and must be installed separately.

#### Setup
For a fast installation it is recommended to use [uv](https://docs.astral.sh/uv/getting-started/installation/):
```
cd path/to/lecture
uv sync
```

if you really don't want to install extra packages just use pip:
```
cd path/to/lecture
python -m venv .venv
source .venv/bin/activate
pip install .
```