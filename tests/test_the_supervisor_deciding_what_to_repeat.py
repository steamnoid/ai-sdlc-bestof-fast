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

from datetime import UTC, datetime
from pathlib import Path

import pytest
from langgraph.types import Command

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

    assert the_command.goto == "supervise_a_repair", (
        "a red suite went to a node other than the supervisor, so nothing in this run could judge "
        "whether the change or the plan was wrong — which is the only question a red suite poses"
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
        delivery=None,  # type: ignore[arg-type]
    )

    assert "begin_delivering_the_work_item" in the_registered_names, (
        f"the graph registers {the_registered_names}, and the routing this file checks belongs to "
        "a node that is not among them — so the check is about a function nothing calls"
    )
