"""The gate: it decides whether a decision may be recorded, and never decides itself."""

from __future__ import annotations

from aisdlc.approval.approval_decision import ApprovalDecision
from aisdlc.domain.approval import Approval
from aisdlc.domain.stage import Stage
from aisdlc.domain.work_item import WorkItem

# Agent identifiers are the `aisdlc-` namespace the glossary fixes. Anything in it is
# an agent, and the gate's rule is about the namespace rather than about a list of
# agents, so an agent invented tomorrow is refused without this changing.
AGENT_IDENTIFIER_PREFIX = "aisdlc-"

# **A policy names itself, and this is where it says so.** The agent namespace above is a
# refusal — anything in it may not answer. This one is the opposite: a name in it is *claiming*
# to be a policy rather than a person, and a claim has to carry the thing it claims to be. An
# identity nobody can read is a record nobody can follow up on.
THE_POLICY_NAMESPACE = "autopilot:"


class APolicysDecisionNamedNoPolicyError(Exception):
    """A decision claimed the policy namespace and left the policy unnamed.

    **Worse than a name nobody recognises, because it looks like a record.** `autopilot:` says
    a policy decided and does not say which; a reader can follow up on a person and can follow
    up on nothing at all here. It is also the shape a truncated configuration value takes, so
    it is not a far-fetched input — it is the one that will actually arrive.
    """

    def __init__(self, decided_by: str) -> None:
        """Quote the claim back, because the fix is a character in the middle of a string."""
        self.decided_by = decided_by
        super().__init__(
            f"{decided_by!r} says a policy decided and names no policy, so the record says a "
            f"decision was made on somebody's behalf by something that cannot be asked about it. "
            f"A policy is written as {THE_POLICY_NAMESPACE}<the policy's name>."
        )


class DecisionNotApplicableError(Exception):
    """A decision was not about the work item, artifact and version it was asked for."""


class AgentDecidedError(Exception):
    """An agent answered the human approval gate, which only a human may do."""


class NotAtTheApprovalGateError(Exception):
    """A work item that is not standing at the approval gate was sent to it."""


def the_policy_named_by(decided_by: str) -> str | None:
    """The policy a name claims to be, or `None` when it claims nothing.

    **One-directional on purpose.** A name outside the namespace is `None` and the gate does
    nothing with it, because a name is not a namespace: refusing names that look unusual would
    refuse people, and reshaping a name to fit a prefix would make it impossible to match to
    the person who decided. So the gate reads the namespace when a name claims it and stays
    silent otherwise — and a claim obliges the claimant to name a policy.
    """
    if not decided_by.startswith(THE_POLICY_NAMESPACE):
        return None

    return decided_by[len(THE_POLICY_NAMESPACE) :].strip() or None


def decided_by_claims_a_policy_and_names_none(decided_by: str) -> bool:
    """Whether a name is inside the policy namespace with nothing behind it.

    **A separate question from `the_policy_named_by`, so the gate reads it once.** The reader
    answers "is this a policy, and which"; this answers only the half that can be refused. Two
    names so the refusal is a sentence about the name rather than a string comparison buried in
    a branch.
    """
    return (
        decided_by.startswith(THE_POLICY_NAMESPACE)
        and the_policy_named_by(decided_by) is None
    )


def the_record_left_by_a_decision(decision: ApprovalDecision) -> Approval | None:
    """The record this decision earns, or `None` — and `None` is the answer for a refusal.

    **Separate from `record_the_decision` on purpose, because the two answer different
    questions.** That one is the gate: it checks that the answer is about the thing the gate
    asked about, and it is the only door a decision may come through. This one is the
    recorder: it takes a decision the gate has already cleared and says what it leaves behind.

    The split is what lets a browser and a policy write into the same record table without
    either of them being able to skip the gate — there is one gate and one recorder, and a
    caller reaching for the recorder has already been through the gate.

    **A refusal returns `None`, and a run answered "no" at the requirements gate is one of the
    most ordinary things that happens here.** Silence is a fault and "no" is an outcome, so a
    refusal is recorded as a decision and leaves no approval behind.
    """
    if not decision.approved:
        return None

    return Approval(
        work_item_id=decision.work_item_id,
        artifact_id=decision.artifact_id,
        artifact_version=decision.artifact_version,
        approved_by=decision.decided_by,
        approved_at=decision.when_it_was_decided(),
        # Copied verbatim, because the gate validates what it was given rather than editing
        # it — a reason that reached the gate is a reason the record keeps, including one
        # that says the artifact should not have been approved.
        reason=decision.reason,
    )


def record_the_decision(
    decision: ApprovalDecision,
    work_item: WorkItem,
    presented_artifact_id: str,
    current_artifact_version: int,
) -> Approval | None:
    """Turn a decision into the record it earns, or into no record at all.

    The gate never decides. It can only say whether an answer it was given is an
    answer about the thing it asked about, and it answers that question three ways.

    An affirmative decision about the work item's current artifact version leaves an
    `Approval` behind. A refusal leaves nothing, which is a completed gate and not a
    fault: silence is a fault, "no" is an outcome. A decision about another work
    item, another artifact, or a version the artifact has moved past raises, because
    a human was asked about one thing and answered about another, and recording that
    as a decision would put a record against work nobody ruled on.

    The gate is *told* what it presented rather than working it out from the answer,
    because a gate that inferred the question from the response would be checking the
    response against itself. The first draft of this function had no such parameter
    and therefore could not check the artifact at all: a decision about a different
    artifact passed, because there was nothing to compare it to.

    The record is made under the identity in the decision, copied verbatim. That is
    the whole of the unattended mode: the gate runs on a person's behalf and the
    record is kept on that person's behalf too, so a policy's decision has to be
    recorded under the policy. A record naming a person for a decision that policy
    made would be a forged audit trail, and it would be indistinguishable from the
    real thing at exactly the moment somebody needs to tell them apart.

    Two refusals protect the boundary itself, and neither of them is about whether
    the decision is a good one. The gate refuses a decision made by an agent, because
    section 11 forbids an agent approving an agent's output and a gate that would
    accept its own identifier is not a gate. It refuses a work item that is not
    standing at it, because a decision recorded against a work item that has already
    finished is evidence of a human ruling on work that was over.
    """
    if work_item.stage is not Stage.AWAITING_HUMAN_APPROVAL:
        raise NotAtTheApprovalGateError(
            f"{work_item.stage.value} is not the approval gate, "
            f"so no decision belongs to it"
        )
    if decision.decided_by.startswith(AGENT_IDENTIFIER_PREFIX):
        raise AgentDecidedError(
            f"{decision.decided_by} is an agent, and only a human, or a policy acting "
            f"for one, may answer the approval gate"
        )
    if decided_by_claims_a_policy_and_names_none(decision.decided_by):
        raise APolicysDecisionNamedNoPolicyError(decision.decided_by)
    if decision.work_item_id != work_item.work_item_id:
        raise DecisionNotApplicableError(
            f"the decision is about {decision.work_item_id}, "
            f"but the work item is {work_item.work_item_id}"
        )
    if decision.artifact_id != presented_artifact_id:
        raise DecisionNotApplicableError(
            f"the decision is about {decision.artifact_id}, "
            f"but the gate presented {presented_artifact_id}"
        )
    if decision.artifact_version != current_artifact_version:
        raise DecisionNotApplicableError(
            f"the decision is about {decision.artifact_id} version "
            f"{decision.artifact_version}, but that artifact is now at version "
            f"{current_artifact_version}"
        )

    if not decision.approved:
        return None

    return Approval(
        work_item_id=decision.work_item_id,
        artifact_id=decision.artifact_id,
        artifact_version=decision.artifact_version,
        approved_by=decision.decided_by,
        approved_at=decision.decided_at,
        # **Copied verbatim for the same reason the identity is.** The gate validates what it
        # was given rather than editing it, so a reason that reached the gate is a reason the
        # record keeps — including one that says the artifact should not have been approved.
        reason=decision.reason,
    )
