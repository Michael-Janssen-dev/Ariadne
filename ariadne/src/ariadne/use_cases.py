import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
from tqdm import tqdm

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
        for activity_name, model in pool.map(_mine_one, tasks, chunksize=4):
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
):
    traces = TraceLogFactory.from_dataframe(log)
    preprocessed = traces.preprocess()

    # Skip groups with no corresponding model up front
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
    total = preprocessed.data["parent_activity_name"].nunique()
    t = tqdm(total=int(total))
    with ProcessPoolExecutor() as pool:
        for activity_name, result in pool.map(_check_one, tasks, chunksize=4):
            if result is not None:
                results[activity_name] = result
            t.update(1)
    t.close()
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
