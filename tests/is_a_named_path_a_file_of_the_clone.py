"""Whether a path an agent wrote names a file of the clone. Judged on its own, without a model.

**Three runs of the pair tier failed on this function and two of those failures were the function
being wrong, not an agent.** It is therefore tested here, in the default tier, where it costs
nothing and where the cases can be read:

- a first run reported two agents "inventing" `Dockerfile` in a repository that has none — which
  was an agent saying the tests run in a Dockerfile;
- the next reported a blob URL as an invented path, which is a link and not a path at all;
- the next reported `github/workflows/gate.yml` as invented, in a repository that holds
  `.github/workflows/gate.yml`, and my fix for that did not work because `lstrip("./")` strips
  characters from the left of the whole string and the dot is on the left of the *first
  component*.

**So the rule is component-wise, and a leading dot on any component is not a difference.** People
write `.github/…` and `github/…` for the same directory, and a check that fails on the difference
produces false failures — which is worse than no check, because a false failure is believed.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from pydantic import BaseModel

# A path as these artifacts write them: **at least one slash**, then a name with a known suffix.
# The slash is required because a mention and a citation are the same characters in a sentence,
# and an extensionless word like `Dockerfile` is a mention far more often than it is a path.
# A slash, then a known extensionless name. **The slash is the whole point of the second
# alternative**: `docker/Dockerfile` is a path a reader could open, while a bare `Dockerfile` in a
# sentence is a mention, and the two were reported as the same thing by a first run.

# **No `\\b` at the front**, and that is the second version of this regex rather than the first.
# `\\b` cannot match between a space and a dot, so `.github/workflows/gate.yml` came out as
# `github/workflows/gate.yml` — the dot was dropped by the *extraction*, and then the matcher's
# leading-dot rule was asked to repair damage this file had done. A lookbehind that excludes word
# characters, slashes and dots starts the match on the dot where the citation does.
WHAT_LOOKS_LIKE_A_PATH = re.compile(
    r"(?<![\w/.-])(?:[\w.-]+/)+[\w.-]+\.(?:py|md|toml|json|yaml|yml|ini|txt)\b"
    r"|(?<![\w/.-])(?:[\w.-]+/)+(?:Dockerfile|Makefile)\b"
)

# A link to a file is not a path in the repository, and the two are the same characters: an agent
# citing a workflow by its blob URL is citing it correctly.
WHAT_IS_A_LINK_RATHER_THAN_A_PATH = re.compile(
    r"(?:https?://|www\.)?[-.\w]*(?:github\.com|githubusercontent\.com)/\S*"
)


def the_paths_named_in(texts: list[str]) -> set[str]:
    """Every path these artifacts cite, with the links taken out first."""
    found: set[str] = set()
    for text in texts:
        without_the_links = WHAT_IS_A_LINK_RATHER_THAN_A_PATH.sub(" ", text)
        found.update(WHAT_LOOKS_LIKE_A_PATH.findall(without_the_links))
    return found


def _the_components_of(a_path: str) -> list[str]:
    """A path as a list of names, with a leading dot on any of them ignored.

    **Dots are only ignored at the front of a component**, never inside it: `run_command.py` and
    `run_commandXpy` are different files and must not match.
    """
    return [a_part.lstrip(".") for a_part in PurePosixPath(a_path).parts]


def is_named_in_the_clone(a_named_path: str, what_is_in_the_clone: set[str]) -> bool:
    """Whether a path an agent wrote names a file of the clone.

    **Component-wise, and the same number of components.** `github/workflows/gate.yml` is grounded
    by `.github/workflows/gate.yml` because the three components are equal once the leading dot is
    ignored. `tools/run_command.py` is *not* grounded by
    `src/aisdlc/tools/run_command.py`, because that is two components against four.

    **A suffix match would have let that second one through**, which is why the count is compared:
    loosening the matcher is the obvious way to fix a false failure, and the obvious fix makes
    every invented path that ends in a real filename pass — which is the one thing the check
    exists to catch. A citation naming fewer components than the real path is an abbreviation a
    reader could not open, so it is refused rather than guessed at.
    """
    the_named = _the_components_of(a_named_path)

    for a_path_in_the_clone in what_is_in_the_clone:
        if a_path_in_the_clone == a_named_path:
            return True
        if _the_components_of(a_path_in_the_clone) == the_named:
            return True
    return False


class HowANamedPathIsWrong(BaseModel):
    """What is wrong with a path an agent wrote, in enough detail to act on.

    **There are two of these and collapsing them into one loses the only thing a reader needs.**
    A file that is not in the clone at all is an agent inventing something. A file that *is* in
    the clone but was named with a prefix missing is an agent who knows the file and wrote it the
    way people write paths when they are typing. The first is a hallucination and the second is
    carelessness, and the remedy is different: one is a prompt problem and the other is a rule
    about how to write a citation.

    **Both are refused. Neither is excused.** A reader holding `aisdlc/agents/x.py` cannot open
    it, and a traceability chain is only worth anything if every link in it opens. But the report
    says which of the two it is, because a red run that says "invented" about a real file is a
    red run nobody believes the next time.
    """

    is_in_the_clone: bool
    how: str


def how_a_named_path_is_wrong(
    a_named_path: str, what_is_in_the_clone: set[str]
) -> HowANamedPathIsWrong | None:
    """`None` when the path is fine, and otherwise what is wrong with it and which file it meant.

    **The search for the file it meant runs on the trailing components, and stops at two.** A path
    that ends in the same two components as a file in the clone is that file, named from the
    inside out; one that shares nothing with anything is an invention. Both are reported, and the
    second one carries the real path so a reader can check the claim rather than take it.
    """
    if is_named_in_the_clone(a_named_path, what_is_in_the_clone):
        return None

    the_named = _the_components_of(a_named_path)

    for a_path_in_the_clone in what_is_in_the_clone:
        what_is_there = _the_components_of(a_path_in_the_clone)
        the_tail = min(2, len(the_named))
        if what_is_there[-the_tail:] == the_named[-the_tail:]:
            return HowANamedPathIsWrong(
                is_in_the_clone=True,
                how=(
                    f"the clone holds it as {a_path_in_the_clone!r}, so the agent knew the file "
                    "and wrote a path from the inside out"
                ),
            )

    return HowANamedPathIsWrong(
        is_in_the_clone=False,
        how="no file in the clone shares even its last two path components with that",
    )
