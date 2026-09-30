"""The answer a human gives when the approval gate asks it."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApprovalDecision(BaseModel):
    """One person's, or one policy's, answer to the approval gate.

    This is what comes back when the gate asks. An `Approval` in the domain is the
    record a decision leaves behind once it is affirmative, so the difference is
    the difference between an answer and the record of that answer: a refusal is a
    decision too, and it produces no record.

    The freeze removes the easy door rather than being the guarantee. `model_copy`
    bypasses `frozen` and the validators alike, so nothing here defends a decision
    that arrived without them. That is deliberate and it is why the gate validates
    what it is given rather than trusting the object in its hand.
    """

    model_config = ConfigDict(frozen=True)

    work_item_id: str
    artifact_id: str
    artifact_version: int = Field(ge=1)
    approved: bool
    decided_by: str
    decided_at: datetime
    reason: str

    @field_validator("reason")
    @classmethod
    def _reject_a_decision_with_no_reason(cls, reason: str) -> str:
        """Refuse a decision that says what it decided and not why.

        **Required rather than optional, because an optional reason is two standards of evidence
        in one table.** A person might skip it and a model would never, and a record that is
        sometimes justified and sometimes bare is a record nobody knows how to read. The cost is
        one line of text at each gate; what it buys is a directory in which every approval can be
        disagreed with.
        """
        if not reason.strip():
            raise ValueError(
                "a decision must say why, or it is a verdict with nothing anybody can question"
            )
        return reason

    @field_validator("work_item_id", "artifact_id", "decided_by")
    @classmethod
    def _reject_a_name_that_identifies_nothing(cls, name: str) -> str:
        """Refuse a decision that does not say what, or who, it is about.

        Every one of these three is the gate's evidence that a decision happened
        at all. A decision that names no work item, no artifact, or nobody cannot
        be told apart from a broken gate, and a gate that cannot tell those apart
        is a gate that will eventually treat silence as consent.
        """
        if not name.strip():
            raise ValueError("a decision must name what it is about, and who decided")
        return name

    @field_validator("decided_at")
    @classmethod
    def _reject_a_decision_with_no_timezone(cls, decided_at: datetime) -> datetime:
        """Refuse a decision timestamped without a timezone, and normalise to UTC.

        A decision is ordered against other decisions on the same artifact, and
        comparing a naive datetime against an aware one raises instead of ordering.
        The rule is the same one the `Approval` record holds, and for the same
        reason: the gate has to be able to say which of two decisions came later.
        """
        if decided_at.tzinfo is None:
            raise ValueError("a decision needs a timezone to be ordered against other decisions")
        return decided_at.astimezone(UTC)

    def when_it_was_decided(self) -> datetime:
        """The moment, in UTC, for a record that has to be sortable.

        The validator above has already normalised it, so this is a name rather than a
        conversion — which is the point. A caller writing `decided_at.astimezone(UTC)`
        at four call sites is four places a record could be written in local time.
        """
        return self.decided_at.astimezone(UTC)
