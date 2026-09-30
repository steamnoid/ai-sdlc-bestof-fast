"""The agents a run reasons with, named once, depending on nothing.

**These are a fact about a run and not about the graph.** They lived in `pickup_node`, which is
wiring, and that put a cycle in the way of `AgentState` naming one of its channels: a state
channel carrying a supervisor's answer needs that answer's type, and the answer's type needs the
list of agents it is required to cover.

The runtime resolves a `TypedDict`'s annotations when a graph is built, so a channel typed with
one of these has to be importable at runtime: `TYPE_CHECKING` is not enough, and a cycle is not
avoidable by hiding an import. The constants are here instead, depending on nothing, and
`pickup_node` re-exports them so the seventeen modules that already import them from there keep
doing so.
"""

from __future__ import annotations

THE_DISCOVER_AGENT = "aisdlc-discover"
THE_PRODUCT_ANALYST_AGENT = "aisdlc-po-analyze"
THE_QA_ANALYST_AGENT = "aisdlc-qa-analyze"
THE_ARCHITECTURE_ANALYST_AGENT = "aisdlc-arch-analyze"
THE_SECURITY_ANALYST_AGENT = "aisdlc-sec-analyze"
THE_DEVELOPER_PLANNING_AGENT = "aisdlc-dev-plan"
THE_DEVELOPER_IMPLEMENTATION_AGENT = "aisdlc-dev-impl"
THE_PULL_REQUEST_AGENT = "aisdlc-pr"

# **Seven and not eight, and the one left out is named where it is left out.** A verdict is
# required for every agent that reasons, and the pull request agent prepares a title, a body and
# a branch -- §10 gives it no reasoning to do, so a verdict about it would be a field the run
# cannot fill honestly.
THE_AGENTS_A_RUN_REASONS_WITH = (
    THE_ARCHITECTURE_ANALYST_AGENT,
    THE_DEVELOPER_IMPLEMENTATION_AGENT,
    THE_DEVELOPER_PLANNING_AGENT,
    THE_DISCOVER_AGENT,
    THE_PRODUCT_ANALYST_AGENT,
    THE_QA_ANALYST_AGENT,
    THE_SECURITY_ANALYST_AGENT,
)
