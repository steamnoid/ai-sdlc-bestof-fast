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
