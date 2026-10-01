"""A Python repository's suite is run with its own tools, because this one is.

**The runner was npm-only and said so in a comment nobody had acted on.** `run_tests.py` held
`THE_SUITE_THAT_THIS_REPOSITORY_DEFINES = ("npm", "test")`,
`THE_INSTALL_THAT_FETCHES_PACKAGES = ("npm", "ci")` and a fallback image of `node:22-bookworm`,
beside a comment saying that a repository whose suite is `pytest` has no such mode and that
`a_listing_command_for_a_toolchain` was "where that question is asked and answered". That
function did not exist, and the consequence was not subtle: **a verification of any change to this
repository installed nothing, ran nothing, went red, and the delivery refused it.** Nothing this
system could change about itself was deliverable.

**The image was already read out of the repository and the other three answers were not.** That
inconsistency is the finding — "the toolchain is declared, not remembered" was true of one answer
out of four — so these tests read a real checkout and assert all four together, which is the shape
a caller gets them in.
"""

from __future__ import annotations

from pathlib import Path

from aisdlc.tools.run_tests import (
    HowThisRepositoryIsTested,
    how_this_repository_is_tested,
    the_test_files_the_suite_reported_running,
)

A_CHECKOUT_HOLDING_ONLY_A_PYPROJECT = """
[project]
name = "a-project"
"""


def _a_checkout(*what_it_declares: str, tmp_path: Path) -> str:
    for a_declaration in what_it_declares:
        (tmp_path / a_declaration.split("::", 1)[0]).write_text(
            a_declaration.split("::", 1)[1], encoding="utf-8"
        )
    return str(tmp_path)


def test_a_repository_declaring_pyproject_is_run_with_pip_and_pytest(tmp_path: Path) -> None:
    """**This repository, read as a repository.** `pyproject.toml` is the declaration, and it is
    the same test a future repository would get from the same rule.
    """
    the_checkout = _a_checkout(
        f"pyproject.toml::{A_CHECKOUT_HOLDING_ONLY_A_PYPROJECT}", tmp_path=tmp_path
    )

    how_it_is_tested = how_this_repository_is_tested(the_checkout)

    assert how_it_is_tested.toolchain_image.startswith("python:"), (
        f"a repository declaring pyproject.toml was verified on "
        f"{how_it_is_tested.toolchain_image!r}, which has no pip and no pytest in it"
    )
    assert how_it_is_tested.installation_command[:5] == (
        "python",
        "-m",
        "pip",
        "install",
        "-e",
    ), f"a Python repository was installed with {how_it_is_tested.installation_command!r}"
    assert how_it_is_tested.suite_command == ("python", "-m", "pytest", "-q"), (
        f"a Python repository's suite was run with {how_it_is_tested.suite_command!r}"
    )


def test_a_repository_declaring_package_json_is_still_run_with_npm(tmp_path: Path) -> None:
    """**And the node path is untouched**, because a fix that breaks the working half is not a fix.

    The real runs this repository inherited were all node, and `node:22-bookworm` with `npm ci`
    and `npm test` is what kept them working.
    """
    the_checkout = _a_checkout('package.json::{"name": "a-project"}', tmp_path=tmp_path)

    how_it_is_tested = how_this_repository_is_tested(the_checkout)

    assert how_it_is_tested.toolchain_image == "node:22-bookworm"
    assert how_it_is_tested.suite_command == ("npm", "test")


def test_the_four_answers_come_back_together_and_are_one_fact(tmp_path: Path) -> None:
    """**Why the model exists and not four arguments.**

    `pip install -e .` inside `node:22-bookworm` is not a configuration anybody chose — it is
    what you get when each answer has its own default and none of them has an owner. This is the
    assertion that the answers arrive as one value.
    """
    how_it_is_tested = how_this_repository_is_tested("/nowhere/at/all")

    assert isinstance(how_it_is_tested, HowThisRepositoryIsTested)
    assert len(type(how_it_is_tested).model_fields) == 4


def test_pytests_own_collection_listing_is_read_for_the_files_it_named() -> None:
    """**The shape is `path::test_name`, and the file is everything before the `::`.**

    pytest's output shares nothing with a node suite's marks, so a parser that understood one
    reported nothing for the other — and "nothing" is the answer that makes an uncollected test
    look like a suite that passed over it.
    """
    what_pytest_said = (
        "tests/test_the_guard.py::test_a_refusal_is_named\n"
        "tests/test_the_guard.py::test_the_clone_is_read_only\n"
        "tests/unit/test_another.py::test_one\n"
        "\n"
        "68 tests collected in 3.11s\n"
    )

    the_files = the_test_files_the_suite_reported_running(what_pytest_said)

    assert the_files == ["tests/test_the_guard.py", "tests/unit/test_another.py"], (
        f"pytest named two files and the reader found {the_files}, so an uncollected test would "
        "look like a suite that passed over it"
    )


def test_the_summary_line_pytest_ends_with_is_not_read_as_a_file() -> None:
    """**A line of prose is not a path**, and one in that list is worse than an empty list."""
    the_files = the_test_files_the_suite_reported_running("68 tests collected in 3.11s\n")

    assert the_files == [], f"a summary line was read as a test file: {the_files}"


def test_a_node_suites_marks_are_still_read_as_before() -> None:
    """**The three marks and the string they were read out of, both paths.**

    A fourth mark was once written from memory and appears in no real output; this is the shape
    that was quoted from a container, and it has to keep working.
    """
    what_vitest_said = "\n".join(
        [
            "  \u2713 tests/unit/thing.test.ts (3)",
            "  \u00d7 tests/unit/broken.test.ts (1)",
            "  \u2193 tests/integration/optional.test.ts (2) skipped",
            "",
        ]
    )

    assert the_test_files_the_suite_reported_running(what_vitest_said) == [
        "tests/unit/thing.test.ts",
        "tests/unit/broken.test.ts",
        "tests/integration/optional.test.ts",
    ]
