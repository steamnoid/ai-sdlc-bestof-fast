"""What an agent judged about its own work, in one place rather than in six.

**The rule is one rule and it is asked in six places, and that is the defect this removes.**
Every agent that reasons in this run answers three questions about its own work: what it found,
what it could not settle, what it expects next. A blank in any of them is refused — because a
blank reads as *the agent had nothing to say*, which is not a thing anybody can check.

Written out four times, a reader learns the meaning of a blank on one card and not on another,
and a change to the rule would be four changes with three of them missed. So the three fields
and the refusal live here, and each answer carries this rather than spelling it out.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

NOTHING_WAS_FOUND = "nothing: this run asked and the answer carried no finding worth naming"
NOTHING_WAS_UNSETTLED = (
    "nothing: every question this run had to answer, the approved requirements answered for it"
)


class WhatAnAgentJudged(BaseModel):
    """The three things an agent is asked about its own work, and the text they leave behind.

    **Frozen and `extra="forbid"`**, for the reason every answer type here is: a conclusion this
    system did not ask for is one no human was ever shown.

    **The middle judgement is the one worth having, and it is why all three are required.** A
    real run's implementer wrote *whether the plan meant a rule for a file that already exists or
    a whole new file, because the plan names one path and no intent* — a true sentence, not a
    reason to stop, and the single most useful thing on the card. The sentence is what a planner
    reading the card, or a supervisor deciding whether another attempt is worth buying, has no
    other way to get.

    **A blank is refused rather than stored**, and the message carries the two sentences an agent
    with nothing to report may say instead. A model that fills a shape and says nothing is what
    this run already knows how to get — four empty lists were passed for a plan — and a silent
    field is indistinguishable from nobody having asked.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    what_it_found: str
    what_it_could_not_settle: str
    what_it_expects_next: str

    @field_validator("what_it_found", "what_it_could_not_settle", "what_it_expects_next")
    @classmethod
    def _refuse_a_judgement_nobody_made(cls, said: str) -> str:
        """Refuse a blank judgement, and say in words what an empty one would have meant."""
        if not said.strip():
            raise ValueError(
                "an agent is asked what it found, what it could not settle and what it expects "
                "next, and one of those is empty; an agent with nothing to report says so in "
                f"words -- {NOTHING_WAS_FOUND!r} and {NOTHING_WAS_UNSETTLED!r} are answers, "
                "and an empty field reads as *the agent had nothing to say*, which is not a "
                "thing anybody can check"
            )
        return said

    def the_text_of_the_note_this_is(self) -> str:
        """The note left on the card, which carries the three judgements and nothing else.

        **The artefact is not in the text, on purpose.** Every artefact beside this note on the
        same card already holds it, and a note repeating it gives a reader the same document
        twice while the one thing worth reading goes to the bottom of a list.
        """
        return (
            f"what it found: {self.what_it_found}\n"
            f"what it could not settle: {self.what_it_could_not_settle}\n"
            f"what it expects next: {self.what_it_expects_next}"
        )
