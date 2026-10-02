"""The state machine: the biconditional invariant, and the table of legal moves."""

from __future__ import annotations

from aisdlc.domain.role import Role
from aisdlc.domain.stage import Stage
from aisdlc.domain.work_item import WorkItem

STAGES_WITHOUT_AN_AGENT = (
    Stage.IDLE,
    Stage.AWAITING_HUMAN_APPROVAL,
    Stage.READY,
    Stage.DONE,
)
"""The stages where nobody is working on the work item, and the stage always says so.

**`AWAITING_AGENT_PICKUP` is deliberately not on this list**, though a released work item waits in
it with no agent. The stage is reached both ways and both are correct, so it is in
`STAGES_WHERE_EITHER_IS_ALLOWED` rather than here.

**`READY` is the stage a released work item most resembles, and it sits here for that reason.** A
ticket nobody has looked at and a change nobody has picked up yet are one situation, and the board
already renders `READY` and `IDLE` as one column. `AWAITING_AGENT_PICKUP` is that same situation
reached from the other end, so it cannot be forced onto this side: nine pickup nodes reach it with
an agent named and one release reaches it without.
"""

STAGES_WITH_AN_AGENT = (
    Stage.IN_PROGRESS_BY_AGENT,
)
"""The stages where somebody is working on the work item and the stage must say who.

**Only one stage, and that is the half of the biconditional that protects a run from believing it
is doing something.** A work item in progress with no agent named is a run that thinks it is
working; the release moves the work item out of here precisely so this can keep holding.
"""

STAGES_WHERE_EITHER_IS_ALLOWED = (
    Stage.AWAITING_AGENT_PICKUP,
)
"""The stages where the work item may be held or unheld, because the stage is the handover itself.

**`AWAITING_AGENT_PICKUP` is reached both ways, and both are correct.** Every pickup node — nine of
them, one per discipline — asks for this stage *naming* the agent it is about to hand the work to,
because that is how a run says which agent owns the work item from the moment it is claimed. A
release asks for the same stage naming **nobody**, because a repair means the refusing agent lets
go and the next agent has not been named yet: that choice is the supervisor's and it has not been
made. Both arrive at "waiting to be picked up", and which of the two it is depends entirely on
whether somebody has claimed it yet.

**A third category rather than a relaxed second one.** Putting this stage on either side of the
biconditional made one of the two moves illegal, and the failure arrived as
`AWAITING_AGENT_PICKUP requires no agent, but aisdlc-dev-impl holds the work item` out of a run
whose supervisor had just named its next agent. Naming the third case says what is true: this
stage is the queue, and a queued work item has an agent on it only once somebody has claimed it.
"""

LEGAL_TRANSITIONS: dict[Stage, frozenset[Stage]] = {
    Stage.IDLE: frozenset({Stage.AWAITING_AGENT_PICKUP}),
    # `AWAITING_AGENT_PICKUP` reaches itself so that a work item waiting in the queue can be
    # **claimed**. Every pickup node asks for this stage naming the agent about to take the work,
    # and after a release the work item is already in the stage held by nobody, so without this
    # row the run that the supervisor just sent back died at the pickup with
    # `AWAITING_AGENT_PICKUP cannot move to AWAITING_AGENT_PICKUP`. Claiming changes the holder and
    # not the stage, which is what the stage means: the work is waiting to be picked up, and stops
    # waiting when somebody picks it up. `_takes_the_work_item_from_the_holding_agent` allows it
    # as written — it only refuses a move from one agent into *another agent's* hands, and a work
    # item nobody holds is not held by anybody.
    Stage.AWAITING_AGENT_PICKUP: frozenset(
        {Stage.AWAITING_AGENT_PICKUP, Stage.IN_PROGRESS_BY_AGENT}
    ),
    Stage.IN_PROGRESS_BY_AGENT: frozenset(
        {Stage.AWAITING_HUMAN_APPROVAL, Stage.AWAITING_AGENT_PICKUP}
    ),
    Stage.AWAITING_HUMAN_APPROVAL: frozenset({Stage.AWAITING_AGENT_PICKUP, Stage.DONE}),
    Stage.READY: frozenset({Stage.AWAITING_AGENT_PICKUP}),
    Stage.DONE: frozenset(),
}


class StateMachineError(Exception):
    """A work item would break a rule of the state machine."""


def validate_state(work_item: WorkItem) -> None:
    """Assert that a work item satisfies the invariants of its own state.

    Two rules, both decidable from one work item alone:

    an agent is present if and only if the stage is one an agent owns, and a work
    item in the `AI` handoff role always has an agent acting on it, because a
    handoff is not a discipline that owns work and cannot outlive the agent
    performing it. Who is *allowed* to move the work item is a question about two
    moments in time, so it belongs to `transition` rather than here.

    **One stage is exempt, and it is exempt because it is reached both ways.**
    `AWAITING_AGENT_PICKUP` holds an agent when a pickup node has named it and holds none when a
    refusing agent has released the work item and the supervisor has not yet said who works next.
    Both are the queue, so the stage says nothing either way about who holds the work item and this
    function says nothing about it. Every other stage is still on exactly one side of the
    biconditional, and `test_every_stage_says_something_about_who_holds_the_work_item` checks that
    the three lists between them cover every stage once.

    Silence means the work item holds. A violation raises `StateMachineError`
    naming what broke, so a reader learns why without instrumenting this module.
    """
    if work_item.stage in STAGES_WHERE_EITHER_IS_ALLOWED:
        return
    stage_without_an_agent = work_item.stage in STAGES_WITHOUT_AN_AGENT
    if stage_without_an_agent and work_item.agent is not None:
        raise StateMachineError(
            f"{work_item.stage.value} requires no agent, but {work_item.agent} holds the work item"
        )
    if not stage_without_an_agent and work_item.agent is None:
        raise StateMachineError(
            f"{work_item.stage.value} requires an agent, but the work item has none"
        )


def _takes_the_work_item_from_the_holding_agent(
    holding_agent: str | None, agent_after_the_move: str | None
) -> bool:
    """Report whether a move would put the work item in another agent's hands.

    An agent that holds a work item either still holds it after a move, or has let
    it go by naming no agent. Naming a *different* agent is neither: the lifecycle
    has no release from one agent to a peer, only a hand-over to a human, so that
    call would let any agent take work assigned to another by claiming it in the
    same breath.
    """
    if holding_agent is None:
        return False
    if agent_after_the_move is None:
        return False
    return agent_after_the_move != holding_agent


def transition(
    work_item: WorkItem,
    to_stage: Stage,
    agent: str | None,
    accountable_role: Role,
) -> WorkItem:
    """Move a work item to a legal next stage and hand back the moved work item.

    This is the only door. The stage is never assigned anywhere else, and neither is
    the role, so whatever leaves this function has passed the transition table, the
    biconditional and the role rules, and a model's proposed stage is checked here
    like any other caller's.

    `agent` and `accountable_role` are both required rather than defaulted, and for
    the same reason: a move into a stage an agent owns has to say who holds the work
    item afterwards and which discipline answers for it, and a move into a resting
    stage has to say that nobody does. A default would let a caller forget the
    difference and produce a work item nobody intended.

    **A turn at the work item is counted here rather than in the pickup**, because the
    graph does not go through the board's pickup gesture: it asks for
    `IN_PROGRESS_BY_AGENT` and the transition node applies it, so counting in the
    gesture would count nothing in a real run and every one of those runs would
    present a second version of an artifact as the first. The edge
    `-> IN_PROGRESS_BY_AGENT` *is* the pickup -- it is what the table calls picking a
    card up -- and it is the only edge that means an agent has begun, so it is the
    one place the count can be right without a caller remembering to ask.

    The role travels with the move because it cannot travel any other way. The work
    item is frozen and one node is the only writer of it, so an orchestrator that
    set the role beside the move would be a second writer, which is the thing the
    single-writer rule exists to forbid.

    An illegal move raises rather than returning the work item unchanged, so a
    pipeline cannot mistake a refusal for progress. The exception names both stages
    and lists what would have been legal, because the usual cause is a caller that
    believes it is somewhere else in the lifecycle.

    Taking the work item from the agent that holds it is refused here rather than in
    `validate_state`, because it is a claim about this move and the one before it,
    not a property of a single work item.

    The moved work item is built through the constructor rather than with
    `model_copy`, which is deliberate and is the reason the field list is spelled
    out: `model_copy` does not validate its update, so it is the one way to let
    something meaningless through the only door. Naming the fields is the price of
    the guarantee, and it is also what a reader wants to see.

    That price is a list to keep in step with the model, and it was not kept:
    `commissioned_from` was dropped by every move, so a run lost the request it
    was commissioned from at its first transition and its summary said it had none.
    `test_a_transition_names_every_field_the_work_item_has` reads this call and
    compares it with the model, which is the only way to be told about a field no
    test has heard of yet. A field that travels with the work item belongs here, not
    just the three this function moves.
    """
    legal_targets = LEGAL_TRANSITIONS[work_item.stage]
    if to_stage not in legal_targets:
        legal_names = ", ".join(sorted(stage.value for stage in legal_targets)) or "none"
        raise StateMachineError(
            f"{work_item.stage.value} cannot move to {to_stage.value}; "
            f"it may move to {legal_names}"
        )

    if _takes_the_work_item_from_the_holding_agent(work_item.agent, agent):
        raise StateMachineError(
            f"{work_item.agent} holds this work item and cannot hand it to {agent}; "
            f"a work item is released to a human, not to another agent"
        )

    work_done = work_item.work_done
    if to_stage is Stage.IN_PROGRESS_BY_AGENT:
        work_done = work_done.and_another_turn_at_it_was_worked_on(agent)

    moved = WorkItem(
        work_item_id=work_item.work_item_id,
        repository=work_item.repository,
        stage=to_stage,
        role=accountable_role,
        commissioned_by=work_item.commissioned_by,
        requested=work_item.requested,
        agent=agent,
        work_done=work_done,
    )
    validate_state(moved)
    return moved
