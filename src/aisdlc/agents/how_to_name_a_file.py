"""How to name a file, said once, because six prompts need saying it.

**Every artifact this pipeline produces writes file paths, and until now no prompt said where a
path starts.** So a model reads an inspection showing `src/aisdlc/graph/router.py` and writes
`graph/router.py` — because that is the import path, and the import path is what a person thinks
in when they are talking about a module.

**This is a convention rather than a slip, and five runs of the pair tier are what says so.**
Those runs produced `graph/router.py`, `creative/a_repository_briefing_itself.py`,
`aisdlc/agents/what_an_agent_judged.py` and `github/workflows/gate.yml`. Every one is a real file
of this repository, named from the inside out. Loosening a path matcher would have stopped the
tier noticing, which is the opposite of fixing it.

**So the sentence lives here and the prompts build it from here.** Six prompts each carrying their
own wording would drift, and then two of the six would be the ones that are wrong.
"""


def the_rule_about_naming_a_file() -> str:
    """The one paragraph every prompt whose answer carries a path puts into itself.

    **A path is written from the root of the repository, and it includes every directory on the
    way.** Not the module's import name and not its name inside the package: `src/aisdlc/graph/
    router.py`, because that is the path a person types to open it, and a path a reader cannot
    open is not a citation however well the file exists.

    **Copy a path out of the inspection rather than writing it out again.** That is the other half
    of it, and it is the half that actually works, because the inspection is the one place in this
    system where a path is guaranteed to be exactly right — it was produced by walking the clone.
    """
    return (
        "\nWrite every file path from the root of the repository, with every directory on the\n"
        "way, and copy it out of the inspection above rather than writing it out again. A path\n"
        "like graph/router.py is the module's import name rather than a path a reader can open;\n"
        "what a reader opens is src/aisdlc/graph/router.py. Do not shorten a path to its last\n"
        "few directories, and do not invent a file the inspection does not show you.\n"
    )
