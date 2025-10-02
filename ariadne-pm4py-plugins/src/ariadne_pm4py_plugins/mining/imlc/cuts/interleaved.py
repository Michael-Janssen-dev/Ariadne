from typing import Any, Optional, Collection
from pm4py.objects.process_tree.obj import ProcessTree, Operator
from pm4py.algo.discovery.inductive.cuts.abc import Cut
from ..dtypes.imlc import IMLCDataStructureUVCL
from pm4py.objects.dfg import util as dfu
from ..util import merge


class NonAtomicInterleavedCut(Cut[IMLCDataStructureUVCL]):
    @classmethod
    def operator(cls, parameters=None) -> ProcessTree:
        return ProcessTree(operator=Operator.INTERLEAVING)

    @classmethod
    def holds(
        cls, obj: IMLCDataStructureUVCL, parameters=None
    ) -> Optional[list[Collection[Any]]]:
        dfg = obj.dfg
        alphabet = dfu.get_vertices(dfg)
        groups = [{a} for a in alphabet]
        for a in alphabet:
            if not dfg.start_activities[a]:
                for b in alphabet:
                    if dfg.graph[(b, a)]:
                        merge(groups, a, b)
        for a in alphabet:
            if not dfg.end_activities[a]:
                for b in alphabet:
                    if dfg.graph[(a, b)]:
                        merge(groups, a, b)
        for a in dfg.start_activities:
            for b in dfg.end_activities:
                if not dfg.graph[(a, b)]:
                    merge(groups, a, b)
