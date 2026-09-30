"""A human decision that a specific artifact, at a specific version, may be relied upon."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Approval(BaseModel):
    """A human's decision to rely on one exact version of one artifact.

    The specification names the five fields, and the version is not optional
    decoration: an approval that does not say which version it covers cannot be
    invalidated when the artifact changes, which is the whole point of having one.

    The freeze removes the easy door, and it is not the whole guarantee: pydantic's
    `model_copy` bypasses both `frozen` and the validators, so a copy that was made
    without them is not a defended record. What defends a record that arrived from
    somewhere is re-validating it from its fields on the way in, which is the gate's
    job and not this model's.
    """

    model_config = ConfigDict(frozen=True)

    work_item_id: str
    artifact_id: str
    artifact_version: int = Field(ge=1)
    approved_by: str
    approved_at: datetime
    reason: str

    @field_validator("work_item_id", "artifact_id", "approved_by")
    @classmethod
    def _reject_a_name_that_identifies_nothing(cls, name: str) -> str:
        """Refuse a blank work item, a blank artifact, or a decider who is nobody.

        An approval is a record of a human's, or a policy's, decision about a
        specific piece of work, so all three halves have to name something. A blank
        work item id is refused here for the same reason the work item refuses a
        blank one of its own: an approval that names nothing can be persisted and
        later pointed at work nobody ruled on.

        `approved_by` is the field the audit trail rests on, and it is the field the
        gate copies out of the decision. `ApprovalDecision` refuses a blank
        `decided_by` already; holding this one to the same rule means the rule
        survives the trip instead of evaporating on the way through.
        """
        if not name.strip():
            raise ValueError("an approval must name what it covers, and who approved")
        return name

    @field_validator("approved_at")
    @classmethod
    def _reject_a_decision_with_no_timezone(cls, approved_at: datetime) -> datetime:
        """Refuse a decision timestamped without a timezone.

        Approvals are ordered against each other, and comparing a naive datetime
        against an aware one raises instead of ordering. Accepting one would mean a
        decision taken on a machine in one timezone could not be placed in order
        against a decision taken in another, which is exactly what a gate needs to
        do when it decides which decision is the later one.
        """
        if approved_at.tzinfo is None:
            raise ValueError("a decision needs a timezone to be ordered against other decisions")
        return approved_at.astimezone(UTC)

    def applies_to(self, work_item_id: str, artifact_id: str, artifact_version: int) -> bool:
        """Report whether this approval still covers what a work item now holds.

        This is the specification's invalidation rule as a question the approval
        can answer: the decision survives exactly while the work item it names, the
        artifact it names, and the version it names all still match. A caller
        holding a work item at an artifact's current version asks this, and a
        `False` means the decision is spent and a human must rule again.

        The work item is part of the question because artifact versions are counted
        per work item. Two work items may both be at their first version of the same
        artifact, and a decision about one is not a decision about the other.
        """
        return (
            self.work_item_id == work_item_id
            and self.artifact_id == artifact_id
            and self.artifact_version == artifact_version
        )
