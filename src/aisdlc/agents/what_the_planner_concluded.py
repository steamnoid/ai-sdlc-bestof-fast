"""What `aisdlc-dev-plan` concluded, in the shape the model fills.

**The plan and the judgement about the plan, in one answer, because they come out of one
question.** The artifact is five lists of paths, and a real run proved what that costs: the
plan named a file, the implementer had to invent the mechanism, and the tests it wrote
observed nothing because nobody had said what the change was for. So the planner is asked two
things at once and answers them together — no second call, and no chance of a judgement
written about a plan that is not the one in the same answer.

**It is deliberately not an `ImplementationPlan`.** That type's fields were fixed by a person
and by the glossary, and a shape a model fills has nowhere to put anything else. Wrapping it
rather than widening it means the artifact a gate presents still holds exactly the five lists a
person is asked to approve, and the reasoning beside it never reaches the card.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from aisdlc.agents.implementation_plan import ImplementationPlan
from aisdlc.agents.what_an_agent_judged import WhatAnAgentJudged

NOTHING_WAS_FOUND = (
    "nothing: the plan changes what the approved requirements already named and adds no finding"
)
NOTHING_WAS_UNSETTLED = (
    "nothing: every question this plan had to answer, the approved requirements answered for it"
)


class ImplementationPlanAnswer(BaseModel):
    """One plan and the planning agent's judgement of it, all required.

    Frozen and `extra="forbid"` for the reason every answer type here is: a conclusion this
    system did not ask for is one no human was ever shown, and a field the model invented
    would be carried inside a plan somebody is asked to approve.

    **The three judgements are required, and the middle one is the reason.**
    `what_it_could_not_settle` has to be answered even when the answer is "nothing" — a real
    run's implementer wrote *the inspection does not show whether the existing `.gitignore`
    already ignores `e2e.db-wal`*, which is a true sentence and not a reason to stop, and that
    sentence is the single most useful thing on the card. A field with a default would let the
    model skip exactly the part a reader needs.

    **A blank is refused rather than stored**, because a blank field reads as *the planner had
    nothing to say* and that is indistinguishable from *nobody asked*. What this run already
    knows how to get is a model filling a shape and saying nothing — four empty lists were
    passed for a plan — so the two sentences below are what an answer with nothing to report
    reaches for instead of silence. They are module constants because they are the sentences a
    model will be shown, and a sentence buried in a validator is a sentence no reader finds.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan: ImplementationPlan
    judged: WhatAnAgentJudged
