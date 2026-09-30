"""The logic behind CharacterProblemsFilter, the securegroups smart filter.

Answers from the snapshot, never from the other apps directly: a group check
over thousands of users stays one read, at the price of being as old as the
last run of the task.
"""

from collections import defaultdict

from django.utils.translation import gettext as _

from . import snapshot as snapshots
from .report import Report


def audit_accounts(users, reversed_logic: bool) -> dict:
    """{user id: {"message": str, "check": bool}} in securegroups' format.

    The whole account counts - every character, alts in other Corporations
    included, as far as *Only characters in the Alliance* keeps them. An
    account the monitor knows nothing about - main not in the Alliance, or no
    snapshot yet - fails either way (the user's choice): without a snapshot a
    smart group loses every member until the next rebuild.
    """
    current = snapshots.current()
    if current is None:
        return defaultdict(lambda: {"message": _("No Auth Monitor result yet"), "check": False})

    result = defaultdict(lambda: {"message": _("Not in the Auth Monitor overview"), "check": False})
    report = Report(current)
    for user in users:
        _corporation, account = report.account(user.pk)
        if account is None:
            continue
        labels = [str(check.label) for check in account.keywords]
        has_problems = bool(labels)
        result[user.pk] = {
            "message": ", ".join(labels) or _("No problems"),
            "check": has_problems if reversed_logic else not has_problems,
        }
    return result
