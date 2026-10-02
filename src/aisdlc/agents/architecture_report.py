"""What the architecture analyst concluded about a repository, in the fields §10 lists.

The field names are not chosen here. `docs/domain-glossary.md` already fixed the contents of
this artifact — findings, modules, dependencies, boundaries, risks — and the agent's name is
the contract, so a field that drifts from that table is a broken promise rather than a rename.
"""

from __future__ import annotations

from pydantic import BaseModel, model_validator

from aisdlc.agents.a_value_that_says_something import a_value_that_says_something

THE_ARCHITECTURE_ANALYST_AGENT = "aisdlc-arch-analyze"


class EmptyArchitectureReportError(Exception):
    """The rule is in `ArchitectureReport`, and this is the only thing that may say it broke.

    Raised rather than returned as a Pydantic `ValidationError`, for the reason
    `EmptyQaPlanError` gives: the caller can ask a model to fix an answer that said nothing,
    and cannot do anything of the sort with a field of the wrong shape.
    """


class ArchitectureReport(BaseModel):
    """What a repository is shaped like, in the words a person would read before changing it.

    Every field is a list here, and the artifact is read rather than decided upon, so the
    emptiness rule is the fourth of its kind and the reason is the same one: a person cannot
    tell a report that says nothing from a real one by looking at it, and this one would be
    filed beside a discovery report and a requirements set that do say something.
    """

    findings: list[str] = []
    modules: list[str] = []
    dependencies: list[str] = []
    boundaries: list[str] = []
    risks: list[str] = []

    def everything_it_says(self) -> tuple[object, ...]:
        """Every field's value, in the order the glossary lists them."""
        return (
            self.findings,
            self.modules,
            self.dependencies,
            self.boundaries,
            self.risks,
        )

    @model_validator(mode="after")
    def it_must_describe_something(self) -> ArchitectureReport:
        """At least one field must carry something, or this is a fault and not a report.

        "At least one" and not "all of them", because a repository can be small enough to
        have no architectural risk, and the honest report says so with four filled fields and
        one empty one rather than inventing a coupling to describe.
        """
        if not any(a_value_that_says_something(value) for value in self.everything_it_says()):
            raise EmptyArchitectureReportError(
                f"{THE_ARCHITECTURE_ANALYST_AGENT} described nothing at all about the "
                "repository: every field was empty. That is a fault rather than an "
                "artifact, because a person cannot tell an empty report from a real one by "
                "looking at it — and a person about to change a repository is the reader who "
                "would act on it."
            )

        return self

    @model_validator(mode="after")
    def it_must_name_a_module(self) -> ArchitectureReport:
        """A report naming no module is refused, and the rule above would have accepted it.

        **The one field the "at least one" rule does not reach.** Its own justification is that
        a repository can have no architectural risk, and that is why the rule is "at least one"
        rather than "all of them" — but no repository has zero modules. A single-file script is
        one module. An empty list here is not an observation about the repository, it is the
        analyst declining a question it was asked, and `modules: []` came back in roughly one run
        in three of the neighbouring-agent tier.

        **What an empty `modules` costs downstream is why this is refused rather than
        tolerated.** The QA analyst is handed this report and asked to write scenarios against
        it, and with nothing named there is nothing to check anything against — the pair's own
        assertion says so: *"the architecture report names no modules, so there was nothing for
        the QA plan to check against"*.

        **Raised rather than defaulted, because the caller can act on this one.** A correction
        says "you named no modules, name them" and goes back to the model; an answer that says
        nothing arrives at the gate as a report that agrees with every possible architecture,
        which is the shape a report takes when the analyst was never asked.
        """
        if not a_value_that_says_something(self.modules):
            raise EmptyArchitectureReportError(
                f"{THE_ARCHITECTURE_ANALYST_AGENT} named no modules. Every repository has at "
                "least one — a single-file script is one — so an empty list is not an "
                "observation about this repository but the answer to no question at all. The QA "
                "plan is written against what is named here, so an empty one leaves it with "
                "nothing to check anything against."
            )

        return self
