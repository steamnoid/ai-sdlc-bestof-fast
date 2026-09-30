"""Which organisation is asked to do the reasoning. A closed set of three.

The values are the strings an operator writes in `LLM_PROVIDER`, and they are lower
case for that reason: this set is read from the environment, not printed in a trace.

`openai_compatible` is a provider of its own rather than a flag on `openai`, because a
self-hosted model reached over an OpenAI-shaped HTTP API is a different thing to reach:
it runs somewhere else, it authenticates differently if at all, and it is the provider
that proves nothing in this system is tied to a company.
"""

from __future__ import annotations

from enum import Enum


class LlmProvider(Enum):
    """The organisation whose model does the reasoning."""

    OPENAI = "openai"
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"
    OPENAI_RESPONSES = "openai_responses"
