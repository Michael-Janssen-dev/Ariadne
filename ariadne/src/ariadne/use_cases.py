from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd
from tqdm import tqdm

from ariadne.domain.models.conformance import ConformanceResult
from ariadne.domain.models.traces import TraceLogFactory
from ariadne.storage import ModelStorage


def _mine_one(args):
    miner_name, activity_name, group = args
    from ariadne.infrastructure.plugin_registry import mining_registry

    miner = mining_registry[miner_name]({})
    model = miner.mine_process(group)
    return activity_name, model


def process_trace_data(df: pd.DataFrame, miner_name: str, *, storage: ModelStorage):
    """
    Process trace data using a specified mining algorithm and output the result.
    Args:
        df: DataFrame containing trace data
        miner: The mining algorithm to use
    """
    traces = TraceLogFactory.from_dataframe(df)
    preprocessed = traces.preprocess()
    storage.ensure_empty()

    tasks = (
        (miner_name, activity_name, group)
        for activity_name, group in preprocessed.group_by_parent_activity()
    )

    with ProcessPoolExecutor() as pool:
        futures = [pool.submit(_mine_one, task) for task in tasks]
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
        ):
            activity_name, model = future.result()
            service_name, name = activity_name
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


def _check_one(args):
    algorithm_name, model, activity_name, group = args
    from ariadne.infrastructure.plugin_registry import conformance_registry

    algorithm = conformance_registry[algorithm_name]({})

    if model is None:
        return activity_name, None
    result = algorithm.check_conformance(model, group)
    return activity_name, result


def check_conformance(
    log: pd.DataFrame,
    algorithm_name: str,
    *,
    model_storage: ModelStorage,
) -> dict[str, ConformanceResult]:
    traces = TraceLogFactory.from_dataframe(log)
    preprocessed = traces.preprocess()

    tasks = (
        (
            algorithm_name,
            model_storage.load_model(activity_name[0], activity_name[1]),
            activity_name,
            group,
        )
        for activity_name, group in preprocessed.group_by_parent_activity()
    )

    results = {}
    with ProcessPoolExecutor() as pool:
        futures = [pool.submit(_check_one, task) for task in tasks]

        for future in tqdm(
            as_completed(futures),
            total=len(futures),
        ):
            activity_name, result = future.result()
            results[activity_name] = result
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
