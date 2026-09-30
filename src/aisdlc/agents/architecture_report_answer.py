"""What the architecture analyst concluded, in the shape the model is asked to fill.

The artifact is `ArchitectureReport` and this is not it. The difference is what the glossary
does not name, which is the point of the split: the artifact's fields were fixed by
`docs/domain-glossary.md` and by a person, and a shape the model fills has nowhere to put
anything else.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from aisdlc.agents.what_an_agent_judged import WhatAnAgentJudged


class ArchitectureReportAnswer(BaseModel):
    """The architecture analyst's conclusion, carrying nothing the glossary did not name."""

    model_config = ConfigDict(extra="forbid")

    findings: list[str] = []
    modules: list[str] = []
    dependencies: list[str] = []
    boundaries: list[str] = []
    risks: list[str] = []
    judged: WhatAnAgentJudged
