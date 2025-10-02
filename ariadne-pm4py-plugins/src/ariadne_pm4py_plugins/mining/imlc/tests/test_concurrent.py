from analysis.trace_mining.imlc.cuts.concurrent import NonAtomicConcurrentCut
from analysis.trace_mining.imlc.tests.utils import CutTestCase, test_cut

cases = [CutTestCase(("d",), None)]


def test_concurrent():
    for case in cases:
        test_cut(case, NonAtomicConcurrentCut)
