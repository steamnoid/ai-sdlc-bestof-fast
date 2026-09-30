"""One tracked unit of SDLC work against a repository."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from aisdlc.domain.commissioned_request import CommissionedRequest
from aisdlc.domain.repository import Repository
from aisdlc.domain.role import Role
from aisdlc.domain.stage import Stage
from aisdlc.domain.the_work_each_agent_has_done import TheWorkEachAgentHasDone

# Agent identifiers are the `aisdlc-` namespace the glossary fixes. It lives here so
# that `aisdlc.approval` imports one definition rather than repeating the literal: a
# duplicated domain fact is a fact that will eventually disagree with itself.
AGENT_IDENTIFIER_PREFIX = "aisdlc-"


class WorkItem(BaseModel):
    """A unit of work, its lifecycle position, and whoever currently owns it.

    The work item is a first-class domain object. Its stage is never changed by
    assigning to it: the state machine's `transition` is the only door, so a
    model can propose a change and cannot perform one. That is why the model is
    frozen, and why `transition` hands back a new work item.

    The freeze removes the easy door rather than being the guarantee. Whatever
    route a work item takes to a new stage, `validate_state` decides whether the
    stage and the agent still agree, so a copy that skipped the freeze is caught
    there.
    """

    # **Frozen and forbidding, and the second is the one nobody writes.** Frozen says this record
    # cannot be edited after the fact; `extra="forbid"` says a caller who named a field this type
    # does not have is told. Without it `WorkItem(..., stage_tickecik="HACKED")` built a work item
    # with the keyword gone and `stage` at its default -- a *valid* work item, because the
    # biconditional holds over the defaults, and one `transition()` would then move along a table
    # that has nothing to do with what the caller asked for.
    model_config = ConfigDict(frozen=True, extra="forbid")

    work_item_id: str
    repository: Repository
    stage: Stage = Stage.IDLE
    role: Role
    commissioned_by: str
    agent: str | None = None
    requested: CommissionedRequest | None = None
    work_done: TheWorkEachAgentHasDone = TheWorkEachAgentHasDone()

    @field_validator("commissioned_by")
    @classmethod
    def _reject_a_commissioner_that_is_nobody(cls, commissioned_by: str) -> str:
        """Refuse a work item that does not say who asked for it.

        A work item exists because somebody wanted something worked on, so the party
        that commissioned it is the reason the work item is here at all. A blank
        commissioner would leave work with no origin, and an origin nobody can name
        cannot be traced back to the request that started it.

        An `aisdlc-` identifier here means a machine was asked, which is the same
        namespace rule the approval gate uses to refuse an agent from answering it.
        """
        if not commissioned_by.strip():
            raise ValueError("a work item must say who commissioned it")
        return commissioned_by

    @field_validator("work_item_id")
    @classmethod
    def _reject_a_blank_work_item_id(cls, work_item_id: str) -> str:
        """Refuse a work item that names nothing.

        A work item is a *tracked* unit of work, and tracking is by name. An
        unnamed work item cannot be approved, persisted, or pointed at by an
        approval, so an empty name is refused where it enters.
        """
        if not work_item_id.strip():
            raise ValueError("a work item must be named")
        return work_item_id

    @field_validator("agent")
    @classmethod
    def _reject_an_agent_that_is_not_an_identity(cls, agent: str | None) -> str | None:
        """Refuse a string that only means "absent", because absence is `None`.

        The state machine decides whether an agent is present by testing
        `agent is None`. So the literal `"none"`, an empty string and a blank
        string would all read as a *present* agent, and a work item resting in a
        stage that requires no agent would appear to break the biconditional for
        the wrong reason. Worse, a work item in IN_PROGRESS_BY_AGENT holding a
        blank agent would pass the biconditional while nobody is working on it.
        """
        if agent is None:
            return None
        if not agent.strip():
            raise ValueError("absence is None, not a blank string")
        if agent == "none":
            raise ValueError("absence is None, not the string 'none'")
        return agent


def a_work_item_commissioned_for_an_agent(
    work_item_id: str,
    repository: Repository,
    accountable_role: Role,
    commissioned_by: str,
    requested: CommissionedRequest | None = None,
) -> WorkItem:
    """The only way a work item enters the lifecycle: somebody asked for it.

    The work item is born at READY with no agent holding it, and the framework picks
    it up along the table's own `READY -> AWAITING_AGENT_PICKUP` edge, which is a move
    the specification already describes. No new stage and no new transition were added
    for this.

    `accountable_role` is the discipline that answers for the work, and it is an
    argument rather than a default because the domain has no business inferring it
    from where the work item happens to be: the first agent to pick this up is
    discovery, and which discipline that is, is the pipeline's business, not the
    domain's. So whoever commissions the work says who answers for it, and the
    pipeline may disagree later through `transition`, which is the only door.

    `commissioned_by` is the party that asked, and it is an argument because that party
    is a person in the ordinary case: they queue the tickecik, and the machine runs it.
    Who does the work is a different question, and it is already answered by the table,
    whose own `READY -> AWAITING_AGENT_PICKUP` edge is the machine picking the work up.

    An agent identifier here means a policy asked for this on somebody's behalf, which
    is the same namespace the approval gate uses to tell an agent from a person. An
    agent may ask for work and may not rule on the result, and the two halves of that
    are enforced in two places rather than assumed to agree.

    This is a birth, not an operation. It adds no third verb to the state machine,
    which names exactly two and is right to.
    """
    return WorkItem(
        work_item_id=work_item_id,
        repository=repository,
        stage=Stage.READY,
        role=accountable_role,
        commissioned_by=commissioned_by,
        requested=requested,
    )
