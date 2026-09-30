"""Which column of the board a work item is shown in.

**The column is a reading of the stage, and this module is the only thing that produces one.**
A second copy of state is a field an agent can write, and an agent that can write the column can
put a card in *to review* without ever standing at a gate. This repository deleted exactly such a
field once — a `tickecik` carrying `READY_FOR_AI` / `READY_FOR_HUMAN` / `BUSY` — and deleting it is
the reason this function exists rather than a column field.

**Six stages, five columns**, and six-to-five is not tidiness: `IDLE` and `READY` are one situation
seen from two ends, both being a work item nobody holds. `TO_REVIEW` is the column that matters —
it is the only one a card cannot reach without a person.

A board that showed columns the stage does not decide would be a second state machine, and two
state machines over one work item is one too many.
"""

from __future__ import annotations

from enum import StrEnum

from aisdlc.domain.stage import Stage
from aisdlc.domain.work_item import WorkItem


class AColumnOfTheBoard(StrEnum):
    """Where a card sits, named for the situation its work item is in."""

    TO_DISCUSS = "to discuss"
    WAITING_FOR_AN_AGENT = "waiting for an agent"
    BEING_WORKED_ON = "being worked on"
    TO_REVIEW = "to review"
    DELIVERED = "delivered"


# The table, once, and read rather than computed: a mapping written as five `if`s is five chances
# to mistype a stage, and a stage the chain does not mention would fall through to nothing.
_THE_COLUMN_OF_A_STAGE: dict[Stage, AColumnOfTheBoard] = {
    Stage.IDLE: AColumnOfTheBoard.TO_DISCUSS,
    Stage.READY: AColumnOfTheBoard.TO_DISCUSS,
    Stage.AWAITING_AGENT_PICKUP: AColumnOfTheBoard.WAITING_FOR_AN_AGENT,
    Stage.IN_PROGRESS_BY_AGENT: AColumnOfTheBoard.BEING_WORKED_ON,
    Stage.AWAITING_HUMAN_APPROVAL: AColumnOfTheBoard.TO_REVIEW,
    Stage.DONE: AColumnOfTheBoard.DELIVERED,
}


def the_column_of(what: Stage | WorkItem) -> AColumnOfTheBoard:
    """The column a stage or a work item is shown in.

    **Both accepted, because the caller is asking about a work item and reaching through to its
    stage would make every caller know that the field exists.** A card is what a person looks at;
    `the_column_of(work_item)` is the question, and the function answers it without the caller
    having to know how.

    **Nothing is written and nothing is stored.** There is no `column` field on `WorkItem` for this
    to disagree with, and a stage the table does not mention raises rather than defaulting — a
    work item shown in the wrong column is a work item nobody is told the truth about, and `DONE`
    is not a safe default for a stage nobody has thought about.
    """
    the_stage = what.stage if isinstance(what, WorkItem) else what

    if the_stage not in _THE_COLUMN_OF_A_STAGE:
        raise NoColumnForThisStageError(the_stage)

    return _THE_COLUMN_OF_A_STAGE[the_stage]


class NoColumnForThisStageError(Exception):
    """The board is a reading of the stage, so a stage it cannot read is a gap in the board.

    Raised rather than falling back to a column, because a fallback is a lie with a position: a
    work item that has just been delivered would be shown as *to discuss* and a person would read
    that as work still to do. This is a new stage arriving before anyone gave it a home.
    """

    def __init__(self, stage: Stage) -> None:
        """Name the stage, because the fix is one row in a table and it is not guessable."""
        super().__init__(
            f"{stage.value!r} is a stage this system's work item can be in, and no column of "
            f"the board reads it. That is a gap in the board rather than a fault in the work "
            f"item, and a person cannot be shown a card whose situation has no name."
        )
