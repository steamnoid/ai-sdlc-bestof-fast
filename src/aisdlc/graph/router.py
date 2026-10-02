"""Where a gate's answer sends the run next.

**This is the routing decision the lifecycle's own docstring said nobody had made.** It is
small because the transition table left nothing to choose: an approved artifact is followed by
the next piece of work the pipeline does, and `AWAITING_HUMAN_APPROVAL -> AWAITING_AGENT_PICKUP`
is the table's own edge. So no new stage and no new transition were added for any stage after
the first, which is the same argument the `READY` entry made for a work item's birth.

**The pipeline is declared here, in one place, in the order it happens.** A run reaches
`record_what_was_decided` once per gate, so one router answers for all of them and the
artifact is the only thing in the state that says which gate this was.
`the_lifecycle` hands this mapping's values to its conditional edge, so a route cannot be
returned without a destination to return *to* — the two cannot drift apart, and a later phase
that adds a stage adds a row here and inherits that guarantee.

**A refusal ends the run, and a refusal is not a fault.** The router reads the *answer* rather
than the record it left, because an answer says "no" and a record's absence says the same thing
less directly. Carrying on past a refusal would mean a work item a person rejected went on to be
planned, implemented and put in front of somebody as a pull request — with a record saying a
human had ruled on it.

The answer is read from the end of `decisions`, which is the answer to the gate that just ran:
a run is walked through several and the list is in the order they happened.

**A terminal artifact is not an error, and that distinction is why the error is named as it
is.** `VerificationReport` is routed to the end of the run because the `aisdlc-pr` agent is a
later phase and a stage invented to have somewhere to send it would be a future concept
implemented because the present graph wanted one. An artifact with no stage after it is
therefore exactly what a terminal artifact looks like, and an error named after a *missing
stage* would report a deliberate ending as a fault. The error is for an artifact nobody wrote
a rule for at all.
"""

from __future__ import annotations

from aisdlc.graph.agent_state import AgentState
from aisdlc.graph.analyze_node import THE_ARTIFACT_THE_PRODUCT_ANALYST_PRODUCES
from aisdlc.graph.apply_node import THE_ARTIFACT_APPLYING_PRODUCES
from aisdlc.graph.architecture_node import THE_ARTIFACT_THE_ARCHITECTURE_ANALYST_PRODUCES
from aisdlc.graph.deliver_node import THE_ARTIFACT_DELIVERY_PRODUCES
from aisdlc.graph.discover_node import THE_ARTIFACT_DISCOVERY_PRODUCES
from aisdlc.graph.plan_node import THE_ARTIFACT_PLANNING_PRODUCES
from aisdlc.graph.qa_node import THE_ARTIFACT_THE_QA_ANALYST_PRODUCES
from aisdlc.graph.security_node import THE_ARTIFACT_THE_SECURITY_ANALYST_PRODUCES

THE_RUN_IS_OVER = "write_how_this_run_ended"
THE_NEXT_ARTIFACT_IS_THE_PROPOSAL = "offer_the_work_item_to_the_product_analyst"
THE_NEXT_ARTIFACT_IS_THE_QA_PLAN = "offer_the_work_item_to_the_qa_analyst"
THE_NEXT_ARTIFACT_IS_THE_ARCHITECTURE = "offer_the_work_item_to_the_architecture_analyst"
THE_NEXT_ARTIFACT_IS_THE_SECURITY_REPORT = "offer_the_work_item_to_the_security_analyst"
THE_NEXT_ARTIFACT_IS_A_PLAN = "offer_the_work_item_to_the_planner"
THE_NEXT_ARTIFACT_IS_THE_CHANGE = "offer_the_work_item_to_the_implementer"
THE_NEXT_ARTIFACT_IS_THE_DELIVERY = "offer_the_work_item_to_the_pull_request_agent"
THE_APPROVED_DELIVERY_IS_PUSHED_AND_OPENED = "deliver_this_run"


class NoRouteIsDeclaredForThisArtifactError(Exception):
    """The rule is in `where_a_gate_outcome_leads`, and this may say it broke.

    Named after a missing *declaration*, not after a missing stage, and the difference is the
    whole point. A terminal artifact has no stage after it either, and that is not a fault:
    `VerificationReport` is routed to the end of the run on purpose. This error is for an
    artifact nobody wrote a rule for at all, which is a gap in the pipeline rather than a
    decision in it.
    """


# What each approved artifact leads to. This is the pipeline, and the router does nothing but
# look a run's artifact up in it — which is why there is no fall-through and why an artifact
# that is not here cannot be routed at all.
WHERE_AN_APPROVED_ARTIFACT_LEADS = {
    THE_ARTIFACT_DISCOVERY_PRODUCES: THE_NEXT_ARTIFACT_IS_THE_PROPOSAL,
    THE_ARTIFACT_THE_PRODUCT_ANALYST_PRODUCES: THE_NEXT_ARTIFACT_IS_THE_QA_PLAN,
    THE_ARTIFACT_THE_QA_ANALYST_PRODUCES: THE_NEXT_ARTIFACT_IS_THE_ARCHITECTURE,
    THE_ARTIFACT_THE_ARCHITECTURE_ANALYST_PRODUCES: THE_NEXT_ARTIFACT_IS_THE_SECURITY_REPORT,
    THE_ARTIFACT_THE_SECURITY_ANALYST_PRODUCES: THE_NEXT_ARTIFACT_IS_A_PLAN,
    THE_ARTIFACT_PLANNING_PRODUCES: THE_NEXT_ARTIFACT_IS_THE_CHANGE,
    THE_ARTIFACT_APPLYING_PRODUCES: THE_NEXT_ARTIFACT_IS_THE_DELIVERY,
    THE_ARTIFACT_DELIVERY_PRODUCES: THE_APPROVED_DELIVERY_IS_PUSHED_AND_OPENED,
}


def where_a_gate_outcome_leads(state: AgentState) -> str:
    """The next node, from two facts: whether a person said yes, and what they said it about.

    A run reaches this only from `record_what_was_decided`, which raises when nobody
    answered and which has just appended the answer being read, so the list has one and it is
    the right one. That is the same division of labour as before: a missing answer is the
    recording node's refusal to raise, not this function's to invent.

    **And there is no route out of here that reads the `repair` channel, which is a removal rather
    than a tidying.** A supervisor's verdict once sent an approved plan straight to the node that
    pushes and opens a pull request, on the reading that "the implementer must not repeat its
    work" meant there was nothing to implement. A real run took that route and died:

        TheDeliveryHasNothingToDeliverError: PullRequestRequest is opened by the stage that
        wrote it, and this run has none.

    The crash is the smaller half. **`WhatToRepeat` carries a verdict for every agent in the run**,
    so the implementer carries one whether or not it ever ran, and a verdict about **who is at
    fault** is not a statement that **there is nothing left to do**. Reading it as one skipped a
    whole implementation and would have delivered the previous plan's change under the new plan's
    approval — a delivery of something nobody implemented against what a person read.

    **The removal is total because the branch had no true case at all.** `repair` is written in
    exactly one place, by the supervisor, which is only reached from a refusal. After a refusal
    either the implementer must repeat — the table's own row, which is not this branch — or the
    planner does, the plan is a *different* plan, and nothing has implemented it. So the branch
    fired in the one situation where it was wrong and in no situation where it was right, and it
    had **no test and no claim in the README** behind it: an untested shortcut is not a rule.
    """
    if not state["decisions"][-1].approved:
        return THE_RUN_IS_OVER

    approved_artifact = state["presented_artifact_id"]

    if approved_artifact not in WHERE_AN_APPROVED_ARTIFACT_LEADS:
        raise NoRouteIsDeclaredForThisArtifactError(
            f"{approved_artifact!r} was approved, and no route is declared for it. The "
            f"declared artifacts are {sorted(WHERE_AN_APPROVED_ARTIFACT_LEADS)}, and an "
            "artifact outside them is a gap in the pipeline rather than a decision in it. It "
            "is not read as a request to implement something."
        )

    return WHERE_AN_APPROVED_ARTIFACT_LEADS[approved_artifact]
