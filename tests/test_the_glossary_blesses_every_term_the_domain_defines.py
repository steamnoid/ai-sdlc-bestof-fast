"""The glossary nine modules cite as their authority does not exist, and nothing noticed.

**Nine production modules open with the same sentence.** `DiscoveryReport`, `Requirements`,
`QaPlan`, `ArchitectureReport`, `SecurityReport`, `ImplementationPlan` and their three answer
shapes all say some version of:

    The field names are not chosen here. `docs/domain-glossary.md` fixed the contents of this
    artifact and the agent's name is the contract, so a field that drifts from that table is a
    broken promise rather than a rename.

**There is no `docs/` directory in this repository at all.** So every one of those is a claim
about where a decision was made, pointing at a document that is not here. A reader who trusts it
goes looking for the table, finds nothing, and has learned that this repository's citations are
worth exactly as much as their targets.

**It has already cost something, more than once.** The security analyst cites
`docs/domain-glossary.md` in its own reasoning — it has been handed a repository whose own
docstrings point there — and a citation an agent can follow into nothing is a citation that makes
an agent's answer weaker, not stronger.

**And it is not only the nine citations.** The glossary is what this system's own rules make the
source of truth the code reads from: *"If the concept is not in the glossary, add it before you
use it"*, and *"every type the domain defines must be a term the glossary blesses."* That second
half is the half a test can check, and it had no test — so the rule was a wish, and the wish was
violated by the absence of the file it was about.

**Why this collects the terms by parsing rather than by listing them.** A test holding its own
list of domain terms is a second list to keep in step, and it would pass on the day a new type
was added and the glossary was not. Reading `src/aisdlc/domain/` means the failure is the one
that matters: a term the code defines and the glossary has never heard of.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

THE_REPOSITORY = Path(__file__).resolve().parents[1]
THE_GLOSSARY = THE_REPOSITORY / "docs" / "domain-glossary.md"
WHERE_THE_DOMAIN_IS_WRITTEN = THE_REPOSITORY / "src" / "aisdlc" / "domain"
WHERE_THE_ARTIFACTS_ARE_NAMED = THE_REPOSITORY / "src" / "aisdlc"

# **The name of a constant that names an artifact, read out of the source.**
# `THE_ARTIFACT_DISCOVERY_PRODUCES = "DiscoveryReport"` and six others say, in one place each,
# what a gate rules on. Reading them is how the artifact list is known without a second list.
AN_ARTIFACT_IS_NAMED_BY = re.compile(r'^THE_ARTIFACT[A-Z_]* = "([A-Za-z]+)"', re.MULTILINE)


def _the_terms_the_code_defines() -> dict[str, str]:
    """Every type the domain defines and every artifact a gate rules on, and where each lives.

    **Two collections and no third, because a wider one was tried and measured.** Collecting every
    class in `src/aisdlc/` produced eighty-nine terms — among them
    `AWriteThatChangesNothingError` and `ADeliveredChange` — and a glossary of eighty-nine entries
    is a warehouse inventory rather than a definition of anything. It would also have passed, which
    is the reason not to do it: a rule satisfied by a list nobody would maintain is a rule that
    stops being true quietly.

    **`src/aisdlc/domain/` is the domain by rule** — the directory structure is the domain
    structure — so every class in it is a term, including `StateMachineError`, because an error
    named after the rule it protects is vocabulary and not an implementation detail.

    **And the artifacts, taken from the constants that name them** rather than from the modules
    they live in. `VerificationReport` is a gate's artifact and has no emptiness rule, so a rule
    that found artifacts by looking for one would have left the seventh gate out of the glossary.
    The constants do not have that blind spot: they are where the pipeline says what it produces.
    """
    the_terms: dict[str, str] = {}

    for a_module in sorted(WHERE_THE_DOMAIN_IS_WRITTEN.glob("*.py")):
        for a_class in _the_classes_declared_in(a_module):
            the_terms[a_class] = str(a_module.relative_to(THE_REPOSITORY))

    for a_module in sorted(WHERE_THE_ARTIFACTS_ARE_NAMED.rglob("*.py")):
        its_text = a_module.read_text(encoding="utf-8")
        for an_artifact in AN_ARTIFACT_IS_NAMED_BY.findall(its_text):
            the_terms.setdefault(an_artifact, str(a_module.relative_to(THE_REPOSITORY)))

    return the_terms


def _the_classes_declared_in(a_module: Path) -> list[str]:
    """The names of the classes a module declares at its top level, private ones left out."""
    the_tree = ast.parse(a_module.read_text(encoding="utf-8"))
    return [
        a_node.name
        for a_node in the_tree.body
        if isinstance(a_node, ast.ClassDef) and not a_node.name.startswith("_")
    ]


def _the_terms_the_glossary_blesses() -> set[str]:
    """Every term the glossary names, read as the set of backticked words in it."""
    if not THE_GLOSSARY.exists():
        return set()

    the_text = THE_GLOSSARY.read_text(encoding="utf-8")
    return {
        a_word.strip(".,;:()")
        for a_line in the_text.splitlines()
        for a_word in _the_backticked_words_in(a_line)
    }


def _the_backticked_words_in(a_line: str) -> list[str]:
    """The words between backticks in a line, which is how a glossary names its terms."""
    the_words: list[str] = []
    the_parts = a_line.split("`")
    for a_part in the_parts[1::2]:
        the_words.append(a_part)
    return the_words


def test_the_glossary_the_nine_modules_cite_exists() -> None:
    """Nine modules name a document as the authority for their field names, and it is absent.

    The narrowest possible assertion, and deliberately so: the file exists. Everything else this
    file says about it is about what is in it, and a reader who wants to know whether a document
    is there does not need a rule about its contents to answer it.

    **This is the claim that has bitten real runs.** The security analyst cites
    `docs/domain-glossary.md` while reasoning, because the repository's own docstrings point there
    and an agent reading a repository reads its docstrings.
    """
    assert THE_GLOSSARY.exists(), (
        f"nine modules in src/aisdlc/agents/ open by saying the field names of their artifact "
        f"were fixed by {THE_GLOSSARY.relative_to(THE_REPOSITORY)}, and that file does not exist — "
        f"there is no docs/ directory in this repository. A citation into nothing is worse than no "
        f"citation, because a reader spends the trust"
    )


def test_the_glossary_blesses_every_term_the_domain_defines() -> None:
    """A type the code defines and the glossary has never heard of is a term with no definition.

    **Read out of the code rather than listed here**, so that adding a domain type without adding
    it to the glossary fails this test on the day it is added — which is the whole point of a
    glossary and the reason a test can hold the rule at all.

    **The artifacts are included, not just the types in `domain/`.** Every one of the nine
    citations is about an artifact, so a glossary that blessed `WorkItem` and said nothing about
    `ArchitectureReport` would leave the actual claim unrecorded while looking thorough.
    """
    the_terms = _the_terms_the_code_defines()

    never_blessed = sorted(
        a_term for a_term in the_terms if a_term not in _the_terms_the_glossary_blesses()
    )

    assert not never_blessed, (
        f"the code defines {never_blessed} and docs/domain-glossary.md names none of them. Each is "
        f"defined in {sorted({the_terms[a_term] for a_term in never_blessed})}. A domain term with "
        f"no entry has no definition, so a later reader has to infer it from its use — which is "
        f"the inference this repository's own rules forbid"
    )
