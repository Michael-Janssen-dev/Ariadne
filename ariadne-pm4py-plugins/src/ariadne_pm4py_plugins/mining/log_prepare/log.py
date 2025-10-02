import os
import pickle

import pandas as pd


def S(activity):
    return "S " + activity


def E(activity):
    return "E " + activity


def is_start(activity: str) -> bool:
    return activity.startswith("S ")


def is_end(activity: str) -> bool:
    return activity.startswith("E ")


def prepare_log_cached(
    df: pd.DataFrame, cache_key: str, update_top_level_activity=False
):
    log_file = os.path.join(f"cache/{cache_key}-prepared.csv")
    mapping_file = os.path.join(f"cache/{cache_key}-mapping.pkl")
    if os.path.exists(log_file) and os.path.exists(mapping_file):
        return pd.read_csv(log_file), pickle.load(open(mapping_file, "rb"))
    log, mapping = prepare_log(df, update_top_level_activity=update_top_level_activity)
    log.to_csv(log_file, index=False)
    pickle.dump(mapping, open(mapping_file, "wb"))


def _remove_trailing_dots(log: pd.DataFrame) -> pd.DataFrame:
    """
    Remove trailing dots from the activity names in the log.
    This is necessary because some activities have trailing dots that can cause issues in processing.
    """
    log["operation_name"] = log["operation_name"].str.rstrip(".")
    log["service_name"] = log["service_name"].str.rstrip(".")
    return log


def prepare_log(log: pd.DataFrame, update_top_level_activity=False):
    # log = _filter_client_spans(df)
    log = _remove_trailing_dots(log)
    if update_top_level_activity:
        log = _update_top_level_activity(log)
    log = log[~log["start_time"].isna() & ~log["end_time"].isna()]
    log, mapping = _create_activity_shortcut_mapping(log)
    return log, mapping


def _create_activity_shortcut_mapping(log: pd.DataFrame):
    m = dict()
    reverse = dict()
    service_nr = 0
    for service_name, group in log.groupby("service_name"):
        activity_nr = 0
        m[service_name] = dict()
        m[service_nr] = service_name
        for activity_name, service_group in group.groupby("operation_name"):
            m[service_name][activity_name] = activity_nr
            reverse[str(service_nr) + "_" + str(activity_nr)] = (
                str(service_name) + "$" + str(activity_name)
            )
            reverse[str(service_name) + "$" + str(activity_name)] = (
                str(service_nr) + "_" + str(activity_nr)
            )
            log.loc[service_group.index, "activity_name"] = (
                str(service_nr) + "_" + str(activity_nr)
            )
            activity_nr += 1
        service_nr += 1
    return log, reverse


"""
Because of clock skew, the start and end times of the children can sometimes be outside the parent's start and end times.
"""


def _fix_child_parent_timing(log: pd.DataFrame):
    log["start_time"] = pd.to_datetime(log["start_time"]).dt.tz_localize(None)
    log["end_time"] = pd.to_datetime(log["end_time"]).dt.tz_localize(None)
    import warnings

    warnings.filterwarnings("ignore")
    log["nested_activity_name"] = log["activity_name"]
    for trace_id, trace in log.groupby("trace_id"):
        parent_map = {}
        for _index, row in trace.iterrows():
            parent_map[row["span_id"]] = row["parent_span_id"]
        root = trace[trace["parent_span_id"].isna()]
        bfs = [(root, [])]
        while bfs:
            current, parents = bfs.pop(0)
            current_name = current["nested_activity_name"].iloc[0]
            if len(parents) == 0:
                new_name = current_name
            else:
                new_name = current_name + "<-" + "<-".join(parents)
            log.loc[current.index, "nested_activity_name"] = new_name
            children = trace[trace["parent_span_id"] == current["span_id"].iloc[0]]
            if len(children) == 0:
                continue
            lower_children = children[
                children["start_time"] < current["start_time"].iloc[0]
            ]
            for i, (index, child) in enumerate(lower_children.iterrows()):
                log.loc[index, "start_time"] = current["start_time"].iloc[
                    0
                ] + pd.Timedelta(microseconds=i + 1)
            higher_children = children[
                children["end_time"] > current["end_time"].iloc[0]
            ]
            for i, (index, child) in enumerate(higher_children.iterrows()):
                log.loc[index, "end_time"] = current["end_time"].iloc[0] - pd.Timedelta(
                    microseconds=i + 1
                )
            for _index, child in children.iterrows():
                bfs.append(
                    (
                        trace[trace["span_id"] == child["span_id"]],
                        [current_name] + parents,
                    )
                )
    return log


"""
Load traces from a log file
"""


def _load_log(file_path) -> pd.DataFrame:
    return pd.read_csv(file_path)


"""
Filter out all client spans from the log with no corresponding server span
"""


def _filter_client_spans(log: pd.DataFrame) -> pd.DataFrame:
    clients = log[log["span_kind"] == "client"]
    span_ids = []
    for _index, client in clients.iterrows():
        children = log[log["parent_span_id"] == client["span_id"]]
        if len(children) > 0:
            span_ids.append(client["span_id"])
        log.loc[children.index, "parent_span_id"] = client["parent_span_id"]
    log = log[~log["span_id"].isin(span_ids)]
    return log


"""
Create the activity name. The activity name should be unique over the application,
so we take a combination of the service name and the operation name
"""


def _add_activity_name(log: pd.DataFrame) -> pd.DataFrame:
    log["activity_name"] = log["service_name"] + " " + log["operation_name"]
    return log


"""
Adds the end time to the log.
"""


def _add_end_time(log: pd.DataFrame) -> pd.DataFrame:
    log["time"] = log["end_time"]
    return log


"""
Add the start and end time to the log. The start time is the same as the start time of the log, and the end time is the same as the end time of the log.
The activity name is prefixed with 'S ' and 'E ', respectively.
"""


def _add_start_and_end_time(log: pd.DataFrame) -> pd.DataFrame:
    copy = log.copy()
    copy["time:timestamp"] = copy["start_time"]
    copy["activity_name"] = S(copy["activity_name"])
    log = _add_end_time(log)
    log["activity_name"] = E(log["activity_name"])
    log = pd.concat([copy, log], ignore_index=True)
    return log


"""
Some examples have a duplicate activity name in the beginning.
We need to give those a different name
"""


def _update_top_level_activity(log: pd.DataFrame) -> pd.DataFrame:
    top_level = log[log["parent_span_id"].isnull()]
    log = log[~log.index.isin(top_level.index)]
    children = log[log["parent_span_id"].isin(top_level["span_id"])]
    log.loc[children.index, "parent_span_id"] = None
    return log
