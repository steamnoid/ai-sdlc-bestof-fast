"""Which agent sits next to which, and what one has to be able to tell the next.

**Two agents, and everything else mocked.** The unit here is a *neighbouring pair*: the two
agents the pipeline runs back to back. Both reason for real; the clone is a fixture, and the
graph, the register, the project directory, git, the container and GitHub are all absent —
which is what makes the isolation free, because the one process-wide thing in this system (the
register's single connection) is never opened.

**The list lives in the default tier, not in the e2e one, and that is the whole point of it.**
A guard that says "every neighbouring pair has a case" is worth nothing if it only runs when a
credential is present: it would be green in CI precisely when nobody is looking. So the list and
the guard over it need no network and no key, and the e2e file imports them.

**The order is the pipeline's own, not a list someone typed.** `THE_AGENTS_IN_THE_ORDER_THE_
PIPELINE_RUNS_THEM` is checked against `WHERE_AN_APPROVED_ARTIFACT_LEADS` in
`tests/test_every_declared_neighbouring_pair_has_a_case.py`, so a stage added to the router
cannot slip past this tier: the sequence and the pairs both move or the guard fails.
"""

from __future__ import annotations

from pydantic import BaseModel


class ANeighbouringPair(BaseModel):
    """Two agents the pipeline runs one after the other, and what crosses between them.

    **`what_crosses` is the claim under test, and it is deliberately per pair.** The stages are
    consecutive but the data is not: only one pair hands the previous stage's artifact to the
    next agent, while three of the analysis agents re-read the clone independently. Asserting
    "the second agent receives the first agent's output" for every pair would assert a data flow
    this system does not have — and one of them (`SEC` → `plan`) is a gap rather than a design,
    which is why it is written down here as a claim to be proven false if it still holds.
    """

    first: str
    """The field name of the earlier agent in `TheAgentsThisRun`."""

    second: str
    """The field name of the later agent in `TheAgentsThisRun`."""

    what_crosses: str
    """What the later agent has to have been given, in the domain's own words."""


THE_AGENTS_IN_THE_ORDER_THE_PIPELINE_RUNS_THEM = (
    "discover",
    "propose_requirements",
    "plan_the_tests",
    "describe_the_architecture",
    "inspect_for_security",
    "plan",
    "apply_and_verify",
)

# **Six positions, and `SEC` -> `plan` is the one that is a gap rather than a shape.** The other
# five are checks that could pass today. This one states what the planner must have been given
# and does not have it: `PlanTheChange` takes `(requirements, clone, repository, question)`,
# `SecurityReport` is not among them, and the fourth argument is
# `THE_RUNNER_ANNOUNCED_NOTHING_YET`, which is the empty string. **Three gates approve a
# `SecurityReport` that the agent writing the code has never read.**
THE_NEIGHBOURING_PAIRS = (
    ANeighbouringPair(
        first="discover",
        second="propose_requirements",
        what_crosses=(
            "nothing: the product analyst is handed the clone and the commissioned request, "
            "not the DiscoveryReport, so what it must not do is claim anything about a file "
            "neither of them was shown"
        ),
    ),
    ANeighbouringPair(
        first="propose_requirements",
        second="plan_the_tests",
        what_crosses=(
            "the Requirements: every acceptance criterion the product analyst set must have at "
            "least one scenario behind it, because this is the only pair in the pipeline where "
            "one agent's artifact really is the next agent's input"
        ),
    ),
    ANeighbouringPair(
        first="plan_the_tests",
        second="describe_the_architecture",
        what_crosses=(
            "the clone, not the QaPlan: so every path a scenario names has to be a module or a "
            "named boundary the architecture report mentions, or the QA analyst was planning "
            "tests against a thing nobody described"
        ),
    ),
    ANeighbouringPair(
        first="describe_the_architecture",
        second="inspect_for_security",
        what_crosses=(
            "the clone, not the ArchitectureReport: so every file a SecurityFinding's signal "
            "names has to be a module or boundary the architecture report lists, or the "
            "security analyst reported on something the architecture does not contain"
        ),
    ),
    ANeighbouringPair(
        first="inspect_for_security",
        second="plan",
        what_crosses=(
            "the SecurityReport: the planning agent must have been given the findings its plan "
            "answers, because a plan that does not touch a file three gates have already agreed "
            "is insecure is a plan nobody was told not to write"
        ),
    ),
    ANeighbouringPair(
        first="plan",
        second="apply_and_verify",
        what_crosses=(
            "the ImplementationPlan: every path in files_to_change, files_to_add and "
            "tests_to_add has to be a file of the clone the implementer was shown, because a "
            "plan naming a path the repository does not have is applied to a checkout that "
            "cannot receive it"
        ),
    ),
)
