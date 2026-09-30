"""What the security analyst found, in the fields the glossary lists.

The field names are not chosen here. `docs/domain-glossary.md` fixed the contents of this
artifact and `§10` fixed the agent's responsibilities, and the two are reconciled in that
file — the glossary's row said "findings with severity, signal and false-positive notes" and
§10 also requires recommendations, so the row was corrected rather than the responsibility
dropped.
"""

from __future__ import annotations

from pydantic import BaseModel, model_validator

from aisdlc.agents.a_value_that_says_something import a_value_that_says_something
from aisdlc.agents.security_finding import SecurityFinding

THE_SECURITY_ANALYST_AGENT = "aisdlc-sec-analyze"


class EmptySecurityReportError(Exception):
    """The rule is in `SecurityReport`, and this is the only thing that may say it broke.

    Raised rather than returned as a Pydantic `ValidationError`, for the reason
    `EmptyQaPlanError` gives: the caller can ask a model to fix an answer that said nothing,
    and cannot do anything of the sort with a field of the wrong shape.
    """


class SecurityReport(BaseModel):
    """What a security analyst found, in the words a person would weigh before acting.

    **A report with no findings must say what it looked at, and that is a judgement worth
    stating.** The prompt tells the model that an empty list is an answer — a repository with
    no visible risk should say so rather than invent one — and the rule here is not a
    contradiction of that. An empty list is a *claim*, and a claim with nothing in it is the
    one thing a person cannot tell from a run that never looked: from an empty report, a reader
    concludes the repository is safe, and no model was ever asked that.

    So a report with neither a finding nor an account is refused, and a report with an account
    and no finding is a true negative stated rather than a silence. The account is written by
    the node from the inspection it showed the analyst: `SecurityReportAnswer` is a bare array,
    a shape two real runs forced, so this fact was never available from the model and never
    needed to be.
    """

    findings: list[SecurityFinding] = []

    #: The account a run gives when it examined something and found nothing in it. Written by
    #: the node and never asked of the model, because the answer shape is a bare array — a
    #: shape two real runs forced — and because what the analyst examined is what the node
    #: showed it rather than anything the model said. `None` on a report with findings, which
    #: are their own account.
    nothing_found_because: str | None = None

    @model_validator(mode="after")
    def it_must_report_something(self) -> SecurityReport:
        """At least one finding, or this is a fault and not a report.

        The emptiness rule a fifth time, and the reader is the one a person trusts least:
        silence in a security report is read as safety, and it is the one silence in this
        pipeline that could be acted on with real consequences.
        """
        if a_value_that_says_something(self.findings):
            return self

        if self.nothing_found_because and self.nothing_found_because.strip():
            return self

        raise EmptySecurityReportError(
            f"{THE_SECURITY_ANALYST_AGENT} reported no findings and no account of what it "
            "examined. That is a fault rather than an artifact: a report saying nothing "
            "about a repository's security is read as a report saying it is fine, and no "
            "model was asked that question. A run that found nothing says so by describing "
            "what it looked at."
        )
