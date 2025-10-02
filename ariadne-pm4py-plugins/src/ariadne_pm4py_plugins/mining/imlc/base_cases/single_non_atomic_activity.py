from pm4py.algo.discovery.inductive.base_case.abc import BaseCase
from ..dtypes.imlc import IMLCDataStructureUVCL
from pm4py.objects.process_tree.obj import ProcessTree


class SingleNonAtomicActivityUVCL(BaseCase[IMLCDataStructureUVCL]):
    @classmethod
    def holds(cls, obj: IMLCDataStructureUVCL, parameters=None) -> bool:
        if len(obj.data_structure.keys()) != 1:
            return False
        return (
            len(obj.dfg.graph) == 0
            and len(obj.dfg.start_activities) == 1
            and len(obj.dfg.end_activities) == 1
        )

    @classmethod
    def leaf(cls, obj: IMLCDataStructureUVCL, parameters=None) -> ProcessTree:
        for t in obj.data_structure.keys():
            if t:
                return ProcessTree(label=t[0][2:])
            return ProcessTree()
