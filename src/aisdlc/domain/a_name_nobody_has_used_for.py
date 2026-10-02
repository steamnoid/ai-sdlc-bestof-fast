"""A name nobody has used, built once.

**A work item's id is four things at once** — a directory under the projects root, a branch, a
LangGraph `thread_id` and the key the API addresses a run by — so a collision is not a
duplicate name, it is a second run writing over the first one's state.

**This existed in three copies and two of them were wrong.** The API and the CLI both wrote
`{repo}-{slug}-{YYYYMMDD-HHMMSS}` at second resolution, and their docstrings promised "a name
nobody has used", which was not true: two work items commissioned for the same request inside one
second got one name. **CI found it**, not a test — the whole-run test lost a gate to a 409,
because a decision posted for a closed gate is refused, and that is what a collision looks like
from the outside.

The third copy, in `a_repository_briefing_itself`, already had the fix and its comment said the
moment was what made the name unique: microseconds. Three near-identical builders, one correct,
and nobody could see the other two because they sat in two different modules.

**So one function, three callers, and the uniqueness is a property of this file rather than of
three places agreeing to be careful.**
"""

from __future__ import annotations

from datetime import UTC, datetime

from aisdlc.domain.repository import Repository

HOW_MUCH_OF_THE_REQUEST_IS_KEPT = 48


def a_name_nobody_has_used_for(repository: Repository, what_was_asked_for: str) -> str:
    """A name that is a directory, a branch, a thread and an API key all at once.

    **The slug is the request, cut word by word, and the moment is what makes it unique.** The
    request is what a person reads in a list of branches, so a long sentence is a line that wraps;
    everything that is not a letter or a digit becomes a dash, and only the first
    `HOW_MUCH_OF_THE_REQUEST_IS_KEPT` characters are kept.

    **Microseconds, and that is the whole fix.** At second resolution two work items asked for the
    same thing in the same second are the same work item. This has been the shape of the name
    since the first delivery, and a name used as a directory has to be unique the way a key has
    to be unique, not merely probably.
    """
    the_moment = datetime.now(UTC)
    the_words = "".join(
        a_character if a_character.isalnum() else "-" for a_character in what_was_asked_for.lower()
    )
    the_slug = "-".join(
        a_part for a_part in the_words.split("-") if a_part
    )[:HOW_MUCH_OF_THE_REQUEST_IS_KEPT].strip("-")

    return f"{repository.name}-{the_slug}-{the_moment:%Y%m%d-%H%M%S-%f}"
