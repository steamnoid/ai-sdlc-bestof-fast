"""The node a conflicting delivery is handed to, and the two things it may do about it.

**This is the caller `WhatToDoAroundAConflict` was written for and did not have.** The module
below asked a model which of two named repairs to make about a pull request that will not merge,
and validated the answer; nothing asked it. The reason was never that the contract was wrong — it
was that one of the two repairs needed a rebase, and this repository could not perform one, so
offering a model a choice between an action that could be taken and one that could not was offering
it a coin. `rebase_the_branch_a_run_pushed` is the operation that was missing, and this is the node
that asks and acts.

**A conflict does not end the run here; it is handed over, in GitHub's own words.** The merge node
catches `ThePullRequestIsInConflictError` and puts its sentence in `what_stopped_this_run`, which
is the channel the repair supervisor already uses for a refusal travelling to the node that can
act on it. **A decision made on a summary of a conflict is a decision about the summary**, and this
repository has already had one of those read like a fact about somebody's code — so the facts go
in their own words and nothing here paraphrases them.

**Rebasing sends the run back to the suite, and that is not a detail of the destination.** The
merge is handed the commit the checks were read about, and a rebase produces a *different* commit —
so a repair that went straight back to the merge would be asking GitHub to land a sha no check ever
ran on, and GitHub's own 409 would be the only thing standing between the run and an unproved merge.
The suite node reads the checks **on the commit the pull request now points at**, which is the only
commit a merge can be justified by.

**What ends the run is bounded, and the bound belongs to the tool.** A merge refused as a conflict
sends the run here; a rebase that would change nothing leaves the pull request in front of the same
`mergeable: false`, and a run with no bound would ask a model the same question about the same
facts until the runtime's recursion limit stopped it. `rebase_the_branch_a_run_pushed` refuses that
rebase by name, so the second visit stops. **A decision taken once about a fact that has not changed
is not a decision**, and it is said where the fact lives rather than left for a node to notice.

**Leaving the pull request open is not `DONE`, and nothing here marks the work item.** `DONE` in
this repository means merged; a run whose delivery is left open ends at `write_how_this_run_ended`
with its work item still standing at the gate it was refused after, which is the truth. The single
writer of a work item is `transition_the_work_item` and this node is not it — a node that settled a
conflict by changing a stage would be a second door into the table.
"""

from __future__ import annotations

from collections.abc import Callable

from langgraph.types import Command

from aisdlc.agents.what_to_do_around_a_conflict import (
    WhatKindOfConflict,
    WhatToDoAroundAConflict,
    WhatToDoWhenThePullRequestCannotBeMerged,
)
from aisdlc.graph.agent_state import WHAT_STOPPED_THIS_RUN, AgentState
from aisdlc.graph.merge_node import WHERE_THE_SUITE_WENT_GREEN
from aisdlc.graph.router import THE_RUN_IS_OVER
from aisdlc.store.what_a_run_records import something_the_run_said
from aisdlc.tools.rebase_the_branch_a_run_pushed import (
    ARebaseOfTheBranchARunPushed,
    WhatTheRebaseLeft,
    a_rebase_of_the_branch_a_run_pushed,
)

SettleTheConflict = Callable[[WhatKindOfConflict, str], WhatToDoAroundAConflict]
RebaseTheBranch = Callable[[ARebaseOfTheBranchARunPushed], WhatTheRebaseLeft]


class TheRunHasNoConflictToSettleError(Exception):
    """This run was asked to settle a conflict and holds no conflict, so there is nothing to ask.

    **Refused rather than asked anyway.** Reaching this node without a conflict means the wiring
    sent it here, and a model asked what to do about a conflict this run does not have answers
    about a situation nobody described — and the sentence it produced would go on the card beside a
    delivery that went out perfectly well.
    """


class TheRunHasNoDeliveryToRebaseError(Exception):
    """This run was asked to rebase a delivery it has not described, so there is no branch to move.

    **The branch a run delivers on and the branch it joins are both in the approved delivery**, and
    a rebase is about those two names and nothing else. A run that reached this node with neither
    was wired wrongly, and inventing a branch would be a push to a name nobody in this system chose.
    """


def no_model_was_given_to_settle_a_conflict(
    *_arguments: object, **_keywords: object
) -> WhatToDoAroundAConflict:
    """The default seam, which refuses, as `no_supervisor_was_given_to_this_run` refuses.

    **A default that raises rather than a required field, and the reason is the package.** Deciding
    what to do about a collision is reasoning, so it belongs in `TheAgentsThisRun` beside the seven
    agents that reason — but only one node ever needs it, and a required field would be paid for by
    every test in the repository that assembles a run and never reaches a conflict. So the default
    refuses when it runs, which is louder than a question nobody can answer.
    """
    raise ThereIsNoModelToSettleAConflictError


class ThereIsNoModelToSettleAConflictError(Exception):
    """A run reached a conflict with nothing that can decide about it.

    **The setting and the wiring disagree, and that is what the message is for.** A deployment that
    assembled this run without a model to settle conflicts, against a repository that produced one,
    has a run that will stop at the first collision with a sentence about its own configuration and
    nothing about the collision. Falling back would leave the choice to somebody who is not there.
    """


def settle_the_conflict_in_this_run(
    state: AgentState, settle_the_conflict: SettleTheConflict, rebase_the_branch: RebaseTheBranch
) -> Command:
    """Ask which repair to make, do it, and say on the record which one and why.

    **The decision is announced before it is acted on**, so a run that dies inside the repair still
    has the decision and the model's own reason on the card rather than only a traceback. The text
    is the model's: this system writes its own reasons nowhere near a decision about somebody else's
    repository, and a reason written on the model's behalf is the same forgery as a name.

    **The kind of conflict is named here rather than left to the seam**, because the node is what
    knows which situation it holds, and a seam that worked the kind out for itself would be a place
    where the three closed sets could be crossed.
    """
    the_decision = settle_the_conflict(
        WhatKindOfConflict.THE_PULL_REQUEST_CANNOT_BE_MERGED,
        _what_is_known_about_this_conflict(state),
    )
    something_the_run_said(
        state["work_item"].work_item_id, the_decision.the_text_of_the_decision_this_is()
    )

    if the_decision.which is WhatToDoWhenThePullRequestCannotBeMerged.REBASE_IT_AND_TRY_AGAIN:
        return _the_run_is_sent_to_ask_about_the_suite_again(state, rebase_the_branch)

    return _the_run_is_left_holding_an_open_pull_request(state)


def _what_is_known_about_this_conflict(state: AgentState) -> str:
    """GitHub's own sentence, or a refusal saying this run is not holding a conflict.

    **Read and not summarised, and refused rather than defaulted to a blank.** A blank question
    would ask a model to choose between two repairs with nothing to choose between, and the closed
    set would happily return a valid answer to it.
    """
    what_is_known = state.get(WHAT_STOPPED_THIS_RUN)

    if what_is_known is not None and what_is_known.strip():
        return what_is_known

    raise TheRunHasNoConflictToSettleError(
        "this run was asked to settle a conflict and holds none, so there is no question to put to "
        "a model. The merge node writes what GitHub said into the state before handing over, and "
        "this node is reached only from there — so reaching it without one is the wiring being "
        "wrong rather than a delivery with a conflict nobody mentioned"
    )


def _the_run_is_sent_to_ask_about_the_suite_again(
    state: AgentState, rebase_the_branch: RebaseTheBranch
) -> Command:
    """Put the commit on the branch it joins, and go back to the node that reads the checks.

    **Both commits are announced, because "rebased" is a claim and two shas are the fact.** The one
    before is what the pull request was pointing at and the one after is what it points at now, and
    a person deciding whether to merge it will compare the two against what the checks say.
    """
    what_the_rebase_left = rebase_the_branch(_the_rebase_this_delivery_needs(state))
    something_the_run_said(
        state["work_item"].work_item_id,
        f"rebased onto the branch this delivery joins: "
        f"{what_the_rebase_left.the_commit_it_was} is now "
        f"{what_the_rebase_left.the_commit_it_is_now}",
    )
    return Command(goto=WHERE_THE_SUITE_WENT_GREEN)


def _the_rebase_this_delivery_needs(state: AgentState) -> ARebaseOfTheBranchARunPushed:
    """The two branches, named by the approved delivery and by the checkout holding them.

    **`pull_request_request` and not `opened_pull_request`,** because a rebase is about names: the
    branch a run delivers on and the one it would join were both approved at the eighth gate, and
    the opened pull request carries a number and an address rather than either.
    """
    the_request = state["pull_request_request"]
    the_clone = state["clone"]

    if the_request is None or the_clone is None:
        raise TheRunHasNoDeliveryToRebaseError(
            f"a rebase needs the branch this run delivers on and the branch it would join, and "
            f"this run has {'no approved delivery' if the_request is None else 'no clone'}. "
            "Opening the pull request is what produces both, and it is wired before this node"
        )
    return a_rebase_of_the_branch_a_run_pushed(the_clone, the_request.branch, the_request.base)


def _the_run_is_left_holding_an_open_pull_request(state: AgentState) -> Command:
    """End the run with the pull request still open, and say on the record that nothing landed.

    **`THE_RUN_IS_OVER` and not a move to `DONE`.** `DONE` is a claim that the change is in somebody
    else's base branch, and the repair chosen here is precisely a decision not to put it there. The
    run's own record says which pull request is still open, so the next reader is not left looking
    for a merge that was never asked for.
    """
    the_pull_request = state["opened_pull_request"]
    something_the_run_said(
        state["work_item"].work_item_id,
        f"{the_pull_request.address if the_pull_request else 'the pull request'} is left open and "
        f"nothing was merged into {state['work_item'].repository.address}",
    )
    return Command(goto=THE_RUN_IS_OVER)
