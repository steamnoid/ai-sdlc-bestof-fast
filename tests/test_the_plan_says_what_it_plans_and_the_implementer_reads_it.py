"""A plan cannot say what it plans, and the implementer is given nothing else.

**`the_prompt_to_implement(plan, clone, what_was_wrong)` receives a plan and a checkout.** Not the
request, not the requirements, not the security report — three artifacts this run produced and
filed, none of which reach the agent that does the work. So the plan's five path lists are the whole
of what the implementer knows about *what* to build.

**And the plan is five path lists.** `files_to_change`, `files_to_add`, `tests_to_add`,
`dependencies`, `migrations`. There is nowhere in it to say what the change is for.

**A real policy refused a real plan for exactly that**, and its words are the finding:

> What I looked at is a bare manifest: two paths in files_to_change, the same new path repeated in
> files_to_add and tests_to_add, and empty dependencies/migrations — with no statement of the
> trust-boundary rule to be enforced in run_command.py, no steps or rationale, no test cases, and
> no indication of what the existing run_command.py and the surrounding test conventions look
> like, **so nothing here tells an implementer what 'enforce the trust boundary' actually
> requires.**

**The policy and the implementer were looking at the same artefact and reaching the same
conclusion from opposite sides**: one said a person cannot approve it, the other cannot act on it.

This is the same defect as the first real run's, read from the other end. That run's implementer
read only `files_to_change` and wrote a plan with no implementation behind it — because a plan of
paths carries no statement of what the implementation is for.

**The statement is not decoration, and that is what the first test holds.** A field nothing reads
is an ornament, and an ornament on a gate's artefact is worse than its absence: a reviewer reading
`the_change_it_makes` would take it for the plan's reasoning.
"""

from __future__ import annotations

from pathlib import Path

from aisdlc.agents.implement_the_plan import the_prompt_to_implement
from aisdlc.agents.implementation_plan import EmptyPlanError, ImplementationPlan
from aisdlc.domain.commissioned_request import CommissionedRequest
from aisdlc.tools.github_clone_repository import ClonedRepository

AN_INVARIANT_THE_CHANGE_ENFORCES = (
    "a command may run only inside the checkout this run cloned, and a directory outside it is a "
    "raised error rather than an outcome value"
)


def _a_clone() -> ClonedRepository:
    return ClonedRepository(path=Path(__file__).resolve().parents[1], ref="main", commit="0" * 40)


def test_the_implementer_is_told_what_the_plan_changes() -> None:
    """The plan's own words reach the agent that does the work.

    **This is the assertion that makes the field real.** Everything else — the model, the prompt,
    the glossary — follows from this one: a field nothing reads is an ornament on a gate's
    artefact, and a reviewer reading it would take it for the plan's reasoning.
    """
    a_plan_that_says_what_it_does = ImplementationPlan(
        files_to_change=["src/aisdlc/tools/run_command.py"],
        the_change_it_makes=AN_INVARIANT_THE_CHANGE_ENFORCES,
    )

    the_question_put_to_the_model = the_prompt_to_implement(
        a_plan_that_says_what_it_does, _a_clone()
    )

    assert AN_INVARIANT_THE_CHANGE_ENFORCES in the_question_put_to_the_model, (
        "the plan says what the change makes and the implementer's question does not contain it. "
        "The implementer is given the plan and a checkout and nothing else — no request, no "
        "requirements — so a statement the prompt drops is a statement nobody reads, and the "
        "implementer writes the file from the path alone"
    )


def test_the_planner_is_asked_for_the_statement() -> None:
    """A field the planner is never told about is a field the model leaves empty.

    **Asserted rather than assumed, because nothing else notices.** The plan is filled by the
    model directly — `ImplementationPlanAnswer` holds an `ImplementationPlan` — so a field it is
    never asked about comes back empty, passes every rule here, and reaches a gate as a blank.
    """
    from aisdlc.agents.plan_the_change import the_prompt_to_plan_a_change

    the_question_put_to_the_planner = the_prompt_to_plan_a_change(
        _requirements_the_planner_is_handed(),
        _a_security_report(),
        _an_inspection_that_says_what_this_repository_is(),
        _the_repository(),
    )

    assert "the_change_it_makes" in the_question_put_to_the_planner, (
        "the planner is never told the plan has a field saying what the change makes, so the model "
        "leaves it empty and the gate reads a blank where the reasoning should be"
    )


def test_a_statement_with_no_path_is_not_a_plan() -> None:
    """Saying what the change does is not the same as saying what to change.

    **The rule keeps its shape, and this is why.** The emptiness rule asks whether a plan says
    anything *to do*; a sentence about intent with no file named cannot be implemented by anyone,
    so it does not become a way to pass the rule. This is the other half of the field not being an
    ornament — it has to earn its place rather than become a loophole.

    **And the field's existence is asserted first, because this test would otherwise pass for the
    wrong reason.** Pydantic ignores an unknown keyword, so before the field exists this
    construction is the same as an empty plan and the refusal it hits has nothing to do with the
    statement. A test that can pass because the thing it is about is absent is a test that reports
    success while the defect is still there.
    """
    assert "the_change_it_makes" in ImplementationPlan.model_fields, (
        "the plan has no field saying what the change makes, so this test would otherwise be "
        "exercising the emptiness rule with a keyword Pydantic silently discards"
    )

    try:
        ImplementationPlan(the_change_it_makes=AN_INVARIANT_THE_CHANGE_ENFORCES)
    except EmptyPlanError:
        return

    raise AssertionError(
        "a plan that says what the change makes and names no file was accepted. The statement is "
        "for the implementer to act on, and there is nothing to act on"
    )


def _requirements_the_planner_is_handed() -> object:
    from aisdlc.agents.requirements import Requirements

    return Requirements(
        requirements=["run_command may run only inside the checkout"],
        acceptance_criteria=["a path outside the root is refused"],
    )


def _a_security_report() -> object:
    from aisdlc.agents.security_report import SecurityReport

    return SecurityReport(nothing_found_because="this repository trusts its own runner")


def _an_inspection_that_says_what_this_repository_is() -> str:
    return "## src/aisdlc/tools/run_command.py\n\ndef run(a_command): ..."


def _the_repository() -> object:
    from aisdlc.domain.repository import Repository

    return Repository(owner="steamnoid", name="ai-sdlc-bestof-fast-selfaware")


def _the_request_nobody_read() -> CommissionedRequest:
    """Named only so the omission is visible: the implementer is given none of this."""
    return CommissionedRequest(
        title="Enforce the trust boundary of run_command",
        body=AN_INVARIANT_THE_CHANGE_ENFORCES,
    )
