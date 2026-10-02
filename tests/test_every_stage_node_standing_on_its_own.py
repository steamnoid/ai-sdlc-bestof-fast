"""Each stage's node, on its own, with everything before it and after it replaced.

**Why these are here and why they are separate from the whole run.** Until now the pipeline was
proven by one test that starts a run from the board and answers eight gates. Every agent seam in
that test is a hardcoded closure, and a graph wired in the wrong order, a stage handed the wrong
document, or a note that never reached the card all read the same way through it: the run still
got to `DONE`. So nine nodes — six of the eight stages, the clone, the single writer of the work
item, and the router — had no test of their own, and a defect in any of them was invisible until
a real run reached it twenty minutes in.

**Everything on both sides is replaced, and that is the point rather than a limitation.** Each test
below builds an `AgentState` from the production `a_run_beginning_at` — so every channel is
present and none is invented here — hands the node one collaborator that is a plain closure, and
asserts what the node *reads* and what it *writes*. The stages before it do not run, the gate
after it does not run, and no model, no network, no credential and no container is touched. That
is what makes a failure here readable: the message can say which node and which channel, rather
than that a run went somewhere nobody expected.

**A writable projects root, because six of these nine nodes write.** A note left on a card is a
file beside the run's clone and a moved work item is a second one, so a node that writes cannot be
given a root that does not exist — and a test that passes a root it never created fails with
`FileNotFoundError` from inside a node, which is a fact about the test and not about the node.
The root is therefore the one every test below uses, and it is `tmp_path`.

**The list of nodes is the audit's list, not a selection.** `transition_the_work_item` and
`where_a_gate_outcome_leads` are here beside the six stages on purpose — the transition node is
the only writer of a work item and the router is the only thing that turns an answer into a
destination, and both were reachable only through a whole run.

**And these are characterisation tests, not RED-then-GREEN cycles.** Every one of the nine nodes
was already written under this repository's regime and already correct; what was missing was the
test. Not one assertion here was satisfied by changing a line of `src/`, and saying otherwise
would be the dishonest half of TDD reported as the honest half. What they are worth is the next
change.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

import pytest

from aisdlc.agents.architecture_report import ArchitectureReport
from aisdlc.agents.architecture_report_answer import ArchitectureReportAnswer
from aisdlc.agents.discovery_answer import DiscoveryAnswer
from aisdlc.agents.discovery_report import DiscoveryReport, EvidenceFile
from aisdlc.agents.implementation_plan import ImplementationPlan
from aisdlc.agents.plan_the_change import PlannedTestDirectoryNotCollectedError, plan_the_change
from aisdlc.agents.qa_plan import QaPlan
from aisdlc.agents.qa_plan_answer import QaPlanAnswer
from aisdlc.agents.requirements import Requirements
from aisdlc.agents.requirements_answer import RequirementsAnswer
from aisdlc.agents.security_report import SecurityReport
from aisdlc.agents.what_an_agent_judged import WhatAnAgentJudged
from aisdlc.agents.what_the_planner_concluded import ImplementationPlanAnswer
from aisdlc.application.a_run_being_assembled import a_run_beginning_at
from aisdlc.approval.approval_decision import ApprovalDecision
from aisdlc.domain.commissioned_request import a_request_about
from aisdlc.domain.repository import Repository
from aisdlc.domain.role import Role
from aisdlc.domain.stage import Stage
from aisdlc.domain.state_machine import transition
from aisdlc.domain.work_item import WorkItem, a_work_item_commissioned_for_an_agent
from aisdlc.graph.agent_state import WHAT_STOPPED_THIS_RUN, AgentState
from aisdlc.graph.analyze_node import (
    THE_ARTIFACT_THE_PRODUCT_ANALYST_PRODUCES,
    analyze_the_repository_in_this_run,
)
from aisdlc.graph.apply_node import THE_ARTIFACT_APPLYING_PRODUCES
from aisdlc.graph.architecture_node import (
    THE_ARTIFACT_THE_ARCHITECTURE_ANALYST_PRODUCES,
    analyze_the_architecture_in_this_run,
)
from aisdlc.graph.clone_node import (
    TheRepositoryHasNotBeenClonedYetError,
    clone_the_repository_for_this_run,
)
from aisdlc.graph.discover_node import (
    THE_ARTIFACT_DISCOVERY_PRODUCES,
    discover_the_repository_in_this_run,
)
from aisdlc.graph.pickup_node import (
    THE_DEVELOPER_PLANNING_AGENT,
    begin_working_on_the_work_item,
    offer_the_work_item_to_discover,
)
from aisdlc.graph.plan_node import (
    THE_ARTIFACT_PLANNING_PRODUCES,
    PlanTheChange,
    ThePlanHasNoApprovedRequirementsError,
    plan_the_change_in_this_run,
)
from aisdlc.graph.qa_node import (
    THE_ARTIFACT_THE_QA_ANALYST_PRODUCES,
    RequirementsHaveNotBeenApprovedYetError,
    analyze_the_requirements_in_this_run,
)
from aisdlc.graph.release_the_work_item_node import (
    WHERE_AN_AGENT_LETS_GO_OF_THE_WORK_ITEM,
)
from aisdlc.graph.router import (
    THE_NEXT_ARTIFACT_IS_A_PLAN,
    THE_NEXT_ARTIFACT_IS_THE_ARCHITECTURE,
    THE_NEXT_ARTIFACT_IS_THE_CHANGE,
    THE_NEXT_ARTIFACT_IS_THE_DELIVERY,
    THE_RUN_IS_OVER,
    WHERE_AN_APPROVED_ARTIFACT_LEADS,
    NoRouteIsDeclaredForThisArtifactError,
    where_a_gate_outcome_leads,
)
from aisdlc.graph.security_node import (
    THE_ARTIFACT_THE_SECURITY_ANALYST_PRODUCES,
    inspect_for_security_risk_in_this_run,
)
from aisdlc.graph.the_agents_that_leave_a_note import THE_AGENTS_THAT_LEAVE_A_NOTE
from aisdlc.graph.transition_node import transition_the_work_item
from aisdlc.store.the_record_of_a_run import the_notes_on_the_card
from aisdlc.store.the_register_of_work_items import the_work_item_a_commission_registers
from aisdlc.store.where_the_register_lives import holding_the_register, the_register_lives_at
from aisdlc.tools.github_client import Addresses
from aisdlc.tools.github_clone_repository import (
    ClonedRepository,
    RepositoryNotFoundError,
    a_repository_to_clone,
)
from aisdlc.tools.the_project_directory import the_clone_directory_of

A_REPOSITORY = Repository(owner="an", name="owner")
A_MOMENT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

A_JUDGEMENT = WhatAnAgentJudged(
    what_it_found="one thing",
    what_it_could_not_settle="one other thing",
    what_it_expects_next="the next agent reads this",
)

A_CLONE = ClonedRepository(path=Path("/a/clone"), ref="main", commit="0" * 40)

THE_REQUIREMENTS_A_PERSON_APPROVED = Requirements(
    requirements=["an unauthenticated health endpoint"],
    acceptance_criteria=["the suite's file count goes up by one"],
)


@pytest.fixture
def a_projects_root(tmp_path: Path, monkeypatch) -> Path:
    """A writable projects root and an open register, which is what a node that writes needs.

    **Two destinations rather than one, because these nodes write to two.** A node that leaves a
    note writes a JSON file beside the run's own directory, and the transition node also writes
    the `WorkItem.json` a resuming run reads from — and the engine's own finding is that those two
    drifting apart is what made a finished run's register claim nothing had happened.

    **The register is opened rather than passed in**, because `where_the_register_lives` holds one
    connection for the process and everything in the graph reaches for it by name. A second
    connection handed to these tests would be a second writer to the same file, which is the
    failure the single lock exists to prevent.
    """
    monkeypatch.setenv("AISDLC_PROJECTS_DIR", str(tmp_path / "projects"))
    the_register_lives_at(tmp_path / "the-register.sqlite3")
    return tmp_path / "projects"


def _a_commissioned_work_item() -> WorkItem:
    return a_work_item_commissioned_for_an_agent(
        work_item_id="a-stage-standing-alone",
        repository=A_REPOSITORY,
        accountable_role=Role.PO,
        commissioned_by="a person reading a test",
        requested=a_request_about("add a health endpoint", ""),
    )


def _a_state_at_the_start(a_projects_root: Path) -> AgentState:
    """The production starting state, so a node under test sees every channel a run would carry.

    **Commissioning is not done here**, because a node that only reads must not need a register:
    most of the nodes below never write to one, and a fixture every one of them depended on would
    be a fixture making the read-only tests look like write tests.
    """
    return a_run_beginning_at(_a_commissioned_work_item(), a_projects_root)


def _a_registered_state(a_projects_root: Path) -> AgentState:
    """The same state, with this work item commissioned — what a node that records needs."""
    the_work_item = _a_commissioned_work_item()
    with holding_the_register() as a_register:
        the_work_item_a_commission_registers(a_register, the_work_item)
    return a_run_beginning_at(the_work_item, a_projects_root)


def _a_registered_state_that_has_cloned(a_projects_root: Path) -> AgentState:
    """A commissioned run that has cloned, which is what every node that records is handed."""
    return {**_a_registered_state(a_projects_root), "clone": A_CLONE}


def _the_notes_on_the_card(state: AgentState) -> list[str]:
    """What the agents of this run have said, read back out of the register."""
    with holding_the_register() as a_register:
        return [
            a_note.what_was_said
            for a_note in the_notes_on_the_card(a_register, state["work_item"].work_item_id)
        ]


def _a_state_that_has_cloned(a_projects_root: Path) -> AgentState:
    return {**_a_state_at_the_start(a_projects_root), "clone": A_CLONE}


def _a_state_somebody_approved_the_requirements(a_projects_root: Path) -> AgentState:
    """A run carrying approved requirements and a clone, which is what the planner is handed."""
    return {
        **_a_state_that_has_cloned(a_projects_root),
        "requirements": THE_REQUIREMENTS_A_PERSON_APPROVED,
    }


def _a_state_a_person_ruled_on_without_asking_about_code(
    a_projects_root: Path,
) -> AgentState:
    """Approved requirements and **no clone**, which is the state the QA analyst is reached in.

    **No clone and not a missing one.** Every other analysis node refuses a run with `clone` set
    to `None`, and this one is reached with exactly that, so a test which handed it a clone would
    be testing a state the graph never produces.
    """
    return {
        **_a_state_at_the_start(a_projects_root),
        "requirements": THE_REQUIREMENTS_A_PERSON_APPROVED,
    }


def _a_plan_from_a_planner_that_answers() -> ImplementationPlanAnswer:
    return ImplementationPlanAnswer(
        plan=ImplementationPlan(files_to_change=["health.py"]), judged=A_JUDGEMENT
    )


def test_discovery_refuses_a_run_with_no_clone_rather_than_reading_nothing(
    a_projects_root: Path,
) -> None:
    """A graph wired with discovery before the clone has to say so, not carry a `None` onward."""

    def discover(clone, repository):
        raise AssertionError("discovery was asked about a run with no clone")

    with pytest.raises(TheRepositoryHasNotBeenClonedYetError):
        discover_the_repository_in_this_run(_a_state_at_the_start(a_projects_root), discover)


def test_discovery_writes_the_report_and_the_artifact_the_gate_will_ask_about(
    a_projects_root: Path,
) -> None:
    """Two halves, and they are different facts.

    The report is what was found and the identity is what a person is asked to rule on. A report
    in the state with nothing beside it would be approved as nothing, and the record would say a
    human had ruled on a document nobody was shown.
    """
    report = DiscoveryReport(
        languages=["Python"],
        architecture_summary="one module",
        key_components=["health.py"],
        evidence_files=[EvidenceFile(path="health.py", link="local://an/owner/health.py")],
    )

    what_it_wrote = discover_the_repository_in_this_run(
        _a_state_that_has_cloned(a_projects_root),
        lambda clone, repository: (
            report,
            DiscoveryAnswer(
                languages=["Python"], architecture_summary="one module", judged=A_JUDGEMENT
            ),
        ),
    )

    assert what_it_wrote == {
        "discovery_report": report,
        "presented_artifact_id": THE_ARTIFACT_DISCOVERY_PRODUCES,
        "presented_artifact_version": 1,
    }, (
        "discovery has to write what it found *and* what the gate will name, because the gate "
        "presents an artifact id and a version rather than the report itself"
    )


def test_an_agent_that_reasons_leaves_a_note_a_person_reads(a_projects_root: Path) -> None:
    """The note is the agent's own three sentences, and it lands on this work item's card."""
    state = _a_registered_state_that_has_cloned(a_projects_root)

    discover_the_repository_in_this_run(
        state,
        lambda clone, repository: (
            DiscoveryReport(languages=["Python"], architecture_summary="one module"),
            DiscoveryAnswer(languages=["Python"], judged=A_JUDGEMENT),
        ),
    )

    assert _the_notes_on_the_card(state) == [A_JUDGEMENT.the_text_of_the_note_this_is()], (
        "an agent that reasoned left nothing on the card, and a card with no note reads as an "
        "agent that had nothing to say — which is not a thing anybody can check"
    )


def test_the_product_analyst_is_handed_the_request_and_not_only_the_repository(
    a_projects_root: Path,
) -> None:
    """The sentence somebody typed has to be in the room where the requirements are written.

    **This is the most expensive defect the family's history records and the cheapest thing to
    assert.** A real run handed this node a repository and an inspection and nothing else, so the
    four analysis agents answered *what is this project* — a real question with a real answer —
    while the one sentence describing what somebody actually asked for went straight to the
    planner. A requirement is an answer to a question, and the question has to be present.
    """
    what_the_analyst_was_handed: list[tuple[object, object]] = []
    found = {
        "requirements": ["an unauthenticated health endpoint"],
        "acceptance_criteria": ["the suite's file count goes up by one"],
    }

    def analyze(clone, repository, requested):
        what_the_analyst_was_handed.append((repository, requested))
        return Requirements(**found), RequirementsAnswer(judged=A_JUDGEMENT, **found)

    state = _a_state_that_has_cloned(a_projects_root)
    analyze_the_repository_in_this_run(state, analyze)

    assert what_the_analyst_was_handed == [
        (A_REPOSITORY, state["work_item"].requested)
    ], (
        "the product analyst was handed something other than the commission and the repository, "
        "so what it proposes is about the project rather than about the work that was asked for"
    )


def test_the_product_analyst_refuses_a_run_with_no_clone(a_projects_root: Path) -> None:
    with pytest.raises(TheRepositoryHasNotBeenClonedYetError):
        analyze_the_repository_in_this_run(
            _a_state_at_the_start(a_projects_root),
            lambda clone, repository, requested: pytest.fail("the analyst was asked with no clone"),
        )


def test_the_product_analyst_writes_the_artifact_the_gate_will_ask_about(
    a_projects_root: Path,
) -> None:
    found = {"requirements": ["a health endpoint"]}

    what_it_wrote = analyze_the_repository_in_this_run(
        _a_state_that_has_cloned(a_projects_root),
        lambda clone, repository, requested: (
            Requirements(**found),
            RequirementsAnswer(judged=A_JUDGEMENT, **found),
        ),
    )

    assert what_it_wrote["presented_artifact_id"] == THE_ARTIFACT_THE_PRODUCT_ANALYST_PRODUCES
    assert what_it_wrote["presented_artifact_version"] == 1


def test_the_qa_analyst_needs_no_clone_because_it_reads_the_requirements_not_the_code(
    a_projects_root: Path,
) -> None:
    """This node's question is about a document, and the code would be a distraction.

    **And the check is on the state rather than on the function.** The clone on this state is
    `None`, which is the case the other three analysis nodes refuse outright. A change that
    copied their clone check into this one would make the QA stage unreachable rather than
    wrong, and the pipeline would stop three gates in with a message about ordering.
    """
    state = _a_state_a_person_ruled_on_without_asking_about_code(a_projects_root)
    assert state["clone"] is None
    found = {"test_strategy": "run the suite", "scenarios": ["a call answers"]}

    what_it_wrote = analyze_the_requirements_in_this_run(
        state, lambda requirements: (QaPlan(**found), QaPlanAnswer(judged=A_JUDGEMENT, **found))
    )

    assert what_it_wrote["presented_artifact_id"] == THE_ARTIFACT_THE_QA_ANALYST_PRODUCES
    assert what_it_wrote["qa_plan"].scenarios == ["a call answers"]


def test_the_qa_analyst_is_handed_the_requirements_a_person_approved(
    a_projects_root: Path,
) -> None:
    what_the_analyst_was_handed: list[object] = []
    state = _a_state_a_person_ruled_on_without_asking_about_code(a_projects_root)
    found = {"scenarios": ["a call answers"]}

    def analyze(requirements):
        what_the_analyst_was_handed.append(requirements)
        return QaPlan(**found), QaPlanAnswer(judged=A_JUDGEMENT, **found)

    analyze_the_requirements_in_this_run(state, analyze)

    assert what_the_analyst_was_handed == [state["requirements"]], (
        "a QA plan planned from anything other than the approved requirements looks finished to "
        "the person at the gate, and nothing downstream can tell the two apart"
    )


def test_the_qa_analyst_refuses_a_run_with_no_approved_requirements(
    a_projects_root: Path,
) -> None:
    with pytest.raises(RequirementsHaveNotBeenApprovedYetError):
        analyze_the_requirements_in_this_run(
            _a_state_that_has_cloned(a_projects_root),
            lambda requirements: pytest.fail("a plan was made from nothing"),
        )


def test_the_architecture_analyst_is_handed_the_clone_and_the_repository(
    a_projects_root: Path,
) -> None:
    what_the_analyst_was_handed: list[tuple[object, object]] = []
    found = {"findings": ["one module"], "modules": ["health.py"]}

    def analyze(clone, repository):
        what_the_analyst_was_handed.append((clone, repository))
        return (
            ArchitectureReport(**found),
            ArchitectureReportAnswer(judged=A_JUDGEMENT, **found),
        )

    what_it_wrote = analyze_the_architecture_in_this_run(
        _a_state_that_has_cloned(a_projects_root), analyze
    )

    assert what_the_analyst_was_handed == [(A_CLONE, A_REPOSITORY)]
    assert what_it_wrote["presented_artifact_id"] == (
        THE_ARTIFACT_THE_ARCHITECTURE_ANALYST_PRODUCES
    )


def test_the_architecture_analyst_refuses_a_run_with_no_clone(a_projects_root: Path) -> None:
    with pytest.raises(TheRepositoryHasNotBeenClonedYetError):
        analyze_the_architecture_in_this_run(
            _a_state_at_the_start(a_projects_root),
            lambda clone, repository: pytest.fail("the analyst was asked with no clone"),
        )


def test_the_security_analyst_is_handed_the_clone_and_the_repository(
    a_projects_root: Path,
) -> None:
    what_the_analyst_was_handed: list[tuple[object, object]] = []

    def inspect(clone, repository):
        what_the_analyst_was_handed.append((clone, repository))
        return SecurityReport(nothing_found_because="one commit of markdown")

    what_it_wrote = inspect_for_security_risk_in_this_run(
        _a_state_that_has_cloned(a_projects_root), inspect
    )

    assert what_the_analyst_was_handed == [(A_CLONE, A_REPOSITORY)]
    assert what_it_wrote["presented_artifact_id"] == THE_ARTIFACT_THE_SECURITY_ANALYST_PRODUCES


def test_the_security_analyst_leaves_no_note_because_its_answer_cannot_carry_one(
    a_projects_root: Path,
) -> None:
    """The one agent that reasons and says nothing, and the list says which and why.

    **Asserted rather than assumed, because the silence is what a reader of the card has to be
    able to interpret.** A card with no note from the security analyst means *this agent said
    nothing*, and a run that read it as *this agent had no doubt* would be reassuring itself
    about a stage that never answered.
    """
    state = _a_registered_state_that_has_cloned(a_projects_root)

    inspect_for_security_risk_in_this_run(
        state, lambda clone, repository: SecurityReport(nothing_found_because="one commit")
    )

    assert _the_notes_on_the_card(state) == []
    assert "aisdlc-sec-analyze" not in THE_AGENTS_THAT_LEAVE_A_NOTE, (
        "the security analyst left a note this test cannot see, and a reader told it does not "
        "would be told something false"
    )


def test_the_planner_is_handed_the_requirements_the_clone_and_the_runner(
    a_projects_root: Path,
) -> None:
    """Four arguments in a fixed order, and the fourth is the runner's own announcement.

    **The announcement is a fourth argument rather than nothing**, because a test's directory has
    to be one the suite will look in, and that is a fact about the runner rather than something
    this system or the model may decide.
    """
    what_the_planner_was_handed: list[tuple[object, ...]] = []
    state = _a_state_somebody_approved_the_requirements(a_projects_root)

    def plan(requirements, clone, repository, what_the_suite_announced):
        what_the_planner_was_handed.append(
            (requirements, clone, repository, what_the_suite_announced)
        )
        return _a_plan_from_a_planner_that_answers()

    plan_the_change_in_this_run(state, plan)

    assert len(what_the_planner_was_handed) == 1
    what_it_got = what_the_planner_was_handed[0]
    assert what_it_got[0] is state["requirements"]
    assert what_it_got[1] is A_CLONE
    assert what_it_got[2] == A_REPOSITORY
    assert isinstance(what_it_got[3], str), (
        f"the fourth argument is {what_it_got[3]!r} rather than what the runner announced, and "
        "the planner reads emptiness as 'ask nothing'"
    )


def test_the_planner_seam_and_the_planner_name_the_same_arguments() -> None:
    """The seam and the real planner are compared here, in order, minus the model.

    **A `Callable` seam says nothing at import time.** A whole real run in the family this came
    from walked seven gates, six models and a real branch, and was refused by an arity at the
    last step — twenty-four minutes in — because the node's seam and the planner it stands for
    disagreed about their arguments and nothing compared them.

    **The type names and not the parameters themselves**, because the two sides are not the same
    kind of thing: a subscripted `Callable` carries the argument *types* and no names, and the
    planner's own signature carries both. Comparing a class to an `inspect.Parameter` would fail
    for a reason that has nothing to do with the two agreeing.
    """
    what_the_seam_names = [a_kind.__name__ for a_kind in get_args(PlanTheChange)[0]]
    what_the_planner_names = [
        str(a_kind.annotation).strip("'\"")
        for a_name, a_kind in inspect.signature(plan_the_change).parameters.items()
        if a_name != "model"
    ]

    assert what_the_seam_names == what_the_planner_names, (
        f"the node calls the planner with {what_the_seam_names} and the planner takes "
        f"{what_the_planner_names} minus the model the factory closes over"
    )


def test_the_planner_writes_the_version_of_the_plan_it_has_already_written(
    a_projects_root: Path,
) -> None:
    """The version is the count of the planning agent's turns, not a counter of runs.

    **Because a plan a person already approved is a different artifact from the plan written on
    the next turn**, and an approval that cannot tell them apart covers a document nobody read.
    The count is carried by the work item, so a node cannot claim a version.
    """
    state = _a_state_somebody_approved_the_requirements(a_projects_root)
    the_work_item = state["work_item"]

    for _turn in range(2):
        the_work_item = transition(
            the_work_item, Stage.AWAITING_AGENT_PICKUP, THE_DEVELOPER_PLANNING_AGENT, Role.DEV
        )
        the_work_item = transition(
            the_work_item, Stage.IN_PROGRESS_BY_AGENT, THE_DEVELOPER_PLANNING_AGENT, Role.DEV
        )
        the_work_item = transition(the_work_item, Stage.AWAITING_HUMAN_APPROVAL, None, Role.DEV)

    what_it_wrote = plan_the_change_in_this_run(
        {**state, "work_item": the_work_item},
        lambda requirements, clone, repository, announced: _a_plan_from_a_planner_that_answers(),
    )

    assert what_it_wrote["presented_artifact_version"] == 2, (
        "a plan written on the planning agent's second turn was presented at version 1, which is "
        "the version a person already approved"
    )


def test_the_planner_refuses_a_run_with_no_approved_requirements(a_projects_root: Path) -> None:
    with pytest.raises(ThePlanHasNoApprovedRequirementsError):
        plan_the_change_in_this_run(
            _a_state_that_has_cloned(a_projects_root),
            lambda requirements, clone, repository, announced: pytest.fail("it planned anyway"),
        )


def test_a_plan_naming_a_test_the_suite_does_not_collect_is_handed_to_the_supervisor(
    a_projects_root: Path,
) -> None:
    """One named refusal, and the node says in one place that it hands it on.

    **A returned `Command` rather than a raised error**, because this refusal is repairable: the
    plan was wrong about the repository, and the planner is the one who can fix it. A refusal the
    run could not route would end a run over a directory the runner does not collect.
    """

    def a_planner_that_found_an_uncollected_test(
        requirements, clone, repository, what_the_suite_announced
    ):
        raise PlannedTestDirectoryNotCollectedError(["tests/e2e/W-1"], ["tests/unit"])

    what_it_wrote = plan_the_change_in_this_run(
        _a_state_somebody_approved_the_requirements(a_projects_root),
        a_planner_that_found_an_uncollected_test,
    )

    assert what_it_wrote.goto == WHERE_AN_AGENT_LETS_GO_OF_THE_WORK_ITEM, (
        "the refusal goes straight to the supervisor, and the work item is still in the planner's "
        "hands when it gets there. A work item holds exactly one agent and the transition table "
        "refuses to move it into another's, so whichever agent the supervisor names cannot pick it "
        "up — a real run died of exactly that, on `StateMachineError`. The release comes first"
    )
    assert "tests/e2e/W-1" in what_it_wrote.update[WHAT_STOPPED_THIS_RUN], (
        "the supervisor is told a run stopped and not which directory the runner misses, so it "
        "is asked to judge without the one fact the refusal exists to carry"
    )


def test_a_run_that_resumes_takes_the_clone_it_already_has_and_asks_git_nothing(
    a_projects_root: Path,
) -> None:
    """The resume rule is the whole content of this node.

    **Re-making it would work underneath that clone**, and the refusal about a non-empty
    destination would then blame somebody else's work for work this run did ten minutes ago —
    which is a message about the wrong thing entirely.
    """
    what_it_wrote = clone_the_repository_for_this_run(
        _a_state_that_has_cloned(a_projects_root),
        lambda repository, where: pytest.fail("git was reached on resume"),
    )

    assert what_it_wrote == {"clone": A_CLONE}


def test_the_clone_is_asked_where_to_land_before_it_is_fetched(a_projects_root: Path) -> None:
    """The destination is derived from the work item and asked for before anything is fetched.

    **The question comes before the cost**, because a refusal about a missing projects root that
    arrives after a download has begun leaves an operator with a half-finished clone and a
    message about a setting.
    """
    state = _a_registered_state(a_projects_root)
    what_the_clone_was_told: list[tuple[object, Path]] = []

    def plan_the_clone(repository, where):
        what_the_clone_was_told.append((repository, where))
        return a_repository_to_clone(
            repository,
            Addresses(fetch_from="local://bare", origin_of_the_code="local://bare"),
            where,
        )

    with pytest.raises(RepositoryNotFoundError):
        clone_the_repository_for_this_run(state, plan_the_clone)

    assert what_the_clone_was_told == [
        (
            A_REPOSITORY,
            the_clone_directory_of(state["work_item"], a_projects_root),
        )
    ], (
        "the clone was not asked to land in this work item's own clone directory, so two runs "
        "of one work item would fetch into one place and the second would refuse on work the "
        "first one did"
    )


def test_the_transition_node_moves_the_work_item_and_writes_nothing_else(
    a_projects_root: Path,
) -> None:
    """One channel out, and it is the work item.

    **A node returning the whole state would be a writer of every channel**, which is the thing
    the single-writer rule exists to prevent: two branches writing one channel in a step is what
    killed every repair in this system's history.
    """
    state = _a_state_an_agent_has_been_handed_the_work_item(a_projects_root)

    what_it_wrote = transition_the_work_item(state)

    assert list(what_it_wrote) == ["work_item"], (
        f"the transition node wrote {list(what_it_wrote)} rather than only the work item, so it "
        "is a second writer of channels it has no business writing"
    )
    assert what_it_wrote["work_item"].stage is Stage.IN_PROGRESS_BY_AGENT


def test_the_transition_node_records_where_the_work_got_to_so_a_resume_finds_it(
    a_projects_root: Path,
) -> None:
    """Two registers and one move, written from one value at one moment.

    **The engine's own finding is what makes this a test rather than a preference.** A run
    interrupted after four gates left a register that still said `READY` — four gates on disk and
    a work item claiming nobody had started, which is worse than having no register at all.
    """
    state = _a_state_an_agent_has_been_handed_the_work_item(a_projects_root)

    transition_the_work_item(state)

    this_runs_directory = a_projects_root / "an" / "owner" / "a-stage-standing-alone"
    assert (this_runs_directory / "WorkItem.json").is_file(), (
        "the move happened in the run's state and nothing on disk says so, so a run that resumes "
        "picks up work a finished run had already done"
    )


def test_a_refusal_ends_the_run_wherever_it_was_refused(a_projects_root: Path) -> None:
    """One answer, one destination, and saying no is an ending rather than a gap."""
    state = {
        **_a_state_at_the_start(a_projects_root),
        "presented_artifact_id": THE_ARTIFACT_DISCOVERY_PRODUCES,
        "decisions": [
            _an_answer_about(
                THE_ARTIFACT_DISCOVERY_PRODUCES, approved=False, why="it describes a project"
            )
        ],
    }

    assert where_a_gate_outcome_leads(state) == THE_RUN_IS_OVER


def test_an_approved_artifact_leads_exactly_where_the_declared_pipeline_says(
    a_projects_root: Path,
) -> None:
    """The router is a lookup in a declared table, so every row is a claim and is checked here.

    **Compared against the table rather than against a list written here**, because the table is
    also what `the_lifecycle` hands to the graph as the list of destinations. A row that named a
    node the graph has no edge for would stop a run with nothing said.
    """
    what_each_approved_artifact_leads_to = {
        an_artifact: where_a_gate_outcome_leads(
            {
                **_a_registered_state(a_projects_root),
                "presented_artifact_id": an_artifact,
                "decisions": [_an_answer_about(an_artifact, approved=True, why="it is right")],
            }
        )
        for an_artifact in WHERE_AN_APPROVED_ARTIFACT_LEADS
    }

    assert what_each_approved_artifact_leads_to == dict(WHERE_AN_APPROVED_ARTIFACT_LEADS), (
        "the router and the table it reads have drifted apart, and the destination list handed "
        "to the graph is the table's — so a row that disagrees is a route with no node behind it"
    )
    assert what_each_approved_artifact_leads_to[THE_ARTIFACT_PLANNING_PRODUCES] == (
        THE_NEXT_ARTIFACT_IS_THE_CHANGE
    )
    assert what_each_approved_artifact_leads_to[THE_ARTIFACT_THE_QA_ANALYST_PRODUCES] == (
        THE_NEXT_ARTIFACT_IS_THE_ARCHITECTURE
    )
    assert what_each_approved_artifact_leads_to[THE_ARTIFACT_THE_SECURITY_ANALYST_PRODUCES] == (
        THE_NEXT_ARTIFACT_IS_A_PLAN
    )
    assert what_each_approved_artifact_leads_to[THE_ARTIFACT_APPLYING_PRODUCES] == (
        THE_NEXT_ARTIFACT_IS_THE_DELIVERY
    )


def test_an_artifact_nobody_declared_a_route_for_is_refused_by_name(a_projects_root: Path) -> None:
    """A gap in the pipeline is not a decision in it, and the difference is the error's name."""
    state = {
        **_a_state_at_the_start(a_projects_root),
        "presented_artifact_id": "AnArtifactNobodyPlanned",
        "decisions": [
            _an_answer_about("AnArtifactNobodyPlanned", approved=True, why="it is right")
        ],
    }

    with pytest.raises(NoRouteIsDeclaredForThisArtifactError) as the_refusal:
        where_a_gate_outcome_leads(state)

    assert "AnArtifactNobodyPlanned" in str(the_refusal.value), (
        "the refusal does not name the artifact, so a reader has to go and work out which stage "
        "of the pipeline is missing a destination"
    )


def _a_state_an_agent_has_been_handed_the_work_item(a_projects_root: Path) -> AgentState:
    """A registered run standing at `AWAITING_AGENT_PICKUP`, asked to start work.

    **The pickup is applied through the one writer that may make it, and the second move is left
    for the test to make.** `READY -> AWAITING_AGENT_PICKUP` is an edge of the table and applying
    it by hand would be building a state the graph never has; `AWAITING_AGENT_PICKUP ->
    IN_PROGRESS_BY_AGENT` is the edge under test, so the node under test is what makes it.
    """
    state = _a_registered_state(a_projects_root)
    picked_up = {**state, **offer_the_work_item_to_discover(state)}
    with_the_pickup_applied = {**picked_up, **transition_the_work_item(picked_up)}
    return {
        **with_the_pickup_applied,
        **begin_working_on_the_work_item(with_the_pickup_applied),
    }


def _an_answer_about(an_artifact: str, approved: bool, why: str) -> ApprovalDecision:
    """One gate's answer, shaped as the gate's own record — never read from the state by hand."""
    return ApprovalDecision(
        work_item_id="a-stage-standing-alone",
        artifact_id=an_artifact,
        artifact_version=1,
        approved=approved,
        decided_by="a person reading a test",
        decided_at=A_MOMENT,
        reason=why,
    )
