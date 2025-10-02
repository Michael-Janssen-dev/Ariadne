from typing import Any, Optional, Tuple
from pm4py.objects.process_tree.obj import ProcessTree, Operator
from pm4py.algo.discovery.inductive.fall_through.abc import FallThrough

from ..dtypes.imlc import IMLCDataStructureUVCL
from ..util import base


class SingleActivityTauLoop(FallThrough[IMLCDataStructureUVCL]):
    @classmethod
    def holds(
        cls, obj: IMLCDataStructureUVCL, parameters: Optional[dict[str, Any]] = None
    ) -> bool:
        for t in obj.data_structure:
            for e in t:
                if base(e) != base(t[0]):
                    return False
        return True

    @classmethod
    def apply(
        cls, obj: IMLCDataStructureUVCL, parameters=None
    ) -> Optional[Tuple[ProcessTree, list[IMLCDataStructureUVCL]]]:
        if not cls.holds(obj, parameters):
            return None
        for t in obj.data_structure:
            return ProcessTree(
                operator=Operator.LOOP,
                children=[ProcessTree(label=base(t[0])), ProcessTree()],
            ), []
