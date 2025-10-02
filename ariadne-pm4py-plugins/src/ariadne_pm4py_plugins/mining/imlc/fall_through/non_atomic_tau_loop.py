from collections import Counter

from ..dtypes.imlc import IMLCDataStructureUVCL
from ..fall_through.strict_non_atomic_tau_loop import StrictNonAtomicTauLoop
from pm4py.util.compression.dtypes import UVCL

from ..util import base


class NonAtomicTauLoop(StrictNonAtomicTauLoop):
    @classmethod
    def _get_projected_log(
        cls, obj: IMLCDataStructureUVCL, parameters=None
    ) -> UVCL | None:
        start_activities = obj.dfg.start_activities
        log = obj.data_structure
        proj = Counter()
        for t in log:
            x = 0
            for i in range(1, len(t)):
                if base(t[i]) in start_activities:
                    if not cls._is_consistent(t[x:i]):
                        return None
                    proj.update({t[x:i]: log[t]})
                    x = i
            proj.update({t[x : len(t)]: log[t]})
        return proj
