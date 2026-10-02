"""A run that delivered reads the suite, merges that commit, and only then says it is delivered.

**The eighth gate approves a delivery. What happens to that delivery on somebody else's repository
is a fact about the commit GitHub is holding, and this file is that fact.** Two nodes sit between
the delivery and the move to `DONE`: one asks whether the suite is green **on the commit being
merged**, and one merges that same commit. There is no ninth gate and no ninth decision, and the
table of legal transitions is untouched — the merge is the consequence of a gate that already
happened, not a question somebody has not answered yet.

**The two halves have to agree about one commit, and that is what the tests below hold.** A suite
read green for a head that has since moved is a green run about a commit nobody is merging, so the
answer travels in the state and the merge is handed that exact sha. A node that re-read the head
here would be racing the thing it is trying to prove, and the merge tool's own refusal is what
catches a head that moved anyway.

**Both nodes announce rather than approve, and they move nothing.** The single writer of a work
item is `transition_the_work_item`, and `mark_the_work_item_delivered` is what asks for `DONE`; a
stage that moved the work item would be a second door. What the two nodes say goes in the run's
own record — the timeline the board streams — because "green on <sha>" and "merged <sha>" are
facts about the world and not the judgement of an agent, which is why they are not notes on the
card: the pull request agent is on the list of agents that leave no note, and it still will be.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aisdlc.application.a_run_being_assembled import a_run_beginning_at
from aisdlc.domain.commissioned_request import a_request_about
from aisdlc.domain.repository import Repository
from aisdlc.domain.role import Role
from aisdlc.domain.work_item import a_work_item_commissioned_for_an_agent
from aisdlc.graph.merge_node import (
    TheDeliveryHasNotBeenOpenedError,
    TheSuiteWasNotReadBeforeTheMergeError,
    merge_the_delivery_in_this_run,
    the_suite_went_green_in_this_run,
)
from aisdlc.store.the_record_of_a_run import the_events_this_run_produced
from aisdlc.store.the_register_of_work_items import the_work_item_a_commission_registers
from aisdlc.store.where_the_register_lives import holding_the_register, the_register_lives_at
from aisdlc.tools.github_create_pull_request import AnOpenedPullRequest
from aisdlc.tools.merge_a_pull_request import WhatTheMergeLanded
from aisdlc.tools.the_suite_went_green import WhatTheSuiteSaid

A_REPOSITORY = Repository(owner="an", name="owner")
AN_OPENED_PULL_REQUEST = AnOpenedPullRequest(number=7, address="local://an/owner/pull/7")
THE_COMMIT_THE_SUITE_WENT_GREEN_ON = "1" * 40
A_WORK_ITEM_ID = "a-merge-standing-alone"


@pytest.fixture
def a_projects_root(tmp_path: Path, monkeypatch) -> Path:
    """A writable projects root and an open register, so what a node announces can be read back."""
    monkeypatch.setenv("AISDLC_PROJECTS_DIR", str(tmp_path / "projects"))
    the_register_lives_at(tmp_path / "the-register.sqlite3")
    return tmp_path / "projects"


def _a_state_that_delivered(a_projects_root: Path) -> dict:
    """A registered run holding a pull request it opened, which is what the suite is read for."""
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
        **a_run_beginning_at(the_work_item, a_projects_root),
        "opened_pull_request": AN_OPENED_PULL_REQUEST,
    }


def _what_the_run_said(a_projects_root: Path) -> list[str]:
    with holding_the_register() as a_register:
        return [
            an_event.what_happened
            for an_event in the_events_this_run_produced(a_register, A_WORK_ITEM_ID)
        ]


def test_the_suite_is_read_for_the_pull_request_this_run_opened(a_projects_root: Path) -> None:
    """The node asks about the run's own pull request, and the suite's answer goes in the state.

    **Both halves, and the state channel is the point.** The answer has to travel, because the
    merge is handed the commit out of it rather than looking one up again — and a node that looked
    it up again would be reading a head that may have moved since the checks ran.
    """
    what_it_was_handed: list[tuple[object, object]] = []
    the_suite = WhatTheSuiteSaid(
        head_commit=THE_COMMIT_THE_SUITE_WENT_GREEN_ON, which_checks_went_green=["the_gate"]
    )

    def ask(the_pull_request, repository):
        what_it_was_handed.append((the_pull_request, repository))
        return the_suite

    what_it_wrote = the_suite_went_green_in_this_run(
        _a_state_that_delivered(a_projects_root), ask
    )

    assert what_it_was_handed == [(AN_OPENED_PULL_REQUEST, A_REPOSITORY)]
    assert what_it_wrote == {"what_the_suite_said": the_suite}


def test_the_commit_the_suite_went_green_on_is_announced_with_the_checks_that_did(
    a_projects_root: Path,
) -> None:
    """A card saying "green" is not a record; a card naming the commit and the checks is.

    **Announced and not approved.** The run's own record is what the board streams, and the two
    facts a person needs afterwards are which commit was proved and by what — so both are in the
    line rather than a summary this system wrote on GitHub's behalf.
    """
    the_suite = WhatTheSuiteSaid(
        head_commit=THE_COMMIT_THE_SUITE_WENT_GREEN_ON,
        which_checks_went_green=["the_gate", "unit"],
    )
    the_suite_went_green_in_this_run(
        _a_state_that_delivered(a_projects_root), lambda the_pull_request, repository: the_suite
    )

    assert any(
        THE_COMMIT_THE_SUITE_WENT_GREEN_ON in what_was_said
        and "the_gate" in what_was_said
        and "unit" in what_was_said
        for what_was_said in _what_the_run_said(a_projects_root)
    ), (
        "the run's own record does not say which commit the suite went green on and which checks "
        "did it, so a person reading the card in a month has to guess which commit was proved"
    )


def test_the_suite_is_not_read_for_a_run_that_opened_no_pull_request(
    a_projects_root: Path,
) -> None:
    """There is no commit being merged without a pull request, and the run is told so."""
    state = _a_state_that_delivered(a_projects_root)
    state["opened_pull_request"] = None

    with pytest.raises(TheDeliveryHasNotBeenOpenedError):
        the_suite_went_green_in_this_run(
            state,
            lambda the_pull_request, repository: pytest.fail("the suite was read about nothing"),
        )


def test_the_merge_is_given_the_commit_the_suite_went_green_on(a_projects_root: Path) -> None:
    """The one guarantee: the merge lands the commit the checks were read about.

    **Asserted as what the collaborator was handed**, because a node that re-read the head sha here
    would look identical from the outside and would be merging a commit that moved under the
    checks. The commit comes out of the state the suite node wrote.
    """
    what_the_merge_was_given: list[tuple[object, object, object]] = []
    the_suite = WhatTheSuiteSaid(
        head_commit=THE_COMMIT_THE_SUITE_WENT_GREEN_ON, which_checks_went_green=["the_gate"]
    )
    state = {**_a_state_that_delivered(a_projects_root), "what_the_suite_said": the_suite}

    def merge(the_pull_request, repository, the_commit):
        what_the_merge_was_given.append((the_pull_request, repository, the_commit))
        return WhatTheMergeLanded(commit=the_commit, what_github_said="Pull Request merged")

    merge_the_delivery_in_this_run(state, merge)

    assert what_the_merge_was_given == [
        (AN_OPENED_PULL_REQUEST, A_REPOSITORY, THE_COMMIT_THE_SUITE_WENT_GREEN_ON)
    ], (
        "the merge was handed something other than the commit the suite went green on, so a head "
        "that moved between the two would be merged on a verdict about a commit nobody proved"
    )


def test_a_merge_is_refused_when_nothing_in_the_run_says_the_suite_was_read(
    a_projects_root: Path,
) -> None:
    """Merging a commit nothing was read about is the failure this channel exists to prevent.

    **Refused rather than reading the head again.** Asking GitHub what the pull request points at
    would answer, and the answer would be a commit the checks have not been read about — which is
    exactly the commit the merge tool's own argument is there to stop.
    """
    with pytest.raises(TheSuiteWasNotReadBeforeTheMergeError):
        merge_the_delivery_in_this_run(
            _a_state_that_delivered(a_projects_root),
            lambda the_pull_request, repository, the_commit: pytest.fail("it merged anyway"),
        )


def test_the_commit_that_landed_is_announced(a_projects_root: Path) -> None:
    """What a person looks for in the base branch's history is written down, with GitHub's sentence.

    **GitHub's own words and not a summary of them.** A run reporting a merge in its own language
    can be wrong about a merge having happened; the sentence GitHub answered with is the evidence,
    and the commit is the fact a reader will go and check.
    """
    the_suite = WhatTheSuiteSaid(
        head_commit=THE_COMMIT_THE_SUITE_WENT_GREEN_ON, which_checks_went_green=["the_gate"]
    )
    state = {**_a_state_that_delivered(a_projects_root), "what_the_suite_said": the_suite}

    merge_the_delivery_in_this_run(
        state,
        lambda the_pull_request, repository, the_commit: WhatTheMergeLanded(
            commit=the_commit, what_github_said="Pull Request successfully merged"
        ),
    )

    said = " ".join(_what_the_run_said(a_projects_root))
    assert THE_COMMIT_THE_SUITE_WENT_GREEN_ON in said
    assert "Pull Request successfully merged" in said, (
        "the run's own record says a merge happened without saying what GitHub answered, so a "
        "person reading it has to take this system's word for it"
    )


def test_neither_node_moves_the_work_item(a_projects_root: Path) -> None:
    """One writer of a work item, and these two are not it.

    **The channels are read and never written.** A stage that set a stage would be a second door
    into the table, and the table is checked once, in the transition node, for every move the
    graph ever makes.
    """
    the_suite = WhatTheSuiteSaid(
        head_commit=THE_COMMIT_THE_SUITE_WENT_GREEN_ON, which_checks_went_green=["the_gate"]
    )
    the_state = _a_state_that_delivered(a_projects_root)

    after_the_suite = the_suite_went_green_in_this_run(
        the_state, lambda the_pull_request, repository: the_suite
    )
    after_the_merge = merge_the_delivery_in_this_run(
        {**the_state, **after_the_suite},
        lambda the_pull_request, repository, the_commit: WhatTheMergeLanded(
            commit=the_commit, what_github_said="merged"
        ),
    )

    assert "work_item" not in after_the_suite, (
        "the node that read the suite moved the work item, and the move to DONE is asked for by "
        "mark_the_work_item_delivered and made by the one writer"
    )
    assert "work_item" not in (after_the_merge.update or {}), (
        "the node that merged moved the work item, which is a second door into the transition "
        "table. **It names its own destination now** — it hands a conflict to the node that "
        "settles it and sends everything else to the move that says the delivery is done — so "
        "what it hands back is a `Command` and the channels it wrote are in its `update`"
    )
