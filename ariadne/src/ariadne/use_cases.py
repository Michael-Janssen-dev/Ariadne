from ariadne.domain.models.traces import TraceLogFactory
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
