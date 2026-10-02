"""A work item nobody is holding, waiting in the queue, is a stage the biconditional left out.

**A real run, the repair supervisor's first firing on one, and the run dying twice for it.** The
implementer handed a refusal on, the supervisor named the planner, and the run died at the
planner's pickup with `StateMachineError: aisdlc-dev-impl holds this work item and cannot hand it
to`. A work item in `IN_PROGRESS_BY_AGENT` holds exactly one agent and the table refuses to move it
into another's hands, which is right — so the work item has to come back to the queue first, and
`AWAITING_AGENT_PICKUP` is where a released work item waits.

**`AWAITING_AGENT_PICKUP` was in `STAGES_WITH_AN_AGENT`, and that is the second death.** Every
other move into that stage names the agent about to pick it up, so the stage always had an agent
and the biconditional held. Releasing a work item means naming **nobody** — the agent that will
take it next is the supervisor's judgement and has not been made yet — and `validate_state` raised
`AWAITING_AGENT_PICKUP requires an agent, but the work item has none` before the move was made.

**So the stage means "waiting to be picked up", and waiting is exactly what an agent-less work
item is doing.** `READY` already means the same thing — a ticket nobody has looked at yet — and it
already sits with `IDLE` in the stages without an agent, sharing a board column for that reason.
This stage is the same fact reached from the other end: a work item whose previous agent let it
go and whose next one has not been named. **The table is untouched**, because `IN_PROGRESS_BY_AGENT
-> AWAITING_AGENT_PICKUP` has always been legal and every run has simply never taken it with
`agent=None`.

**What this does not change.** `IN_PROGRESS_BY_AGENT` still requires an agent, and that is the
biconditional doing its job: a work item somebody is working on must say who. A pickup node asks
for `AWAITING_AGENT_PICKUP` naming the agent it is about to hand to, so a run at a gate waiting
for its next agent is still named from the moment it is picked up rather than from when the work
item was released.
"""

from __future__ import annotations

import pytest

from aisdlc.domain.commissioned_request import a_request_about
from aisdlc.domain.repository import Repository
from aisdlc.domain.role import Role
from aisdlc.domain.stage import Stage
from aisdlc.domain.state_machine import (
    STAGES_WHERE_EITHER_IS_ALLOWED,
    STAGES_WITH_AN_AGENT,
    STAGES_WITHOUT_AN_AGENT,
    StateMachineError,
    transition,
)
from aisdlc.domain.work_item import a_work_item_commissioned_for_an_agent

A_REPOSITORY = Repository(owner="an", name="owner")
THE_IMPLEMENTER = "aisdlc-dev-impl"


def _a_work_item_somebody_is_holding() -> object:
    """A work item mid-change, which is the state a refusal is raised from."""
    commissioned = a_work_item_commissioned_for_an_agent(
        work_item_id="issue-9",
        repository=A_REPOSITORY,
        accountable_role=Role.DEV,
        commissioned_by="a person",
        requested=a_request_about("remove the fallback"),
    )
    picked_up = transition(commissioned, Stage.AWAITING_AGENT_PICKUP, THE_IMPLEMENTER, Role.DEV)
    return transition(picked_up, Stage.IN_PROGRESS_BY_AGENT, THE_IMPLEMENTER, Role.DEV)


def test_a_work_item_in_the_queue_waits_with_nobody_holding_it() -> None:
    """Released, it is waiting to be picked up — and waiting is what an agent-less work item does.

    **The stage this reaches is `AWAITING_AGENT_PICKUP`, and it is legal.** `IN_PROGRESS_BY_AGENT
    -> AWAITING_AGENT_PICKUP` has been in the table since this repository was assembled; no run
    had ever taken it, because no run had ever released a work item before a repair. The move is
    therefore not new and the table is unchanged — what is new is that the arriving stage no longer
    requires an agent to be named, which is what a release is.
    """
    released = transition(
        _a_work_item_somebody_is_holding(), Stage.AWAITING_AGENT_PICKUP, None, Role.DEV
    )

    assert released.stage == Stage.AWAITING_AGENT_PICKUP, (
        f"the release landed on {released.stage.value!r} rather than the stage a work item waits "
        "in, so the agent the supervisor names has no queue to be handed the work from"
    )
    assert released.agent is None, (
        f"the release left the work item held by {released.agent!r}, which is the peer hand-over "
        "the table refuses and the reason a real run died of `StateMachineError`"
    )


def test_waiting_to_be_picked_up_is_a_stage_that_needs_no_agent() -> None:
    """The biconditional, and why this one stage is the exception it now names.

    **Both directions, because a biconditional with one direction is half a rule.** Every other
    stage in this table either always has an agent or never does; this one does both, and which it
    does is the fact the stage is for. A work item is picked up *at* the moment a node names the
    agent — `apply_the_pickup_by_the_planner` and its eight siblings all ask for this stage naming
    themselves — so a work item sitting here with no agent is one that was released by a refusal
    and has not been claimed yet.

    **`READY` says the same thing and shares a board column with `IDLE` for it.** A ticket nobody
    has looked at and a change nobody has picked up yet are one situation seen from two ends, and
    the board already renders them as one column. Putting this stage on the same side of the
    biconditional as `READY` is what makes that shared column true at the level of the state
    machine rather than only in the view.
    """
    assert Stage.AWAITING_AGENT_PICKUP in STAGES_WHERE_EITHER_IS_ALLOWED, (
        "a released work item waits in `AWAITING_AGENT_PICKUP` held by nobody while nine pickup "
        "nodes reach the same stage naming the agent about to take it, so the stage allows either "
        "and `validate_state` must say nothing about it. Without this the release fails validation "
        "and a run cannot repair — a real run died of `AWAITING_AGENT_PICKUP requires no agent, "
        "but aisdlc-dev-impl holds the work item`, one fix after it died of the mirror-image one"
    )
    assert Stage.AWAITING_AGENT_PICKUP not in STAGES_WITHOUT_AN_AGENT, (
        "the queue stage is also in the stages that forbid an agent, so the nine pickup nodes that "
        "name one are refused and no run can start"
    )
    assert Stage.AWAITING_AGENT_PICKUP not in STAGES_WITH_AN_AGENT, (
        "the queue stage is also in the stages that require one, so a release naming nobody is "
        "refused and a run cannot repair"
    )


def test_every_stage_says_something_about_who_holds_the_work_item() -> None:
    """The three lists, and that between them they cover every stage exactly once.

    **This is the biconditional's own completeness, and it is the check the two lists never had.**
    A stage in none of the three is one `validate_state` says nothing about, so it would validate
    whether or not it names an agent. A stage in two of them is a table that contradicts itself,
    and which of the two rules a reader believes is decided by which line they happened to read.
    Neither failure raises; both are a work item in a state nobody could describe.

    **Read out of all three rather than two**, because the exempt stage is exactly the kind of entry
    a check written before it existed would not know to look for.
    """
    every_stage = set(Stage)
    the_three_lists = {
        STAGES_WITHOUT_AN_AGENT,
        STAGES_WITH_AN_AGENT,
        STAGES_WHERE_EITHER_IS_ALLOWED,
    }

    assert all(
        len(the_lists) == len(set(the_lists)) for the_lists in the_three_lists
    ), "one of the three lists holds the same stage twice"
    assert set().union(*the_three_lists) == every_stage, (
        f"{sorted(the_stage.value for the_stage in every_stage - set().union(*the_three_lists))} "
        "is in none of the three lists, so `validate_state` checks nothing about whether an agent "
        "holds the work item"
    )


def test_an_agent_may_claim_a_work_item_that_is_waiting_in_the_queue() -> None:
    """A work item nobody holds can be claimed, and claiming it is not a change of stage.

    **The half of the release a real run found after the half before it.** The release puts a
    work item in the queue with nobody holding it; the supervisor then names a stage and the run
    arrives at that stage's pickup node, which asks for `AWAITING_AGENT_PICKUP` naming the agent
    about to take it. The stage is the one it is already in, and the table refused:

        StateMachineError: AWAITING_AGENT_PICKUP cannot move to AWAITING_AGENT_PICKUP

    **A queued work item is claimed, and claiming it changes the holder rather than the stage.**
    That is what the stage means: the work is waiting to be picked up, and it stops waiting when
    somebody picks it up. `_takes_the_work_item_from_the_holding_agent` allows it without being
    touched, because it only refuses a move that would put a work item one agent holds into
    *another agent's* hands — and a work item nobody holds is not held by anybody.

    **One row, and not a general rule about self-moves.** Every other stage still cannot move to
    itself, and that is worth keeping: a stage that could move to itself would make a rewiring
    error invisible rather than loud.
    """
    waiting_in_the_queue = transition(
        _a_work_item_somebody_is_holding(), Stage.AWAITING_AGENT_PICKUP, None, Role.DEV
    )

    claimed = transition(
        waiting_in_the_queue, Stage.AWAITING_AGENT_PICKUP, "aisdlc-dev-plan", Role.DEV
    )

    assert claimed.stage == Stage.AWAITING_AGENT_PICKUP, (
        f"claiming a queued work item moved it to {claimed.stage.value!r} rather than leaving it "
        "waiting to be picked up, so the stage no longer says what it says"
    )
    assert claimed.agent == "aisdlc-dev-plan", (
        f"the work item is waiting in the queue and nobody holds it — the claim asked for "
        f"{claimed.agent!r}, which is the whole of what a claim is"
    )


def test_a_stage_still_cannot_move_to_itself() -> None:
    """The row added for claiming is one row, and not a new rule about self-moves.

    **Every other stage, and this is the half that keeps a rewiring error loud.** A table where a
    stage could generally move to itself would accept a node wired to itself — the `Command`-plus-
    edge defect that killed every repair in this system would become a loop nobody sees rather
    than a `StateMachineError` at build time. One row says exactly one thing: a work item waiting
    in the queue may be claimed.
    """
    for a_stage in Stage:
        if a_stage is Stage.AWAITING_AGENT_PICKUP:
            continue
        at_that_stage = _a_work_item_moved_to(a_stage, "aisdlc-dev-impl")
        if at_that_stage.stage is not a_stage:
            continue
        who_holds_it_now = at_that_stage.agent
        with pytest.raises(StateMachineError):
            transition(at_that_stage, a_stage, who_holds_it_now, Role.DEV)


def _a_work_item_moved_to(a_stage: Stage, agent: str) -> object:
    """A work item standing at any stage, reached by walking the table and naming an agent.

    **Walked and not jumped, because every stage's row names where it comes from and jumping
    would read as a bug in the test.** The two stages with no agent are reached naming `None` and
    the rest name the agent holding them, so each work item this builds satisfies the biconditional
    before the self-move is attempted — otherwise the test would pass by refusing the wrong thing.
    """
    a_work_item = a_work_item_commissioned_for_an_agent(
        work_item_id="issue-9",
        repository=A_REPOSITORY,
        accountable_role=Role.DEV,
        commissioned_by="a person",
        requested=a_request_about("remove the fallback"),
    )
    the_stages_a_work_item_passes_through = (
        Stage.AWAITING_AGENT_PICKUP,
        Stage.IN_PROGRESS_BY_AGENT,
        Stage.AWAITING_HUMAN_APPROVAL,
        Stage.DONE,
    )
    if a_stage not in the_stages_a_work_item_passes_through:
        return a_work_item

    for a_stage_on_the_way in the_stages_a_work_item_passes_through:
        who_holds_it = agent
        if a_stage_on_the_way in (Stage.AWAITING_HUMAN_APPROVAL, Stage.DONE):
            who_holds_it = None
        a_work_item = transition(a_work_item, a_stage_on_the_way, who_holds_it, Role.DEV)
        if a_stage_on_the_way is a_stage:
            return a_work_item
    return a_work_item


def test_a_work_item_somebody_is_working_on_still_must_name_who() -> None:
    """The half of the biconditional the exception does not touch.

    **`IN_PROGRESS_BY_AGENT` still requires an agent, and a released work item is not that stage.**
    This is the half that would be lost if the fix above had moved the wrong stage, or had made
    every stage lenient: a work item in progress with nobody working on it is a run that believes
    it is doing something, which is the failure a board exists to make visible. The release moves
    the work item *out* of this stage precisely so that this rule can keep holding.
    """
    with pytest.raises(StateMachineError):
        transition(
            _a_work_item_somebody_is_holding(),
            Stage.IN_PROGRESS_BY_AGENT,
            None,
            Role.DEV,
        )


