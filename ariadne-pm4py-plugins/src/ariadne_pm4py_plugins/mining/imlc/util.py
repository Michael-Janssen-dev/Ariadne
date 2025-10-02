from typing import Any, Set


def merge(groups: list[Set[Any]], a: Any, b: Any):
    groups.append({a, b})
    if {a} in groups:
        groups.remove({a})
    if {b} in groups:
        groups.remove({b})


def is_start(activity) -> bool:
    return activity.startswith("S ")


def is_end(activity) -> bool:
    return activity.startswith("E ")


def base(activity) -> str:
    return activity[2:]
