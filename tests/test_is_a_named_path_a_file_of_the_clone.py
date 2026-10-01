"""Every way a named path can be right, and every way it can be wrong, in one file.

**These are the cases the pair tier got wrong three times.** Each one is a real agent output
observed on a real run, so each is a case that happened rather than one invented to be tidy —
which is the only kind worth writing down, because the two invented ones would have passed the
version of the function that was broken.
"""

from __future__ import annotations

from tests.is_a_named_path_a_file_of_the_clone import (
    how_a_named_path_is_wrong,
    is_named_in_the_clone,
    the_paths_named_in,
)

# **A miniature of the real clone, and it has to contain the file each case is about.** The first
# version of this set had no `agents/` directory, so the case for a path missing its `src/` prefix
# reported the agent as having invented a file the miniature simply did not have. A fixture that
# is not representative produces confident nonsense.
WHAT_THE_CLONE_HOLDS = {
    ".github/workflows/gate.yml",
    "src/aisdlc/tools/run_command.py",
    "src/aisdlc/tools/run_tests.py",
    "tests/test_what_two_real_runs_found.py",
    "src/aisdlc/agents/what_an_agent_judged.py",
    "src/aisdlc/agents/requirements.py",
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


def test_a_path_whose_prefix_is_missing_names_a_real_file_and_says_so() -> None:
    """What a real run reported as invented, and it is not invented.

    **The agent wrote `aisdlc/agents/what_an_agent_judged.py` for a file this repository holds as
    `src/aisdlc/agents/what_an_agent_judged.py`.** It knew the file and lost a directory. Calling
    that an invented path is a false accusation, and a false accusation is worse than a missed one
    because it is believed.
    """
    what_is_wrong = how_a_named_path_is_wrong(
        "aisdlc/agents/what_an_agent_judged.py", WHAT_THE_CLONE_HOLDS
    )

    assert what_is_wrong is not None, "that path is not in the clone, so something must be said"
    assert what_is_wrong.is_in_the_clone, (
        f"{what_is_wrong.how} — but src/aisdlc/agents/what_an_agent_judged.py is in this clone, so "
        "the agent did not invent anything and the report must not say it did"
    )
    assert "src/aisdlc/agents/what_an_agent_judged.py" in what_is_wrong.how, (
        "the report has to name the real path, so a reader can check the claim rather than take "
        "it. A finding that says only 'wrong' is a finding nobody can act on"
    )


def test_a_path_matching_nothing_is_reported_as_invented() -> None:
    """What a real run found: `docs/domain-glossary.md`, which is not in this repository at all."""
    what_is_wrong = how_a_named_path_is_wrong("docs/domain-glossary.md", WHAT_THE_CLONE_HOLDS)

    assert what_is_wrong is not None
    assert not what_is_wrong.is_in_the_clone, (
        "nothing in the clone ends in domain-glossary.md, so this is the other fault and saying "
        "it is carelessness would let an invented file through"
    )


def test_a_correct_path_is_reported_as_nothing_wrong() -> None:
    assert how_a_named_path_is_wrong("src/aisdlc/tools/run_tests.py", WHAT_THE_CLONE_HOLDS) is None
