"""A plan whose only content is a file to add is refused, and a file to add is a file.

**`ImplementationPlan` has five lists. Its emptiness rule counts four.**

Its validator's docstring says *'At least one of the four lists must name something, or this is a
fault'*, and the refusal it raises names *'no file to change, no test to add, no dependency and no
migration'* — which is a complete description of the fields it looked at, and `files_to_add` is
not among them.

**So `ImplementationPlan(files_to_add=["tests/test_a_thing.py"])` raises `EmptyPlanError`**, and
that is a plan with exactly as much in it as a plan that adds a dependency — which the same rule
accepts, and for a stated reason: *'a plan that adds a dependency and changes no file is a plan —
that is what `dependencies` is for'*.

The reasoning that admits a dependency-only plan admits an add-only plan and the code does not
follow its own reasoning. **Adding a file without changing one is the ordinary case for a
repository that does not yet have the thing being added**, and it is the case this rule refuses.

**The method claims to list every field.** Its own docstring says *'Every field's value, in the
order the glossary lists them'*, and `docs/domain-glossary.md` lists five — `files_to_change`,
`files_to_add`, `tests_to_add`, `dependencies`, `migrations`. The code enumerates four, in the
glossary's order, having skipped one in the middle. A reader trusting the docstring would not
notice, because the list is right in every particular.

**Found by reading a refused plan rather than by a failing test.** The plan a real run produced and
a real policy refused held two paths in `files_to_change`, one in `files_to_add` and one in
`tests_to_add` — so it passed the rule through `files_to_change` and this defect was not what
stopped that run. It would have stopped a different one: the same run, with a smaller request.
"""

from __future__ import annotations

from aisdlc.agents.implementation_plan import ImplementationPlan


def test_a_plan_that_only_adds_a_file_is_a_plan() -> None:
    """One file to add and nothing else, which is what a repository missing that file needs.

    **Written as a construction and not as a `pytest.raises`, after the first version got that
    backwards.** Asserting that the refusal happens would have been a test of the bug, passing
    today and failing the moment the bug was fixed — a test that changes meaning when the code
    improves is a test nobody can trust in either state. What is wanted is stated positively: the
    plan is a plan, so building it must work.
    """
    a_plan = ImplementationPlan(files_to_add=["tests/test_a_thing.py"])

    assert a_plan.files_to_add == ["tests/test_a_thing.py"]


def test_a_plan_that_adds_a_dependency_is_accepted_for_the_same_reason() -> None:
    """The control, and it passes today.

    The emptiness rule says in its own docstring that *"a plan that adds a dependency and changes
    no file is a plan — that is what `dependencies` is for"*. This test is here so that the fix
    above is a widening rather than a substitution: if it were ever changed to refuse this one
    instead, the two tests would say so.
    """
    a_plan = ImplementationPlan(dependencies=["httpx"])

    assert a_plan.dependencies == ["httpx"]


def test_every_field_the_plan_has_is_the_list_the_emptiness_rule_looks_at() -> None:
    """The rule names four lists in a class with five, and this is what makes that a defect.

    Read from the model's own fields rather than from a copy of them here, so a field added to
    `ImplementationPlan` without being added to `everything_it_says` fails here instead of
    producing a plan whose one content is silently unseeable.
    """
    every_field_the_plan_has = list(ImplementationPlan.model_fields)

    what_the_rule_looks_at = list(_the_fields_the_emptiness_rule_looks_at())

    assert every_field_the_plan_has == what_the_rule_looks_at, (
        f"ImplementationPlan has {every_field_the_plan_has} and the emptiness rule looks at "
        f"{what_the_rule_looks_at}. A field it does not look at is a field a plan can be made of "
        f"and be refused for being empty"
    )


def _the_fields_the_emptiness_rule_looks_at() -> tuple[object, ...]:
    """The values `everything_it_says` returns, matched back to the fields they came from."""
    a_plan = ImplementationPlan(
        files_to_change=["a.py"],
        files_to_add=["b.py"],
        tests_to_add=["c.py"],
        dependencies=["httpx"],
        migrations=["one.sql"],
    )

    by_value = {
        id(a_plan.files_to_change): "files_to_change",
        id(a_plan.files_to_add): "files_to_add",
        id(a_plan.tests_to_add): "tests_to_add",
        id(a_plan.dependencies): "dependencies",
        id(a_plan.migrations): "migrations",
    }
    return tuple(by_value.get(id(a_value), str(a_value)) for a_value in a_plan.everything_it_says())
