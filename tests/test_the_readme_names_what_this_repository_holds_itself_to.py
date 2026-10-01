"""The README has to name every test file here, because twice it did not.

**Two failures of the same kind, and this is the second guard for it.** The tag feature landed
with eleven tests and a commit message describing a README section that was never written — the
edit anchored on a heading from another repository's README, so it silently did nothing, and the
commit went through because an unrelated line in the same edit did land. Two days later the README
still said "four test files" when there were six. **Both times a count or a name in the README went
stale without anything noticing**, and a stale count is the kind of thing a reader trusts.

**So the check is mechanical rather than a habit.** Every `tests/*.py` is compared against the
README's table of what each file holds this repository to. A new test file with no row fails; a row
naming a file that no longer exists fails. Neither can be satisfied by editing prose, which is the
failure mode being guarded against.

**The table rather than a prose sentence, and that is the design.** A sentence can say "six test
files" and be wrong in a way no test can see; a table that has to list each one is wrong in a way
this can see. It also forces the useful half — saying what each file *holds the repository to*,
rather than what kind of test it is, which is the thing that goes stale when a file grows a second
purpose.
"""

from __future__ import annotations

import re
from pathlib import Path

THE_README = Path(__file__).resolve().parent.parent / "README.md"
THE_TESTS = Path(__file__).resolve().parent


def _the_test_files_that_exist() -> set[str]:
    return {
        a_file.name
        for a_file in sorted(THE_TESTS.glob("test_*.py"))
        if a_file.is_file()
    }


def _the_test_files_the_readme_names() -> set[str]:
    """Every `test_*.py` the README mentions in backticks, however it mentions it.

    **Any mention counts, not a table row.** The point is that a reader arriving at this repository
    can find the file from the README, and a guard that only accepted one particular format would
    fail on a perfectly good sentence.
    """
    what_the_readme_says = THE_README.read_text(encoding="utf-8")
    return set(re.findall(r"`(test_[a-z0-9_]+\.py)`", what_the_readme_says))


def test_the_readme_names_every_test_file_and_no_file_it_names_is_gone() -> None:
    assert _the_test_files_that_exist(), (
        "no test files were found, so this is comparing two empty sets and would pass forever"
    )

    the_files_that_exist = _the_test_files_that_exist()
    the_files_the_readme_names = _the_test_files_the_readme_names()

    undocumented = the_files_that_exist - the_files_the_readme_names
    assert not undocumented, (
        f"{', '.join(sorted(undocumented))} exists and the README does not say what it holds this "
        "repository to. A test file nobody can find is a claim nobody is reading, and this "
        "repository has now had a feature land that way — with a commit message describing "
        "documentation that was never written"
    )

    gone = the_files_the_readme_names - the_files_that_exist
    assert not gone, (
        f"the README names {', '.join(sorted(gone))} and there is no such file, so a reader is "
        "sent to look for something that is not there"
    )
