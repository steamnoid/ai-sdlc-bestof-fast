"""The repair supervisor: a stage was wrong, something reads the card and says where to start again.

**This is the one part of the pipeline that had never run.** Everything else in this repository
had been exercised against a real model or a real repository by the time this file was written —
two whole runs, two real briefings — and the supervisor was carried across untouched, because
both runs were answered by a policy that never refused and neither stage hit a refusal worth
repairing. A mechanism nobody has watched is a claim.

**What it is, and the two ways it ends.** A stage that knows its refusal is repairable hands it to
the supervisor as a `Command(goto=...)`; the supervisor reads the card, asks a model which agent
should work again, leaves what it decided where a person will find it, and names one of two
stages. If every agent is told to stand down the run **raises** rather than returning, because a
run that returns quietly reads as a run that finished. If the deployment's ceiling says an agent
is out of turns, it raises a *different* error, because a clean stop and a judgement that failed
must not look alike in a record.

**Three stages route here, and each is named rather than caught broadly.** A node catching
`Exception` would make the supervisor the place a run goes when anything goes wrong, and a repair
that repairs work nobody commissioned is a circle. The three refusals are the ones a *different*
agent can fix: a plan whose test is in a directory the suite does not collect is the planner's
mistake, a test that passes without the change is the implementer's, and a suite that went red is
somebody's.

**The model is faked in every case here and the routing is not.** Each refusal below is a real one,
raised by production code, and the assertion is on the production routing that catches it — so
what is unproven is whether a model answers well, which is `evals/`'s question and not this
file's.
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

import pytest
from langgraph.types import Command

import aisdlc.graph.lifecycle as lifecycle_module
import aisdlc.verify_the_change as verify_the_change
from aisdlc.agents import implement_the_plan
from aisdlc.agents.implementation_plan import ImplementationPlan
from aisdlc.domain.commissioned_request import a_request_about
from aisdlc.domain.repository import Repository
from aisdlc.domain.role import Role
from aisdlc.domain.stage import Stage
from aisdlc.domain.state_machine import transition
from aisdlc.domain.the_work_each_agent_has_done import (
    TheWorkEachAgentHasDone,
    TheWorkOneAgentHasDone,
)
from aisdlc.domain.work_item import WorkItem, a_work_item_commissioned_for_an_agent
from aisdlc.graph import apply_node
from aisdlc.graph.agent_state import WHAT_STOPPED_THIS_RUN, AgentState
from aisdlc.graph.supervise_a_repair import (
    TheRepeatBudgetRanOutError,
    TheSupervisorJudgedThisIsNotRepairingError,
    supervise_a_repair,
    the_text_of_the_decision_this_is,
)
from aisdlc.graph.what_to_repeat import (
    WhatOneAgentMustDoAgain,
    WhatToRepeat,
    WhereTheRunShouldStartAgain,
)
from aisdlc.tools.what_people_said_about_a_work_item import what_people_said_about

A_REPOSITORY = Repository(owner="an", name="owner")
THE_PLANNER = "aisdlc-dev-plan"
THE_IMPLEMENTER = "aisdlc-dev-impl"
A_MOMENT = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# The card a supervisor is handed, and the refusals it is handed with.
# ---------------------------------------------------------------------------


@pytest.fixture
def an_open_register(tmp_path: Path) -> Path:
    """A register in this test's directory, because leaving a note now writes to it.

    **Not ceremony.** A note is written twice — once to the card beside the clone and once to the
    register a board reads — and the supervisor's whole reason for leaving one is that a run which
    repeats an agent's work must be explainable to whoever reads it third. A test that let the
    write fail would be testing a supervisor that cannot record its own decisions.
    """
    from aisdlc.store.where_the_register_lives import the_register_lives_at

    the_register_lives_at(tmp_path / "the-register.sqlite3")
    return tmp_path


@pytest.fixture
def a_work_item_at_a_stage(tmp_path: Path, an_open_register: Path) -> WorkItem:
    """A work item that has been picked up and worked on, so its turns are countable.

    **The turns are what the ceiling is checked against**, and a work item that has never had any
    is one where the ceiling can never bite — so the counts are set by hand rather than by
    walking the table, which is what a run does and what this test is not about.
    """
    a_work_item = a_work_item_commissioned_for_an_agent(
        work_item_id="issue-7",
        repository=A_REPOSITORY,
        accountable_role=Role.DEV,
        commissioned_by="a person",
        requested=a_request_about("add a health endpoint"),
    )
    return a_work_item.model_copy(
        update={
            "work_done": TheWorkEachAgentHasDone(
                worked=(
                    TheWorkOneAgentHasDone(agent=THE_PLANNER, how_many_times=1),
                    TheWorkOneAgentHasDone(agent=THE_IMPLEMENTER, how_many_times=1),
                )
            )
        }
    )


def _a_verdict(
    agent: str, must_repeat: bool = True, why: str = "the test was in a directory nothing collects"
) -> WhatOneAgentMustDoAgain:
    return WhatOneAgentMustDoAgain(agent=agent, must_repeat_its_work=must_repeat, why=why)


# Every agent a run reasons with, and `WhatToRepeat` requires a verdict for each of them: **a
# run cannot tell an agent that had nothing to do from an agent nobody spoke about.** A verdict
# that is missing is a silence, and a silence in this table would be read as "nothing to do".
EVERY_AGENT_THIS_RUN_REASONS_WITH = (
    "aisdlc-discover",
    "aisdlc-po-analyze",
    "aisdlc-qa-analyze",
    "aisdlc-arch-analyze",
    "aisdlc-sec-analyze",
    "aisdlc-dev-plan",
    "aisdlc-dev-impl",
)


def _a_decision(
    where: WhereTheRunShouldStartAgain,
    *verdicts: WhatOneAgentMustDoAgain,
    what_has_not_changed: str = "the repository still collects nothing under that directory",
) -> WhatToRepeat:
    """A decision in which every agent not named is told to stand down.

    **The stand-down is written rather than left out**, and that is the rule the model is held to
    as much as this helper is. `WhatToRepeat` refuses a verdict that is missing, because a run
    cannot tell an agent that had nothing to do from an agent nobody spoke about — and this
    helper has to satisfy the same rule the model does, or the tests would be asserting against
    a shape the real answer cannot take.
    """
    the_named_agents = {verdict.agent for verdict in verdicts}
    everyone_else = tuple(
        _a_verdict(
            an_agent,
            must_repeat=False,
            why=f"{an_agent} had nothing to do with what stopped this run",
        )
        for an_agent in EVERY_AGENT_THIS_RUN_REASONS_WITH
        if an_agent not in the_named_agents
    )

    return WhatToRepeat(
        what_each_agent_must_do=(*verdicts, *everyone_else),
        where_to_start_again=where,
        what_has_not_changed=what_has_not_changed,
    )


class _AModelThatAnswers:
    """A model that answers whatever the supervisor asks, and records that it was asked.

    **The question is kept and not only the answer returned**, because the supervisor's whole job
    is to decide on two things — the card's notes and the refusal's own words — and a test that
    only checked the returned command would pass if the supervisor had asked the model about
    neither.
    """

    def __init__(self, the_answer: WhatToRepeat) -> None:
        self.the_answer = the_answer
        self.what_it_was_asked: list[str] = []

    def with_structured_output(self, *arguments: object, **keywords: object) -> object:
        """LangChain's entry point, and the answer is already decided, so this is the model."""
        return self

    def invoke(self, the_question: str) -> dict[str, object]:
        """Hand back the prepared answer, and keep the question so a test can read it."""
        self.what_it_was_asked.append(the_question)
        return self.the_answer.model_dump(mode="json")


# ---------------------------------------------------------------------------
# The two places a verdict can send a run, and the two ways the loop ends.
# ---------------------------------------------------------------------------


def test_a_verdict_to_rewrite_the_plan_sends_the_run_back_to_the_planner(
    a_work_item_at_a_stage: WorkItem, tmp_path: Path, monkeypatch
) -> None:
    """An uncollected test directory is the planner's mistake, and the run goes back there."""
    monkeypatch.setenv("AISDLC_REPEAT_BUDGET", "0")
    the_model = _AModelThatAnswers(
        _a_decision(
            WhereTheRunShouldStartAgain.THE_CHANGE_IS_PLANNED_AGAIN,
            _a_verdict(THE_PLANNER),
            _a_verdict(THE_IMPLEMENTER, must_repeat=False, why="the implementer was right"),
        )
    )

    the_command = supervise_a_repair(
        a_work_item_at_a_stage,
        tmp_path,
        "the plan's tests_to_add names tests/unit, and the repository collects nothing there",
        the_model,  # type: ignore[arg-type]
    )

    assert isinstance(the_command, Command)
    assert the_command.goto == "offer_the_work_item_to_the_planner", (
        "a plan that was wrong about the repository can only be fixed by the agent that made it, "
        "so the supervisor names the planner — and the name is a literal here rather than a value "
        "read from a model, because a model routing this graph is the one thing in the pipeline "
        "that is declared as code rather than reasoned about"
    )
    assert the_command.update["repair"].where_to_start_again is (
        WhereTheRunShouldStartAgain.THE_CHANGE_IS_PLANNED_AGAIN
    )


def test_a_verdict_to_rewrite_the_change_sends_the_run_back_to_the_implementer(
    a_work_item_at_a_stage: WorkItem, tmp_path: Path, monkeypatch
) -> None:
    """A test that passed without the change is the implementer's mistake, and goes back there."""
    monkeypatch.setenv("AISDLC_REPEAT_BUDGET", "0")
    the_model = _AModelThatAnswers(
        _a_decision(
            WhereTheRunShouldStartAgain.THE_CHANGE_IS_WRITTEN_AGAIN,
            _a_verdict(THE_IMPLEMENTER, why="the test passed with the change put back"),
        )
    )

    the_command = supervise_a_repair(
        a_work_item_at_a_stage,
        tmp_path,
        "test_health.py passes with health.py deleted, so it observed nothing",
        the_model,  # type: ignore[arg-type]
    )

    assert the_command.goto == "offer_the_work_item_to_the_implementer"


def test_every_agent_told_to_stand_down_stops_the_run_by_refusing(
    a_work_item_at_a_stage: WorkItem, tmp_path: Path, monkeypatch
) -> None:
    """Nobody repeats anything, so the run raises rather than returning.

    **A refusal and not a return, and that is the whole of the difference between the two ways a
    repair loop ends.** A run that returned quietly reads as a run that finished: the work item
    would sit at whatever stage it was at, the card would show no reason, and a reader finding it
    stopped would look for one and find nothing.
    """
    monkeypatch.setenv("AISDLC_REPEAT_BUDGET", "0")
    the_model = _AModelThatAnswers(
        _a_decision(
            WhereTheRunShouldStartAgain.THE_CHANGE_IS_WRITTEN_AGAIN,
            _a_verdict(THE_IMPLEMENTER, must_repeat=False, why="the change was right"),
            what_has_not_changed="nothing the supervisor could act on has changed",
        )
    )

    with pytest.raises(TheSupervisorJudgedThisIsNotRepairingError) as stopped:
        supervise_a_repair(
            a_work_item_at_a_stage,
            tmp_path,
            "the suite went red",
            the_model,  # type: ignore[arg-type]
        )

    assert "nothing the supervisor could act on has changed" in str(stopped.value), (
        "the refusal carries the supervisor's own sentence about what has not changed, because "
        "that sentence is the reason a person reading this card three months later will need"
    )


def test_an_agent_out_of_turns_stops_the_run_and_says_it_was_the_ceiling(
    a_work_item_at_a_stage: WorkItem, tmp_path: Path, monkeypatch
) -> None:
    """A repeat an agent has already had is overruled, and that is a fact of its own.

    **A different error from a clean stop, and the reason is in the message.** The supervisor
    judged a repair worth trying and the deployment overruled it. A reader who cannot tell those
    apart goes to the wrong place — one to read the card, the other to read the setting — so the
    two are separate types.
    """
    monkeypatch.setenv("AISDLC_REPEAT_BUDGET", "1")
    the_model = _AModelThatAnswers(
        _a_decision(
            WhereTheRunShouldStartAgain.THE_CHANGE_IS_WRITTEN_AGAIN,
            _a_verdict(THE_IMPLEMENTER, why="it wrote a test that observed nothing"),
        )
    )

    with pytest.raises(TheRepeatBudgetRanOutError) as the_ceiling:
        supervise_a_repair(
            a_work_item_at_a_stage,
            tmp_path,
            "the suite went red",
            the_model,  # type: ignore[arg-type]
        )

    assert "already had every turn" in str(the_ceiling.value)
    assert "AISDLC_REPEAT_BUDGET" in str(the_ceiling.value), (
        "the refusal names the setting, because a person reading it has to go and change the "
        "number and cannot do that without knowing which one"
    )


def test_a_ceiling_of_zero_means_the_ceiling_does_not_apply(
    a_work_item_at_a_stage: WorkItem, tmp_path: Path, monkeypatch
) -> None:
    """`0` lifts the ceiling rather than forbidding every repeat, which is not a count."""
    monkeypatch.setenv("AISDLC_REPEAT_BUDGET", "0")
    the_model = _AModelThatAnswers(
        _a_decision(
            WhereTheRunShouldStartAgain.THE_CHANGE_IS_WRITTEN_AGAIN,
            _a_verdict(THE_IMPLEMENTER),
        )
    )

    the_command = supervise_a_repair(
        a_work_item_at_a_stage,
        tmp_path,
        "the suite went red",
        the_model,  # type: ignore[arg-type]
    )

    assert the_command.goto == "offer_the_work_item_to_the_implementer", (
        "an implementer that has already had a turn is asked again with a ceiling of 0, which is "
        "a deployment that lifted the ceiling rather than one that forbade every repeat. Reading "
        "0 as 'no repeats at all' would make the setting mean two different things depending on "
        "which agent it was read for"
    )


# ---------------------------------------------------------------------------
# What the supervisor is handed, and what it leaves behind.
# ---------------------------------------------------------------------------


def test_the_supervisor_is_handed_the_card_whole_and_the_refusal_whole(
    a_work_item_at_a_stage: WorkItem, tmp_path: Path, monkeypatch
) -> None:
    """Every note on the card is in the question, and the refusal arrives as the words themselves.

    **A summary would not be the evidence.** The note mechanism exists so that a later agent
    reads what an earlier one actually wrote — including the sentence an implementer wrote when
    it was not sure which of two things it had been asked to do — and a supervisor handed a
    summary is a supervisor guessing.
    """
    monkeypatch.setenv("AISDLC_REPEAT_BUDGET", "0")
    from aisdlc.tools.what_people_said_about_a_work_item import a_comment_was_left

    a_comment_was_left(
        a_work_item_at_a_stage,
        what_was_said=(
            "found: the plan names tests/unit\ncould not settle: what the runner collects"
        ),
        by=THE_PLANNER,
        at=A_MOMENT,
        projects_root=tmp_path,
    )
    a_comment_was_left(
        a_work_item_at_a_stage,
        what_was_said="could not settle: whether the plan meant a rule or a whole new file",
        by=THE_IMPLEMENTER,
        at=A_MOMENT,
        projects_root=tmp_path,
    )

    the_refusal = (
        "tests/unit/test_health.py is in the plan's tests_to_add, and the repository collects "
        "nothing under tests/unit"
    )
    the_model = _AModelThatAnswers(
        _a_decision(
            WhereTheRunShouldStartAgain.THE_CHANGE_IS_PLANNED_AGAIN,
            _a_verdict(THE_PLANNER),
        )
    )
    supervise_a_repair(a_work_item_at_a_stage, tmp_path, the_refusal, the_model)  # type: ignore[arg-type]

    the_question = the_model.what_it_was_asked[0]

    assert the_refusal in the_question, (
        "the refusal arrives as its own words rather than as a summary of them, because a "
        "supervisor deciding on a summary is a supervisor guessing"
    )
    assert "could not settle: what the runner collects" in the_question
    assert "could not settle: whether the plan meant a rule or a whole new file" in the_question


def test_the_decision_is_left_on_the_card_before_the_run_moves(
    a_work_item_at_a_stage: WorkItem, tmp_path: Path, monkeypatch
) -> None:
    """Every verdict is written down, including the ones that stand an agent down.

    **Before it acts, not after.** A run that repeats an agent's work and leaves no record of why
    is a run whose second attempt is unexplainable to whoever reads it third — and the note is
    what a person reads when they are deciding whether the repair was justified.
    """
    monkeypatch.setenv("AISDLC_REPEAT_BUDGET", "0")
    the_model = _AModelThatAnswers(
        _a_decision(
            WhereTheRunShouldStartAgain.THE_CHANGE_IS_PLANNED_AGAIN,
            _a_verdict(THE_PLANNER),
            _a_verdict(THE_IMPLEMENTER, must_repeat=False, why="the implementer was right"),
            what_has_not_changed="the runner still collects nothing under that directory",
        )
    )

    supervise_a_repair(a_work_item_at_a_stage, tmp_path, "the plan was wrong", the_model)  # type: ignore[arg-type]

    the_notes = what_people_said_about(A_REPOSITORY, "issue-7", tmp_path).comments
    said_by_the_supervisor = [
        a_note for a_note in the_notes if a_note.said_by.endswith("supervise")
    ]

    assert len(said_by_the_supervisor) == 1, (
        "the supervisor left no decision on the card, so a run that repeated an agent's work is "
        "unexplainable to whoever reads it third"
    )

    what_it_said = said_by_the_supervisor[0].what_was_said
    assert f"{THE_PLANNER}: repeat" in what_it_said
    assert f"{THE_IMPLEMENTER}: stand down" in what_it_said, (
        "a record saying only who repeats cannot be argued with afterwards — a reader who "
        "disagrees with the implementer being left alone has nothing to point at"
    )
    assert "the runner still collects nothing under that directory" in what_it_said


def test_what_the_supervisor_said_names_every_agent_it_judged(
    a_work_item_at_a_stage: WorkItem, tmp_path: Path, monkeypatch
) -> None:
    """The text on the card is the same text the run is handed, written once."""
    monkeypatch.setenv("AISDLC_REPEAT_BUDGET", "0")
    the_decision = _a_decision(
        WhereTheRunShouldStartAgain.THE_CHANGE_IS_WRITTEN_AGAIN,
        _a_verdict(THE_IMPLEMENTER),
        _a_verdict(THE_PLANNER, must_repeat=False, why="the plan was right"),
    )
    the_model = _AModelThatAnswers(the_decision)

    supervise_a_repair(a_work_item_at_a_stage, tmp_path, "red suite", the_model)  # type: ignore[arg-type]

    the_notes = what_people_said_about(A_REPOSITORY, "issue-7", tmp_path).comments
    what_the_supervisor_said = next(
        a_note.what_was_said for a_note in the_notes if a_note.said_by.endswith("supervise")
    )

    assert the_text_of_the_decision_this_is(the_decision) == what_the_supervisor_said, (
        "two renderings of one decision are two things that can disagree, and the one a person "
        "reads on the card is the one that has to be the one the run acted on"
    )


# ---------------------------------------------------------------------------
# The three refusals that reach the supervisor, each one raised by production code.
# ---------------------------------------------------------------------------


def test_a_suite_that_went_red_is_handed_to_the_supervisor_and_not_delivered() -> None:
    """A red suite is the supervisor's to judge, and the delivery refuses rather than pushing.

    **A `Command` and not a raise, because the run is not stopping.** A red suite is the one
    failure this whole mechanism exists for: the change may be wrong, or the plan that produced
    it may be wrong, and a supervisor handed the card is the one thing that can tell which. A
    delivery that raised here would be a run that stopped for a reason nobody had judged.
    """
    from aisdlc.agents.verification_report import VerificationReport
    from aisdlc.graph.deliver_node import open_the_delivery

    a_state: AgentState = {
        "work_item": _a_work_item_at_the_delivery_gate(),
        "projects_root": Path("/nowhere"),
        "clone": None,
        "requested_stage": Stage.AWAITING_HUMAN_APPROVAL,
        "requested_agent": None,
        "requested_role": Role.DEV,
        "discovery_report": None,
        "requirements": None,
        "qa_plan": None,
        "architecture_report": None,
        "security_report": None,
        "implementation_plan": None,
        "written_files": None,
        "verification_report": VerificationReport(
            suite_before_the_change=_a_suite_that(passed=True),
            suite_after_the_change=_a_suite_that(passed=False),
        ),
        "pull_request_request": None,
        "opened_pull_request": None,
        "presented_artifact_id": "PullRequestRequest",
        "presented_artifact_version": 1,
        "repair": None,
        "what_stopped_this_run": None,
        "decisions": [],
        "approvals": [],
    }

    our_copy, push, open_a_pull_request = _a_delivery_that_records()
    the_command = open_the_delivery(a_state, our_copy, push, open_a_pull_request)

    assert the_command.goto == "let_go_of_the_work_item", (
        "a red suite went to a node other than the one that releases the work item and then the "
        "supervisor. A work item still held by the delivery agent cannot be picked up by whichever "
        "agent the supervisor names — the transition table refuses it, which a real run did, with "
        "`StateMachineError: aisdlc-dev-impl holds this work item and cannot hand it to`. The "
        "supervisor is still two steps away and still the only node that judges a red suite"
    )
    assert WHAT_STOPPED_THIS_RUN in the_command.update
    assert "red" in the_command.update[WHAT_STOPPED_THIS_RUN].lower(), (
        "the refusal handed over does not say the suite went red, so the supervisor is asked to "
        "decide on something other than the thing that happened"
    )


def test_a_refusal_with_no_reason_is_refused_before_the_supervisor_is_asked() -> None:
    """A run sent to the supervisor without saying what stopped it is refused, not guessed at.

    **The supervisor is told a stage was wrong; what it was wrong about is the evidence.** A
    prompt with the first half and not the second is a model asked to guess, and a guess here is a
    stage being repeated for a reason nobody wrote down.
    """
    from aisdlc.graph.supervise_a_repair import ARefusalWithNoReasonToRepairError
    from aisdlc.graph.supervise_a_repair_in_this_run import supervise_a_repair_in_this_run

    was_called = []

    def a_supervisor(*arguments: object, **keywords: object) -> Command:
        was_called.append(arguments)
        return Command(goto="wherever")

    the_state: AgentState = {
        "work_item": _a_work_item_at_the_delivery_gate(),
        "projects_root": Path("/nowhere"),
        WHAT_STOPPED_THIS_RUN: "",
    }

    with pytest.raises(ARefusalWithNoReasonToRepairError):
        supervise_a_repair_in_this_run(the_state, a_supervisor)  # type: ignore[arg-type]

    assert was_called == [], "the supervisor was asked with nothing to decide on"


def test_a_run_with_no_supervisor_at_all_stops_saying_which_one_is_missing() -> None:
    """The default seam refuses by name, so a run cannot arrive here having quietly done nothing."""
    from aisdlc.graph.supervise_a_repair import (
        ThereIsNoSupervisorForThisRunError,
        no_supervisor_was_given_to_this_run,
    )

    with pytest.raises(ThereIsNoSupervisorForThisRunError) as missing:
        no_supervisor_was_given_to_this_run()

    assert "supervise" in str(missing.value), (
        "the refusal has to say which field was not named, because whoever reads this in a trace "
        "is a person deciding whether to wire a supervisor into their deployment"
    )


# ---------------------------------------------------------------------------
# Two small builders, so a state above is not a wall of literals.
# ---------------------------------------------------------------------------


def _a_delivery_that_records() -> tuple[Repository, object, object]:
    """A delivery that pushes nothing, because the refusal this test provokes comes first.

    **A red suite is checked before the branch is pushed**, so a delivery that would have pushed
    is never reached — and the two collaborators are therefore not exercised at all. They are
    given values rather than doubles that raise, because a double that raised would be a second
    refusal in the same test and the assertion would not know which one it was reading.
    """
    return (
        A_REPOSITORY,
        lambda clone, name: pytest.fail("nothing should be pushed by a run whose suite went red"),
        lambda wanted: pytest.fail(
            "no pull request should be opened by a run whose suite went red"
        ),
    )


def _a_suite_that(passed: bool) -> object:
    """One suite outcome, passing or not, for a verification report to be made of."""
    from aisdlc.tools.run_tests import SuiteOutcome

    return SuiteOutcome(
        exit_code=0 if passed else 1,
        passed=passed,
        dependencies_installed=True,
        output="1 passed" if passed else "1 failed",
    )


def _a_work_item_at_the_delivery_gate() -> WorkItem:
    """A work item that has reached its last gate, which is where a delivery is judged."""
    the_work_item = a_work_item_commissioned_for_an_agent(
        work_item_id="issue-7",
        repository=A_REPOSITORY,
        accountable_role=Role.DEV,
        commissioned_by="a person",
        requested=a_request_about("add a health endpoint"),
    )
    # **Three moves, because the table says so and nothing else may be jumped.** The rule being
    # read here is the transition table's, and a builder that went straight to the gate would be
    # a test asserting about a work item this system cannot be in.
    picked_up = transition(
        the_work_item, Stage.AWAITING_AGENT_PICKUP, THE_IMPLEMENTER, Role.DEV
    )
    working = transition(picked_up, Stage.IN_PROGRESS_BY_AGENT, THE_IMPLEMENTER, Role.DEV)
    return transition(working, Stage.AWAITING_HUMAN_APPROVAL, None, Role.DEV)


def test_the_node_whose_routing_is_checked_is_the_one_the_graph_registers() -> None:
    """The delivery node this file calls is the node the graph registers, by name.

    **A check about a function nothing calls is a check that passes forever.** The routing above
    is only a claim about the pipeline if the function carrying it is the one wired into the
    graph, and the only thing that settles that is the name the graph registers.

    **The cast is `None` for both of the things this stage is handed, and the reason is that the
    graph is only being asked what it registers.** `_the_delivery_stage` grew an `agents`
    parameter when the conflict node arrived — it registers a node that reads
    `agents.settle_a_conflict`, and a node that reads a field is a node that needs the field —
    and this call was left with two arguments, so the stage could not be registered at all. Both
    collaborators are read inside the lambdas this stage hands the graph, and a lambda is not
    called by `add_node`, so nothing here ever touches either one. **A cast and not a double:**
    a stand-in for `TheAgentsThisRun` would be a second cast of the same claim, and this file's
    claim is about names rather than about collaborators.
    """
    from aisdlc.graph.lifecycle import _the_delivery_stage

    the_registered_names: list[str] = []

    class AGraphThatRecordsWhatWasAdded:
        """Stands in for a `StateGraph`, recording the names and asserting nothing else."""

        def add_node(self, name: str, *arguments: object, **keywords: object) -> None:
            the_registered_names.append(name)

        def add_edge(self, *arguments: object, **keywords: object) -> None:
            """The edges are not what this checks, so they are dropped."""

        def add_conditional_edges(self, *arguments: object, **keywords: object) -> None:
            """And the conditional edges, for the same reason."""

    _the_delivery_stage(
        AGraphThatRecordsWhatWasAdded(),  # type: ignore[arg-type]
        agents=None,  # type: ignore[arg-type]
        delivery=None,  # type: ignore[arg-type]
    )

    assert "begin_delivering_the_work_item" in the_registered_names, (
        f"the graph registers {the_registered_names}, and the routing this file checks belongs to "
        "a node that is not among them — so the check is about a function nothing calls"
    )


def test_a_change_that_writes_nothing_is_handed_to_the_supervisor() -> None:
    """An implementer that wrote the file back unchanged is the most repairable refusal there is.

    **And it killed the run until a real run found it.** Asked to change the Dockerfile's
    healthcheck interval, the planner named the Dockerfile and the implementer wrote it back
    byte-for-byte, keeping `--interval=30s`. That is the refusal this mechanism exists for — the
    plan was right and named the file, the implementer ignored it, and the answer to "which agent
    was wrong" is not in doubt — and the run stopped dead, because this node's `except` named
    only the other refusal.

    The refusal was right and the routing was wrong, which is the combination this repository has
    now found three times: something the gate did correctly, and an engine underneath it that did
    not.
    """
    from aisdlc.agents.implement_the_plan import AWriteThatChangesNothingError
    from aisdlc.graph.agent_state import WHAT_STOPPED_THIS_RUN
    from aisdlc.graph.apply_node import apply_and_verify_in_this_run

    what_the_plan_asked = ImplementationPlan(
        files_to_change=["Dockerfile"], tests_to_add=[]
    )
    a_state: AgentState = {
        "work_item": _a_work_item_at_the_delivery_gate(),
        "projects_root": Path("/nowhere"),
        "clone": _a_clone_standing_in_for_a_real_one(),
        "implementation_plan": what_the_plan_asked,
        "requested_stage": Stage.AWAITING_HUMAN_APPROVAL,
        "requested_agent": None,
        "requested_role": Role.DEV,
        "presented_artifact_id": "VerificationReport",
        "presented_artifact_version": 1,
        "decisions": [],
        "approvals": [],
        WHAT_STOPPED_THIS_RUN: None,
    }

    def an_implementer_that_wrote_nothing(*arguments: object) -> object:
        """The real refusal, raised by the real exception with the real paths."""
        raise AWriteThatChangesNothingError(["Dockerfile"])

    the_command = apply_and_verify_in_this_run(a_state, an_implementer_that_wrote_nothing)  # type: ignore[arg-type]

    assert isinstance(the_command, Command)
    assert the_command.goto == "let_go_of_the_work_item", (
        "an implementer that wrote the file back unchanged stops the run, and it is the one "
        "refusal where the answer is least in doubt: the plan named the file and said what to "
        "change in it. A question this system built a reader for is not a question to answer by "
        "stopping. **And it goes through the release first**, because a work item still held by "
        "this agent cannot be picked up by the one the supervisor names — a real run died of "
        "`StateMachineError: aisdlc-dev-impl holds this work item and cannot hand it to`, on the "
        "supervisor's first firing inside a real run"
    )
    assert "Dockerfile" in the_command.update[WHAT_STOPPED_THIS_RUN], (
        "the refusal handed over does not name the file, so the supervisor is asked to judge "
        "without knowing which one was left alone"
    )


def test_every_node_that_hands_a_refusal_on_releases_the_work_item_through_the_node_that_does() -> (
    None
):
    """All three hand over to the release, and the release is the only place the move is asked for.

    **The defect the previous test found, applied to the two nodes beside it, and then to the
    shape of the fix itself.** A real run's implementer handed a refusal on and died one node later
    with `StateMachineError: aisdlc-dev-impl holds this work item and cannot hand it to`. The
    planner and the delivery node have the same shape — same `Command(goto=supervisor)`, same
    refusal channel, no release — and they are the two a real run reaches whenever a plan is wrong
    about the runner or a suite goes red after a change.

    **The first version of the fix put the request in each of the three nodes, and that was wrong
    too.** A request for a move is not a move, and a node that asks for one has not made it — so
    the request sat in the state and the next pickup node overwrote it with its own. The release
    is therefore a node, and it is the only place the move is asked for: three nodes hand a
    refusal to it, and one of them owns the move. **That is why this reads the destinations rather
    than the updates.**
    """
    from aisdlc.graph import apply_node, deliver_node, plan_node

    the_handovers: dict[str, str] = {}
    for a_module, a_node_name in (
        (apply_node, "make_and_verify_the_change"),
        (plan_node, "plan_the_change"),
        (deliver_node, "deliver_this_run"),
    ):
        the_source = ast.parse(Path(a_module.__file__).read_text())
        for what_is_called in ast.walk(the_source):
            if not isinstance(what_is_called, ast.Call):
                continue
            if not isinstance(what_is_called.func, ast.Name):
                continue
            if what_is_called.func.id != "Command":
                continue
            what_it_was_given = {
                a_keyword.arg: a_keyword.value for a_keyword in what_is_called.keywords
            }
            what_it_goes_to = what_it_was_given.get("goto")
            if not isinstance(what_it_goes_to, ast.Name):
                continue
            if what_it_goes_to.id == "WHERE_AN_AGENT_LETS_GO_OF_THE_WORK_ITEM":
                the_handovers[a_node_name] = what_it_goes_to.id

    assert set(the_handovers) == {
        "make_and_verify_the_change",
        "plan_the_change",
        "deliver_this_run",
    }, (
        f"only {sorted(the_handovers)} hand a refusal on through the release. A refusal handed "
        "straight to the supervisor leaves the work item in the refusing agent's hands, and the "
        "supervisor's verdict is then unrepresentable — a real run died of "
        "`StateMachineError: aisdlc-dev-impl holds this work item and cannot hand it to`"
    )


def test_the_release_asks_for_the_work_item_to_come_back_held_by_nobody() -> None:
    """The move the release makes, and why it is a release and not a hand-over to the next agent.

    **`AWAITING_AGENT_PICKUP` with no agent, and this is the whole of it.** A work item in
    `IN_PROGRESS_BY_AGENT` holds exactly one agent, and
    `_takes_the_work_item_from_the_holding_agent` refuses a move that would put it in another
    agent's hands — which is right, and which is why a repair needs this move to happen first. The
    alternative would be for this node to name whichever agent the supervisor is about to name,
    and it cannot know: that verdict has not been made yet, and a node that guessed it would be a
    second place where a run decides who works next.

    **The refusal is not read here.** `what_stopped_this_run` is already in the state, written by
    the node that handed over, and the supervisor still reads it in that node's own words.

    **A plain update and not a `Command`, and that is a bug this test was written after.** The
    first version returned `Command(goto=supervisor, ...)` naming where the work item should go,
    which reads as the tidier shape — a node that hands on and says what it wants. It skips the
    transition node that would make the move, so the request sat in the state and the next pickup
    node overwrote it with its own. The run still died at the same `StateMachineError`, one node
    later, and the fix had changed nothing observable. **A `Command` names its own destination**,
    so a node that asks the graph to make a move must not return one.
    """
    from aisdlc.graph.release_the_work_item_node import let_go_of_the_work_item

    what_it_asked_for = let_go_of_the_work_item(_a_state_at_the_start_with_a_work_item_being_held())

    assert what_it_asked_for["requested_stage"] == Stage.AWAITING_AGENT_PICKUP, (
        f"the release asked for {what_it_asked_for['requested_stage']!r}, so the work item is "
        "left in IN_PROGRESS_BY_AGENT and the agent the supervisor names cannot pick it up"
    )
    assert what_it_asked_for["requested_agent"] is None, (
        f"the release asked for the work item to be held by "
        f"{what_it_asked_for['requested_agent']!r}, which is the peer hand-over the transition "
        "table refuses — the very refusal a real run died of. A release names nobody"
    )
    assert not isinstance(what_it_asked_for, Command), (
        "the release returns a Command, so it names its own destination and the transition node "
        "that would make the move is skipped entirely. The request then sits in the state until "
        "the next pickup node overwrites it, and the run dies at the same place it died before "
        "this node existed. A node that asks for a move must let the graph walk it"
    )


def _a_state_at_the_start_with_a_work_item_being_held() -> AgentState:
    """A run whose work item an agent is holding, which is what a refusal is raised from."""
    return {
        "work_item": _a_work_item_being_implemented(),
        "projects_root": Path("/nowhere"),
        "clone": None,
        "requested_stage": Stage.IN_PROGRESS_BY_AGENT,
        "requested_agent": THE_IMPLEMENTER,
        "requested_role": Role.DEV,
        "presented_artifact_id": "VerificationReport",
        "presented_artifact_version": 1,
        "decisions": [],
        "approvals": [],
        WHAT_STOPPED_THIS_RUN: "the refusal, in the words the refusing node used",
    }


def _a_work_item_being_implemented() -> WorkItem:
    """A work item an implementer is holding, which is the state a refusal is raised from."""
    commissioned = a_work_item_commissioned_for_an_agent(
        work_item_id="issue-9",
        repository=A_REPOSITORY,
        accountable_role=Role.DEV,
        commissioned_by="a person",
        requested=a_request_about("remove the fallback"),
    )
    picked_up = transition(
        commissioned, Stage.AWAITING_AGENT_PICKUP, THE_IMPLEMENTER, Role.DEV
    )
    working = transition(picked_up, Stage.IN_PROGRESS_BY_AGENT, THE_IMPLEMENTER, Role.DEV)
    return transition(working, Stage.AWAITING_HUMAN_APPROVAL, None, Role.DEV)


def _a_clone_standing_in_for_a_real_one() -> object:
    """A clone the implementer node accepts, built without one being on disk.

    **This node checks that a clone and a plan arrived and nothing else** — the refusal below is
    raised by the collaborator it is handed, before anything reads the clone. A real checkout
    would make this test about the fixture rather than about the routing.
    """
    from aisdlc.tools.github_clone_repository import ClonedRepository

    return ClonedRepository(path=Path("/nowhere/a-clone"), ref="main", commit="0" * 40)


def test_a_test_the_suite_never_ran_is_handed_to_the_supervisor() -> None:
    """The third sibling: the change ships, the suite is green, and the new test never ran.

    **The green report is the point.** `ATestThatPassesWithoutTheChangeError` fires when a change
    proves nothing because the suite is the same either way, and this one fires when the suite
    agrees and *never collected the test the plan said it added* — a green report over a change
    that was never executed is the report that lies, and it is the only one of the three that
    looks entirely healthy from the outside.

    **It is raised by the same node as its sibling and was not routed, which is how the second
    one was missed.** Two of these three refusals came out of real runs and the third was found
    by reading the `except` that had been edited to hold the other two. Naming two siblings and
    leaving the third to be discovered by a run is not a defensible way to hold a list, so this
    is the test that says the list is closed.
    """
    from aisdlc.graph.agent_state import WHAT_STOPPED_THIS_RUN
    from aisdlc.graph.apply_node import apply_and_verify_in_this_run
    from aisdlc.verify_the_change import AnUnrunTestError

    a_state: AgentState = {
        "work_item": _a_work_item_at_the_delivery_gate(),
        "projects_root": Path("/nowhere"),
        "clone": _a_clone_standing_in_for_a_real_one(),
        "implementation_plan": ImplementationPlan(
            files_to_change=["src/health.ts"], tests_to_add=["test_health.ts"]
        ),
        "requested_stage": Stage.AWAITING_HUMAN_APPROVAL,
        "requested_agent": None,
        "requested_role": Role.DEV,
        "presented_artifact_id": "VerificationReport",
        "presented_artifact_version": 1,
        "decisions": [],
        "approvals": [],
        WHAT_STOPPED_THIS_RUN: None,
    }

    def a_verifier_whose_new_test_was_never_collected(
        *arguments: object,
    ) -> object:
        raise AnUnrunTestError(
            "The suite passed and never ran 1 of the 1 test(s) this approved plan said the "
            "change adds: test_health.ts. A test file the suite's runner never collects is not a "
            "passing test — it is a file that was never opened."
        )

    the_command = apply_and_verify_in_this_run(  # type: ignore[arg-type]
        a_state, a_verifier_whose_new_test_was_never_collected
    )

    assert isinstance(the_command, Command)
    assert the_command.goto == "let_go_of_the_work_item", (
        "a change that was delivered with its test never collected goes nowhere that can judge it, "
        "and it is the one refusal of the three where the report looks entirely healthy — a reader "
        "of the board sees a green suite and a delivered change, and nothing anywhere says the new "
        "test was never opened. **Through the release first**, because the work item is still held "
        "by the implementer and the agent the supervisor names cannot pick it up from there"
    )
    assert "test_health.ts" in the_command.update[WHAT_STOPPED_THIS_RUN], (
        "the refusal handed over does not name the uncollected test, so the supervisor cannot "
        "tell a test in the wrong directory from a test that was never written"
    )


def test_every_refusal_the_change_can_raise_is_routed_somewhere() -> None:
    """The closed list, checked against the source — because a list nobody checks is a wish.

    **How both of the routing gaps were found, and why this is the only check that could have
    found the second one.** `apply_node`'s `except` held one name, then two, each added by a
    real run that tripped it. That is how the third got in and it cost a run; the pattern is that
    a refusal is discovered by *meeting* it, and the only refusals ever met are the ones a run
    happened to reach. Adding a name per run is a list that grows at the rate runs fail.

    **So the list is read from the source rather than written out again here.** `verify_the_change`
    and `implement_the_plan` are the two modules that can refuse — a green suite that is a lie, a
    change that proves nothing, a change that was never made, a test that was never opened — and
    every `A…Error` they define is a run that stops for a reason a supervisor could have judged.
    A fifth one added to either module without a route is a run that stops on a question this
    system has a reader for, and this says so at the moment it is written rather than twenty
    minutes into a run nobody is watching.

    **Both sides are parsed, not imported, and that is deliberate.** Importing the classes would
    make a test that has to be updated to stay in step with the code, which is the same list
    twice — and the second copy is the one that goes stale quietly. Here a rename or a deletion
    on either side is seen as what it is.
    """
    import ast

    the_modules_that_can_refuse = [
        Path(verify_the_change.__file__),
        Path(implement_the_plan.__file__),
    ]
    routed = _the_refusals_this_node_hands_on()
    every_refusal: set[str] = set()
    for a_module in the_modules_that_can_refuse:
        the_classes = ast.parse(a_module.read_text()).body
        for a_class in the_classes:
            if not isinstance(a_class, ast.ClassDef):
                continue
            if not a_class.name.endswith("Error") or not a_class.name.startswith("A"):
                continue
            if not any(
                isinstance(a_base, ast.Name) and a_base.id == "Exception"
                for a_base in a_class.bases
            ):
                continue
            every_refusal.add(a_class.name)

    assert routed, (
        "no refusal was found on the routing side, so this test is reading nothing and would "
        "report every refusal as unrouted — or worse, pass because the set happened to be empty"
    )

    assert every_refusal, (
        "no refusal was found in either module, so this test is not reading the code it claims to "
        "read and would pass forever"
    )

    unrouted = {
        a_refusal for a_refusal in sorted(every_refusal) if a_refusal not in routed
    }
    assert not unrouted, (
        f"{', '.join(unrouted)} can stop a run and nothing hands it to the supervisor. It is a "
        f"refusal a person could judge, which is the whole reason the supervisor exists, and a "
        f"run that hits it stops instead of asking"
    )


def test_no_node_that_chooses_its_own_destination_still_carries_an_edge() -> None:
    """The rule both broken nodes broke, checked against the graph rather than against either node.

    **Every repair in this system died here, and every refusal-routing test passed.** A node that
    returns `Command(goto=...)` on one outcome and a plain state update on the other, and that
    the graph *also* gives a static edge to, runs both ways in the same step: the run is diverted
    to the supervisor and carries on down the ordinary path, the two arrive at the same node, both
    write `requested_stage`, and LangGraph refuses the run —

        At key 'requested_stage': Can receive only one value per step.

    The refusal was correct, the routing was correct, the supervisor ran, and the run still died at
    the moment the repair was being performed, with a message about concurrent writes rather than
    about the repair. Twelve tests could not see it because they call the function and read the
    `Command`; the defect was entirely in the wiring, and nothing built the graph.

    **Two nodes had the shape, and fixing the first found the second.** The node that implements a
    plan was fixed by running a whole run. The node that delivers a change had the same edge and
    the same `Command`, and was found by reading for the shape afterwards — which is the argument
    for the check being a check and not a habit.

    **So the rule is asserted about the graph's own wiring.** A node whose function can return a
    `Command` must have no `add_edge` out of it, because a node that names its own destination and
    a node that is told its destination are two designs, and a graph holding both cannot say which
    one it meant.
    """
    # **The nodes whose functions return a `Command`, not the nodes they name.** The first
    # version of this check listed the two *destinations* — `write_what_the_change_says` and
    # `mark_the_work_item_delivered` — and failed on `add_edge("write_what_the_change_says",`,
    # which is correct and harmless: a node somebody else sends control to is *supposed* to have
    # an edge out. The node that must not have one is the one that reads the state and decides,
    # because that decision and the edge are two answers to one question.
    # **The third one is the merge, and it arrived for the same reason as the second.** A pull
    # request GitHub will not merge is the only conflict a delivery can reach, and settling it is a
    # node — so the merge node returns a `Command` naming where the run goes on a conflict and where
    # it goes otherwise. It carried an edge out of it for a day, and this check is what says so.
    the_nodes_that_choose_their_own_destination = [
        "make_and_verify_the_change",
        "deliver_this_run",
        "merge_the_delivery_in_this_run",
    ]

    every_node_the_graph_tells_where_to_go = _the_nodes_with_an_edge_out_of_them()

    for a_node in the_nodes_that_choose_their_own_destination:
        assert a_node not in every_node_the_graph_tells_where_to_go, (
            f"`{a_node}` returns a Command naming its own destination, and the graph also carries "
            "an edge out of it. Both fire in the same step, so a run that refuses is diverted to "
            "the supervisor *and* carries on down the ordinary path, and LangGraph refuses it for "
            "writing a state key twice. That is how every repair in this system died while every "
            "routing test passed."
        )

    assert len(the_nodes_that_choose_their_own_destination) == 3, (
        "a fourth node joined this shape and this list has not been updated, so the check now "
        "covers three of the places the defect can sit"
    )


def _the_refusals_this_node_hands_on() -> set[str]:
    """The refusal names this node actually catches, read from its `except` clause and not its text.

    **The first version of this searched `apply_node`'s source for the names and passed — and the
    pass was worth nothing, because the file is mostly prose about refusals.** A name in a comment
    satisfies a regex over the source exactly as well as a name in an `except` clause, and the
    comments in that file name all three refusals while explaining why each one is repairable. So
    the check could not have failed for the reason it exists, which is the worst property a guard
    can have: it looks armed and is not.

    So it parses. The `except` clause is read as what it is — the tuple of names the node catches —
    and anything in a docstring is ignored, which is the whole point.
    """
    the_node = ast.parse(Path(apply_node.__file__).read_text())
    the_names: set[str] = set()
    for a_statement in ast.walk(the_node):
        if not isinstance(a_statement, ast.Try):
            continue
        for a_handler in a_statement.handlers:
            if a_handler.type is None:
                # A bare `except:` catches everything, which is the thing this whole test is
                # about. Recorded as a name that catches nothing in particular, so the assertion
                # below has something true to say about it.
                the_names.add("except:")
                continue
            for a_named in ast.walk(a_handler.type):
                if isinstance(a_named, ast.Name):
                    the_names.add(a_named.id)
    return the_names


def _the_nodes_with_an_edge_out_of_them() -> set[str]:
    """The node names `add_edge` sends control *from*, parsed from the graph rather than its text.

    **This is the same mistake as the `except` guard one commit earlier, in a different file.**
    That check searched `apply_node` for refusal names and passed, because the file is prose about
    refusals and a name in a comment matched as well as a name in a clause. This one searched
    `lifecycle` for `add_edge("<node>",` — and `lifecycle` carries a long comment explaining
    precisely this defect, which quotes the call it forbids. So the guard could not have failed for
    the reason it exists, and it was written a few hours after I had already written down why that
    is the worst property a check can have.

    **The lesson worth keeping is that a guard needs a *negative* case, not just a passing one.**
    Both of these passed. What caught them was deliberately breaking the thing and watching the
    test fail, which is the only thing that distinguishes a check that is armed from one that is
    merely green. Parsing cannot fix that habit — it makes the guard real, and the habit is still
    what catches the next one.

    **And the habit caught a third thing in this very guard, one commit after it was written.**
    This parsed `add_edge`'s first argument as a *string literal*, which is what the two nodes it
    was written for pass. The merge node is `add_edge(WHERE_THE_SUITE_WENT_GREEN,
    WHERE_THE_DELIVERY_WAS_MERGED)` — its arguments are module constants, and a parser that reads
    only literals saw no edge out of the merge node at all. So the edge was added back, on purpose,
    to see whether this would fail: **it did not.** The guard was green on the exact wiring that
    killed every repair in this system, which is worse than not having it, because a green guard is
    read as a checked thing. The names are now resolved through the module's own constants, which
    is the other half of reading the graph rather than its text.
    """
    the_lifecycle = ast.parse(Path(lifecycle_module.__file__).read_text())
    the_names_the_module_uses_for_its_nodes = _the_node_names_the_lifecycle_declares(the_lifecycle)
    the_nodes_with_an_edge_out: set[str] = set()
    for a_statement in ast.walk(the_lifecycle):
        if not isinstance(a_statement, ast.Call):
            continue
        the_name_of_what_was_called = getattr(a_statement.func, "attr", None)
        if the_name_of_what_was_called not in {"add_edge", "add_conditional_edges"}:
            continue
        if not a_statement.args:
            continue
        the_node_it_leaves_from = _the_name_it_leaves_from(
            a_statement.args[0], the_names_the_module_uses_for_its_nodes
        )
        if the_node_it_leaves_from is not None:
            the_nodes_with_an_edge_out.add(the_node_it_leaves_from)
    return the_nodes_with_an_edge_out


def _the_name_it_leaves_from(
    the_first_argument: ast.expr, the_names_the_module_uses: dict[str, str]
) -> str | None:
    """The node name that argument spells, whether it is written out or named by a constant.

    **Both spellings, and the second is what was missing.** `WHERE_THE_SUITE_WENT_GREEN` is how
    this repository writes the node that has to have no edge out of it, so a parser that only reads
    literals cannot see an edge out of it — and the guard that was supposed to stop exactly that
    wiring was green while the edge was there.
    """
    if isinstance(the_first_argument, ast.Constant) and isinstance(the_first_argument.value, str):
        return the_first_argument.value
    if isinstance(the_first_argument, ast.Name):
        return the_names_the_module_uses.get(the_first_argument.id)
    return None


def _the_node_names_the_lifecycle_declares(the_lifecycle: ast.Module) -> dict[str, str]:
    """Every name `lifecycle` uses for one of its nodes, whether it declares it or imports it.

    **Both, and the second is what the first version of this guard missed.** A node name is a
    string, and where the string came from does not change what it is — but `WHERE_THE_SUITE_WENT_
    GREEN` is *imported* from `merge_node`, so resolving only this module's own assignments left
    every edge out of the two nodes that matter invisible to the check. An imported name is read
    from the module that owns it, which is the same import this test already does.
    """
    the_names: dict[str, str] = _the_names_declared_here(the_lifecycle)
    the_names.update(_the_names_imported_from_where_they_are_owned(the_lifecycle))
    return the_names


def _the_names_declared_here(the_lifecycle: ast.Module) -> dict[str, str]:
    """The module-level names whose value is a plain string, which is what a node name is here.

    **A name built by a call or a join is not one this graph declares by hand**, and reading one
    would be reading the module's intent rather than its wiring.
    """
    the_names: dict[str, str] = {}
    for a_statement in the_lifecycle.body:
        if not isinstance(a_statement, ast.Assign) or len(a_statement.targets) != 1:
            continue
        the_target = a_statement.targets[0]
        if not isinstance(the_target, ast.Name) or not isinstance(a_statement.value, ast.Constant):
            continue
        if isinstance(a_statement.value.value, str):
            the_names[the_target.id] = a_statement.value.value
    return the_names


def _the_names_imported_from_where_they_are_owned(the_lifecycle: ast.Module) -> dict[str, str]:
    """Every name this module imports that turns out to be a node name, read from its owner."""
    import importlib

    the_names: dict[str, str] = {}
    for a_statement in the_lifecycle.body:
        if not isinstance(a_statement, ast.ImportFrom) or a_statement.module is None:
            continue
        the_module_it_came_from = importlib.import_module(a_statement.module)
        for an_imported in a_statement.names:
            what_it_holds = getattr(the_module_it_came_from, an_imported.name, None)
            if isinstance(what_it_holds, str):
                the_names[an_imported.asname or an_imported.name] = what_it_holds
    return the_names
