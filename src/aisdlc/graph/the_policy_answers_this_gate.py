"""The graph's one line between a policy and the node that answers with it.

**A function, because `add_node` infers its type from the callable and a bare `Callable` alias
does not carry the state type through.** Every other seam in the graph is wrapped in the same
shape for the same reason, and this is that shape for the gate's.

The indirection buys one thing worth having: the graph never learns what a policy is. It hands
over a node and receives state, and whether that node asks a model or answers from a script is
the deployment's business.
"""

from __future__ import annotations

from aisdlc.agents.review_an_artifact import AnswerTheGate
from aisdlc.graph.agent_state import AgentState


def the_policy_answers_this_gate(state: AgentState, policy: AnswerTheGate) -> dict:
    """Hand the run to the node the deployment gave this graph to answer its gates."""
    return policy(state)
