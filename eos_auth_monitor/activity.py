"""Active in Mumble: of the days a main played EVE, on how many was it connected to Mumble too.

The periodic task notes the days from what Auth's Mumble authenticator and
corptools already store; the pages read the shares. Days are EVE time (UTC).
Only mains with Mumble linked are noted: without it there is nothing to rate.
"""

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from . import snapshot as snapshots
from .checks import is_app_installed
from .models import ActivityDay, MonitorConfiguration
from .sources import corptools as corptools_source
from .sources import services as services_source

# the Mumble server restarts every day: a connection without a disconnect that is older was lost, not kept
CONNECTED_AT_MOST = timedelta(hours=24)


def _mumble_days(connect, disconnect, now) -> set:
    if connect is None:
        return set()
    days = {connect.date()}
    if disconnect and disconnect > connect:
        days.add(disconnect.date())
    elif now - connect <= CONNECTED_AT_MOST:
        # still connected
        days.add(now.date())
    return days


def _login_days(login, logoff, read) -> set:
    if login is None:
        return set()
    days = {login.date()}
    if logoff and logoff > login:
        days.add(logoff.date())
    elif read:
        # online when corptools read it - which may be a day ago, so that day counts, not today
        days.add(read.date())
    return days


def first_day(days: int, today):
    """The first day counted: `days` back, but not before the setting's start date."""
    first = today - timedelta(days=days)
    start = MonitorConfiguration.get_solo().activity_start
    return max(first, start) if start else first


def record(now=None) -> None:
    """Note the days the stored timestamps tell of, and drop the days older than the setting keeps."""
    snapshot = snapshots.current()
    if snapshot is None or not (is_app_installed("mumble") and is_app_installed("corptools")):
        return
    now = now or timezone.now()
    days = MonitorConfiguration.get_solo().activity_days
    keep = now.date() - timedelta(days=days)
    first = first_day(days, now.date())

    # the snapshot's accounts: the mains of the Alliance, with the characters the settings count
    accounts = [account for corporation in snapshot.data["corporations"] for account in corporation["accounts"]]
    connections = services_source.mumble_connections([account["user_id"] for account in accounts])
    owners = {
        character["id"]: account["user_id"]
        for account in accounts
        if account["user_id"] in connections
        for character in account["characters"]
    }
    marks = {
        "mumble": {
            (user_id, day) for user_id, times in connections.items() for day in _mumble_days(*times, now)
        },
        "eve_login": {
            (owners[character_id], day)
            for character_id, *times in corptools_source.logins(list(owners))
            for day in _login_days(*times)
        },
    }
    for flag, pairs in marks.items():
        pairs = {(user_id, day) for user_id, day in pairs if day >= first}
        ActivityDay.objects.bulk_create(
            [ActivityDay(user_id=user_id, day=day) for user_id, day in pairs], ignore_conflicts=True
        )
        for day in {day for _user_id, day in pairs}:
            ActivityDay.objects.filter(
                day=day, user_id__in=[user_id for user_id, marked in pairs if marked == day]
            ).update(**{flag: True})
    # the start date hides days, it deletes none
    ActivityDay.objects.filter(day__lt=keep).delete()


def rates(days: int) -> dict[int, tuple[int, int]]:
    """Per account: (days with EVE and Mumble, days with EVE) over the last ``days`` whole days.

    Today is left out: a main that played in the morning may still join Mumble tonight.
    """
    today = timezone.now().date()
    return {
        row["user_id"]: (row["both"], row["logins"])
        for row in ActivityDay.objects.filter(eve_login=True, day__gte=first_day(days, today), day__lt=today)
        .values("user_id")
        .annotate(logins=Count("pk"), both=Count("pk", filter=Q(mumble=True)))
    }


def breakdown(user_id: int, days: int) -> list[ActivityDay]:
    """The days behind one main's share: today first, then the ``days`` whole days ``rates()`` counts.

    A day nothing was noted on comes as an unsaved ActivityDay with both flags off.
    """
    today = timezone.now().date()
    first = min(first_day(days, today), today)  # a start date in the future leaves today alone
    noted = {row.day: row for row in ActivityDay.objects.filter(user_id=user_id, day__gte=first)}
    dates = [today - timedelta(days=back) for back in range((today - first).days + 1)]
    return [noted.get(date) or ActivityDay(user_id=user_id, day=date) for date in dates]
