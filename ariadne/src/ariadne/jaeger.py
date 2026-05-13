import csv
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import tqdm

from ariadne.constants import (
    END_TIME_COL,
    PARENT_ID_COL,
    REQUIRED_COLUMNS,
    SERVICE_NAME_COL,
    SPAN_ID_COL,
    SPAN_NAME_COL,
    START_TIME_COL,
    TRACE_ID_COL,
)


def extract_rows(path: Path) -> list[dict]:
    with open(path, "r") as f:
        d = json.load(f)
    rows = []
    for trace in d["data"]:
        for span in trace["spans"]:
            parent_span_id = None
            for ref in span.get("references", []):
                if ref["refType"] == "CHILD_OF":
                    parent_span_id = ref["spanID"]
            rows.append(
                {
                    TRACE_ID_COL: span["traceID"],
                    SPAN_ID_COL: span["spanID"],
                    SERVICE_NAME_COL: trace["processes"][span["processID"]][
                        "serviceName"
                    ],
                    PARENT_ID_COL: parent_span_id,
                    SPAN_NAME_COL: span["operationName"],
                    START_TIME_COL: span["startTime"],
                    END_TIME_COL: span["startTime"] + span["duration"],
                }
            )
    return rows


def process_traces(directory: Path):
    files = [f for f in sorted(directory.iterdir())]
    with open("spans.csv", "w") as f, ProcessPoolExecutor() as pool:
        writer = csv.DictWriter(f, REQUIRED_COLUMNS)
        writer.writeheader()
        for rows in tqdm.tqdm(
            pool.map(extract_rows, files, chunksize=4), total=len(files)
        ):
            writer.writerows(rows)


if __name__ == "__main__":
    process_traces(Path("data/bottom-up-trace"))
