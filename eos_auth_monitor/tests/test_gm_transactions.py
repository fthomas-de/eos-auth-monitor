import re
from unittest import skipUnless
from unittest.mock import patch

from django.apps import apps
from django.urls import reverse
from django.utils import timezone

from eos_auth_monitor.models import Snapshot
from eos_auth_monitor.permissions import BASIC_ACCESS, VIEW_ALL
from eos_auth_monitor.report import Report
from eos_auth_monitor.sources import gm_transactions

from .base import MonitorTestCase, account_row, character_row, corporation_row, make_user, snapshot_data, store_snapshot
from .test_views import ViewTestCase, main_cards

AUDIT_MISSING = {"check": "char_audit_missing", "detail": []}
TAX_INSTALLED = apps.is_installed("eos_tax")
GM_ACCESS = "eos_tax.gm_bots_access"
CEO_ACCESS = "eos_tax.basic_access"


# a main outside the Alliance with an alt in 2002, from 2002's member list
OUTSIDE = {
    "user_id": 99,
    "main_id": 9900,
    "main_name": "Outside main",
    "main_corporation_name": "Corp 5005",
    "characters": [{"id": 9002, "name": "Outside alt"}],
}


def found(character_ids=None, corporation_id=None, other_mains=()):
    """2001 with an account whose alts are in 2002 and outside the Alliance (3001); 2002 with its own account."""
    report = Report(
        store_snapshot(
            snapshot_data(
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
                                    character_row(1103, corporation_id=2002),
                                    character_row(1104, corporation_id=3001),
                                ],
                            )
                        ],
                    ),
                    {
                        **corporation_row(2002, [account_row(22, 2201, corporation_id=2002)]),
                        "other_mains": list(other_mains),
                    },
                ],
                checks=["char_audit_missing"],
            )
        )
    )
    if character_ids is not None:
        report.add_gm_transactions(character_ids, corporation_id)
    return report


class TestReport(MonitorTestCase):
    def test_should_show_nothing_until_added(self):
        report = found()

        self.assertFalse(report.gm_shown)
        self.assertFalse(report.corporation(2001).gm_shown)
        self.assertEqual(report.corporation(2001).gm_accounts, [])

    def test_should_count_the_mains_whose_account_has_one(self):
        report = found({1102, 1103, 2201})

        # 11's whole account counts in 2001 and, by its card there (1103), in 2002 as well
        self.assertEqual([account.user_id for account in report.corporation(2001).gm_accounts], [11])
        self.assertEqual([account.user_id for account in report.corporation(2002).gm_accounts], [11, 22])
        # the cockpit sums the Corporations, as the spy tile does
        self.assertEqual(report.gm_count, 3)

    def test_should_mark_the_main_by_an_alt_in_another_corporation(self):
        report = found({1103})

        self.assertEqual([account.user_id for account in report.corporation(2001).gm_accounts], [11])

    def test_should_mark_a_visiting_main_by_its_main(self):
        # 1103, its alt in 2002, has none; the main in 2001 has
        report = found({1101})

        self.assertEqual([account.user_id for account in report.corporation(2002).gm_accounts], [11])

    def test_should_mark_a_character_outside_the_alliance(self):
        report = found({1104})

        _corporation, account = report.account(11)
        self.assertIn(1104, [character.id for character in account.listed_characters])
        self.assertEqual([account.user_id for account in report.corporation(2001).gm_accounts], [11])

    def test_should_mark_a_main_outside_the_alliance_by_its_alt_or_its_main(self):
        for ids in ({9002}, {9900}):
            with self.subTest(ids=ids):
                corporation = found(ids, other_mains=[OUTSIDE]).corporation(2002)

                self.assertEqual([other.main_name for other in corporation.gm_accounts], ["Outside main"])
                self.assertTrue(corporation.unrated_other_mains[0].has_gm)

    def test_should_keep_a_main_outside_the_alliance_off_another_corporations_page(self):
        # its alt and its main: either would mark it, but not on a page the CEO of 2001 is not shown
        corporation = found({9002, 9900}, corporation_id=2001, other_mains=[OUTSIDE]).corporation(2002)

        self.assertEqual(corporation.gm_accounts, [])
        self.assertFalse(corporation.unrated_other_mains[0].alts[0].gm)

    def test_should_name_the_mains_in_the_todo_and_export(self):
        corporation = found({1103, 2201}).corporation(2002)

        self.assertEqual(corporation.gm_names, "Char 1101, Char 2201")
        self.assertEqual(
            [(row.group, row.name) for row in corporation.todo_rows if row.group == "gm_transactions"],
            [("gm_transactions", "Char 1101"), ("gm_transactions", "Char 2201")],
        )

    def test_should_change_no_problem_count(self):
        plain = found().corporation(2001)
        marked = found({1101, 1102}).corporation(2001)

        self.assertEqual(len(marked.problem_accounts), len(plain.problem_accounts))

    def test_should_list_a_marked_character_on_the_account_page(self):
        _corporation, account = found({1102}).account(11)

        self.assertEqual([c.id for c in account.listed_characters], [1101, 1102])
        self.assertNotIn(1102, [c.id for c in account.problem_free_characters])

    def test_should_show_a_ceo_their_own_corporation_only(self):
        report = found({1103, 2201}, corporation_id=2002)

        self.assertTrue(report.corporation(2002).gm_shown)
        self.assertFalse(report.corporation(2001).gm_shown)
        # the cockpit tile and the overview column count the whole Alliance
        self.assertFalse(report.gm_shown)
        self.assertEqual([account.user_id for account in report.corporation(2002).gm_accounts], [11, 22])
        self.assertEqual(report.corporation(2001).gm_accounts, [])


@skipUnless(TAX_INSTALLED, "eos-tax is not installed")
class TestSource(MonitorTestCase):
    def store(self, transactions):
        from eos_tax.models import GmReport

        GmReport.objects.update_or_create(
            pk=1, defaults={"report": {"transactions": transactions}, "computed_at": timezone.now()}
        )

    def row(self, character_id, entry_id, other):
        return {
            "character_id": character_id,
            "entry_id": entry_id,
            "date": "2026-11-01T00:00:00Z",
            "amount": "100",
            "description": f"GM [16519715] issued transaction between Someone {character_id} and {other}",
        }

    def paths(self):
        """eos-tax's read API, then the fallback for an eos-tax older than it."""
        yield "api"
        with patch.object(gm_transactions, "_api", return_value=None):
            yield "page"

    def test_should_take_only_transactions_against_gm_x(self):
        self.store([self.row(9001, 1, "GM X"), self.row(9002, 2, "EVE Central Bank")])

        for path in self.paths():
            with self.subTest(path):
                self.assertEqual(gm_transactions.character_ids(), {9001})

    def test_should_find_nothing_before_the_first_run(self):
        for path in self.paths():
            with self.subTest(path):
                self.assertEqual(gm_transactions.character_ids(), set())

    def test_should_need_one_of_the_tabs_permissions(self):
        self.assertTrue(gm_transactions.can_view(make_user("gm", GM_ACCESS)))
        self.assertTrue(gm_transactions.can_view(make_user("taxadmin", "eos_tax.admin_view")))
        self.assertFalse(gm_transactions.can_view(make_user("member", "eos_tax.basic_access")))

    def test_should_show_nothing_without_the_app(self):
        with patch.object(gm_transactions, "is_installed", return_value=False):
            self.assertFalse(gm_transactions.can_view(make_user("gm", GM_ACCESS)))
            self.assertIsNone(gm_transactions.ceo_corporation_id(make_user("ceo", CEO_ACCESS)))
            self.assertEqual(gm_transactions.character_ids(), set())

    def test_should_give_eos_taxs_ceo_role_the_own_corporation(self):
        self.assertEqual(gm_transactions.ceo_corporation_id(make_user("ceo", CEO_ACCESS, corporation_id=2002)), 2002)
        # the full view wins; no role, no Corporation
        self.assertIsNone(gm_transactions.ceo_corporation_id(make_user("gm", GM_ACCESS, CEO_ACCESS)))
        self.assertIsNone(gm_transactions.ceo_corporation_id(make_user("member", BASIC_ACCESS)))

    def test_should_give_no_ceo_view_with_an_eos_tax_that_cannot_filter(self):
        ceo = make_user("ceo", CEO_ACCESS, corporation_id=2002)
        with patch("eos_tax.db.gm_transactions.get_gm_page", lambda stored: {"rows": []}):
            with patch.object(gm_transactions, "_api", return_value=None):
                self.assertIsNone(gm_transactions.ceo_corporation_id(ceo))
            # the read API filters by Corporation from its first release on
            self.assertEqual(gm_transactions.ceo_corporation_id(ceo), 2002)

    def test_should_ask_the_api_for_the_ceos_characters(self):
        with patch("eos_tax.api.gm_x_character_ids", return_value={9001}) as api:
            self.assertEqual(gm_transactions.character_ids(2002), {9001})

        self.assertEqual(api.call_args.kwargs, {"corporation_id": 2002})

    def test_should_ask_an_eos_tax_without_the_api_for_the_ceos_rows(self):
        self.store([self.row(9001, 1, "GM X")])
        with (
            patch.object(gm_transactions, "_api", return_value=None),
            patch("eos_tax.db.gm_transactions.get_gm_page", return_value={"rows": []}) as page,
        ):
            gm_transactions.character_ids(2002)

        self.assertEqual(page.call_args.kwargs, {"corporation_id": 2002})

    def test_should_fall_back_without_the_api(self):
        import eos_tax

        api = gm_transactions._api()
        self.assertIsNotNone(api)
        # an imported module stays reachable as the package's attribute
        del eos_tax.api
        try:
            with patch.dict("sys.modules", {"eos_tax.api": None}):
                self.assertIsNone(gm_transactions._api())
        finally:
            eos_tax.api = api


@skipUnless(TAX_INSTALLED, "eos-tax is not installed")
class TestViews(ViewTestCase):
    """The reader is a stand-in: 1102 (an alt of 2001's account, in 2002) and 2201 have GM transactions."""

    def setUp(self):
        super().setUp()
        snapshot = Snapshot.objects.get()
        snapshot.data["corporations"][0]["accounts"][0]["characters"].append(character_row(1102, corporation_id=2002))
        snapshot.save()
        reader = patch.object(gm_transactions, "character_ids", return_value={1102, 2201})
        self.reader = reader.start()
        self.addCleanup(reader.stop)
        self.gm_leader = make_user("gmleader", VIEW_ALL, GM_ACCESS, corporation_id=2001)
        self.gm_ceo = make_user("gmceo", BASIC_ACCESS, GM_ACCESS, corporation_id=2002)
        self.gm_page = reverse("eos_tax:gm_transactions")

    def test_should_show_the_cockpit_tile_with_the_alliance_count(self):
        content = self.get(self.gm_leader, "index").content.decode()
        tile = content[content.index("eos-auth-monitor-gm-tile"):content.index("eos-auth-monitor-view-pane")]

        # the sum of the Corporations: 11 in 2001 and, by 1102, in 2002; 22 in 2002
        self.assertRegex(tile, r'<div class="fs-3 fw-bold" style="color: var\(--bs-pink\)">3</div>')
        self.assertIn(f'href="{self.gm_page}"', tile)

    def test_should_add_the_column_to_the_overview_table(self):
        content = self.get(self.gm_leader, "index").content.decode()
        table = content[content.index("eos-auth-monitor-overview-table"):]

        self.assertIn("</i> GM</th>", table)
        counts = re.findall(r'<td data-order="(\d+)" class="[^"]*eos-auth-monitor-gm-count[^>]*>(\d+)</td>', table)
        # no link: the cockpit tile above opens eos-tax
        self.assertEqual(sorted(counts), [("1", "1"), ("2", "2")])
        self.assertNotIn(self.gm_page, table[:table.index("</table>")])

    def gm_rows(self, user):
        content = self.get(user, "index").content.decode()
        tiles = content[content.index('view-pane="tiles"'):content.index('view-pane="table"')]
        return sorted(re.findall(r'eos-auth-monitor-gm-row"[^>]*>\s*<span>.*?</span>\s*(<span[^>]*>\d+)</span>', tiles))

    def test_should_add_the_row_to_the_overview_tiles(self):
        pink = '<span class="fw-semibold" style="color: var(--bs-pink)">'
        # the table's numbers: 2001's account by 1101's alt 1102; 2002 by that alt and by 2201
        self.assertEqual(self.gm_rows(self.gm_leader), [pink + "1", pink + "2"])

        self.reader.return_value = {2201}
        self.assertIn('<span class="fw-semibold text-success">0', self.gm_rows(self.gm_leader))
        self.assertNotContains(self.get(self.leader, "index"), "eos-auth-monitor-gm-row")

    def test_should_leave_the_transactions_out_when_eos_tax_fails(self):
        self.reader.side_effect = RuntimeError("eos-tax broke")
        for page, args in (("index", ()), ("corporation", (2002,)), ("account", (11,))):
            with self.subTest(page), self.assertLogs("extensions.eos_auth_monitor.views", "ERROR"):
                response = self.get(self.gm_leader, page, *args)

                self.assertContains(response, "eos-tax could not be read")
                self.assertNotContains(response, "eos-auth-monitor-gm-")
                self.assertNotContains(response, self.gm_page)

    def test_should_hide_everything_without_the_permission(self):
        for page, args in (("index", ()), ("corporation", (2002,)), ("account", (11,))):
            with self.subTest(page):
                response = self.get(self.leader, page, *args)
                self.assertNotContains(response, "GM transactions")
                self.assertNotContains(response, self.gm_page)

    def test_should_show_the_corporation_tile(self):
        content = self.get(self.gm_ceo, "corporation", 2002).content.decode()
        tile = content[content.index("eos-auth-monitor-gm-tile"):content.index("eos-auth-monitor-todos")]

        self.assertIn('style="color: var(--bs-pink)">2</div>', tile)
        self.assertIn(f'href="{self.gm_page}"', tile)

    def test_should_show_a_clean_corporation_with_a_green_zero(self):
        self.reader.return_value = {2201}
        content = self.get(self.gm_leader, "corporation", 2001).content.decode()

        self.assertRegex(content, r'eos-auth-monitor-gm-tile[\s\S]*?<div class="fs-3 fw-bold text-success">0</div>')
        self.assertNotIn("eos-auth-monitor-gm-todo", content)

    def test_should_list_the_mains_in_a_pink_todo_linked_to_their_pages(self):
        content = self.get(self.gm_leader, "corporation", 2002).content.decode()
        todo = content[content.index("eos-auth-monitor-gm-todo"):content.index("Mains of this Corporation")]

        self.assertIn('style="background-color: var(--bs-pink)"', todo)
        self.assertIn('data-eos-auth-monitor-copy="Char 1101, Char 2201"', todo)
        self.assertIn(f'href="{reverse("eos_auth_monitor:account", args=[11])}">Char 1101</a>', todo)
        self.assertIn(f'href="{reverse("eos_auth_monitor:account", args=[22])}">Char 2201</a>', todo)

    def test_should_tag_the_main_cards(self):
        cards = main_cards(self.get(self.gm_leader, "corporation", 2002).content.decode())

        # 2201's card is red by its problem; 1102 brings its visiting main a red card of its own
        for name in ("Char 2201", "Char 1101"):
            self.assertIn("eos-auth-monitor-gm-tag", cards[name])
            self.assertTrue(cards[name].startswith('border-danger"'))

    def test_should_export_the_group_only_for_its_viewers(self):
        url = reverse("eos_auth_monitor:corporation_export", args=[2002])
        self.client.force_login(self.gm_leader)
        response = self.client.get(url, {"group": "gm_transactions"})
        self.assertEqual(response.content.decode("utf-8-sig").split(), ["Name", "Char", "1101", "Char", "2201"])

        self.client.force_login(self.leader)
        self.assertEqual(self.client.get(url, {"group": "gm_transactions"}).status_code, 404)

    def test_should_mark_the_character_on_the_account_page_with_a_link(self):
        content = self.get(self.gm_leader, "account", 11).content.decode()
        table = content[content.index("<tbody>"):content.index("</tbody>")]

        # 1102 has no problem of its own: the GM transaction brings it into the table
        self.assertIn("Char 1102", table)
        self.assertIn("eos-auth-monitor-gm-marker", table)
        # eos-tax opens its page searched for the main's name, as a phrase
        self.assertIn(f'href="{self.gm_page}?search=%22Char%201101%22"', table)

    def test_should_show_eos_taxs_ceo_the_own_corporation(self):
        ceo = make_user("taxceo", BASIC_ACCESS, CEO_ACCESS, corporation_id=2002)
        content = self.get(ceo, "corporation", 2002).content.decode()

        self.reader.assert_called_with(2002)
        tile = content[content.index("eos-auth-monitor-gm-tile"):content.index("eos-auth-monitor-todos")]
        self.assertIn('style="color: var(--bs-pink)">2</div>', tile)
        self.assertIn(f'href="{self.gm_page}"', tile)
        self.assertIn("eos-auth-monitor-gm-todo", content)

    def test_should_show_eos_taxs_ceo_nothing_beyond_the_own_corporation(self):
        ceo = make_user("taxceoleader", VIEW_ALL, CEO_ACCESS, corporation_id=2002)

        for page, args in (("index", ()), ("corporation", (2001,))):
            with self.subTest(page):
                self.assertNotContains(self.get(ceo, page, *args), "eos-auth-monitor-gm-")

    def test_should_show_eos_taxs_ceo_nothing_on_another_corporation_page(self):
        # what eos-tax shows 2001's CEO includes 1102, an alt of 2001's account that counts in 2002
        ceo = make_user("taxceoelsewhere", VIEW_ALL, CEO_ACCESS, corporation_id=2001)

        self.assertNotContains(self.get(ceo, "corporation", 2002), "eos-auth-monitor-gm-")
        url = reverse("eos_auth_monitor:corporation_export", args=[2002])
        self.assertEqual(self.client.get(url, {"group": "gm_transactions"}).status_code, 404)
        # the account page of 2001's main keeps the alt's marker, as eos-tax's own page does
        self.assertContains(self.get(ceo, "account", 11), "eos-auth-monitor-gm-marker")

    def test_should_mark_the_main_by_its_alt_in_another_corporation(self):
        content = self.get(self.gm_leader, "corporation", 2001).content.decode()

        tile = content[content.index("eos-auth-monitor-gm-tile"):content.index("eos-auth-monitor-todos")]
        self.assertIn('style="color: var(--bs-pink)">1</div>', tile)
        self.assertIn("eos-auth-monitor-gm-todo", content)
        card = main_cards(content)["Char 1101"]
        self.assertIn("eos-auth-monitor-gm-tag", card)
        self.assertTrue(card.startswith('border-danger"'))

    def outside_main(self):
        snapshot = Snapshot.objects.get()
        row = next(row for row in snapshot.data["corporations"] if row["id"] == 2002)
        row["other_mains"] = [OUTSIDE]
        snapshot.save()
        # its alt in 2002 and its main outside
        self.reader.return_value = {9002, 9900}

    def test_should_mark_a_main_outside_the_alliance(self):
        self.outside_main()
        content = self.get(self.gm_leader, "corporation", 2002).content.decode()

        section = content[content.index("eos-auth-monitor-other-mains"):]
        card = section[section.rindex('<div class="card h-100', 0, section.index("Outside main")):]
        card = card.split('<div class="col">')[0]
        self.assertTrue(card.startswith('<div class="card h-100 border-danger">'))
        self.assertIn("eos-auth-monitor-gm-tag", card)
        # the to-do names the main without a link: there is no account page for it
        todo = content[content.index("eos-auth-monitor-gm-todo"):content.index("Mains of this Corporation")]
        self.assertIn("Outside main", todo)
        self.assertNotIn(reverse("eos_auth_monitor:account", args=[99]), content)
        tile = content[content.index("eos-auth-monitor-gm-tile"):content.index("eos-auth-monitor-todos")]
        self.assertIn('style="color: var(--bs-pink)">1</div>', tile)

        url = reverse("eos_auth_monitor:corporation_export", args=[2002])
        response = self.client.get(url, {"group": "gm_transactions"})
        self.assertEqual(response.content.decode("utf-8-sig").split(), ["Name", "Outside", "main"])

    def test_should_show_a_main_outside_the_alliance_only_to_its_viewers(self):
        self.outside_main()
        ceo_elsewhere = make_user("taxceooutside", VIEW_ALL, CEO_ACCESS, corporation_id=2001)

        for user in (self.leader, ceo_elsewhere):
            with self.subTest(user.username):
                response = self.get(user, "corporation", 2002)
                self.assertContains(response, "Outside main")
                self.assertNotContains(response, "eos-auth-monitor-gm-")
