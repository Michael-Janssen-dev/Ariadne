from collections import Counter

from pm4py.objects.dfg.obj import DFG


def discover_non_atomic_dfg_uvcl(uvcl):
    graph = Counter()
    start_activities = Counter()
    end_activities = Counter()

    for trace in uvcl:
        occurrences = uvcl[trace]
        events = [(e[0] == "S", e[2:]) for e in trace]
        n = len(events)

        # Start/end activities (single passes)
        for is_start, activity in events:
            if is_start:
                start_activities[activity] += occurrences
                break
        for is_start, activity in reversed(events):
            if is_start:
                break
            end_activities[activity] += occurrences

        # DFG edges
        # For each complete event at i, the forward window ends at the first
        # complete of an activity started in that window.
        # Two-pointer / sweep approach:

        completes_pending = []  # complete events whose forward window is open

        for is_start, activity in events:
            if is_start:
                # Every pending complete gets an edge to this start
                for prev_activity, started_set in completes_pending:
                    graph[(prev_activity, activity)] += occurrences
                    started_set.add(activity)
            else:
                # Close any pending complete whose window contains this activity
                still_pending = []
                for prev_activity, started_set in completes_pending:
                    if activity in started_set:
                        # window closes for this complete
                        pass
                    else:
                        still_pending.append((prev_activity, started_set))
                completes_pending = still_pending
                # Now this complete event itself becomes pending
                completes_pending.append((activity, set()))
    return DFG(graph, start_activities, end_activities)
