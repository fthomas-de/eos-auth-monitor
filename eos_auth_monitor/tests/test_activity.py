import datetime
import re
from unittest import skipUnless
from unittest.mock import patch

from django.apps import apps
from django.urls import reverse
from django.utils import timezone

from eos_auth_monitor import activity
from eos_auth_monitor.checks import is_app_installed
from eos_auth_monitor.models import ActivityDay, Snapshot
from eos_auth_monitor.report import Report
from eos_auth_monitor.sources import corptools as corptools_source
from eos_auth_monitor.sources import services as services_source

from .base import (
    MonitorTestCase,
    account_row,
    character_row,
    configure,
    corporation_row,
    make_user,
    snapshot_data,
    store_snapshot,
)

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def at(day, hour, minute=0):
    return datetime.datetime(2026, 11, day, hour, minute, tzinfo=UTC)


def day(number):
    return datetime.date(2026, 11, number)


class TestDays(MonitorTestCase):
    def test_should_count_both_days_of_a_mumble_session_over_midnight(self):
        self.assertEqual(activity._mumble_days(at(13, 23, 50), at(14, 0, 10), NOW), {day(13), day(14)})

    def test_should_count_today_while_still_connected(self):
        # the disconnect is the one of the session before
        self.assertEqual(activity._mumble_days(at(15, 20), at(15, 19), NOW), {day(15), day(16)})
        self.assertEqual(activity._mumble_days(at(15, 20), None, NOW), {day(15), day(16)})

    def test_should_not_count_a_connection_the_daily_restart_must_have_ended(self):
        self.assertEqual(activity._mumble_days(at(14, 20), None, NOW), {day(14)})

    def test_should_count_nothing_for_an_account_never_connected(self):
        self.assertEqual(activity._mumble_days(None, None, NOW), set())

    def test_should_count_both_days_of_an_eve_session_over_midnight(self):
        self.assertEqual(activity._login_days(at(13, 22), at(14, 1), at(16, 9)), {day(13), day(14)})

    def test_should_count_the_day_corptools_saw_the_character_online_not_today(self):
        # the logoff is the one of the session before
        self.assertEqual(activity._login_days(at(14, 23), at(14, 20), at(15, 0, 30)), {day(14), day(15)})

    def test_should_count_nothing_for_a_character_never_seen(self):
        self.assertEqual(activity._login_days(None, None, at(16, 9)), set())


class TestRecord(MonitorTestCase):
    def setUp(self):
        super().setUp()
        configure()
        self.linked = make_user("linked")
        self.unlinked = make_user("unlinked")
        store_snapshot(
            snapshot_data(
                [
                    corporation_row(
                        2001,
                        [
                            account_row(self.linked.pk, 1101, [character_row(1101), character_row(1102)]),
                            account_row(self.unlinked.pk, 1201),
                        ],
                    )
                ],
                services=["mumble"],
            )
        )

    def record(self, connections, logins, now=NOW):
        with (
            patch.object(activity, "is_app_installed", return_value=True),
            patch.object(services_source, "mumble_connections", return_value=connections) as asked_mumble,
            patch.object(corptools_source, "logins", return_value=logins) as asked_logins,
        ):
            activity.record(now)
        return asked_mumble, asked_logins

    def days(self):
        return set(ActivityDay.objects.values_list("user_id", "day", "eve_login", "mumble"))

    def test_should_note_the_days_of_the_main_from_any_of_its_characters(self):
        connections = {self.linked.pk: (at(15, 20), at(15, 22))}
        logins = [(1101, at(14, 20), at(14, 21), at(16, 9)), (1102, at(15, 20), at(15, 21), at(16, 9))]

        asked_mumble, asked_logins = self.record(connections, logins)

        self.assertEqual(
            self.days(), {(self.linked.pk, day(14), True, False), (self.linked.pk, day(15), True, True)}
        )
        self.assertCountEqual(asked_mumble.call_args.args[0], [self.linked.pk, self.unlinked.pk])
        # a main without Mumble linked is not rated: its characters are not even asked about
        self.assertCountEqual(asked_logins.call_args.args[0], [1101, 1102])

    def test_should_add_to_a_day_already_noted_and_never_take_back(self):
        self.record({self.linked.pk: (at(15, 20), at(15, 22))}, [])
        self.record({self.linked.pk: (at(16, 8), at(16, 9))}, [(1101, at(15, 20), at(15, 21), at(16, 9))])

        self.assertEqual(
            self.days(), {(self.linked.pk, day(15), True, True), (self.linked.pk, day(16), False, True)}
        )

    def test_should_drop_and_ignore_days_older_than_the_setting(self):
        configure(activity_days=2)
        ActivityDay.objects.create(user=self.linked, day=day(13), eve_login=True)
        ActivityDay.objects.create(user=self.linked, day=day(14), eve_login=True)

        self.record({self.linked.pk: (at(10, 20), at(10, 22))}, [])

        self.assertEqual(self.days(), {(self.linked.pk, day(14), True, False)})

    def test_should_do_nothing_without_a_snapshot(self):
        Snapshot.objects.all().delete()

        asked_mumble, _asked_logins = self.record({}, [])

        asked_mumble.assert_not_called()


class TestRates(MonitorTestCase):
    def test_should_count_the_whole_days_in_eve_and_those_with_mumble_too(self):
        user = make_user("pilot")
        today = timezone.now().date()

        def note(days_ago, eve_login, mumble):
            ActivityDay.objects.create(
                user=user, day=today - datetime.timedelta(days=days_ago), eve_login=eve_login, mumble=mumble
            )

        note(0, True, True)  # today is not over
        note(1, True, True)
        note(2, True, False)
        note(3, False, True)  # in Mumble without playing changes nothing
        note(4, True, True)
        note(5, True, True)  # before the window

        self.assertEqual(activity.rates(4), {user.pk: (2, 3)})


class TestSources(MonitorTestCase):
    @skipUnless(is_app_installed("mumble"), "the Mumble service is not installed")
    def test_should_read_the_mumble_connection_times(self):
        user = make_user("pilot")
        # not objects.create(): Auth's manager takes a user and sets a password
        apps.get_model("mumble", "MumbleUser")(
            user=user, username="pilot", pwhash="x", last_connect=at(15, 20), last_disconnect=at(15, 22)
        ).save()

        self.assertEqual(
            services_source.mumble_connections([user.pk, make_user("other").pk]),
            {user.pk: (at(15, 20), at(15, 22))},
        )

    @skipUnless(is_app_installed("corptools"), "corptools is not installed")
    def test_should_read_the_login_times_of_corptools(self):
        main = make_user("pilot").profile.main_character
        apps.get_model("corptools", "CharacterAudit").objects.create(
            character=main,
            last_known_login=at(15, 20),
            last_known_logoff=at(15, 22),
            update_timestamps={"login": at(16, 9).isoformat()},
        )

        self.assertEqual(
            corptools_source.logins([main.character_id]), [(main.character_id, at(15, 20), at(15, 22), at(16, 9))]
        )


def report(accounts, services=("mumble",)):
    return Report(store_snapshot(snapshot_data([corporation_row(2001, accounts)], services=services)))


class TestReport(MonitorTestCase):
    def accounts(self):
        return [
            account_row(11, 1101, services={"mumble": True}),
            account_row(12, 1201, services={"mumble": True}),
            account_row(13, 1301, services={"mumble": True}),
            account_row(14, 1401),
        ]

    def test_should_give_each_linked_main_its_share_and_the_tiles_their_mean(self):
        found = report(self.accounts())

        # 11: 1 of 4 days; 12: every day; 13: never in EVE; 14: no Mumble
        found.add_activity({11: (1, 4), 12: (3, 3), 14: (2, 2)})

        corporation = found.corporation(2001)
        shares = {account.user_id: account.activity and account.activity.percent for account in corporation.accounts}
        self.assertEqual(shares, {11: 25, 12: 100, 13: None, 14: None})
        self.assertEqual((found.account(11)[1].activity.part, found.account(11)[1].activity.total), (1, 4))
        # the mean of 25 and 100, each main once - not 4 of 7 days
        self.assertEqual(corporation.activity.percent, 62)
        mumble = next(row for row in corporation.service_counts if row.service.key == "mumble")
        self.assertEqual(mumble.activity.percent, 62)
        self.assertEqual(mumble.percent, 75)
        self.assertEqual(found.cockpit()[0].activity.percent, 62)
        self.assertEqual([str(row.label) for row in corporation.rows], ["Mumble", "Active in Mumble"])

    def test_should_show_no_share_where_nobody_played(self):
        found = report(self.accounts())

        found.add_activity({})

        self.assertIsNone(found.corporation(2001).activity.percent)

    def test_should_show_nothing_without_the_mumble_service(self):
        found = report(self.accounts(), services=("discord",))

        found.add_activity({11: (1, 4)})

        corporation = found.corporation(2001)
        self.assertFalse(found.activity_shown)
        self.assertIsNone(corporation.accounts[0].activity)
        self.assertEqual([str(row.label) for row in corporation.rows], ["Discord"])
        self.assertIsNone(found.cockpit()[0].activity)


class TestPages(MonitorTestCase):
    def setUp(self):
        super().setUp()
        configure()
        self.leader = make_user("leader", "eos_auth_monitor.view_all")
        self.pilot = make_user("pilot")
        accounts = [
            account_row(self.pilot.pk, 1101, services={"mumble": True}),
            account_row(self.leader.pk, 1201),
        ]
        store_snapshot(snapshot_data([corporation_row(2001, accounts)], services=["mumble"]))
        yesterday = timezone.now().date() - datetime.timedelta(days=1)
        ActivityDay.objects.create(user=self.pilot, day=yesterday, eve_login=True, mumble=True)
        ActivityDay.objects.create(
            user=self.pilot, day=yesterday - datetime.timedelta(days=1), eve_login=True, mumble=False
        )
        self.client.force_login(self.leader)

    def content(self, name, *args):
        return self.client.get(reverse(f"eos_auth_monitor:{name}", args=args)).content.decode()

    def cells(self, content):
        return re.findall(r'<td data-order="(-?\d+)" class="[^"]*eos-auth-monitor-activity', content)

    def test_should_show_the_share_below_the_linked_share_on_the_mumble_tiles(self):
        pattern = re.compile(r'eos-auth-monitor-activity">\s*Active in Mumble:\s*<span class="fw-semibold ([^"]+)">50')

        for page in (self.content("index"), self.content("corporation", 2001)):
            self.assertEqual(pattern.findall(page), ["text-danger"])

    def test_should_add_a_column_to_the_overview_table(self):
        content = self.content("index")
        table = content[content.index("eos-auth-monitor-overview-table"):]

        self.assertIn('<th title="Active in Mumble">', table)
        # the Mumble column (1 of 2 mains linked) and the new one, both 50 %
        self.assertEqual(table[table.index("</thead>"):table.index("</table>")].count("50&nbsp;%"), 2)

    def test_should_show_each_main_its_share_in_the_mumble_lists(self):
        for page in (self.content("service", "mumble"), self.content("corporation_service", 2001, "mumble")):
            # the pilot with 1 of 2 days, the leader without Mumble
            self.assertCountEqual(self.cells(page), ["50", "-1"])
            self.assertIn('title="1 of 2"', page)
