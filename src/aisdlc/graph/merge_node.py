"""The two nodes between a delivery and a delivered run: the suite, and the merge.

**Both are consequences of the eighth gate and neither is a gate of its own.** A person approved
a delivery; what happens next to it on somebody else's repository is a fact about the commit
GitHub is holding, not another question. So there is no ninth gate, no ninth decision and no new
stage — `the_suite_went_green_in_this_run` and `merge_the_delivery_in_this_run` sit between the
delivery and the move to `DONE`, and the table of legal transitions does not change.

**The suite is read on the commit GitHub says the pull request points at, and the merge is given
that same commit.** Both facts travel together, in one state channel, because the alternative is
two reads of a head that can move between them — and a merge that lands whatever happens to be
there is a merge of a commit nothing was proved about. The suite's own answer is a refusal when it
is anything but green, so a run that reaches here on a red suite ends with GitHub's words for it.

**Neither node moves the work item.** `mark_the_work_item_delivered` asks for the move to `DONE`
and `transition_the_work_item` is the only writer, and that rule is the reason a stage cannot set a
stage. What these two nodes do is announce what happened, in the run's own record — the board's
timeline, which a person reads to see whether the work landed and what it landed as.

**A conflict is handed over and everything else ends the run, and GitHub's own words are in the
handing.** `ThePullRequestIsInConflictError` is the one refusal here that has an answer somebody
can act on: a pull request that conflicts can be replayed on the branch it joins, and
`settle_the_conflict_in_this_run` is the node that decides whether to do that. Every other refusal
— a base branch that is protected, a head that moved, a check that has not finished, a GitHub that
would not answer — ends the run where it is, because none of them is a stage that can be sent back
to a planner and a repair supervisor asked to repeat an agent over them would be repeating an agent
that did nothing wrong. The card carries the refusal and the run stops with the reason on it.

**The name of the node a conflict is handed to is declared here, and the node lives elsewhere.**
`settle_a_conflict_node` needs this module's `WHERE_THE_SUITE_WENT_GREEN` — the destination of a
repair — and a name declared in both directions is two modules importing each other. A destination
is named by the node that goes to it, and this is the node that goes to it, so it is here.
"""

from __future__ import annotations

from collections.abc import Callable

from langgraph.types import Command

from aisdlc.domain.repository import Repository
from aisdlc.graph.agent_state import WHAT_STOPPED_THIS_RUN, AgentState
from aisdlc.store.what_a_run_records import something_the_run_said
from aisdlc.tools.github_create_pull_request import AnOpenedPullRequest
from aisdlc.tools.merge_a_pull_request import (
    ThePullRequestIsInConflictError,
    WhatTheMergeLanded,
)
from aisdlc.tools.the_suite_went_green import WhatTheSuiteSaid

WHERE_THE_SUITE_WENT_GREEN = "the_suite_went_green_in_this_run"
WHERE_THE_DELIVERY_WAS_MERGED = "merge_the_delivery_in_this_run"
WHERE_A_CONFLICT_IS_SETTLED = "settle_the_conflict_in_this_run"

AskWhetherTheSuiteWentGreen = Callable[[AnOpenedPullRequest, Repository], WhatTheSuiteSaid]
MergeThePullRequest = Callable[[AnOpenedPullRequest, Repository, str], WhatTheMergeLanded]


class TheDeliveryHasNotBeenOpenedError(Exception):
    """This run was asked whether the suite is green and has opened no pull request to ask about.

    **The wiring's own fault, and named as such.** The check-runs endpoint is asked about a commit,
    and without a pull request there is no commit that is being merged — so a run reaching this
    node means the delivery did not run, and continuing would mean asking about whatever the
    branch happens to point at.
    """


class TheSuiteWasNotReadBeforeTheMergeError(Exception):
    """This run was asked to merge a commit and nothing in it says which commit was read about.

    **The whole reason the suite's answer travels in the state.** A merge with no green suite
    behind it is a merge of a commit nobody proved anything about, and reading the head sha again
    here would not help: the sha could have moved since the suite was read, which is the one thing
    the merge tool's commit argument exists to catch.
    """


def the_suite_went_green_in_this_run(
    state: AgentState, ask_whether_the_suite_went_green: AskWhetherTheSuiteWentGreen
) -> dict:
    """What GitHub says about the checks on the commit about to be merged, kept for the merge.

    **The answer is written down and not merely obtained**, because the node after this one has to
    merge that same commit and a head that has moved since the checks ran is a commit nothing was
    proved about. The suite's own refusals are not caught here: a red suite, a check still running
    and a GitHub that will not answer all end the run with GitHub's own words for it, because none
    of them is a stage that can be sent back to an agent that did nothing wrong.
    """
    the_pull_request = _the_pull_request_this_run_opened(state)

    what_the_suite_said = ask_whether_the_suite_went_green(
        the_pull_request, state["work_item"].repository
    )
    something_the_run_said(
        state["work_item"].work_item_id,
        f"the suite went green on {what_the_suite_said.head_commit}: "
        f"{', '.join(what_the_suite_said.which_checks_went_green)}",
    )
    return {"what_the_suite_said": what_the_suite_said}


def merge_the_delivery_in_this_run(
    state: AgentState, merge_the_pull_request: MergeThePullRequest
) -> Command:
    """Merge exactly the commit the suite was read on, and say what GitHub said it landed.

    **The commit comes out of the state and nowhere else.** Reading the head again here would be
    racing the thing this stage is for: the checks were read about one sha, and a head that moved
    between the two is the case the merge tool's own commit argument refuses. There is no `DONE`
    move here either — `mark_the_work_item_delivered` asks for that, and the transition node
    is the only writer of a work item.

    **The destination is named on both outcomes, so this node carries no edge.** A conflict goes
    to the node that can settle it and everything else goes to the move that says the delivery is
    done; an edge out of here would fire *alongside* whichever of the two the node chose, which is
    how every repair in this system died. `test_no_node_that_chooses_its_own_destination_still_
    carries_an_edge` is the guard, and it was widened to name this node when it arrived.
    """
    what_the_suite_said = state["what_the_suite_said"]
    if what_the_suite_said is None:
        raise TheSuiteWasNotReadBeforeTheMergeError(
            "a merge lands one commit, and the checks were read about a commit this run has not "
            "recorded. Asking GitHub which commit the pull request points at would answer, and the "
            "answer would be a commit nothing was proved about — which is the one thing the commit "
            "the merge is given exists to prevent"
        )

    try:
        what_the_merge_landed = merge_the_pull_request(
            _the_pull_request_this_run_opened(state),
            state["work_item"].repository,
            what_the_suite_said.head_commit,
        )
    except ThePullRequestIsInConflictError as conflict:
        return _the_conflict_is_handed_to_the_repair(state, conflict)

    something_the_run_said(
        state["work_item"].work_item_id,
        f"merged {what_the_merge_landed.commit}: {what_the_merge_landed.what_github_said}",
    )
    return Command(goto="mark_the_work_item_delivered")


def _the_conflict_is_handed_to_the_repair(
    state: AgentState, conflict: ThePullRequestIsInConflictError
) -> Command:
    """GitHub's own sentence, put where a node that can act on it will read it.

    **`what_stopped_this_run` rather than a new channel.** It is the channel a refusal travels in
    on its way to the repair supervisor, so a conflict reaches a node that can settle it by the
    same road as every other fact a refusal carries — and a state channel added for one node would
    have to be added to every hand-built starting state in the package.
    """
    return Command(
        goto=WHERE_A_CONFLICT_IS_SETTLED, update={WHAT_STOPPED_THIS_RUN: str(conflict)}
    )


def _the_pull_request_this_run_opened(state: AgentState) -> AnOpenedPullRequest:
    """The pull request this run opened, or a refusal naming what was asked without one.

    **Refused rather than defaulted.** The checks are read about a commit, and with no pull request
    there is no commit that is being merged — so a run reaching this node without one means the
    delivery did not run, and continuing would mean asking about whatever a branch points at.
    """
    the_pull_request = state["opened_pull_request"]
    if the_pull_request is not None:
        return the_pull_request
    raise TheDeliveryHasNotBeenOpenedError(
        "the suite is read about the commit a pull request points at, and this run has opened no "
        "pull request. The delivery node opens one and is wired before this one, so reaching here "
        "without one is the wiring being wrong rather than a run with nothing to merge"
    )
