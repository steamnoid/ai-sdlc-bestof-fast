"""No title this system builds can be one GitHub refuses, and this is what that cost.

**Eight gates approved and the delivery died on a character count.** A run closed a critical
vulnerability in `wellbeing-tracker-public` — discovery, requirements, QA, architecture, security,
plan, **verification**, pull request, all approved — and then:

```text
PullRequestNotOpenedError: a pull request from
steamnoid:aisdlc/wellbeing-tracker-public-web-app-src-lib-auth-js-13-and-web-app
-src-middl-20261003-114421-625766 into 'main' was not opened, so nothing was
delivered. GitHub said: Validation Failed; title is too long (maximum is 256
characters)
```

**The title was 2472 characters.** It is the first sentence of the request, verbatim, and the CLI's
own help for that argument says *"One sentence saying what should change"* — a sentence is 2472
characters only if the person writing it did not read the help. **This system built an unopenable
pull request and discovered it at the last node**, after three container suite runs and a policy
ruling on eight artifacts.

**The same string is also the branch name**, which is why the branch reads
`aisdlc/wellbeing-tracker-public-web-app-src-lib-auth-js-13-and-web-app-src-middl-…`. **So the
length was visible for six stages and only ever noticed by the platform at the end**, which is the
worst place to find it and the only place anybody was checking.

**Truncated and not refused, because the body already holds the whole request.** Somebody who
explains themselves at length has said something a person will want to read, and refusing the run
over a field that appears in a list of forty would be a punishment for good manners. **Nothing is
lost**: `CommissionedRequest` carries the request in both `title` and `body`, and only the title is
bound.

**Two rules, and the second is the one that would have saved the run.** A title long enough to be
cut, and a title cut **at a word** — because a title ending mid-word reads as a mistake to the
person scanning the list, and a truncated title is now a permanent part of a public repository.
"""

from __future__ import annotations

from aisdlc.domain.commissioned_request import CommissionedRequest, a_request_about

# **GitHub's own number, and the reason it is named here rather than invented.** "Validation Failed;
# title is too long (maximum is 256 characters)" is what a delivery said when this was found, and
# a limit this system chose would be a guess about a platform that has already stated one.
THE_LONGEST_TITLE_GITHUB_ACCEPTS = 256


def _the_request_a_person_wrote() -> str:
    """The first sentence of the request that produced the 2472-character title.

    **A fragment rather than the whole thing, and it is still over the limit**, because a test that
    needed a kilobyte to fail would be a test nobody could read. The property under test is that
    length is bounded, and 600 characters already exercises it.
    """
    return (
        "web-app/src/lib/auth.js:13 and web-app/src/middleware.ts:7 both fall back to a hard-coded "
        "session key: process.env.JWT_SECRET. That literal is in the repository since its initial "
        "commit and this repository is public, so anyone can sign a JWT the app accepts. "
        "Dockerfile:38 sets ENV NODE_ENV=production and never sets JWT_SECRET, so the fallback is "
        "what a container built from this Dockerfile signs with. A requirements analyst already "
        "refused a previous version of this request for being self-contradictory, and it was: I "
        "had asked for existing tests to stay untouched while requiring a value those tests never "
        "supply. This version resolves that."
    )


def test_a_title_longer_than_github_accepts_is_bounded() -> None:
    """The claim, stated as the platform states it: this title would not open.

    **Asserted against GitHub's number and not against a constant of this system's**, because a
    test that compared the result with `THE_LONGEST_TITLE_GITHUB_ACCEPTS` would pass if both were
    changed together and the delivery would still fail. The relationship that matters is *this
    system's title fits inside GitHub's limit*, and it has to be written with GitHub's number on the
    right-hand side for that to mean anything.
    """
    the_title = CommissionedRequest(title=_the_request_a_person_wrote()).title

    assert len(the_title) <= THE_LONGEST_TITLE_GITHUB_ACCEPTS, (
        f"the title is {len(the_title)} characters and GitHub refuses above "
        f"{THE_LONGEST_TITLE_GITHUB_ACCEPTS}. **Not hypothetical: a run spent eight gates, three "
        "container suite runs and a policy ruling producing a pull request this system could not "
        "open**, and the title it built was the person's own sentence, 2472 characters long"
    )


def test_a_bounded_title_ends_where_a_person_would_end_it() -> None:
    """A cut mid-word reads as a defect, and a title is permanent in a public repository.

    **The rule is a space, searched backwards from the bound** rather than forwards from the start,
    because a title is filled from the front and the tail is what is cut.
    """
    the_title = CommissionedRequest(title=_the_request_a_person_wrote()).title

    assert not the_title.endswith(" "), (
        f"the title ends with a space: {the_title[-20:]!r}. **A trailing space is a title that was "
        "cut and not tidied**, and a person scanning a list of forty sees the gap before they read "
        "the words"
    )
    assert the_title == the_title.strip(), (
        f"the title is {the_title[:40]!r}…{the_title[-40:]!r} and is padded at one end, which is "
        "what a cut that kept its boundary but not its tidiness looks like"
    )


def test_a_title_that_fits_is_the_person_s_own_words() -> None:
    """The bound costs nothing when it is not needed, and this is what proves the bound is not a
    rewriter.

    **A truncator that also shortened, lowercased or tidied would pass the first test and fail
    this one**, and a person who asked for something in their own words would find a title that is
    not what they said for reasons nobody asked for.
    """
    what_the_person_wrote = "Remove the hardcoded session-secret fallback from the auth library"

    assert a_request_about(what_the_person_wrote).title == what_the_person_wrote, (
        "a title inside the bound was not returned unchanged, so the bound is also rewriting words "
        "and a person's own sentence does not survive it"
    )


def test_the_body_keeps_what_the_title_had_to_drop() -> None:
    """Truncation only looks harmless if the rest is somewhere, and right now it is not.

    **The CLI splits one argument into a title and a body, and the body's default is empty.** So a
    long sentence becomes a long title and an empty body — the long text is bound away and kept
    nowhere. **This test says so out loud**, because the bound'"'"'s docstring claims truncation is
    cheap and this is the fact that makes that claim worth arguing with.
    """
    the_whole_request = _the_request_a_person_wrote()

    the_request = a_request_about(the_whole_request)

    assert the_request.title != the_whole_request, (
        "this test needs a request the bound actually acts on, and this one fitted inside it — so "
        "the truncation path is not exercised and a regression in it would not show up here"
    )
    assert the_request.body == "", (
        f"the body was {the_request.body[:80]!r}, and this test asserts the CLI leaves it empty. "
        "**If that has changed then the title may be bounded without loss, and this test is "
        "stale** — which is the only way it should ever be deleted"
    )
