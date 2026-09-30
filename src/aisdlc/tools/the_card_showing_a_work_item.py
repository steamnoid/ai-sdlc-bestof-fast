"""What the board shows for one work item.

**A card is a reading, and that is the whole of its design.** The column is read off the stage by
`the_column_of` rather than carried here, so a card cannot disagree with the work item it shows.
Every other field is either a fact about the work item or something said *about* it, and neither is
a second copy of the stage — the one thing a second copy of would be dangerous.

**It is built, not assembled by its caller.** A function taking both a work item and a column would
be one whose caller chooses the answer, and the caller is the thing this workstream refuses to
trust: a column a caller can pass is a gate a caller can walk past.

**The request comes along because a card that says `wellbeing-7` is not something anybody can act
on.** The id is a name this system chose; the request is the words a person typed.

**It may be absent, and the card says so.** A work item can be commissioned with no request, and
a card that showed a blank line where the words should be would be making a claim about work that
nobody described. `None` here means the same thing it means on the work item.

**The assignee is `null` more often than not, and that is the ordinary case.** Nobody has said who
is accountable for the next thing yet, and a card that invented somebody would be a claim about a
person's time this system is not entitled to make.

**Nothing here reads a run's artifacts.** A card that read the discovery report would be a second
thing to keep in step with what is on disk, and the directory is already the place where that is
true.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from aisdlc.domain.commissioned_request import CommissionedRequest
from aisdlc.domain.stage import Stage
from aisdlc.domain.work_item import WorkItem
from aisdlc.tools.the_column_of_a_card import AColumnOfTheBoard, the_column_of
from aisdlc.tools.the_project_directory import the_project_directory_of


class TheCardShowingAWorkItem(BaseModel):
    """One work item as the board shows it: what a person needs to decide whether to touch it.

    **Frozen, because a card is a reading and a card that could be edited would be a second place
    the stage could be set** — through the one door this system permits, which is `transition`.
    `ConfigDict` is here to say that in the only terms Pydantic has, and the field list carries no
    `column` to be edited even if this were not frozen.
    """

    # **Forbidding as well as frozen, and a card is where a lost field is least visible.** A card is
    # a *reading* of a work item, so a field that vanished shows less than the record holds and
    # nothing that says which. `column` above is refused here for a different reason and the same
    # one: a card's column is read off the stage, never carried in.
    model_config = ConfigDict(frozen=True, extra="forbid")

    work_item_id: str
    requested: CommissionedRequest | None
    commissioned_by: str
    stage: Stage
    column: AColumnOfTheBoard
    held_by: str | None
    assignee: str | None
    where_it_recorded_itself: Path


def the_card_showing(work_item: WorkItem, projects_root: Path) -> TheCardShowingAWorkItem:
    """The card for this work item, with its column read rather than chosen.

    **One argument that matters, and one that does not.** The work item decides the column, the
    stage and who holds it; the projects root only says where the run's own record is, and a
    caller passing a different column could not — there is no such argument to pass.
    """
    return TheCardShowingAWorkItem(
        work_item_id=work_item.work_item_id,
        requested=work_item.requested,
        commissioned_by=work_item.commissioned_by,
        stage=work_item.stage,
        column=the_column_of(work_item),
        held_by=work_item.agent,
        assignee=None,
        where_it_recorded_itself=the_project_directory_of(work_item, projects_root),
    )
