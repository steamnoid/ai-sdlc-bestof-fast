"""The work item's first steps: an agent picks the work up, and then works on it."""

from __future__ import annotations

from aisdlc.domain.role import Role
from aisdlc.domain.stage import Stage
from aisdlc.graph.agent_state import AgentState
from aisdlc.graph.the_agents_a_run_reasons_with import (
    THE_ARCHITECTURE_ANALYST_AGENT,
    THE_DEVELOPER_IMPLEMENTATION_AGENT,
    THE_DEVELOPER_PLANNING_AGENT,
    THE_DISCOVER_AGENT,
    THE_PRODUCT_ANALYST_AGENT,
    THE_PULL_REQUEST_AGENT,
    THE_QA_ANALYST_AGENT,
    THE_SECURITY_ANALYST_AGENT,
)


def offer_the_work_item_to_discover(state: AgentState) -> dict:
    """Ask discovery to take the work item, by naming where the move should go.

    This node writes no work item. It says where the work item should be, and the
    transition node is what makes it so, which is the same division for every move in
    the graph.
    """
    return {
        "requested_stage": Stage.AWAITING_AGENT_PICKUP,
        "requested_agent": THE_DISCOVER_AGENT,
        "requested_role": Role.PO,
    }


def begin_working_on_the_work_item(state: AgentState) -> dict:
    """Say discovery has started, and hand the request to the transition node.

    Same division as every other move: this node says where the work item should be,
    and the transition node makes it so through the table.
    """
    return {
        "requested_stage": Stage.IN_PROGRESS_BY_AGENT,
        "requested_agent": THE_DISCOVER_AGENT,
        "requested_role": Role.PO,
    }


def hand_the_work_to_a_human(state: AgentState) -> dict:
    """Say the agent's work is finished and a person has to rule on it.

    Clearing the agent is the point. The table says AWAITING_HUMAN_APPROVAL requires
    no agent, so the move hands the work over rather than parking it with whoever was
    holding it.
    """
    return {
        "requested_stage": Stage.AWAITING_HUMAN_APPROVAL,
        "requested_agent": None,
        "requested_role": Role.PO,
    }


def offer_the_work_item_to_the_planner(state: AgentState) -> dict:
    """Ask the planning agent to take the work item, naming where the move should go.

    The same division as discovery's pickup, and the same reason: this node says where the
    work item should be and the transition node makes it so. The role changes to `DEV` here
    rather than at the handover, because the discipline accountable for a change is accountable
    for it from the moment somebody asks for it and not only when it is finished.
    """
    return {
        "requested_stage": Stage.AWAITING_AGENT_PICKUP,
        "requested_agent": THE_DEVELOPER_PLANNING_AGENT,
        "requested_role": Role.DEV,
    }


def begin_planning_the_change(state: AgentState) -> dict:
    """Say the planning agent has started, and hand the request to the transition node."""
    return {
        "requested_stage": Stage.IN_PROGRESS_BY_AGENT,
        "requested_agent": THE_DEVELOPER_PLANNING_AGENT,
        "requested_role": Role.DEV,
    }


def hand_the_plan_to_a_human(state: AgentState) -> dict:
    """Say the plan is finished and a person has to rule on it before anything is written.

    The same move as discovery's handover, and the reason is the same: §10 says the
    implementation agent operates *only after* the plan has been approved, so the run must
    come back to a gate rather than carry straight on into writing files.
    """
    return {
        "requested_stage": Stage.AWAITING_HUMAN_APPROVAL,
        "requested_agent": None,
        "requested_role": Role.DEV,
    }


def offer_the_work_item_to_the_implementer(state: AgentState) -> dict:
    """Ask the implementation agent to take the work item, naming where the move should go.

    `Role.DEV` again rather than a new role, because planning and implementing a change are the
    same discipline answering for it. A role per agent would be a handoff dressed as a
    discipline, which is the thing `Role` was corrected for.
    """
    return {
        "requested_stage": Stage.AWAITING_AGENT_PICKUP,
        "requested_agent": THE_DEVELOPER_IMPLEMENTATION_AGENT,
        "requested_role": Role.DEV,
    }


def begin_implementing_the_plan(state: AgentState) -> dict:
    """Say the implementation agent has started, and hand the request to the transition node."""
    return {
        "requested_stage": Stage.IN_PROGRESS_BY_AGENT,
        "requested_agent": THE_DEVELOPER_IMPLEMENTATION_AGENT,
        "requested_role": Role.DEV,
    }


def offer_the_work_item_to_the_pull_request_agent(state: AgentState) -> dict:
    """Ask the delivery to take the work item, naming where the move should go.

    `Role.DEV` again, and the reason is the implementer's: opening a pull request for a change
    is the same discipline finishing its own job, and a role per agent would be a handoff
    dressed as a discipline.
    """
    return {
        "requested_stage": Stage.AWAITING_AGENT_PICKUP,
        "requested_agent": THE_PULL_REQUEST_AGENT,
        "requested_role": Role.DEV,
    }


def begin_delivering_the_work_item(state: AgentState) -> dict:
    """Say the delivery has started, and hand the request to the transition node."""
    return {
        "requested_stage": Stage.IN_PROGRESS_BY_AGENT,
        "requested_agent": THE_PULL_REQUEST_AGENT,
        "requested_role": Role.DEV,
    }


def hand_the_delivery_to_a_human(state: AgentState) -> dict:
    """Say the change is verified and the delivery is described, and a person has to rule on it.

    The eighth gate, and the one §10 is about: the pull request is created "only after
    explicit human approval". The seven before it decide whether a change may be *offered*;
    this decides whether the offer may be *delivered*, and a run that verified a change and
    opened a pull request without asking would have produced a delivery nobody looked at.
    """
    return {
        "requested_stage": Stage.AWAITING_HUMAN_APPROVAL,
        "requested_agent": None,
        "requested_role": Role.DEV,
    }


def hand_the_verification_to_a_human(state: AgentState) -> dict:
    """Say the change is made and the suite has spoken, and a person has to rule on it.

    The gate before the delivery, and no longer the last one.
    """
    return {
        "requested_stage": Stage.AWAITING_HUMAN_APPROVAL,
        "requested_agent": None,
        "requested_role": Role.DEV,
    }


# The four analysis stages. Twelve functions, and the repetition is the domain written out
# rather than a pattern left implicit: the state machine needs a named node per move, the
# graph needs a distinct name per node, and the one thing that differs between four stages
# is which agent holds the work and which discipline answers for it. A helper taking the
# agent and the role as arguments would produce the same graph with four shorter functions
# and a reader who has to look up four names to learn what one line does.
#
# The roles are the four analysis disciplines of `Role` — `PO`, `QA`, `ARCH`, `SEC` — which
# is the same fact §10's pipeline is written in. Each stage's role is the discipline that
# answers for *that* analysis, set at the pickup rather than at the handover, because the
# discipline accountable for a piece of work is accountable for it from the moment somebody
# asks for it and not only when it is finished.
#
# `In progress` and `hand over` are the same two moves four times over, and each stage's
# docstring says the one thing about it that a reader could otherwise get wrong.


def offer_the_work_item_to_the_product_analyst(state: AgentState) -> dict:
    """Ask the product analyst to take the work item, naming where the move should go.

    `Role.PO` rather than a new role, because discovery is the same discipline answering for
    the same repository: a role per agent would be a handoff dressed as a discipline, which is
    the thing `Role` was corrected for.
    """
    return {
        "requested_stage": Stage.AWAITING_AGENT_PICKUP,
        "requested_agent": THE_PRODUCT_ANALYST_AGENT,
        "requested_role": Role.PO,
    }


def begin_the_product_analysis(state: AgentState) -> dict:
    """Say the product analyst has started, and hand the request to the transition node."""
    return {
        "requested_stage": Stage.IN_PROGRESS_BY_AGENT,
        "requested_agent": THE_PRODUCT_ANALYST_AGENT,
        "requested_role": Role.PO,
    }


def hand_the_requirements_to_a_human(state: AgentState) -> dict:
    """Say the proposal is finished and a person has to rule on it before anything is planned.

    Clearing the agent is the point, and it is the same point as discovery's handover: the
    table says `AWAITING_HUMAN_APPROVAL` requires no agent, so the move hands the work over
    rather than parking it with whoever was holding it.
    """
    return {
        "requested_stage": Stage.AWAITING_HUMAN_APPROVAL,
        "requested_agent": None,
        "requested_role": Role.PO,
    }


def offer_the_work_item_to_the_qa_analyst(state: AgentState) -> dict:
    """Ask the QA analyst to take the work item, naming where the move should go.

    `Role.QA` and not `Role.PO`, because the QA analyst is handed the *approved requirements*
    rather than the repository: what it is accountable for is whether the work is specified
    well enough to test, which is a different discipline's question from what should be built.
    """
    return {
        "requested_stage": Stage.AWAITING_AGENT_PICKUP,
        "requested_agent": THE_QA_ANALYST_AGENT,
        "requested_role": Role.QA,
    }


def begin_planning_the_tests(state: AgentState) -> dict:
    """Say the QA analyst has started, and hand the request to the transition node."""
    return {
        "requested_stage": Stage.IN_PROGRESS_BY_AGENT,
        "requested_agent": THE_QA_ANALYST_AGENT,
        "requested_role": Role.QA,
    }


def hand_the_qa_plan_to_a_human(state: AgentState) -> dict:
    """Say the QA plan is finished and a person has to rule on it before it is built on.

    A gate after this one matters more than after the others: the QA plan is the artifact
    that says what testing the work will consist of, so a person approving it is approving the
    shape of the verification before anybody has written a line of the change.
    """
    return {
        "requested_stage": Stage.AWAITING_HUMAN_APPROVAL,
        "requested_agent": None,
        "requested_role": Role.QA,
    }


def offer_the_work_item_to_the_architecture_analyst(state: AgentState) -> dict:
    """Ask the architecture analyst to take the work item, naming where the move should go."""
    return {
        "requested_stage": Stage.AWAITING_AGENT_PICKUP,
        "requested_agent": THE_ARCHITECTURE_ANALYST_AGENT,
        "requested_role": Role.ARCH,
    }


def begin_describing_the_architecture(state: AgentState) -> dict:
    """Say the architecture analyst has started, and hand the request to the transition node."""
    return {
        "requested_stage": Stage.IN_PROGRESS_BY_AGENT,
        "requested_agent": THE_ARCHITECTURE_ANALYST_AGENT,
        "requested_role": Role.ARCH,
    }


def hand_the_architecture_report_to_a_human(state: AgentState) -> dict:
    """Say the description is finished and a person has to rule on it."""
    return {
        "requested_stage": Stage.AWAITING_HUMAN_APPROVAL,
        "requested_agent": None,
        "requested_role": Role.ARCH,
    }


def offer_the_work_item_to_the_security_analyst(state: AgentState) -> dict:
    """Ask the security analyst to take the work item, naming where the move should go."""
    return {
        "requested_stage": Stage.AWAITING_AGENT_PICKUP,
        "requested_agent": THE_SECURITY_ANALYST_AGENT,
        "requested_role": Role.SEC,
    }


def begin_inspecting_for_security_risk(state: AgentState) -> dict:
    """Say the security analyst has started, and hand the request to the transition node."""
    return {
        "requested_stage": Stage.IN_PROGRESS_BY_AGENT,
        "requested_agent": THE_SECURITY_ANALYST_AGENT,
        "requested_role": Role.SEC,
    }


def hand_the_security_report_to_a_human(state: AgentState) -> dict:
    """Say the inspection is finished and a person has to rule on it before anything is built.

    The last of the four analysis gates, and the one where a person's approval is least
    reversible: everything after this writes files. §10 calls this analysis advisory and not a
    replacement for a scanner, so the approval is of a reading of the code and not of a
    guarantee — and the record saying a person approved a security report is true either way.
    """
    return {
        "requested_stage": Stage.AWAITING_HUMAN_APPROVAL,
        "requested_agent": None,
        "requested_role": Role.SEC,
    }


def mark_the_work_item_delivered(state: AgentState) -> dict:
    """Ask for the move to `DONE`, the one edge the delivery gate's approval allows.

    **A request and not the move, because `transition_the_work_item` is the only node that may
    write a work item.** This node says which move and the transition node checks it against the
    table and the biconditional, so "which node may change a stage" stays one answer rather than
    one per stage.

    **The eighth gate is what marks a run delivered**, and that is a reading of the table rather
    than an addition to it. There is exactly one edge into `DONE` — `AWAITING_HUMAN_APPROVAL ->
    DONE` — and the work item is at `AWAITING_HUMAN_APPROVAL` after the delivery gate, because
    that gate is the last one a person rules on. The move the table has always allowed is the one
    the run was not making.

    **No agent, and that is the biconditional rather than a choice:** `DONE` is a stage nobody
    holds, so a work item delivered and still in an agent's hands would fail validation.
    """
    return {
        "requested_stage": Stage.DONE,
        "requested_agent": None,
        "requested_role": state["work_item"].role,
    }
