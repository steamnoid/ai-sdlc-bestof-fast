"""What the QA analyst concluded, in the shape the model is asked to fill.

The artifact is `QaPlan` and this is not it. The difference is what the glossary does not
name, which is the point of the split: the artifact's fields were fixed by
`docs/domain-glossary.md` and by a person, and a shape the model fills has nowhere to put
anything else. Discovery's and the product analyst's answers are closed for the same reason.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from aisdlc.agents.what_an_agent_judged import WhatAnAgentJudged


class QaPlanAnswer(BaseModel):
    """The QA analyst's conclusion, carrying nothing the glossary did not name."""

    model_config = ConfigDict(extra="forbid")

    test_strategy: str = ""
    scenarios: list[str] = []
    edge_cases: list[str] = []
    regression_risks: list[str] = []
    judged: WhatAnAgentJudged
