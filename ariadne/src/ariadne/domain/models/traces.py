from dataclasses import dataclass
import pandas as pd


@dataclass
class EndpointChildSpans:
    """
    Represents child spans associated with a specific endpoint.
    """

    data: pd.DataFrame
    total_traces: int
    service_name: str
    endpoint_name: str


@dataclass
class Traces:
    """
    Represents a collection of spans (traces) with methods to manipulate and query them.
    """

    data: pd.DataFrame

    def group_by_parent_activity(self):
        """
        Groups spans by their parent activity, yielding tuples of (service_name, span_name) and corresponding child spans.
        """
        for (service_name, span_name), group in self.data.groupby(
            ["service_name", "name"]
        ):
            filtered_data = self.data[
                self.data["parent_span_id"].isin(group["span_id"])
            ]
            total_traces = len(group["trace_id"].unique())
            yield (
                (service_name, span_name),
                EndpointChildSpans(
                    data=filtered_data,
                    total_traces=total_traces,
                    service_name=service_name,
                    endpoint_name=span_name,
                ),
            )

    @classmethod
    def from_otel_df(cls, df: pd.DataFrame):
        return cls(data=df)
