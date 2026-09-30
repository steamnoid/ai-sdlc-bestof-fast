"""What a board can say, and where a card sits without anybody saying so.

**A column is read off the stage and stored nowhere.** A stored column is a field an agent can
write, and an agent that can write it can put a card *to review* without ever standing at a gate.
A sibling project deleted a field of exactly that shape — a `tickecik` carrying `READY_FOR_AI` /
`BUSY` / `READY_FOR_HUMAN` — which then had to be *derived* from the stage precisely so that it
could not be used to skip a human gate. Three of its values described a stage `Stage` already
said, and deleting the field deleted the rule with it.

**Six stages, five columns, and that is not a mistake.** `IDLE` and `READY` are one situation seen
from two ends: a ticket nobody has looked at.

**A stage with no column raises rather than defaulting,** because a fallback is a lie with a
position — a card in a column nobody chose is a card somebody put there by accident.

**A board is a reading of the store, never a projection assembled in a widget.** A board that
computed its own state from the run would be a second source of truth able to disagree with the
first, which is the shape of the bug a sibling project shipped: a register and the run it was
recording told two different stories and nothing in the run looked wrong. **This module is that
reading and it is the only place a board's facts come from.**

**The context meter is the growing context, measured in words.** Every gate answered, every note an
agent left, every line the run said — counted and summed. A card listing artifacts tells a person
what exists; a card with a number tells them whether this run is getting anywhere, and it is the
one figure on a card that is comparable between two runs.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, computed_field

from aisdlc.approval.approval_decision import ApprovalDecision
from aisdlc.domain.commissioned_request import CommissionedRequest
from aisdlc.domain.repository import Repository
from aisdlc.domain.role import Role
from aisdlc.domain.stage import Stage
from aisdlc.domain.work_item import WorkItem
from aisdlc.store.the_record_of_a_run import (
    AComment,
    WhatARunSaid,
    the_decisions_this_run_collected,
    the_events_this_run_produced,
    the_notes_on_the_card,
    what_the_gate_was_asking_about,
)
from aisdlc.store.the_register_of_work_items import (
    AWorkItemNobodyAskedForError,
    NoSuchWorkItemError,
    the_work_item_registered_at,
    the_work_items_this_register_holds,
)

# What a hundred words is called on a card, because "1.4k" is a figure a reader scans and "1432"
# is a number a reader has to parse. The thresholds are named so the three lines that render the
# meter are three words rather than three arithmetic expressions.
_WORDS_A_KILO_WORD_IS = 1000
_WORDS_A_THOUSAND_WORDS_IS = 10000


class AColumnOfTheBoard(StrEnum):
    """The five places a card can be, and they are all read off the stage.

    **`StrEnum` and not a plain `Enum`,** which is the opposite of the choice `Stage` makes and for
    the opposite reason. A column is a *label for a person*, and it is compared against a string in
    a test and rendered as one in a template. A stage is a *rule*, and a stage that equals a
    hand-written string is a stage a typo can reach.
    """

    TO_DISCUSS = "to discuss"
    WAITING_FOR_AN_AGENT = "waiting for an agent"
    BEING_WORKED_ON = "being worked on"
    TO_REVIEW = "to review"
    DELIVERED = "delivered"


class NoColumnForThisStageError(Exception):
    """A work item is at a stage the board has no column for.

    **Raised and not defaulted, and that is the whole rule.** A fallback here is a lie with a
    position: the card would sit somewhere a person did not put it, and every later action on it
    would be taken in a column nobody chose. The only way this happens is a stage added to the enum
    without a row here, which is a change and not a run.
    """

    def __init__(self, what: str) -> None:
        """Quote what was not placeable, because the fix is one row in the table below."""
        self.what = what
        super().__init__(
            f"{what!r} is a stage this board has no column for, and the columns are "
            f"{[column.value for column in AColumnOfTheBoard]}. A card in a column nobody chose is "
            "a card somebody put there by accident — so this raises rather than guessing, and the "
            "only way to reach it is a stage added to the enum without a row here"
        )


# Which column each stage sits in. **Six stages, five rows, and `IDLE` and `READY` share one
# because they are one situation: a ticket nobody has looked at yet.**
_WHERE_EACH_STAGE_SITS = {
    Stage.IDLE: AColumnOfTheBoard.TO_DISCUSS,
    Stage.READY: AColumnOfTheBoard.TO_DISCUSS,
    Stage.AWAITING_AGENT_PICKUP: AColumnOfTheBoard.WAITING_FOR_AN_AGENT,
    Stage.IN_PROGRESS_BY_AGENT: AColumnOfTheBoard.BEING_WORKED_ON,
    Stage.AWAITING_HUMAN_APPROVAL: AColumnOfTheBoard.TO_REVIEW,
    Stage.DONE: AColumnOfTheBoard.DELIVERED,
}


def the_column_of(what: Stage | WorkItem) -> AColumnOfTheBoard:
    """The column this work item is in, read off its stage.

    **Takes a work item as readily as a stage,** so a caller with a card in its hand does not have
    to remember to unwrap it — and there is no way to unwrap it wrongly, because there is nothing
    to choose.
    """
    the_stage = what.stage if isinstance(what, WorkItem) else what

    if isinstance(the_stage, Stage) and the_stage in _WHERE_EACH_STAGE_SITS:
        return _WHERE_EACH_STAGE_SITS[the_stage]

    raise NoColumnForThisStageError(
        the_stage.name if isinstance(the_stage, Stage) else str(the_stage)
    )


class TheContextARunHasAccumulated(BaseModel):
    """How much a run has accumulated, as counts and a figure a person can compare.

    **Words, and not a count of artifacts.** Two runs that produced four artifacts each may have
    produced four one-line artifacts and four thousand-word ones, and a card showing *4* on both
    is telling a person nothing they can act on. The sum is the figure that is comparable.

    **Three counts and not one,** because they fail differently: a run with gates answered and no
    notes is being stopped at every gate by people, and a run with notes and no gates answered is
    reasoning that nobody has looked at. Both read as *4* on a single counter.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    how_many_gates_were_answered: int = 0
    how_many_notes_were_left: int = 0
    how_many_things_the_run_said: int = 0
    how_many_words_were_produced: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def in_words(self) -> str:
        """The meter, as the one line a card shows.

        **A computed field and not a method,** and that is not a style choice: a card is served as
        JSON, and a method does not serialise — so a method would have produced a card with a
        blank meter in the browser while every test that called it in Python stayed green. The
        browser and the test read the same field, which is the only way one of them can catch the
        other being wrong.

        **Three counts and a size, because a card is scanned and not read.** Gates first, then
        notes, then the total — a person looking at a board is looking for the first thing and
        then the size.
        """
        if self.how_many_words_were_produced == 0:
            return "nothing yet"

        return (
            f"{self.how_many_gates_were_answered} "
            f"gate{'' if self.how_many_gates_were_answered == 1 else 's'} answered"
            f" · {self.how_many_notes_were_left} note"
            f"{'' if self.how_many_notes_were_left == 1 else 's'}"
            f" · {self.how_many_words_readable}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def how_many_words_readable(self) -> str:
        """The word count as a figure rather than a number, because a card is scanned."""
        if self.how_many_words_were_produced < _WORDS_A_KILO_WORD_IS:
            return f"{self.how_many_words_were_produced} words"
        if self.how_many_words_were_produced < _WORDS_A_THOUSAND_WORDS_IS:
            return f"{self.how_many_words_were_produced / _WORDS_A_KILO_WORD_IS:.1f}k words"
        return f"{self.how_many_words_were_produced // _WORDS_A_THOUSAND_WORDS_IS}k words"


class ACardOnTheBoard(BaseModel):
    """One work item, as a person reads it in a column.

    **Frozen, and every fact on it is read from the store.** A board is a reading, and a widget
    that filled in a blank would be a second source of truth — which is how a sibling project's
    register and the run it was recording came to tell two different stories.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    work_item_id: str
    repository: Repository
    title: str
    who_asked: str
    discipline: Role
    stage: Stage
    column: AColumnOfTheBoard
    in_words: str
    context: TheContextARunHasAccumulated
    agent_holding_it: str | None = None
    artifact_it_is_waiting_about: str | None = None
    version_it_is_waiting_at: int | None = None
    why_it_was_refused: str | None = None
    who_refused_it: str | None = None
    asked_about: str | None = None
    how_many_gates_it_has_been_through: int = 0

    def discipline_in_words(self) -> str:
        """The discipline in a word a person reads, and not the abbreviation a route uses."""
        return self.discipline.in_words()

    def address_of_the_filing(self) -> str | None:
        """Where the request can be read, or `None` when it was never filed anywhere.

        **`None` and not a composed address,** for the same reason the work item carries one: a
        board showing a link nobody has confirmed exists is worse than a board showing nothing.
        """
        return self.asked_about

    def is_waiting_on_a_person(self) -> bool:
        """Whether this card is standing at a gate, and so whether it is *this one* to answer.

        **Read from the store's record of the question and not from the stage.** A card at
        `AWAITING_HUMAN_APPROVAL` whose question has already been answered is not waiting on
        anybody, and a board that said it was would put a person in front of a button that does
        nothing.
        """
        return self.artifact_it_is_waiting_about is not None

    def the_pill_it_wears(self) -> str:
        """The one word on a card that says what it needs from a reader.

        **Four words and no more**, because a card is scanned: *waiting* when it is your turn,
        *working* when an agent has it, *done*, and *refused* with a reason beside it.
        """
        if self.why_it_was_refused is not None:
            return "refused"
        if self.is_waiting_on_a_person():
            return "waiting"
        if self.stage is Stage.DONE:
            return "done"
        if self.stage is Stage.IN_PROGRESS_BY_AGENT:
            return "working"
        return "queued"


def the_board_this_register_holds(a_register: sqlite3.Connection) -> list[ACardOnTheBoard]:
    """Every card on the board, ordered by column and then by identifier.

    **Ordered by column first**, so a card does not jump between reads when a run moves — a board
    that reorders itself is a board nobody can learn to read — and by identifier within a column so
    two cards in the same place are in the same order every time.
    """
    the_columns = {column: index for index, column in enumerate(AColumnOfTheBoard)}

    the_cards = [
        what_the_board_can_say_about(a_register, work_item.work_item_id)
        for work_item in the_work_items_this_register_holds(a_register)
    ]

    return sorted(
        [a_card for a_card in the_cards if a_card is not None],
        key=lambda a_card: (the_columns[a_card.column], a_card.work_item_id),
    )


def what_the_board_can_say_about(
    a_register: sqlite3.Connection, work_item_id: str
) -> ACardOnTheBoard | None:
    """One card, read entirely out of the store, or `None` when the register holds no such ticket.

    **`None` rather than a refusal, because a board asks about identifiers it does not know
    every time it renders.** A run asking would be a different question with a different answer,
    and that is `NoSuchWorkItemError` in the register.
    """
    try:
        the_work_item = the_work_item_registered_at(a_register, work_item_id)
    except NoSuchWorkItemError:
        return None

    return _a_card_from(a_register, the_work_item)


def _a_card_from(a_register: sqlite3.Connection, the_work_item: WorkItem) -> ACardOnTheBoard:
    """Read every fact about one work item out of the store and onto a card."""
    the_decisions = the_decisions_this_run_collected(a_register, the_work_item.work_item_id)
    the_notes = the_notes_on_the_card(a_register, the_work_item.work_item_id)
    the_events = the_events_this_run_produced(a_register, the_work_item.work_item_id)
    the_question = what_the_gate_was_asking_about(a_register, the_work_item.work_item_id)
    the_last_refusal = _the_most_recent_refusal(the_decisions)

    return ACardOnTheBoard(
        work_item_id=the_work_item.work_item_id,
        repository=the_work_item.repository,
        title=_the_title_of(the_work_item),
        who_asked=the_work_item.commissioned_by,
        discipline=the_work_item.role,
        stage=the_work_item.stage,
        column=the_column_of(the_work_item),
        in_words=the_work_item.stage.in_words(),
        context=_the_context_of(the_decisions, the_notes, the_events),
        agent_holding_it=the_work_item.agent,
        artifact_it_is_waiting_about=the_question[0] if the_question else None,
        version_it_is_waiting_at=the_question[1] if the_question else None,
        why_it_was_refused=the_last_refusal.reason if the_last_refusal else None,
        who_refused_it=the_last_refusal.decided_by if the_last_refusal else None,
        asked_about=_where_the_request_can_be_read(the_work_item),
        how_many_gates_it_has_been_through=len(the_decisions),
    )


def _the_title_of(the_work_item: WorkItem) -> str:
    """What a card is titled, which is what somebody asked for.

    **The request's own title and never the work item's id.** A board of a hundred cards is read
    by scanning, and an id is a name for this system's record rather than a description of the
    work.

    **`the_work_item` rather than its request, and the refusal is where a card becomes a card.**
    `WorkItem.requested` is optional in the domain because the engine's unit tests build work
    items directly, but a card with no title is a blank the board has to render, and a board
    rendering a blank is indistinguishable from a run that stopped without saying why. So this
    refuses a work item nobody asked for rather than inventing a subject for it.
    """
    return _the_request_on(the_work_item).title


def _where_the_request_can_be_read(the_work_item: WorkItem) -> str | None:
    """The address GitHub answered with, or `None` for a request out of a sentence."""
    return _the_request_on(the_work_item).where_it_can_be_read()


def _the_request_on(the_work_item: WorkItem) -> CommissionedRequest:
    """The request this work item answers, or a refusal that it does not answer one."""
    if the_work_item.requested is None:
        raise AWorkItemNobodyAskedForError(
            f"{the_work_item.work_item_id!r} is on the board without saying what was asked "
            "for, and a card is titled by its request. The register already refuses a work "
            "item like this on the way in, so reaching this means one was constructed without "
            "going through it"
        )
    return the_work_item.requested


def _the_most_recent_refusal(
    the_decisions: Sequence[ApprovalDecision],
) -> ApprovalDecision | None:
    """The last answer that was no, or `None` when every answer so far was yes.

    **The last one and not the first,** because a run that was refused at the third gate and then
    approved the fourth is working, and a card still showing the third gate's refusal would be a
    card about a stop that has not happened.
    """
    refusals = [a_decision for a_decision in the_decisions if not a_decision.approved]
    return refusals[-1] if refusals else None


def _the_context_of(
    the_decisions: Sequence[ApprovalDecision],
    the_notes: Sequence[AComment],
    the_events: Sequence[WhatARunSaid],
) -> TheContextARunHasAccumulated:
    """The three counts and the word sum, read from everything the store holds about this run.

    **Words counted from the text itself and not from a length a caller computed.** A note is
    three sentences and an event is one line, and counting characters would make a run that said
    little look like one that produced a lot.
    """
    everything_was_said = (
        [a_note.what_was_said for a_note in the_notes]
        + [an_event.what_happened for an_event in the_events]
        + [a_decision.reason for a_decision in the_decisions]
    )

    return TheContextARunHasAccumulated(
        how_many_gates_were_answered=len(the_decisions),
        how_many_notes_were_left=len(the_notes),
        how_many_things_the_run_said=len(the_events),
        how_many_words_were_produced=sum(len(words) for words in everything_was_said),
    )

