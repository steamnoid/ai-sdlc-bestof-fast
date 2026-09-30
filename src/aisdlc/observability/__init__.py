"""Observability: what a run is doing, said while it is doing it.

Layer C in `AGENTS.md`'s own layering, and the layer this package exists for. A run makes seven
model calls, clones a repository and runs a container suite twice, and without this package
none of that is visible between the milestones — so a slow call, a hung gateway and a refused
request are the same three minutes of silence, and nobody watching can tell them apart.
"""

from __future__ import annotations
