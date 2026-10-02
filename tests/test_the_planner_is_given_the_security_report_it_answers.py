"""The planning agent answers three gates' work, so it is given all three.

**A real pair test found this and it is not a defect in the test.** `inspect_for_security` and
`plan` are neighbours in the pipeline, the security analyst's findings are approved by a gate, and
`PlanTheChange` took `(Requirements, ClonedRepository, Repository, str)` — so a plan that ignored
every finding three gates had agreed on was a plan nobody had told the planner not to write.

**The report was already in the state.** `security_node` writes `security_report` and the channel
has been in `AgentState` all along, so this was never a missing value; it was a value nobody
threaded to the one agent that has to act on it. That is a different kind of fault from a gap, and
it is the kind that reads as a design rather than as an omission — which is why it survived.

**Checked in the default tier, without a model**, because this is a fact about a signature and a
node's reading of the state, and neither of those needs a model to establish.
"""

from __future__ import annotations

import inspect

from aisdlc.agents.security_report import SecurityReport
from aisdlc.graph.plan_node import plan_the_change_in_this_run
from tests.the_arguments_the_planner_is_handed import the_types_the_planner_is_handed


def test_the_seam_takes_the_security_report() -> None:
    """Read from the alias, because a parameter name is a choice and a type is the contract."""
    what_the_planner_is_handed = the_types_the_planner_is_handed()

    assert SecurityReport in what_the_planner_is_handed, (
        f"the planner is handed {list(what_the_planner_is_handed)} and a SecurityReport is not "
        "among them, so a plan that ignores the security findings three gates have approved is a "
        "plan nobody was told not to write"
    )


def test_the_node_passes_the_report_out_of_the_state_rather_than_asking_for_it() -> None:
    """The node reads it from the state, so the value has one home.

    **And it refuses when there is none**, rather than passing `None` and letting the planner
    quietly plan around the absence. A run that has no security report has not passed that stage,
    and a planner handed nothing cannot be told the findings were considered.
    """
    the_source = inspect.getsource(plan_the_change_in_this_run)

    assert 'state["security_report"]' in the_source, (
        "the planning node does not read security_report out of the state, so the report the "
        "security analyst produced stops at the gate that approved it"
    )
    assert "SecurityReportHaveNotBeenApprovedYetError" in the_source, (
        "the planning node does not refuse a run with no security report. It should: a run that "
        "has not passed the security stage cannot be planned, and passing None is how a plan "
        "quietly comes to exist without one"
    )
