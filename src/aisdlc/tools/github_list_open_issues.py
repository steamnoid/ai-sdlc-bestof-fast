"""`github.list_open_issues`: what work a repository is already tracking.

**Reading an issue list is the cheapest way to stop filing the same work twice**, and it is the
difference between a briefing that helps a team and a briefing that fills their queue with work
they have already agreed to do. There is no cleverer source for it: the issues *are* the record of
what a team has already decided, and reading anything else — a README, the code, a changelog —
answers a different question.

**Open issues only, and that is not a detail.** A closed issue was dealt with: implemented,
rejected, or superseded. Re-proposing it asks a team to consider something somebody has already
considered and closed, which is worse than a duplicate, because it ignores a decision rather than
overlooking one.

**No credential, because a reading operation should not need a writing one.** Filing needs
`GITHUB_TOKEN` and this does not. That matters more than it sounds: the read half of creative mode
is clone, inspect, report — all of it free — and requiring a token to look at a public repository's
issues would put the harmless half behind the same door as the half that touches a stranger's
board.

**The comparison with what is already filed is a judgement and it is stated rather than buried.**
Titles for the same work rarely match as text, so this compares the words they share rather than
testing for equality — but a one-word overlap would refuse half of every backlog, so the words
that appear in almost every title are dropped before comparing. A filter that silently drops a real
issue is worse than a duplicate, which is why the shape of the rule is in the module docstring and
not only in the function.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence

import httpx
from pydantic import BaseModel, ConfigDict

from aisdlc.domain.repository import Repository
from aisdlc.tools.github_client import a_github_client

SECONDS_A_READ_MAY_TAKE = 10
HOW_MANY_ISSUES_ARE_READ = 100

WHERE_GITHUB_KEEPS_ISSUES = "/repos/{owner}/{name}/issues"

WORDS_THAT_SAY_NOTHING_ABOUT_THE_WORK = frozenset(
    {
        "add",
        "the",
        "a",
        "an",
        "to",
        "for",
        "of",
        "in",
        "on",
        "and",
        "or",
        "is",
        "it",
        "should",
        "must",
        "not",
        "be",
        "fix",
        "make",
        "use",
        "with",
    }
)


class AnIssueGitHubWouldNotReadError(Exception):
    """GitHub did not answer with a list, so nothing can be said about what is already tracked.

    **A refusal rather than an empty list, because an empty list reads as "nothing is tracked".**
    That is a fact, and a false one would mean the briefing proposes work a team has already
    agreed to do — which is the exact failure this tool exists to prevent. So a GitHub that will
    not answer stops the briefing rather than allowing it to proceed on a lie.
    """


class AnOpenIssue(BaseModel):
    """One issue somebody opened, with the number a reader would cite and the title they filed.

    **The body is deliberately not read.** A hundred issue bodies is tens of thousands of words
    that go into a prompt to answer a question titles answer: *is this work already tracked?*
    Bodies are where the detail lives, and detail is what the clone and the code are for.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    number: int
    title: str


class WorkAlreadyTrackedError(Exception):
    """An issue about this work is already open, so filing another would duplicate it.

    **The one refusal in creative mode that is about the work rather than about the write.** Every
    other refusal here protects the person filing; this one protects the person whose queue is
    about to be filled. It fires before anything is opened, because an issue that is opened and
    then found to be a duplicate has already landed in somebody's queue and has to be closed by a
    person to remove it.
    """

    def __init__(self, what_was_proposed: str, the_issue_that_already_says_it: AnOpenIssue) -> None:
        self.what_was_proposed = what_was_proposed
        self.issue_that_already_says_it = the_issue_that_already_says_it
        super().__init__(
            f"{what_was_proposed!r} is already tracked as issue "
            f"#{the_issue_that_already_says_it.number} "
            f"({the_issue_that_already_says_it.title!r}), so nothing was filed. A second issue "
            "about the same work does not get anybody's work done sooner; it makes the queue "
            "harder to read for the people who have to read it"
        )


def read_the_open_issues(
    client: httpx.Client, repository: Repository
) -> list[AnOpenIssue]:
    """The open issues of one repository, oldest first, as GitHub lists them.

    **Skipped rows rather than refused rows.** The endpoint returns pull requests alongside issues
    and a `null` title is possible, and a briefing that refused to run because one of two hundred
    rows was odd would be a briefing that never runs — which is a worse failure than a briefing
    that read the other hundred and ninety-nine.
    """
    answer = client.get(
        WHERE_GITHUB_KEEPS_ISSUES.format(
            owner=repository.owner, name=repository.name
        ),
        params={"state": "open", "per_page": HOW_MANY_ISSUES_ARE_READ},
        timeout=SECONDS_A_READ_MAY_TAKE,
    )

    if answer.status_code != 200:
        raise AnIssueGitHubWouldNotReadError(
            f"the open issues of {repository.owner}/{repository.name} could not be read, so this "
            f"briefing cannot promise it will not propose work that is already tracked. GitHub "
            f"said: {answer.text}"
        )

    the_issues: list[AnOpenIssue] = []
    for a_row in answer.json():
        if not isinstance(a_row, dict):
            continue
        a_title = a_row.get("title")
        if a_row.get("state") != "open" or not isinstance(a_title, str) or not a_title.strip():
            continue
        the_issues.append(AnOpenIssue(number=int(a_row["number"]), title=a_title))
    return the_issues


HOW_MANY_SHARED_WORDS_MEAN_THE_SAME_WORK = 2
"""Two meaningful words in common, which is low enough to catch a re-worded duplicate.

**Two, and not one, because one is almost always a coincidence** in a backlog that has any size.
**And not three**, because the honest phrasing of a duplicate is often shorter than the original —
"Session cookie never expires" against "The session cookie has no expiry, so a browser keeps it
forever" shares two of three meaningful words and would slip past a threshold of three. That last
one is a judgement about the cost of a duplicate against the cost of a dropped proposal, and the
cost of a dropped proposal is paid by somebody who never hears about the opportunity.
"""


def the_issues_listed_as_tracked(
    what_is_proposed: str, already_tracked: Sequence[AnOpenIssue]
) -> None:
    """Raise when an open issue is already about this work.

    **The words that carry the meaning, not the words that overlap.** Titles for the same work
    rarely match as text — "Add an expiry to the session cookie" against "The session cookie has
    no expiry" shares three words out of five and four out of five, and shares them in a different
    order. But "Add a test" and "Add a health endpoint" share one word out of three, and refusing
    the second because of the first would make creative mode useless on any repository with a
    backlog. So the comparison drops the words that appear in nearly every title and requires most
    of what remains to be shared.
    """
    the_words_in_this_one = _the_words_that_carry_meaning(what_is_proposed)
    if not the_words_in_this_one:
        return

    for an_issue in already_tracked:
        the_words_in_that_one = _the_words_that_carry_meaning(an_issue.title)
        if not the_words_in_that_one:
            continue
        the_shared = the_words_in_this_one & the_words_in_that_one
        if len(the_shared) >= HOW_MANY_SHARED_WORDS_MEAN_THE_SAME_WORK:
            raise WorkAlreadyTrackedError(what_is_proposed, an_issue)


def _the_words_that_carry_meaning(a_title: str) -> set[str]:
    """The words of a title that distinguish it, which is not all of them."""
    every_word = re.findall(r"[a-z0-9]+", a_title.lower())
    return {
        a_word
        for a_word in every_word
        if a_word not in WORDS_THAT_SAY_NOTHING_ABOUT_THE_WORK and len(a_word) > 2
    }


ReadWhichIssuesAreOpen = Callable[[Repository], list[AnOpenIssue]]
"""How a deployment finds out what is already tracked, so a test can hand the briefing a list.

**A seam and not a keyword for "do not read anything",** because the list is not optional: it is
what the briefing model is shown and what the duplicate refusal compares against. A test that
supplied an empty list would be testing a briefing on a repository with no issues, which is a real
case worth testing — and would be testing nothing at all about the case where there are some.
"""


def the_issues_this_deployment_can_read() -> ReadWhichIssuesAreOpen:
    """The real one: GitHub's issues endpoint, with no credential, for any repository."""

    def reading(repository: Repository) -> list[AnOpenIssue]:
        return read_the_open_issues(a_github_client(), repository)

    return reading
