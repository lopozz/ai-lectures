"""
Tool call accuracy, scored like ragas `ToolCallAccuracy` but without the dependency.

A call is a dict {"name": str, "arguments": dict}, as returned by `parse_calls`
in the notebooks. Scores are in [0, 1].
"""


def exact_match_args(pred_args: dict, ref_args: dict) -> float:
    """Share of reference arguments whose value (compared as a string) is predicted correctly.
    Extra predicted arguments are not penalized."""
    if not ref_args and not pred_args:
        return 1.0
    if not ref_args:
        return 0.0
    return sum(k in pred_args and str(pred_args[k]) == str(ref_args[k]) for k in ref_args) / len(ref_args)


def _sort_key(call: dict) -> tuple:
    key = [call["name"]]
    for name in sorted(call["arguments"]):
        key += [name, str(call["arguments"][name])]
    return tuple(key)


def tool_call_accuracy(pred_calls: list[dict], ref_calls: list[dict], strict_order: bool = True) -> float:
    """
    - both lists empty: 1.0 (the model correctly made no call)
    - only one of them empty: 0.0
    - the sequences of function names differ (order or length): 0.0
    - otherwise the mean, over the reference calls, of `exact_match_args`

    With strict_order=False the calls may come in any order.
    """
    if not pred_calls and not ref_calls:
        return 1.0
    if not pred_calls or not ref_calls:
        return 0.0
    if not strict_order:
        pred_calls = sorted(pred_calls, key=_sort_key)
        ref_calls = sorted(ref_calls, key=_sort_key)
    if [c["name"] for c in pred_calls] != [c["name"] for c in ref_calls]:
        return 0.0
    return sum(exact_match_args(p["arguments"], r["arguments"]) for p, r in zip(pred_calls, ref_calls)) / len(ref_calls)
