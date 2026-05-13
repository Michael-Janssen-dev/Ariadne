from collections import Counter
from copy import copy
from typing import Any, List, Optional, Tuple

from pm4py.algo.discovery.inductive.variants.abc import InductiveMinerFramework
from pm4py.objects.dfg.obj import DFG
from pm4py.objects.process_tree.obj import ProcessTree
from pm4py.objects.process_tree.utils import generic as pt_util
from pm4py.objects.process_tree.utils.generic import tree_sort
from pm4py.util.compression.dtypes import UVCL

from .base_cases.factory import IMLCBaseCaseFactory
from .cuts.factory import IMLCCutFactory
from .dtypes.imlc import IMLCDataStructureUVCL
from .fall_through.empty_traces import NonAtomicEmptyTracesUVCL
from .fall_through.factory import IMLCFallThroughFactory
from .util import base, is_start


class IMLC(InductiveMinerFramework[IMLCDataStructureUVCL]):
    def apply_base_cases(
        self, obj: IMLCDataStructureUVCL, parameters: dict[str, Any] | None = None
    ) -> ProcessTree | None:
        return IMLCBaseCaseFactory.apply_base_cases(obj, None, parameters=parameters)

    def find_cut(
        self, obj: IMLCDataStructureUVCL, parameters: dict[str, Any] | None = None
    ) -> ProcessTree | None:
        return IMLCCutFactory.find_cut(obj, None, parameters=parameters)

    def fall_through(
        self, obj: Any, parameters: dict[str, Any] | None = None
    ) -> Tuple[ProcessTree, List]:
        return IMLCFallThroughFactory.fall_through(
            obj, None, None, None, parameters=parameters
        )

    def instance(self):
        return None


class IMFLC(IMLC):
    def apply(
        self,
        obj: IMLCDataStructureUVCL,
        parameters: Optional[dict[str, Any]] = None,
        second_iteration=False,
    ) -> ProcessTree:
        noise_threshold = (
            parameters["NOISE_THRESHOLD"]
            if parameters and "NOISE_THRESHOLD" in parameters
            else 0.01
        )

        empty_traces = NonAtomicEmptyTracesUVCL.apply(obj, parameters)
        if empty_traces is not None and empty_traces[1]:
            number_original_traces = sum(y for y in obj.data_structure.values())
            number_filtered_traces = sum(
                y for y in empty_traces[1][1].data_structure.values()
            )

            if (
                number_original_traces - number_filtered_traces
                > noise_threshold * number_original_traces
            ):
                return self._recurse(empty_traces[0], empty_traces[1], parameters)
            else:
                obj = empty_traces[1][1]

        obj = self.__filter_dfg_noise(obj, noise_threshold)

        tree = self.apply_base_cases(obj, parameters)
        if tree is None:
            cut = self.find_cut(obj, parameters)
            if cut is not None:
                _is_complete(cut[1])
                tree = self._recurse(cut[0], cut[1], parameters=parameters)
            if tree is None:
                if not second_iteration:
                    # filtered_ds = self.__filter_dfg_noise(obj, noise_threshold)
                    # tree = self.apply(filtered_ds, parameters, second_iteration=True)
                    # if tree is None:
                    ft = self.fall_through(obj, parameters)
                    tree = self._recurse(ft[0], ft[1], parameters=parameters)
        return tree

    def __filter_dfg_noise(self, obj, noise_threshold):
        start_activities = copy(obj.dfg.start_activities)
        end_activities = copy(obj.dfg.end_activities)
        dfg = copy(obj.dfg.graph)
        outgoing_max_occ = {}
        for x, y in dfg.items():
            act = x[0]
            if act not in outgoing_max_occ:
                outgoing_max_occ[act] = y
            else:
                outgoing_max_occ[act] = max(y, outgoing_max_occ[act])
            if act in end_activities:
                outgoing_max_occ[act] = max(outgoing_max_occ[act], end_activities[act])
        dfg_list = sorted(
            [(x, y) for x, y in dfg.items()], key=lambda x: (x[1], x[0]), reverse=True
        )
        dfg_list = [
            x for x in dfg_list if x[1] > noise_threshold * outgoing_max_occ[x[0][0]]
        ]
        dfg_list = [x[0] for x in dfg_list]
        # filter the elements in the DFG
        graph = {x: y for x, y in dfg.items() if x in dfg_list}

        dfg = DFG()
        for sa in start_activities:
            dfg.start_activities[sa] = start_activities[sa]
        for ea in end_activities:
            dfg.end_activities[ea] = end_activities[ea]
        for act in graph:
            dfg.graph[act] = graph[act]

        return IMLCDataStructureUVCL(obj.data_structure, dfg)


def _is_complete(cut):
    for group in cut:
        for trace in group.data_structure:
            started = []
            for event in trace:
                if is_start(event):
                    started.append(base(event))
                else:
                    if base(event) not in started:
                        raise Exception("Trace is not complete")
                    started.remove(base(event))


def refine_labels(uvcl: UVCL) -> UVCL:
    """
    Relabel activities that are concurrent to itself
    """
    return uvcl
    new_uvcl = Counter()
    for trace in uvcl:
        new_trace = list()
        open_activities = dict()
        for event in trace:
            if is_start(event):
                if open_activities.get(base(event), 0) > 0:
                    # relabel
                    new_event = f"{event}/{open_activities[base(event)]}"
                    new_trace.append(new_event)
                else:
                    new_trace.append(event)

                open_activities[base(event)] = open_activities.get(base(event), 0) + 1
            else:
                if base(event) not in open_activities:
                    raise Exception("Trace is not complete")
                open_activities[base(event)] -= 1
                if open_activities[base(event)] > 0:
                    new_trace.append(f"{event}/{open_activities[base(event)]}")
                else:
                    new_trace.append(event)
        new_uvcl[tuple(new_trace)] = uvcl[trace]
    return new_uvcl


def discover_petri_net_inductive_lifecycle(uvcl: UVCL):
    uvcl = refine_labels(uvcl)
    im = IMFLC(None)
    data = IMLCDataStructureUVCL(uvcl)
    tree = im.apply(data, parameters=None)
    tree = pt_util.fold(tree)
    tree_sort(tree)
    return tree
