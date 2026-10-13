"""Starting a run for a work item a briefing filed, rather than for a sentence somebody typed.

**This is the glue the autonomous loop was missing.** A briefing files issues and commissions
a work item for each one at `READY`, carrying the number and the address GitHub returned in
`requested.filed_as`. Nothing started those work items: `POST /api/runs` commissions *and*
starts a run for a sentence, while the picks path only commissioned. So a filed issue sat in
`TO_DISCUSS` with no graph walking it, and the only way to work it was to retype its words as
a new sentence — which produced a second work item with no filing, a branch named after the
run instead of the issue, and a pull request body with no traceability section.

**Loading and starting are one caller's two steps, and this module is the first.** It reads
the registered work item and refuses anything that is not a filed filing waiting to be worked:
no such work item, no filing on it, or already delivered. Starting itself stays with the
caller — the API holder or the terminal walk — because a library that started threads would
make a unit test hold a graph, while a library that only loads makes the refusal the fact
under test.
"""

from __future__ import annotations

from aisdlc.domain.stage import Stage
from aisdlc.domain.work_item import WorkItem
from aisdlc.store.the_register_of_work_items import (
    NoSuchWorkItemError,
    the_work_item_registered_at,
    the_work_items_this_register_holds,
)
from aisdlc.store.where_the_register_lives import holding_the_register


class NotAFiledWorkItemError(Exception):
    """This work item was not filed as an issue, so there is nothing to work here.

    **Refused rather than started anyway.** A run started for an unfiled work item would be
    a second run for words that already have one, with a branch and a pull request body that
    say nothing about the filing — the exact traceability this module exists to keep.
    """


class AFiledWorkItemThatIsAlreadyDoneError(Exception):
    """This filing is already delivered, so starting it again would be a second delivery.

    **Refused rather than re-run.** A delivered filing has a merged pull request behind it;
    walking it again would push a second branch for the same issue and open a second pull
    request closing the same number.
    """


def a_filed_work_item_to_start(work_item_id: str) -> WorkItem:
    """The registered work item this filing commissioned, ready to be walked.

    **Read from the register and not built.** The filing already commissioned it at `READY`
    with `requested.filed_as` carrying GitHub's own number and address; rebuilding it here
    would be a second commission of the same identifier, and the register's own rule is that
    a second commission never overwrites.
    """
    with holding_the_register() as register:
        the_work_item = the_work_item_registered_at(register, work_item_id)

    if the_work_item.requested is None or the_work_item.requested.filed_as is None:
        raise NotAFiledWorkItemError(
            f"{work_item_id!r} was commissioned from a sentence rather than filed as an "
            "issue, so it has no filing to answer. Start it from its own run instead — a "
            "run started here would carry no issue number into its branch or its pull request"
        )

    if the_work_item.stage is Stage.DONE:
        raise AFiledWorkItemThatIsAlreadyDoneError(
            f"{work_item_id!r} is already delivered, so there is nothing to start. A filing "
            "that is worked again after its merge would open a second pull request closing "
            "the same issue"
        )

    return the_work_item


def the_ready_filings() -> list[WorkItem]:
    """Every filed work item still at `READY`, oldest commission first.

    **Filed and waiting, and nothing else.** A work item past `READY` already has a graph
    walking it or a decision behind it; starting it again would be a second run for one
    filing. The register orders by identifier, and a filing's identifier carries its issue
    number first, so this is also roughly issue order.
    """
    with holding_the_register() as register:
        the_work_items = the_work_items_this_register_holds(register)

    return [
        the_work_item
        for the_work_item in the_work_items
        if the_work_item.stage is Stage.READY
        and the_work_item.requested is not None
        and the_work_item.requested.filed_as is not None
    ]


__all__ = [
    "AFiledWorkItemThatIsAlreadyDoneError",
    "NoSuchWorkItemError",
    "NotAFiledWorkItemError",
    "a_filed_work_item_to_start",
    "the_ready_filings",
]
