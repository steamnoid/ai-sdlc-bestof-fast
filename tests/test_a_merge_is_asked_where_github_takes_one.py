"""A merge is asked at GitHub's merge endpoint, and this exists because it was asked elsewhere.

**A run delivered a real pull request — all eight gates approved, the fork's own suite green —
and the merge failed with `404 Not Found`.** Not a conflict, not a permission, not a red check:

```text
TheMergeWasRefusedByGitHubError: GitHub did not merge pull request 43 of
steamnoid/wellbeing-tracker-public, so b9c3d01… was not landed …
GitHub answered 404 and said: Not Found
```

**And every other fact was right.** Read out of the live repository with the run's own token:
`x-oauth-scopes: … repo …`, `GET /repos/steamnoid/wellbeing-tracker-public/pulls/43` → **200**,
`mergeable: true`, `merged: false`. The credential worked, the pull request was mergeable, and the
run still could not merge.

**The address was wrong.** The module asked

```text
PUT /repos/{owner}/{name}/pulls/{number}      {"sha": …}
```

which is GitHub's *update a pull request* address. A merge is asked at

```text
PUT /repos/{owner}/{name}/pulls/{number}/merge
```

Reproduced by hand, with the run's own token, against the run's own pull request:

```text
$ curl -X PUT …/pulls/43 -d '{"sha":"b9c3d01…"}'
404
{"message": "Not Found", …}
```

**And no test noticed, because the double answers every `PUT` with a merge.** The one in
`test_a_merge_asks_whether_the_pull_request_is_mergeable.py` reads:

```python
if request.method == "PUT":
    return httpx.Response(200, json={…, "merged": True})
```

— **on the method, and not on the address.** So every property of this request is asserted
somewhere except the one that decides whether the merge can happen at all.

**This is this repository's own rule arriving somewhere it was not aimed.** A field and the
command it describes cannot disagree; **a request and the address it names cannot disagree
either**, and a double that answers anything cannot catch it. The double below answers **404 for
an address GitHub does not serve**, which is what GitHub does.
"""

from __future__ import annotations

import json
import os
import subprocess

import httpx
import pytest

from aisdlc.domain.repository import Repository
from aisdlc.tools.merge_a_pull_request import APullRequestToMerge, merge_a_pull_request

_A_REPOSITORY = Repository(owner="steamnoid", name="wellbeing-tracker-public")
_THE_COMMIT = "b9c3d018a9227c2283337600c53fd64ed86d8d6a"
_A_CREDENTIAL = "a-token-this-test-never-sends"

# **The address, written out rather than imported, because a test that reads the constant it
# is testing proves nothing about it.**
WHERE_GITHUB_TAKES_A_MERGE = "/repos/steamnoid/wellbeing-tracker-public/pulls/43/merge"


def _the_pull_request_to_merge() -> APullRequestToMerge:
    return APullRequestToMerge(
        repository=_A_REPOSITORY, number=43, the_commit_a_merge_may_land=_THE_COMMIT
    )


def _a_github_serving_only_what_github_serves(
    what_it_was_asked: list[httpx.Request],
) -> httpx.Client:
    """A GitHub that answers a merge where GitHub answers one, and 404s everywhere else.

    **The 404 is the point and it is not decoration.** GitHub answers `404 Not Found` for an
    address it does not serve, and the double every other test here uses answers `200 merged:
    true` to any `PUT` — **which is why a run spent eight gates and forty minutes discovering
    by running that its merge request went somewhere else.**
    """

    def answer(request: httpx.Request) -> httpx.Response:
        what_it_was_asked.append(request)
        if request.url.path.endswith("/merge"):
            return httpx.Response(200, json={"sha": _THE_COMMIT, "merged": True})
        if request.method == "GET":
            # **The pull request's own address, served because GitHub serves it.** A double
            # refusing the read too would be refusing more than GitHub refuses, and a double
            # that refuses more is a double that has opinions.
            return httpx.Response(
                200,
                json={
                    "number": 43,
                    "head": {"sha": _THE_COMMIT},
                    "mergeable": True,
                    "merged": False,
                },
            )
        return httpx.Response(404, json={"message": "Not Found"})

    return httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(answer))


def test_the_merge_is_asked_where_github_takes_a_merge() -> None:
    """The address, asserted rather than assumed.

    **This is the assertion that was missing, and the finding in one line.** Every other
    property of this request is already tested: the sha travels in the body, `mergeable` is
    read first, a conflict is its own refusal, a missing credential is refused rather than
    attempted. **The address was not tested at all** — and it is the part GitHub answers
    `404` to.
    """
    what_github_was_asked: list[httpx.Request] = []

    merge_a_pull_request(
        _a_github_serving_only_what_github_serves(what_github_was_asked),
        _the_pull_request_to_merge(),
        _A_CREDENTIAL,
    )

    the_addresses_asked = [a_request.url.path for a_request in what_github_was_asked]
    assert WHERE_GITHUB_TAKES_A_MERGE in the_addresses_asked, (
        f"the run asked {the_addresses_asked} and GitHub takes a merge at "
        f"{WHERE_GITHUB_TAKES_A_MERGE}. **A real run delivered a pull request with all eight "
        "gates approved and could not merge it — `GitHub answered 404 and said: Not Found`** "
        "— because the request went to the update-a-pull-request address, which is a real "
        "GitHub address that merges nothing"
    )


def test_a_github_that_will_not_serve_the_address_stops_the_run() -> None:
    """A `404` from GitHub is a refusal, and this is what one looks like from outside.

    **The other half, and the reason the first is believable.** A test asserting a path is a
    test asserting a string; this one asserts the consequence — **the run stops and quotes
    GitHub's status**, rather than reporting a merge that did not happen.
    """

    def answer_everything_with_not_found(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    a_github_that_serves_nothing = httpx.Client(
        base_url="https://api.github.com",
        transport=httpx.MockTransport(answer_everything_with_not_found),
    )

    with pytest.raises(Exception) as what_was_said:
        merge_a_pull_request(
            a_github_that_serves_nothing, _the_pull_request_to_merge(), _A_CREDENTIAL
        )

    assert "404" in str(what_was_said.value), (
        f"the refusal was {what_was_said.value}. **GitHub's status is the only fact in this "
        "refusal a person can act on** — 404 is an address, 409 is a conflict, 405 is a method"
    )


def test_github_really_does_take_a_merge_at_that_address() -> None:
    """The address is checked against GitHub itself — and skipped loudly without a token.

    **A test asserting a string against another string in the same file proves nothing.** So
    this one asks GitHub: it reads the pull request the run delivered, and **fails if that
    pull request is not mergeable**, because one that cannot be merged cannot tell a right
    address from a wrong one.

    **It reads and merges nothing.** A `GET` on a pull request this system opened.
    """
    if not os.environ.get("GITHUB_TOKEN"):
        pytest.skip("no GITHUB_TOKEN, so GitHub cannot be asked what it serves")

    answer = subprocess.run(
        [
            "curl",
            "-s",
            "-H",
            "Authorization: Bearer " + os.environ["GITHUB_TOKEN"],
            "-H",
            "Accept: application/vnd.github+json",
            "https://api.github.com/repos/steamnoid/wellbeing-tracker-public/pulls/43",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    the_pull_request = json.loads(answer.stdout)

    assert the_pull_request.get("number") == 43, (
        f"pull request 43 was not readable with this credential, so this test is measuring "
        f"nothing: {answer.stdout[:140]}"
    )
    assert the_pull_request.get("mergeable") is True, (
        f"pull request 43 is not mergeable, so it cannot tell a right address from a wrong "
        f"one: state {the_pull_request.get('state')!r}, merged "
        f"{the_pull_request.get('merged')!r}"
    )
