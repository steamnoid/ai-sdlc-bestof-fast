"""Reading a request from the place a person filed it, rather than from what somebody retyped.

**The side of the chain that did not exist.** Every delivery this repository has made took its
request as a sentence somebody typed, so what has been proven is *text → pull request*. The claim
`gh issues -> pr` needs the input read from an issue, and nothing read one.

**The address is read, not composed, and that is the whole correction.** The type this replaces
carried `…/issues/N` assembled from `owner/name` and a number, and on the one repository this
system had been pointed at that link resolved to nothing — a false reference in the one thing a
traceability chain exists to be. A `html_url` GitHub itself returned is a fact, and whether an
issue exists is something only GitHub knows. So the number is ours, the address is theirs, and
where the two disagree the address is what settles it.

**A pull request is not an issue.** The GitHub API returns both from one path, and the 9 items in
the repository this system has been pointed at are all of the first kind -- which is why "that
repository has no issues" was true of a repository whose issues endpoint answers with nine entries.
A pull request carries a head branch and a merged flag, a filed request does not, and the
`pull_request` key in the answer is how the two are told apart.
"""

from __future__ import annotations

import httpx
from pydantic import BaseModel, ConfigDict, Field

from aisdlc.domain.commissioned_request import CommissionedRequest
from aisdlc.domain.repository import Repository
from aisdlc.domain.role import Role
from aisdlc.domain.the_issue_this_answers import TheIssueThisAnswers
from aisdlc.domain.work_item import WorkItem, a_work_item_commissioned_for_an_agent

WHERE_GITHUB_KEEPS_AN_ISSUE = "/repos/{owner}/{name}/issues/{number}"

SECONDS_A_READ_MAY_TAKE = 30
GITHUB_SAYS_IT_IS_NOT_THERE = 404


class NoSuchIssueError(Exception):
    """The rule is in this module, and this is the only thing that may say it broke.

    **Two facts arrive as one answer and neither is guessed.** An issue that does not exist and a
    repository this deployment cannot see are the same HTTP status, and a run that invented a
    request would go on to write eight artifacts and a summary about work nobody commissioned
    — every one of them shaped like a record. So the refusal names both possibilities rather
    than picking one.
    """


class AnIssueToRead(BaseModel):
    """Which issue, of which repository. A number, because that is what a person types."""

    model_config = ConfigDict(frozen=True)

    repository: Repository
    number: int = Field(ge=1)


class AnIssueRead(BaseModel):
    """A filed request as its author wrote it, and where it actually lives.

    **`address` is the one GitHub returned**, not one derived from `repository` and `number`.
    An issue that was transferred answers at an address that does not carry the number asked
    for, and a composed address cannot express that — it can only be right or wrong, and it
    was silently wrong on the only repository this system had been pointed at.

    **`state` is carried because a closed request is a fact a person reads before ruling.** A
    stage deciding whether to work on something that was closed should see that without asking
    GitHub a second time.

    **`body` may be empty and that is a real request.** Somebody filed it with a title and nothing
    else, and refusing that would refuse the issue a person wrote in the fewest seconds.
    """

    model_config = ConfigDict(frozen=True)

    repository: Repository
    number: int
    title: str
    body: str
    address: str
    state: str


def an_issue_to_read(repository: Repository, number: int) -> AnIssueToRead:
    """The issue to read, refused if the number could not be one.

    **Refused here rather than sent, because a mistyped number and a missing issue answer
    identically** and a run that could not tell them apart would report "no such issue" for somebody
    who simply typed `7 `.
    """
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise ValueError(
            f"{number!r} is not an issue number. GitHub numbers issues from one, so a number "
            "that is not one has no address, and asking anyway turns a typo into a refusal that "
            "reads as a missing request."
        )
    return AnIssueToRead(repository=repository, number=number)


def read_issue(request: AnIssueToRead, client: httpx.Client) -> AnIssueRead:
    """The filed request, or the reason there is not one to read.

    **A pull request at this address is refused rather than read as a request.** GitHub answers
    both from one path, so a number handed for an issue may name a pull request — and that
    body's description of a change, not a request for one. Every item in the repository this
    system has been pointed at is a pull request, so this is the likely reading, not a corner.
    """
    where = WHERE_GITHUB_KEEPS_AN_ISSUE.format(
        owner=request.repository.owner,
        name=request.repository.name,
        number=request.number,
    )

    response = client.get(where, timeout=SECONDS_A_READ_MAY_TAKE)

    if response.status_code == GITHUB_SAYS_IT_IS_NOT_THERE:
        raise NoSuchIssueError(
            f"Issue {request.number} was not read from {request.repository.owner}/"
            f"{request.repository.name}. Either no issue carries that number, or this "
            "deployment cannot see that repository. Nothing was read, and no conclusion may be "
            "drawn about what was asked for — a run that invented a request here would go on to "
            "write eight artifacts about work nobody commissioned."
        )

    answered = response.json()

    if answered.get("pull_request") is not None:
        raise NoSuchIssueError(
            f"{request.number} in {request.repository.owner}/{request.repository.name} is a "
            f"pull request, not a filed request: {answered.get('html_url')!r}. GitHub answers "
            "both from one path, and a pull request's body describes a change rather than "
            "asking for one, so reading it as a request would hand the pipeline a description "
            "to work from."
        )

    return AnIssueRead(
        repository=request.repository,
        number=answered["number"],
        title=answered["title"],
        body=answered.get("body") or "",
        address=answered["html_url"],
        state=answered["state"],
    )


def a_work_item_commissioned_from_a_filed_request(
    work_item_id: str,
    accountable_role: Role,
    commissioned_by: str,
    the_issue: AnIssueRead,
) -> WorkItem:
    """A work item whose request was filed, and the address a reader follows to the rest of it.

    **The one read, and the reason this function exists rather than two arguments.** A caller able
    to hand over a title and a number separately can hand over one issue's title with another's
    number, and every record downstream would read as complete while answering a question nobody
    asked. Here the words and the reference are the same `AnIssueRead`, so they cannot come apart —
    and a test mutates the read and watches both halves of the work item move with it.

    **It lives in `tools/` and not in `domain/`, because the domain must not know what GitHub is.**
    I put it there first and the guard `test_the_domain_layer_never_imports_a_model` refused the
    import, which is the guard being right: a work item is a domain fact and an `AnIssueRead` is a
    fact about an API. So the composition lives where the read is, and the domain keeps the two
    values apart — one carrying the words, one carrying where they were written.

    **The repository is the issue's own, and not an argument.** A work item worked on a repository
    and filed against another is a record with two repositories in it, and nothing downstream could
    say which one the pipeline read.
    """
    return a_work_item_commissioned_for_an_agent(
        work_item_id=work_item_id,
        repository=the_issue.repository,
        accountable_role=accountable_role,
        commissioned_by=commissioned_by,
        requested=CommissionedRequest(
            title=the_issue.title,
            body=the_issue.body,
            filed_as=TheIssueThisAnswers(
                number=the_issue.number, address=the_issue.address
            ),
        ),
    )
