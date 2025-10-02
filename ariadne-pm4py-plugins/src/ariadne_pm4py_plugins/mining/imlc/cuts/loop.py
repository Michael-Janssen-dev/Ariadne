from collections import Counter
from typing import Collection, Any, Optional, Tuple

from pm4py.objects.dfg.obj import DFG

from ..dtypes.imlc import IMLCDataStructureUVCL
from pm4py.algo.discovery.inductive.cuts.loop import LoopCut
from pm4py.util import nx_utils
from pm4py.objects.dfg import util as dfu
from pm4py.util.compression.dtypes import UVCL

from ..util import base


class NonAtomicLoopCutUVCL(LoopCut[IMLCDataStructureUVCL]):
    @classmethod
    def holds(cls, obj: IMLCDataStructureUVCL, parameters=None):
        """
        Finds a loop cut in the DFG and returns exactly two groups:
        - groups[0]: the 'do' group (start ∪ end activities plus merged components as per checks)
        - groups[1]: a single 'redo' group obtained by merging all remaining non-empty groups

        If no non-empty redo part remains, returns None.
        """
        dfg = obj.dfg
        start_activities = set(dfg.start_activities.keys())
        end_activities = set(dfg.end_activities.keys())
        if len(dfg.graph) == 0:
            return None

        # Initial groups: do-part is start ∪ end; other parts are connected components after removing boundaries
        groups = [start_activities.union(end_activities)]
        for c in cls._compute_connected_components_concurrent(
            dfg, start_activities, end_activities, obj.concurrency_graph
        ):
            groups.append(set(c.nodes))

        # Apply the original reachability/completeness checks
        groups = cls._exclude_sets_non_reachable_from_start(
            dfg, start_activities, end_activities, groups
        )
        groups = cls._exclude_sets_no_reachable_from_end(
            dfg, start_activities, end_activities, groups
        )
        groups = cls._check_start_completeness(
            dfg, start_activities, end_activities, groups
        )
        groups = cls._check_end_completeness(
            dfg, start_activities, end_activities, groups
        )

        # Keep only non-empty groups
        groups = [set(g) for g in groups if len(g) > 0]

        # Require at least a do group and something to redo
        if len(groups) <= 1:
            return None

        # Merge all remaining non-empty groups (from the second to the last) into a single redo group
        redo_merged = set()
        for g in groups[1:]:
            redo_merged.update(g)

        return [set(groups[0]), redo_merged]

    @classmethod
    def _compute_connected_components_concurrent(
        cls,
        dfg: DFG,
        start_activities: Collection[Any],
        end_activities: Collection[Any],
        concurrency_graph,
        parameters=None,
    ):
        nxd = dfu.as_nx_graph(dfg)
        for a, b in concurrency_graph:
            nxd.add_edge(a, b)
        [
            nxd.remove_edge(a, b)
            for (a, b) in dfg.graph
            if a in start_activities
            or a in end_activities
            or b in start_activities
            or b in end_activities
        ]
        [nxd.remove_node(a) for a in start_activities if nxd.has_node(a)]
        [nxd.remove_node(a) for a in end_activities if nxd.has_node(a)]
        nxu = nxd.to_undirected()
        return [nxd.subgraph(c).copy() for c in nx_utils.connected_components(nxu)]

    @classmethod
    def project(
        cls,
        obj: IMLCDataStructureUVCL,
        groups: list[Collection[Any]],
        parameters: Optional[dict[str, Any]] = None,
    ) -> list[IMLCDataStructureUVCL]:
        """
        Split the (compressed) log into one 'do' log and N 'redo' logs.
        Traces are segmented into do/redo slices; redo slices are routed to the
        redo log whose activity set overlaps most with the slice.
        """
        do = set(groups[0])
        redo_groups = [set(g) for g in groups[1:]]

        # For quick membership checks
        redo_activities = set().union(*redo_groups) if redo_groups else set()

        do_log = Counter()
        redo_logs = [Counter() for _ in redo_groups]

        for t, card in obj.data_structure.items():
            do_trace: Tuple[Any, ...] = tuple()
            redo_trace: Tuple[Any, ...] = tuple()

            for e in t:
                if base(e) in do:
                    do_trace += (e,)
                    # flush redo if we were inside a redo slice
                    if redo_trace:
                        redo_logs = cls._append_trace_to_redo_log(
                            redo_trace, redo_logs, redo_groups, card
                        )
                        redo_trace = tuple()
                elif base(e) in redo_activities:
                    redo_trace += (e,)
                    # flush do if we were inside a do slice
                    if do_trace:
                        do_log.update({do_trace: card})
                        do_trace = tuple()
                else:
                    # Safety: if an event is in neither do nor any redo group,
                    # flush any current slice and ignore the event
                    if do_trace:
                        do_log.update({do_trace: card})
                        do_trace = tuple()
                    if redo_trace:
                        redo_logs = cls._append_trace_to_redo_log(
                            redo_trace, redo_logs, redo_groups, card
                        )
                        redo_trace = tuple()

            # Flush tail slices
            if redo_trace:
                redo_logs = cls._append_trace_to_redo_log(
                    redo_trace, redo_logs, redo_groups, card
                )
            do_log.update(
                {do_trace: card}
            )  # keep empty do slices, consistent with original

        logs = [do_log] + redo_logs
        return [IMLCDataStructureUVCL(l) for l in logs]

    @classmethod
    def _append_trace_to_redo_log(
        cls,
        redo_trace: Tuple[Any, ...],
        redo_logs: list[UVCL],
        redo_groups: list[Collection[Any]],
        cardinality: int,
        parameters: Optional[dict[str, Any]] = None,
    ) -> list[UVCL]:
        """
        Append a redo slice to the best matching redo log (largest activity overlap).
        """
        if not redo_logs:
            return redo_logs

        activities = set(base(x) for x in redo_trace)
        overlaps = [
            (i, len(activities.intersection(set(redo_groups[i]))))
            for i in range(len(redo_groups))
        ]
        overlaps.sort(key=lambda x: (x[1], x[0]), reverse=True)
        target = overlaps[0][0]
        redo_logs[target].update({redo_trace: cardinality})
        return redo_logs
