"""What the planner's seam is handed, read properly.

**`get_args` on a `Callable` returns two things and the first is the whole parameter list.** So
`SecurityReport in get_args(PlanTheChange)` asks whether a type is equal to a *list of types*, and
answers no forever — whether or not the planner has been handed one. Two tests made that mistake
before this function existed, and both were wrong in the same direction: they would have failed
after the fix as well as before it, which is worse than not testing.

**So the parameter types are unpacked once, here**, and the two tests that care read this. A seam's
contract is its types rather than its parameter names, because a name is a choice anybody can make
and a type is what a caller is held to.
"""

from __future__ import annotations

from typing import get_args

from aisdlc.graph.plan_node import PlanTheChange


def the_types_the_planner_is_handed() -> tuple[type, ...]:
    """Every type in the planner's seam, in order, with the return type left out."""
    the_parameters, _the_answer = get_args(PlanTheChange)
    return the_parameters
