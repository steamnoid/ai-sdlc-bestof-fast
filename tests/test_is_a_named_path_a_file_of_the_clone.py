"""Every way a named path can be right, and every way it can be wrong, in one file.

**These are the cases the pair tier got wrong three times.** Each one is a real agent output
observed on a real run, so each is a case that happened rather than one invented to be tidy —
which is the only kind worth writing down, because the two invented ones would have passed the
version of the function that was broken.
"""

from __future__ import annotations

from tests.is_a_named_path_a_file_of_the_clone import (
    is_named_in_the_clone,
    the_paths_named_in,
)

WHAT_THE_CLONE_HOLDS = {
    ".github/workflows/gate.yml",
    "src/aisdlc/tools/run_command.py",
    "src/aisdlc/tools/run_tests.py",
    "tests/test_what_two_real_runs_found.py",
    "README.md",
}


def test_an_exact_citation_is_grounded() -> None:
    assert is_named_in_the_clone("src/aisdlc/tools/run_command.py", WHAT_THE_CLONE_HOLDS)


def test_a_citation_that_dropped_the_leading_dot_is_grounded() -> None:
    """What a real run reported as invented: the file is `.github/workflows/gate.yml`.

    **A first fix for this used `lstrip("./")` on the whole string, which does nothing** — the dot
    is at the front of the first *component*, not at the front of the string. Comparing component
    by component is the only thing that gets it, and that is why this case is written down.
    """
    assert is_named_in_the_clone("github/workflows/gate.yml", WHAT_THE_CLONE_HOLDS)


def test_a_citation_naming_a_file_the_clone_does_not_have_is_not_grounded() -> None:
    """What a real run found: an agent cited `docs/domain-glossary.md`, which is not here.

    **The one real failure this function ever reported, and it must stay reported.** The check is
    only worth having if a path nobody has read is refused, so the negative case is asserted
    rather than left implied by the positives passing.
    """
    assert not is_named_in_the_clone("docs/domain-glossary.md", WHAT_THE_CLONE_HOLDS)


def test_a_citation_naming_fewer_components_than_the_real_path_is_refused() -> None:
    """A suffix is a suffix: `tools/run_command.py` is not `src/aisdlc/tools/run_command.py`.

    **Asserted because loosening the matcher is the obvious way to fix a false failure**, and the
    obvious fix is wrong — it makes every invented path that happens to end in a real filename
    pass, which is precisely what the check exists to catch.
    """
    assert not is_named_in_the_clone("tools/run_command.py", WHAT_THE_CLONE_HOLDS)


def test_a_link_to_a_file_is_not_a_path_in_the_repository() -> None:
    """What a real run reported as invented: a correct citation, written as a blob URL."""
    the_texts = [
        "the gate runs in "
        "github.com/steamnoid/ai-sdlc-bestof-fast-selfaware/blob/main/"
        ".github/workflows/gate.yml and it is required"
    ]

    assert the_paths_named_in(the_texts) == set()
    assert the_paths_named_in(["see .github/workflows/gate.yml for the gate"]) == {
        ".github/workflows/gate.yml"
    }


def test_an_extensionless_mention_is_not_a_citation() -> None:
    """What a real run reported as invented: an agent saying the tests run in a Dockerfile."""
    assert the_paths_named_in(["the suite runs in a Dockerfile"]) == set()
    assert the_paths_named_in(["as docker/Dockerfile shows"]) == {"docker/Dockerfile"}
