"""The one credential this system cannot do without, named once.

Reading a public repository needs no credential, which is why most of this system's tools
carry one only sometimes. Two operations cannot: forking, because a fork is an account's
copy of somebody's repository; and opening a pull request, because a pull request is
somebody's decision to review.

So the credential is required for those two and refused by name when absent, and the
refusal happens before any request is attempted. An empty credential would otherwise
arrive at GitHub as a request from nobody and come back as a 401 that explains nothing,
which is the most expensive way to learn a setting is missing.

One error rather than one per operation: the setting is the same variable either way, and
two names for one fault is two things to catch and two messages to keep in step.
"""

from __future__ import annotations


class NoCredentialError(Exception):
    """The rule is in the tool that needs the credential, and only it may say it broke.

    Raised rather than returned as a failed outcome, because there is no outcome to
    report: nothing was attempted, so there is nothing to have gone wrong.
    """
