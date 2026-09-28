"""The logic behind AccountProblemsFilter, the securegroups smart filter.

Answers from the snapshot, never from the other apps directly: a group check
over thousands of users stays one read, at the price of being as old as the
last run of the task.
"""

from collections import defaultdict

from django.utils.translation import gettext as _

from . import snapshot as snapshots
from .report import Report


def audit_accounts(users, reversed_logic: bool, include_corporation: bool) -> dict:
    """{user id: {"message": str, "check": bool}} in securegroups' format.

    An account outside the overview - main not in the Alliance, or no
    snapshot yet - fails either way: nothing is known about it.
    """
    result = defaultdict(lambda: {"message": _("Not in the Auth Monitor overview"), "check": False})
    current = snapshots.current()
    if current is None:
        return result

    report = Report(current)
    wanted = {user.pk for user in users}
    for corporation in report.corporations:
        for account in corporation.accounts:
            if account.user_id not in wanted:
                continue
            labels = [str(check.label) for check in account.keywords]
            if include_corporation:
                labels += [str(problem.check.label) for problem in corporation.problems]
            has_problems = bool(labels)
            result[account.user_id] = {
                "message": ", ".join(dict.fromkeys(labels)) or _("No problems"),
                "check": has_problems if reversed_logic else not has_problems,
            }
    return result
