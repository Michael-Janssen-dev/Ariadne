from ariadne.domain.models.process_model import EndpointModel
from ariadne.domain.models.conformance import ConformanceResult
from ariadne.domain.models.traces import EndpointChildSpans
from ariadne.domain.plugins import ConformanceChecker


class PM4PYConformanceChecker(ConformanceChecker):
    name = "pm4py_conformance_checker"
    display_name = "PM4PY Conformance Checker"
    description = "Conformance checking using PM4PY"
    license = "AGPL-3.0"

    def check_conformance(
        self, model: EndpointModel, traces: EndpointChildSpans
    ) -> ConformanceResult:
        from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
        from pm4py.objects.petri_net.importer.variants.pnml import (
            import_net_from_string,
        )
        from pm4py import format_dataframe

        # Convert Traces to PM4PY event log
        event_log = traces.data

        event_log = format_dataframe(
            event_log,
            case_id="trace_id",
            activity_key="activity_name",
            timestamp_key="end_time",
        )

        # Convert ProcessModel to PM4PY Petri net
        petri_net, initial_marking, final_marking = import_net_from_string(
            model.pnml_content
        )

        # Perform token-based replay conformance checking
        replayed_traces = token_replay.apply(
            event_log,
            petri_net,
            initial_marking,
            final_marking,
            parameters={"show_progress_bar": False},
        )

        total_traces = len(replayed_traces)
        fitting_traces = sum(1 for trace in replayed_traces if trace["trace_is_fit"])
        fitness = fitting_traces / total_traces if total_traces > 0 else 1.0

        return ConformanceResult(fitness=fitness)
