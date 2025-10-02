from collections import Counter
from copy import copy

from pm4py import ProcessTree
from pm4py.algo.discovery.inductive.dtypes.im_ds import IMDataStructureUVCL
from pm4py.algo.discovery.inductive.fall_through.empty_traces import EmptyTracesUVCL
from pm4py.objects.process_tree.obj import Operator

from ..dtypes.imlc import IMLCDataStructureUVCL


class NonAtomicEmptyTracesUVCL(EmptyTracesUVCL):
    @classmethod
    def apply(cls, obj: IMDataStructureUVCL, pool=None, manager=None, parameters=None):
        if cls.holds(obj, parameters):
            data_structure = copy(obj.data_structure)
            del data_structure[()]
            if data_structure:
                return ProcessTree(operator=Operator.XOR), [
                    IMLCDataStructureUVCL(Counter()),
                    IMLCDataStructureUVCL(data_structure),
                ]
            else:
                return ProcessTree(), []
        else:
            return None
