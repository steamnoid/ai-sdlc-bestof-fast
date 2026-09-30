"""What the verification agent found, from two runs of a repository's own suite.

The artifact holds the suite's outcome on each side of a change and nothing else it had to
be told. `regressions` is a **property rather than a field**, and that is the whole
difference: a field is something the caller states, and the caller is not in a position to
state whether a change broke anything — it has two outcomes and no opinion about the
relationship between them. So the report derives it, and a caller cannot pass a verdict in.

**`extra="forbid"`, because a stated verdict must be an error rather than a shrug.** Pydantic
ignores a keyword a model does not have, so without this a caller could pass
`regressions=[...]` and watch it disappear: the report would still be right and the caller
would still believe they had said something. A rule a model cannot hold should fail loudly.

**There is no `acceptance_criteria_satisfied` field, on purpose.** The glossary's contract
for this artifact names three things, and one of them cannot be computed: satisfying an
acceptance criterion needs a `Requirements` artifact, and none has been produced. An empty
list would read as *no criterion was satisfied*, which is a different claim from *nobody has
said what the criteria are*, and the second is the true one. A test asserts the field is
absent, because adding it back as an empty default is the mistake this paragraph exists to
prevent.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from aisdlc.tools.run_tests import SuiteOutcome


class VerificationReport(BaseModel):
    """The suite before the change, the suite after it, and what that pair says."""

    model_config = ConfigDict(extra="forbid")

    suite_before_the_change: SuiteOutcome
    suite_after_the_change: SuiteOutcome

    @property
    def regressions(self) -> list[str]:
        """What the suite said after the change that it did not say before, if it went red.

        Only when it went from passing to not passing. A suite that was already red is not
        evidence that this change was safe, and it is not written down as a regression
        either — this system cannot establish that cause, and a cause it cannot establish
        should not appear in a record as though it had. The two outcomes are still both
        here, so "it was already broken" is visible to whoever reads it rather than
        laundered into a clean bill of health.

        The words are the suite's own, not a list of test names. Parsing another project's
        output to name the test that broke would mean trusting a format this system knows
        nothing about, and a name a scraper invented is a name nobody verified.
        """
        if self.suite_before_the_change.passed and not self.suite_after_the_change.passed:
            return [self.suite_after_the_change.output]
        return []
