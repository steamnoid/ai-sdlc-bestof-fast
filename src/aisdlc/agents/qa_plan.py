"""What the QA analyst concluded should be tested, in the fields the glossary lists.

The field names are not chosen here. `docs/domain-glossary.md` already fixed the contents of
this artifact — test strategy, scenarios, edge cases, regression risks — and the agent's name
is the contract, so a field that drifts from that table is a broken promise rather than a
rename.
"""

from __future__ import annotations

from pydantic import BaseModel, model_validator

from aisdlc.agents.a_value_that_says_something import a_value_that_says_something

THE_QA_ANALYST_AGENT = "aisdlc-qa-analyze"


class EmptyQaPlanError(Exception):
    """The rule is in `QaPlan`, and this is the only thing that may say it broke.

    Raised rather than returned as a Pydantic `ValidationError`, for the reason
    `EmptyRequirementsError` gives: the caller can ask a model to fix an answer that said
    nothing, and cannot do anything of the sort with a field of the wrong shape.
    """


class QaPlan(BaseModel):
    """What a QA analyst proposes to test, in the words a person would approve or refuse.

    The four collections are the glossary's, and they are not required together. A set of
    requirements with nothing ambiguous about it has no edge cases to name, and the honest
    artifact says so with three filled fields and one empty one rather than inventing a
    boundary condition to fill it.
    """

    test_strategy: str = ""
    scenarios: list[str] = []
    edge_cases: list[str] = []
    regression_risks: list[str] = []

    def everything_it_says(self) -> tuple[object, ...]:
        """Every field's value, in the order the glossary lists them."""
        return (
            self.test_strategy,
            self.scenarios,
            self.edge_cases,
            self.regression_risks,
        )

    @model_validator(mode="after")
    def it_must_propose_something_to_test(self) -> QaPlan:
        """At least one field must carry something, or this is a fault and not a plan.

        The rule is emptiness a third time and it is the same rule: the consumer is a person
        deciding whether to fund testing, and a QA plan with nothing in it is
        indistinguishable from no QA analyst having run at all.
        """
        if not any(a_value_that_says_something(value) for value in self.everything_it_says()):
            raise EmptyQaPlanError(
                f"{THE_QA_ANALYST_AGENT} proposed nothing to test: every field was empty. "
                "That is a fault rather than an artifact, because a person cannot tell an "
                "empty plan from a real one by looking at it — and approving one would "
                "record a decision about testing that nobody made."
            )

        return self
