from collections import Counter

from pm4py.objects.dfg.obj import DFG


def discover_non_atomic_dfg_uvcl(uvcl):
    graph = Counter()
    start_activities = Counter()
    end_activities = Counter()

    for trace in uvcl:
        occurrences = uvcl[trace]
        last_completed_activity = None
        for i, event in enumerate(trace):
            is_start = event.startswith("S")
            activity = event[2:]
            if is_start:
                if last_completed_activity is None:
                    start_activities[activity] += occurrences
            else:
                last_completed_activity = activity
                started = set()
                for j, event2 in enumerate(trace[i + 1 :], start=i + 1):
                    if event2.startswith("S"):
                        started.add(event2[2:])
                        graph[(activity, event2[2:])] += occurrences
                    else:
                        if event2[2:] in started:
                            break
        for event in reversed(trace):
            is_start = event.startswith("S")
            activity = event[2:]
            if is_start:
                break
            end_activities[activity] += occurrences
    return DFG(graph, start_activities, end_activities)
