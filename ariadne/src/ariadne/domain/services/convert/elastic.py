import pandas as pd

TIMESTAMP_COL = "@timestamp"
DURATION_COL = "transaction.duration.us"
DEFAULT_DURATION = 1  # in ms


def _convert_elastic_times_to_otel(log):
    # Parse timestamps
    log["start_time"] = pd.to_datetime(
        log[TIMESTAMP_COL], format="%b %d, %Y @ %H:%M:%S.%f"
    )

    # Handle missing durations
    log.loc[log[DURATION_COL] == "-", DURATION_COL] = DEFAULT_DURATION

    # Parse durations
    log["duration"] = log[DURATION_COL].str.replace(" ms", "").astype(float)
    log["duration"] = pd.to_timedelta(log["duration"], unit="ms")

    # Calculate end times
    log["end_time"] = log["start_time"] + log["duration"]

    # Clean up columns (duration messes with pm4py checks)
    log.drop(columns=["duration", DURATION_COL, TIMESTAMP_COL], inplace=True)


def _rename_columns(log):
    log.rename(
        columns={
            "trace.id": "trace_id",
            "span.id": "span_id",
            "parent.id": "parent_span_id",
            "transaction.name": "name",
            "service.name": "service_name",
        },
        inplace=True,
    )


def convert_elastic_csv_to_otel(log: pd.DataFrame) -> pd.DataFrame:
    """
    Convert Elastic APM CSV export to OTEL-compatible CSV format.
    Args:
        elastic: DataFrame with Elastic APM trace data
    Returns:
        DataFrame in OTEL format
    """

    _convert_elastic_times_to_otel(log)
    _rename_columns(log)
    return log
