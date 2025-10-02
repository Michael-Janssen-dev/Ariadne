from collections import Counter
from typing import Any, Optional, Tuple
from pm4py.objects.process_tree.obj import ProcessTree, Operator
from pm4py.algo.discovery.inductive.fall_through.abc import FallThrough
from pm4py.util.compression.dtypes import UVCL

from ..dtypes.imlc import IMLCDataStructureUVCL
from ..util import base


class StrictNonAtomicTauLoop(FallThrough[IMLCDataStructureUVCL]):
    @classmethod
    def _get_projected_log(
        cls, obj: IMLCDataStructureUVCL, parameters=None
    ) -> UVCL | None:
        start_activities = obj.dfg.start_activities
        end_activities = obj.dfg.end_activities
        log = obj.data_structure
        proj = Counter()
        for t in log:
            x = 0
            for i in range(1, len(t)):
                if base(t[i]) in start_activities and base(t[i - 1]) in end_activities:
                    if not cls._is_consistent(t[x:i]):
                        return None
                    proj.update({t[x:i]: log[t]})
                    x = i
            proj.update({t[x : len(t)]: log[t]})
        return proj

    @classmethod
    def _is_consistent(cls, trace: Tuple[str]) -> bool:
        started = set()
        for i in range(len(trace)):
            if trace[i].startswith("S"):
                started.add(trace[i][2:])
            else:
                if trace[i][2:] in started:
                    started.remove(trace[i][2:])
                else:
                    return False
        return len(started) == 0

    @classmethod
    def holds(
        cls, obj: IMLCDataStructureUVCL, parameters: Optional[dict[str, Any]] = None
    ) -> bool:
        projected = cls._get_projected_log(obj, parameters=parameters)
        if projected is None:
            return False
        return sum(projected.values()) > sum(obj.data_structure.values())

    @classmethod
    def apply(
        cls, obj: IMLCDataStructureUVCL, parameters=None
    ) -> Optional[Tuple[ProcessTree, list[IMLCDataStructureUVCL]]]:
        log = obj.data_structure
        projected = cls._get_projected_log(obj, parameters=parameters)
        if projected is None:
            return None
        if sum(projected.values()) > sum(log.values()):
            return ProcessTree(operator=Operator.LOOP), [
                IMLCDataStructureUVCL(projected),
                IMLCDataStructureUVCL(Counter()),
            ]
