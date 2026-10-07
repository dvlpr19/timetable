"""Solver interface. CP-SAT is the only implementation now; others (a greedy baseline or a
metaheuristic for the thesis comparison) plug in the same way."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field

from apps.scheduling.validators import DEFAULT_WEIGHTS, Placement

from .problem import Problem


@dataclass
class SolveParams:
    time_limit: float = 90.0  # seconds
    workers: int = 8
    seed: int = 0
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))


@dataclass
class SolveResult:
    status: str  # optimal | feasible | infeasible | unknown | cancelled
    placements: list[Placement]  # new lessons only (problem.fixed stays as it is)
    objective: float | None = None
    best_bound: float | None = None
    wall_time: float = 0.0
    model_stats: dict = field(default_factory=dict)


Progress = Callable[[dict], None]
ShouldStop = Callable[[], bool]


class BaseSolver(ABC):
    name = "base"

    @abstractmethod
    def solve(
        self,
        problem: Problem,
        params: SolveParams,
        *,
        hints: dict[str, tuple] | None = None,
        progress: Progress | None = None,
        should_stop: ShouldStop | None = None,
    ) -> SolveResult:
        """Place as many units as possible without breaking a hard constraint."""
