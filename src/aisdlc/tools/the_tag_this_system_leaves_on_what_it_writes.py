"""The name every issue and pull request this system opens carries, and making sure it exists.

**One rule, one place, because there are exactly two things that write to a repository somebody
else owns.** `github.open_an_issue` and `github.create_pull_request` are the pair, and a rule
written into both of them is two rules that will drift: somebody tags issues for one project,
forgets pull requests, and every filing after that is half-tagged. Neither tool is wrong on its
own, which is exactly why nothing would catch it.

**The tag is the project's full name — `owner/name` — and the repository's own by default.** A
deployment that has thought about this at all should get a tag without configuring anything, and
`Repository.address` is the one fact already present on both writes and the one place that joins
the two halves. **Full, rather than the name on its own, because a repository name is only unique
within an owner**: two forks of one project share a name, and a bare name filed by both would put
their work under one label and make the filter lie. A setting overrides it for the cases where a
project and a repository are not the same thing — several repositories under one project, or a
monorepo whose repository name is the container rather than the thing being worked on.

**And the label has to exist before anything carries it.** GitHub refuses an issue or a pull
request naming a label it has never heard of, with a 422 that reads like a delivery failure. So the
label is created first, and a 422 to *that* is success, because a label that already exists is
exactly what GitHub says when it refuses to create one. Filing is not a one-off — a briefing
proposes several opportunities and a deployment may run against the same repository every week — so
this has to be idempotent, and treating 422 as success is what makes it so.
"""

from __future__ import annotations

import os

import httpx

from aisdlc.domain.repository import Repository

THE_SETTING_NAMING_THE_PROJECT = "AISDLC_PROJECT_NAME"
"""The setting a deployment uses to name the project, when the repository name is not it."""

WHERE_A_LABEL_IS_CREATED = "/repos/{owner}/{name}/labels"
"""Where GitHub creates a label on a repository, and where it refuses to create one twice."""

GITHUB_CREATED_IT = 201
GITHUB_SAYS_IT_ALREADY_EXISTS = 422

# **Grey, and not a colour anybody chose.** A label this system creates is a filing label — it says
# where the thing came from, not how urgent it is — and picking a colour would imply a priority
# this system has no standing to assign. GitHub's own default for an uncoloured label is this.
THE_COLOUR_A_FILING_LABEL_IS = "ededed"


def the_tag_this_system_leaves(repository: Repository) -> str:
    """The label an issue or a pull request about this repository is filed under.

    **The full name — owner and name together — and not the name on its own.** A repository name
    is only unique within an owner, and a tag that cannot tell two repositories apart cannot answer
    the one question it is filed under: *which project asked for this?* Two forks of the same
    project share a name, `wellbeing-tracker-public` is a plausible thing for more than one person
    to own, and a bare name filed by both would put their work under one label and make the filter
    lie. `owner/name` is also what GitHub itself calls a repository's full name, so the tag and
    the thing it names are the same string as the one a reader would type.

    **Blank falls back rather than raising**, because a deployment that empties a setting to turn a
    name off should get the repository's full name instead of an exception from inside an HTTP
    call — and `GITHUB_TOKEN=` present-but-empty is already handled that way in this repository,
    so a deployment that learned that lesson here learns it twice.
    """
    what_the_deployment_stated = os.environ.get(THE_SETTING_NAMING_THE_PROJECT, "")
    if what_the_deployment_stated.strip():
        return what_the_deployment_stated.strip()
    return repository.address


def make_sure_the_tag_is_there(
    client: httpx.Client, credential: str, repository: Repository, tag: str
) -> None:
    """Create the label if the repository has not got it, and do nothing if it has.

    **A 422 here is the success case and that is the whole subtlety.** GitHub answers a request to
    create a label that already exists with 422 and a body saying so, which is the same status it
    uses for a genuinely invalid request. Treating it as failure would mean every filing after the
    first refused, and treating it as failure to create is how a deployment ends up filing issues
    without the tag it was configured with. So it is read as "it is already there", which is what it
    means here, and every other answer is a refusal quoting GitHub's own words.

    **Before anything is opened, and not after.** An issue filed without its label is an issue
    somebody has to go and label by hand, and a pull request already open cannot be un-opened.
    """
    headers = {
        "Authorization": f"Bearer {credential}",
        "Accept": "application/vnd.github+json",
    }
    answer = client.post(
        WHERE_A_LABEL_IS_CREATED.format(
            owner=repository.owner, name=repository.name
        ),
        json={"name": tag, "color": THE_COLOUR_A_FILING_LABEL_IS},
        headers=headers,
    )

    if answer.status_code in {GITHUB_CREATED_IT, GITHUB_SAYS_IT_ALREADY_EXISTS}:
        return

    raise ALabelThisRunNeedsIsNotOnTheRepositoryError(
        f"{tag!r} is not on {repository.owner}/{repository.name} and could not be put "
        f"there, so nothing this run files will carry it. GitHub said: {answer.text}"
    )


class ALabelThisRunNeedsIsNotOnTheRepositoryError(Exception):
    """The label the run writes with does not exist and cannot be made, so nothing is filed."""
