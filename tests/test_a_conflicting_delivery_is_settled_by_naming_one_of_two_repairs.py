"""A delivery GitHub will not merge is settled by naming one of two repairs, and by doing it.

**`WhatToDoAroundAConflict` existed with no caller, and the reason it had none was a missing git
operation rather than a missing node.** The only conflict a delivery reaches is a pull request that
conflicts with its base, and one of its two repairs needs a rebase — which this repository could
not perform. The tool is now here, so what is left is the half that was always going to be a node:
ask the model, and do what it chose.

**Three refusals and one decision, and the node names the destination on every outcome.** A merge
refused as a conflict does not end the run here; it hands the conflict over, in GitHub's own words,
and stops. That is the same rule the implementer and the delivery already follow — a node that
returns `Command(goto=...)` carries no edge, because an edge fires *alongside* the `goto` and
every repair in this system died of exactly that — so this one names where the run goes on a
success as well, and `test_no_node_that_chooses_its_own_destination_still_carries_an_edge` was
widened to hold it.

**Rebasing sends the run back to the suite rather than to the merge, and that is the whole
argument.** The merge is handed the commit the checks were read about, and a rebase produces a
different commit — so the repair goes to the node that reads the checks *on the commit the pull
request now points at*. From there the run merges only if something proved that commit, and stops
with the suite's own refusal if nothing has. **A repair that skipped the suite would be merging a
commit no check ever ran on**, which is the one thing the two nodes above the delivery exist to
prevent.

**Leaving it open is not `DONE`, and that is not a detail of the wiring.** `DONE` in this
repository means merged. A run whose pull request was left open with the reason on the card ends at
`write_how_this_run_ended` with its work item still at `AWAITING_HUMAN_APPROVAL`, which is the
truth: nothing landed in somebody else's repository, so nothing may claim that it did.

**What ends the run is bounded, and the bound is the tool's.** A rebase that would change nothing is
refused by `rebase_the_branch_a_run_pushed`, so a merge refused as a conflict twice running cannot
be asked about twice: the second visit finds the branch already carrying the branch it would join
and stops. The refusal is not a coincidence of this fixture; it is the only thing between this node
and a walk until the runtime's recursion limit.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from langgraph.types import Command

from aisdlc.agents.what_to_do_around_a_conflict import (
    WhatKindOfConflict,
    WhatToDoAroundAConflict,
    WhatToDoWhenThePullRequestCannotBeMerged,
)
from aisdlc.application.a_run_being_assembled import a_run_beginning_at
from aisdlc.domain.commissioned_request import a_request_about
from aisdlc.domain.repository import Repository
from aisdlc.domain.role import Role
from aisdlc.domain.work_item import a_work_item_commissioned_for_an_agent
from aisdlc.graph.agent_state import WHAT_STOPPED_THIS_RUN
from aisdlc.graph.router import THE_RUN_IS_OVER
from aisdlc.store.the_record_of_a_run import the_events_this_run_produced
from aisdlc.store.the_register_of_work_items import the_work_item_a_commission_registers
from aisdlc.store.where_the_register_lives import holding_the_register, the_register_lives_at
from aisdlc.tools.github_clone_repository import ClonedRepository
from aisdlc.tools.github_create_pull_request import AnOpenedPullRequest
from aisdlc.tools.merge_a_pull_request import (
    ThePullRequestIsInConflictError,
    WhatTheMergeLanded,
)
from aisdlc.tools.rebase_the_branch_a_run_pushed import WhatTheRebaseLeft

A_REPOSITORY = Repository(owner="an", name="owner")
AN_OPENED_PULL_REQUEST = AnOpenedPullRequest(number=7, address="local://an/owner/pull/7")
THE_COMMIT_THE_SUITE_WENT_GREEN_ON = "1" * 40
THE_BRANCH_THIS_RUN_DELIVERS_ON = "aisdlc/issue-1-a-conflicting-delivery"
A_WORK_ITEM_ID = "a-conflicting-delivery"

WHAT_GITHUB_SAYS_ABOUT_A_CONFLICT = (
    "GitHub says pull request 7 of an/owner conflicts with the branch it would join, and it "
    "cannot be merged as it stands. The commit it would have landed is "
    f"{THE_COMMIT_THE_SUITE_WENT_GREEN_ON}. This is a conflict and not a refusal: a protected base "
    "branch is refused instead, and GitHub words the two the same way, which is why this is read "
    "from the field and not from the message"
)


def _the_suite_went_green_on_the_commit():
    """The suite's answer as the node above the merge left it, because the merge is pinned to it."""
    from aisdlc.tools.the_suite_went_green import WhatTheSuiteSaid

    return WhatTheSuiteSaid(
        head_commit=THE_COMMIT_THE_SUITE_WENT_GREEN_ON, which_checks_went_green=["the_gate"]
    )


def _a_state_whose_merge_was_refused_as_a_conflict(tmp_path: Path, monkeypatch) -> dict:
    """A registered run that delivered, whose merge GitHub refused because the branch conflicts."""
    monkeypatch.setenv("AISDLC_PROJECTS_DIR", str(tmp_path / "projects"))
    the_register_lives_at(tmp_path / "the-register.sqlite3")
    the_work_item = a_work_item_commissioned_for_an_agent(
        work_item_id=A_WORK_ITEM_ID,
        repository=A_REPOSITORY,
        accountable_role=Role.DEV,
        commissioned_by="a person reading a test",
        requested=a_request_about("add a health endpoint", ""),
    )
    with holding_the_register() as a_register:
        the_work_item_a_commission_registers(a_register, the_work_item)
    return {
        **a_run_beginning_at(the_work_item, tmp_path / "projects"),
        "clone": ClonedRepository(path=tmp_path / "the-clone", ref="main", commit="a" * 40),
        "opened_pull_request": AN_OPENED_PULL_REQUEST,
        "pull_request_request": _a_request_for_this_delivery(tmp_path),
        "what_the_suite_said": _the_suite_went_green_on_the_commit(),
        WHAT_STOPPED_THIS_RUN: WHAT_GITHUB_SAYS_ABOUT_A_CONFLICT,
    }


def _a_request_for_this_delivery(tmp_path: Path):
    """The approved delivery: which branch this run delivers on, and which one it would join."""
    from aisdlc.agents.pull_request_request import PullRequestRequest

    return PullRequestRequest(
        repository=A_REPOSITORY,
        work_item_id=A_WORK_ITEM_ID,
        branch=THE_BRANCH_THIS_RUN_DELIVERS_ON,
        base="main",
        title="add a health endpoint",
        body="what changed",
    )


def _what_the_run_said(tmp_path: Path) -> list[str]:
    with holding_the_register() as a_register:
        return [
            an_event.what_happened
            for an_event in the_events_this_run_produced(a_register, A_WORK_ITEM_ID)
        ]


def _a_decision_choosing(
    which: WhatToDoWhenThePullRequestCannotBeMerged, why: str
) -> WhatToDoAroundAConflict:
    return WhatToDoAroundAConflict(
        about=WhatKindOfConflict.THE_PULL_REQUEST_CANNOT_BE_MERGED, which=which, why=why
    )


def _a_merge_git_hub_refused_as_a_conflict() -> tuple[list, object]:
    """The merge, recording what it was handed, and refusing as GitHub would have refused."""
    what_it_was_handed: list[tuple] = []

    def merge(the_pull_request, repository, the_commit):
        what_it_was_handed.append((the_pull_request, repository, the_commit))
        raise ThePullRequestIsInConflictError(WHAT_GITHUB_SAYS_ABOUT_A_CONFLICT)

    return what_it_was_handed, merge


def _the_node():
    """The node under test, imported where a missing module fails on a statement about it.

    **A refusal in words rather than an import error,** because a stack naming a module that does
    not exist says nothing about the rule this file is about, and a test that fails on an import
    has not yet asked a question.
    """
    try:
        from aisdlc.graph import settle_a_conflict_node
    except ImportError:
        pytest.fail(
            "there is no node that settles a conflict by naming one of two repairs. GitHub says a "
            "pull request conflicts, this repository has the question and the two repairs written "
            "down and tested, and nothing connects them — so the decision is a contract with no "
            "caller and the only conflict a delivery reaches has no way out of itself"
        )
    return settle_a_conflict_node


def _where_a_conflict_is_settled() -> str:
    """The node a merge hands a conflict to, or a refusal saying the name does not exist yet."""
    from aisdlc.graph import merge_node

    if not hasattr(merge_node, "WHERE_A_CONFLICT_IS_SETTLED"):
        pytest.fail(
            "a merge refused as a conflict has nowhere to go: the graph names no node for settling "
            "one, so GitHub's own sentence about the conflict ends the run instead of being "
            "decided about"
        )
    return merge_node.WHERE_A_CONFLICT_IS_SETTLED


def test_a_merge_refused_as_a_conflict_hands_the_run_to_the_repair(tmp_path, monkeypatch) -> None:
    """GitHub's own words travel to the node that can act on them, and the run does not carry on.

    **What is handed over is the refusal and not a summary of it.** A decision made on a summary
    of a conflict is a decision about the summary, and this repository has already had one of those
    read like a fact about the code. The state channel is the one the repair supervisor already uses
    for exactly this, so there is one place a refusal travels rather than two.
    """
    from aisdlc.graph import merge_node

    what_it_was_handed, merge = _a_merge_git_hub_refused_as_a_conflict()
    the_state = _a_state_whose_merge_was_refused_as_a_conflict(tmp_path, monkeypatch)
    where_a_conflict_goes = _where_a_conflict_is_settled()

    what_it_did = _the_return_of_a_merge_that_was_refused(
        merge_node, the_state, merge, where_a_conflict_goes
    )

    assert what_it_was_handed == [
        (AN_OPENED_PULL_REQUEST, A_REPOSITORY, THE_COMMIT_THE_SUITE_WENT_GREEN_ON)
    ]
    assert isinstance(what_it_did, Command), (
        "the merge did not hand the conflict over, so the run ends at the node that records how it "
        "stopped, carrying GitHub's sentence as a bare traceback rather than as a decision made "
        "about it — and `DONE` means merged, so a run cannot claim to have got there either"
    )
    assert what_it_did.goto == where_a_conflict_goes, (
        f"a merge refused as a conflict went to {what_it_did.goto!r} rather than to the node that "
        "can settle it, so the decision about what to do with it is made by nobody"
    )
    assert what_it_did.update[WHAT_STOPPED_THIS_RUN] == WHAT_GITHUB_SAYS_ABOUT_A_CONFLICT, (
        "the run was handed something other than GitHub's own sentence about the conflict, and a "
        "decision made on a summary of a conflict is a decision about the summary"
    )


def test_the_model_is_asked_which_conflict_it_is_deciding_about(tmp_path, monkeypatch) -> None:
    """The question names the conflict and quotes GitHub, so the answer is about this situation.

    **Both halves, and the second is the one that goes stale.** Asking "what should we do about
    this?" would work the day there is one kind of conflict and stop working the day there are
    three — and this repository already has three closed sets of repairs with a refusal for using
    one conflict's repair about another.
    """
    settle_the_conflict_in_this_run = _the_node().settle_the_conflict_in_this_run

    what_it_was_asked: list[tuple] = []

    def settling(about, what_is_known):
        what_it_was_asked.append((about, what_is_known))
        return _a_decision_choosing(
            WhatToDoWhenThePullRequestCannotBeMerged.LEAVE_IT_OPEN_AND_SAY_WHY,
            "the base branch is protected on purpose",
        )

    settle_the_conflict_in_this_run(
        _a_state_whose_merge_was_refused_as_a_conflict(tmp_path, monkeypatch),
        settling,
        _a_rebase_that_must_not_be_called(),
    )

    assert what_it_was_asked == [
        (
            WhatKindOfConflict.THE_PULL_REQUEST_CANNOT_BE_MERGED,
            WHAT_GITHUB_SAYS_ABOUT_A_CONFLICT,
        )
    ], (
        f"the model was asked {what_it_was_asked!r}, which is not the conflict this run holds and "
        "not GitHub's own words about it — so the decision is about a situation nobody put to it"
    )


def _the_return_of_a_merge_that_was_refused(
    merge_node, the_state, merge, where_a_conflict_goes: str
) -> Command:
    """The merge's return, or a statement that it refused to hand the conflict over at all.

    **The conflict GitHub raised is the reason a reader needs here**, because until the node hands
    it over that exception *is* the behaviour: a run that ends with GitHub's sentence in a
    traceback has not decided anything, and a test that only showed the raised error would not say
    what the run should have done instead.
    """
    try:
        return merge_node.merge_the_delivery_in_this_run(the_state, merge)
    except ThePullRequestIsInConflictError as conflict:
        pytest.fail(
            f"the merge let GitHub's conflict end the run instead of handing it to "
            f"{where_a_conflict_goes!r}: {conflict}"
        )
    raise AssertionError("unreachable")


def _a_rebase_that_must_not_be_called():

    def rebase(wanted):
        pytest.fail(
            f"the run rebased {wanted.the_branch_this_run_pushed!r} even though the model chose to "
            "leave the pull request open, so a decision about a delivery was not the decision that "
            "was acted on"
        )

    return rebase


def test_rebasing_asks_about_the_commit_the_pull_request_now_points_at(
    tmp_path, monkeypatch
) -> None:
    """The repair puts the commit on the branch it joins, and sends the run to the suite.

    **The destination is the assertion, and the rebase is what makes it necessary.** A rebase makes
    a different commit, and the merge is handed the commit the checks were read about — so a repair
    that went straight back to the merge would be asking GitHub to land a sha nothing was proved
    about, and GitHub refusing it (409) would be the only thing standing between a run and a merge
    of an unproved commit.
    """
    from aisdlc.graph import merge_node

    settle_the_conflict_in_this_run = _the_node().settle_the_conflict_in_this_run
    what_the_rebase_was_handed: list = []

    def rebasing(wanted):
        what_the_rebase_was_handed.append(wanted)
        return WhatTheRebaseLeft(the_commit_it_was="a" * 40, the_commit_it_is_now="b" * 40)

    where_the_run_went = settle_the_conflict_in_this_run(
        _a_state_whose_merge_was_refused_as_a_conflict(tmp_path, monkeypatch),
        lambda about, what_is_known: _a_decision_choosing(
            WhatToDoWhenThePullRequestCannotBeMerged.REBASE_IT_AND_TRY_AGAIN,
            "the base moved on and this delivery is worth replaying on it",
        ),
        rebasing,
    )

    assert len(what_the_rebase_was_handed) == 1
    assert (
        what_the_rebase_was_handed[0].the_branch_this_run_pushed == THE_BRANCH_THIS_RUN_DELIVERS_ON
    ), (
        "the rebase was handed a branch other than the one this run delivered, so the branch that "
        "conflicts is the one somebody has to go and find"
    )
    assert what_the_rebase_was_handed[0].the_branch_it_would_join == "main"
    assert where_the_run_went.goto == merge_node.WHERE_THE_SUITE_WENT_GREEN, (
        f"after rebasing, the run went to {where_the_run_went.goto!r} rather than to the node that "
        "reads the checks on the commit the pull request now points at — so the only thing between "
        "a rebased commit and a merge is the merge's own refusal"
    )


def test_leaving_it_open_says_why_and_never_says_it_was_merged(tmp_path, monkeypatch) -> None:
    """The other repair ends the run with the reason on it, and does not claim a delivery happened.

    **The run's own record is what a person reads**, so the sentence has to name the conflict, the
    repair and the model's reason — the model having written the reason is the one thing that makes
    a decision about somebody else's repository arguable afterwards.
    """
    settle_the_conflict_in_this_run = _the_node().settle_the_conflict_in_this_run
    the_reason = "the base branch is protected on purpose, so a rebase would land in nothing"

    where_the_run_went = settle_the_conflict_in_this_run(
        _a_state_whose_merge_was_refused_as_a_conflict(tmp_path, monkeypatch),
        lambda about, what_is_known: _a_decision_choosing(
            WhatToDoWhenThePullRequestCannotBeMerged.LEAVE_IT_OPEN_AND_SAY_WHY, the_reason
        ),
        _a_rebase_that_must_not_be_called(),
    )

    assert where_the_run_went.goto == THE_RUN_IS_OVER, (
        f"leaving a conflicting pull request open sent the run to {where_the_run_went.goto!r}, and "
        "the next thing after the delivery is a move to `DONE` — so this run would claim a merge "
        "that never happened"
    )
    what_was_said = " ".join(_what_the_run_said(tmp_path))
    assert the_reason in what_was_said, (
        "the run's own record does not carry the reason the model gave, so the decision that was "
        "made about somebody else's repository cannot be argued with afterwards"
    )
    what_to_leave_it_open = WhatToDoWhenThePullRequestCannotBeMerged.LEAVE_IT_OPEN_AND_SAY_WHY.value
    assert what_to_leave_it_open in what_was_said, (
        "the record does not name which repair was chosen, so a reader is left with a reason and "
        "no decision"
    )


def test_the_repair_moves_no_work_item(tmp_path, monkeypatch) -> None:
    """One writer of a work item, and this node is not it.

    **The channels are read and never written.** `transition_the_work_item` is the only node that
    may change a stage, and `DONE` in particular is asked for by `mark_the_work_item_delivered` —
    so a repair that wrote either would be a second door into the table, reached from a place
    nobody would look for it.
    """
    settle_the_conflict_in_this_run = _the_node().settle_the_conflict_in_this_run

    what_the_repair_wrote = settle_the_conflict_in_this_run(
        _a_state_whose_merge_was_refused_as_a_conflict(tmp_path, monkeypatch),
        lambda about, what_is_known: _a_decision_choosing(
            WhatToDoWhenThePullRequestCannotBeMerged.LEAVE_IT_OPEN_AND_SAY_WHY,
            "a protected base branch cannot be merged into at all",
        ),
        _a_rebase_that_must_not_be_called(),
    )

    the_channels_the_repair_wrote = set(what_the_repair_wrote.update or {})
    what_the_single_writer_owns = ("work_item", "requested_stage", "requested_agent")
    assert not set(what_the_single_writer_owns) & the_channels_the_repair_wrote, (
        "the node that settled a conflict wrote a work item channel, and `DONE` is a stage only "
        "one node may ask for"
    )


def test_a_run_with_no_conflict_in_it_is_refused_rather_than_decided_about(
    tmp_path, monkeypatch
) -> None:
    """There is nothing to decide about, and a decision made about nothing is still a decision.

    **Refused rather than defaulted.** A node reaching this without a conflict means the wiring
    sent it there, and asking a model what to do about a conflict this run does not have would put
    a sentence on the card about a situation that never happened.
    """
    settle_the_conflict_in_this_run = _the_node().settle_the_conflict_in_this_run
    the_run_has_no_conflict = _the_node().TheRunHasNoConflictToSettleError

    the_state = _a_state_whose_merge_was_refused_as_a_conflict(tmp_path, monkeypatch)
    the_state[WHAT_STOPPED_THIS_RUN] = None

    with pytest.raises(the_run_has_no_conflict):
        settle_the_conflict_in_this_run(
            the_state,
            lambda about, what_is_known: pytest.fail("a model was asked about nothing"),
            _a_rebase_that_must_not_be_called(),
        )


def test_a_merge_that_succeeds_never_reaches_the_repair(tmp_path, monkeypatch) -> None:
    """The repair is for a conflict and nothing else, so a merged delivery does not mention it.

    **A node that runs on both outcomes is a node whose second outcome is untested.** The merge
    still announces what GitHub landed, and announcing it next to a model being asked whether to
    rebase would be a card describing two different runs.
    """
    from aisdlc.graph import merge_node

    what_the_run_was_told: list[str] = []
    the_state = _a_state_whose_merge_was_refused_as_a_conflict(tmp_path, monkeypatch)

    what_it_did = merge_node.merge_the_delivery_in_this_run(
        the_state,
        lambda the_pull_request, repository, the_commit: WhatTheMergeLanded(
            commit=the_commit, what_github_said="Pull Request successfully merged"
        ),
    )
    what_the_run_was_told.extend(_what_the_run_said(tmp_path))

    assert isinstance(what_it_did, Command), (
        "the merge returned a plain state update rather than naming where the run goes next, so "
        "the graph has to be carrying an edge out of it — and a node that names its own "
        "destination and a node that is told its destination are two designs"
    )
    assert what_it_did.goto == "mark_the_work_item_delivered", (
        f"a merge that GitHub performed went to {what_it_did.goto!r}, and the only thing that "
        "follows a delivery on this path is a run asking to be marked delivered — so a merge that "
        "worked would stop short of saying so"
    )
    assert not any("rebasing" in what_was_said for what_was_said in what_the_run_was_told)
