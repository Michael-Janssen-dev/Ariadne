from collections import Counter
from dataclasses import dataclass
from typing import Generic, Tuple, Type, TypeVar

from pm4py import ProcessTree
from pm4py.algo.discovery.inductive.base_case.abc import BaseCase
from pm4py.algo.discovery.inductive.cuts.abc import Cut

from ariadne_pm4py_plugins.mining.imlc.dtypes.imlc import IMLCDataStructureUVCL

T = TypeVar("T")


@dataclass
class IMLCTestCase(Generic[T]):
    traces: Tuple[str]
    expected: T


@dataclass
class BaseCaseTestCase(IMLCTestCase[ProcessTree | None]):
    pass


def test_basecase(
    case: BaseCaseTestCase, basecase: Type[BaseCase[IMLCDataStructureUVCL]]
):
    uvcl = _expand_traces(case.traces)
    data = IMLCDataStructureUVCL(uvcl)
    result = basecase.apply(data)
    assert result == case.expected


@dataclass
class CutTestCase(IMLCTestCase[list[IMLCDataStructureUVCL]]):
    pass


def test_cut(case: CutTestCase, cut: Type[Cut[IMLCDataStructureUVCL]]):
    uvcl = _expand_traces(case.traces)
    data = IMLCDataStructureUVCL(uvcl)
    result = cut.apply(data)
    assert result == case.expected


def _expand_traces(traces: Tuple[str]):
    d = dict()
    for t in traces:
        d[tuple(t.split(", "))] = 1
    return Counter(d)
