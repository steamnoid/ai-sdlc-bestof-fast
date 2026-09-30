"""One run from an empty register to a delivered pull request, and a board that shows it.

**This is the whole product in one test, and it is the only test in the repository.** It exists
because the two projects this was assembled from each had half of it and neither had the whole:
one had a board over a store that nothing ever wrote, and the other had a pipeline that only
`pytest -m e2e` could start. So the question this file answers is the only one worth asking at
first — *does starting a run work, and does what comes out look right?*

**A real clone, a real state machine, real gates, a real register, a real HTTP request.** Four
things are replaced and each is named below. Everything else is production code on its real path,
because the parts being replaced are the parts that need a network and a model, and the parts
that are *not* replaced are exactly the ones this product is a claim about: that a work item
cannot be moved illegally, that a gate suspends, that a decision reaches the board only through
the gate, and that a run which delivered says so in a column.

**A local bare repository rather than a fixture for the clone.** `git clone /some/path` needs no
network and is the same code that clones from GitHub, so the clone, the branch and the checkout
are genuinely exercised. A doubled clone would have left the most expensive step in the pipeline
unproven and made this file much shorter, which is not the same as better.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aisdlc.agents.apply_the_plan import ADeliveredChange
from aisdlc.agents.architecture_report import ArchitectureReport
from aisdlc.agents.architecture_report_answer import ArchitectureReportAnswer
from aisdlc.agents.discovery_answer import DiscoveryAnswer
from aisdlc.agents.discovery_report import DiscoveryReport, EvidenceFile
from aisdlc.agents.implement_the_plan import FileToWrite
from aisdlc.agents.implementation_plan import ImplementationPlan
from aisdlc.agents.qa_plan import QaPlan
from aisdlc.agents.qa_plan_answer import QaPlanAnswer
from aisdlc.agents.requirements import Requirements
from aisdlc.agents.requirements_answer import RequirementsAnswer
from aisdlc.agents.security_report import SecurityReport
from aisdlc.agents.verification_report import VerificationReport
from aisdlc.agents.what_an_agent_judged import WhatAnAgentJudged
from aisdlc.agents.what_the_planner_concluded import ImplementationPlanAnswer
from aisdlc.application.the_runs_this_process_is_holding import TheRunsThisProcessIsHolding
from aisdlc.domain.repository import Repository
from aisdlc.domain.stage import Stage
from aisdlc.graph.lifecycle import the_lifecycle
from aisdlc.graph.the_agents_this_run import TheAgentsThisRun
from aisdlc.graph.the_delivery_of_this_run import TheDeliveryOfThisRun
from aisdlc.store.the_board_reads import AColumnOfTheBoard
from aisdlc.store.the_register_of_work_items import the_work_item_registered_at
from aisdlc.store.where_the_register_lives import the_register_lives_at
from aisdlc.tools.github_client import Addresses
from aisdlc.tools.github_clone_repository import RepositoryToClone
from aisdlc.tools.github_create_branch import PushedBranch
from aisdlc.tools.github_create_pull_request import AnOpenedPullRequest
from aisdlc.tools.run_tests import SuiteOutcome
from aisdlc.web.the_api import the_api_over

A_REPOSITORY = Repository(owner="pikuniu", name="a-project")
A_MOMENT = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
HOW_LONG_A_SMOKE_MAY_WAIT_IN_SECONDS = 30.0


# ---------------------------------------------------------------------------
# A real repository, made locally, because the clone is the step worth proving.
# ---------------------------------------------------------------------------


@pytest.fixture
def a_repository_to_clone_into(tmp_path: Path) -> Path:
    """A bare repository with one commit in it, on this machine, reachable by `git clone`.

    **A real `git init`, a real commit and a real bare remote.** The run under test then clones
    it with the same `git clone` it would use for a public repository, which means the expensive
    step is exercised rather than stubbed — and the test needs no network, no credential and no
    fixture that lies about what a clone is.
    """
    the_bare = tmp_path / "the-origin.git"
    the_bare.mkdir()
    _git(the_bare, "init", "--bare", "--initial-branch=main")

    a_working_copy = tmp_path / "a-working-copy"
    a_working_copy.mkdir()
    _git(a_working_copy, "init", "--initial-branch=main")
    _git(a_working_copy, "config", "user.email", "a-run@example.com")
    _git(a_working_copy, "config", "user.name", "a run")
    (a_working_copy / "README.md").write_text("# a project\n", encoding="utf-8")
    (a_working_copy / "test_thing.py").write_text(
        "def test_the_thing():\n    assert True\n", encoding="utf-8"
    )
    _git(a_working_copy, "add", ".")
    _git(a_working_copy, "commit", "-m", "the first commit")
    _git(a_working_copy, "remote", "add", "origin", str(the_bare))
    _git(a_working_copy, "push", "origin", "main")

    return the_bare


def _git(where: Path, *what: str) -> str:
    """One `git` call in one directory, and its output if it failed.

    **Loud rather than quiet**, because a clone that failed for a reason nobody read is the
    exact shape of a test that passes for the wrong reason — the assertion after it never runs.
    """
    what_happened = subprocess.run(
        ["git", *what], cwd=where, capture_output=True, text=True, check=False
    )
    if what_happened.returncode != 0:
        pytest.fail(f"git {' '.join(what)} in {where} failed: {what_happened.stderr}")
    return what_happened.stdout


# ---------------------------------------------------------------------------
# The four things this test replaces, and one line each saying which.
# ---------------------------------------------------------------------------


def _the_agents_no_model_would_produce() -> TheAgentsThisRun:
    """Every agent answered without a model, which is the first of the four replacements.

    **The seven seams are the production seams, in the production shapes.** Each is a plain
    callable taking the same arguments the real agent takes, and each returns the same
    `(artifact, answer)` pair — so the graph is handed exactly what a real run hands it, and the
    only thing missing is the reasoning. What the run *does* with the answer: the gate, the
    record, the board, the delivery, is entirely production code.

    **Every answer carries a `judged`**, because that is where the note a person reads on the
    card comes from. An agent that returned an artifact with no judgement would leave a card with
    no note on it, and the board would show a run that produced artifacts and never said what it
    concluded about them.
    """
    the_judged = WhatAnAgentJudged(
        what_it_found="one commit and one test",
        what_it_could_not_settle="whether the database is reachable in production",
        what_it_expects_next="the next agent reads what this one found",
    )

    def discover(clone, repository) -> tuple[DiscoveryReport, DiscoveryAnswer]:
        # **The answer holds paths and the report holds links, and that is the production split.**
        # A model is given the paths it concluded something from and the address is derived from
        # the repository, because a model asked for a link will name a host it likes. So the fake
        # answers in paths and builds the report the way the real node does.
        the_paths = ["README.md", "test_thing.py"]
        return (
            DiscoveryReport(
                languages=["Python"],
                architecture_summary="a single module and a test beside it",
                key_components=["test_thing.py"],
                evidence_files=[
                    EvidenceFile(path=a_path, link=f"local://{repository.address}/{a_path}")
                    for a_path in the_paths
                ],
            ),
            DiscoveryAnswer(
                languages=["Python"],
                architecture_summary="a single module and a test beside it",
                key_components=["test_thing.py"],
                evidence_files=the_paths,
                judged=the_judged,
            ),
        )

    def propose_requirements(
        clone, repository, requested
    ) -> tuple[Requirements, RequirementsAnswer]:
        the_found = {
            "requirements": ["an unauthenticated health endpoint"],
            "acceptance_criteria": ["the suite's file count goes up by one"],
        }
        return (
            Requirements(**the_found),
            RequirementsAnswer(judged=the_judged, **the_found),
        )

    def plan_the_tests(requirements) -> tuple[QaPlan, QaPlanAnswer]:
        the_found = {
            "test_strategy": "run the suite and count the files it collects",
            "scenarios": ["a call to the health endpoint answers"],
        }
        return QaPlan(**the_found), QaPlanAnswer(judged=the_judged, **the_found)

    def describe_the_architecture(
        clone, repository
    ) -> tuple[ArchitectureReport, ArchitectureReportAnswer]:
        the_found = {
            "findings": ["one module, no boundaries drawn yet"],
            "modules": ["test_thing.py"],
            "boundaries": ["the endpoint and the thing it reports on"],
        }
        return (
            ArchitectureReport(**the_found),
            ArchitectureReportAnswer(judged=the_judged, **the_found),
        )

    def inspect_for_security(clone, repository) -> SecurityReport:
        # **An account and no finding, never an empty report.** A report with neither is refused
        # by the artifact's own rule, because a reader cannot tell a repository that was
        # examined and found clean from one no analyst ever looked at.
        return SecurityReport(
            nothing_found_because="one commit of markdown and one trivial test"
        )

    def plan(
        requirements, clone, repository, what_the_suite_announced=""
    ) -> ImplementationPlanAnswer:
        return ImplementationPlanAnswer(
            judged=the_judged,
            plan=ImplementationPlan(
                files_to_add=["health.py"],
                tests_to_add=["test_health.py"],
            ),
        )

    def apply_and_verify(clone, repository, implementation_plan) -> ADeliveredChange:
        a_suite_that_passed = SuiteOutcome(
            exit_code=0,
            passed=True,
            dependencies_installed=True,
            output="1 passed",
        )
        return ADeliveredChange(
            written=[
                FileToWrite(
                    path="health.py", content="def health():\n    return {'ok': True}\n"
                )
            ],
            verification=VerificationReport(
                suite_before_the_change=a_suite_that_passed,
                suite_after_the_change=a_suite_that_passed,
            ),
            what_the_implementer_said="added the endpoint the requirements asked for",
        )

    def supervise(what_the_run_stopped_on) -> object:
        pytest.fail(
            f"the supervisor was asked about {what_the_run_stopped_on!r} on a run whose stages "
            "never refuse, so a repair here means something upstream is broken and the run "
            "should have carried on"
        )

    return TheAgentsThisRun(
        discover=discover,
        propose_requirements=propose_requirements,
        plan_the_tests=plan_the_tests,
        describe_the_architecture=describe_the_architecture,
        inspect_for_security=inspect_for_security,
        plan=plan,
        apply_and_verify=apply_and_verify,
        supervise=supervise,
    )


def _a_delivery_that_only_writes_down(clone_path: Path) -> TheDeliveryOfThisRun:
    """The second replacement: a delivery that reports what it would have done.

    **A `PushedBranch` and an `AnOpenedPullRequest` with real numbers.** The graph's delivery node
    decides *whether* to deliver and asks these two collaborators to do it; what they do is a
    network call. So they are the seam, and the decision — the last gate, the refusal check, the
    move to `DONE` — is production code being tested.
    """
    return TheDeliveryOfThisRun(
        our_copy=A_REPOSITORY,
        push_the_branch=lambda the_clone, name: PushedBranch(
            name=name, address=f"local://{clone_path}/branch/{name}"
        ),
        open_the_pull_request=lambda what_to_open: AnOpenedPullRequest(
            number=1, address="https://example.invalid/paligakrzychu/a-project/pull/1"
        ),
    )


def _cloning_from_a_local_repository(the_bare: Path):
    """The third replacement: clone from a path on this machine instead of from GitHub.

    **A real `git clone` of a real repository.** The only thing changed is the address, which is
    the one field `Addresses` exists to vary — fetched from somewhere writable, the code came
    from somewhere readable. Everything the clone node does around it is production code.
    """

    def planning(source: Repository, into: Path) -> RepositoryToClone:
        return RepositoryToClone(
            repository=source,
            addresses=Addresses(
                fetch_from=str(the_bare), origin_of_the_code=str(the_bare)
            ),
            into=into,
        )

    return planning


# ---------------------------------------------------------------------------
# The run, and the board it has to end up on.
# ---------------------------------------------------------------------------


@pytest.fixture
def a_register_and_a_projects_root(tmp_path: Path, monkeypatch) -> tuple[sqlite3.Connection, Path]:
    """An empty register and a projects root, with the process told where both are.

    **`the_register_lives_at` rather than a connection threaded through everything.** The graph's
    nodes are handed the state and nothing else, so the connection cannot travel in the state
    without putting a database cursor in a `TypedDict` of domain values. The composition root
    opens it once and the recorders read it, which is the same door the board reads.
    """
    monkeypatch.setenv("AISDLC_PROJECTS_DIR", str(tmp_path / "projects"))
    the_register_lives_at(tmp_path / "the-register.sqlite3")
    return _the_open_register(), tmp_path / "projects"


def _the_open_register() -> sqlite3.Connection:
    from aisdlc.store.where_the_register_lives import the_register

    return the_register()


def test_a_run_started_from_the_board_reaches_delivered(
    a_repository_to_clone_into: Path, a_register_and_a_projects_root, tmp_path: Path
) -> None:
    """A person posts a repository and a sentence, answers eight gates, and gets a pull request.

    **The whole product, and the eight gates are answered one at a time on purpose.** A run
    answered by a policy never suspends, so a smoke test that approved everything at once would
    never reach a board showing a card waiting for somebody — and that card is the thing this
    repository is for. So each answer is posted, and between two of them the board is read to
    prove the run is standing at a gate rather than past it.
    """
    _, the_projects_root = a_register_and_a_projects_root
    os.environ["AISDLC_PROJECTS_DIR"] = str(the_projects_root)

    the_runs = _the_runs_holding_a_run_built_out_of_fakes(a_repository_to_clone_into)
    with TestClient(the_api_over(_the_open_register(), the_runs)) as the_board:
        started = the_board.post(
            "/api/runs",
            json={
                "repository_owner": A_REPOSITORY.owner,
                "repository_name": A_REPOSITORY.name,
                "asked_for": "add a health endpoint that answers",
            },
        )

        assert started.status_code == 200, started.text
        the_work_item_id = started.json()["work_item_id"]

        # **A card exists before the run has done anything.** A request that returned after four
        # minutes of cloning would be indistinguishable from a request the server dropped.
        the_first_reading = the_board.get("/api/board").json()
        assert [a_card["work_item_id"] for a_card in the_first_reading["cards"]] == [
            the_work_item_id
        ], (
            "a card has to be on the board the moment the request is accepted, not when the "
            "run reaches a gate"
        )

        already_answered: set[str] = set()
        for gate in range(1, _how_many_gates_there_are() + 1):
            question = _wait_until_the_gate_is_asking(
                the_board, the_work_item_id, already_answered
            )
            already_answered.add(question["artifact_id"])

            answered = the_board.post(
                f"/api/runs/{the_work_item_id}/decisions",
                json={
                    "approved": True,
                    "decided_by": "pikuniu",
                    "reason": "it answers the request",
                },
            )
            assert answered.status_code == 200, (
                f"gate {gate} refused the answer: {answered.text}"
            )

        _wait_until_the_run_has_finished(the_board, the_work_item_id)

    # **The card is in the delivered column, and it is the only card.** Six stages, eight gates,
    # one pull request — and a board that showed anything else would be showing a second source
    # of truth.
    the_cards = the_board.get("/api/board").json()["cards"]
    assert len(the_cards) == 1, f"a run should have left one card and left {len(the_cards)}"
    the_card = the_cards[0]

    assert the_card["column"] == AColumnOfTheBoard.DELIVERED.value, (
        f"the card is in {the_card['column']!r} rather than delivered, at stage "
        f"{the_card['stage']!r}"
    )
    assert the_card["stage"] == Stage.DONE.name
    assert the_card["how_many_gates_it_has_been_through"] == 8, (
        "eight gates, and a run that recorded a different number answered a different number of "
        "them — the card is counting decisions, so this is a fact and not a display"
    )

    # **The work item really is at `DONE`, read back out of the register.** The card is a
    # projection; this is the fact it projects. A card saying "delivered" over a work item at
    # `AWAITING_HUMAN_APPROVAL` is the exact shape of bug this store was written to make
    # impossible, and reading it back is the cheapest way to be sure it is not happening.
    the_registered = the_work_item_registered_at(_the_open_register(), the_work_item_id)
    assert the_registered.stage is Stage.DONE, (
        f"the board says delivered and the register holds {the_registered.stage.name}. Two "
        "records of one run, telling two stories, is the failure this whole store exists to "
        "prevent — so this reads the register and not the card"
    )

    the_story = the_board.get(f"/api/runs/{the_work_item_id}").json()
    assert len(the_story["gates"]) == 8
    assert len(the_story["approvals"]) == 8, (
        "an approved gate leaves a record and a refused one does not, so eight approvals for "
        "eight answers is what an entirely approved run looks like"
    )
    assert all(a_gate["approved"] for a_gate in the_story["gates"])
    assert the_story["how_it_ended"] is None, (
        "this run delivered, so there is nothing to report about how it stopped"
    )
    assert any(
        "https://example.invalid" in a_line["what_happened"] for a_line in the_story["what_it_said"]
    ), "the address of the pull request has to reach the card — it is the run's whole output"


def test_a_refusal_ends_a_run_and_leaves_the_reason_on_the_card(
    a_repository_to_clone_into: Path, a_register_and_a_projects_root
) -> None:
    """Saying no at the second gate stops the run, and the card says who said it and why.

    **A refusal is a decision and not a gap**, so this asserts two things a run that merely
    stopped would fail: the decision is on the record, and no approval exists for it. A board
    built from approvals alone cannot show a gate somebody answered no to, which is the ordinary
    case rather than the rare one.
    """
    _, the_projects_root = a_register_and_a_projects_root
    os.environ["AISDLC_PROJECTS_DIR"] = str(the_projects_root)

    the_runs = _the_runs_holding_a_run_built_out_of_fakes(a_repository_to_clone_into)
    with TestClient(the_api_over(_the_open_register(), the_runs)) as the_board:
        started = the_board.post(
            "/api/runs",
            json={
                "repository_owner": A_REPOSITORY.owner,
                "repository_name": A_REPOSITORY.name,
                "asked_for": "add a health endpoint that answers",
            },
        )
        the_work_item_id = started.json()["work_item_id"]

        _wait_until_the_gate_is_asking(the_board, the_work_item_id, set())
        the_board.post(
            f"/api/runs/{the_work_item_id}/decisions",
            json={"approved": True, "decided_by": "pikuniu", "reason": "it is right"},
        )

        # **The set of gates this test has answered, and not the set the record holds.** The
        # record is written by the run's own thread, so a set read from it at the moment of the
        # wait can be a gate behind: the answer was posted and the run has not recorded it yet,
        # so the set is empty, the pending question is gate one, and the wait returns at once on
        # a question the run is about to clear. The test knows what it posted, and that is a
        # fact about the test rather than a fact about a race.
        already_answered: set[str] = set()
        first = _wait_until_the_gate_is_asking(the_board, the_work_item_id, already_answered)
        already_answered.add(first["artifact_id"])
        the_board.post(
            f"/api/runs/{the_work_item_id}/decisions",
            json={"approved": True, "decided_by": "pikuniu", "reason": "it is right"},
        )

        _wait_until_the_gate_is_asking(the_board, the_work_item_id, already_answered)
        refused = the_board.post(
            f"/api/runs/{the_work_item_id}/decisions",
            json={
                "approved": False,
                "decided_by": "pikuniu",
                "reason": "that is not the change I meant to ask for",
            },
        )
        assert refused.status_code == 200, (
            f"a refusal is a completed gate, not an error: {refused.text}"
        )

        # **Wait for the refusal to reach the record, rather than reading on the strength of the
        # 200.** The answer is handed to a thread, and the thread is what writes it down; a test
        # that read immediately would be asserting about a run that had not finished reacting,
        # and it would pass or fail on how fast the machine is.
        _wait_until(
            lambda: len(the_board.get(f"/api/runs/{the_work_item_id}").json()["gates"]) == 2,
            f"the refusal at the second gate never reached the record on {the_work_item_id}",
        )

    the_story = the_board.get(f"/api/runs/{the_work_item_id}").json()

    assert len(the_story["gates"]) == 2
    assert len(the_story["approvals"]) == 1, (
        "a refusal leaves a decision and no approval, so one approval for two answers is what "
        "being refused looks like — a run that recorded two would be claiming a record exists "
        "for a decision that did not approve anything"
    )
    assert the_story["gates"][-1]["approved"] is False
    assert the_story["gates"][-1]["reason"] == "that is not the change I meant to ask for"

    the_card = the_story["card"]
    assert the_card["why_it_was_refused"] == "that is not the change I meant to ask for"
    assert the_card["who_refused_it"] == "pikuniu", (
        "the record names who decided, verbatim. A record naming anybody else is a forged audit "
        "trail and it looks exactly like the real thing at the moment somebody needs to tell "
        "them apart"
    )
    assert the_card["stage"] == Stage.AWAITING_HUMAN_APPROVAL.name, (
        "a refused run is left where it was refused, so a person can see it. A run that carried "
        "on would be doing the work anyway, and one that moved to DONE would be claiming a "
        "delivery nobody approved"
    )


def test_an_agent_may_not_answer_its_own_gate(
    a_repository_to_clone_into: Path, a_register_and_a_projects_root
) -> None:
    """An `aisdlc-` identifier posted as a decider is refused with the gate's own sentence.

    **The prohibition is an assertion and not a convention.** §11 forbids an agent approving an
    agent's output, and a boundary enforced only by a naming convention is a boundary the next
    agent written will cross. The `AgentDecidedError` exists to be raised, and this is where.
    """
    _, the_projects_root = a_register_and_a_projects_root
    os.environ["AISDLC_PROJECTS_DIR"] = str(the_projects_root)

    the_runs = _the_runs_holding_a_run_built_out_of_fakes(a_repository_to_clone_into)
    with TestClient(the_api_over(_the_open_register(), the_runs)) as the_board:
        started = the_board.post(
            "/api/runs",
            json={
                "repository_owner": A_REPOSITORY.owner,
                "repository_name": A_REPOSITORY.name,
                "asked_for": "add a health endpoint that answers",
            },
        )
        the_work_item_id = started.json()["work_item_id"]
        _wait_until_the_gate_is_asking(the_board, the_work_item_id, set())

        the_answer = the_board.post(
            f"/api/runs/{the_work_item_id}/decisions",
            json={
                "approved": True,
                "decided_by": "aisdlc-po-analyze",
                "reason": "I approved my own work",
            },
        )

    assert the_answer.status_code == 400
    assert "only a human" in the_answer.json()["detail"], (
        "the refusal has to reach a person as a sentence about the rule, not as a line number in "
        "a validation error — a browser shows this text and nobody is going to read a stack"
    )


# ---------------------------------------------------------------------------
# Waiting for a run, which is minutes of real work and must not be a fixed sleep.
# ---------------------------------------------------------------------------


def _the_runs_holding_a_run_built_out_of_fakes(
    the_bare: Path,
) -> TheRunsThisProcessIsHolding:
    """A holder whose runs are the real graph, the real clone and seven agents that did not ask.

    **The composition root is replaced and the graph is not.** `the_lifecycle` is the production
    wiring — every node, every edge, the router, the state machine, the gate, the delivery node —
    and this hands the holder a graph built by that function. What is replaced is the cast of
    agents and the two delivery collaborators, and the address the clone is fetched from.

    That split is the whole claim of this file: the pipeline is the product, and the pipeline is
    production code. A test that replaced the graph would be testing its own fakes, and a test
    that needed a credential would be testing that a deployment is configured.
    """
    from aisdlc.application.the_runs_this_process_is_holding import TheRunsThisProcessIsHolding

    def building_the_graph(source: Repository, the_model: object = None) -> object:
        return the_lifecycle(
            agents=_the_agents_no_model_would_produce(),
            delivery=_a_delivery_that_only_writes_down(the_bare),
            plan_the_clone=_cloning_from_a_local_repository(the_bare),
        )

    return TheRunsThisProcessIsHolding(build_the_graph=building_the_graph)


def _how_many_gates_there_are() -> int:
    """How many times a person is asked, read off the router rather than written down here.

    **Read from the code so the number cannot go stale.** A hard-coded eight would keep passing
    if a stage were added, and the test that is supposed to prove a run reached the end would
    instead be waiting at a gate for a ninth answer that never comes.
    """
    from aisdlc.graph.router import WHERE_AN_APPROVED_ARTIFACT_LEADS

    return len(WHERE_AN_APPROVED_ARTIFACT_LEADS)


def _wait_until_the_gate_is_asking(
    the_board: TestClient, work_item_id: str, already_answered: set[str]
) -> dict[str, object]:
    """Wait for the board to ask about an artifact nobody has answered yet.

    **"Not answered yet" and not simply "asking", and the difference is a race this test lost
    once.** The graph clears a question when it records the answer, which happens *after* this
    endpoint's response has already gone back. So a poll for "is it asking" answers yes with
    the question it was just given permission to stop asking — and the assertion two lines later
    finds nothing. A gate list is what makes the wait a fact: the question has to be about
    something no decision names yet.
    """
    return _wait_until(
        lambda: _a_question_nobody_has_answered(the_board, work_item_id, already_answered),
        f"{work_item_id} never reached a gate that was still waiting",
    )


def _a_question_nobody_has_answered(
    the_board: TestClient, work_item_id: str, already_answered: set[str]
) -> dict[str, object] | None:
    """The pending question, or `None` while the one before it is still being cleared."""
    the_question = the_board.get(f"/api/runs/{work_item_id}").json()["the_question"]
    if the_question is None or the_question["artifact_id"] in already_answered:
        return None
    return the_question


def _wait_until_the_run_has_finished(the_board: TestClient, work_item_id: str) -> None:
    """Wait for the run to stop asking, which is how both delivering and refusing end."""
    _wait_until(
        lambda: the_board.get(f"/api/runs/{work_item_id}").json()["the_question"] is None,
        f"{work_item_id} was still asking questions when the test gave up",
    )


def _wait_until(what_to_read, what_to_say_when_it_never_became_true: str):
    """One fact, polled, with a ceiling — the ceiling is a backstop and not the mechanism.

    **Polling a fact rather than sleeping a duration.** A fixed sleep is either too short, and
    the test fails for having been impatient, or too long, and it is paid on every run. This
    looks at the one thing it is waiting for, so it is as fast as the run and no slower — and it
    hands back what it read, so a caller that needed the value does not read it a second time
    and race itself.
    """
    how_long_it_has_waited = 0.0
    while how_long_it_has_waited < HOW_LONG_A_SMOKE_MAY_WAIT_IN_SECONDS:
        what_it_says = what_to_read()
        if what_it_says:
            return what_it_says
        time.sleep(0.1)
        how_long_it_has_waited += 0.1
    pytest.fail(
        f"{what_to_say_when_it_never_became_true}, after {HOW_LONG_A_SMOKE_MAY_WAIT_IN_SECONDS}s"
    )
