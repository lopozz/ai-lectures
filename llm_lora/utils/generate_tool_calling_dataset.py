import os
import re
import json
import random
import argparse
from string import Formatter

from tool_schemas import TOOLS
from tool_pools import TEST_POOLS, TRAIN_POOLS
from tool_templates import (
    SIMPLE,
    SIMPLE_PER_FORM,
    MISSING_ARG,
    MISSING_ARG_QUOTA,
    NOT_SUPPORTED,
    NOT_SUPPORTED_QUOTA,
)

# category -> behavior being tested (policy in tools.md)
CATEGORIES = [
    "simple",  # a supported action with all its arguments -> call the matching function
    "missing_arg",  # supported action, required value missing -> no call
    "not_supported",  # about collections/videos/notes, but no function does it -> no call
]

# columns written to the output file
COLUMNS = ["messages", "tools", "category"]

FORMS = ["direct", "question"]
NO_CALL_TEXT = "I can't do that."

# slot name -> pool it is drawn from
POOL_OF = {"name": "collections", "collection": "collections", "video": "videos", "note": "notes", "query": "queries"}

# utterances must not refer to objects by context (labeling convention 4)
CONTEXT_WORDS = re.compile(r"\b(this|that|it|latest)\b|\bthe last\b")


def slots_of(template: str) -> list[str]:
    return [field for _, field, _, _ in Formatter().parse(template) if field]


def fill_cell(
    rng: random.Random,
    pools: dict,
    templates: list[str],
    n: int,
    exclude: frozenset = frozenset(),
    strict: bool = True,
) -> list[tuple[str, dict]]:
    """
    Generate n (utterance, slot values) pairs from the templates of one cell.
    Templates are used round-robin; the values of each slot are drawn without
    replacement (the pool is reshuffled when n exceeds its size), and a
    template without slots is used at most once. Utterances in `exclude` are
    never produced. When fewer than n unique utterances exist, strict raises
    and non-strict returns what it found.
    """
    templates = rng.sample(templates, len(templates))
    values = {}  # slot -> shuffled values of its pool
    for t in templates:
        for slot in slots_of(t):
            if slot not in values:
                pool = pools[POOL_OF[slot]]
                values[slot] = [v for _ in range(-(-n // len(pool))) for v in rng.sample(pool, len(pool))]

    out = []
    seen = set(exclude)
    for i in range(len(templates) * (n + 1)):
        if len(out) == n:
            break
        t = templates[i % len(templates)]
        v = {s: values[s][len(out)] for s in slots_of(t)}
        u = t.format(**v)
        if u in seen:  # also covers slot-free templates already used
            continue
        seen.add(u)
        out.append((u, v))

    if len(out) < n:
        msg = f"only {len(out)}/{n} unique utterances from {templates}"
        if strict:
            raise ValueError(msg)
        print(f"warning: {msg}")
    return out


def split_evenly(n: int, parts: list[str]) -> dict[str, int]:
    base, extra = divmod(n, len(parts))
    return {p: base + (i < extra) for i, p in enumerate(parts)}


def call_turn(name: str, arguments: dict) -> dict:
    return {"role": "assistant", "tool_calls": [{"type": "function", "function": {"name": name, "arguments": arguments}}]}


def no_call_turn() -> dict:
    return {"role": "assistant", "content": NO_CALL_TEXT}


def make_row(category: str, subcategory: str, function: str | None, utterance: str, assistant: dict) -> dict:
    """
    One generated row (the id is assigned after shuffling; subcategory and
    function are dropped when writing):
    - messages: user turn (input) + gold assistant turn (output)
    - tools: the available functions, as a JSON string
    - category, subcategory: the behavior being tested
    - function: the called function; for missing_arg the incomplete one; None for not_supported
    """
    return {
        "messages": [{"role": "user", "content": utterance}, assistant],
        "tools": json.dumps(TOOLS, ensure_ascii=False),
        "category": category,
        "subcategory": subcategory,
        "function": function,
    }


def generate_simple(rng: random.Random, pools: dict, scale: int = 1, **fill) -> list[dict]:
    rows = []
    for function, forms in SIMPLE.items():
        for form in FORMS:
            for utterance, args in fill_cell(rng, pools, forms[form], SIMPLE_PER_FORM * scale, **fill):
                rows.append(make_row("simple", form, function, utterance, call_turn(function, args)))
    return rows


def generate_missing_arg(rng: random.Random, pools: dict, scale: int = 1, **fill) -> list[dict]:
    rows = []
    for (function, missing), forms in MISSING_ARG.items():
        for form, n in split_evenly(MISSING_ARG_QUOTA[(function, missing)] * scale, FORMS).items():
            for utterance, _ in fill_cell(rng, pools, forms[form], n, **fill):
                rows.append(make_row("missing_arg", missing, function, utterance, no_call_turn()))
    return rows


def generate_not_supported(rng: random.Random, pools: dict, scale: int = 1, **fill) -> list[dict]:
    rows = []
    for subcategory, templates in NOT_SUPPORTED.items():
        for utterance, _ in fill_cell(rng, pools, templates, NOT_SUPPORTED_QUOTA[subcategory] * scale, **fill):
            rows.append(make_row("not_supported", subcategory, None, utterance, no_call_turn()))
    return rows


def validate(rows: list[dict], pools: dict):
    """Checks the labeling conventions of tools.md; raises on the first violation."""
    utterances = [r["messages"][0]["content"] for r in rows]
    assert len(set(utterances)) == len(utterances), "duplicate utterances"

    required = {t["function"]["name"]: t["function"]["parameters"]["required"] for t in TOOLS}
    for r, u in zip(rows, utterances):
        assert re.fullmatch(r"[a-z0-9 ]+", u), f"not lowercase / has punctuation: {u!r}"
        assert not CONTEXT_WORDS.search(u), f"refers to an object by context: {u!r}"
        turn = r["messages"][1]
        if r["category"] == "simple":
            call = turn["tool_calls"][0]["function"]
            assert call["name"] == r["function"]
            assert sorted(call["arguments"]) == sorted(required[call["name"]]), u
            for v in call["arguments"].values():
                assert v == v.lower() and v in u, f"argument {v!r} not in {u!r}"
        else:
            assert "tool_calls" not in turn and turn["content"] == NO_CALL_TEXT

    # not_supported: at least half must be near-misses (real names in the request)
    ns = [u for r, u in zip(rows, utterances) if r["category"] == "not_supported"]
    pool_values = {v for p in pools.values() for v in p}
    near = sum(any(v in u for v in pool_values) for u in ns)
    assert near * 2 >= len(ns), f"only {near}/{len(ns)} not_supported are near-misses"


# split -> slot value pools and a multiplier on the quotas of the test set
SPLITS = {
    "test": {"pools": TEST_POOLS, "scale": 1},
    "train": {"pools": TRAIN_POOLS, "scale": 1},
}


def build(split: str, rng: random.Random, **fill) -> list[dict]:
    pools, scale = SPLITS[split]["pools"], SPLITS[split]["scale"]
    rows = []
    rows += generate_simple(rng, pools, scale, **fill)
    rows += generate_missing_arg(rng, pools, scale, **fill)
    rows += generate_not_supported(rng, pools, scale, **fill)
    validate(rows, pools)
    rng.shuffle(rows)
    return rows


def main():
    """
    This script generates the tool-calling test or train set described in
    tools.md (Dataset Generation Policy) from templates and name pools, with
    columns: id, messages, tools, category.
    Both splits share the templates but use disjoint name pools; the train set
    also never contains an utterance of the test set.
    The results are saved in a JSONL file.
    """

    # fmt: off
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", type=str, choices=list(SPLITS), default="test")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test_seed", type=int, default=42, help="seed the test set was generated with (train excludes its utterances)")
    parser.add_argument("--output_path", type=str, default=None, help="where to save results (default: tool_calling_<split>.jsonl)")
    # fmt: on

    args = parser.parse_args()
    output_path = args.output_path or f"tool_calling_{args.split}.jsonl"

    for kind in TEST_POOLS:
        assert not set(TEST_POOLS[kind]) & set(TRAIN_POOLS[kind]), f"train and test '{kind}' pools overlap"
        for split in SPLITS:
            pool = SPLITS[split]["pools"][kind]
            assert len(set(pool)) == len(pool), f"duplicates in {split} '{kind}' pool"

    if args.split == "test":
        rows = build("test", random.Random(args.seed))
    else:
        test_rows = build("test", random.Random(args.test_seed))
        exclude = frozenset(r["messages"][0]["content"] for r in test_rows)
        rows = build("train", random.Random(args.seed), exclude=exclude, strict=False)

    # subcategory and function are only used for generation and validation
    results = [
        {"id": f"{args.split}-{i:05d}", **{k: r[k] for k in COLUMNS}} for i, r in enumerate(rows)
    ]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    counts = {c: sum(r["category"] == c for r in results) for c in CATEGORIES}
    print(f"Saved {len(results)} records to {output_path} {counts}")


if __name__ == "__main__":
    main()
