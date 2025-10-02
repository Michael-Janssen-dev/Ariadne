from collections import Counter
from typing import Collection, Any, Optional, Tuple

from pm4py.algo.discovery.inductive.cuts.sequence import SequenceCutUVCL
from pm4py.algo.discovery.inductive.dtypes.im_ds import IMDataStructureUVCL

from ..dtypes.imlc import IMLCDataStructureUVCL
from ..util import is_end, base, is_start


class NonAtomicSequenceCutUVCL(SequenceCutUVCL):
    @classmethod
    def holds(
        cls, obj: IMLCDataStructureUVCL, parameters: Optional[dict[str, Any]] = None
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
        cls,
        obj: IMLCDataStructureUVCL,
        groups: list[Collection[Any]],
        parameters: Optional[dict[str, Any]] = None,
    ) -> list[IMDataStructureUVCL]:
        logs = [Counter() for g in groups]
        for t in obj.data_structure:
            i = 0
            split_point = 0
            act_union = set()
            while i < len(groups):
                new_split_point = cls._find_split_point(
                    t, groups[i], split_point, act_union
                )
                trace_i = tuple()
                j = split_point
                started = []
                ended = []
                while j < new_split_point:
                    base_activity = base(t[j])
                    if base_activity in groups[i]:
                        if is_start(t[j]):
                            if base_activity not in ended:
                                started.append(base_activity)
                            else:
                                ended.append(base_activity)
                        else:
                            if base_activity not in started:
                                ended.append(base_activity)
                            else:
                                started.remove(base_activity)
                        trace_i = trace_i + (t[j],)
                    j = j + 1
                while len(started) > 0:
                    # We find the closest corresponding end activity
                    if is_end(t[j]) and base(t[j]) in started:
                        trace_i = trace_i + (t[j],)
                        started.remove(base(t[j]))
                    j += 1
                j = split_point
                while len(ended) > 0:
                    if is_start(t[j]) and base(t[j]) in ended:
                        trace_i = (t[j],) + trace_i
                        ended.remove(base(t[j]))
                    j -= 1
                logs[i].update({trace_i: obj.data_structure[t]})
                split_point = new_split_point
                act_union = act_union.union(set(groups[i]))
                i = i + 1
        return list(map(lambda l: IMLCDataStructureUVCL(l), logs))

    @classmethod
    def _find_split_point(
        cls,
        t: Tuple[Any],
        group: Collection[Any],
        start: int,
        ignore: Collection[Any],
        parameters: Optional[dict[str, Any]] = None,
    ) -> int:
        least_cost = 0
        position_with_least_cost = start
        cost = 0
        i = start
        while i < len(t):
            if base(t[i]) in group:
                cost = cost - 1
            elif base(t[i]) not in ignore:
                cost = cost + 1
            if cost < least_cost:
                least_cost = cost
                position_with_least_cost = i + 1
            i = i + 1
        return position_with_least_cost
