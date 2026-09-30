"""Where this system's own runs are kept, and the rule that keeps them out of a pull request.

Two facts, and the second is the one that does the work.

**A hidden folder keeps our runs out of a reader's way.** `.aisdlc` at the top of a
repository is not part of that repository's subject, so a directory whose name begins with
a dot is the honest place for it: every tool that lists a project already skips it.

**A separate branch keeps them out of a diff.** This is the part that is easy to get
backwards, so it is worth stating plainly: hiding the folder has nothing to do with the
pull request. A pull request shows the difference between its base and its head, and a
hidden folder on that branch is in the diff exactly as loudly as a visible one. What keeps
our runs out of the diff is that they live on a branch no product pull request is opened
from.
"""

from __future__ import annotations

import re

from aisdlc.domain.work_item import WorkItem

OUR_OWN_FOLDER = ".aisdlc"
THE_BRANCH_OUR_OWN_RUNS_LIVE_ON = "aisdlc/runs"

A_PRODUCT_BRANCH_IS_NAMED_AFTER_ITS_WORK = "aisdlc/wellbeingt-{number}"
THE_NAME_OF_A_TICKET = re.compile(r"\d+$")
OUR_NAMESPACE = "aisdlc"
A_NAME_A_BRANCH_MAY_BE = re.compile(r"[A-Za-z0-9._-]+")


class AWorkItemIdThatCannotNameABranchError(Exception):
    """The rule is in `a_delivery_branch_named`, and only it may say the rule broke.

    Named rather than a bare `ValueError` for the reason every error in this repository is
    named: a caller reading `ValueError: invalid value` learns nothing about which rule it
    broke, and this one is a decision about what a delivery is called rather than a parse
    failure of a string.
    """


def is_ours(path: str) -> bool:
    """Whether a path is one of our own, rather than one of the product's.

    A whole leading segment, not a substring: a repository can have a directory called
    `.aisdlc` inside its own source tree, and a check that matched the name anywhere
    would call a product file ours over a coincidence.
    """
    return path == OUR_OWN_FOLDER or path.startswith(f"{OUR_OWN_FOLDER}/")


def a_delivery_branch_named(work_item_id: str) -> str:
    """The branch one work item's delivery is cut onto, named `aisdlc/<work item id>`.

    **The work item's id and not a ticket**, because the tracker this deployment points at is
    a self-hosted Plane it cannot read, and a `WELLBEINGT-NNN` on a branch whose work has
    nothing to do with it is a false reference in an audit trail. The work item's id is ours,
    unique per run, and needs no model to derive.

    Refused rather than sanitised where it cannot be a branch name at all. `../../etc` as a
    branch is a ref that resolves outside the repository, and a slash reads as a directory to
    everything that walks refs; the rule is here rather than at the push because the push is
    where a bad name stops being a string and becomes a ref.
    """
    if not work_item_id.strip() or not A_NAME_A_BRANCH_MAY_BE.fullmatch(work_item_id):
        raise AWorkItemIdThatCannotNameABranchError(
            f"a work item's id has to name a branch, and {work_item_id!r} cannot: a branch is "
            "one path segment of letters, digits, dots, dashes and underscores, and a run's id "
            "is what it is called"
        )
    return f"{OUR_NAMESPACE}/{work_item_id}"


def a_product_branch_named(ticket: int) -> str:
    """The branch a delivery for one ticket is cut onto.

    Named after the ticket rather than after the work item, because the ticket is what a
    person recognises in a list of branches and what a commit message already says.
    """
    return A_PRODUCT_BRANCH_IS_NAMED_AFTER_ITS_WORK.format(number=ticket)


def a_delivery_branch_for_a_filing(work_item: WorkItem) -> str:
    """The branch a delivery for a filed request is cut onto, named after the filing.

    **The word is the one the address uses, and that is the whole correction.** GitHub's own
    address is `…/issues/7`, so `aisdlc/issue-7` is read off the same place the words came from.
    `a_product_branch_named` says `aisdlc/wellbeingt-7` — a tracker name taken out of one
    repository's `.gitignore` — and naming a branch after a tracker this system was never told
    about is the guess the recorded departure is about.

    **The number first, then the run's own identity, and the second half is there because the first
    one collided.** The number is what a person recognises, and it is unqualified so a list of
    branches can be scanned; the suffix is the work item's id, which is already unique per run and
    already in the register. A second run for the same filing is an ordinary scenario — a retry
    after a review, two people on one ticket, a resumed run — and naming the branch after the filing
    alone made the second one undeliverable at the last step with
    `NothingToPushError: aisdlc/issue-1 is already on origin`, which says nothing about the
    plan, the change or the suite.

    **The address does not come into the branch at all.** An issue that was transferred keeps its
    number and answers elsewhere, and a branch is not a link — the address travels in the pull
    request's body where a reader can follow it.

    **Refused without a filing rather than defaulted.** A delivery with no request would need a
    number invented to fill this field, and an invented number on a branch is a reference to
    somebody else's issue that does not answer it — a false reference in the one thing a
    traceability chain exists to be. A caller that has no filing has the work item's own id to name
    the branch with, and that is what `a_delivery_branch_named` is for.
    """
    if work_item.requested is None or work_item.requested.filed_as is None:
        raise ValueError(
            f"{work_item.work_item_id!r} is not filed, so there is no number to name its branch "
            "after. Inventing one would put a reference to somebody else's issue on a branch that "
            "does not answer it, which is the failure this exists to undo; a run whose request was "
            "typed rather than filed should be named by its work item's own id instead."
        )
    return a_delivery_branch_named(
        f"issue-{work_item.requested.filed_as.number}-{work_item.work_item_id}"
    )
