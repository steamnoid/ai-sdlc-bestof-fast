"""A report that names no file of the repository is not grounded in it.

**A real run was refused at its first gate for exactly this**, and the reason was right:

> The DiscoveryReport has an empty evidence_files list and blank
> architecture_summary/key_components, so the suggested change is not
> grounded in any inspected file.

**And every check this repository has about a discovery report passed
it.** `_the_cited_files_that_are_in` proves each citation is a file of
the clone *and* was shown to the model — and it proves that of zero
citations without complaint. `it_must_say_something_about_the_repository`
requires that *at least one field* carry a value, and a list of
languages is a value.

**So a report that says what a repository is built with, and never says
what it read, was a valid discovery report.**

**This is the third of one bug, and naming that is the point.**

- `expect(true).toBe(true)` — a tautology passing whatever the code
  does. #40 on the fork.
- `<jwt-secret-guard-test>.test.ts` — a plan naming the place a path
  would go, and passing every check made about paths.
- `evidence_files: []` — a report citing nothing, and passing every
  check made about citations.

**All three are the same shape: an empty value satisfies a rule written
about its members.** Every check was real, and each was written in the
form *every X must be Y* — which an empty list satisfies without doing
anything. **None was found by a model failing; all three were found by
a person or a gate reading a value that had passed.**

**So these tests assert this one field and not the general rule**,
because the general rule is already here and it is what let this
through. A report may legitimately have no CI and no build system, and
demanding every field would only ever be satisfied by a report that
guesses. **The field that cannot be empty is the one carrying what was
read.**
"""

from __future__ import annotations

import pytest

from aisdlc.agents.discovery_report import (
    DiscoveryReport,
    EmptyDiscoveryReportError,
    EvidenceFile,
    EvidenceOutsideRepositoryError,
    evidence_for,
)
from aisdlc.domain.repository import Repository

_A_REPOSITORY = Repository(owner="steamnoid", name="wellbeing-tracker-public")

_A_FILE_OF_THE_REPOSITORY = EvidenceFile(
    path="web-app/src/lib/auth.js",
    link=(
        "https://github.com/steamnoid/wellbeing-tracker-public/blob/main"
        "/web-app/src/lib/auth.js"
    ),
)


def test_a_report_that_cites_no_file_is_refused() -> None:
    """The shape that passed every check: real fields, and nothing the claims rest on.

    **Filled with a language and a build system on purpose.** An entirely
    empty report is already refused by a rule that exists; the finding is
    that filling two fields was enough, and only a report shaped exactly
    like this demonstrates it.

    **A shell and not the class this rule raises**, because a RED that
    imports a missing name fails on the name rather than on the
    behaviour. Which class it is, is asserted below.
    """
    with pytest.raises(Exception) as what_was_said:
        DiscoveryReport(
            languages=["TypeScript", "JavaScript"],
            build_system="npm",
            architecture_summary="A Next.js application with an API of its own.",
            suggested_changes=["Remove the hardcoded fallback from auth.js"],
        )

    assert "evidence_files" in str(what_was_said.value), (
        f"the refusal was {what_was_said.value}. **A person reading it has to know which field to "
        "fill**: the gate that caught this run said the same thing, and the run still had to be "
        "re-planned around the sentence"
    )


def test_a_report_that_cites_one_file_is_a_report() -> None:
    """The other half: the rule is about the field, not about being complete.

    **One citation and nothing else.** A report that named one file and
    guessed at everything else is still grounded, and a rule that
    demanded more would refuse a repository this system has not read
    carefully — which is most of them, and every one worth onboarding.
    """
    a_report = DiscoveryReport(evidence_files=[_A_FILE_OF_THE_REPOSITORY])

    assert a_report.evidence_files == [_A_FILE_OF_THE_REPOSITORY]


def test_the_refusal_names_the_action_a_correction_needs() -> None:
    """The name and the wording, because the correction loop is built from both.

    **`ValidationError` is already in that tuple, so a bare one would
    work by accident** — and then the correction prompt would say *fix
    your fields*, which is advice a model cannot act on when the problem
    is that it cited nothing. **The rule this adds is a distinct error on
    purpose**, so the correction names the action: cite a file you read.
    """
    with pytest.raises(EmptyDiscoveryReportError) as what_was_said:
        DiscoveryReport(languages=["TypeScript"])

    assert "read" in str(what_was_said.value).lower(), (
        f"the refusal was {what_was_said.value!r}, and a correction built from it would tell a "
        "model to fix its fields. **The instruction has to name the action** — cite a file you "
        "read — or the model fills a field it already filled and the run bounces again"
    )


def test_a_citation_outside_the_repository_is_still_refused() -> None:
    """The other rule, kept: a citation that is not a file of this repository links to nowhere.

    **Asserted here because the new rule must not have displaced it.**
    Adding a rule about emptiness is exactly the kind of change that
    quietly makes an existing one unreachable, and a report citing a path
    outside the repository is a failure this system learned about the
    hard way.
    """
    with pytest.raises(EvidenceOutsideRepositoryError):
        evidence_for(["../elsewhere/secrets.ts"], _A_REPOSITORY)
