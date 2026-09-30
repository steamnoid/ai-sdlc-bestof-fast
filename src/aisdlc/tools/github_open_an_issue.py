"""`github.open_an_issue`: filing a piece of work somebody could be given.

**This is a write to the outside world, and it is the only place a briefing touches anything it
does not own.** Everything else a briefing does is in this process — read a clone, propose work,
put a card on a board — and an issue is a thing that lands in somebody else's inbox and stays
there. That is why it is a tool with a credential and a refusal rather than a line in a node.

**The address is GitHub's own answer and never a composition.** `…/issues/N` is a shape, and a
shape is not a fact: a repository that has been transferred keeps its issues where they were, so
the composed string is a link to a page nobody has confirmed exists. Every later thing this
system does with a filing — the work item's request, the branch a delivery pushes, the body of
the pull request — reads the address from here, so getting it wrong once puts the same wrong
link in three places.

**No credential is refused rather than attempted.** An issue cannot be opened anonymously, and
GitHub's answer to a request with no credential is a 401 that says nothing about which of a
dozen settings is wrong. The refusal names the setting, because the person who has to fix it is
reading this message and not GitHub.

**Nothing about which issue this is is decided here.** The title, the body and the repository
all arrive built, because a tool that composed a body would be a second rendering of the
opportunity — and two renderings are two things that can disagree, with the one a person read on
the board not being the one the run worked on.
"""

from __future__ import annotations

import httpx
from pydantic import BaseModel, ConfigDict

from aisdlc.creative.an_opportunity import AnOpportunity
from aisdlc.creative.filing_what_the_briefing_found import AnIssueThatWasOpened
from aisdlc.domain.repository import Repository
from aisdlc.tools.github_client import THE_SETTING_NAMING_THE_CREDENTIAL
from aisdlc.tools.github_create_pull_request import what_github_said

GITHUB_CREATED_IT = 201

WHERE_AN_ISSUE_IS_OPENED = "https://api.github.com/repos/{owner}/{name}/issues"


class NoCredentialError(Exception):
    """Filing is an external write and there is nobody to make it as."""


class AnIssueWasNotOpenedError(Exception):
    """GitHub did not open the issue, so nothing was filed and the work item was not made."""


class AnIssueToOpen(BaseModel):
    """The issue somebody wants filed: a repository, a title, and a body already written."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: Repository
    title: str
    body: str


def an_issue_for(an_opportunity: AnOpportunity, repository: Repository) -> AnIssueToOpen:
    """The issue this opportunity becomes, with its body already written.

    **The body is rendered by the opportunity and not here.** `AnOpportunity.in_words` is the one
    rendering of it, and a second rendering in this tool is a second thing that can disagree with
    the first — with the one a person read on the board being the one that was not filed.
    """
    return AnIssueToOpen(
        repository=repository,
        title=an_opportunity.what_could_be_done,
        body=an_opportunity.in_words(),
    )


def open_an_issue(
    wanted: AnIssueToOpen, client: httpx.Client, credential: str
) -> AnIssueThatWasOpened:
    """Open it, and hand back the number and the address GitHub answered with.

    **A refusal quotes GitHub and says what it cost.** An issue that was not opened is a piece of
    work nobody can see and no work item standing behind it, and a caller carrying on past this
    would put a card on a board for a filing that does not exist. So the message is GitHub's own
    words plus the fact that nothing was filed.
    """
    if not credential.strip():
        raise NoCredentialError(
            f"{THE_SETTING_NAMING_THE_CREDENTIAL} is not set, so there is no account to file an "
            "issue as. An issue is a thing a person has to be able to see and answer, and nobody "
            "cannot see anything."
        )

    answer = client.post(
        WHERE_AN_ISSUE_IS_OPENED.format(
            owner=wanted.repository.owner, name=wanted.repository.name
        ),
        json={"title": wanted.title, "body": wanted.body},
        headers={
            "Authorization": f"Bearer {credential}",
            "Accept": "application/vnd.github+json",
        },
    )

    if answer.status_code != GITHUB_CREATED_IT:
        raise AnIssueWasNotOpenedError(
            f"{wanted.title!r} was not filed against "
            f"{wanted.repository.owner}/{wanted.repository.name}, so no work item was made for "
            f"it. GitHub said: {what_github_said(answer)}"
        )

    opened = answer.json()

    return AnIssueThatWasOpened(
        number=int(opened["number"]),
        address=str(opened["html_url"]),
    )
