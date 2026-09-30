"""Who answers a gate: a person, or a policy the deployment named.

**One decision, in one place, and it is a decision rather than a setting read at eight call
sites.** Every stage hands its work to the gate, so a run reaches eight edges that all went to
`ask_a_human`. Putting a policy on the far side of those would have meant teaching eight stages
about a deployment's configuration, and the eighth to be different from the seventh is how a
person stops being asked without anybody deciding that they should.

**A named policy routes to the policy and a run with none routes to the person.** One question,
one answer: `decisions` accumulates, so a run that both let a policy answer and interrupted a
person would hold two answers to one question and record whichever it read last.

**A conditional edge rather than a node that routes.** The first version put a node between the
handover and the gate, returning `Command(goto=...)`. It parked correctly and then could not be
resumed — a graph parked on an interrupt reached through a `Command` routing did not deliver the
answer to the node that asked, so the decision arrived empty and the run finished having
recorded nothing. `add_conditional_edges` is the mechanism this repository already uses for the
router after a gate, and resuming through it is what the gate tests have always relied on.

**The setting is read here, at the moment of the decision, and refused if it is broken.** A
truncated policy name stops the run rather than falling back, because the fallback is a run that
answers its own gate with a policy nobody can name in the record.
"""

from __future__ import annotations

from aisdlc.agents.review_an_artifact import the_policy_a_deployment_stated
from aisdlc.graph.agent_state import AgentState

# **The two destinations, named, because a route is a promise and a promise wants a name.**
WHERE_A_PERSON_ANSWERS = "ask_a_human"
WHERE_A_POLICY_ANSWERS = "let_the_policy_answer"
THE_GATE_IS_ANSWERED_BY: list[str] = sorted(
    {WHERE_A_POLICY_ANSWERS, WHERE_A_PERSON_ANSWERS}
)


def where_the_gate_leads(state: AgentState) -> str:
    """Name the destination: the policy a deployment stated, or a person.

    **`state` is unused and declared anyway, because a LangGraph conditional edge is called with
    the state and a reader has to be able to see that the shape is satisfied deliberately.**
    Whether a policy is in charge is a fact about the deployment, not about the work item, so
    nothing here depends on what the run produced.
    """
    if the_policy_a_deployment_stated() is None:
        return WHERE_A_PERSON_ANSWERS

    return WHERE_A_POLICY_ANSWERS
