"""The agents of this run that leave a note on the card, and the one that does not.

**A list rather than a convention, and the one name in it is the whole point of the module.**
Every agent that reasons in this run is asked three questions about its own work and leaves the
answer on the work item's card. `aisdlc-sec-analyze` is not among them, and the reason is a
property of the protocol rather than an oversight: its answer is a bare array of findings, two
real runs sent a JSON array where an object was asked for, and adding three required fields to
that answer would spend the whole correction budget on packaging.

**A supervisor reading the card must be able to tell those two things apart.** A card with no
note from the security analyst means *this agent said nothing*, which is not the same as *this
agent had no doubt* — and a run that cannot tell them apart will read a missing note as a
reassurance it was never given. So the absence is named, the reason is here, and the list is
sorted so a reader comparing two runs is not reading an accident of declaration order.

`aisdlc-pr` is not here either, and for a different reason: §10 gives it four responsibilities
and not one is a model call, so it has nothing to say and asking would buy a call to hear it.
"""

from __future__ import annotations

from aisdlc.graph.pickup_node import (
    THE_ARCHITECTURE_ANALYST_AGENT,
    THE_DEVELOPER_IMPLEMENTATION_AGENT,
    THE_DEVELOPER_PLANNING_AGENT,
    THE_DISCOVER_AGENT,
    THE_PRODUCT_ANALYST_AGENT,
    THE_PULL_REQUEST_AGENT,
    THE_QA_ANALYST_AGENT,
    THE_SECURITY_ANALYST_AGENT,
)

THE_AGENTS_THAT_LEAVE_A_NOTE = (
    THE_DISCOVER_AGENT,
    THE_PRODUCT_ANALYST_AGENT,
    THE_QA_ANALYST_AGENT,
    THE_ARCHITECTURE_ANALYST_AGENT,
    THE_DEVELOPER_PLANNING_AGENT,
    THE_DEVELOPER_IMPLEMENTATION_AGENT,
)

# **A tuple and not a one-item tuple of reasons, and named as the absence it is.** The two
# names are here for two different reasons and a reader must be able to tell them: the first
# agent reasoned and its answer's shape cannot carry a note, and the second has nothing to say
# because §10 gives it no reasoning to do. A reader who finds the first missing from the card is
# told why; a reader who finds the second is not left wondering.
THE_AGENTS_THAT_LEAVE_NO_NOTE = (
    THE_SECURITY_ANALYST_AGENT,
    THE_PULL_REQUEST_AGENT,
)
