"""How a deployment says how many times a run may put an agent back on a work item.

The rule a deployment is stating is a ceiling on the supervisor's judgement, and it exists
because a model asked "is another attempt worth it?" has very little reason to say no: each
attempt looks reasonable on its own and the failure only changes shape. So the supervisor
decides, and this bounds it.
"""

from __future__ import annotations

import os

# Stated by a deployment rather than written here. The names in this package are its
# convention -- `AISDLC_CORRECTION_BUDGET` is the other one.
THE_SETTING_NAMING_THE_REPEAT_BUDGET = "AISDLC_REPEAT_BUDGET"

# What a deployment gets for saying nothing. Three because a second attempt at a stage is
# where a repair usually lands, and a third is where it is worth knowing the run cannot
# fix itself; every number past the second costs a repository's own suite in a container.
HOW_MANY_REPEATS_WHEN_NO_BUDGET_IS_STATED = 3

# Zero repeats means the count does not apply, rather than meaning "never repeat anything".
# A deployment lifting the ceiling writes `0`, and a system that read it as a prohibition
# would stop a run the moment a model got something wrong.
NO_REPEAT_APPLIES = 0


class ARepeatBudgetThatIsNotANumberError(Exception):
    """The rule is in this module: a budget is a number, and a word is not one.

    Raised rather than falling back to the default, because a fallback is invisible. A
    deployment whose `AISDLC_REPEAT_BUDGET` reads `unlimited` would otherwise be given
    three repeats and no sign of it, and would find out from a run that gave up after a
    repair that would have worked.
    """


def how_many_repeats_a_run_may_buy() -> int:
    """How many times a run may put an agent back on a work item, as a deployment states it.

    Read at the moment it is asked rather than once at import, because a deployment that
    changes a ceiling between two runs is stating two runs' ceilings, and a value frozen
    at import would answer the second with the first.
    """
    stated = os.environ.get(THE_SETTING_NAMING_THE_REPEAT_BUDGET)

    if stated is None:
        return HOW_MANY_REPEATS_WHEN_NO_BUDGET_IS_STATED

    try:
        return int(stated)
    except ValueError as not_a_number:
        raise ARepeatBudgetThatIsNotANumberError(
            f"{THE_SETTING_NAMING_THE_REPEAT_BUDGET} was read as {stated!r}, which is not a "
            f"number; a deployment states how many repeats a run may buy as a whole number, "
            f"or states 0 when the count does not apply"
        ) from not_a_number
