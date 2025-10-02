from typing import Tuple

from pm4py import ProcessTree
from pm4py.algo.discovery.inductive.cuts.factory import CutFactory
from pm4py.algo.discovery.inductive.cuts.abc import Cut

from .loop import NonAtomicLoopCutUVCL
from ..dtypes.imlc import IMLCDataStructureUVCL
from ..cuts.concurrent import NonAtomicConcurrentCut

from ..cuts.sequence import NonAtomicSequenceCutUVCL
from ..cuts.xor import NonAtomicExclusiveChoiceCutUVCL


class IMLCCutFactory(CutFactory):
    @classmethod
    def get_cuts(
        cls, obj: IMLCDataStructureUVCL, inst=None, parameters=None
    ) -> list[Cut]:
        return [
            NonAtomicExclusiveChoiceCutUVCL,
            NonAtomicSequenceCutUVCL,
            NonAtomicConcurrentCut,
            NonAtomicLoopCutUVCL,
        ]

    @classmethod
    def find_cut(
        cls, obj: IMLCDataStructureUVCL, inst=None, parameters=None
    ) -> Tuple[ProcessTree, list[IMLCDataStructureUVCL]]:
        for f in cls.get_cuts(obj, inst, parameters):
            r = f.apply(obj)
            if r is not None:
                return r
        return None
