from collections import Counter

from pm4py.objects.dfg.obj import DFG

from analysis.trace_mining.imlc.dfg.algorithm import discover_non_atomic_dfg_uvcl

cases = [
    (
        Counter({("S D", "S A", "E A", "S B", "E B", "S C", "E D", "E C"): 1}),
        DFG(
            graph=Counter({("A", "B"): 1, ("B", "C"): 1}),
            start_activities=Counter({"A": 1, "D": 1}),
            end_activities=Counter({"D": 1, "C": 1}),
        ),
    )
]


def test_non_atomic_dfg():
    for case in cases:
        uvcl, expected_dfg = case
        dfg = discover_non_atomic_dfg_uvcl(uvcl)
        assert dfg.graph == expected_dfg.graph
        assert dfg.start_activities == expected_dfg.start_activities
        assert dfg.end_activities == expected_dfg.end_activities
