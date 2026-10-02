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


def _how_many_arguments_the_stage_hands_the_inspection(a_stage: object) -> int:
    """How many arguments a stage gives the inspection, read from its own source by parsing it.

    **Counted and not checked for the request by name**, because a stage that hands the inspection
    one argument and a stage that hands it two differ in a way a reader of the signature cannot
    miss but a keyword search can be satisfied by: a test looking for the word `requested` finds it
    in the signature of all five, including the one that never passes it.
    """
    the_source = Path(a_stage.__file__).read_text(encoding="utf-8")  # type: ignore[attr-defined]
    the_calls = [
        a_node
        for a_node in ast.walk(ast.parse(the_source))
        if isinstance(a_node, ast.Call)
        and isinstance(a_node.func, ast.Name)
        and a_node.func.id == "an_inspection_of_the_code"
    ]
    assert len(the_calls) == 1, (
        f"{a_stage.__name__} calls an_inspection_of_the_code {len(the_calls)} times, so there is "
        "no single call to count"
    )
    return len(the_calls[0].args)


def test_every_stage_is_told_what_the_run_is_about() -> None:
    """A stage handed no request gets the selection the name rule alone produces, silently.

    **The same shape as the rule above it, one level down, and the reason it is a separate test.**
    Every stage now takes the request and passes it on, because a run about
    `src/aisdlc/tools/run_command.py` was refused at its first gate for citing twenty-one test
    files and no source file — having been shown exactly that, because `run_command.py` is one of
    the hundred and fifty-eight files the name rule drops out of a hundred and sixty-nine
    eligible ones. The request contained the path in plain text.

    **One stage taking the parameter and not passing it would look identical from outside.** Five
    signatures would each say `what_the_run_is_about: CommissionedRequest | None`, one call would
    pass it and four would not, and the result would be four stages reasoning from a repository
    without their subject in it — which is the exact failure this file exists for, arrived at
    through a different door. Counting arguments is what can tell the difference, and a search
    for the parameter's name cannot.
    """
    stages_handed_nothing = [
        a_stage.__name__
        for a_stage in A_STAGE_THAT_REASONS_ABOUT_WHAT_A_REPOSITORY_CONTAINS
        if _how_many_arguments_the_stage_hands_the_inspection(a_stage) < 2
    ]

    assert not stages_handed_nothing, (
        f"{', '.join(stages_handed_nothing)} takes the request and does not pass it to the "
        "inspection. A stage told nothing about the run is handed a selection made only from a "
        "list of words in file names, which is how a run about run_command.py was handed "
        "twenty-one test files and no source file and refused for writing the truth"
    )
