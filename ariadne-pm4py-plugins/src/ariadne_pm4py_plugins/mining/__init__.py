import xml.etree.ElementTree as ET
from ariadne.domain.models.process_model import EndpointModel
from ariadne.domain.models.traces import EndpointChildSpans
from ariadne.domain.plugins import MiningAlgorithm
from ariadne_pm4py_plugins.mining.imlc.algorithm import (
    discover_petri_net_inductive_lifecycle,
)
import pm4py
from .layered.algorithm import (
    MinerVariants,
    _get_uvcl,
    merge_lifecycles,
)
from pm4py.algo.discovery.inductive.algorithm import Variants as InductiveVariants
from pm4py.convert import convert_to_petri_net
from pm4py.objects.petri_net.exporter.variants.pnml import export_petri_tree
from pm4py.visualization.bpmn import visualizer as bpmn_visualizer
from pm4py.algo.discovery.inductive import algorithm as inductive


class PM4PyMiningAlgorithm(MiningAlgorithm):
    name: str = "pm4py_mining_algorithm"
    display_name: str = "PM4Py Mining Algorithm"
    description: str = "A mining algorithm implemented using PM4Py."
    license: str = "AGPL-3.0"

    def mine_process(self, traces: EndpointChildSpans) -> EndpointModel:
        """
        Mine a process model from the given traces using PM4Py.
        """
        variant = self.config.get("variant", "IMlc")
        try:
            miner_variant = MinerVariants[variant]
        except KeyError:
            try:
                miner_variant = InductiveVariants[variant.upper()]
            except KeyError:
                raise ValueError(f"Unknown miner variant: {variant}")

        if isinstance(miner_variant, MinerVariants):
            match miner_variant:
                case MinerVariants.IMlc:
                    child_spans = merge_lifecycles(traces.data)
                    formatted = pm4py.format_dataframe(
                        child_spans,
                        case_id="trace_id",
                        activity_key="activity_name",
                        timestamp_key="time",
                    )
                    uvcl = _get_uvcl(formatted, total_cases=traces.total_traces)
                    tree = discover_petri_net_inductive_lifecycle(uvcl)
                case _:
                    raise ValueError(f"Unknown miner variant: {miner_variant}")
        elif isinstance(miner_variant, InductiveVariants):
            formatted = pm4py.format_dataframe(
                traces.data,
                case_id="trace_id",
                activity_key="activity_name",
                timestamp_key="time",
            )
            uvcl = _get_uvcl(formatted, total_cases=traces.total_traces)
            tree = inductive.apply(uvcl, variant=miner_variant)
        else:
            raise ValueError(f"Unknown miner variant: {miner_variant}")
        petri_net, im, fm = convert_to_petri_net(tree)
        pnml_tree: ET.ElementTree = export_petri_tree(petri_net, im, fm)
        pnml = ET.tostring(pnml_tree.getroot(), encoding="utf-8").decode("utf-8")  # type: ignore
        bpmn = pm4py.convert_to_bpmn(petri_net, im, fm)  # type: ignore
        dot = bpmn_visualizer.apply(bpmn).source
        return EndpointModel(pnml_content=pnml, dot_content=dot)
