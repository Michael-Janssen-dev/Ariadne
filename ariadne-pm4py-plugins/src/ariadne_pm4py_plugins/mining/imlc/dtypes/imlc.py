from pm4py.util.compression.dtypes import UVCL
from pm4py.algo.discovery.inductive.dtypes.im_ds import IMDataStructureUVCL
from pm4py.objects.dfg.obj import DFG
from ..dfg.algorithm import discover_non_atomic_dfg_uvcl
from ..concurrency.algorithm import discover_concurrency_graph_uvcl
from ..util import base


class IMLCDataStructureUVCL(IMDataStructureUVCL):
    def __init__(self, uvcl: UVCL, dfg: DFG = None):
        if dfg is None:
            dfg = discover_non_atomic_dfg_uvcl(uvcl)
        super().__init__(uvcl, dfg)
        self.fix_completeness()
        self.concurrency_graph = discover_concurrency_graph_uvcl(self.data_structure)

    @property
    def dfg(self) -> DFG:
        return self._dfg

    def fix_completeness(self):
        new_log = UVCL()
        for t in self.data_structure:
            active = {}
            fix = []
            for i, e in enumerate(t):
                is_start = e.startswith("S ")
                if is_start:
                    if base(e) not in active:
                        active[base(e)] = []
                    active[base(e)].append(i)
                else:
                    if base(e) in active and active[base(e)]:
                        active[base(e)].pop()
                    else:
                        fix.append((e, i))
            for a in active:
                for j in active[a]:
                    fix.append(("S " + a, j))
            fix.sort(key=lambda x: -x[1])
            for e, i in fix:
                is_start = e.startswith("S ")
                if is_start:
                    t = t[: i + 1] + ("E " + base(e),) + t[i + 1 :]
                else:
                    t = t[:i] + ("S " + base(e),) + t[i:]
            new_log[t] = self.data_structure[t]
        self._obj = new_log
