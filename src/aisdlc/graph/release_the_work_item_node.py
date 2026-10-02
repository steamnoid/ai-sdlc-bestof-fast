"""The move that hands a work item back to the queue before a repair may take it.

**A real run, the repair supervisor's first firing on one, and the run dying because this node
did not exist.** Asked to remove a hardcoded session-secret fallback, the implementer wrote
`tests/unit/session-secret.test.js` while `vitest.config.ts` collects `*.ts` — so the file was
never opened by the runner. The supervisor caught it, named it, and sent the run back to the
planner. The run then died at the planner's pickup:

    StateMachineError: aisdlc-dev-impl holds this work item and cannot hand it to

**The refusal was routed correctly and the work item was never let go of.** A work item in
`IN_PROGRESS_BY_AGENT` holds exactly one agent, and `_takes_the_work_item_from_the_holding_agent`
exists so that an agent cannot hand work straight to a peer — which is right, and which made the
supervisor's verdict unrepresentable. Every routing test passed: each one calls a node and reads
the `Command` it returns, so nothing ever had the work item in a hand.

**So the release asks for the move and hands on, and it is not the node that makes it.**
`transition_the_work_item` is the only writer of a work item in this package, so this node names
where the work item should go and the graph walks it through the node that does the writing. **It
returns a plain update and not a `Command`, and that is the whole reason:** a `Command` names its
own destination, so returning one would skip the transition node entirely and the request would sit
in the state — which is what the first version of this fix did, and the run still died at the same
`StateMachineError`, one node later.
"""

from __future__ import annotations

from aisdlc.graph.agent_state import AgentState

WHERE_AN_AGENT_LETS_GO_OF_THE_WORK_ITEM = "let_go_of_the_work_item"

# What the three nodes that hand a refusal on reach, and what this node asks for. **A constant
# rather than a shape written three times,** because the refusal and the move it earns are one
# event and this is where both halves are written.
THE_STAGE_A_RELEASED_WORK_ITEM_WAITS_AT = "AWAITING_AGENT_PICKUP"


def let_go_of_the_work_item(state: AgentState) -> dict:
    """Ask for the work item to come back to the queue, held by nobody.

    **The agent is `None` and this is the whole of it.** A work item in `IN_PROGRESS_BY_AGENT`
    holds exactly one agent, and `_takes_the_work_item_from_the_holding_agent` refuses a move that
    would put it in another's hands. A repair is exactly such a move, which is why this has to
    happen before the supervisor names anybody — and this node cannot name that agent itself:
    which agent works next is the supervisor's judgement and has not been made yet, so a node that
    guessed would be a second place a run decides who works next.

    **The role is carried because a work item's accountable discipline travels with every move**
    and this node is not changing it — it is releasing the work item, not reassigning it.

    **The refusal is neither read nor rewritten here.** `what_stopped_this_run` is already in the
    state, written by the node that handed over, and the supervisor reads it in that node's own
    words. A summary here would be a decision made on a summary.
    """
    from aisdlc.domain.stage import Stage

    return {
        "requested_stage": Stage[THE_STAGE_A_RELEASED_WORK_ITEM_WAITS_AT],
        "requested_agent": None,
        "requested_role": state["work_item"].role,
    }
