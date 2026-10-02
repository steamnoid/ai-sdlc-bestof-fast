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
uv run pytest -q     # 147 passed, 3 skipped, ~8s, no network, no model, no credential, no container

# The three skips are the real tier, and each one prints what it is missing: one needs a real
# model, two need a real GITHUB_TOKEN and a repository to file against. They are collected by the
# default run and skipped rather than deselected, because a skip that says why is a claim and a
# deselection is silent — see `test_every_marker_this_repository_declares_is_carried_by_a_test.py`.
# To watch the model judge:
set -a && . ./.env && set +a && uv run pytest -q -s \
  tests/test_a_real_model_judging_a_real_refusal.py

# A live-model run through the board is driven through the same board by starting the server with
# a `.env` in place — there is no separate tier to select.
```

One file, and it is the whole product: a person posts a repository and a sentence over real
HTTP, answers eight gates one at a time, and gets a pull request — with a **real `git clone`** of
a repository made locally on the spot, the real state machine, the real gate, the real register
and a real board. Three things are replaced and each is named where it is replaced: the seven
agents do not call a model, the five delivery collaborators do not call GitHub, and the clone is
fetched from a path rather than a host. Everything else is production code on its real path.

It asserts the things that would be a lie otherwise: that a card exists before the run has done
anything, that the work item really is at `DONE` when the board says delivered, that the run read
the checks and merged that commit before it said it was delivered, that a refusal leaves one
decision and no approval, and that an `aisdlc-` identifier posted as a decider is refused with the
gate's own sentence.

---

## After the eighth gate: the suite, and the merge

**The eighth gate approves a delivery. It never merged anything.** Until now the pipeline ended at
a pull request and marked the work item `DONE`, which is a word that means *merged* to anybody
reading a board and did not mean it here: the branch was pushed, the pull request was open, and a
maintainer had it in their review list. **Two nodes now sit between the delivery and `DONE`** —
read the checks, then merge that commit — and there is no ninth gate, because a merge is the
consequence of a gate somebody already answered rather than a question somebody has not.

**"Green" is about the commit being merged, and the pull request is asked which commit that is.**
The tool reads the pull request first and takes `head.sha` from GitHub's own answer, then reads
that commit's check runs. Asked about a *branch* instead, GitHub answers with the latest run on
that branch — which after a rebase, an "update branch" or a second run pushing the same branch is
a green run describing a commit nobody is merging. **The test reads the request back out of the
transport**, because the failure this guards is a tool working perfectly on the wrong commit.

| what GitHub says | what this system does |
|---|---|
| no check runs at all | refused — nothing was proved, and a repository with no checks is not a green repository |
| any check `failure`, `timed_out`, `cancelled`, `action_required`, `stale`, `startup_failure` | refused, naming the check and its conclusion — red does not become green by waiting |
| any check still running, or a conclusion that is not `success` | refused — **an absent verdict is never green**, and `skipped` and `neutral` are absences |
| a `404` about the pull request | refused as its own fact, because "GitHub did not tell us" and "the suite is still running" send a reader to two different places |

**A merge is asked about before it is attempted, and the word "not mergeable" is never read.**
GitHub answers *"Pull Request is not mergeable"* for a pull request that conflicts with its base —
which can be rebased and tried again — **and** for a base branch that is protected, which cannot
be merged into at all. Classifying the refusal by that phrase calls the second one a conflict and
sends a person after a merge conflict on a branch that is protected on purpose. So `mergeable` is
read first: `false` is the only thing that makes this a conflict, `null` (GitHub computes
conflicts in the background) is a third refusal that waits for nothing, and a refusal by the merge
itself is quoted rather than re-interpreted.

**The merge is given the commit, and GitHub is the one who refuses a head that moved.** The sha
is in the request body, which is `gh pr merge --match-head-commit` in a different tool: the checks
were read about one commit, and a head that moved between the two is a commit nothing was proved
about. GitHub answers 409 and this system quotes it, rather than noticing afterwards. **No merge
method is chosen** — merge, squash or rebase is that repository's setting, and a system that picked
one would silently change how every repository it delivers to records history.

**A collision has a name, two named repairs, and nothing else.**
`WhatToDoAroundAConflict` is a closed set a model chooses from: three conflicts — a pull request
that will not merge, an opportunity somebody already filed, two runs that changed one file — each
with its own two repairs, and an answer outside the set, or a repair belonging to a different
conflict, or a repair with no reason behind it, is `AConflictNobodyCouldRuleOnError`.

**One of the three is asked by a node now, and it is the one a delivery reaches.**
`settle_the_conflict_in_this_run` is what the merge node hands a `mergeable: false` to, **in
GitHub's own sentence** — the same `what_stopped_this_run` channel a refusal travels to the repair
supervisor in, because a decision made on a summary of a conflict is a decision about the summary.
The decision is announced on the card before it is acted on, and the reason in it is the model's:
this system writes no reason of its own next to a decision about somebody else's repository.

| the repair | what happens |
|---|---|
| `rebase it and try again` | the commit is put on the branch it joins and the run goes back to the node that reads the checks — **not** to the merge |
| `leave it open and say why` | the run ends at `write_how_this_run_ended`, its work item still at the gate it was refused after |

**A rebase goes back to the suite and not to the merge, and that is the whole argument.** The merge
is handed the commit the checks were read about, and a rebase produces a *different* commit — so a
repair that went straight back to the merge would be asking GitHub to land a sha no check ever ran
on, with GitHub's own 409 as the only thing standing between the run and an unproved merge. The
suite node reads the checks **on the commit the pull request now points at**, which is the only
commit a merge can be justified by; if nothing has run there yet, the run stops with the suite's own
refusal. **`leave it open` is not `DONE`** — `DONE` means merged, and the repair chosen there is
precisely a decision not to put the change in somebody's base branch.

**What ends the run is bounded, and the bound belongs to the tool.** A merge refused as a conflict
sends the run to the repair; a rebase that would change nothing leaves the pull request in front of
the same `mergeable: false`; a run with no bound asks a model the same question about the same facts
until the runtime's recursion limit stops it. The tool refuses that rebase by name, so the second
visit stops.

## The rebase under that repair, and the one rule it has to keep

`git.rebase_the_branch_a_run_pushed` is three `git` calls and a decision between them: fetch the
branch the pull request would join **from `upstream`**, replay this run's commit on it, and put the
result on the branch this run delivered **on `origin`**. Every address is a remote's *name*. The
obvious way to fetch is to compose a URL, and a URL that needs a credential is a URL git prints
back inside its own error message — which is where this repository's error messages come from, and
which is why `the_clone_url_of` refuses to read the environment at all.

**The branch may be moved only where this run left it, and git is what checks that.**
`create_a_branch_on_a_remote` refuses to push a branch that is already on the remote, because a run
must never move a branch somebody else is using — and a rebase has to do precisely that, so the
refusal could not be relaxed. It is stated instead: the commit the branch is expected to be at goes
into the push as a **lease** (`--force-with-lease=refs/heads/<branch>:<sha>`), which git compares
against the branch *inside the push that would move it*. A read of the branch beforehand would leave
a window between the read and the push, and what that window admits is somebody else's commit,
destroyed. A lease git refuses is not read as "somebody else pushed": this system will not announce
a cause a remote has not stated, so the refusal says which condition it gave git and quotes git.

**A rebase that would change nothing is refused by name, and that is what stops a run going round.**
A merge refused as a conflict sends the run to the repair; a rebase that changes nothing leaves the
pull request in front of the same `mergeable: false`; the run reaches the repair again with the same
facts and walks until the runtime's recursion limit. `git merge-base --is-ancestor FETCH_HEAD HEAD`
answers the question, so the tool refuses rather than reporting a repair that moved nothing — **a
decision taken once about a fact that has not changed is not a decision**, and this is said where
the fact lives rather than left for a node to notice on a second visit.

**A rebase git cannot finish leaves the checkout as it found it**, because a clone stopped mid-rebase
refuses the next `git` command the run makes and the clone is the whole of a run's state. The
refusal names the files through `git diff --name-only --diff-filter=U` rather than out of git's
prose: a conflicting rebase says `could not apply` and prints `git add/rm <conflicted_files>`
without naming one, so which path appears at all depends on the backend git picked.

---

## It has run for real, twice, and both runs found something

Every proof above uses a faked model, which makes it a proof about the wiring and not about the
product. So the pipeline was pointed at `paligakrzychu/wellbeing-tracker-public` with the
deployment's real model, a real container and a real fork, and `AISDLC_APPROVAL_POLICY` answering
the gates unattended.

**Run 1: five gates approved, the sixth refused.** The security analyst was refused for a reason
no test would ever have produced:

> The report never read the item it was commissioned to review: it states the entire inspection
> was a top-level listing plus the contents of `package.json` … Six of the seven entries are then
> speculation from filenames and dependency declarations alone

It was right. The run stopped where it was refused, with the reason on the card.

**Two real defects, both found only by running it.**

**A security analyst shown no source code.** `an_inspection_of` was built for *discovery*, whose
job is a repository's shape — its own docstring says "Source files are not in it, because a
discovery report is a summary of a repository's shape and not a copy of its contents" — and the
security analyst was later wired to the same one. It was therefore asked to find authentication
and authorization problems while being handed a directory listing and a `package.json`. Now
`an_inspection_of_the_code` shows the code, chosen by the names security problems live in, and
**ends by naming what it did not show**. The same model on the same repository then produced:

| before | after |
|---|---|
| 7 findings, six reasoning from `Dockerfile`, `.dockerignore` and `bcryptjs` | 7 findings, every one quoting code |
| 1,434 characters of evidence | 10,835 |
| coverage gap filed as `informational` | *"I could not verify dependency resolution"* — the model naming the limit of its own evidence |

The first finding after the fix, quoted from the model, at severity **high**:

> `function secret() { return new TextEncoder().encode(process.env.JWT_SECRET ||
> "dev-secret-change-me"); }` in `web-app/src/lib/auth.js` and the identical helper in
> `web-app/src/middleware.ts`

A hardcoded JWT secret fallback, in a real public repository, found by this system and delivered
as a report with every quotation checked back to a file it read.

**A symlinked projects root broke the planner.** `plan_the_change` asked the confinement check
where a test's directory was, got back a path that had been **resolved**, and compared it against
a root that had **not**. On any machine where the two spellings differ the comparison raised
Python's own `ValueError` about a subpath, out of a stage, twenty minutes into a run:

> `'/private/tmp/…/repository/tests' is not in the subpath of '/tmp/…/repository'`

macOS makes `/tmp` a link to `/private/tmp`. **No unit test could have found it**: pytest hands
out an already-resolved `tmp_path` and every test in the suite ran from one. `filesystem_read`
already resolved both sides for exactly this reason and says so in its own docstring — the same
bug, one module over, never fixed there.

**Run 2, with both fixed: the same five gates, and the security gate approved on the evidence.**

> Every finding is anchored to quoted code in a named file (the duplicated
> `process.env.JWT_SECRET || "dev-secret-change-me"` in `web-app/src/lib/auth.js` and
> `web-app/src/middleware.ts`, the `||`-short-circuited bcrypt compare …), severities are
> calibrated

and the planner produced a plan, which gate 6 refused for its own independent reason — that the
plan named `vitest.config.ts` without saying what change it needed. The run stopped cleanly,
`how_it_ended: None`, because a refusal is a decision and not a fault.

**And then four more, from one run each — and a pattern.**

Every one of these is the same shape: **the gate was right and something underneath it was
wrong.** That is what a real run is for. Four runs, four refusals, and in three of them the
refusal named the defect precisely enough to fix it.

| what the gate said | what was actually wrong |
|---|---|
| *"The report never opens the Dockerfile — the only file this work item actually changes."* | `Dockerfile` carries **no extension**, and the source-suffix filter excluded exactly the files that carry none. A `Dockerfile` and a `Makefile` were invisible to every agent in the system |
| *"Its one nod to the healthcheck is an inference from the repository's branch name."* | the file selection was named after the **security** question — which fixed the security analyst and was then applied to every agent. A selection framed around one consumer is the wrong selection for the others, and it is now what a *change* tends to touch |
| *"the suite passed identically with the file present and deleted"* | the implementer wrote the file back byte-for-byte, and that refusal **killed the run** instead of reaching the supervisor — the one refusal where the answer is least in doubt, because the plan named the file and said what to change in it |
| *"while `Dockerfile` nonetheless appears in `evidence_files` with blob links as though they had been read"* | discovery cites were proved to be **files of the clone** and never checked against **what the model was shown**. A report could say a file's contents were not shown and cite it anyway, and the check that existed could not see it |

The fourth one has a test that bites: a file that genuinely exists in the clone — `.gitignore` —
is refused because the inspection did not contain it. Before, the existence check passed it.

**A fifth, and it is the one worth having.** Six gates, five approvals, and a refusal at the plan
that reads like a person who has read the repository:

> The plan names `Dockerfile` as the only file to change and explicitly declares
> `tests_to_add` as empty, so nothing in this run will ever exercise the healthcheck it is
> adding. **A `HEALTHCHECK` whose path, port, or interval is wrong does not fail loudly — the
> container simply reports unhealthy forever** — and this plan contains no build-and-run step
> confirming the endpoint exists and that the container reaches "healthy".

And it was right: `tests/unit/wellbeingt-17-docker-static.test.ts` asserts `--interval=30s`, so
the change this run was asked for makes that suite red, and the plan said nothing about it.

**And the repair supervisor ran, for the first time, against a real card.** Three stages hand a
refusal to it — a plan whose test is in a directory the suite does not collect, a test that
passed without the change, a suite that went red — and it reads the card, asks a model, and names
one of two stages to start again at. Both real runs above were answered by a policy that never
refused, so none of the three fired; the mechanism was carried across unexercised, and a
mechanism nobody has watched is a claim.

**It has now fired, and it fired twice on one run, and each time it was right.** A run asked to
remove a hardcoded session-secret fallback. The implementer wrote
`tests/unit/session-secret.test.js`; `vitest.config.ts` collects `*.{test,spec}.ts`, so the file
was never opened by the runner. The supervisor read the card, named it, and sent the run back to
the planner — *"The repository's test runner still does not collect
tests/unit/session-secret.test.js, so the one test the approved plan added remains a file"*. The
planner planned the same `.js` file again, and the supervisor caught it again and said so again.
**This is the mechanism working**: the one file the plan named was a file nobody ran, the run said
so in its own words, and nobody had to notice.

**And it died there, on a step the mechanism had never needed before.** The run stopped with

```text
StateMachineError: aisdlc-dev-impl holds this work item and cannot hand it to
```

The refusal was routed correctly and **the work item was never let go of**. A work item in
`IN_PROGRESS_BY_AGENT` holds exactly one agent, and `_takes_the_work_item_from_the_holding_agent`
exists so an agent cannot hand work straight to a peer — which is right, and which made the
supervisor's verdict unrepresentable: the supervisor named the planner, and the work item was
still the implementer's. Every routing test passed, because each one calls a node and reads the
`Command` it returns; the graph had never been walked with a work item in a hand.

**The release is the step that was missing, and it is a node rather than a key.** The three nodes
that hand a refusal on now hand it to `let_go_of_the_work_item`, which asks for
`AWAITING_AGENT_PICKUP` held by nobody; `transition_the_work_item` makes the move, and only it
may. Two things about that were wrong first and are the argument for the shape:

- **A request in the state is not a move.** The first version put `requested_stage` into the
  refusing node's own `update`, and the request sat there until the next pickup node overwrote it
  with its own. The run died at the same `StateMachineError`, one node later, and the fix had
  changed nothing observable.
- **A `Command` names its own destination**, so the release cannot return one. Asking the graph to
  make a move means letting the graph walk it.

**And the biconditional had to learn a stage it did not have.** `AWAITING_AGENT_PICKUP` required
an agent, because every move into it named one. A release names nobody, so the run then died of
`AWAITING_AGENT_PICKUP requires no agent, but aisdlc-dev-impl holds the work item` — the mirror
image of the first failure, one fix later. **The stage is now in a third list,
`STAGES_WHERE_EITHER_IS_ALLOWED`, and it is the only one there.** Nine pickup nodes reach it with
an agent named and one release reaches it without; both are the queue. Forcing it onto either side
of the biconditional makes one of the two moves illegal, which is what happened twice.
`IN_PROGRESS_BY_AGENT` deliberately stays where it was — a work item in progress with nobody on it
is a run that believes it is working, which is the failure the single-holder rule exists to make
visible.

**One row was added to the table, and it says exactly one thing.**
`AWAITING_AGENT_PICKUP -> AWAITING_AGENT_PICKUP` exists so a queued work item can be **claimed**,
which changes the holder and not the stage. Without it the run died again at
`AWAITING_AGENT_PICKUP cannot move to AWAITING_AGENT_PICKUP` when the supervisor's chosen agent
arrived to pick up work that was already in the queue. `_takes_the_work_item_from_the_holding_
agent` allows it as written — it refuses a move from one agent into *another agent's* hands, and
work nobody holds is held by nobody. **No other stage can move to itself**, and a test says so: a
table where stages generally could would make a rewiring error invisible rather than loud.

Asked with the **real card from run 2** — five notes real agents left about a real repository —
and a real refusal, a real model decided in 6 seconds:

> **the run starts again at: the planner**
>
> what has not changed: *No observation has contradicted the requirement that the root
> `package.json` be asserted, and `vitest.config.ts` still has no include that collects anything
> under `tests/e2e/WELLBEINGT-201`, so the repository's test runner reads exactly as much of the
> change as it did on the first attempt.*
>
> **`aisdlc-dev-plan`: repeat** — *This is the vacuous-test failure and the plan owns it. The plan
> named `tests/e2e/WELLBEINGT-201/package-json-typecheck.test.ts` while no include in
> `vitest.config.ts` reaches it, so the suite passed identically with the file present and
> deleted.*

It named the planner and only the planner, and its reason is the one the engine's own log records
from a run two years of work ago: *a plan that lands a test the runner never collects is a plan
that misunderstood the repository.*

**A refusal is a refusal, and stopping is a refusal too — two different ones.** Every agent told
to stand down **raises**, because a run that returned quietly reads as a run that finished. An
agent out of turns raises a *different* error naming `AISDLC_REPEAT_BUDGET`, because a clean stop
and a judgement the deployment overruled must not look alike in a record. And `0` lifts the
ceiling rather than forbidding every repeat — which is the opposite of a count, and reading it as
"no repeats" would make the setting mean two things depending on which agent it was read for.

**A note is written before the supervisor acts, not after.** Every verdict goes on the card,
including the ones that stand an agent down: a record saying only who repeats cannot be argued
with afterwards by a reader who disagrees with the planner being sent back.

**One thing a real run showed about the board.** A run spent twenty minutes inside the
planner and the board said "working" for all of it. The run's own record carries a timestamp on
every line, so a card now says `on begin_planning_the_change · 20 minutes`. The first version of
that card read `on __interrupt__`, because when a run parks, the node that last "ran" is
LangGraph's own.

---

## The other half: a repository briefs itself

**A run answers a sentence somebody typed. A briefing answers "what should this repository be
given",** which is a different kind of question — nothing in it came from the deployment, and a
model that is not shown the repository's own files will invent the work.

```bash
AISDLC_CREATIVE_MODE=on uv run aisdlc serve
```

Then press **what should this repository be given?**. It clones read-only, forks nothing, needs no
credential, and takes two to three minutes — which the button says, because a button that appears
to have done nothing is worse than one that says it is waiting.

A real briefing of `paligakrzychu/wellbeing-tracker-public`, 2m42s, five opportunities, every
citation proved against the clone:

> **[1] Replace the ticket-named end-to-end specs with tests named for the behaviour they assert**
> — QA — *"A check enumerates tests/e2e and fails on any spec whose file name does not match"*
>
> **[3] Assert the authentication contract in `tests/unit` rather than only through the browser**
> — SEC — *"a test calls the login route handler and asserts the `Set-Cookie` header carries
> `HttpOnly`…"*
>
> **[4] Check that `web-app/schema.sql` and the queries the application actually issues agree**
> — DEV — *"the integration test applies `schema.sql` to an empty database, inserts a row…"*

and what it could not settle, which is the half that matters:

> Whether the hex-named spec files in `tests/e2e` carry their ticket meaning in the spec bodies or
> in `tests/e2e/mapping.ts`

**A person then picks, and the picks become work.** Filing is a `POST` to GitHub and there is no
undo, so it is a second call carrying indices rather than a briefing that files itself: a briefing
which became tickets without anybody choosing would be a backlog this system invented. Filing is
idempotent against the opportunity's own words, because a briefing retried because its answer was
slow is a briefing retried for a reason that happens.

**And what a real briefing found, twice, about the same model on the same repository:**

| | first briefing | after the paths were listed |
|---|---|---|
| the repository it described | *"a small web application… `src/App.jsx`"* — a React app the repository is not | *"a Next.js web application… cookie-session auth"*, which is what it is |
| citations | `src/App.jsx` × 4 — **a path the repository does not have** | 31 real files, every one proved |
| opportunities | 0, after the refusal corrected it | 5, specific enough to file |

The first briefing invented `src/App.jsx` in all four opportunities. **Nothing caught it, because
the check read `evidence_files` — a field the model cannot write — and an empty list proves
nothing.** The check now reads what the model wrote, and the prompt lists the sixty paths a
citation may name, which turns citing from a recall into a lookup.

---

## Where this came from

This is an assembly of two half-products that are each other's missing half, and being explicit
about that is more useful than pretending it was written from nothing.

| | |
|---|---|
| **`ai-sdlc-os`** | the engine, unchanged and unrewritten. Eight agents with real prompts, the GitHub tools, the containerised test runner, the delivery, the repair supervisor, LangGraph. It has opened three real pull requests on a public repository. What it had not: any way to see or start a run — its own `AGENTS.md` says "What is genuinely not built is the API and the CLI" |
| **`ai-sdlc-bestof`** | the interface, unchanged and unrewritten. The SQLite store, the five-column board, the FastAPI over it, the browser UI, the event stream, the derived column rule. What it had not: a way to start a run, any GitHub tool, and six of its eight stages had no agent at all — it was a board over a store nothing wrote |

So the engine got the board and the board got an engine. The parts written here are the ones
neither had:

- `application/a_run_being_assembled.py` — the composition root. Before this, the only code that
  ever assembled a run was a test in a real-dependency tier, which is a test suite doing a
  product's job.
- `application/the_runs_this_process_is_holding.py` — the bridge. A run is a compiled graph with
  a checkpoint in memory; this holds it between the moment it parks at a gate and the moment
  somebody answers, and it is where a decision enters.
- `store/what_a_run_records.py` — five write-through recorders, hung on the five places the
  engine already had a function that made something a fact. **No new nodes and no rewiring.**
- `web/the_api.py` — `POST /api/runs`, the endpoint neither project had.
- `cli.py` — the two commands.
- the form on the board, and the run-status line that joins what is on disk to what is in memory.

### Two more bugs, found by running rather than reading

**`the_lifecycle` took a `plan_the_clone` parameter and one of its own wiring functions ignored
it**, reading the module constant instead. The parameter was a claim about the function that was
false, and nothing could have found it but a test that passed a clone planner and watched the
real one run instead.

**Two locks on one SQLite connection.** The board and the run each had their own, which is the
same as no lock at all: `InterfaceError: bad parameter or other API misuse` from a query that
worked a moment earlier. There is now one lock, taken by both, in one module.

---

## Every issue and pull request carries the project's full name

**An issue lands in a queue among hundreds and a pull request in a review list among dozens**, and
with nothing on them saying which project asked, the only way to tell a briefing's issue from a
person's is to read every body and recognise the formatting — which stops working silently the
moment the formatting changes.

**The tag is *this system's* project — not the repository it files into.** This is the whole rule
and it took six attempts to get right, so it is written plainly. **A tag answers *who produced
this*, and that is a fact about the codebase, not about where the work landed.** The first version
derived it from the repository being filed into, so a briefing on somebody's project opened issues
there tagged with *that project's* name — which looks like a tag about their work, answers nothing
about which tool wrote the issue, and would make two automations filing into one repository
indistinguishable to a person reading the queue.

**So the function takes no repository at all.** Taking one is what invited the mistake: the
argument was there, it was the only name in scope, and it was the wrong name. An argument nobody
needs is an argument that will be used wrongly. The name is a constant, and `AISDLC_PROJECT_NAME`
overrides it for a deployment that forks this.

**It is the full name, `owner/name`, not the bare name** — a repository name is only unique within
an owner, and two forks of one project share a name.

**One rule, one module, read by both writes.** `github.open_an_issue` and
`github.create_pull_request` are the only two things here that write to a repository somebody else
owns. A rule stated in each is two rules that drift — somebody tags issues and forgets pull requests,
and every filing after that is half-tagged, with neither tool individually wrong. A test reads both
against the same rule.

**And the label is created first, because GitHub refuses an issue carrying a label it has never
heard of.** A 422 there reads as "the delivery failed" and costs somebody twenty minutes of
reasoning to diagnose. A 422 to the *creation* is success, because a label that already exists is
exactly what GitHub says when it refuses to create one — which is what makes filing several issues
against one repository work at all.

**A pull request is labelled *after* it is opened, and that is not a style choice.** GitHub's
create-pull-request endpoint does not take `labels`. It does not reject the field and it does not
warn: it answers **201**, opens the pull request, and discards the labels. A pull request *is* an
issue in GitHub's data model, which is exactly why labels work on one and silently do nothing on
the other. **Every pull request this system opened for a week arrived untagged while all eleven
assertions about it passed**, because every one of them was about the request rather than about the
pull request. The label now goes on through `POST /repos/{owner}/{name}/issues/{number}/labels`,
which is where GitHub keeps a pull request's labels at all — and this is written down beside the
code that was wrong, because the test that found it is the whole argument for testing a thing
against the thing it talks to.

**It costs one write per delivery, and after the first that write is refused.** A deployment running
ten deliveries against one repository makes ten label requests and GitHub answers nine with 422.
Caching it would avoid those, and would also mean a label deleted halfway through a run's life is
silently absent from every filing after it — found out by a person filtering by project and seeing
nothing. A wasted write is visible in a rate limit; a stale cache is visible in a wrong answer.

**And a deployment that cannot create labels still delivers.** Labels live on GitHub's *issues*
API: opening a pull request needs `pull_requests: write`, creating a label needs `issues: write`,
and a deployment provisioned for delivering has no reason to hold the second. **The first version
of this rule refused every delivery on such a deployment, with an error about a label, twenty
minutes after a run had pushed a branch** — a worse outcome than an untagged pull request by a
distance nobody would defend. So a tag that cannot be created is not used and the pull request still
goes out, untagged. The tag is how a person finds the work; the pull request is the work.

**And it is proven against real GitHub, not only against a stand-in.**
`tests/test_the_tag_reaching_real_github.py` files one real issue, reads it back through GitHub's
own record of it, asserts the label is on the thing rather than in the request, and closes it
again. It skips loudly unless a deployment states both `GITHUB_TOKEN` and
`AISDLC_THE_REPOSITORY_TO_FILE_AGAINST`, because a test that files into a repository nobody named
writes to a stranger's board. **It is what found the pull-request bug above**, by opening a real
pull request and reading GitHub's record of it rather than its answer. **It also opens, labels, reads back, closes and deletes a real pull request**, and that is the
half which was broken: `labels` in the create-pull-request payload is accepted and discarded, so
eleven request-level assertions passed while every pull request arrived untagged. **The branch is
genuinely deleted; the pull request is only closed**, because GitHub has no endpoint for deleting
one — which is the same kind of claim as the field it does ignore, and this file held one too.

**Each run leaves one closed issue and one closed pull request behind.** Both are opt-in, and both
are the visible record that the tag arrived; a deployment running these on every push accumulates
them, which is a cost to know about rather than a reason not to file.

Set `AISDLC_PROJECT_NAME` when a project spans repositories or a monorepo's repository name is the
container rather than the thing being worked on.

## main is protected, and it was not for the first hour

**`main` accepted a direct push for the first hour of this repository existing**, and I proved it
by pushing a stray line straight to it while testing something else. The line is gone. What
matters is the three things that took to fix, and each was found by testing the rule rather than by
trusting the response:

| what was wrong | how it showed up |
|---|---|
| `enforce_admins: false` | the protection was on and the push went through anyway — **the owner is the one person it does not stop** |
| `required_approving_review_count` defaulted to 1 | every pull request sat `BLOCKED` forever, because nobody can approve their own |
| the required context was `gate` | the workflow's name, while GitHub's status context is the **job's** name, `the_gate` — so the requirement could never be met and every merge was blocked |

**What is required now:** a pull request, the `the_gate` check green, up to date with `main`, stale
approvals dismissed, no force pushes, no deletions, **and it applies to administrators** — verified
by pushing again and reading `GH006: Protected branch update failed`.

Not required: a second human. One approval was the default and it makes a one-person repository
unmergeable, which is not a safety property.

## A briefing reads the issues, and filing refuses a duplicate anyway

**Two changes, because one of them is not enough.**

**The briefing is shown what is already tracked.** A model told to "propose work" proposes work it
knows about — it is a retrieval task and it recalls a different project. `github.list_open_issues`
reads the open issues of whatever repository is being briefed, and the prompt lists them and says
not to propose them again. **No credential**, because issue listing is public where filing is not:
a briefing is a reading operation all the way through, and making it need a token would put the
harmless half of creative mode behind the same door as the half that touches a stranger's board.

**And filing refuses a duplicate anyway.** A prompt is not a check — this repository has a standing
rule about that, learned from a model citing a file that did not exist while being told to cite
real ones. The model may ignore the list, misread it, or re-word the work it names, and **an issue
that is opened and then found to be a duplicate has already landed in somebody's queue** and can
only be removed by a person closing it. So the refusal is in `filing_what_the_briefing_found`,
ahead of `open_the_issue`.

**The comparison is about the work, not the string.** Two titles for the same work rarely match as
text, so this compares the words they share — after dropping the words that appear in nearly every
title, because "Add a test" and "Add a health endpoint" share `Add` and nothing else, and refusing
the second because of the first would make creative mode useless on any repository with a backlog.
Two meaningful words in common is the threshold. **That is a judgement, and the cost of being wrong
is asymmetric**: a duplicate is noise in a queue, a dropped opportunity is work nobody hears about.

**A repository with no issues says so in one line** rather than saying nothing, because "nobody has
filed anything" and "you were not shown anything" read identically to a model and only one is true.

**And GitHub refusing to answer refuses the briefing**, rather than returning an empty list. An
empty list reads as "nothing is tracked", which is a fact — and a false one would mean proposing
work a team has already agreed to do, which is the exact failure this is for.

**The limit, named.** The list is read once, at briefing time. An issue filed between the briefing
and a person's pick is not in it.

## What is not built

Stated rather than left to be discovered.

- ~~**Every repair in this system crashed the run.**~~ **Fixed, and it is the most important
  finding in this repository's history, because it made the whole supervisor unreachable.** The
  node that makes the change returned a plain state update on success and a `Command(goto=...)` on
  a repairable refusal — *and* the graph also carried a static edge out of that node. A
  `Command`'s `goto` and a static edge from the same node **both fire**. So a refusal did not
  divert the run: the run went to the supervisor *and* carried on down the ordinary path, the two
  arrived at the same node in the same step, both wrote `requested_stage`, and LangGraph refused
  it:

      At key 'requested_stage': Can receive only one value per step.

  The refusal was correct, the routing was correct, the supervisor ran, and the run still died —
  **at the moment the repair was being performed, with a message about concurrent writes rather
  than about the repair.** Every refusal-routing test here passed, because they call the function
  and read the `Command` it returns; the defect was entirely in the wiring, and no unit test
  builds the graph. The node now names its own destination on both outcomes and carries no edge,
  which is what the supervisor already did and for the same reason.
- **A repairing run does re-present the verification gate, and that is correct.** A person
  approved it *for a change*; the run then found the change did not happen; asking again is the
  only honest thing left, and delivering on that approval would be delivering something nobody
  saw. It is why a whole-run test cannot use the "nobody has answered yet" wait for this shape.
- ~~**Open: a run that repairs does not reach `DONE`.**~~ **False, and it was this repository's
  own test lying.** A repairing run reaches `DONE`, like any other. The run that appeared to stop
  at `AWAITING_HUMAN_APPROVAL` was answering every question twice — the graph clears a question
  when it records the answer, which happens after the POST returns, so the second read is the race
  every other test in the file works around — and a second answer to the *delivery* gate left the
  run approved-everything and delivered nothing. Three attempts at that test failed the same way,
  each looking like impatience rather than the wrong question: answer-whatever-appears,
  count-sixteen, and report-finished-by-returning-`None`. The fourth used the pattern the other
  tests already use, and the defect was not there.
- ~~**The supervisor still has not fired inside a whole run.**~~ **It has** — on a whole run
  through the real graph, and on that run it found the wiring was broken in a way no routing test
  could see.
- **The rule that would catch an unobservable change was never wrong — it was never asked.** The
  check that a test passes with the change undone runs the *whole suite* with the change removed,
  precisely so it can ask "does anything notice". But it returns early when the plan named no
  test, on the reasoning that a plan adding no test has nothing to observe the change. That is true
  of the plan's tests and false of the suite, and it is the exact case that mattered: the Dockerfile
  run's plan named no test, so the one rule that could have said *"nothing here notices this
  healthcheck"* stayed silent and a policy had to notice it by reading two suite outputs.
  **The docstring now argues against its own early return**, and
  `tests/test_whether_anything_observed_the_change.py` pins the gap so whoever closes it is closing
  something named.
- **Not fixed, because the obvious fix is worse.** Deleting the early return refuses every
  documentation change this pipeline is asked for — the truthful answer to "did anything notice?"
  about a README is no, and there was nothing wrong. Separating a silent change from a harmless one
  needs to know whether the change touched something a suite could read, and
  `refuse_a_change_nothing_observed` is not told what the change wrote. That is a design decision
  with a cost on both sides, and it is written down rather than made overnight.
- ~~**An end-to-end proof of the *delivery* repair was attempted and abandoned.**~~ **It was the
  harness, and the answer was to stop using it.** The board clears a question before it records the
  answer, so a run that repairs and re-presents the verification looks identical to the race every
  other test in that file works around. Four shapes of loop were tried — count the gates, count
  twice the gates, report-finished-by-returning-`None`, and count quiet moments per artifact — and
  each failed on its own cleverness rather than on anything to do with the graph. **The graph
  compiles with its own checkpointer and its gates ask with `interrupt`, so the whole run can be
  walked without the board at all**: stream it, answer with `Command(resume=...)`, stream again.
  Nothing polls, so there is no race to lose. The delivery repair is now proved on a run that goes
  all the way — suite red, delivery refuses, supervisor sends it back, change made again, suite
  green, run reaches `DONE`.
  **And re-adding the edge the delivery node used to carry makes that test fail**, which is the only
  thing that distinguishes a check that is armed from one that is merely green. Not with the error
  the implementer's defect produced — this one dies of `DONE cannot move to AWAITING_AGENT_PICKUP`
  rather than of `Can receive only one value per step`. Both are a dead run and both are invisible
  to a unit test, which is the whole point of walking the graph.
- **And a live model has now made it seven gates on the same repository, twice refused by the
  policy and never once by an exception.** The first refusal is still the strongest thing in this
  file:

  > The plan names `Dockerfile` as the only file to change and explicitly declares `tests_to_add`
  > as empty, so nothing in this run will ever exercise the healthcheck it is adding. **A
  > `HEALTHCHECK` whose path, port, or interval is wrong does not fail loudly — the container
  > simply reports unhealthy forever** — and this plan contains no build-and-run step confirming
  > the endpoint exists and that the container reaches "healthy".

  The second is the same judgement made independently, at the verification gate, by reading the
  suite rather than the plan: the two runs are indistinguishable, and the nine integration tests
  that would exercise the interval were skipped in both. **A run whose plan adds no test is a run
  the engine cannot check**, because the check that a test passes with the change undone needs a
  test to undo it beside — so a genuinely unobservable change is caught by a person or a policy
  reading the evidence, and not by the machinery. That is a design decision with a real cost, and
  the cost is that the last line of defence is a judgement rather than an assertion. It has been asked, by a real model,
  with a real card and a real refusal, and it answered correctly — and its routing is now covered
  for all four refusals that reach it. What has not happened is an end-to-end run tripping one,
  and the reason is now clear rather than mysterious: **a gate refusal stops the run by design**,
  and both runs refused at a gate, where the supervisor is deliberately not involved. Reaching a
  node refusal needs the plan to be *right* and the implementation to be *wrong*, which is not a
  thing to ask a model for on purpose. `tests/test_the_supervisor_deciding_what_to_repeat.py` and
  a whole run through the real graph both drive the routing; what neither can do is make a real
  model misbehave on demand.
- **A run has not reached `DONE` on a real repository.** Every claim above about the merge, the
  conflict and the rebase is proven against a transport that answers, not against GitHub — and
  the two runs that got furthest were stopped by the *gate*, not by the merge. What has been
  proven on a real model against a real clone is: eight gates answered by a policy, a real
  `git clone`, a real container running the repository's own suite on both sides of a change, and
  **the repair supervisor firing for the first time and catching a test file the runner never
  opens**. What is not proven is the tail — a pull request opened against a real remote, checks
  read on its head commit, and that exact commit merged. The tenth section above says why the
  seventh is the deepest a run has got, and the merge is one node beyond it.
- **The upstream repository cannot be a delivery target, for two reasons that are facts about the
  world rather than about this system.** `paligakrzychu/wellbeing-tracker-public` has **no check
  runs at all** — no workflows, `total_count: 0` on `main` and on every pull request's head — so
  `the_suite_went_green` refuses it as `TheSuiteHasNotRunYetError`, correctly: nothing was proved
  about the commit about to be merged. And the deployment's credential holds `pull` on it and
  `admin` only on its own fork, so `merge_a_pull_request` would be refused there too. **The fork
  is the only repository this deployment can deliver to end-to-end**, and a CI workflow was added
  to it (`npm ci` then `npm test`) for exactly that reason. A deployment wanting the upstream as
  its target needs both write access and CI there, and neither is a change to this repository.
- **The product analyst was shown a repository's shape and not its code, for two real runs.** The
  security analyst had this fixed first, and `an_inspection_of_the_code` was written to fix it —
  then given to security and to briefing and to nothing else, while the stage whose question is
  *what is being asked of this repository* kept the shape-only inspection. A person asked for the
  session cookie's contract to be tested and named the file implementing it; the analyst wrote
  four requirements about that contract and then listed as an ambiguity *what `buildSetCookie`
  actually returns*, because it had been handed a listing and a `package.json`. **The gate refused
  the run on precisely that ambiguity and was right to** — the file was in the clone and the
  inspection had not been asked for it. An ambiguity the repository can answer is this system
  declining to look, and a run that produces one has not found a question.
- **`space-bunny-free` does not read the inspection, and the run says so by stopping.** It is the
  deployment's model, and on this repository it answered the same requirements question five times
  with five ambiguities, every one of them answerable from a file the inspection contained. The
  same question to `deepseek-v4-pro` — same prompt, same inspection, same run — produced **zero**.
  Nothing in the code changed between those two answers, so this is a fact about the model and not
  about the pipeline, and it is recorded here because a deployment reads this file before choosing
  a model and would otherwise learn it from a gate refusal twenty minutes into a run.
- **A durable checkpointer.** Runs are held in memory, so **a restart loses every parked run**.
  The register, the clone and every artifact survive; the graph's place in the pipeline does
  not. What *is* built is the honesty about it: the API says whether this process is holding a
  run at all, and a card for a run nobody is in reads *"the process this run was in has gone —
  ask for it again to start another attempt"* rather than *waiting for you*. Before that, the
  board invited a decision on a gate that would then answer `410`, which is a button that
  discards what is pressed into it. Making the memory durable is a real change with a real cost;
  making the board stop lying about not having one was the part that was owed today.
- **Nobody has filed a real briefing.** The filing path is proven with a stand-in for GitHub's
  issue API, and the four refusals around it were checked against a live server against a real
  briefing — but opening five issues on a third party's public repository is an outward-facing
  write with no undo, so it is the one thing left deliberately untriggered. Start a server with
  `AISDLC_CREATIVE_MODE=on`, press the button, and tick the boxes; or run
  `aisdlc brief <owner>/<name>`, which does the same filing with nobody choosing.
- **A merge has not been made against a real repository either**, and that is the same refusal for
  the same reason. `github.merge_a_pull_request` and `github.the_suite_went_green` are proven
  against a transport that answers, not against GitHub — so the one thing they cannot tell us is
  whether GitHub words a refusal the way this file believes it does, which is why the refusals quote
  GitHub's own sentence instead of classifying it.
- **Authentication.** There is none. Anybody who can reach `127.0.0.1:842` can start a run on a
  real repository and answer every gate on it. The loopback address is the whole of the
  boundary, and a deployment that needs it exposed has to put its own authentication in front.
- **A browser test tier.** The UI is served and the JSON it renders is proven; nothing drives a
  real browser. The two defects the board had when it arrived — a refused gate drawn in the
  colour and the word of an approved one, and no way to start a run at all — were found by
  reading the source, and the first is fixed. The third was found by looking at a real card, which
  is `on __interrupt__`.
- **Every unit and graph test the engine had.** Its 686 unit tests, 150 graph tests and 45
  end-to-end tests were not copied. This repository ships twenty test files, and each one is a
  claim rather than a category:

  | file | what it holds this repository to |
  |---|---|
  | `test_a_run_from_a_request_to_a_delivery.py` | a run from a sentence to a delivery, and both repairs walked end to end |
  | `test_every_stage_node_standing_on_its_own.py` | that each stage's node, the one writer of a work item, and the router work on their own, with every agent replaced by a closure |
  | `test_every_marker_this_repository_declares_is_carried_by_a_test.py` | that no marker is declared without a test behind it, and that nothing is deselected by default |
  | `test_green_means_green_on_the_commit_being_merged.py` | that "green" is the commit GitHub says the pull request points at, and that an absent verdict is never green |
  | `test_a_merge_asks_whether_the_pull_request_is_mergeable.py` | that a merge is asked about before it is attempted, and that a refusal is never read as a conflict |
  | `test_a_conflict_is_decided_by_naming_one_of_two_repairs.py` | that a collision is decided by naming one of two repairs, and that prose or another conflict's repair is refused |
  | `test_a_conflicting_delivery_is_settled_by_naming_one_of_two_repairs.py` | that a merge GitHub refused as a conflict hands the run to the repair in GitHub's own words; that a rebase sends it back to the suite rather than to the merge; that leaving a pull request open ends the run without claiming a merge, and that the repair moves no work item |
  | `test_a_rebase_puts_a_runs_commit_on_the_branch_it_joins.py` | that the rebase moves this run's commit onto the branch it would join, on a lease; that a branch somebody else has moved is left alone; that a rebase which changes nothing and one git cannot finish are both refused — the first because it is the bound on the second — and that no `git` argument carries a credential |
  | `test_a_run_merges_only_the_commit_its_suite_went_green_on.py` | that the merge is given the commit the checks were read about, and that neither new node moves the work item |
  | `test_a_briefing_can_file_its_own_opportunities.py` | that a briefing files its own opportunities with no person between, against a double for GitHub, and that the open issues are read again to do it |
  | `test_what_two_real_runs_found.py` | the defects two real runs found, and the inspections that carry the code now |
  | `test_a_work_item_waiting_to_be_picked_up.py` | that a work item nobody holds waits in the queue, that a queued work item can be claimed, and that no other stage may move to itself |
  | `test_the_supervisor_deciding_what_to_repeat.py` | every refusal routes to the supervisor and releases the work item first, and no node chooses a destination *and* carries an edge |
  | `test_a_repository_briefing_itself.py` | a repository briefs itself, and filing is refused without a credential |
  | `test_the_tag_this_system_leaves_on_what_it_writes.py` | every issue and pull request carries the project's full name, or still goes out untagged |
  | `test_whether_anything_observed_the_change.py` | the rule that catches a change nothing observed, and its one gap |
  | `test_a_real_model_judging_a_real_refusal.py` | a real model's judgement inside a real graph; skips loudly without a credential |
  | `test_the_readme_names_what_this_repository_holds_itself_to.py` | that this table names every test file, which it twice did not |
  | `test_the_tag_reaching_real_github.py` | that the tag is on a real issue and not only in a payload; files one and closes it — it found the pull-request bug |
  | `test_work_already_tracked_is_not_proposed_again.py` | that a briefing reads the repository's open issues, and that filing refuses a duplicate before anything is opened |

  The engine's own suite is where the per-agent contracts are proven, and it still exists in
  `ai-sdlc-os`. **Every one of the twenty is newer than the assembly this repository was cut
  from**, and four of them exist because a check this repository had written could not have
  failed. Ten arrived with the merge that follows a delivery, and five of those ten are about a
  commit: which one the checks were read on, whether it may be merged at all, which of two
  repairs a conflict gets, what a rebase does to a branch somebody else is using, and whether
  the run merged only what its suite went green on. The eleventh is
  `test_a_work_item_waiting_to_be_picked_up.py`, and it exists because a real run reached the
  repair supervisor for the first time and died there — see the section on the release.

  **The whole-run test replaced all seven agent seams with hardcoded closures**, so it could
  prove the wiring and could not prove a stage. A graph wired in the wrong order, a stage handed
  the wrong document, and a note that never reached the card all read the same way through it:
  the run still reached `DONE`. Six of the eight stages, the clone, the single writer of a work
  item and the router were reachable only that way, and
  `test_every_stage_node_standing_on_its_own.py` is what they are now covered by — each node
  called directly, on a state built by the production `a_run_beginning_at`, with one plain
  closure handed in and no model, no network, no credential and no container. **Those are
  characterisation tests rather than RED-then-GREEN cycles**: every one of the nine nodes was
  already correct, no assertion in that file was satisfied by a line of `src/`, and what it is
  worth is the next change.


  **And the table is checked rather than trusted**, by the last row of it. The tag feature landed
  with eleven tests and a commit message describing a README section that was never written — the
  edit anchored on a heading belonging to another repository, so it silently did nothing, and the
  commit passed because an unrelated line in the same edit did land. Two days later this table
  still said "four test files" when there were six. Both times a count went stale and nothing
  noticed, so a test now compares the files on disk against the names here and fails on either
  difference.
- **The quality gates the engine was built under.** Strict TDD, the readability guards, the
  glossary guard, the per-cycle commit discipline, `mypy --strict`, the e2e and container tiers.
  This repository was assembled for speed and carries one test, `ruff`, and a non-strict `mypy`.
  That is a real trade: the engine's safeguards are not reproduced here, and the engine is where
  they still run.
- ~~**`pyproject.toml` declared an `e2e` marker and filtered on it, and no test carried it.**~~
  **Fixed, and it was a claim about the suite that nothing could check.** The marker was declared
  in `markers`, `addopts` said `-m 'not e2e'`, and **zero tests were marked `e2e`** — so the
  filter deselected nothing and the marker named a tier that did not exist, while reading to
  anyone who opened the file as a deliberate separation copied from the engine. What this
  repository actually does is the opposite: three tests need a real model, a real `GITHUB_TOKEN`
  and a real repository to file against, and they are **collected by the default run and skipped
  with the reason printed**, so a reader is told which three and what was missing. A deselection
  is silent, and a tier that vanishes without saying why is indistinguishable from a tier with
  nothing in it — so the marker and the filter are gone,
  `test_every_marker_this_repository_declares_is_carried_by_a_test.py` compares the declared set
  with the set the tests carry, and the second direction is `--strict-markers`. **Zero
  `parametrize` in the repository is recorded rather than fixed**: where a table would read — the
  router's declared pipeline, the check runs' verdicts — this repository uses a comprehension
  over the same table instead, because a failure that names the artifact is worth more than the
  shorthand.
