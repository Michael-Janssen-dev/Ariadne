from collections import Counter
from typing import Tuple
from pm4py.objects.process_tree.obj import ProcessTree, Operator
from pm4py.algo.discovery.inductive.fall_through.abc import FallThrough
from ..dtypes.imlc import IMLCDataStructureUVCL
from pm4py.objects.dfg import util as dfu


class NonAtomicActivityOncePerTrace(FallThrough[IMLCDataStructureUVCL]):
    @classmethod
    def holds(cls, obj: IMLCDataStructureUVCL, parameters=None) -> bool:
        alphabet = dfu.get_vertices(obj.dfg)
        for a in alphabet:
            start = "S " + a
            end = "E " + a
            found = True
            for t in obj.data_structure.keys():
                if t.count(start) != 1 or t.count(end) != 1:
                    found = False
                    break
            if found:
                return True
        return False

    @classmethod
    def apply(
        cls, obj: IMLCDataStructureUVCL, pool=None, manager=None, parameters=None
    ) -> Tuple[ProcessTree, list[IMLCDataStructureUVCL]]:
        alphabet = dfu.get_vertices(obj.dfg)
        for a in alphabet:
            start = "S " + a
            end = "E " + a
            found = True
            for t in obj.data_structure.keys():
                if t.count(start) != 1 or t.count(end) != 1:
                    found = False
                    break
            if found:
                uvcl_a = Counter()
                uvcl_other = Counter()
                for trace in obj.data_structure.keys():
                    uvcl_a[
                        tuple(
                            [
                                event
                                for event in trace
                                if event != start and event != end
                            ]
                        )
                    ] += obj.data_structure[trace]
                    uvcl_other[
                        tuple(
                            [event for event in trace if event == start or event == end]
                        )
                    ] += obj.data_structure[trace]
                return ProcessTree(operator=Operator.PARALLEL), [
                    IMLCDataStructureUVCL(uvcl_a),
                    IMLCDataStructureUVCL(uvcl_other),
                ]
        return None
