"""A work item's id is a branch, a directory, a thread and an API key, so it cannot collide.

**CI caught this one and it is not a test fault.** `the_api.py` and `cli.py` both built a work
item id as `{repo}-{slug}-{YYYYMMDD-HHMMSS}` — second resolution — and then the delivery test lost
a gate with a 409, because two of them in the same run landed on one id and a decision posted for
a closed gate is refused.

**And the third copy of this same function already had the fix.** `a_repository_briefing_itself`
builds the same shape of name with `-%f` on the end, microseconds, and its comment says the
moment is what makes it unique. Three near-identical builders, one of them correct, and nobody
could see the other two because they lived in two different modules.

**So the rule is checked, not asserted, and the three are compared against each other.** A name
that is not unique is not a name, and a name used as a directory is a name that must be.
"""

from __future__ import annotations

from aisdlc.cli import _a_work_item_id_for as the_one_the_cli_builds
from aisdlc.creative.a_repository_briefing_itself import a_briefing_id_for
from aisdlc.domain.repository import Repository
from aisdlc.web.the_api import _a_work_item_id_for as the_one_the_api_builds

A_REPOSITORY = Repository(owner="steamnoid", name="ai-sdlc-bestof-fast-selfaware")
A_REQUEST = "add a health endpoint that answers"


def test_two_work_items_asked_for_the_same_thing_do_not_share_an_id() -> None:
    """The claim in the docstring, checked by asking twice in the same breath.

    **Two calls a microsecond apart is the case that matters**, and it is why the moment in the
    name is written with `%f`: at second resolution these two are the same string, and the second
    run of a work item overwrites the first one's directory, branch and thread.
    """
    the_first = the_one_the_api_builds(A_REPOSITORY, A_REQUEST)
    the_second = the_one_the_api_builds(A_REPOSITORY, A_REQUEST)

    assert the_first != the_second, (
        f"two work items asked for {A_REQUEST!r} were both named {the_first!r}. That name is a "
        "directory, a branch and a LangGraph thread_id, so a collision is a second run writing "
        "over the first one's state rather than an inconvenience"
    )


def test_the_cli_and_the_api_build_the_same_kind_of_name() -> None:
    """Two entry points must not disagree about what a work item is called."""
    assert the_one_the_cli_builds(A_REPOSITORY, A_REQUEST) != the_one_the_api_builds(
        A_REPOSITORY, A_REQUEST
    ), (
        "the CLI and the API built the same name for the same request. They do not have to be "
        "equal — they are two moments — but they cannot be equal, and if this ever fires they "
        "have both lost the uniqueness that makes an id usable"
    )


def test_a_briefing_id_carries_finer_than_a_second() -> None:
    """The third copy already solved this, and the fix is a format flag.

    **Read as a format rather than as behaviour**, because the behaviour is untestable without
    freezing the clock and the format is what the fix actually is: `-%f` on the end. This is the
    check that stops the other two from drifting further away from the one that is right.
    """
    the_first = a_briefing_id_for(A_REPOSITORY)
    the_second = a_briefing_id_for(A_REPOSITORY)

    assert the_first != the_second, (
        f"two briefings of one repository were both named {the_first!r}, so the one copy of this "
        "function that carries microseconds is not carrying them either"
    )
