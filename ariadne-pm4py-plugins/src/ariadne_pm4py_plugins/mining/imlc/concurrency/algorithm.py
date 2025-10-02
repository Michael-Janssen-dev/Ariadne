from collections import Counter
from typing import Tuple
from pm4py.util.compression.dtypes import UVCL


def discover_concurrency_graph_uvcl(uvcl: UVCL) -> Counter[Tuple[str, str]]:
    concurrency_graph = Counter()
    for trace in uvcl:
        occurences = uvcl[trace]
        active_activities = list()
        for event in trace:
            is_start = event.startswith("S")
            activity = event[2:]
            if is_start:
                for active_activity in active_activities:
                    concurrency_graph[(active_activity, activity)] += occurences
                    concurrency_graph[(activity, active_activity)] += occurences
                active_activities.append(activity)
            else:
                active_activities.remove(activity)
    return concurrency_graph


ConcurrencyGraph = Counter[Tuple[str, str]]
