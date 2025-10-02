from enum import Enum, auto
import pm4py
import random
import pandas as pd
from pm4py.util.compression import util as comut
from pm4py.util.compression.dtypes import UVCL


NOISE_THRESHOLD = 0.1


class MinerVariants(Enum):
    IMlc = auto()


def rename_places(petri_net: pm4py.PetriNet, activity_name) -> pm4py.PetriNet:
    random_id = random.randint(0, 100000)
    for place in petri_net.places:
        place.name = place.name + " " + activity_name + " " + str(random_id)
    return petri_net


def merge_lifecycles(log: pd.DataFrame) -> pd.DataFrame:
    start = log.copy()
    end = log.copy()
    start["activity_name"] = "S " + start["activity_name"]
    end["activity_name"] = "E " + end["activity_name"]
    start["time"] = start["start_time"]
    end["time"] = end["end_time"]
    return pd.concat([start, end])


def _get_uvcl(log: pd.DataFrame, total_cases: int) -> UVCL:
    uvcl = comut.get_variants(
        comut.project_univariate(
            log,
            key="concept:name",
            df_glue="case:concept:name",
            df_sorting_criterion_key="time:timestamp",
        )  # type: ignore
    )
    filled_cases = sum(uvcl.values())
    if filled_cases < total_cases:
        uvcl[()] = total_cases - filled_cases  # type: ignore
    return uvcl
