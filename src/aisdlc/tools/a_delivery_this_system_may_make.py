"""A delivery built from the environment, which is the one the real run gets.

**The only place the environment is read for a delivery**, and it is here rather than in the
graph for the reason the fork tool reads its own: a node that read a setting would make the
unit tier — which reads none — unable to run at all, and would put an address-shaped decision
in a file whose job is routing.

**Both halves read the environment when they are *called*, not when this factory runs.** A
factory that read the settings at import would freeze one deployment's account into a process,
and a run resumed tomorrow would push to yesterday's fork. The clone collaborator already
works this way for the same reason and says so.

**The account is named once and used twice.** `our_copy` and the push both have to agree about
whose copy of the repository this is; reading it in two places would make a deployment with
two accounts a delivery that pushes to one and opens against the other, which fails at GitHub
with a 422 about a head that is not there.
"""

from __future__ import annotations

from aisdlc.domain.repository import Repository
from aisdlc.graph.deliver_node import OpenThePullRequest, PushTheBranch
from aisdlc.graph.merge_node import AskWhetherTheSuiteWentGreen, MergeThePullRequest
from aisdlc.graph.settle_a_conflict_node import RebaseTheBranch
from aisdlc.graph.the_delivery_of_this_run import TheDeliveryOfThisRun
from aisdlc.tools.github_client import a_github_client, the_credential
from aisdlc.tools.github_clone_repository import ClonedRepository
from aisdlc.tools.github_create_branch import (
    PushedBranch,
    a_branch_to_push,
    create_a_branch_on_a_remote,
)
from aisdlc.tools.github_create_pull_request import (
    AnOpenedPullRequest,
    PullRequestToOpen,
    open_a_pull_request,
)
from aisdlc.tools.github_fork_repository import the_account_we_fork_into
from aisdlc.tools.merge_a_pull_request import (
    WhatTheMergeLanded,
    a_pull_request_to_merge,
    merge_a_pull_request,
)
from aisdlc.tools.rebase_the_branch_a_run_pushed import rebase_the_branch_a_run_pushed
from aisdlc.tools.the_suite_went_green import WhatTheSuiteSaid, the_suite_went_green


def the_delivery_this_system_may_make(repository: Repository) -> TheDeliveryOfThisRun:
    """The delivery for a run working on `repository`, built from this deployment's settings.

    The repository is an argument and the account is read, because the account names *which*
    copy of *that* repository is ours — a run that forked `wellbeing-tracker-public` into one
    account and pushed to another would produce a pull request nobody can merge.
    """
    our_copy = Repository(owner=the_account_we_fork_into(), name=repository.name)

    return TheDeliveryOfThisRun(
        our_copy=our_copy,
        push_the_branch=_a_branch_pusher(our_copy),
        open_the_pull_request=_a_pull_request_opener(),
        ask_whether_the_suite_went_green=_a_reader_of_the_suite(),
        merge_the_pull_request=_a_merger_of_the_pull_request(),
        rebase_the_branch=_a_rebaser_of_the_branch(),
    )


def _a_branch_pusher(our_copy: Repository) -> PushTheBranch:
    """Push the branch to our copy of the repository, refusing rather than moving a branch.

    The refusal lives in `create_a_branch_on_a_remote`, which asks the remote before it pushes
    and will not move a branch it did not create. That check is the reason this is a thin
    wrapper and not the whole thing written again here.
    """

    def pushing(clone: ClonedRepository, branch_name: str) -> PushedBranch:
        return create_a_branch_on_a_remote(
            clone, a_branch_to_push(clone, branch_name), our_copy
        )

    return pushing


def _a_pull_request_opener() -> OpenThePullRequest:
    """Open it with this deployment's credential, read when the call is made.

    `open_a_pull_request` refuses an empty credential before it attempts anything, because a
    pull request cannot be opened anonymously — it is somebody's decision to review.
    """

    def opening(wanted: PullRequestToOpen) -> AnOpenedPullRequest:
        return open_a_pull_request(wanted, a_github_client(), the_credential())

    return opening


def _a_reader_of_the_suite() -> AskWhetherTheSuiteWentGreen:
    """Read GitHub's own record of the checks on the commit the pull request points at.

    **The repository is passed in and not taken from the closure**, because the checks are read on
    the repository the pull request is on — the upstream one, not this deployment's fork — and a
    closure that had captured the fork would read the fork's checks, which are none.
    """

    def reading(the_pull_request: AnOpenedPullRequest, repository: Repository) -> WhatTheSuiteSaid:
        return the_suite_went_green(a_github_client(), the_pull_request, repository)

    return reading


def _a_merger_of_the_pull_request() -> MergeThePullRequest:
    """Merge the one commit the checks were read about, as whoever this deployment is.

    **The commit is an argument rather than something this wrapper looks up**, and that is the
    whole guarantee: GitHub is asked to merge that sha or nothing, so a head that moved between
    the checks and the merge is refused by GitHub rather than merged on a verdict about a commit
    nobody proved.
    """

    def merging(
        the_pull_request: AnOpenedPullRequest, repository: Repository, the_commit: str
    ) -> WhatTheMergeLanded:
        return merge_a_pull_request(
            a_github_client(),
            a_pull_request_to_merge(repository, the_pull_request.number, the_commit),
            the_credential(),
        )

    return merging


def _a_rebaser_of_the_branch() -> RebaseTheBranch:
    """The real rebase, in the clone this run already made.

    **No wrapper beyond the function's own name, and that is deliberate.** Every other collaborator
    here needs a decision made by the deployment — whose copy, whose credential — and this one needs
    none: the branches are named by the approved delivery and the checkout is in the state. A thin
    wrapper that closed over nothing would be a place for a future deployment to put an answer, so
    the tool is handed straight to the node.
    """
    return rebase_the_branch_a_run_pushed
