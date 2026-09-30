"""How much a security finding should worry the person reading it.

The vocabulary is ours and not the specification's: §10 asks for severity and §18 asks for
*severity consistency* between runs, and a consistency measure needs a closed set to measure
consistency over. A free-text severity would be the one field in
the artifact that could not be compared with any other run.

**Five, and the fifth was added because a real run needed it.** The model analysing a real
repository classified something as `informational` — an observation, not a risk at any of the
other four — and the answer was refused. A closed set that cannot express an observation forces
a model to call an observation a `low`, and a report that bends severities to fit a vocabulary
is a report whose severities mean nothing. `informational` is the word advisory tools and CVE
records already use for exactly this, so the vocabulary was short rather than the model wrong.
"""

from __future__ import annotations

from enum import StrEnum


class Severity(StrEnum):
    """How much a finding should worry a person, as a closed set rather than a phrase."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"
