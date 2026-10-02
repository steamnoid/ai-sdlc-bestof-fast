"""A briefing can file its own opportunities, and the list of open issues is read again to do it.

**The half of the product that needs no person is the half nobody has ever switched on.** Filing
is the only irreversible thing in creative mode — an issue lands in somebody's queue and stays
there — and it is gated behind a browser and a person ticking boxes. This file makes the same
filing happen without the browser, against a double for GitHub, because **nobody may be shown
filing five issues on a real repository to find out whether it works.**

**The window between reading the list of open issues and writing is real, and it is documented in
two places today.** `filing_what_the_briefing_found` says so in its own docstring: the list is
read once, at briefing time, and an issue filed between the briefing and the pick is not in it.
A person choosing takes minutes, which is a wide window; a machine filing straight on takes
milliseconds. **The list is therefore read again at the moment of filing, and the second read is
what the duplicate refusal compares against** — so the window is one API call wide rather than as
wide as a human's afternoon, and an issue somebody else filed in between is caught rather than
duplicated.

**It cannot be closed, and this file says so rather than implying otherwise.** GitHub offers no way
to say "open this issue unless one matching it exists", so the check and the write are two
requests and a race is a race. What the re-read removes is the *long* window — the one a person
creates. What it cannot remove is the one between two adjacent requests. An automatic filing is
also **all or nothing from the first duplicate onwards**, because the existing refusal stops the
whole filing rather than skipping one opportunity: that is the price of automating a path whose
refusal was written for a person who could look again, and it is recorded here rather than changed
behind a test.

**Everything external is a double, and GitHub is a transport rather than a stub.** The clone is a
local bare repository, the model is a prepared briefing, the issue opener is a closure, and the
open issues are read through the production `read_the_open_issues` against an `httpx.MockTransport`
that answers twice with different content. **A green run here proves the wiring** and says nothing
about whether a model proposes good work, which is `evals/`'s question and this file's is not.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import httpx
import pytest

from aisdlc.agents.what_an_agent_judged import WhatAnAgentJudged
from aisdlc.creative.a_repository_briefing_itself import (
    filing_a_briefing_without_asking_anybody,
)
from aisdlc.creative.an_opportunity import AnOpportunity
from aisdlc.creative.filing_what_the_briefing_found import AnIssueThatWasOpened
from aisdlc.creative.the_opportunities_this_repository_offers import (
    TheOpportunitiesThisRepositoryOffers,
)
from aisdlc.domain.repository import Repository
from aisdlc.store.the_board_reads import AColumnOfTheBoard, the_board_this_register_holds
from aisdlc.store.where_the_register_lives import holding_the_register, the_register_lives_at
from aisdlc.tools.github_client import Addresses
from aisdlc.tools.github_clone_repository import a_repository_to_clone
from aisdlc.tools.github_list_open_issues import (
    AnOpenIssue,
    WorkAlreadyTrackedError,
    read_the_open_issues,
)

A_REPOSITORY = Repository(owner="steamnoid", name="wellbeing-tracker-public")

AN_ISSUE_SOMEONE_ELSE_FILED = {
    "number": 7,
    "title": "The authentication module keeps a fallback secret",
    "state": "open",
}


@pytest.fixture
def creative_mode_on(monkeypatch) -> None:
    """The deployment says a repository may brief itself, in the one word that means it."""
    monkeypatch.setenv("AISDLC_CREATIVE_MODE", "on")


@pytest.fixture
def an_open_register(tmp_path: Path, monkeypatch) -> None:
    """Where the work items a filing makes are recorded, on a real SQLite file."""
    monkeypatch.setenv("AISDLC_PROJECTS_DIR", str(tmp_path / "projects"))
    the_register_lives_at(tmp_path / "the-register.sqlite3")


def _git(where: Path, *what: str) -> str:
    what_happened = subprocess.run(
        ["git", *what], cwd=where, capture_output=True, text=True, check=False
    )
    if what_happened.returncode != 0:
        pytest.fail(f"git {' '.join(what)} in {where} failed: {what_happened.stderr}")
    return what_happened.stdout


def _a_repository_to_brief(tmp_path: Path) -> Path:
    """A bare repository with one file in it, made locally, so a briefing can really clone it."""
    the_bare = tmp_path / "the-origin.git"
    the_bare.mkdir()
    _git(the_bare, "init", "--bare", "--initial-branch=main")

    a_working_copy = tmp_path / "a-working-copy"
    a_working_copy.mkdir()
    _git(a_working_copy, "init", "--initial-branch=main")
    _git(a_working_copy, "config", "user.email", "a-briefing@example.com")
    _git(a_working_copy, "config", "user.name", "a briefing")
    (a_working_copy / "README.md").write_text("# a project\n", encoding="utf-8")
    _git(a_working_copy, "add", ".")
    _git(a_working_copy, "commit", "-m", "the first commit")
    _git(a_working_copy, "remote", "add", "origin", str(the_bare))
    _git(a_working_copy, "push", "origin", "main")
    return the_bare


def _an_opportunity(what: str, how_it_would_be_known: str) -> AnOpportunity:
    return AnOpportunity(
        what_could_be_done=what,
        why_it_is_worth_doing="A reader of this repository would otherwise work it out themselves",
        how_it_would_be_known_to_have_worked=how_it_would_be_known,
        the_files_that_show_this=["README.md"],
        the_discipline_that_owns_it="SEC",
        the_risk_of_it="none",
    )


def _a_briefing_finding(*opportunities: AnOpportunity):
    """A model that has already been asked and has already answered, as the real node would."""

    def briefing(the_clone, repository, what_the_environment_allows, what_was_already_tracked):
        del the_clone, what_the_environment_allows, what_was_already_tracked
        return TheOpportunitiesThisRepositoryOffers(
            about=repository,
            what_this_repository_is="a small project with one file in it",
            opportunities=list(opportunities),
            what_the_briefing_could_not_settle=[],
            agent_judgement=WhatAnAgentJudged(
                what_it_found="one thing",
                what_it_could_not_settle="one other thing",
                what_it_expects_next="every opportunity becomes a filing",
            ),
        )

    return briefing


def _a_reader_returning(what_is_open_at_each_read: list[list[dict[str, object]]]):
    """A stand-in for GitHub's open issues, answering differently on each read.

    **A different answer on the second read is the whole point.** A double that returned the same
    list both times would pass a filing that never re-read anything — which is the defect this
    file exists to make impossible to have.
    """
    how_many_reads_so_far = 0

    def reading(repository: Repository) -> list[AnOpenIssue]:
        nonlocal how_many_reads_so_far
        which_read = min(how_many_reads_so_far, len(what_is_open_at_each_read) - 1)
        how_many_reads_so_far += 1
        del repository
        return read_the_open_issues_from(what_is_open_at_each_read[which_read])

    return reading


def read_the_open_issues_from(what_github_holds: list[dict[str, object]]) -> list[AnOpenIssue]:
    """The production reader, against a transport that answers with this one list."""
    return read_the_open_issues(_a_github_answering(what_github_holds), A_REPOSITORY)


def _a_github_answering(
    what_github_holds: list[dict[str, object]], what_it_was_asked: list[str] | None = None
) -> httpx.Client:
    """A GitHub that answers its issues endpoint and records being asked."""
    the_asks = what_it_was_asked if what_it_was_asked is not None else []

    def answering(request: httpx.Request) -> httpx.Response:
        the_asks.append(str(request.url))
        return httpx.Response(200, json=what_github_holds)

    return httpx.Client(
        base_url="https://api.github.com", transport=httpx.MockTransport(answering)
    )


def _an_issue_opener() -> tuple[list[str], object]:
    """An opener that records the titles it was handed and answers with a number, in that order."""
    the_titles: list[str] = []

    def opening(an_opportunity: AnOpportunity, repository: Repository) -> AnIssueThatWasOpened:
        the_titles.append(an_opportunity.what_could_be_done)
        the_number = 100 + len(the_titles)
        return AnIssueThatWasOpened(
            number=the_number,
            address=f"https://github.com/{repository.address}/issues/{the_number}",
        )

    return the_titles, opening


def _cloning_from(the_bare: Path, into: Path):
    def planning(repository: Repository, where: Path):
        del where
        return a_repository_to_clone(
            repository,
            Addresses(fetch_from=str(the_bare), origin_of_the_code=str(the_bare)),
            into,
        )

    return planning


def test_every_opportunity_a_briefing_found_becomes_an_issue_and_a_card(
    creative_mode_on: None, an_open_register: None, tmp_path: Path
) -> None:
    """The whole point: two opportunities, two issues, two cards, and nobody chose between them.

    **Every one rather than the best one, because there is nobody to choose.** A person at the
    board picks which of five opportunities their project should be given; a machine that filed
    only one would be making that judgement itself without saying so, and a machine that filed two
    of three would be filing a partial backlog nobody asked for. All of them, or nothing.

    **The cards are read off the board rather than off the return value**, because a filing whose
    work items nothing on the board can show is a filing that produced no work anybody can rule on.
    """
    the_bare = _a_repository_to_brief(tmp_path)
    the_titles, opening = _an_issue_opener()
    opportunities = (
        _an_opportunity(
            "The authentication module keeps a fallback secret",
            "a test refuses to start without the setting",
        ),
        _an_opportunity(
            "The public search endpoint is not rate limited",
            "a test calls it twice and is refused the second time",
        ),
    )

    the_filing = filing_a_briefing_without_asking_anybody(
        A_REPOSITORY,
        a_briefing=_a_briefing_finding(*opportunities),
        plan_the_clone=_cloning_from(the_bare, tmp_path / "a-clone"),
        read_which_issues_are_open=_a_reader_returning([[], []]),
        open_the_issue=opening,
    )

    assert the_titles == [
        an_opportunity.what_could_be_done for an_opportunity in opportunities
    ], "a briefing that filed its own opportunities filed a different set than it proposed"
    assert the_filing.how_many_became_filings == 2
    with holding_the_register() as a_register:
        the_cards = the_board_this_register_holds(a_register)
    assert [a_card.column for a_card in the_cards] == [AColumnOfTheBoard.TO_DISCUSS] * 2, (
        "a filing made issues but no work items on the board, and an issue with no card is a "
        "ticket nobody rules on"
    )


def test_the_open_issues_are_read_again_at_the_moment_of_filing(
    creative_mode_on: None, an_open_register: None, tmp_path: Path
) -> None:
    """The window, and the only honest way to narrow it: read the list again, at the write.

    **The count is the assertion, because a filing that read once passes every other test here.**
    Twice: once for the prompt the briefing model was shown, and once for the comparison the
    refusal makes — and it is the second that closes the window a person would have opened.
    """
    the_bare = _a_repository_to_brief(tmp_path)
    _the_titles, opening = _an_issue_opener()
    how_many_times_the_issues_were_read: list[int] = []

    def reading_which_issues_are_open(repository: Repository) -> list[AnOpenIssue]:
        how_many_times_the_issues_were_read.append(1)
        return read_the_open_issues_from([])

    filing_a_briefing_without_asking_anybody(
        A_REPOSITORY,
        a_briefing=_a_briefing_finding(
            _an_opportunity("Rate limit the public search", "a test is refused the second call")
        ),
        plan_the_clone=_cloning_from(the_bare, tmp_path / "a-clone"),
        read_which_issues_are_open=reading_which_issues_are_open,
        open_the_issue=opening,
    )

    assert len(how_many_times_the_issues_were_read) == 2, (
        "the open issues were read "
        f"{len(how_many_times_the_issues_were_read)} time(s): one for the briefing and one for "
        "the filing is what narrows the window between reading the list and writing to one call"
    )


def test_an_issue_filed_while_the_briefing_was_running_is_refused_and_nothing_is_opened(
    creative_mode_on: None, an_open_register: None, tmp_path: Path
) -> None:
    """The second read earns its keep: the duplicate the first read could not have seen.

    **Nothing is opened, which is the half that matters.** An issue that is opened and then found
    to be a duplicate has landed in somebody's queue and can only be removed by a person closing
    it — so the refusal happens before the opener is reached, and the test is that it never is.
    """
    the_bare = _a_repository_to_brief(tmp_path)
    the_titles, opening = _an_issue_opener()

    with pytest.raises(WorkAlreadyTrackedError):
        filing_a_briefing_without_asking_anybody(
            A_REPOSITORY,
            a_briefing=_a_briefing_finding(
                _an_opportunity(
                    "The authentication module keeps a fallback secret",
                    "a test refuses to start without the setting",
                )
            ),
            plan_the_clone=_cloning_from(the_bare, tmp_path / "a-clone"),
            read_which_issues_are_open=_a_reader_returning(
                [[], [AN_ISSUE_SOMEONE_ELSE_FILED]]
            ),
            open_the_issue=opening,
        )

    assert the_titles == [], (
        "an issue was opened for work somebody had already filed while the briefing was running, "
        "and it can only be removed by a person closing it on a board that is not ours"
    )
    with holding_the_register() as a_register:
        assert the_board_this_register_holds(a_register) == [], (
            "a work item was made for a filing that never happened, and a card on the board for "
            "work nobody is doing is a card somebody will rule on"
        )
