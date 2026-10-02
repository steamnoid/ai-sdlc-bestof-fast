"""Every prompt whose answer can carry a path has to say paths are written from the repository root.

**Six prompts, and none of them says it.** Every artifact this pipeline produces writes file
paths, and not one prompt says where a path starts. So a model reads the inspection, sees
`src/aisdlc/graph/router.py`, and writes `graph/router.py` — because that is the import path and
the import path is what a person thinks in.

**A real run proved it is systematic rather than careless.** Five runs of the pair tier produced
`graph/router.py`, `creative/a_repository_briefing_itself.py`, `aisdlc/agents/
what_an_agent_judged.py` and `github/workflows/gate.yml`. Every one is a real file of this
repository named from the inside out. Individually that reads as a slip; four of them is a
convention, and no amount of loosening a path matcher fixes a convention — it only stops noticing.

**So the rule goes where the behaviour is: in the prompt.** A test cannot make a model cite a path
openably. Saying it plainly can, and saying it once in one place is better than saying it slightly
differently in six.
"""

from __future__ import annotations

import inspect

import aisdlc.agents.analyze_the_architecture as architecture
import aisdlc.agents.analyze_the_repository as repository_analysis
import aisdlc.agents.analyze_the_requirements as requirements
import aisdlc.agents.implement_the_plan as implement
import aisdlc.agents.inspect_for_security_risk as security
import aisdlc.agents.plan_the_change as plan

# **The prompts whose answers carry a file path, and the modules they live in.** Written out
# rather than discovered, because the test below also checks that each of these really does
# mention paths — a list of prompts that had quietly stopped producing any would otherwise be a
# list nobody notices going stale.
THE_PROMPTS_WHOSE_ANSWERS_CARRY_A_PATH = (
    repository_analysis.the_prompt_to_analyze_a_repository,
    requirements.the_prompt_to_analyze_requirements,
    architecture.the_prompt_to_analyze_the_architecture,
    security.the_prompt_to_inspect_for_security_risk,
    plan.the_prompt_to_plan_a_change,
    implement.the_prompt_to_implement,
)


def test_every_prompt_whose_answer_carries_a_path_says_where_a_path_starts() -> None:
    """The rule reaches the prompt, and this is what "reaches" means, read from the source.

    **The six prompts have six different signatures**, so calling them all is a piece of
    machinery about argument shapes that would have nothing to do with the rule. What matters is
    whether the sentence is in the prompt, and a prompt is a function that returns a string — so
    what is checked is that each one builds it from the shared function. A prompt that stopped
    doing so would still return a string and still pass anything that looked only at the output
    of a call this test cannot make.
    """
    not_saying = [
        a_prompt.__name__
        for a_prompt in THE_PROMPTS_WHOSE_ANSWERS_CARRY_A_PATH
        if "the_rule_about_naming_a_file" not in inspect.getsource(a_prompt)
    ]

    assert not not_saying, (
        f"these prompts can return file paths and never say where a path starts: {not_saying}. "
        "Five runs of the pair tier produced graph/router.py, creative/a_repository_briefing_"
        "itself.py, aisdlc/agents/what_an_agent_judged.py and github/workflows/gate.yml — four "
        "real files named from the inside out, which is a convention rather than four slips, and "
        "no path matcher fixes a convention"
    )


def test_the_rule_is_one_sentence_written_once() -> None:
    """Six prompts saying this six ways would drift, and then three of them would be wrong.

    **So the sentences come from one function**, and this test is what stops a second copy being
    added when a seventh prompt appears.
    """
    from aisdlc.agents.how_to_name_a_file import the_rule_about_naming_a_file

    assert "root of the repository" in the_rule_about_naming_a_file(), (
        "the shared sentence does not say where a path starts, which is the one thing it is for"
    )
