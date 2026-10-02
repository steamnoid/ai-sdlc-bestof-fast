"""`modules: []` is a failure to answer, and every other empty field is an answer.

**The rule is already written down and nothing enforces it.** `docs/domain-glossary.md` says of
`ArchitectureReport`:

> At least one field must say something, and `modules` is the one that cannot honestly be empty. A
> repository can have no architectural risk and the report says so; no repository has zero modules,
> so `modules: []` is a failure to answer rather than an answer.

**And the model agrees, reliably.** An empty `modules` comes back in roughly one run in three of
the neighbouring-agent tier, and the assertion there is blunt about what it costs:

> the architecture report names no modules, so there was nothing for the QA plan to check against

So the codebase holds three positions at once: a glossary saying `modules` must be there, a
validator saying any one field is enough, and a real tier that fails when it is empty. **Two of
those three are tests and one is prose, and the prose is the one that is right.**

**Why `modules` and not the other four.** The existing rule's own justification is *"a repository
can be small enough to have no architectural risk"*, and that reasoning is sound — it is why the
rule is "at least one" rather than "all of them". It does not reach `modules`. There is no
repository with zero modules; a single-file script is one module. An empty list there is not an
observation, it is the analyst declining to answer a question it was asked.

**Why refusing beats defaulting.** A refusal raises `EmptyArchitectureReportError`, which the
caller can turn into a correction — "you named no modules, name them" — and an answer that goes
back to the model with a reason is the whole reason the correction budget exists. Defaulting to
`[]` is the alternative and it is what happens now: the model says nothing, the artifact says
nothing, and the gate is handed a report that agrees with every possible architecture.
"""

from __future__ import annotations

import pytest

from aisdlc.agents.architecture_report import (
    ArchitectureReport,
    EmptyArchitectureReportError,
)


def test_a_report_that_names_no_module_is_refused() -> None:
    """`risks` filled and `modules` empty is a report about a repository with no modules.

    Every other field empty too, so this is the smallest report that says *something* and still
    identifies nothing. It was accepted before, and that was the defect: the emptiness rule
    accepted it because it was written about risk rather than about modules.

    **The first version of this test built the same report outside the `raises` block as a
    control, and the rule made that line raise too** — which is the rule working and the control
    being pointless. A control that cannot survive the change it is a control for is not a
    control, and the second test already carries the other half.
    """
    with pytest.raises(EmptyArchitectureReportError) as what_it_refused:
        ArchitectureReport(
            risks=["the cycle depends on one unversioned file"],
            modules=[],
        )

    assert "module" in str(what_it_refused.value), (
        f"the refusal says {str(what_it_refused.value)!r}, which does not name the field that was "
        "empty. A refusal a correction cannot act on is a refusal the next run repeats"
    )


def test_a_report_that_names_one_module_is_accepted() -> None:
    """The other half, because a rule that refuses everything is not a rule about modules."""
    a_report = ArchitectureReport(modules=["src/aisdlc/tools/run_command.py"])

    assert a_report.modules == ["src/aisdlc/tools/run_command.py"]
