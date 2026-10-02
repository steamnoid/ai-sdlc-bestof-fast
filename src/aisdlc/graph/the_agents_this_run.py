"""The agents a run reasons with, named by what each of them is asked for.

**This exists because `the_lifecycle` had nine parameters and ruff refused the fifth, which
was the rule being right.** Seven of those were collaborators — a discovery, four analysis
agents, a planner and an implementer — and a reader of a test calling that function saw a wall
of names with no indication that they were one thing: the cast of a run.

They are one thing, and §10 lists them. So the graph is handed its cast as a named model
rather than as seven keywords, and a test says which agents it wants by saying which cast it
wants.

**The field names are what each agent is asked for, not how it works.** `propose_requirements`
is what the product analyst does, not `analyze`; a field named after a technique would be a
field whose name a reader has to translate before they know what it is for. The four analysis
fields are also the four disciplines of `Role` the pipeline spends its gates on, which is the
same fact written twice — once as an agent identifier and once as the role accountable for the
work — and writing it twice is better than one name standing for both.

**No default, and that is the point.** The three collaborators this replaces had no defaults
so that a test has to say out loud which model reasons, which one plans and which one writes.
This model keeps that: a run cannot be built without naming its agents, so nothing reaches a
model by accident.

**The field types are the nodes' own seams**, so a change to a node's signature is a change to
this model and mypy says so rather than a reader discovering it at the edge.
"""

from __future__ import annotations

from pydantic import BaseModel

from aisdlc.graph.analyze_node import Analyze
from aisdlc.graph.apply_node import ApplyAndVerify
from aisdlc.graph.architecture_node import AnalyzeTheArchitecture
from aisdlc.graph.discover_node import Discover
from aisdlc.graph.plan_node import PlanTheChange
from aisdlc.graph.qa_node import AnalyzeTheRequirements
from aisdlc.graph.security_node import InspectForSecurityRisk
from aisdlc.graph.settle_a_conflict_node import (
    SettleTheConflict,
    no_model_was_given_to_settle_a_conflict,
)
from aisdlc.graph.supervise_a_repair import (
    SuperviseARepair,
    no_supervisor_was_given_to_this_run,
)


class TheAgentsThisRun(BaseModel):
    """Every collaborator that reasons, named by what it is asked for."""

    discover: Discover
    propose_requirements: Analyze
    plan_the_tests: AnalyzeTheRequirements
    describe_the_architecture: AnalyzeTheArchitecture
    inspect_for_security: InspectForSecurityRisk
    plan: PlanTheChange
    apply_and_verify: ApplyAndVerify
    supervise: SuperviseARepair = no_supervisor_was_given_to_this_run
    settle_a_conflict: SettleTheConflict = no_model_was_given_to_settle_a_conflict
