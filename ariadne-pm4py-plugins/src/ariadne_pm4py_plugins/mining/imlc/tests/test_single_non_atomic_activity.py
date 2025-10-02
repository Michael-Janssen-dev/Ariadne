from pm4py import ProcessTree

from analysis.trace_mining.imlc.base_cases.single_non_atomic_activity import (
    SingleNonAtomicActivityUVCL,
)
from analysis.trace_mining.imlc.tests.utils import test_basecase, BaseCaseTestCase

cases = [
    BaseCaseTestCase(("S A, E A",), ProcessTree(label="A")),
    BaseCaseTestCase(("S A",), None),
]


def test_single_non_atomic_activity():
    for case in cases:
        test_basecase(case, SingleNonAtomicActivityUVCL)
