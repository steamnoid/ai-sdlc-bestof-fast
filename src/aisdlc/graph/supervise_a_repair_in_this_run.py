"""The node that reads a run's card and asks a model what to repeat.

**The state is read here and nowhere else, because the model is the seam and the state is not.**
`supervise_a_repair` takes a work item, a projects root, the refusal's own words and a model.
Which of those live in the run's state is a fact about this graph and not about the supervisor,
so it is settled in this one place — and every other node in this package is wired the same way,
by a lambda that turns a state into arguments.

**The refusal arrives as text and is not summarised on the way in.** A supervisor asked to decide
on a paragraph written for a person is deciding on a summary, and the whole note mechanism
exists so that a later agent reads what an earlier one actually wrote.
"""

from __future__ import annotations

from langgraph.types import Command

from aisdlc.graph.agent_state import WHAT_STOPPED_THIS_RUN, AgentState
from aisdlc.graph.supervise_a_repair import (
    ARefusalWithNoReasonToRepairError,
    SuperviseARepair,
)


def supervise_a_repair_in_this_run(state: AgentState, supervise: SuperviseARepair) -> Command:
    """Ask the supervisor what to repeat, having read the refusal out of the run's state.

    **A refusal with no text is refused rather than handed over as an empty question.** The
    supervisor is told a stage was wrong; what it was wrong about is the evidence, and a prompt
    with the first half and not the second is a model asked to guess.
    """
    what_stopped_this_run = state.get(WHAT_STOPPED_THIS_RUN)

    if not what_stopped_this_run:
        raise ARefusalWithNoReasonToRepairError

    return supervise(
        state["work_item"],
        state["projects_root"],
        what_stopped_this_run,
    )
