"""What the agent concluded, in the shape the model is asked to fill.

The artifact is `DiscoveryReport` and this is not it. The difference is the address:
an answer carries paths, because a path is something only the agent knows, and a report
carries addresses, because an address is derived from the repository and the system
should be the only thing that writes one. Asking a model for an address would be asking
it for a string it can invent, and a plausible invented host in front of an approver is
worse than no address at all.
"""

from __future__ import annotations

from pydantic import BaseModel

from aisdlc.agents.what_an_agent_judged import WhatAnAgentJudged


class DiscoveryAnswer(BaseModel):
    """The agent's conclusion, with the files it concluded from and nothing derived."""

    languages: list[str] = []
    frameworks: list[str] = []
    build_system: str | None = None
    ci_system: str | None = None
    architecture_summary: str = ""
    key_components: list[str] = []
    evidence_files: list[str] = []
    suggested_changes: list[str] = []
    judged: WhatAnAgentJudged
