from collections import Counter
from typing import Tuple

from pm4py.util.compression.dtypes import UVCL


def discover_concurrency_graph_uvcl(uvcl: UVCL) -> Counter[Tuple[str, str]]:
    concurrency_graph = Counter()
    for trace in uvcl:
        occurrences = uvcl[trace]
        active = {}
        for event in trace:
            is_start = event[0] == "S"
            activity = event[2:]
            if is_start:
                for other in active:
                    concurrency_graph[(other, activity)] += occurrences
                    concurrency_graph[(activity, other)] += occurrences
                active[activity] = active.get(activity, 0) + 1
            else:
                active[activity] -= 1
                if active[activity] == 0:
                    del active[activity]
    return concurrency_graph


ConcurrencyGraph = Counter[Tuple[str, str]]
