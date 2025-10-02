from collections import Counter
from typing import Any, Optional, Collection
from pm4py.objects.process_tree.obj import ProcessTree, Operator
from pm4py.algo.discovery.inductive.cuts.abc import Cut
from ..dtypes.imlc import IMLCDataStructureUVCL
from pm4py.objects.dfg import util as dfu
from ..util import base


class NonAtomicConcurrentCut(Cut[IMLCDataStructureUVCL]):
    @classmethod
    def operator(cls, parameters=None) -> ProcessTree:
        return ProcessTree(operator=Operator.PARALLEL)

    @classmethod
    def holds(
        cls, obj: IMLCDataStructureUVCL, parameters=None
    ) -> Optional[list[Collection[Any]]]:
        if () in obj.data_structure:
            return None
        dfg = obj.dfg
        alphabet = dfu.get_vertices(dfg)
        groups = [{a} for a in alphabet]
        i = 0
        while i < len(groups) - 1 and len(groups) > 1:
            done = False
            for j in range(i + 1, len(groups)):
                for a in groups[i]:
                    for b in groups[j]:
                        if not obj.concurrency_graph[(a, b)] and (
                            not dfg.graph[(a, b)] or not dfg.graph[(b, a)]
                        ):
                            groups[i].update(groups[j])
                            del groups[j]
                            done = True
                            break
                    if done:
                        break
                if done:
                    break
            if not done:
                i += 1
        groups = list(sorted(groups, key=lambda g: len(g)))
        i = 0
        while i < len(groups) and len(groups) > 1:
            if (
                len(groups[i].intersection(set(dfg.start_activities.keys()))) > 0
                and len(groups[i].intersection(set(dfg.end_activities.keys()))) > 0
            ):
                i += 1
                continue
            group = groups[i]
            del groups[i]
            if i == 0:
                groups[i].update(group)
            else:
                groups[i - 1].update(group)
        if len(groups) == 1:
            return None
        return groups

    @classmethod
    def project(
        cls, obj: IMLCDataStructureUVCL, groups: list[Collection[Any]], parameters=None
    ) -> list[IMLCDataStructureUVCL]:
        uvcls = []
        for group in groups:
            uvcl = Counter()
            for trace in obj.data_structure:
                filtered = tuple(e for e in trace if base(e) in group)
                uvcl[filtered] += obj.data_structure[trace]
            uvcls.append(IMLCDataStructureUVCL(uvcl))
        return uvcls
