"""The tag, proved against real GitHub — the only test here that files anything.

**Everything else about this rule is proved with a stand-in for GitHub.** The other test
for the tag asserts the payload carries the project's full name and that a label which
cannot be created does not stop the filing. That is the right shape for a unit
test and it is not evidence: a payload can be exactly right and GitHub can still
ignore it, and this repository has a standing complaint about mechanisms nobody has
watched.

**So this files one real issue, reads it back, and closes it.** Read-back rather than "the call
returned 201", because the claim is that the *label is on the issue*, and the only place that claim
can be wrong is GitHub's own record of the issue. A test that trusted the status code would be
testing the mock it already trusts.

**It only runs when a deployment names both a credential and a repository to file against**, and it
skips loudly otherwise. A green run that never called GitHub is a lie, and a test that files into
somebody's repository by default is worse than a lie. **It closes the issue it opened**, so running
it twice does not leave a queue behind — though the first version's own comment called that
"idempotent" before measuring it, which is a word for a property one has to earn.

**The repository is named by the deployment and never hard-coded**, which is this system's rule
about repositories: the same code must be able to file for an arbitrary one.
"""

from __future__ import annotations

import os

import pytest

from aisdlc.domain.repository import Repository
from aisdlc.tools.github_client import a_github_client, the_credential
from aisdlc.tools.github_open_an_issue import AnIssueToOpen, open_an_issue
from aisdlc.tools.the_tag_this_system_leaves_on_what_it_writes import (
    the_tag_this_system_leaves,
)

THE_SETTING_NAMING_WHERE_TO_FILE = "AISDLC_THE_REPOSITORY_TO_FILE_AGAINST"


def _the_repository_to_file_against() -> str:
    return os.environ.get(THE_SETTING_NAMING_WHERE_TO_FILE, "")


def _why_this_proves_nothing() -> str | None:
    if not the_credential().strip():
        return (
            "GITHUB_TOKEN is not set, so nothing was filed and the tag was not proven on GitHub"
        )
    if not _the_repository_to_file_against().strip():
        return (
            f"{THE_SETTING_NAMING_WHERE_TO_FILE} is not set, so there is no repository to file "
            "against. It is not defaulted: a test that files into a repository nobody named is a "
            "test that writes to a stranger's board"
        )
    return None


@pytest.mark.skipif(
    bool(_why_this_proves_nothing()),
    reason=(
        "filing for real needs GITHUB_TOKEN and "
        f"{THE_SETTING_NAMING_WHERE_TO_FILE}. Without them the tag is proven only against a "
        "stand-in for GitHub, which is a payload assertion and not evidence."
    ),
)
def test_an_issue_filed_for_real_carries_the_projects_full_name() -> None:
    """File one, read it back, assert the label, close it.

    **The assertion is on GitHub's record of the issue rather than on what we sent it.** Sending
    `labels: [...]` is a request; the label being *on the thing* is a fact. Everything else in this
    repository's suite is about the request.
    """
    the_repository = Repository(
        owner=_the_repository_to_file_against().split("/")[0],
        name=_the_repository_to_file_against().split("/")[1],
    )
    the_client = a_github_client()
    the_tag = the_tag_this_system_leaves(the_repository)

    opened = open_an_issue(
        AnIssueToOpen(
            repository=the_repository,
            title="Proving this repository's filing tag reaches GitHub",
            body=(
                "Filed by `tests/test_the_tag_reaching_real_github.py`, against real GitHub, to\n"
                "prove that an issue carries the project's full name as a label.\n\n"
                "This issue is closed by the same test that opened it. It exists because every\n"
                "other proof of this rule is a stand-in for GitHub's API, and a payload that is\n"
                "exactly right and a label that is not there look identical from the outside.\n\n"
                "If you are reading this on GitHub: the label bar on the left is the claim."
            ),
        ),
        the_client,
        the_credential(),
    )

    try:
        the_issue_as_github_has_it = the_client.get(
            f"/repos/{the_repository.owner}/{the_repository.name}/issues/{opened.number}"
        )
        assert the_issue_as_github_has_it.status_code == 200, (
            f"issue {opened.number} was filed and then could not be read back: "
            f"{the_issue_as_github_has_it.text}"
        )
        the_labels_on_it = [
            a_label["name"] for a_label in the_issue_as_github_has_it.json().get("labels", [])
        ]

        assert the_tag in the_labels_on_it, (
            f"issue {opened.number} exists on {the_repository.owner}/{the_repository.name} and "
            f"carries {the_labels_on_it}, not {the_tag!r}. The request asked for the label and "
            "GitHub did not put it there, so everything this repository asserts about the tag is "
            "asserted about a payload and not about an issue"
        )
        assert the_tag == f"{the_repository.owner}/{the_repository.name}", (
            f"the tag is {the_tag!r} and the repository's full name is "
            f"{the_repository.owner}/{the_repository.name!r}, so the tag is not the full name"
        )
    finally:
        the_client.patch(
            f"/repos/{the_repository.owner}/{the_repository.name}/issues/{opened.number}",
            json={"state": "closed"},
            headers={"Authorization": f"Bearer {the_credential()}"},
        )
