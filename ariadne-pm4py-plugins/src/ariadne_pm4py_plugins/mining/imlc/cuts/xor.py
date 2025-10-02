from collections import Counter
from typing import Collection, Any, Optional

from pm4py.algo.discovery.inductive.cuts.abc import T
from pm4py.algo.discovery.inductive.cuts.xor import ExclusiveChoiceCut

from ..dtypes.imlc import IMLCDataStructureUVCL
from ..util import base

"""
Same algorithm as normal exclusive choice, but split in the right way
"""


class NonAtomicExclusiveChoiceCutUVCL(ExclusiveChoiceCut[IMLCDataStructureUVCL]):
    @classmethod
    def holds(
        cls, obj: T, parameters: Optional[dict[str, Any]] = None
    ) -> Optional[list[Collection[Any]]]:
        if () in obj.data_structure:
            return None
        groups = super().holds(obj, parameters)
        if groups is None:
            return None
        while True:
            new_groups, changed = cls.merge_concurrent_groups(obj, groups)
            if not changed:
                break
            groups = new_groups
        if len(groups) == 1:
            return None
        return groups

    @classmethod
    def merge_concurrent_groups(cls, obj, groups):
        changed = False
        i = 0
        while i < len(groups) - 1 and len(groups) > 1:
            concurrent = False
            for a in groups[i]:
                for b in groups[i + 1]:
                    if obj.concurrency_graph[(a, b)]:
                        concurrent = True
                        break
                if concurrent:
                    break
            if concurrent:
                groups[i].update(groups[i + 1])
                del groups[i + 1]
                changed = True
            else:
                i += 1
        return groups, changed

    @classmethod
    def project(
        cls, obj: IMLCDataStructureUVCL, groups: list[Collection[Any]], parameters=None
    ) -> list[IMLCDataStructureUVCL]:
        """
        Also handles deviating traces.
        """
        logs = [Counter() for _ in groups]
        for t in obj.data_structure:
            count = {i: 0 for i in range(len(groups))}
            for index, group in enumerate(groups):
                for e in t:
                    if base(e) in group:
                        count[index] += 1
            count = sorted(
                list((x, y) for x, y in count.items()),
                key=lambda x: (x[1], x[0]),
                reverse=True,
            )
            new_trace = tuple()
            for e in t:
                if base(e) in groups[count[0][0]]:
                    new_trace = new_trace + (e,)
            logs[count[0][0]].update({new_trace: obj.data_structure[t]})
        return list(map(lambda l: IMLCDataStructureUVCL(l), logs))
