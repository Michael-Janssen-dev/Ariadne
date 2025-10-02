from typing import Tuple, Optional, Any

from pm4py import ProcessTree
from pm4py.algo.discovery.inductive.fall_through.factory import FallThroughFactory
from pm4py.algo.discovery.inductive.base_case.abc import BaseCase

from ..fall_through.single_activity_tau_loop import (
    SingleActivityTauLoop,
)
from ..dtypes.imlc import IMLCDataStructureUVCL

from ..fall_through.empty_traces import NonAtomicEmptyTracesUVCL
from ..fall_through.non_atomic_activity_once_per_trace import (
    NonAtomicActivityOncePerTrace,
)
from ..fall_through.activity_concurrent import ActivityConcurrent
from ..fall_through.strict_non_atomic_tau_loop import StrictNonAtomicTauLoop
from ..fall_through.non_atomic_tau_loop import NonAtomicTauLoop
from ..fall_through.concurrent_flower import ConcurrentFlowerModel


class IMLCFallThroughFactory(FallThroughFactory):
    @classmethod
    def get_fall_throughs(
        cls, obj: IMLCDataStructureUVCL, inst=None, parameters=None
    ) -> list[BaseCase]:
        return [
            NonAtomicEmptyTracesUVCL,
            NonAtomicActivityOncePerTrace,
            ActivityConcurrent,
            StrictNonAtomicTauLoop,
            NonAtomicTauLoop,
            SingleActivityTauLoop,
            ConcurrentFlowerModel,
        ]

    @classmethod
    def fall_through(
        cls,
        obj: IMLCDataStructureUVCL,
        inst,
        pool,
        manager,
        parameters: Optional[dict[str, Any]] = None,
    ) -> Tuple[ProcessTree, list[IMLCDataStructureUVCL]]:
        for f in cls.get_fall_throughs(obj, inst, parameters):
            r = f.apply(obj, pool)
            if r is not None:
                return r
        return None
