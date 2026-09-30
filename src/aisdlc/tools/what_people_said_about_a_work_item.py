"""What people have said about a work item, and who is accountable for the next thing.

**A comment is not an approval, and the difference is structural rather than a matter of
wording.** An `ApprovalDecision` carries an `artifact_id`, an `artifact_version` and an `approved`
flag: it says which exact document was ruled on, and a later change to that document invalidates
it. A comment carries none of the three, so **it cannot be read as approving anything** — there is
nothing to mistake. A system where "approved" and "somebody wrote something" were the same claim
would have no gates at all.

**The assignee is a fact about a person, and it is kept off the work item.** `WorkItem` is a type
the state machine validates: its stage and its agent are bound together by the biconditional, and
who is accountable for the next thing belongs to neither. Putting a name on it would put a human
fact into a type whose whole value is that nothing can set its state but `transition`.

**So both live in one record beside the work item, and a card reads them.** They are the same kind
of thing: something a person said about the work. The work item is what the machine governs; this
is what people said about it.

**An absent record is an empty one, not a failure.** Nobody has commented and nobody has been
assigned more often than not, and a board that refused to show such a card would show almost
nothing.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from aisdlc.domain.commissioned_request import CommissionedRequest
from aisdlc.domain.repository import Repository
from aisdlc.domain.stage import Stage
from aisdlc.domain.work_item import WorkItem
from aisdlc.store.what_a_run_records import the_note_was_recorded
from aisdlc.tools.the_column_of_a_card import AColumnOfTheBoard, the_column_of
from aisdlc.tools.the_project_directory import the_project_directory_of

A_FILE_EXTENSION_A_PERSON_CAN_READ = ".json"
WHERE_PEOPLES_OWN_WORDS_ARE_KEPT = "WhatPeopleSaidAboutAWorkItem.json"


class AComment(BaseModel):
    """One note, who left it, and when.

    **Three fields, and the three an approval also has are deliberately not among them.** The
    absence is the guarantee: a comment cannot name an artifact, cannot carry a version and cannot
    carry a verdict, so nothing downstream can mistake one for a decision at a gate.

    **`extra="forbid"` as well as `frozen`, and the absence alone was not enough.** Frozen blocks
    `__setattr__` and says nothing about what a constructor accepts, so
    `AComment(…, approved=True)` was accepted and the keyword silently dropped — a caller that meant
    to record an approval holding a comment, with nothing recording the mistake. **Silently
    discarding a field is a fallback with a position**, and this repository raises rather than
    defaults in three other places for exactly that reason: a stage with no column, a runner that
    announced nothing, a card that fell through.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    what_was_said: str
    said_by: str
    said_at: datetime


class WhatPeopleSaidAboutAWorkItem(BaseModel):
    """Everything a person has said about one work item, and who is accountable for it.

    **`extra="forbid"` for the same reason its comments carry it.** A comment that refuses a stray
    keyword and a record that swallows one would make the refusal a property of the leaf and leave
    the path open above it — and this is the value written to disk and read back months later, so a
    field that vanished between the two is a question nobody can answer then.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    about: str
    comments: list[AComment] = Field(default_factory=list)
    assignee: str | None = None


def what_people_said_about(
    repository: Repository, work_item_id: str, projects_root: Path
) -> WhatPeopleSaidAboutAWorkItem:
    """What is recorded beside this work item, or an empty record when nothing is.

    **An absent file is an empty record, because a board showing nothing must still show a
    card.** Raising here would make "nobody has commented" indistinguishable from "the record is
    broken", and the second of those is worth stopping for while the first is not.
    """
    the_record = (
        projects_root / repository.owner / repository.name / work_item_id
    ) / WHERE_PEOPLES_OWN_WORDS_ARE_KEPT

    if not the_record.is_file():
        return WhatPeopleSaidAboutAWorkItem(about=work_item_id)

    return WhatPeopleSaidAboutAWorkItem.model_validate_json(
        the_record.read_text(encoding="utf-8")
    )


def a_comment_was_left(
    work_item: WorkItem,
    what_was_said: str,
    by: str,
    at: datetime,
    projects_root: Path,
) -> WhatPeopleSaidAboutAWorkItem:
    """Leave a note on this work item, and hand back the record as it now reads.

    **Sorted by when it was said rather than appended in the order it arrived.** A comment left
    while a run was going and read afterwards is older than one left after it, and the only order
    anybody reading them would find wrong is the one the file system would give.

    **The same note is also announced to the register.** A supervisor is handed this record and a
    board renders this record, and they are two readers of one thing — so the note is written
    once, here, and the two readers are handed the same words. A board that read its own copy
    could show a note the supervisor never saw.
    """
    the_record = what_people_said_about(
        work_item.repository, work_item.work_item_id, projects_root
    )
    with_the_note = the_record.model_copy(
        update={
            "comments": sorted(
                [
                    *the_record.comments,
                    AComment(what_was_said=what_was_said, said_by=by, said_at=at),
                ],
                key=lambda comment: comment.said_at,
            )
        }
    )
    _the_record_is_kept_at(with_the_note, work_item, projects_root)
    the_note_was_recorded(work_item, by, what_was_said)

    return with_the_note


def the_work_item_is_assigned_to(
    work_item: WorkItem, who: str, projects_root: Path
) -> WhatPeopleSaidAboutAWorkItem:
    """Say who is accountable for the next thing, which is a fact about a person.

    **And not a third way of holding the work.** The agent is bound to the stage by the
    biconditional and `transition` is the only door for it; a name assigned here moves nothing and
    claims nothing about the run, so this cannot become a way around a gate.
    """
    the_record = what_people_said_about(
        work_item.repository, work_item.work_item_id, projects_root
    )
    with_the_name = the_record.model_copy(update={"assignee": who})
    _the_record_is_kept_at(with_the_name, work_item, projects_root)

    return with_the_name


def the_card_showing_what_people_said(
    work_item: WorkItem, projects_root: Path
) -> TheCardShowingWhatPeopleSaid:
    """A card with the column the stage implies, the assignee, and the notes.

    **The column is read here and not carried from the plain card**, so there is one rule about
    where a card sits and it is `the_column_of`. A second builder that could decide a column would
    put the same work item in two places depending on which function happened to show it.
    """
    the_record = what_people_said_about(
        work_item.repository, work_item.work_item_id, projects_root
    )

    return TheCardShowingWhatPeopleSaid(
        work_item_id=work_item.work_item_id,
        requested=work_item.requested,
        commissioned_by=work_item.commissioned_by,
        stage=work_item.stage,
        column=the_column_of(work_item),
        held_by=work_item.agent,
        assignee=the_record.assignee,
        comments=the_record.comments,
        where_it_recorded_itself=the_project_directory_of(work_item, projects_root),
    )


class TheCardShowingWhatPeopleSaid(BaseModel):
    """A card that also carries what people have said about the work item.

    **Frozen, for the same reason the plain card is**: a card that could be edited would be a
    second place the stage could be set, through the one door this system permits.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    work_item_id: str
    requested: CommissionedRequest | None
    commissioned_by: str
    stage: Stage
    column: AColumnOfTheBoard
    held_by: str | None
    assignee: str | None
    comments: list[AComment]
    where_it_recorded_itself: Path


def _the_record_is_kept_at(
    the_record: WhatPeopleSaidAboutAWorkItem, work_item: WorkItem, projects_root: Path
) -> None:
    """Beside the run's own records, as JSON, because this is a record and not a feature."""
    the_directory = the_project_directory_of(work_item, projects_root)

    where = the_directory / WHERE_PEOPLES_OWN_WORDS_ARE_KEPT
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(
        json.dumps(the_record.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
