import pandas as pd

from ariadne.domain.models.traces import TraceLogFactory
from ariadne.storage import ModelStorage


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
        model = model_storage.load_model(service_name, name)
        if model is None:
            continue
        result = algorithm.check_conformance(model, group)
        results[(service_name, name)] = result

    return results


def list_miners():
    from ariadne.infrastructure.plugin_registry import mining_registry

    return [
        (miner.name, miner.display_name, miner.description)
        for miner in mining_registry.values()
    ]


def list_conformance_checkers():
    from ariadne.infrastructure.plugin_registry import conformance_registry

    return [
        (checker.name, checker.display_name, checker.description)
        for checker in conformance_registry.values()
    ]


def render_visualization_html(model_storage: ModelStorage):
    import os

    from jinja2 import Environment, FileSystemLoader

    # Load the Jinja2 template
    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    template = env.get_template("visualization_template.j2")

    models = {}
    for service_name, endpoint_name in model_storage.list_models():
        model = model_storage.load_model(service_name, endpoint_name)
        if model is None:
            continue
        if service_name not in models:
            models[service_name] = {}
        models[service_name][endpoint_name] = {"dot": model.dot_content}

    # Render the template with the models
    rendered_html = template.render(models=models)

    return rendered_html
