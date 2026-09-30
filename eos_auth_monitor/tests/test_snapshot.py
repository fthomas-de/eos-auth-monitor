from unittest.mock import patch

from corptools.app_settings import CT_CHAR_MAX_INACTIVE_DAYS
from corptools.models import CharacterAudit, CharacterRoles

from django.contrib.auth.models import User

from allianceauth.eveonline.models import EveCorporationInfo

from allianceauth.tests.auth_utils import AuthUtils

from eos_auth_monitor import progress, snapshot
from eos_auth_monitor.checks import CHECKS, DIRECTOR_GROUPS, SERVICES_BY_KEY, installed_checks
from eos_auth_monitor.models import MonitorConfiguration, Snapshot
from eos_auth_monitor.sources import corptools as corptools_source

from .base import (
    ALLIANCE_ID,
    OTHER_ALLIANCE_ID,
    MonitorTestCase,
    add_alt,
    configure,
    make_corporation,
    make_token,
    make_user,
)


# every check that needs the Directors: the Director check and the groups with a Director list
NO_DIRECTOR_CHECKS = ["char_director_token_missing"] + [
    check.key for check in CHECKS if check.group in DIRECTOR_GROUPS
]


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

    def test_should_leave_out_the_characters_outside_the_alliance_when_switched_on(self):
        inside = add_alt(self.pilot, 9002, "Alt inside", corporation_id=2002)
        other_alliance = add_alt(self.pilot, 9003, "Alt allied", corporation_id=2999, alliance_id=OTHER_ALLIANCE_ID)

        with patch(
            "eos_auth_monitor.snapshot.corptools_source.character_problems", return_value={}
        ) as characters:
            account = corporation(build(alliance_characters_only=True), 2001)["accounts"][0]

        main_id = self.pilot.profile.main_character.character_id
        self.assertEqual([character["id"] for character in account["characters"]], [main_id, inside.character_id])
        # both sides sorted: the main's ID comes from the user's pk, which grows with a kept test database
        self.assertEqual(sorted(characters.call_args.args[0]), sorted([main_id, inside.character_id]))
        self.assertNotIn(other_alliance.character_id, characters.call_args.args[0])
        # the alt without an Alliance and the one in another Alliance
        self.assertEqual(account["left_out"], 2)

    def test_should_leave_out_no_character_by_default(self):
        account = corporation(build(), 2001)["accounts"][0]

        self.assertEqual(account["left_out"], 0)

    def director_problems(self, character):
        audit = CharacterAudit.objects.create(character=character, update_timestamps={})
        CharacterRoles.objects.create(character=audit, director=True)
        account = corporation(build(), 2001)["accounts"][0]
        found = next(entry for entry in account["characters"] if entry["id"] == character.character_id)
        return [item["check"] for item in found["problems"] if item["check"] == "char_director_token_missing"]

    def test_should_flag_a_director_of_the_alliance_without_a_corporation_token(self):
        self.assertEqual(self.director_problems(self.pilot.profile.main_character), ["char_director_token_missing"])

    def test_should_not_flag_a_director_of_a_corporation_outside_the_alliance(self):
        # the alt is checked for everything else, but its Corporation is none of the Alliance's
        self.assertEqual(self.director_problems(self.alt), [])

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

    def test_should_not_ask_esi_for_roles_when_nothing_needs_the_directors(self):
        ask, _ = self.handed_over(fetch_members=True, disabled_checks=NO_DIRECTOR_CHECKS)

        ask.assert_not_called()

    def test_should_ask_esi_for_roles_for_a_director_list_without_the_director_check(self):
        ask, _ = self.handed_over(
            fetch_members=True, disabled_checks=[key for key in NO_DIRECTOR_CHECKS if key != "corp_token_missing"]
        )

        ask.assert_called_once_with(2001)

    def test_should_ask_once_per_corporation_the_accounts_have_characters_in(self):
        add_alt(self.pilot, 5001, "Alt", corporation_id=2001)
        add_alt(self.pilot, 5002, "Other alt", corporation_id=2002)

        ask, _ = self.handed_over(fetch_members=True)

        self.assertEqual(sorted(call.args[0] for call in ask.call_args_list), [2001, 2002])

    def test_should_ask_about_no_corporation_outside_the_alliance(self):
        add_alt(self.pilot, 5003, "Alt elsewhere", corporation_id=5005, alliance_id=None)

        everywhere, _ = self.handed_over(fetch_members=True)
        inside, _ = self.handed_over(fetch_members=True, alliance_characters_only=True)

        # the alt is still checked, its Corporation's Directors are not the Alliance's concern
        self.assertEqual([call.args[0] for call in everywhere.call_args_list], [2001])
        self.assertEqual([call.args[0] for call in inside.call_args_list], [2001])

    def test_should_let_only_the_characters_in_the_alliance_count_as_directors(self):
        inside = add_alt(self.pilot, 5004, "Alt inside", corporation_id=2001)
        add_alt(self.pilot, 5003, "Alt elsewhere", corporation_id=5005, alliance_id=None)

        _, characters = self.handed_over(fetch_members=True)

        self.assertEqual(
            sorted(characters.call_args.kwargs["director_ids"]), sorted([self.main_id, inside.character_id])
        )

    def marker(self, directors, **config):
        with (
            patch("eos_auth_monitor.snapshot.members_source.corporation_directors", return_value=directors),
            patch("eos_auth_monitor.snapshot.members_source.corporation_members", return_value=None),
            patch("eos_auth_monitor.snapshot.corptools_source.character_problems", return_value={}),
        ):
            data = build(fetch_members=True, **config)
        return corporation(data, 2001)["no_director_token"]

    def test_should_mark_a_corporation_whose_roles_no_director_token_could_read(self):
        self.assertTrue(self.marker(None))

    def test_should_not_mark_a_corporation_whose_roles_were_read(self):
        self.assertFalse(self.marker({self.main_id}))
        self.assertFalse(self.marker(set()))

    def test_should_not_mark_anything_when_the_roles_were_never_asked_for(self):
        self.assertFalse(self.marker(None, disabled_checks=NO_DIRECTOR_CHECKS))

    def test_should_not_mark_anything_when_esi_is_switched_off(self):
        with patch("eos_auth_monitor.snapshot.members_source.corporation_directors", return_value=None) as ask:
            data = build(fetch_members=False)

        ask.assert_not_called()
        self.assertFalse(corporation(data, 2001)["no_director_token"])

    def test_should_mark_a_corporation_of_the_alliance_without_any_account(self):
        make_corporation(2002)

        with (
            patch("eos_auth_monitor.snapshot.members_source.corporation_directors", return_value=None) as ask,
            patch("eos_auth_monitor.snapshot.members_source.corporation_members", return_value=None),
            patch("eos_auth_monitor.snapshot.corptools_source.character_problems", return_value={}),
        ):
            data = build(fetch_members=True)

        self.assertTrue(corporation(data, 2002)["no_director_token"])
        self.assertEqual(sorted(call.args[0] for call in ask.call_args_list), [2001, 2002])

    def test_should_survive_a_corporation_without_a_readable_roles_list(self):
        with (
            patch("eos_auth_monitor.snapshot.members_source.corporation_directors", return_value=None),
            patch("eos_auth_monitor.snapshot.members_source.corporation_members", return_value=None),
        ):
            self.assertIsNotNone(build(fetch_members=True))


class TestDirectorLists(MonitorTestCase):
    """The Directors of each Corporation, for the lists behind the Corporation Audit and Structures tiles."""

    def setUp(self):
        super().setUp()
        make_corporation(2001)
        self.pilot = make_user("pilot", corporation_id=2001)
        self.main_id = self.pilot.profile.main_character.character_id
        # an account whose main is outside the Alliance, with a Director alt in it
        self.outsider = make_user("outsider", corporation_id=5005, alliance_id=OTHER_ALLIANCE_ID)
        self.outsider_alt = add_alt(self.outsider, 5101, "Outsider alt", corporation_id=2001)

    def directors(self, from_esi, groups=("corptools_corporations",), names=None, **config):
        with patch("eos_auth_monitor.snapshot.members_source.names", return_value=names or {}) as lookup:
            found = snapshot._directors([2001], from_esi, {self.pilot.pk}, list(groups), configure(**config))
        self.lookup = lookup
        return {row["id"]: row for row in found.get(2001, [])}

    def test_should_list_the_directors_esi_names_with_their_accounts(self):
        found = self.directors(
            {2001: {self.main_id, self.outsider_alt.character_id, 9001}},
            names={self.main_id: "pilot main", self.outsider_alt.character_id: "Outsider alt", 9001: "Stranger"},
        )

        self.assertEqual(
            {key: (row["name"], row["in_auth"], row["user_id"], row["main_name"]) for key, row in found.items()},
            {
                self.main_id: ("pilot main", True, self.pilot.pk, "pilot main"),
                # in Auth, but its account is not in the overview: no page to link to
                self.outsider_alt.character_id: ("Outsider alt", True, None, "outsider main"),
                9001: ("Stranger", False, None, None),
            },
        )

    def test_should_add_the_directors_corptools_knows(self):
        alt = add_alt(self.pilot, 5201, "Pilot alt", corporation_id=2001)
        audit = CharacterAudit.objects.create(character=alt)
        CharacterRoles.objects.create(character=audit, director=True)

        found = self.directors({}, names={5201: "Pilot alt"})

        self.assertEqual(list(found), [5201])
        self.assertEqual(found[5201]["user_id"], self.pilot.pk)

    def test_should_tell_which_director_has_a_corporation_token(self):
        make_token(self.pilot.profile.main_character, corptools_source.corporation_scopes())
        make_token(self.outsider_alt, corptools_source.corporation_scopes()[:-1])

        found = self.directors({2001: {self.main_id, self.outsider_alt.character_id}})

        self.assertEqual(found[self.main_id]["tokens"], {"corptools_corporations": True})
        self.assertEqual(found[self.outsider_alt.character_id]["tokens"], {"corptools_corporations": False})

    def test_should_leave_out_the_excluded_corporation_scopes(self):
        scopes = corptools_source.corporation_scopes()
        make_token(self.pilot.profile.main_character, scopes[:-1])

        found = self.directors({2001: {self.main_id}}, excluded_corporation_scopes=scopes[-1:])

        self.assertEqual(found[self.main_id]["tokens"], {"corptools_corporations": True})

    def test_should_tell_which_director_fetches_for_the_structure_owner(self):
        with patch(
            "eos_auth_monitor.snapshot.structures_source.owner_characters", return_value={2001: {self.main_id}}
        ) as owners:
            found = self.directors({2001: {self.main_id, 9001}}, groups=["structures"])

        owners.assert_called_once_with([2001])
        self.assertEqual(found[self.main_id]["tokens"], {"structures": True})
        self.assertEqual(found[9001]["tokens"], {"structures": False})

    def test_should_ask_nothing_without_a_director(self):
        self.assertEqual(self.directors({2001: set()}), {})
        self.lookup.assert_not_called()

    def stored(self, **config):
        with (
            patch("eos_auth_monitor.snapshot.members_source.corporation_directors", return_value={self.main_id}),
            patch("eos_auth_monitor.snapshot.members_source.corporation_members", return_value=None),
        ):
            data = build(fetch_members=True, **config)
        return [row["id"] for row in corporation(data, 2001)["directors"]]

    def test_should_store_the_directors_per_corporation(self):
        self.assertEqual(self.stored(), [self.main_id])

    def test_should_store_no_directors_without_a_director_list(self):
        without_lists = [check.key for check in CHECKS if check.group in DIRECTOR_GROUPS]

        self.assertEqual(self.stored(disabled_checks=without_lists), [])


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
