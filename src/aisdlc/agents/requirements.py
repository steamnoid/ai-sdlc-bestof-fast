"""What the product analyst concluded should be built, in the fields the glossary lists.

The field names are not chosen here. `docs/domain-glossary.md` already fixed the contents
of this artifact — requirements, acceptance criteria, ambiguities — and the agent's name is
the contract, so a field that drifts from that table is a broken promise rather than a rename.
"""

from __future__ import annotations

from pydantic import BaseModel, model_validator

from aisdlc.agents.a_value_that_says_something import a_value_that_says_something
from aisdlc.agents.requirements_answer import AnAmbiguity

THE_PRODUCT_ANALYST_AGENT = "aisdlc-po-analyze"


class EmptyRequirementsError(Exception):
    """The rule is in `Requirements`, and this is the only thing that may say it broke.

    Raised rather than returned as a Pydantic `ValidationError`, for the reason
    `EmptyDiscoveryReportError` gives: the caller can ask a model to fix an answer that said
    nothing, and cannot do anything of the sort with a field of the wrong shape.
    """


class Requirements(BaseModel):
    """What a product analyst proposes, in the words a person would approve or refuse.

    The three collections are the glossary's, kept flat and unpaired. Acceptance criteria
    are not hung off the requirement they verify, because `PullRequestRequest` is the
    artifact that traces a change back to what it was for, and pairing them here would
    build the same traceability twice — in the artifact where nobody asked for it, and in
    the one where §10 does.
    """

    requirements: list[str] = []
    acceptance_criteria: list[str] = []
    ambiguities: list[AnAmbiguity] = []

    def everything_it_says(self) -> tuple[object, ...]:
        """Every field's value, in the order the glossary lists them."""
        return (
            self.requirements,
            self.acceptance_criteria,
            self.ambiguities,
        )

    @model_validator(mode="after")
    def it_must_propose_something(self) -> Requirements:
        """At least one collection must carry something, or this is a fault and not a proposal.

        "At least one" and not "all of them", because a repository can be unambiguous — and
        then the honest artifact says so with two empty lists rather than inventing an
        ambiguity to fill the third. A rule demanding every field would only ever be
        satisfied by a proposal that guessed.
        """
        if not any(a_value_that_says_something(value) for value in self.everything_it_says()):
            raise EmptyRequirementsError(
                f"{THE_PRODUCT_ANALYST_AGENT} proposed nothing at all about "
                f"{'the project'}: every field was empty. That is a fault rather than an "
                "artifact, because a person cannot tell an empty proposal from a real one "
                "by looking at it — and a blank page is the one thing a run may not put in "
                "front of the person who commissioned the work."
            )

        return self
