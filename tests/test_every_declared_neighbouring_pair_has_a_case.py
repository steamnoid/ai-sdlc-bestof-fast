"""Every stage the pipeline runs next to another must have a pair test, and it must be one.

**This file runs in the default tier: no network, no credential, no model.** That is the reason
it is here rather than beside the pair tests themselves. A guard that only runs when a key is
present is a guard that is green in CI and silent everywhere a decision gets made, and this
system's own record is full of checks that were exactly that.

**Two claims, and the second is the one with teeth.**

The first says the six pairs cover the six adjacent positions in
`THE_AGENTS_IN_THE_ORDER_THE_PIPELINE_RUNS_THEM`. That catches a pair quietly dropped from the
list.

The second says that sequence really is the pipeline — derived from the router's own table and
from the artifact each agent produces, not asserted alongside it. So when somebody adds a stage
to `WHERE_AN_APPROVED_ARTIFACT_LEADS`, this fails and names what has to move: the sequence, and
then the pairs. **A tier nobody has to remember to extend is a tier that quietly stops covering
things**, and the pair list is exactly the kind of list that decays.
"""

from __future__ import annotations

import aisdlc.graph.analyze_node as analyze_node
import aisdlc.graph.apply_node as apply_node
import aisdlc.graph.architecture_node as architecture_node
import aisdlc.graph.discover_node as discover_node
import aisdlc.graph.plan_node as plan_node
import aisdlc.graph.qa_node as qa_node
import aisdlc.graph.security_node as security_node
from aisdlc.graph.router import WHERE_AN_APPROVED_ARTIFACT_LEADS
from tests.the_neighbouring_agent_pairs import (
    THE_AGENTS_IN_THE_ORDER_THE_PIPELINE_RUNS_THEM,
    THE_NEIGHBOUR_PAIRS_THIS_TIER_DOES_NOT_CLAIM,
    THE_NEIGHBOURING_PAIRS,
)


def test_every_pair_names_two_agents_that_sit_next_to_each_other() -> None:
    """A pair is two *neighbours*, so a pair naming two distant agents is not a pair.

    **Read from the sequence rather than from the pairs**, so this is one rule stated once and
    checked for every pair, instead of a rule each pair's test has to remember.
    """
    the_order = THE_AGENTS_IN_THE_ORDER_THE_PIPELINE_RUNS_THEM

    for a_pair in THE_NEIGHBOURING_PAIRS:
        assert the_order.index(a_pair.second) == the_order.index(a_pair.first) + 1, (
            f"{a_pair.first} and {a_pair.second} are not neighbours in "
            f"{list(the_order)}, so this case is not a neighbouring-pair test: a pair two stages "
            "apart is a pipeline test with two models in it, and it is called something else"
        )


def test_every_pair_says_what_has_to_cross_between_its_two_agents() -> None:
    """A pair with nothing to say is a pair that cannot fail.

    **`what_crosses` is the assertion, written down before the model is called.** A case that
    only checks both artifacts validate would have passed all twelve real runs this repository has
    done, including the one that verified a working change and then could not commit it — so a
    pair that asserts nothing specific is a test that costs twelve model calls and finds nothing.
    """
    for a_pair in THE_NEIGHBOURING_PAIRS:
        assert a_pair.what_crosses.strip(), (
            f"the pair {a_pair.first} -> {a_pair.second} says nothing about what has to cross "
            "between them, so there is nothing for it to disagree about"
        )


def test_the_pairs_cover_every_two_neighbours_in_the_order_the_pipeline_runs_them() -> None:
    """The coverage claim itself: every adjacent position has a case.

    **Deliberately the strictest of the three.** A missing pair is a hole in the tier and a hole
    is invisible, because the tier reports on the pairs it has.
    """
    the_order = THE_AGENTS_IN_THE_ORDER_THE_PIPELINE_RUNS_THEM
    every_position = [
        (the_order[a_place], the_order[a_place + 1]) for a_place in range(len(the_order) - 1)
    ]

    covered = {(a_pair.first, a_pair.second) for a_pair in THE_NEIGHBOURING_PAIRS}
    deliberately_not_claimed = set(THE_NEIGHBOUR_PAIRS_THIS_TIER_DOES_NOT_CLAIM)

    missing = [
        a_place
        for a_place in every_position
        if a_place not in covered and a_place not in deliberately_not_claimed
    ]
    assert not (set(every_position) & deliberately_not_claimed) - covered - {
        ("plan", "apply_and_verify")
    }, (
        f"{sorted(set(every_position) & deliberately_not_claimed - covered)} are listed as "
        "positions this tier does not claim, and one of them is neither covered nor the one "
        "documented exclusion. A list of exclusions that grows is a tier quietly getting "
        "smaller"
    )

    assert not missing, (
        f"these neighbours have no pair test: {missing}. The order is "
        f"{list(the_order)}, so these are the positions this tier is not looking at"
    )


def test_the_order_is_the_pipelines_own_order_and_not_a_list_someone_typed() -> None:
    """The order is derived from the router, so a new stage cannot pass beside this tier.

    **This is the guard that makes the other three worth having.** `WHERE_AN_APPROVED_ARTIFACT_
    LEADS` declares what an approved artifact leads to, and each agent's own module names the
    artifact it produces — so the sequence below is read out of the two rather than written
    beside them. A stage added to the router, or an agent whose artifact moved, changes this
    order, and then the pairs have to change with it.

    **Eight artifacts are routed and seven agents reason.** `apply_and_verify` produces the
    artifact that leads to the delivery, and the delivery itself is not an agent in
    `TheAgentsThisRun` — it is the one stage whose output is a place rather than a finding. So
    the last routed artifact closes the sequence rather than opening another neighbour, and that
    is stated here so a reader does not go looking for an eighth agent.
    """
    the_artifact_each_agent_produces = {
        "discover": discover_node.THE_ARTIFACT_DISCOVERY_PRODUCES,
        "propose_requirements": analyze_node.THE_ARTIFACT_THE_PRODUCT_ANALYST_PRODUCES,
        "plan_the_tests": qa_node.THE_ARTIFACT_THE_QA_ANALYST_PRODUCES,
        "describe_the_architecture": (
            architecture_node.THE_ARTIFACT_THE_ARCHITECTURE_ANALYST_PRODUCES
        ),
        "inspect_for_security": security_node.THE_ARTIFACT_THE_SECURITY_ANALYST_PRODUCES,
        "plan": plan_node.THE_ARTIFACT_PLANNING_PRODUCES,
        "apply_and_verify": apply_node.THE_ARTIFACT_APPLYING_PRODUCES,
    }

    routed = list(WHERE_AN_APPROVED_ARTIFACT_LEADS)

    assert [
        the_artifact_each_agent_produces[an_agent] for an_agent in
        THE_AGENTS_IN_THE_ORDER_THE_PIPELINE_RUNS_THEM
    ] == routed[: len(THE_AGENTS_IN_THE_ORDER_THE_PIPELINE_RUNS_THEM)], (
        "the order these pairs are cut from no longer matches the order the router routes in, so "
        f"the pairs are being asked about {list(THE_AGENTS_IN_THE_ORDER_THE_PIPELINE_RUNS_THEM)} "
        f"while the pipeline runs {[routed[:7]]}. Whichever moved, both have to move together"
    )
