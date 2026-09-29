from unittest.mock import patch

from corptools.app_settings import CT_CHAR_MAX_INACTIVE_DAYS

from django.contrib.auth.models import User

from allianceauth.eveonline.models import EveCorporationInfo

from allianceauth.tests.auth_utils import AuthUtils

from eos_auth_monitor import progress, snapshot
from eos_auth_monitor.checks import CHECKS, SERVICES_BY_KEY, installed_checks
from eos_auth_monitor.models import MonitorConfiguration, Snapshot

from .base import ALLIANCE_ID, OTHER_ALLIANCE_ID, MonitorTestCase, add_alt, configure, make_corporation, make_user


def build(**config):
    return snapshot.build(configure(**config))


def corporation(data, corporation_id):
    return next(row for row in data["corporations"] if row["id"] == corporation_id)


class TestAccounts(MonitorTestCase):
    def setUp(self):
        super().setUp()
        make_corporation(2001)
        self.pilot = make_user("pilot", corporation_id=2001)
        self.alt = add_alt(self.pilot, 9001, "Alt outside", corporation_id=5005, alliance_id=None)

    def test_should_be_empty_without_an_alliance(self):
        self.assertIsNone(build(alliance_id=None))

    def test_should_put_an_account_on_the_tile_of_its_main(self):
        data = build()

        accounts = corporation(data, 2001)["accounts"]
        self.assertEqual([account["user_id"] for account in accounts], [self.pilot.pk])

    def test_should_check_every_character_of_the_account(self):
        account = corporation(build(), 2001)["accounts"][0]

        # main first, then the alts; the alt outside the Alliance included
        self.assertEqual(
            [character["id"] for character in account["characters"]],
            [self.pilot.profile.main_character.character_id, self.alt.character_id],
        )
        self.assertTrue(all(character["problems"] for character in account["characters"]))

    def test_should_take_the_character_count_from_what_auth_stores_for_the_corporation(self):
        EveCorporationInfo.objects.filter(corporation_id=2001).update(member_count=290)
        # a Corporation only known through a main has no stored count
        make_user("visitor", corporation_id=2555)

        data = build()

        self.assertEqual(corporation(data, 2001)["member_total"], 290)
        self.assertIsNone(corporation(data, 2555)["member_total"])

    def test_should_leave_out_accounts_with_their_main_elsewhere(self):
        spy = make_user("spy", corporation_id=2001, alliance_id=OTHER_ALLIANCE_ID)
        add_alt(spy, 9100, "Spy alt", corporation_id=2001)

        accounts = [account["user_id"] for row in build()["corporations"] for account in row["accounts"]]

        self.assertEqual(accounts, [self.pilot.pk])

    def test_should_list_corporations_without_mains_and_mains_without_known_corporation(self):
        make_corporation(2002)
        make_user("newbie", corporation_id=2003)

        data = build()

        self.assertEqual([row["id"] for row in data["corporations"]], [2001, 2002, 2003])
        self.assertEqual(corporation(data, 2002)["accounts"], [])

    def test_should_keep_a_main_without_ownership(self):
        # built by hand: deleting the ownership would make Auth clear the main too
        legacy = AuthUtils.create_user("legacy")
        main = AuthUtils.add_main_character_2(
            legacy, "Legacy main", character_id=8001, corp_id=2001, alliance_id=ALLIANCE_ID
        )

        accounts = {account["user_id"]: account for account in corporation(build(), 2001)["accounts"]}

        self.assertEqual([c["id"] for c in accounts[legacy.pk]["characters"]], [main.character_id])


class TestChecksAndServices(MonitorTestCase):
    def setUp(self):
        super().setUp()
        make_corporation(2001)
        self.pilot = make_user("pilot", corporation_id=2001)

    def test_should_run_no_check_that_is_switched_off(self):
        data = build(disabled_checks=[check.key for check in CHECKS])

        row = corporation(data, 2001)
        self.assertEqual(data["checks"], [])
        self.assertEqual(row["problems"], [])
        self.assertEqual(row["accounts"][0]["characters"][0]["problems"], [])

    def test_should_record_the_checks_it_ran(self):
        data = build(disabled_checks=["corp_data_stale"])

        self.assertEqual(data["checks"], [check.key for check in installed_checks() if check.key != "corp_data_stale"])

    def test_should_take_the_stale_limit_from_corptools_unless_set(self):
        self.assertEqual(build()["stale_after_days"], CT_CHAR_MAX_INACTIVE_DAYS)
        self.assertEqual(build(stale_after_days=9)["stale_after_days"], 9)

    def test_should_pass_the_stale_limit_to_the_corporation_check(self):
        with patch("eos_auth_monitor.snapshot.corptools_source.corporation_problems", return_value={}) as check:
            build(stale_after_days=9)

        self.assertEqual(check.call_args.args[2], 9)

    def test_should_mark_linked_services_per_account(self):
        other = make_user("other", corporation_id=2001)
        with (
            patch("eos_auth_monitor.snapshot.enabled_services", return_value=[SERVICES_BY_KEY["discord"]]),
            patch("eos_auth_monitor.snapshot.services_source.linked_user_ids", return_value={other.pk}),
        ):
            data = build()

        linked = {account["user_id"]: account["services"] for account in corporation(data, 2001)["accounts"]}
        self.assertEqual(data["services"], ["discord"])
        self.assertEqual(linked, {self.pilot.pk: {"discord": False}, other.pk: {"discord": True}})


class TestUpdate(MonitorTestCase):
    def test_should_store_one_snapshot(self):
        make_corporation(2001)
        configure()

        snapshot.update()
        snapshot.update()

        self.assertEqual(Snapshot.objects.count(), 1)
        self.assertEqual(snapshot.current().data["alliance_id"], MonitorConfiguration.get_solo().alliance.alliance_id)

    def test_should_drop_the_snapshot_when_the_alliance_is_removed(self):
        configure()
        snapshot.update()
        configure(alliance_id=None)

        snapshot.update()

        self.assertFalse(Snapshot.objects.exists())

    def test_should_report_every_phase(self):
        configure()
        phases = []

        snapshot.update(on_step=lambda phase, *args: phases.append(phase))

        self.assertEqual(list(dict.fromkeys(phases)), list(progress.PHASES))

    def test_should_store_what_the_build_cost(self):
        make_corporation(2001)
        add_alt(make_user("pilot"), 3001, "Alt")
        configure()

        metrics = snapshot.update().data["metrics"]

        self.assertGreater(metrics["queries"], 0)
        self.assertEqual(list(metrics["phases"]), list(progress.PHASES))
        self.assertEqual((metrics["accounts"], metrics["characters"]), (1, 2))
        self.assertGreater(metrics["payload_bytes"], 0)
        self.assertGreaterEqual(metrics["seconds"], metrics["query_seconds"])

    def test_should_count_only_the_queries_of_its_own_build(self):
        make_corporation(2001)
        configure()
        first = snapshot.update().data["metrics"]["queries"]

        User.objects.count()  # outside any build: must not add to the next one
        second = snapshot.update().data["metrics"]["queries"]

        self.assertEqual(first, second)

    def test_should_count_the_member_lists_it_could_read(self):
        make_corporation(2001)
        make_corporation(2002)
        configure(fetch_members=True)

        with (
            patch("eos_auth_monitor.snapshot.members_source.corporation_members", side_effect=[[1], None]),
            patch("eos_auth_monitor.snapshot.members_source.names", return_value={1: "Nobody"}),
        ):
            metrics = snapshot.update().data["metrics"]

        self.assertEqual(metrics["member_lists"], 1)


class TestExclusions(MonitorTestCase):
    def setUp(self):
        super().setUp()
        make_corporation(2001)
        make_user("pilot", corporation_id=2001)

    def test_should_hand_the_excluded_sections_and_scopes_to_corptools(self):
        with (
            patch("eos_auth_monitor.snapshot.corptools_source.character_problems", return_value={}) as characters,
            patch("eos_auth_monitor.snapshot.corptools_source.corporation_problems", return_value={}) as corporations,
        ):
            build(
                excluded_character_sections=["mails"],
                excluded_character_scopes=["a"],
                excluded_corporation_sections=["observers"],
                excluded_corporation_scopes=["b"],
            )

        self.assertEqual(characters.call_args.args[2:], (["mails"], ["a"], ["b"], set()))
        self.assertEqual(corporations.call_args.args[3:], (["observers"], ["b"]))


class TestDirectorsFromEsi(MonitorTestCase):
    def setUp(self):
        super().setUp()
        make_corporation(2001)
        self.pilot = make_user("pilot", corporation_id=2001)
        self.main_id = self.pilot.profile.main_character.character_id

    def handed_over(self, **config):
        with (
            patch("eos_auth_monitor.snapshot.members_source.corporation_directors", return_value={self.main_id}) as ask,
            patch("eos_auth_monitor.snapshot.members_source.corporation_members", return_value=None),
            patch("eos_auth_monitor.snapshot.corptools_source.character_problems", return_value={}) as characters,
        ):
            build(**config)
        return ask, characters

    def test_should_hand_the_directors_esi_names_to_corptools(self):
        ask, characters = self.handed_over(fetch_members=True)

        ask.assert_called_once_with(2001)
        self.assertEqual(characters.call_args.args[-1], {self.main_id})

    def test_should_not_ask_esi_for_roles_when_member_lists_are_switched_off(self):
        ask, characters = self.handed_over(fetch_members=False)

        ask.assert_not_called()
        self.assertEqual(characters.call_args.args[-1], set())

    def test_should_not_ask_esi_for_roles_when_the_director_check_is_off(self):
        ask, _ = self.handed_over(fetch_members=True, disabled_checks=["char_director_token_missing"])

        ask.assert_not_called()

    def test_should_ask_once_per_corporation_the_accounts_have_characters_in(self):
        add_alt(self.pilot, 5001, "Alt", corporation_id=2001)
        add_alt(self.pilot, 5002, "Other alt", corporation_id=2002)

        ask, _ = self.handed_over(fetch_members=True)

        self.assertEqual(sorted(call.args[0] for call in ask.call_args_list), [2001, 2002])

    def test_should_survive_a_corporation_without_a_readable_roles_list(self):
        with (
            patch("eos_auth_monitor.snapshot.members_source.corporation_directors", return_value=None),
            patch("eos_auth_monitor.snapshot.members_source.corporation_members", return_value=None),
        ):
            self.assertIsNotNone(build(fetch_members=True))


class TestMembers(MonitorTestCase):
    """Members of a Corporation, reduced to their mains."""

    def setUp(self):
        super().setUp()
        make_corporation(2001)
        self.pilot = make_user("pilot", corporation_id=2001)
        self.pilot_alt = add_alt(self.pilot, 9001, "Pilot alt", corporation_id=2001)
        self.visitor = make_user("visitor", corporation_id=5005, alliance_id=None)
        self.visitor_alt = add_alt(self.visitor, 9002, "Visitor alt", corporation_id=2001)

    def build_with_members(self, member_ids, names=None):
        with (
            patch("eos_auth_monitor.snapshot.members_source.corporation_members", return_value=member_ids) as fetch,
            patch("eos_auth_monitor.snapshot.members_source.names", return_value=names or {}) as lookup,
        ):
            data = build(fetch_members=True)
        return corporation(data, 2001), fetch, lookup

    def test_should_count_members_of_its_own_accounts_as_registered(self):
        row, _, _ = self.build_with_members([self.pilot.profile.main_character.character_id, 9001])

        self.assertEqual(row["member_count"], 2)
        self.assertEqual(row["other_mains"], [])
        self.assertEqual(row["unregistered"], [])

    def test_should_reduce_a_member_to_its_main_elsewhere(self):
        row, _, _ = self.build_with_members([9002])

        self.assertEqual(
            row["other_mains"],
            [
                {
                    "user_id": self.visitor.pk,
                    "main_id": self.visitor.profile.main_character.character_id,
                    "main_name": "visitor main",
                    "main_corporation_name": "Corp 5005",
                    "characters": [{"id": 9002, "name": "Visitor alt"}],
                }
            ],
        )

    def test_should_count_an_unknown_member_as_a_main_of_its_own(self):
        row, _, lookup = self.build_with_members([7777], names={7777: "Stranger"})

        self.assertEqual(row["unregistered"], [{"id": 7777, "name": "Stranger"}])
        self.assertEqual(lookup.call_args.args[0], [7777])

    def test_should_say_when_the_list_could_not_be_read(self):
        row, _, _ = self.build_with_members(None)

        self.assertIsNone(row["member_count"])

    def test_should_not_ask_esi_when_switched_off(self):
        with patch("eos_auth_monitor.snapshot.members_source.corporation_members") as fetch:
            row = corporation(build(fetch_members=False), 2001)

        fetch.assert_not_called()
        self.assertIsNone(row["member_count"])
