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
"""The setting a deployment uses to name the project that files, when it is not this one."""

THE_PROJECT_THIS_SYSTEM_FILES_AS = "steamnoid/ai-sdlc-bestof-fast"
"""The full name of the project this system files as — itself, and never a repository it files into.

**Here rather than read from a repository, because that was the mistake.** The first version
derived the tag from the repository being filed into, so every issue this system filed on
`paligakrzychu/wellbeing-tracker-public` was labelled `paligakrzychu/wellbeing-tracker-public`:
the project it landed on, named as though it had asked for the work. A tag exists to answer *who
filed this*, and that answer is a fact about this codebase — the one thing that cannot be read off
a repository somebody else owns.

`AISDLC_PROJECT_NAME` overrides it, which is what a deployment that forks this and files as
something else states."""

WHERE_A_LABEL_IS_CREATED = "/repos/{owner}/{name}/labels"
"""Where GitHub creates a label on a repository, and where it refuses to create one twice."""

GITHUB_CREATED_IT = 201
GITHUB_SAYS_IT_ALREADY_EXISTS = 422

# **Grey, and not a colour anybody chose.** A label this system creates is a filing label — it says
# where the thing came from, not how urgent it is — and picking a colour would imply a priority
# this system has no standing to assign. GitHub's own default for an uncoloured label is this.
THE_COLOUR_A_FILING_LABEL_IS = "ededed"


def the_tag_this_system_leaves() -> str:
    """The label everything this system files carries: **this system's own project.**

    **Its own, and not the repository being filed into.** This took six attempts to get right and
    the wrong version was not a bug so much as a misreading. It returned
    `repository.address` — the repository a run was filing *into* — which meant a briefing on
    somebody else's project labelled every issue it filed with *their* name. That is worse than no
    label at all: a tag is how a reader answers **who produced this**, and the answer it gave was
    a fact about where the work landed rather than about who asked for it. Two automations filing
    into one repository would have been indistinguishable, and a person filtering a stranger's
    issue queue by project would have been reading a label that said nothing about the tool that
    wrote it.

    **So the function takes no repository at all.** Taking one is what invited the mistake: the
    argument was there, it was the only name in scope, and it was the wrong name. An argument
    nobody needs is an argument that will be used wrongly.

    **The full name of the project that files, and it is a constant rather than a lookup.** A
    deployment that forks this and files as something else states `AISDLC_PROJECT_NAME`; the
    default is the repository this code is released from, which is the honest answer for an
    installation that has said nothing.
    """
    what_the_deployment_stated = os.environ.get(THE_SETTING_NAMING_THE_PROJECT, "")
    if what_the_deployment_stated.strip():
        return what_the_deployment_stated.strip()
    return THE_PROJECT_THIS_SYSTEM_FILES_AS


def make_sure_the_tag_is_there(
    client: httpx.Client, credential: str, repository: Repository, tag: str
) -> bool:
    """Create the label if the repository has not got it, and say whether it can be used at all.

    **A 422 here is the success case and that is the first subtlety.** GitHub answers a request to
    create a label that already exists with 422 and a body saying so, which is the same status it
    uses for a genuinely invalid request. Treating it as failure would mean every filing after the
    first refused, and treating it as failure to create is how a deployment ends up filing without
    the tag it was configured with. So it is read as "it is already there", which is what it means
    here.

    **And a refusal is not an error, which is the second subtlety and the more important one.**
    Labels live on GitHub's *issues* API: opening a pull request needs `pull_requests: write` and
    creating a label needs `issues: write`, which are different permissions and a deployment
    provisioned for delivering has no reason to hold the second. **A tag this deployment cannot
    create is not used, and the issue or the pull request still goes out** — untagged rather than
    refused. The first version of this raised, and it refused every delivery on such a deployment
    with an error about a label, twenty minutes after a run had pushed a branch. The tag is how a
    person finds the work; the pull request is the work, and losing it to lose the tag is not a
    trade anybody would defend.

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

    return answer.status_code in {GITHUB_CREATED_IT, GITHUB_SAYS_IT_ALREADY_EXISTS}
