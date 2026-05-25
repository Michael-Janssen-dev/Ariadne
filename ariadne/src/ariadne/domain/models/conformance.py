from dataclasses import dataclass


@dataclass
class ConformanceResult:
    fitness: float
    precision: float
    simplicity: float
    generalization: float
