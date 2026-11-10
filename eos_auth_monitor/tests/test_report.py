from django.urls import reverse

from eos_auth_monitor.report import Report, Row, _problems, describe, shorten
from eos_auth_monitor.sources.spy_network import SpyMarker

from .base import MonitorTestCase, account_row, character_row, corporation_row, snapshot_data, store_snapshot

AUDIT_MISSING = {"check": "char_audit_missing", "detail": []}
SCOPES_MISSING = {"check": "char_scopes_missing", "detail": ["a", "b"]}
CORP_TOKEN_MISSING = {"check": "corp_token_missing", "detail": []}
NO_OWNER = {"check": "structures_no_owner", "detail": []}


def report(corporations, **kwargs):
    return Report(store_snapshot(snapshot_data(corporations, **kwargs)))


class TestDirectorMarker(MonitorTestCase):
    def test_should_read_the_marker_of_a_corporation(self):
        marked = {**corporation_row(2001), "no_director_token": True}

        found = report([marked, corporation_row(2002)])

        self.assertTrue(found.corporation(2001).no_director_token)
        self.assertFalse(found.corporation(2002).no_director_token)

    def test_should_not_mark_a_corporation_of_an_older_snapshot(self):
        self.assertFalse(report([corporation_row(2001)]).corporation(2001).no_director_token)


class TestGaugeTargets(MonitorTestCase):
    def test_should_send_every_gauge_to_its_list(self):
        account = account_row(11, 1101)
        gauges = report(
            [corporation_row(2001, [account])],
            checks=["char_audit_missing", "corp_token_missing", "structures_no_owner"],
            services=["discord"],
        ).cockpit()

        targets = {str(gauge.label): gauge.url for gauge in gauges}
        self.assertEqual(
            targets,
            {
                "Discord": reverse("eos_auth_monitor:service", args=["discord"]),
                "Character Audit complete": reverse("eos_auth_monitor:character_audit"),
                "Corporation Audit working": reverse("eos_auth_monitor:directors", args=["corptools_corporations"]),
                "Structures working": reverse("eos_auth_monitor:directors", args=["structures"]),
            },
        )

    def test_should_leave_a_gauge_unlinked_when_its_page_does_not_resolve(self):
        self.assertEqual(Row("Somewhere", "fas fa-x", 1, 1, url_name="nowhere:page").url, "")
        self.assertEqual(Row("Nothing", "fas fa-x", 1, 1).url, "")


def director_row(character_id, tokens=None, in_auth=True, user_id=None, main_name=None):
    return {
        "id": character_id,
        "name": f"Char {character_id}",
        "in_auth": in_auth,
        "user_id": user_id,
        "main_name": main_name,
        "tokens": dict(tokens or {}),
    }


class TestAltsInAnotherCorporation(MonitorTestCase):
    """An account may have characters in several Corporations of the Alliance; each counts where it is."""

    def found(self):
        account = account_row(
            11,
            1101,
            [
                character_row(1101),
                character_row(1102, [AUDIT_MISSING], corporation_id=2002),
                # a Corporation outside the overview: counted with the main
                character_row(1103, [SCOPES_MISSING], corporation_id=5005),
            ],
        )
        return report(
            [corporation_row(2001, [account]), corporation_row(2002)], checks=["char_audit_missing"]
        )

    def test_should_count_each_character_in_its_own_corporation(self):
        found = self.found()
        main_corporation, alt_corporation = found.corporation(2001), found.corporation(2002)

        self.assertEqual([character.id for character in main_corporation.accounts[0].characters], [1101, 1103])
        self.assertEqual([account.user_id for account in alt_corporation.visiting], [11])
        self.assertEqual([character.id for character in alt_corporation.visiting[0].characters], [1102])
        self.assertEqual(alt_corporation.visiting[0].main_corporation_name, "Corp 2001")

    def test_should_rate_the_alts_corporation_by_the_alt(self):
        found = self.found()
        main_corporation, alt_corporation = found.corporation(2001), found.corporation(2002)

        self.assertEqual(alt_corporation.problem_count, 1)
        self.assertEqual([todo.check.key for todo in alt_corporation.todos], ["char_audit_missing"])
        self.assertEqual([todo.check.key for todo in main_corporation.todos], ["char_scopes_missing"])
        rows = {str(row.label): (row.part, row.total) for row in alt_corporation.check_rows}
        self.assertEqual(rows["Character Audit"], (0, 1))
        # the alt's Corporation has no main of its own; its services count nobody
        self.assertEqual(alt_corporation.mains, 0)

    def test_should_keep_the_whole_account_for_the_account_page(self):
        corporation, account = self.found().account(11)

        self.assertEqual(corporation.id, 2001)
        self.assertEqual([character.id for character in account.characters], [1101, 1102, 1103])
        self.assertEqual([account.user_id for account in self.found().accounts], [11])


class TestDirectors(MonitorTestCase):
    def found(self, group="corptools_corporations"):
        first = {
            **corporation_row(2001),
            "directors": [
                director_row(1101, {"corptools_corporations": True, "structures": False}),
                director_row(1102, {"corptools_corporations": False, "structures": True}),
            ],
        }
        second = {**corporation_row(2002), "directors": [director_row(2201, {"corptools_corporations": False})]}
        found = report([first, second], checks=["corp_token_missing", "structures_no_owner"])
        return [(corporation.id, director.id, has_token) for corporation, director, has_token in found.directors(group)]

    def test_should_list_the_directors_without_the_token_first(self):
        self.assertEqual(self.found(), [(2001, 1102, False), (2002, 2201, False), (2001, 1101, True)])

    def test_should_ask_each_list_for_its_own_token(self):
        # a token the snapshot does not mention counts as missing
        self.assertEqual(self.found("structures"), [(2001, 1101, False), (2002, 2201, False), (2001, 1102, True)])

    def test_should_read_a_snapshot_without_directors(self):
        found = report([corporation_row(2001)], checks=["corp_token_missing"])

        self.assertEqual(found.directors("corptools_corporations"), [])

    def test_should_have_a_director_list_only_for_a_corporation_group_whose_checks_ran(self):
        found = report([corporation_row(2001)], checks=["char_audit_missing", "corp_token_missing"])

        self.assertTrue(found.has_director_list("corptools_corporations"))
        self.assertFalse(found.has_director_list("structures"))
        self.assertFalse(found.has_director_list("corptools_characters"))


class TestAccountDirectors(MonitorTestCase):
    """The Directors of the main's Corporation among an account's characters, wherever those are."""

    def found(self):
        account = account_row(
            11,
            1101,
            [
                character_row(1102, corporation_id=2002),
                character_row(1101),
                character_row(1103, corporation_id=2002),
                character_row(1104),
            ],
        )
        main_corporation = {**corporation_row(2001, [account]), "directors": [director_row(1101), director_row(1102)]}
        # a Director of the alt's own Corporation is none of the main's
        alt_corporation = {**corporation_row(2002), "directors": [director_row(1103)]}
        return report([main_corporation, alt_corporation])

    def test_should_name_the_directors_of_the_mains_corporation(self):
        self.assertEqual(self.found().account(11)[1].directors, ["Char 1101", "Char 1102"])

    def test_should_keep_them_on_the_card_of_a_visiting_main(self):
        self.assertEqual(self.found().corporation(2002).visiting[0].directors, ["Char 1101", "Char 1102"])

    def test_should_name_none_from_a_snapshot_without_directors(self):
        self.assertEqual(report([corporation_row(2001, [account_row(11, 1101)])]).account(11)[1].directors, [])


class TestCorporationLists(MonitorTestCase):
    def corporation(self):
        return report(
            [
                corporation_row(
                    2001,
                    [
                        account_row(
                            11, 1101, [character_row(1101, [AUDIT_MISSING]), character_row(1102, [SCOPES_MISSING])]
                        ),
                        account_row(12, 1201, [character_row(1201), character_row(1202, [AUDIT_MISSING])]),
                        account_row(13, 1301),
                    ],
                )
            ],
            checks=["char_audit_missing", "char_scopes_missing"],
        ).corporation(2001)

    def test_should_group_the_mains_by_failed_check(self):
        todos = self.corporation().todos

        self.assertEqual(
            [(todo.check.key, todo.names) for todo in todos],
            [("char_audit_missing", "Char 1101, Char 1201"), ("char_scopes_missing", "Char 1101")],
        )

    def test_should_list_the_mains_without_problems(self):
        self.assertEqual([account.main_name for account in self.corporation().problem_free_accounts], ["Char 1301"])

    def test_should_split_the_characters_of_an_account(self):
        account = self.corporation().accounts[1]

        self.assertEqual([character.name for character in account.listed_characters], ["Char 1202"])
        self.assertEqual([character.name for character in account.problem_free_characters], ["Char 1201"])

    def test_should_give_every_check_a_hint(self):
        from eos_auth_monitor.checks import CHECKS

        self.assertEqual([check.key for check in CHECKS if not check.hint], [])

    def test_should_give_every_character_check_its_charlink_hints(self):
        # a character's problem links to aa-charlink on the account page and on My account
        from eos_auth_monitor.checks import CHARACTER, CHECKS

        characters = [check for check in CHECKS if check.scope == CHARACTER]
        self.assertEqual([check.key for check in characters if not check.charlink_hint], [])
        self.assertEqual([check.key for check in characters if not check.own_hint], [])
        self.assertEqual([check.key for check in characters if not check.own_app_hint], [])


class TestOverviewTable(MonitorTestCase):
    def test_should_align_the_columns_of_every_corporation(self):
        counted = corporation_row(2001, [account_row(11, 1101, services={"discord": True})])
        counted["member_count"] = 2
        uncounted = corporation_row(2002, [account_row(22, 2201, corporation_id=2002)])

        found = report([uncounted, counted], checks=["char_audit_missing"], services=["discord"])

        columns, lines = found.overview_table()

        # the Corporation with a member list has the Registered row; the other leaves it empty
        self.assertEqual(
            [str(column.label) for column in columns], ["Registered in Auth", "Character Audit", "Discord"]
        )
        cells = {corporation.id: cells for corporation, cells in lines}
        self.assertIsNone(cells[2002][0])
        self.assertEqual([cell.percent for cell in cells[2001]], [100, 100, 100])
        self.assertEqual(cells[2002][2].percent, 0)

    def test_should_have_no_table_without_corporations(self):
        self.assertEqual(report([]).overview_table(), ([], []))


class TestDescribe(MonitorTestCase):
    def test_should_join_the_detail(self):
        self.assertEqual(describe(SCOPES_MISSING), "a, b")

    def test_should_say_when_corporation_data_never_updated(self):
        self.assertEqual(describe({"check": "corp_data_stale", "detail": []}), "never updated")


class TestShorten(MonitorTestCase):
    FIVE = ["a", "b", "c", "d", "e"]

    def test_should_name_two_scopes_and_count_the_rest(self):
        for key in ("char_scopes_missing", "char_director_token_missing"):
            with self.subTest(key):
                self.assertEqual(shorten({"check": key, "detail": self.FIVE}), "a, b and 3 more")

    def test_should_count_a_single_scope_left(self):
        self.assertEqual(shorten({"check": "char_scopes_missing", "detail": ["a", "b", "c"]}), "a, b and 1 more")

    def test_should_keep_two_scopes_whole(self):
        self.assertEqual(shorten(SCOPES_MISSING), "a, b")

    def test_should_keep_a_list_of_sections_whole(self):
        self.assertEqual(shorten({"check": "char_audit_inactive", "detail": self.FIVE}), "a, b, c, d, e")

    def test_should_keep_the_whole_list_for_the_tooltip(self):
        cut, whole = _problems([{"check": "char_scopes_missing", "detail": self.FIVE}, SCOPES_MISSING])

        self.assertEqual((cut.detail, cut.full_detail), ("a, b and 3 more", "a, b, c, d, e"))
        self.assertEqual((whole.detail, whole.full_detail), ("a, b", ""))


class TestMetrics(MonitorTestCase):
    STORED = {
        "seconds": 3.5,
        "phases": {"accounts": 0.5, "characters": 3.0, "gone_in_a_later_release": 1.0},
        "queries": 40,
        "query_seconds": 1.25,
        "corporations": 2,
        "accounts": 5,
        "characters": 9,
        "member_lists": 1,
        "payload_bytes": 30720,
    }

    def metrics(self, stored):
        data = snapshot_data([])
        if stored:
            data["metrics"] = stored
        return Report(store_snapshot(data)).metrics

    def test_should_have_none_for_a_snapshot_from_before_they_were_kept(self):
        self.assertIsNone(self.metrics(None))

    def test_should_label_the_phases_and_skip_unknown_ones(self):
        self.assertEqual(self.metrics(self.STORED)["phases"], [("Reading accounts", 0.5), ("Checking characters", 3.0)])

    def test_should_give_the_size_in_kilobytes(self):
        self.assertEqual(self.metrics(self.STORED)["kilobytes"], 30)


class TestAccounts(MonitorTestCase):
    def test_should_name_each_failed_check_once(self):
        account = account_row(
            1,
            101,
            characters=[
                character_row(101, [SCOPES_MISSING]),
                character_row(102, [AUDIT_MISSING, SCOPES_MISSING]),
            ],
        )
        _, found = report([corporation_row(2001, [account])]).account(1)

        # in check order, not in the order the characters had them
        self.assertEqual([check.key for check in found.keywords], ["char_audit_missing", "char_scopes_missing"])
        self.assertTrue(found.characters[0].is_main)

    def test_should_put_accounts_with_problems_first(self):
        fine = account_row(1, 101)
        broken = account_row(2, 201, characters=[character_row(201, [AUDIT_MISSING])])
        corporation = report([corporation_row(2001, [fine, broken])]).corporation(2001)

        self.assertEqual([account.user_id for account in corporation.accounts_by_problems], [2, 1])
        self.assertEqual([account.user_id for account in corporation.problem_accounts], [2])

    def test_should_sort_by_the_number_of_problems_not_only_by_whether_there_are_any(self):
        one = account_row(1, 101, characters=[character_row(101, [AUDIT_MISSING])])
        three = account_row(
            2, 201, characters=[character_row(201, [AUDIT_MISSING, SCOPES_MISSING]), character_row(202, [AUDIT_MISSING])]
        )
        none = account_row(3, 301)

        corporation = report([corporation_row(2001, [none, one, three])]).corporation(2001)

        self.assertEqual([account.user_id for account in corporation.accounts_by_problems], [2, 1, 3])

    def test_should_sort_equal_problem_counts_by_name(self):
        accounts = [account_row(1, 102), account_row(2, 101)]

        corporation = report([corporation_row(2001, accounts)]).corporation(2001)

        self.assertEqual([account.main_id for account in corporation.accounts_by_problems], [101, 102])

    def test_should_list_the_characters_of_an_account_by_problems_with_the_main_first_among_equals(self):
        characters = [
            character_row(103),
            character_row(102, [AUDIT_MISSING, SCOPES_MISSING]),
            character_row(101),
            character_row(104, [AUDIT_MISSING]),
        ]
        _, found = report([corporation_row(2001, [account_row(1, 101, characters=characters)])]).account(1)

        self.assertEqual([character.id for character in found.listed_characters], [102, 104])
        self.assertEqual([character.id for character in found.problem_free_characters], [101, 103])

    def test_should_rank_corporations_by_their_own_problems_plus_those_of_their_accounts(self):
        broken_account = account_row(
            1, 101, characters=[character_row(101, [AUDIT_MISSING, SCOPES_MISSING], corporation_id=2002)]
        )
        corporations = [
            corporation_row(2001),
            corporation_row(2002, [broken_account]),
            corporation_row(2003, problems=[CORP_TOKEN_MISSING]),
            corporation_row(2004),
        ]

        ranked = report(corporations).corporations_by_problems

        self.assertEqual([corporation.id for corporation in ranked], [2002, 2003, 2001, 2004])

    def test_should_ignore_checks_an_old_snapshot_knows_but_this_release_not(self):
        account = account_row(1, 101, characters=[character_row(101, [{"check": "gone", "detail": []}])])
        _, found = report([corporation_row(2001, [account])]).account(1)

        self.assertFalse(found.has_problems)


class TestCockpit(MonitorTestCase):
    def gauges(self, corporations, **kwargs):
        return {str(gauge.label): (gauge.part, gauge.total, gauge.percent) for gauge in report(corporations, **kwargs).cockpit()}

    def test_should_count_linked_mains_per_service(self):
        corporations = [
            corporation_row(2001, [account_row(1, 101, services={"discord": True}), account_row(2, 201)]),
            corporation_row(2002, [account_row(3, 301, services={"discord": True})]),
        ]

        self.assertEqual(self.gauges(corporations, services=["discord"])["Discord"], (2, 3, 67))

    def test_should_count_complete_characters(self):
        account = account_row(1, 101, characters=[character_row(101), character_row(102, [AUDIT_MISSING])])

        gauges = self.gauges([corporation_row(2001, [account])], checks=["char_audit_missing"])

        self.assertEqual(gauges["Character Audit complete"], (1, 2, 50))

    def test_should_count_working_corporations_per_app(self):
        corporations = [
            corporation_row(2001, problems=[CORP_TOKEN_MISSING]),
            corporation_row(2002, problems=[NO_OWNER]),
            corporation_row(2003),
            corporation_row(2004),
        ]

        gauges = self.gauges(corporations, checks=["corp_token_missing", "structures_no_owner"])

        self.assertEqual(gauges["Corporation Audit working"], (3, 4, 75))
        self.assertEqual(gauges["Structures working"], (3, 4, 75))

    def test_should_count_registered_members_where_the_list_is_known(self):
        corporations = [
            {**corporation_row(2001), "member_count": 4, "unregistered": [{"id": 1, "name": "x"}]},
            {**corporation_row(2002), "member_count": None},
        ]

        self.assertEqual(self.gauges(corporations)["Members registered"], (3, 4, 75))

    def test_should_count_connections_per_service(self):
        corporations = [
            corporation_row(2001, [account_row(1, 101, services={"discord": True, "qq": True}), account_row(2, 201)]),
        ]

        cockpit = report(corporations, services=["discord", "qq"]).cockpit()

        # the Connections tile reads the linked accounts off the service tiles
        self.assertEqual(
            [(gauge.service.key, gauge.part) for gauge in cockpit if gauge.service], [("discord", 1), ("qq", 1)]
        )

    def test_should_give_a_corporation_a_gauge_per_service_over_its_own_mains(self):
        corporations = [
            corporation_row(2001, [account_row(1, 101, services={"discord": True, "qq": False}), account_row(2, 201)]),
            corporation_row(2002, [account_row(3, 301, services={"discord": True, "qq": True})]),
        ]

        gauges = report(corporations, services=["discord", "qq"]).corporation(2001).service_counts

        self.assertEqual(
            [(str(gauge.label), gauge.part, gauge.total, gauge.percent, gauge.service.key) for gauge in gauges],
            [("Discord", 1, 2, 50, "discord"), ("QQ", 0, 2, 0, "qq")],
        )

    def test_should_count_unknown_members_apart_from_the_mains(self):
        strangers = [{"id": n, "name": f"Stranger {n}"} for n in range(3)]
        corporations = [
            {
                **corporation_row(2001, [account_row(1, 101, services={"discord": True}), account_row(2, 201)]),
                "member_count": 6,
                "unregistered": strangers,
            },
            # no member list read: nobody unknown can be named
            corporation_row(2002, [account_row(3, 301, services={"discord": True})]),
        ]
        found = report(corporations, services=["discord"])
        gauges = self.gauges(corporations, services=["discord"])

        # the service shares count the mains only, everywhere
        self.assertEqual(gauges["Discord"], (2, 3, 67))
        self.assertEqual([(row.part, row.total) for row in found.corporation(2001).service_counts], [(1, 2)])
        # the unknown members are the gap of Members registered, of the members whose list was read
        self.assertEqual(gauges["Members registered"][:2], (3, 6))
        self.assertNotIn("Unknown characters", gauges)

    def test_should_open_the_unknown_characters_from_members_registered(self):
        corporations = [{**corporation_row(2001), "member_count": 1, "unregistered": [{"id": 1, "name": "x"}]}]

        gauge = next(gauge for gauge in report(corporations).cockpit() if str(gauge.label) == "Members registered")

        self.assertEqual(gauge.url, reverse("eos_auth_monitor:unknown_characters"))

    def test_should_show_only_gauges_of_checks_that_ran(self):
        self.assertEqual(self.gauges([corporation_row(2001)]), {})

    def test_should_have_no_percentage_without_anything_to_count(self):
        gauges = self.gauges([corporation_row(2001)], services=["discord"])

        self.assertEqual(gauges["Discord"], (0, 0, None))


class TestUnknownCharacters(MonitorTestCase):
    def test_should_list_every_unknown_member_by_corporation_and_name(self):
        corporations = [
            {
                **corporation_row(2002),
                "member_count": 2,
                "unregistered": [{"id": 2, "name": "zed", "in_auth": True}, {"id": 1, "name": "Abe", "in_auth": False}],
            },
            {**corporation_row(2001), "member_count": 1, "unregistered": [{"id": 3, "name": "Mia", "in_auth": False}]},
        ]

        rows = report(corporations).unknown_characters()

        self.assertEqual(
            [(corporation.id, character.name, character.in_auth) for corporation, character in rows],
            [(2001, "Mia", False), (2002, "Abe", False), (2002, "zed", True)],
        )

    def test_should_not_guess_where_an_older_snapshot_did_not_say(self):
        corporations = [{**corporation_row(2001), "member_count": 1, "unregistered": [{"id": 1, "name": "x"}]}]

        (_, character), = report(corporations).unknown_characters()

        self.assertIsNone(character.in_auth)


class TestCharacterCount(MonitorTestCase):
    def characters(self, **fields):
        return report([{**corporation_row(2001), **fields}]).corporation(2001).characters

    def test_should_prefer_the_member_list(self):
        self.assertEqual(self.characters(member_count=279, member_total=290), 279)

    def test_should_fall_back_to_the_count_auth_stores(self):
        self.assertEqual(self.characters(member_count=None, member_total=290), 290)

    def test_should_have_none_when_neither_is_known(self):
        self.assertIsNone(self.characters())


class TestTileRows(MonitorTestCase):
    def rows(self, row, **kwargs):
        corporation = report([row], **kwargs).corporations[0]
        return {str(item.label): (item.part, item.total, item.percent) for item in corporation.rows}

    def test_should_list_each_app_with_its_share(self):
        account = account_row(
            1, 101, characters=[character_row(101), character_row(102, [AUDIT_MISSING])], services={"discord": True}
        )
        row = {**corporation_row(2001, [account], problems=[NO_OWNER]), "member_count": 3, "unregistered": []}

        rows = self.rows(
            row, checks=["char_audit_missing", "corp_token_missing", "structures_no_owner"], services=["discord"]
        )

        self.assertEqual(
            rows,
            {
                "Registered in Auth": (3, 3, 100),
                "Character Audit": (1, 2, 50),
                "Corporation Audit": (None, None, 100),
                "Structures": (None, None, 0),
                "Discord": (1, 1, 100),
            },
        )

    def test_should_keep_the_services_out_of_the_check_rows(self):
        corporation = report([corporation_row(2001, [account_row(1, 101)])], services=["discord"]).corporation(2001)

        self.assertEqual([str(row.label) for row in corporation.rows], ["Discord"])
        self.assertEqual(corporation.check_rows, [])

    def test_should_leave_out_what_did_not_run(self):
        self.assertEqual(self.rows(corporation_row(2001)), {})


MEMBERSHIP = SpyMarker("membership", "Hostile membership", "In a hostile Corporation.")
WALLET = SpyMarker("wallet", "ISK with hostiles", "Wallet entries with hostiles.")
SPY_KINDS = ("membership", "corp_changes", "wallet")


class TestSpyMarkers(MonitorTestCase):
    """eos-spy-network's markers per character: shown where the character counts, never a problem."""

    def found(self, markers=None):
        found = report(
            [
                corporation_row(
                    2001,
                    [
                        account_row(
                            11,
                            1101,
                            [
                                character_row(1101, [AUDIT_MISSING]),
                                character_row(1102),
                                # counts in 2002, where it is
                                character_row(1103, corporation_id=2002),
                            ],
                        )
                    ],
                ),
                corporation_row(2002, [account_row(22, 2201, corporation_id=2002)]),
            ],
            checks=["char_audit_missing"],
        )
        if markers is not None:
            found.add_spy_markers(markers, SPY_KINDS)
        return found

    def test_should_show_nothing_until_added(self):
        found = self.found()

        self.assertFalse(found.spy_shown)
        self.assertFalse(found.corporation(2001).spy_shown)
        self.assertEqual(found.corporation(2001).spy_todos, [])

    def test_should_count_each_character_in_its_own_corporation(self):
        found = self.found({1102: [WALLET], 1103: [MEMBERSHIP, WALLET], 2201: [WALLET]})

        self.assertTrue(found.spy_shown)
        self.assertEqual([character.id for character in found.corporation(2001).spy_characters], [1102])
        self.assertEqual([character.id for character in found.corporation(2002).spy_characters], [1103, 2201])

    def test_should_group_the_todos_by_marker_in_the_apps_order(self):
        corporation = self.found({1103: [WALLET, MEMBERSHIP], 2201: [WALLET]}).corporation(2002)

        self.assertEqual(
            [(todo.group, todo.names) for todo in corporation.spy_todos],
            [("spy_membership", "Char 1103"), ("spy_wallet", "Char 1103, Char 2201")],
        )

    def test_should_add_the_markers_to_the_export_rows(self):
        corporation = self.found({1102: [WALLET]}).corporation(2001)

        self.assertEqual(
            [(row.group, str(row.label), row.name) for row in corporation.todo_rows],
            [("char_audit_missing", "Audit missing", "Char 1101"), ("spy_wallet", "ISK with hostiles", "Char 1102")],
        )

    def test_should_change_no_problem_count(self):
        plain = self.found().corporation(2001)
        marked = self.found({1101: [WALLET], 1102: [WALLET]}).corporation(2001)

        self.assertEqual(marked.problem_count, plain.problem_count)
        self.assertEqual(len(marked.problem_accounts), len(plain.problem_accounts))
        self.assertEqual([todo.check.key for todo in marked.todos], [todo.check.key for todo in plain.todos])

    def test_should_list_a_marked_character_on_the_account_page(self):
        _corporation, account = self.found({1102: [WALLET]}).account(11)

        self.assertEqual([character.id for character in account.listed_characters], [1101, 1102])
        self.assertEqual([character.id for character in account.problem_free_characters], [1103])
        self.assertEqual([character.id for character in account.problem_characters], [1101])

    def test_should_list_problems_first_then_most_markers(self):
        _corporation, account = self.found({1102: [WALLET], 1103: [MEMBERSHIP, WALLET]}).account(11)

        # 1103 before 1102 for its second marker, though the name would put it after
        self.assertEqual([character.id for character in account.listed_characters], [1101, 1103, 1102])


class TestScopeWarnings(MonitorTestCase):
    """Scopes missing below the setting's threshold (3 here) is a warning: shown, counted nowhere."""

    TWO = {"check": "char_scopes_missing", "detail": ["a", "b"]}
    THREE = {"check": "char_scopes_missing", "detail": ["a", "b", "c"]}
    CHECKS = ["char_audit_missing", "char_scopes_missing", "char_director_token_missing"]

    def found(self, threshold=3, director=()):
        data = snapshot_data(
            [
                corporation_row(
                    2001,
                    [
                        account_row(11, 1101, [character_row(1101, [self.TWO]), character_row(1102)]),
                        account_row(12, 1201, [character_row(1201, [self.THREE])]),
                        account_row(13, 1301, [character_row(1301, [self.TWO]), character_row(1302, [AUDIT_MISSING])]),
                        account_row(14, 1401, [character_row(1401, list(director))]),
                    ],
                ),
                corporation_row(
                    2002, [account_row(21, 2101, [character_row(2101, [self.TWO], 2002)], corporation_id=2002)]
                ),
            ],
            checks=self.CHECKS,
        )
        if threshold is not None:
            data["critical_scope_count"] = threshold
        return Report(store_snapshot(data))

    @staticmethod
    def keys(problems):
        return [problem.check.key for problem in problems]

    def test_should_warn_below_the_threshold_and_fail_from_it(self):
        found = self.found()
        warned = found.account(11)[1].characters[0]
        failed = found.account(12)[1].characters[0]

        self.assertEqual((self.keys(warned.problems), self.keys(warned.warnings)), ([], ["char_scopes_missing"]))
        self.assertEqual((self.keys(failed.problems), self.keys(failed.warnings)), (["char_scopes_missing"], []))

    def test_should_fail_every_missing_scope_of_a_snapshot_without_the_threshold(self):
        warned = self.found(threshold=None).account(11)[1].characters[0]

        self.assertEqual((self.keys(warned.problems), warned.warnings), (["char_scopes_missing"], []))

    def test_should_keep_a_director_token_missing_one_scope_a_problem(self):
        found = self.found(director=[{"check": "char_director_token_missing", "detail": ["a"]}])
        character = found.account(14)[1].characters[0]

        self.assertEqual((self.keys(character.problems), character.warnings), (["char_director_token_missing"], []))

    def test_should_count_a_warning_nowhere_on_the_overview(self):
        found = self.found()
        warned_only = found.corporation(2002)

        self.assertFalse(warned_only.has_problems)
        self.assertEqual(warned_only.problem_count, 0)
        self.assertEqual(found.corporation(2001).problem_count, 2)
        # the warned character counts as complete in the Character Audit share, on the tile and in the cockpit
        self.assertEqual(warned_only.check_rows[0].percent, 100)
        audit = next(row for row in found.cockpit() if row.url_name == "eos_auth_monitor:character_audit")
        self.assertEqual((audit.part, audit.total), (5, 7))
        # the smart filter and the Character Audit list read the keywords
        account = found.account(11)[1]
        self.assertEqual(account.keywords, [])
        self.assertEqual([check.key for check in account.warning_keywords], ["char_scopes_missing"])

    def test_should_list_a_warned_account_apart_on_the_corporation_page(self):
        corporation = self.found().corporation(2001)

        self.assertEqual([account.user_id for account in corporation.problem_accounts], [12, 13])
        self.assertEqual([account.user_id for account in corporation.warning_accounts], [11])
        self.assertEqual([account.user_id for account in corporation.problem_free_accounts], [14])
        # problems first, then warnings: 13 before 12 for its warning, 11 before 14
        self.assertEqual([account.user_id for account in corporation.accounts_by_problems], [13, 12, 11, 14])

    def test_should_put_red_cards_before_yellow_ones(self):
        found = self.found()
        found.add_spy_markers({1401: [WALLET]}, SPY_KINDS)

        # 14 has a spy marker alone: red, so before the warned 11
        self.assertEqual([account.user_id for account in found.corporation(2001).card_accounts], [13, 12, 14, 11])

    def test_should_put_directors_then_gm_transactions_first_within_each_colour(self):
        two_problems = [AUDIT_MISSING, {"check": "char_director_token_missing", "detail": []}]
        accounts = [
            # red: 31 has the most problems, 32 a Director, 33 a GM transaction
            account_row(31, 3101, [character_row(3101, two_problems)]),
            account_row(32, 3201, [character_row(3201, [AUDIT_MISSING])]),
            account_row(33, 3301, [character_row(3301, [AUDIT_MISSING])]),
            # yellow (a GM transaction would make it red): 34 has the most warnings, 35 a Director
            account_row(34, 3401, [character_row(3401, [self.TWO]), character_row(3402, [self.TWO])]),
            account_row(35, 3501, [character_row(3501, [self.TWO])]),
        ]
        corporation = {**corporation_row(2001, accounts), "directors": [director_row(3201), director_row(3501)]}
        data = snapshot_data([corporation], checks=self.CHECKS)
        data["critical_scope_count"] = 3
        found = Report(store_snapshot(data))
        found.add_gm_transactions({3301})

        self.assertEqual([account.user_id for account in found.corporation(2001).card_accounts], [32, 33, 31, 35, 34])

    def test_should_list_the_warnings_as_a_to_do_group_of_their_own(self):
        corporation = self.found().corporation(2001)

        self.assertEqual(
            [(todo.group, todo.label, todo.names) for todo in corporation.listed_todos],
            [
                ("char_audit_missing", "Audit missing", "Char 1301"),
                ("char_scopes_missing", "Scopes missing", "Char 1201"),
                ("char_scopes_missing_warning", "Scopes missing (warning)", "Char 1101, Char 1301"),
            ],
        )
        self.assertEqual(
            [(row.group, row.name) for row in corporation.todo_rows if row.group.startswith("char_scopes")],
            [
                ("char_scopes_missing", "Char 1201"),
                ("char_scopes_missing_warning", "Char 1101"),
                ("char_scopes_missing_warning", "Char 1301"),
            ],
        )

    def test_should_list_a_warned_character_on_the_account_page(self):
        account = self.found().account(13)[1]

        # the problem first, then the warning; nothing left without either
        self.assertEqual([character.id for character in account.listed_characters], [1302, 1301])
        self.assertEqual(account.problem_free_characters, [])
