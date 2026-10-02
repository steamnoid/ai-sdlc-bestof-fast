# ai-sdlc-bestof-fast

An AI-native software lifecycle with a board. A repository goes in, a sentence says what should
change, and a pull request comes out with every decision in the trail.

```text
  a repository and a sentence
              │
              ▼
   discovery ─▶ requirements ─▶ scenarios ─▶ architecture ─▶ security
       │            │              │             │             │
     a gate        a gate         a gate        a gate        a gate
       │            │              │             │             │
       ▼            ▼              ▼             ▼             ▼
      plan ─▶ implementation ─▶ verification ─▶ pull request ─▶ DONE
       │              │              │
     a gate        a gate         a gate
       │              │              │
       └──────── a refusal or a red suite goes to the repair supervisor ─┘
```

Eight gates, and a person is asked at every one. A refusal ends the run where it was refused,
with the reason on the card. **After the eighth gate the run reads the checks on the commit GitHub
says the pull request points at, merges that exact commit, and only then marks itself delivered** —
so `DONE` means merged rather than offered.

---

[![gate](https://github.com/steamnoid/ai-sdlc-bestof-fast/actions/workflows/gate.yml/badge.svg)](https://github.com/steamnoid/ai-sdlc-bestof-fast/actions/workflows/gate.yml)

## Run it

```bash
uv sync --all-groups
uv run aisdlc serve            # the board, on http://127.0.0.1:842
```

Open the address, type a repository and a sentence, press **start a run**. A card appears
immediately — before the clone, before the first model call — and then moves on its own until it
reaches a gate and waits for you. Click the card to read what the run found and to answer.

A run in a terminal instead, with the gates in your own shell:

```bash
uv run aisdlc run paligakrzychu/wellbeing-tracker-public "add a /health endpoint"
```

### Configuration

A run needs a model, and the deployment says which:

```bash
LLM_PROVIDER=openai_compatible
LLM_ENDPOINT=https://...
LLM_MODEL=...
LLM_THREAD_ID=aisdlc            # the gateway routes by session and refuses without it
OPENAI_API_KEY=...               # the name LangChain's clients read, so this one reads it too
```

| setting | what it does |
|---|---|
| `AISDLC_PROJECTS_DIR` | where every run's directory goes, and where the register file sits. Defaults to `./aisdlc-projects` |
| `AISDLC_APPROVAL_POLICY` | a bare name. The policy that answers the gates instead of a person, recorded as `autopilot:<name>` and never as a person |
| `AISDLC_FORK_OWNER` | whose copy a run pushes to. Delivery needs it; a run that only reasons does not |
| `AISDLC_CORRECTION_BUDGET` | how many times a run may ask a model for an answer it already had |
| `AISDLC_REPEAT_BUDGET` | how many times the supervisor may put an agent back on a ticket |
| `AISDLC_WHAT_A_RUN_IS_DOING` | `1` sends every tool call and every token to the terminal |

`GITHUB_TOKEN` is needed for delivery and not for reasoning. Every one of these is **refused
rather than defaulted** when it holds something this system cannot read — a setting nobody
noticed and an answer nobody asked for are the same failure wearing different names.

---

## The test

```bash
uv run pytest -q     # 227 passed, 3 skipped, 8 deselected, ~12s, no network, no model, no credential, no container
