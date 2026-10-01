"""Every stage that reasons about a file's contents must be shown that file's contents.

**A real run found this, and the reason is the whole argument.** Asked to enforce the trust
boundary of `src/aisdlc/tools/run_command.py`, this system's own policy refused the requirements
with this:

> The artifact itself records that neither `src/aisdlc/tools/run_command.py` nor
> `src/aisdlc/agents/inspect_for_security_risk.py` had its contents in the inspection, yet
> requirements 3, 4, 6 and 7 state what those files catch, where the boundary is enforced, and
> that nothing escapes the project directory.

**A model wrote four requirements about two files nobody in that stage had read.** The product
analyst and the architecture analyst were handed `an_inspection_of` — the directory listing and the
manifests — while discovery, the security analyst and the briefing were handed
`an_inspection_of_the_code`, the one that carries file contents.

**It was already fixed once, for discovery, and never checked for the stages after it.** That is
the recurring shape in this repository: a fix that is made where the bug was found and not where
the rule is. So the rule is now a test over the whole set, and it is read by parsing rather than by
grepping the source — a guard that can be satisfied by a comment is the third one of those this
repository has now had.

**Why a test and not a shared helper.** A shared function would make this impossible to write
wrong and impossible to check, and the failure it prevents is not a typo: it is two stages written
at different times, by different nights, with a different inspection each. The disagreement is
between two correct-looking calls.
"""

from __future__ import annotations

import ast
from pathlib import Path

from aisdlc.agents import (
    analyze_the_architecture,
    analyze_the_repository,
    brief_this_repository,
    discover_the_repository,
    inspect_for_security_risk,
)

A_STAGE_THAT_REASONS_ABOUT_WHAT_A_REPOSITORY_CONTAINS = [
    analyze_the_repository,
    analyze_the_architecture,
    discover_the_repository,
    inspect_for_security_risk,
    brief_this_repository,
]


def _the_inspection_each_stage_hands_its_model(a_stage: object) -> str | None:
    """The inspection function a stage calls, read from its own source by parsing it.

    **Parsed and not imported, because a double could answer either way.** The claim is about what
    the production code calls; a test that replaced the inspection could only prove that the
    replacement was used.
    """
    the_source = Path(a_stage.__file__).read_text(encoding="utf-8")  # type: ignore[attr-defined]
    the_calls = [
        a_node.func.id
        for a_node in ast.walk(ast.parse(the_source))
        if isinstance(a_node, ast.Call) and isinstance(a_node.func, ast.Name)
    ]
    inspections = [
        a_name for a_name in the_calls if a_name.startswith("an_inspection_of")
    ]
    assert len(inspections) <= 1, (
        f"{a_stage.__name__} calls {inspections}, so there is no single inspection to check and a "
        "reader has to work out which one the model is actually given"
    )
    return inspections[0] if inspections else None


def test_no_stage_reasons_about_a_file_it_was_not_shown() -> None:
    shown_shape_only: list[str] = []
    for a_stage in A_STAGE_THAT_REASONS_ABOUT_WHAT_A_REPOSITORY_CONTAINS:
        the_inspection = _the_inspection_each_stage_hands_its_model(a_stage)
        if the_inspection == "an_inspection_of_the_code":
            continue
        shown_shape_only.append(f"{a_stage.__name__} uses {the_inspection or 'none'}")

    assert not shown_shape_only, (
        f"{', '.join(shown_shape_only)} — a stage given the directory listing will write findings "
        "about files nobody in it has read, and a policy reading the artifact against its own "
        "evidence list will refuse the run for it. That is what happened to the requirements "
        "stage on the first self-run."
    )
