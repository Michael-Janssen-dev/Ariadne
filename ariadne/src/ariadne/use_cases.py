from ariadne.domain.models.process_model import EndpointModel
from ariadne.domain.models.traces import TraceLogFactory
from ariadne.domain.plugins import ConformanceChecker
from ariadne.storage import ModelStorage
import pandas as pd


def process_trace_data(df: pd.DataFrame, miner_name: str, *, storage: ModelStorage):
    """
    Process trace data using a specified mining algorithm and output the result.
    Args:
        df: DataFrame containing trace data
        miner: The mining algorithm to use (e.g., "inductive", "heuristic")
    """
    traces = TraceLogFactory.from_dataframe(df)
    preprocessed = traces.preprocess()
    storage.ensure_empty()

    from ariadne.infrastructure.plugin_registry import mining_registry

    miner = mining_registry[miner_name]({})
    for (service_name, name), group in preprocessed.group_by_parent_activity():
        model = miner.mine_process(group)
        storage.save_model(service_name, name, model, miner_name)


def convert_elastic_csv_to_otel(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert an Elastic APM CSV export to OTEL-compatible CSV format.

    Args:
        df: DataFrame containing Elastic APM trace data
    Returns:
        DataFrame in OTEL format
    """
    from ariadne.domain.services.convert.elastic import convert_elastic_csv_to_otel

    return convert_elastic_csv_to_otel(df)


def check_conformance(
    log: pd.DataFrame, algorithm_name: str, *, model_storage: ModelStorage
):
    """
    Check the conformance of a process model against trace data using a specified conformance checker.

    Args:
        log: DataFrame containing trace data
        algorithm: The conformance checking algorithm to use
        model_storage: Storage containing the process models
    Returns:
        List of conformance results for each model
    """
    from ariadne.infrastructure.plugin_registry import conformance_registry

    traces = TraceLogFactory.from_dataframe(log)
    preprocessed = traces.preprocess()
    results = {}

    algorithm = conformance_registry[algorithm_name]({})

    for (service_name, name), group in preprocessed.group_by_parent_activity():
        pnml = model_storage.load_model(service_name, name)
        if pnml is None:
            continue
        model = EndpointModel(pnml_content=pnml, dot_content="")
        result = algorithm.check_conformance(model, group)
        results[(service_name, name)] = result

    return results
