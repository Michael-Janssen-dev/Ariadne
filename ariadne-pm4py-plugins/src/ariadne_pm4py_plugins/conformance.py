import os

import pandas as pd
from pm4py.objects.petri_net.obj import PetriNet

from ariadne_pm4py_plugins.mining.layered.algorithm import merge_lifecycles

os.environ["PM4PY_SHOW_PROGRESS_BAR"] = "False"
import pm4py
from ariadne.domain.models.conformance import ConformanceResult
from ariadne.domain.models.process_model import EndpointModel
from ariadne.domain.models.traces import EndpointChildSpans
from ariadne.domain.plugins import ConformanceChecker
from pm4py.objects.petri_net.utils.petri_utils import (
    add_arc_from_to,
    add_place,
    add_transition,
    remove_transition,
)


def _expand_lifecycle_activities(net: PetriNet) -> PetriNet:
    for transition in list(net.transitions):
        if transition.label is None:
            continue
        start = add_transition(net, "S " + transition.name, "S " + transition.label)
        for arc in transition.in_arcs:
            add_arc_from_to(arc.source, start, net)

        end = add_transition(net, "E " + transition.name, "E " + transition.label)
        for arc in transition.out_arcs:
            add_arc_from_to(end, arc.target, net)

        middle = add_place(net, transition.name)
        add_arc_from_to(start, middle, net)
        add_arc_from_to(middle, end, net)

        remove_transition(net, transition)
    return net


class PM4PYConformanceChecker(ConformanceChecker):
    name = "pm4py"
    description = "Conformance checking using PM4PY"
    license = "AGPL-3.0"

    def check_conformance(
        self, model: EndpointModel, traces: EndpointChildSpans
    ) -> ConformanceResult:
        from pm4py import format_dataframe
        from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
        from pm4py.objects.petri_net.importer.variants.pnml import (
            import_net_from_string,
        )

        # Convert Traces to PM4PY event log
        event_log = traces.data

        event_log = merge_lifecycles(event_log)

        event_log = format_dataframe(
            event_log,
            case_id="case_id",
            activity_key="activity_name",
            timestamp_key="time",
        )

        event_log["time:timestamp"] = pd.to_datetime(
            event_log["time:timestamp"], unit="us"
        )

        # Convert ProcessModel to PM4PY Petri net
        petri_net, initial_marking, final_marking = import_net_from_string(
            model.pnml_content
        )

        petri_net = _expand_lifecycle_activities(petri_net)

        # Perform token-based replay conformance checking
        replayed_traces = token_replay.apply(
            event_log,
            petri_net,
            initial_marking,
            final_marking,
            parameters={"show_progress_bar": False},
        )

        size = event_log.groupby("case_id").size()
        if not size[size > 500].empty:
            precision = -2.0
        else:
            precision = pm4py.precision_token_based_replay(
                event_log,
                petri_net,
                initial_marking,
                final_marking,
            )

        simplicity = pm4py.simplicity_petri_net(
            petri_net, initial_marking, final_marking
        )
        generalization = pm4py.generalization_tbr(
            event_log, petri_net, initial_marking, final_marking
        )

        total_traces = len(replayed_traces)
        fitting_traces = sum(1 for trace in replayed_traces if trace["trace_is_fit"])
        fitness = fitting_traces / total_traces if total_traces > 0 else 1.0

        return ConformanceResult(
            fitness=fitness,
            precision=precision,
            simplicity=simplicity,
            generalization=generalization,
        )
