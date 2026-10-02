"""What the development planning agent produced, in the four fields `§10` lists.

The field names are not chosen here. `docs/domain-glossary.md` fixes the contents of this
artifact, and the agent's name is the contract, so a field that drifts from that table is a
broken promise rather than a rename. There is no separate shape for the model's answer, the
way `DiscoveryAnswer` exists beside `DiscoveryReport`, because that split exists to keep a
derived field away from a model: a link a reviewer clicks is derived from
`owner`/`name`/`branch`/`path` and must not be asked for, and nothing here is derived. A
second type for the same four lists would be a shape with no reason to differ, and the
model is asked for this one directly.

**`tests_to_add` is the one list whose paths are not checked against the clone.** A test
that does not exist yet is the whole point of it. `files_to_change` is the opposite: every
one of those is a file of the repository as it stands, and `plan_the_change` proves it
before a plan exists.
"""

from __future__ import annotations

from pydantic import BaseModel, model_validator


class EmptyPlanError(Exception):
    """The rule is in `ImplementationPlan`, and this is the only thing that may say it broke.

    Raised rather than returned as a Pydantic `ValidationError`, for the reason
    `EmptyDiscoveryReportError` is: the caller has something to do about this that it
    cannot do about a malformed field. Four empty lists is a fault to be told about in our
    own words, because a person cannot tell it from a real plan by looking at it — and the
    next thing that happens to a real plan is that a person approves it.
    """


class ImplementationPlan(BaseModel):
    """Which files change, which tests are added, what is depended on, what must migrate.

    **And what the change makes, which is the sixth field and the only one that is a sentence.**
    It was missing, and the plan a real run produced and a real policy refused said why in one
    sentence: *"nothing here tells an implementer what 'enforce the trust boundary' actually
    requires"*. Five lists of paths carry no intent, and the implementer is handed this plan and
    a checkout — no request, no requirements, no security report — so the intent has nowhere else
    to live.

    **It is deliberately outside the emptiness rule.** That rule asks whether a plan says anything
    *to do*, and a sentence with no file named cannot be implemented by anyone, so the statement
    is not a way to pass it. A field that both carried the reasoning and satisfied the rule would
    be a loophole wearing the same name as the fix.
    """

    the_change_it_makes: str = ""
    files_to_change: list[str] = []
    files_to_add: list[str] = []
    tests_to_add: list[str] = []
    dependencies: list[str] = []
    migrations: list[str] = []

    def everything_it_says(self) -> tuple[object, ...]:
        """Every field's value, in the order the glossary lists them."""
        return (
            self.files_to_change,
            self.files_to_add,
            self.tests_to_add,
            self.dependencies,
            self.migrations,
        )

    @model_validator(mode="after")
    def it_must_say_something_to_do(self) -> ImplementationPlan:
        """At least one of the five lists must name something, or this is a fault.

        "At least one" and not "all of them", because a plan that adds a dependency and
        changes no file is a plan — that is what `dependencies` is for — and a rule demanding
        every field would be satisfied only by a plan that guesses. What is refused is the
        plan with nothing in it, which is what a model returns when it did not do the
        reading, and which is indistinguishable from a real plan to a person approving it.

        **All five, and it was four.** `files_to_add` was missing from this rule, from the list
        it names in its own docstring, and from the refusal it raises — so a plan whose only
        content was a file to add was refused as empty, while a plan whose only content was a
        dependency was accepted. The reasoning that admits one admits the other: adding a file
        without changing one is the ordinary case for a repository that does not yet have the
        thing being added. Found by reading a plan a real run had produced and a real policy
        had refused, which passed this rule through `files_to_change` and so did not reveal it.
        """
        if not any(self.everything_it_says()):
            raise EmptyPlanError(
                "The planning agent returned a plan that names no file to change, no file to "
                "add, no test to add, no dependency and no migration. That is a fault rather "
                "than a plan, because the next thing that happens to a plan is that a person "
                "is asked to approve it, and a person cannot tell an empty plan from a real "
                "one by looking at it."
            )

        return self
