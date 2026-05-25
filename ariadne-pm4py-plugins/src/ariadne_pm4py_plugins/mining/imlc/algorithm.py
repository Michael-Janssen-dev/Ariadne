from typing import Any, List, Tuple

from pm4py.algo.discovery.inductive.variants.abc import InductiveMinerFramework
from pm4py.objects.process_tree.obj import ProcessTree
from pm4py.objects.process_tree.utils import generic as pt_util
from pm4py.objects.process_tree.utils.generic import tree_sort
from pm4py.util.compression.dtypes import UVCL

from .base_cases.factory import IMLCBaseCaseFactory
from .cuts.factory import IMLCCutFactory
from .dtypes.imlc import IMLCDataStructureUVCL
from .fall_through.factory import IMLCFallThroughFactory


class IMLC(InductiveMinerFramework[IMLCDataStructureUVCL]):
    def apply_base_cases(
        self, obj: IMLCDataStructureUVCL, parameters: dict[str, Any] | None = None
    ) -> ProcessTree | None:
        return IMLCBaseCaseFactory.apply_base_cases(obj, None, parameters=parameters)  # pyright: ignore[reportArgumentType]

    def find_cut(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, obj: IMLCDataStructureUVCL, parameters: dict[str, Any] | None = None
    ) -> ProcessTree | None:
        return IMLCCutFactory.find_cut(obj, None, parameters=parameters)  # pyright: ignore[reportReturnType, reportArgumentType]

    def fall_through(
        self, obj: Any, parameters: dict[str, Any] | None = None
    ) -> Tuple[ProcessTree, List]:
        return IMLCFallThroughFactory.fall_through(
            obj,
            None,  # pyright: ignore[reportArgumentType]
            None,
            None,
            parameters=parameters,
        )

    def instance(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        return None


def discover_petri_net_inductive_lifecycle(uvcl: UVCL):
    im = IMLC(None)
    data = IMLCDataStructureUVCL(uvcl)
    tree = im.apply(data, parameters=None)
    tree = pt_util.fold(tree)
    tree_sort(tree)
    return tree
