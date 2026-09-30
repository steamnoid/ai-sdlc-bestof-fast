"""The two nodes that make the gate a gate: ask whoever answers, then record what they said.

**One name changed and two did not, and the reasons are different.** This node was
`record_what_was_decided` and a deployment can now put a policy at the gate, so the
name was false about the thing it does: it records whatever answered, and a policy answers.
`ask_a_human` is still `ask_a_human` because it does ask a human, and it is only reached when
one is the answerer — the routing in `who_answers_a_gate` is what makes that true, and a
node whose name says `human` and whose body asks a model would be the actual lie.

They are two nodes and not one because a LangGraph node re-runs from its first line on
resume. Anything that ran before the `interrupt()` would run again after the gate is
answered, so a model call or a side effect placed before it would be paid for twice per
approval. The node that asks therefore does nothing but ask, and the recording happens
in the next one.
"""

from __future__ import annotations

from langgraph.types import interrupt

from aisdlc.approval.approval_decision import ApprovalDecision
from aisdlc.approval.approval_gate import record_the_decision
from aisdlc.approval.approval_question import ApprovalQuestion
from aisdlc.graph.agent_state import AgentState
from aisdlc.store.what_a_run_records import (
    the_decision_was_recorded,
    the_gate_started_asking,
)


class NobodyAnsweredTheGateError(Exception):
    """The run reached the recording with nobody having answered the question."""


def ask_a_human(state: AgentState) -> dict:
    """Put the question to a human and stop the run until somebody answers.

    The value handed to `interrupt` is the question, which is serialisable because it names
    a work item, an artifact and a version rather than carrying an artifact. What comes back
    on the second pass is a validated `ApprovalDecision`, because `interrupt` is handed the
    model's class and parses the answer before returning it.

    **The question is written to the register before the run is parked.** That is the one
    fact a killed run cannot rebuild: everything else it replays by reading the artifacts it
    already wrote, and which artifact it was in the middle of asking about is the question it
    never got answered. A board reading this therefore knows a run is *waiting*, rather than
    guessing it from a stage — and a run killed in here leaves a card that says so, which is
    the difference between a stopped run and a vanished one.

    The `interrupt` is still the only statement that stops the run. Recording the question is
    an announcement, not a second suspension point, and it is the same function that says it
    to the store, so a policy answering the gate and a person answering it leave the same
    trace.
    """
    the_question = ApprovalQuestion(
        work_item_id=state["work_item"].work_item_id,
        artifact_id=state["presented_artifact_id"],
        artifact_version=state["presented_artifact_version"],
    )
    the_gate_started_asking(
        the_question.work_item_id,
        the_question.artifact_id,
        the_question.artifact_version,
    )

    return {
        "decisions": [
            interrupt(the_question, response_schema=ApprovalDecision),
        ]
    }


def record_what_was_decided(state: AgentState) -> dict:
    """Turn whatever answered into the record it earns, or into no record at all.

    **A person's and a policy's answer arrive through the same channel and leave through the
    same rules.** That is deliberate: a machine added to a boundary is exactly where a shortcut
    past the rules would be written, and this node is what makes the shortcut unnecessary.

    The gate's own rules run here, against what was actually presented rather than
    against the work item's stage, so a decision about a version that has moved on is
    refused rather than believed.

    Three outcomes and the caller can tell them apart: an affirmative current decision
    leaves an `Approval`; a refusal leaves none, which is a completed gate rather than a
    fault; and reaching here with no answer at all is a broken run, which is neither.

    **A refusal writes no channel at all** rather than an empty one, because the refusal is
    already in `decisions` and the absence of an approval is what it means. Writing an empty
    list would be a second thing to read to learn the same fact.

    **The answer is also written to the register**, and it is written *after* the gate has
    cleared it — so a decision the gate refused is never on the board, which is the whole
    reason the gate is a separate function from the recorder.
    """
    decision = state["decisions"][-1] if state["decisions"] else None
    if decision is None:
        raise NobodyAnsweredTheGateError(
            f"the gate asked about {state['presented_artifact_id']} version "
            f"{state['presented_artifact_version']} and the run reached the recording "
            f"with nobody having answered"
        )

    recorded = record_the_decision(
        decision,
        state["work_item"],
        state["presented_artifact_id"],
        state["presented_artifact_version"],
    )
    the_decision_was_recorded(decision)
    if recorded is None:
        return {}

    return {"approvals": [recorded]}
