"""Whether a repository is going to brief itself, and how many issues it may file.

**`on` is the only value that means on, and everything else is refused by name.** This is the one
setting in the repository where a fallback is the worst answer available, because it decides
whether a repository files issues about itself — a run with a truncated value would either file
nothing while a person watched a board expecting cards, or file five. Neither is recoverable from
the record afterwards, because the record only shows what happened.

**Absent and empty are two different facts.** Absent is a deployment that said nothing, and it gets
the default. Empty is a deployment that wrote the setting and put nothing in it — which is the shape
a truncated value actually takes — and a fallback there is a run that quietly got a default nobody
chose. So empty is refused.

**The count is a positive whole number and nothing else.** `0` is refused rather than read as *file
no issues*: a briefing that filed nothing because a deployment wrote a zero is a briefing that
looked broken, and the fix is in a configuration file.

**Read at the moment it is asked, never once at import**, because a deployment that changes this
between two runs is stating two runs' settings and a value frozen at import would answer the
second with the first.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

THE_SETTING_NAMING_CREATIVE_MODE = "AISDLC_CREATIVE_MODE"
THE_SETTING_NAMING_HOW_MANY_TO_FILE = "AISDLC_OPPORTUNITIES_TO_FILE"

# Lower case and one word, and the comparison is against the whole trimmed value. `On` and `ON` are
# refused, and that is deliberate: a setting that is case-insensitive is a setting two people can
# read two ways, and this one decides whether a repository writes to the outside world.
THE_ONLY_VALUE_THAT_MEANS_ON = "on"

# Five, because a briefing that proposes twenty is a backlog rather than a briefing, and one that
# proposes two is a suggestion. Five is also the number a person can read on a card.
HOW_MANY_OPPORTUNITIES_WHEN_NO_COUNT_IS_STATED = 5


class ACreativeSettingThatIsNotOnError(Exception):
    """A deployment set the creative mode to something that is not `on`, and the run stopped.

    **Raised rather than read as off**, and that is the whole of the rule. This is the one setting
    where a fallback is the worst available answer: it decides whether a repository files GitHub
    issues about itself, and either wrong answer leaves a person looking at a board that disagrees
    with a run's record. A run that stops and says which value to write is recoverable in one edit.
    """

    def __init__(self, stated: str) -> None:
        """Quote what was set, because the fix is in a deployment's own configuration file."""
        self.stated = stated
        super().__init__(
            f"{THE_SETTING_NAMING_CREATIVE_MODE} was read as {stated!r}, and the only value that "
            f"means on is {THE_ONLY_VALUE_THAT_MEANS_ON!r}. Leave the setting out for a run that "
            "starts from a request, and write it as that one word for a repository that briefs "
            "itself. Anything else is refused rather than read as off, because this setting "
            "decides whether a repository writes to the outside world and a wrong reading is not "
            "recoverable from the record afterwards"
        )


class ACountThatIsNotANumberError(Exception):
    """A deployment stated how many issues to file as something that is not a positive number."""

    def __init__(self, setting: str, stated: str) -> None:
        """Name the setting and quote the value, because both are what somebody has to edit."""
        self.setting = setting
        self.stated = stated
        super().__init__(
            f"{setting} was read as {stated!r}, which is not a whole number above zero. Write it "
            f"as one — {HOW_MANY_OPPORTUNITIES_WHEN_NO_COUNT_IS_STATED} is what you get for "
            f"saying nothing. Zero is refused rather than read as *file no issues*, because a "
            "briefing that filed nothing looks broken and the fix is in a configuration file"
        )


def is_creative_mode_on(environment: Mapping[str, str] | None = None) -> bool:
    """Whether a repository is going to brief itself before the product analyst starts.

    **`True` or it raises.** There is no third answer, and a caller that wanted a boolean has to
    decide what to do about a deployment that is wrong rather than being handed `False` and
    carrying on — a person watching a board cannot tell those two apart afterwards.
    """
    stated = _what_was_stated(THE_SETTING_NAMING_CREATIVE_MODE, environment)

    if stated is None:
        return False

    if stated != THE_ONLY_VALUE_THAT_MEANS_ON:
        raise ACreativeSettingThatIsNotOnError(stated)

    return True


def what_the_environment_allows(environment: Mapping[str, str] | None = None) -> int:
    """How many opportunities a briefing proposes, as a deployment states it.

    **A ceiling rather than a target,** and the analyst is still told to propose only what it can
    show files for. A deployment writing a high number gets a longer list of weaker opportunities;
    a deployment writing one gets the single best thing this repository could be given, which is
    usually the right answer and is never a thing a system should be told.
    """
    stated = _what_was_stated(THE_SETTING_NAMING_HOW_MANY_TO_FILE, environment)

    if stated is None:
        return HOW_MANY_OPPORTUNITIES_WHEN_NO_COUNT_IS_STATED

    if not stated:
        raise ACountThatIsNotANumberError(THE_SETTING_NAMING_HOW_MANY_TO_FILE, stated)

    try:
        how_many = int(stated)
    except ValueError as not_a_number:
        raise ACountThatIsNotANumberError(
            THE_SETTING_NAMING_HOW_MANY_TO_FILE, stated
        ) from not_a_number

    if how_many < 1:
        raise ACountThatIsNotANumberError(THE_SETTING_NAMING_HOW_MANY_TO_FILE, stated)

    return how_many


def _what_was_stated(setting: str, environment: Mapping[str, str] | None) -> str | None:
    """What a deployment wrote, trimmed, or `None` when it wrote nothing at all.

    **Absent and empty are different and both matter here.** Absent is a deployment that said
    nothing. Empty is a deployment that wrote the setting and put nothing in it, and this is the
    shape a truncated value actually takes — a shell that exported an empty variable, a `docker
    run` without `-e`. A fallback there is a run that quietly got a default nobody chose.
    """
    stated = dict(environment if environment is not None else os.environ).get(setting)
    if stated is None:
        return None
    return stated.strip()
