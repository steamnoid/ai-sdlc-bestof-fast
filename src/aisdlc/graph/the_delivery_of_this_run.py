"""Every collaborator that delivers, named by what it is asked for.

The mirror image of `TheAgentsThisRun`, and separate from it for one reason: **none of these
reasons.** §10 gives the PR agent four responsibilities — prepare the change summary, prepare
the title and body, verify that the required gates passed, create the pull request only after
explicit human approval — and not one of them is a model call. Putting them in the type that
exists to say what a run reasons *with* would put a lie in it, and `aisdlc-pr` is the agent
identifier this run's work item carries through its last three moves.

**No default, and that is the point.** A run built without a delivery is a run that verifies a
change, writes a branch name into a file, and stops — which is what this pipeline did, and
which reads from the outside exactly like success. So a caller has to say how the run delivers
or the graph cannot be assembled at all.

**Two of these are consequences of the delivery rather than parts of it.** `ask_whether_the_suite_
went_green` and `merge_the_pull_request` are what happen to a delivered pull request on somebody
else's repository, and they are here for the same reason as the other three: §10 gives the pull
request agent four responsibilities and none of them is a model call, and a run whose delivery
cannot read a suite or merge anything is a run that opened a pull request and stopped.

**`rebase_the_branch` is here for the same reason and for one more.** It is the repair a conflicting
delivery takes, so it happens after the delivery and not as part of it — but it happens *to* the
delivery: the branch this run pushed, on this run's copy. Keeping it here rather than beside the
node that decides to use it is what says the decision belongs to an agent and the acting to a
delivery, which is the same line `TheAgentsThisRun` draws on the other side of it.

`our_copy` is here rather than read from the environment inside the graph, because
`the_account_we_fork_into` is where the environment is read and the fork tool's own rule is
that every address-shaped decision lives in the tools. It also means the unit tier, which
reads no environment variable, can build a run.
"""

from __future__ import annotations

from pydantic import BaseModel

from aisdlc.domain.repository import Repository
from aisdlc.graph.deliver_node import OpenThePullRequest, PushTheBranch
from aisdlc.graph.merge_node import AskWhetherTheSuiteWentGreen, MergeThePullRequest
from aisdlc.graph.settle_a_conflict_node import RebaseTheBranch


class TheDeliveryOfThisRun(BaseModel):
    """Whose copy to deliver from, the two things that put the delivery on a remote, and the two
    things that happen to it there."""

    our_copy: Repository
    push_the_branch: PushTheBranch
    open_the_pull_request: OpenThePullRequest
    ask_whether_the_suite_went_green: AskWhetherTheSuiteWentGreen
    merge_the_pull_request: MergeThePullRequest
    rebase_the_branch: RebaseTheBranch
