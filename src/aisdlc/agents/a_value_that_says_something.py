"""Whether a value carries anything a person could read.

One rule with three callers, and it is here because a real run found that all three had it
wrong. `DiscoveryReport`, `Requirements` and `QaPlan` each ask "does any field say
something?", and each answered with `any()` over the raw values — which is `True` for a
string of spaces. A QA plan whose entire test strategy was `" "` passed the rule, and a run
would have put it in front of a person to approve.

So the rule is not "is this value truthy" but "is there anything in it once whitespace is
gone", and the two are different questions. It lives in one module because a fourth artifact
would otherwise arrive with a fourth `any()`, which is how the first three all got it.
"""

from __future__ import annotations

from collections.abc import Iterable


def a_value_that_says_something(value: object) -> bool:
    """Whether there is anything in this value a person could read.

    Four kinds of value, four answers, and each is a value the domain actually uses:

    * `None` says nothing. It is absence, which this system represents deliberately —
      `DiscoveryReport.build_system` is `str | None` because a repository with no CI has
      nothing to say about CI — and absence is not emptiness.
    * text says something when a non-whitespace character is left after stripping.
    * a list says something when any one of its entries says something, so one real
      requirement among three blank strings is a run with one requirement.
    * anything else is said by the model rather than the domain, and is not guessed at: a
      report must not become approvable because a field holds a truthy object nobody read.
    """
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, Iterable):
        return any(a_value_that_says_something(entry) for entry in value)

    return False
