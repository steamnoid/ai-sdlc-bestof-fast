"""Two agents, back to back, asked whether they agree. Everything else is mocked.

**The unit is a pair of neighbours, and the question is whether they contradict each other.**
The stages are consecutive but the data is not: only one pair really hands one agent's artifact to
the next, and three analysis agents re-read the clone independently. So the interesting failure is
not a malformed output — that is what `model_validate` is for — it is **two agents reading the same
repository and telling the reader different things.** Nothing else in this repository can see that,
because every other tier either mocks both sides or runs the whole pipeline and checks only that
the stages completed.

**What is real:** the two agents, on the configured model. **What is mocked:** the clone's origin
(local), git's remotes, the container, GitHub, the supervisor, the register, the project directory
and the graph. Nothing process-wide is opened, which is why the isolation is free here and has to
be maintained everywhere else.

**One pair needs no model at all, and that is the finding.** `inspect_for_security` and `plan` are
neighbours, and the claim in `what_crosses` is that the planner was given the `SecurityReport` it
answers. It was not: `PlanTheChange` takes `(requirements, clone, repository, question)` and the
fourth argument at the call site is `THE_RUNNER_ANNOUNCED_NOTHING_YET`. That is a fact about a
function signature, so it is checked without spending two model calls to discover it.

**Skips loudly.** No credential means this file does nothing, and a green run that never called a
model is a lie told with a tick.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from aisdlc.agents.security_report import SecurityReport
from aisdlc.application.a_run_being_assembled import a_run_of, the_model_this_run_reasons_with
from aisdlc.domain.commissioned_request import a_request_about
from aisdlc.domain.repository import Repository
from aisdlc.tools.github_clone_repository import ClonedRepository
from tests.is_a_named_path_a_file_of_the_clone import (
    how_a_named_path_is_wrong,
    the_paths_named_in,
)
from tests.the_arguments_the_planner_is_handed import the_types_the_planner_is_handed
from tests.the_neighbouring_agent_pairs import (
    THE_NEIGHBOURING_PAIRS,
    ANeighbouringPair,
)
from tests.what_an_artifact_must_have_said import WHAT_EVERY_FINDING_MUST_HAVE_SAID

pytestmark = pytest.mark.e2e

A_REQUEST = a_request_about(
    "a command may only run inside the checkout this run confined itself to"
)


def _every_artifact_text(an_artifact: object) -> list[str]:
    """Every string anywhere in an artifact, because none of these models has a linked field.

    **Deliberately everything rather than one field.** The claims being checked are about whether
    an agent mentioned a file, and an artifact that puts the file in `recommendation` instead of
    `signal` has still mentioned it. A check that read one field would pass on an artifact that
    talked about the file in the next one.
    """
    the_texts: list[str] = []

    def walk(what: object) -> None:
        if isinstance(what, str):
            the_texts.append(what)
        elif isinstance(what, dict):
            for one_value in what.values():
                walk(one_value)
        elif isinstance(what, (list, tuple)):
            for one_item in what:
                walk(one_item)
        elif hasattr(what, "model_dump"):
            walk(what.model_dump())

    walk(an_artifact)
    return the_texts


def _every_path_named_in(texts: list[str]) -> set[str]:
    """Every path either agent cited. The rule is the default tier's, and tested there."""
    return the_paths_named_in(texts)


def _what_is_in_the_clone(a_clone: ClonedRepository) -> set[str]:
    """Every path that exists in the clone, relative to its root."""
    return {
        str(one_path.relative_to(a_clone.path))
        for one_path in a_clone.path.rglob("*")
        if one_path.is_file() and ".git" not in one_path.relative_to(a_clone.path).parts
    }


def _why_there_is_no_model() -> str | None:
    """The setting that is missing, or `None` when a model can be built."""
    try:
        the_model_this_run_reasons_with()
    except Exception as a_problem:
        return str(a_problem)
    return None


def test_the_planner_is_handed_the_security_report_it_is_meant_to_answer() -> None:
    """`SEC` -> `plan`, checked as a type because that is what the claim is about.

    **No model is called here and none is needed.** The claim in `what_crosses` is that the
    planning agent was given the findings its plan answers. What it is handed is declared in one
    alias, `PlanTheChange`, and the declaration says four types and `SecurityReport` is not one
    of them. Read from the alias rather than from a parameter name, because a name is a choice
    and a type is the contract.

    **So this test is red, and it is red on purpose.** Three gates approve a `SecurityReport`,
    the architecture and security analyses are the planner's neighbours in this very list, and
    the planner has never read either. Repairing it is a decision about the pipeline — a planner
    that takes the security report is a different planner — and not something to do by deleting
    the assertion.
    """
    what_the_planner_is_handed = the_types_the_planner_is_handed()

    assert SecurityReport in what_the_planner_is_handed, (
        f"the planner is handed {list(what_the_planner_is_handed)} and a SecurityReport is not "
        "among them, so a plan that ignores the security findings three gates have approved is a "
        "plan nobody was told not to write. This is a decision about the pipeline and not a test "
        "to delete: the planner needs the report as an input."
    )


@pytest.mark.parametrize(
    "a_pair",
    THE_NEIGHBOURING_PAIRS,
    ids=[f"{a_pair.first}_then_{a_pair.second}" for a_pair in THE_NEIGHBOURING_PAIRS],
)
def test_two_neighbouring_agents_do_not_contradict_each_other(
    a_pair: ANeighbouringPair, a_clone_of_this_repository: ClonedRepository
) -> None:
    """Both agents reason for real, on the same clone, and neither names a file absent from it.

    **Two claims, and the second is why this tier exists.** The first is grounding: a path either
    agent names has to be a file of the clone both were shown, so the run cannot reason about a
    repository it has not got. The second is in each pair's `what_crosses`, and it is the one a
    per-agent test cannot make.
    """
    if a_pair.first == "inspect_for_security" and a_pair.second == "plan":
        pytest.skip(
            "this pair's claim is about a function signature rather than about model output, so it "
            "is proven without a model in the test above"
        )

    what_is_missing = _why_there_is_no_model()
    if what_is_missing is not None:
        pytest.skip(f"no model could be built, so no agent ran: {what_is_missing}")

    the_cast = a_run_of(THE_REPOSITORY, the_model=None)
    the_clone = a_clone_of_this_repository

    the_first, the_second = _run_the_pair(a_pair, the_cast, the_clone)

    _what_each_had_to_have_said(the_first, the_cast)
    _what_each_had_to_have_said(the_second, the_cast)

    what_is_in_the_clone = _what_is_in_the_clone(the_clone)
    everything_they_said = _every_artifact_text(the_first) + _every_artifact_text(the_second)

    for a_path in sorted(_every_path_named_in(everything_they_said)):
        what_is_wrong = how_a_named_path_is_wrong(a_path, what_is_in_the_clone)
        if what_is_wrong is None:
            continue
        assert not what_is_wrong.is_in_the_clone, (
            f"{a_pair.first} and {a_pair.second} between them name {a_path!r}, which is not a "
            f"file of the clone — there are {len(what_is_in_the_clone)} files there and "
            f"{what_is_wrong.how}. That is an invented path, and it is the one that matters: a "
            "reader following it arrives nowhere"
        )
        raise AssertionError(
            f"{a_pair.first} and {a_pair.second} between them name {a_path!r}, and the clone "
            f"holds it as {what_is_wrong.how}. So the agent knew the file and wrote a path from "
            "the inside out. **This is carelessness, not invention**, and the two are reported "
            "separately because the remedy differs: a prompt that stops an agent inventing files "
            "will not stop it dropping a directory"
        )

    _what_must_hold_between_them(a_pair, the_first, the_second, what_is_in_the_clone)


THE_REPOSITORY = Repository(owner="steamnoid", name="ai-sdlc-bestof-fast-selfaware")


def _run_the_pair(
    a_pair: ANeighbouringPair, the_cast: object, the_clone: ClonedRepository
) -> tuple:
    """Call the two agents of one pair, in the order the pipeline runs them."""
    if a_pair.first == "discover":
        the_report, _ = the_cast.discover(the_clone, THE_REPOSITORY)
        the_requirements, _ = the_cast.propose_requirements(
            the_clone, THE_REPOSITORY, A_REQUEST
        )
        return the_report, the_requirements

    if a_pair.first == "propose_requirements":
        the_requirements, _ = the_cast.propose_requirements(
            the_clone, THE_REPOSITORY, A_REQUEST
        )
        the_qa_plan, _ = the_cast.plan_the_tests(the_requirements)
        return the_requirements, the_qa_plan

    if a_pair.first == "plan_the_tests":
        the_requirements, _ = the_cast.propose_requirements(
            the_clone, THE_REPOSITORY, A_REQUEST
        )
        the_qa_plan, _ = the_cast.plan_the_tests(the_requirements)
        the_architecture, _ = the_cast.describe_the_architecture(the_clone, THE_REPOSITORY)
        return the_qa_plan, the_architecture

    if a_pair.first == "describe_the_architecture":
        the_architecture, _ = the_cast.describe_the_architecture(the_clone, THE_REPOSITORY)
        the_security = the_cast.inspect_for_security(the_clone, THE_REPOSITORY)
        return the_architecture, the_security

    raise AssertionError(
        f"{a_pair.first} -> {a_pair.second} has no way of being run here, and a pair that cannot "
        "be called is a pair the tier is pretending to cover"
    )


def _what_each_had_to_have_said(the_artifact: object, the_cast: object) -> None:
    """Every finding has to have said something, from the rule the default tier holds them to.

    **Applied per artifact rather than per pair**, because two agents in one pair can each be
    empty and the pair still "agrees" — an empty report and an empty report contradict nothing.
    The rule and the fields it names live in `tests/what_an_artifact_must_have_said.py`, and that
    they name real fields is checked there without a model, so this can be a lookup.
    """
    for a_rule in WHAT_EVERY_FINDING_MUST_HAVE_SAID:
        if not isinstance(the_artifact, a_rule.artifact):
            continue
        what_it_said = [
            getattr(the_artifact, a_field, None) for a_field in a_rule.at_least_one_of
        ]
        if any(a_value and str(a_value).strip() for a_value in what_it_said):
            return
        raise AssertionError(
            f"{a_rule.artifact.__name__} came back with none of "
            f"{list(a_rule.at_least_one_of)} filled in. {a_rule.why_an_empty_one_is_a_fault}"
        )


def _what_must_hold_between_them(
    a_pair: ANeighbouringPair,
    the_first: object,
    the_second: object,
    what_is_in_the_clone: set[str],
) -> None:
    """The claim that pair declares, checked against the two artifacts it produced."""
    if a_pair.first == "discover":
        # **This pair's claim is the grounding check above, and saying so is the whole answer.**
        # Nothing crosses between these two agents: the product analyst is handed the clone and
        # the request, not the DiscoveryReport. So there is nothing to compare and the thing worth
        # asserting is the one the pair is named for — that neither of them spoke about a file
        # neither was shown — which the caller has already done for both artifacts at once.
        return

    if a_pair.first == "propose_requirements":
        the_criteria = list(getattr(the_first, "acceptance_criteria", []) or [])
        the_scenarios = " ".join(_every_artifact_text(the_second))
        for a_criterion in the_criteria:
            assert any(
                a_word in the_scenarios.lower() for a_word in _the_words_of(a_criterion)
            ), (
                f"criterion {a_criterion!r} has nothing behind it in the QA plan. The product "
                "analyst set it and the QA analyst planned tests, and this is the one pair where "
                "one agent's artifact really is the next agent's input"
            )
        return

    if a_pair.first == "plan_the_tests":
        the_modules = " ".join(getattr(the_first, "modules", []) or []).lower()
        assert the_modules, (
            "the architecture report names no modules, so there is nothing for the QA plan's "
            "scenarios to agree or disagree with. A report that lists nothing agrees with "
            "everything, which is the same as saying nothing — and it is the reason a pair test "
            "needs a claim about emptiness as well as a claim about contradiction"
        )
        for a_path in sorted(_every_path_named_in(_every_artifact_text(the_second))):
            assert a_path.lower() in the_modules or Path(a_path).name.lower() in the_modules, (
                f"{a_path!r} is in the architecture report but the QA plan was already planning "
                f"tests against it, and the architecture report does not mention it in its "
                f"modules ({the_modules!r}). Two agents read the same clone and only one of them "
                "saw the thing the other was working on"
            )
        return

    if a_pair.first == "describe_the_architecture":
        the_modules = " ".join(getattr(the_first, "modules", []) or []).lower()
        for a_finding in getattr(the_second, "findings", []) or []:
            for a_path in sorted(_every_path_named_in([a_finding.signal, a_finding.statement])):
                assert a_path.lower() in the_modules or Path(a_path).name.lower() in the_modules, (
                    f"the security analyst raised a finding about {a_path!r} and the "
                    "architecture report does not list it as a module, so the two disagreed about "
                    "what is in the repository rather than about whether it is safe"
                )
        return

    raise AssertionError(
        f"{a_pair.first} -> {a_pair.second} declares what must cross between its two agents and "
        "nothing here checks it, so the pair runs two models and asserts nothing about them"
    )


def _the_words_of(a_sentence: str) -> list[str]:
    """The words worth looking for: long enough not to match by accident."""
    return re.findall(r"[a-zA-Z]{5,}", a_sentence.lower())
