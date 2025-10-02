from collections import Counter
from typing import Any, Tuple
from pm4py.objects.process_tree.obj import ProcessTree, Operator
from pm4py.algo.discovery.inductive.fall_through.abc import FallThrough
from ..dtypes.imlc import IMLCDataStructureUVCL


class ConcurrentFlowerModel(FallThrough[IMLCDataStructureUVCL]):
    @classmethod
    def holds(cls, obj, parameters=None) -> bool:
        return True

    @classmethod
    def apply(
        cls,
        t: IMLCDataStructureUVCL,
        pool=None,
        manager=None,
        parameters: dict[str, Any] | None = None,
    ) -> Tuple[ProcessTree, list[IMLCDataStructureUVCL]] | None:
        max_concurrent = Counter()
        for trace in t.data_structure:
            concurrent = Counter()
            for event in trace:
                if event.startswith("S"):
                    concurrent[event[2:]] += 1
                    max_concurrent[event[2:]] = max(
                        max_concurrent[event[2:]], concurrent[event[2:]]
                    )
                else:
                    concurrent[event[2:]] -= 1
        result = ProcessTree(operator=Operator.PARALLEL)
        for activity, count in max_concurrent.items():
            child = ProcessTree(operator=Operator.LOOP)
            for i in range(count):
                child.children.append(ProcessTree(label=activity))
                child.children.append(ProcessTree())
            result.children.append(child)
        return result, [IMLCDataStructureUVCL(Counter())]
