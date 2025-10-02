from typing import Optional

from pm4py import ProcessTree
from pm4py.algo.discovery.inductive.base_case.factory import BaseCaseFactory, T
from pm4py.algo.discovery.inductive.base_case.abc import BaseCase
from ..dtypes.imlc import IMLCDataStructureUVCL
from pm4py.algo.discovery.inductive.base_case.empty_log import EmptyLogBaseCaseUVCL
from ..base_cases.single_non_atomic_activity import SingleNonAtomicActivityUVCL
from pm4py.algo.discovery.inductive.variants.instances import IMInstance


class IMLCBaseCaseFactory(BaseCaseFactory):
    @classmethod
    def get_base_cases(
        cls, obj: IMLCDataStructureUVCL, inst=None, parameters=None
    ) -> list[BaseCase]:
        return [EmptyLogBaseCaseUVCL, SingleNonAtomicActivityUVCL]

    @classmethod
    def apply_base_cases(
        cls, obj: T, inst: IMInstance, parameters=None
    ) -> Optional[ProcessTree]:
        for f in cls.get_base_cases(obj, inst, parameters):
            r = f.apply(obj)
            if r is not None:
                return r
        return None
