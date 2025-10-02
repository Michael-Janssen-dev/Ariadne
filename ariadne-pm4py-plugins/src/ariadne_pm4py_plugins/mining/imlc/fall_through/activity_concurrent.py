from collections import Counter
from typing import Any, Optional, Tuple
from pm4py.objects.process_tree.obj import ProcessTree, Operator
from pm4py.algo.discovery.inductive.fall_through.abc import FallThrough
from pm4py.util.compression.dtypes import UVCL
from pm4py.util.compression import util as comut
from ..dtypes.imlc import IMLCDataStructureUVCL
from ..cuts.factory import IMLCCutFactory
from ..util import base


class ActivityConcurrent(FallThrough[IMLCDataStructureUVCL]):
    MULTI_PROCESSING_LOWER_BOUND = 20

    @classmethod
    def _process_candidate(
        cls, c: Any, log: UVCL, parameters: Optional[dict[str, Any]] = None
    ):
        l_alt = Counter()
        for t in log:
            l_alt[tuple(filter(lambda e: base(e) != c, t))] = log[t]
        cut = cls._find_cut(IMLCDataStructureUVCL(l_alt), parameters=parameters)
        return cut if cut is not None else None

    @classmethod
    def _get_candidate(
        cls, obj: IMLCDataStructureUVCL, parameters: Optional[dict[str, Any]] = None
    ) -> Optional[Any]:
        if parameters is None:
            parameters = {}

        log = obj.data_structure
        candidates = sorted(set(base(x) for x in comut.get_alphabet(log)))
        for a in candidates:
            cut = cls._process_candidate(a, log, parameters=parameters)
            if cut is not None:
                return a
        return None

    @classmethod
    def _find_cut(
        cls, obj: IMLCDataStructureUVCL, parameters: Optional[dict[str, Any]] = None
    ) -> Optional[Tuple[ProcessTree, list[IMLCDataStructureUVCL]]]:
        for c in IMLCCutFactory.get_cuts(obj, None, parameters=parameters):
            r = c.apply(obj, parameters)
            if r is not None:
                return r
        return None

    @classmethod
    def holds(
        cls, obj: IMLCDataStructureUVCL, parameters: Optional[dict[str, Any]] = None
    ) -> bool:
        return cls._get_candidate(obj, parameters) is not None

    @classmethod
    def apply(
        cls, obj: IMLCDataStructureUVCL, parameters: Optional[dict[str, Any]] = None
    ) -> Optional[Tuple[ProcessTree, list[IMLCDataStructureUVCL]]]:
        candidate = cls._get_candidate(obj, parameters)
        if candidate is None:
            return None
        log = obj.data_structure
        l_a = Counter()
        l_other = Counter()
        for t in log:
            l_a.update({tuple(filter(lambda e: base(e) == candidate, t)): log[t]})
            l_other.update({tuple(filter(lambda e: base(e) != candidate, t)): log[t]})
        return ProcessTree(operator=Operator.PARALLEL), [
            IMLCDataStructureUVCL(l_a),
            IMLCDataStructureUVCL(l_other),
        ]
