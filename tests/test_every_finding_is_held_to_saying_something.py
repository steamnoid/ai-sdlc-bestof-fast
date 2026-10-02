"""Every finding has to have said something, and the rule has to name fields that exist.

**This runs in the default tier: no network, no credential, no model.** That is the point of it.
The rule is applied by the pair tests to whatever a real model returned, and a rule that only
ever runs against a model is a rule nobody has read yet — so what is checked here is that the
mapping is real, and the pair tests do the rest.

**A rule naming a field that has been renamed is a rule that silently stopped applying.** That
is the whole failure this file exists to prevent, and it is why every entry names the field on
the model rather than a string the check happens to read.
"""

from __future__ import annotations

from aisdlc.agents.architecture_report import ArchitectureReport
from aisdlc.agents.discovery_report import DiscoveryReport
from aisdlc.agents.implementation_plan import ImplementationPlan
from aisdlc.agents.qa_plan import QaPlan
from aisdlc.agents.requirements import Requirements
from tests.what_an_artifact_must_have_said import WHAT_EVERY_FINDING_MUST_HAVE_SAID

EVERY_FINDING_THIS_PIPELINE_PRODUCES = (
    DiscoveryReport,
    Requirements,
    QaPlan,
    ArchitectureReport,
    ImplementationPlan,
)


def test_every_finding_this_pipeline_produces_is_held_to_saying_something() -> None:
    """The coverage claim: an artifact nobody held to anything is an artifact that may be empty."""
    held_to = {a_rule.artifact for a_rule in WHAT_EVERY_FINDING_MUST_HAVE_SAID}

    missing = [
        an_artifact.__name__ for an_artifact in EVERY_FINDING_THIS_PIPELINE_PRODUCES
        if an_artifact not in held_to
    ]

    assert not missing, (
        f"these findings may be returned empty and nothing notices: {missing}. An empty list has "
        "always read as 'found nothing', and for a stage that is the difference between an answer "
        "and a refusal that no reader can tell apart"
    )


def test_every_rule_names_fields_that_exist_on_the_artifact_it_is_about() -> None:
    """A renamed field turns the rule into decoration, silently.

    **Checked against the model's own fields rather than against the class name**, because that
    is the only thing that goes wrong when a field is renamed: nothing raises, and the tier keeps
    reporting that it checked something.
    """
    for a_rule in WHAT_EVERY_FINDING_MUST_HAVE_SAID:
        the_fields_of_the_artifact = set(a_rule.artifact.model_fields)

        named = set(a_rule.at_least_one_of)
        assert named, f"{a_rule.artifact.__name__} is held to nothing"
        assert named <= the_fields_of_the_artifact, (
            f"{a_rule.artifact.__name__} is held to {sorted(named - the_fields_of_the_artifact)}, "
            f"which are not fields of it. It has {sorted(the_fields_of_the_artifact)}, so this "
            "rule is now decoration and the tier keeps saying it checked something"
        )


def test_every_rule_says_why_an_empty_one_would_be_a_fault() -> None:
    """A rule with no reason attached is a rule the next reader will delete.

    **`EmptySecurityReportError` carries its reason in its own message** — that silence in a
    security report reads as safety — and that is the standard. A rule here without a reason would
    be a rule asking to be removed the first time it fires on an artifact that legitimately had
    nothing to say.
    """
    for a_rule in WHAT_EVERY_FINDING_MUST_HAVE_SAID:
        assert a_rule.why_an_empty_one_is_a_fault.strip(), (
            f"{a_rule.artifact.__name__} is held to saying something and nobody wrote down why "
            "an empty one would be a fault"
        )
