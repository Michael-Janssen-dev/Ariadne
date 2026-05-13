from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from ariadne.constants import *


@dataclass
class EndpointChildSpans:
    """
    Represents child spans associated with a specific endpoint.
    """

    data: pd.DataFrame
    total_traces: int
    service_name: str
    endpoint_name: str


EMPTY_VALUES_STR = "null,NULL,none,None,-,N/A,n/a,"


@dataclass
class TraceLog:
    """
    Represents a collection of spans (traces) with methods to manipulate and query them.
    """

    data: pd.DataFrame

    def _transitive_merge(self):
        """
        Transitive merge spans with "empty" operation names.
        """
        log = self.data
        empty_values = [v.strip() for v in EMPTY_VALUES_STR.split(",")]

        op = log[SPAN_NAME_COL]
        empty_mask = (
            op.isna() | (op.astype(str).str.strip() == "") | (op.isin(empty_values))
        )
        to_remove = set(log.loc[empty_mask, SPAN_ID_COL])
        parent_map = dict(zip(log[SPAN_ID_COL], log[PARENT_ID_COL]))

        def as_none(x):
            if pd.isna(x):
                return None
            s = str(x)
            if s.strip() == "" or s in empty_values:
                return None
            return x

        # Collapse through any chain of removable ancestors
        @lru_cache(maxsize=None)
        def collapsed_parent(pid):
            pid = as_none(pid)
            seen = set()
            cur = pid
            while cur is not None and cur in to_remove:
                seen.add(cur)
                cur = as_none(parent_map.get(cur))
            return None if cur == pid else cur

        new_parent_values = []
        for pid in log[PARENT_ID_COL].tolist():
            pid_norm = as_none(pid)
            new_parent_values.append(
                collapsed_parent(pid_norm) if pid_norm in to_remove else pid_norm
            )

        out = log.copy()
        out[PARENT_ID_COL] = new_parent_values

        out = out[~out[SPAN_ID_COL].isin(to_remove)].copy()

        self.data = out

    def _remove_self_referencing_spans(self):
        """
        Set the parent of any self-referencing spans to None.
        """
        log = self.data
        mask = log[SPAN_ID_COL] == log[PARENT_ID_COL]
        log.loc[mask, PARENT_ID_COL] = None
        self.data = log

    def preprocess(self):
        """
        Preprocesses the trace log data, such as formatting timestamps.
        """
        self._remove_self_referencing_spans()
        self._transitive_merge()
        return PreprocessedTraceLog(data=self.data)


@dataclass
class PreprocessedTraceLog(TraceLog):
    """
    Represents a preprocessed trace log, ready for analysis.
    """

    def __post_init__(self):
        self.data.loc[:, ACTIVITY_NAME_COL] = (
            self.data[SERVICE_NAME_COL] + "$" + self.data[SPAN_NAME_COL]
        )
        self.data = self.data.drop_duplicates(subset=["span_id"])
        parent_key = self.data["parent_span_id"].map(
            self.data.set_index("span_id").apply(
                lambda r: f"{r[SERVICE_NAME_COL]}${r[SPAN_NAME_COL]}", axis=1
            )
        )
        self.data.loc[:, "parent_activity_name"] = parent_key
        self.counts = self.data["activity_name"].value_counts()

    def group_by_parent_activity(self):
        """
        Groups spans by their parent activity, yielding tuples of (service_name, span_name) and corresponding child spans.
        """
        for activity_name, group in self.data.groupby("parent_activity_name"):
            service_name, span_name = str(activity_name).split("$")
            yield (
                (service_name, span_name),
                EndpointChildSpans(
                    data=group,
                    total_traces=self.counts[activity_name],
                    service_name=service_name,
                    endpoint_name=span_name,
                ),
            )

    pass


class TraceLogFactory:
    REQUIRED_COLUMNS = {
        TRACE_ID_COL,
        SPAN_ID_COL,
        PARENT_ID_COL,
        SPAN_NAME_COL,
        SERVICE_NAME_COL,
        START_TIME_COL,
        END_TIME_COL,
    }

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> TraceLog:
        cls._validate_dataframe(df)
        return TraceLog(data=df)

    @classmethod
    def _validate_dataframe(cls, df: pd.DataFrame):
        missing_columns = cls.REQUIRED_COLUMNS - set(df.columns)
        if missing_columns:
            raise ValueError(
                f"DataFrame is missing required columns: {missing_columns}"
            )
