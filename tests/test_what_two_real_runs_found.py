"""Two defects a real run found, and the tests that hold them there.

Both of these were invisible to a test suite that only ever ran from pytest's own `tmp_path`,
and both were found by pointing the product at a real repository from a real shell. That is the
argument for this file existing at all: it is short, and every case in it is a place where the
machine's own behaviour, rather than the code's logic, is what a test would have to be told
about.

**A symlinked projects root, because `/tmp` is one on macOS and a real deployment will use one
on Linux too.** `plan_the_change` asked the confinement check where a test's directory was, got
back a path that had been resolved, and compared it against a root that had not. On any machine
where the two spellings differ — which is every machine where the root is a link — the
comparison raised Python's own `ValueError` about a subpath, out of a stage, twenty minutes into
a run. The failure was loud and named, which is the only reason it was cheap to find; it was
still a bug, and it is the kind a unit test cannot reach.

**A security analyst shown no source code, because one inspection was doing two jobs.** The
inspection was built for discovery, whose job is a repository's *shape*, and the security analyst
was later wired to the same one. It was therefore asked to find authentication and authorization
problems while being handed a directory listing and a `package.json` — and it reasoned from
filenames, which a real run's gate refused for exactly that.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from aisdlc.agents.implementation_plan import ImplementationPlan
from aisdlc.agents.plan_the_change import _every_test_is_where_the_suite_will_look_for_it
from aisdlc.tools.github_clone_repository import ClonedRepository
from aisdlc.tools.inspect_the_repository import (
    an_inspection_of,
    an_inspection_of_the_code,
)
from aisdlc.tools.the_project_directory import where_projects_live


@pytest.fixture
def a_symlinked_projects_root(tmp_path: Path) -> tuple[Path, Path]:
    """One directory reached two ways — once directly, once through a link — and a clone in each.

    **A real symlink, not a mocked one.** The whole defect is that `resolve()` and not
    `resolve()` produce two different strings for the same directory, and the only honest way to
    have that happen is to have a link. A test that faked the path would have tested the fake.
    """
    the_real_one = tmp_path / "the-real-projects"
    the_real_one.mkdir()
    a_link_to_it = tmp_path / "a-link-to-them"
    a_link_to_it.symlink_to(the_real_one)

    # **The same directory twice, which is what a link is.** `exist_ok` is what makes that
    # true rather than accidental: the second root resolves to the first, so the clone is built
    # once and both tests then reach it by two names.
    a_clone = the_real_one / "an" / "owner" / "a-repository" / "repository"
    (a_clone / "tests" / "unit").mkdir(parents=True, exist_ok=True)
    (a_clone / "tests" / "unit" / "test_the_existing_thing.test.ts").write_text("// one")

    return the_real_one, a_link_to_it


def _a_clone_at(a_projects_root: Path) -> ClonedRepository:
    """A clone in the place a run puts one, reached through whichever root was given."""
    return ClonedRepository(
        path=a_projects_root / "an" / "owner" / "a-repository" / "repository",
        ref="main",
        commit="d009c2cf0c233ebe9aa5ba2dccd3823c6f004ec4",
    )


def _where_the_planner_believes_a_test_belongs(a_projects_root: Path) -> str:
    """What the planner says about a test in a directory that already holds one.

    **The runner is announced as something this system cannot parse**, which is a real run's
    ordinary case and which makes the planner fall through to asking the repository. That is the
    branch the bug was on: a path is compared against a root before the repository is asked
    anything, so the comparison has to survive a symlink for the question to be reached at all.
    """
    a_plan = ImplementationPlan(tests_to_add=["tests/unit/test_a_new_thing.test.ts"])
    _every_test_is_where_the_suite_will_look_for_it(
        _a_clone_at(a_projects_root), a_plan, "the runner announced nothing this system can read"
    )
    return "accepted"


def test_a_symlinked_projects_root_is_answered_exactly_as_a_real_one(
    a_symlinked_projects_root: tuple[Path, Path],
) -> None:
    """The same plan, the same repository, and the same answer whether the root is a link.

    **The two answers are compared to each other, not to a list.** "A symlink does not raise
    Python's `ValueError`" is a weaker claim than "a symlink and a real path are
    indistinguishable", and only the second one would notice a fix that made the linked case
    pass by refusing everything.
    """
    the_real_one, a_link_to_it = a_symlinked_projects_root

    what_a_real_root_says: object
    what_a_linked_root_says: object

    for a_root, into in ((the_real_one, "real"), (a_link_to_it, "linked")):
        try:
            what_the_planner_said = _where_the_planner_believes_a_test_belongs(a_root)
        except Exception as a_problem:
            what_the_planner_said = f"{type(a_problem).__name__}: {a_problem}"
        if into == "real":
            what_a_real_root_says = what_the_planner_said
        else:
            what_a_linked_root_says = what_the_planner_said

    assert what_a_linked_root_says == what_a_real_root_says, (
        "a projects root reached through a symlink is the same directory and must be answered "
        "the same way. It is not: the confinement check resolves the path it is given and the "
        "comparison used the root unresolved, so on any machine where the two spellings differ "
        "the stage raised Python's own ValueError about a subpath — which is what a real run on "
        "macOS did, where /tmp is a link to /private/tmp. No unit test could find it, because "
        "every one of this repository's tests ran from an already-resolved tmp_path."
    )

    assert "is not in the subpath of" not in str(what_a_linked_root_says), (
        "the linked root produced a raw ValueError out of a stage rather than one of this "
        "system's named refusals. A refusal is a decision somebody can act on; a ValueError "
        "about a subpath is a bug wearing a decision's clothes."
    )


def test_the_security_analyst_is_shown_the_code_and_not_only_the_manifests(
    a_symlinked_projects_root: tuple[Path, Path],
) -> None:
    """The inspection a security analyst gets contains code the one a discovery gets does not.

    **Two inspections and one of them is bigger, which is the whole claim.** A discovery report
    is a summary of a repository's shape and this module's own note that source files are not in
    that inspection is right. A security analyst is asked about authentication and authorization
    and a manifest answers neither — so the two need different things and sharing one selection
    is what made a real run's gate refuse a whole report for reasoning from filenames.
    """
    the_real_one, _ = a_symlinked_projects_root
    the_clone = _a_clone_at(the_real_one)

    # A file whose name says it may hold something risky, which is the only signal there is
    # without reading every file in the repository.
    (the_clone.path / "web-app" / "src" / "lib").mkdir(parents=True)
    (the_clone.path / "web-app" / "src" / "lib" / "auth.js").write_text(
        "const secret = process.env.JWT_SECRET || 'dev-secret-change-me';\n"
        "export const SESSION_DAYS = 7;\n",
        encoding="utf-8",
    )

    what_discovery_sees = an_inspection_of(the_clone)
    what_security_sees = an_inspection_of_the_code(the_clone)

    assert "JWT_SECRET" in what_security_sees, (
        "the security analyst's inspection did not contain the auth file it was selected for. A "
        "model asked to find authentication problems while handed a directory listing and a "
        "package.json will reason from filenames, and a real run's gate refused a report for "
        "exactly that."
    )
    assert "JWT_SECRET" not in what_discovery_sees, (
        "discovery's inspection is a repository's shape and this module says on purpose that "
        "source files are not in it — a summary of a project is not a copy of it. If this fails, "
        "the two inspections have been merged and the security analyst's evidence is now paid "
        "for by every discovery call."
    )


def test_the_security_inspection_says_what_it_did_not_show(
    a_symlinked_projects_root: tuple[Path, Path],
) -> None:
    """The inspection ends by naming its own limits, in a section a reader can find.

    **This is the half that matters more than the code it carries.** A model shown files it was
    not shown cannot tell that it was not shown them, and neither can a reader — which is how a
    report about a repository that was never read reaches a gate looking like a report about one
    that was. With the section present, the same model on the same repository reported the limit
    of its own evidence ("this is a gap in what I was shown, not a defect I observed") instead
    of filing speculation as a finding.
    """
    the_real_one, _ = a_symlinked_projects_root
    what_security_sees = an_inspection_of_the_code(_a_clone_at(the_real_one))

    assert "# What you were not shown" in what_security_sees, (
        "the inspection has to end by naming what it left out. Without it a report reasoning "
        "about a file nobody was shown is indistinguishable from one reasoning about a file "
        "somebody was, and that is the finding the real run's gate had to make by reading the "
        "report line by line."
    )
    # And it has to be a claim about the inspection, not a heading with nothing under it.
    what_follows_the_heading = what_security_sees.split("# What you were not shown")[1]
    assert what_follows_the_heading.strip(), (
        "the section is empty, which says less than saying nothing at all — a reader has to be "
        "able to tell 'nothing was withheld' from 'this was not written'"
    )


def test_the_analyst_is_told_about_the_files_it_was_not_shown() -> None:
    """The prompt names the section, so the instruction is not only in the data.

    **A rule in an assertion rather than in prose that asks for it.** The prompt already forbade
    inventing paths, and a real run spent eight attempts on a test directory that did not exist
    because the prompt forbade it — the reason this repository treats a rule a prompt has to
    forbid as a rule a test has to assert. This is that test, and the wording in the prompt is
    left in place because it is the same rule said twice in two registers, one of which a reader
    of the report can check.
    """
    from aisdlc.agents.inspect_for_security_risk import the_prompt_to_inspect_for_security_risk

    the_prompt = the_prompt_to_inspect_for_security_risk(
        "# What you were not shown\n\nnothing",
        _a_repository_for_the_prompt(),
    )

    assert "NOT shown" in the_prompt or "not shown" in the_prompt, (
        "the analyst is not told that its evidence has limits. It is handed an inspection whose "
        "last section says so and a prompt that does not mention it, and a model weighs the two."
    )


def _a_repository_for_the_prompt():
    from aisdlc.domain.repository import Repository

    return Repository(owner="an", name="owner")


def test_the_projects_root_setting_is_the_only_reader_of_its_own_variable() -> None:
    """`AISDLC_PROJECTS_DIR` is read in one place, and a deployment change is one edit.

    **Parsed and not grepped, because a grep finds the word.** This file's own prose quotes the
    setting's name, a comment explaining a symlink quotes the path a deployment would set, and a
    substring search reports both as readers — which is how the first version of this test failed
    on a comment three lines above it. What it is after is a subscript of `os.environ` or a call
    to `os.getenv`, which is what "reading a variable" means.

    A second reader would be a second answer to "where do runs go", and the two would agree until
    a deployment pointed them at different directories — at which point a run's clone is in one
    place and its register in another, and neither is wrong.
    """
    the_readers: list[str] = []
    for a_module in (
        Path(__file__).resolve().parents[1].joinpath("src", "aisdlc").rglob("*.py")
    ):
        if _this_module_reads_the_setting(ast.parse(a_module.read_text(encoding="utf-8"))):
            the_readers.append(a_module.name)

    assert the_readers == ["the_project_directory.py"], (
        f"AISDLC_PROJECTS_DIR is read by {the_readers}, and the rule is that "
        "the_project_directory.py is the only one."
    )

    # And that one reader does answer, rather than only being the only candidate.
    os.environ["AISDLC_PROJECTS_DIR"] = "/somewhere/specific"
    try:
        assert where_projects_live() == Path("/somewhere/specific")
    finally:
        del os.environ["AISDLC_PROJECTS_DIR"]


def _this_module_reads_the_setting(the_tree: ast.AST) -> bool:
    """Whether any line of this module actually reads the setting, rather than naming it.

    **Both spellings, and matched on the object rather than the method name.** Python has
    `os.environ["X"]` and `os.environ.get("X")`, and the second one's AST puts `get` on the outer
    attribute and `os.environ` on its value — so a check that looks for the string `environ` in
    the method's own name finds neither spelling and reports a module that reads the setting as
    one that does not. That is the same class of mistake as the grep this replaced, one level
    down, and the only way to see it is to run the test that came out of it.
    """
    for a_node in ast.walk(the_tree):
        if (
            isinstance(a_node, ast.Subscript)
            and _is_the_environment(a_node.value)
            and _is_the_setting(a_node.slice)
        ):
            return True

        if (
            isinstance(a_node, ast.Call)
            and a_node.args
            and _is_the_setting(a_node.args[0])
            and _reads_the_environment(a_node.func)
        ):
            return True

    return False


def _is_the_setting(a_node: ast.AST | None) -> bool:
    """Whether this expression is the setting's name."""
    return isinstance(a_node, ast.Constant) and a_node.value == "AISDLC_PROJECTS_DIR"


def _is_the_environment(a_node: ast.AST | None) -> bool:
    """Whether this expression is `os.environ` and nothing else.

    **The one on the left of a subscript.** `os.environ["X"]` puts the environment on the
    subscript's value, and there is no method to allow for.
    """
    return (
        isinstance(a_node, ast.Attribute)
        and a_node.attr == "environ"
        and isinstance(a_node.value, ast.Name)
        and a_node.value.id == "os"
    )


def _reads_the_environment(a_node: ast.AST | None) -> bool:
    """Whether this expression is a lookup on the environment, whatever the method is called.

    **`os.environ.get` and `os.getenv` both answer here.** The method's own name is not what
    makes it an environment read, and keying on it is how `os.environ.get` gets missed by a
    check written for `os.getenv` — which is what happened the first two times this test ran.
    """
    if isinstance(a_node, ast.Name):
        return a_node.id == "os.environ"

    if not isinstance(a_node, ast.Attribute):
        return False

    if isinstance(a_node.value, ast.Name) and a_node.value.id == "os":
        return a_node.attr == "getenv"

    return _is_the_environment(a_node.value)


def test_a_card_says_how_long_a_run_has_been_on_the_step_it_is_on() -> None:
    """A card carries the step and the minutes on it, and a run that says nothing carries neither.

    **A real run spent twenty minutes inside one node and the board said "working" for all of
    it.** A run's own record carries a timestamp on every line, so the answer was in the store
    the whole time; what was missing was a card that read it. A person who can see "20 minutes on
    the planner" can decide whether that is slow or wrong, and a person shown the word "working"
    can decide neither — which is the only reason this is on a card rather than in a log.

    **Both fields are `None` together, and never one without the other.** A step with no time is
    a step from a run that has not moved since it started, and a time with no step is a number
    against nothing.
    """
    from aisdlc.store.the_board_reads import _how_long_on_this_step, _the_step_it_is_on
    from aisdlc.store.the_record_of_a_run import WhatARunSaid

    def an_event(what_happened: str, seconds_ago: int) -> WhatARunSaid:
        from datetime import UTC, datetime, timedelta

        return WhatARunSaid(
            what_happened=what_happened,
            happened_at=datetime.now(UTC) - timedelta(seconds=seconds_ago),
        )

    assert _the_step_it_is_on([]) is None
    assert _how_long_on_this_step([]) is None

    the_events = [
        an_event("a person asked for this", 900),
        an_event("ran offer_the_work_item_to_discover", 880),
        an_event("wrote DiscoveryReport", 860),
        an_event("ran apply_the_pickup", 840),
    ]

    assert _the_step_it_is_on(the_events) == "apply_the_pickup", (
        "the step is the last `ran <node>` line and not the last line of any kind: a run that "
        "wrote an artifact and is now inside the next node is on the node, and a card saying "
        "'wrote DiscoveryReport' for nine minutes is a card that cannot answer what it is asked"
    )

    how_long = _how_long_on_this_step(the_events)
    assert how_long is not None
    # Polling twice reads the clock twice; the band is generous enough to hold both.
    assert 800 <= how_long <= 900, f"a run 840s into its step reported {how_long}s on it"

    # A record of only sentences — no node has run yet — has no step and therefore no duration.
    only_sentences = [an_event("a person asked for this", 10)]
    assert _the_step_it_is_on(only_sentences) is None
    assert _how_long_on_this_step(only_sentences) is None


def test_a_card_never_names_a_framework_node_as_a_step() -> None:
    """`__interrupt__` is LangGraph's internal name and a card must not show it.

    **It appeared on a real card, reading "on `__interrupt__`".** The run's record says a node
    ran; when a run parks at a gate, the node that "ran" is the framework's own, and a double
    underscored name is the one signal this system has that the name is not about this system's
    work. A card names steps a person could act on, and says nothing rather than showing a
    framework's spelling to the one reader who cannot do anything with it.
    """
    from datetime import UTC, datetime

    from aisdlc.store.the_board_reads import _the_step_it_is_on
    from aisdlc.store.the_record_of_a_run import WhatARunSaid

    def an_event(what_happened: str) -> WhatARunSaid:
        return WhatARunSaid(what_happened=what_happened, happened_at=datetime.now(UTC))

    the_events = [
        an_event("ran offer_the_work_item_to_discover"),
        an_event("ran discover_the_repository"),
        an_event("ran __interrupt__"),
    ]

    assert _the_step_it_is_on(the_events) == "discover_the_repository", (
        "a framework's own node was shown to a person as the step this run is on. A run parked at "
        "a gate has `__interrupt__` as its last node and a card that says so is naming "
        "LangGraph's internals to the one reader who cannot do anything with them"
    )
    assert _the_step_it_is_on([an_event("ran __interrupt__")]) is None
