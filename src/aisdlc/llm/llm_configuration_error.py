"""The one error a misconfigured model may raise, kept apart so both raisers can use it.

It lives in its own module because two modules raise it: the one that reads what a
deployment stated, and the one that builds the model. Giving it a home in either would
make the other import across the seam, and an error type is exactly the thing that must
not sit on a cycle.
"""

from __future__ import annotations


class LlmConfigurationError(Exception):
    """The provider abstraction, and the only thing that may say a provider is wrong.

    It covers two faults, because they are the same fault seen from two sides: naming a
    provider this system cannot reach, and naming one that cannot answer without being
    told where. Both are answered before any network call, so both are a decision about
    configuration rather than a failure of a model.
    """
