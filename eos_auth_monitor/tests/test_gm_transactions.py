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
from .test_views import ViewTestCase

AUDIT_MISSING = {"check": "char_audit_missing", "detail": []}
TAX_INSTALLED = apps.is_installed("eos_tax")
GM_ACCESS = "eos_tax.gm_bots_access"


def found(character_ids=None):
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
                    corporation_row(2002, [account_row(22, 2201, corporation_id=2002)]),
                ],
                checks=["char_audit_missing"],
            )
        )
    )
    if character_ids is not None:
        report.add_gm_transactions(character_ids)
    return report


class TestReport(MonitorTestCase):
    def test_should_show_nothing_until_added(self):
        report = found()

        self.assertFalse(report.gm_shown)
        self.assertFalse(report.corporation(2001).gm_shown)
        self.assertEqual(report.corporation(2001).gm_accounts, [])

    def test_should_count_each_character_in_its_own_corporation(self):
        report = found({1102, 1103, 2201})

        self.assertEqual([c.id for c in report.corporation(2001).gm_characters], [1102])
        self.assertEqual(sorted(c.id for c in report.corporation(2002).gm_characters), [1103, 2201])
        self.assertEqual(len(report.gm_characters), 3)

    def test_should_skip_a_character_outside_the_alliance(self):
        report = found({1104})

        self.assertEqual(report.gm_characters, [])
        self.assertEqual(report.corporation(2001).gm_accounts, [])

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

        self.assertEqual(marked.problem_count, plain.problem_count)
        self.assertEqual(len(marked.problem_accounts), len(plain.problem_accounts))

    def test_should_list_a_marked_character_on_the_account_page(self):
        _corporation, account = found({1102}).account(11)

        self.assertEqual([c.id for c in account.listed_characters], [1101, 1102])
        self.assertNotIn(1102, [c.id for c in account.problem_free_characters])


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

    def test_should_take_only_transactions_against_gm_x(self):
        self.store([self.row(9001, 1, "GM X"), self.row(9002, 2, "EVE Central Bank")])

        self.assertEqual(gm_transactions.character_ids(), {9001})

    def test_should_find_nothing_before_the_first_run(self):
        self.assertEqual(gm_transactions.character_ids(), set())

    def test_should_need_one_of_the_tabs_permissions(self):
        self.assertTrue(gm_transactions.can_view(make_user("gm", GM_ACCESS)))
        self.assertTrue(gm_transactions.can_view(make_user("taxadmin", "eos_tax.admin_view")))
        self.assertFalse(gm_transactions.can_view(make_user("member", "eos_tax.basic_access")))

    def test_should_show_nothing_without_the_app(self):
        with patch.object(gm_transactions, "is_installed", return_value=False):
            self.assertFalse(gm_transactions.can_view(make_user("gm", GM_ACCESS)))
            self.assertEqual(gm_transactions.character_ids(), set())


@skipUnless(TAX_INSTALLED, "eos-tax is not installed")
class TestViews(ViewTestCase):
    """The reader is a stand-in: 1102 (an alt of 2001's account, in 2002) and 2201 have GM transactions."""

    def setUp(self):
        super().setUp()
        snapshot = Snapshot.objects.get()
        snapshot.data["corporations"][0]["accounts"][0]["characters"].append(character_row(1102, corporation_id=2002))
        snapshot.save()
        reader = patch.object(gm_transactions, "character_ids", return_value={1102, 2201})
        reader.start()
        self.addCleanup(reader.stop)
        self.gm_leader = make_user("gmleader", VIEW_ALL, GM_ACCESS, corporation_id=2001)
        self.gm_ceo = make_user("gmceo", BASIC_ACCESS, GM_ACCESS, corporation_id=2002)
        self.gm_page = reverse("eos_tax:gm_transactions")

    def test_should_show_the_cockpit_tile_with_the_alliance_count(self):
        content = self.get(self.gm_leader, "index").content.decode()
        tile = content[content.index("eos-auth-monitor-gm-tile"):content.index("eos-auth-monitor-view-pane")]

        self.assertRegex(tile, r'<div class="fs-3 fw-bold" style="color: var\(--bs-pink\)">2</div>')
        self.assertIn(f'href="{self.gm_page}"', tile)

    def test_should_add_the_column_to_the_overview_table(self):
        content = self.get(self.gm_leader, "index").content.decode()
        table = content[content.index("eos-auth-monitor-overview-table"):]

        self.assertIn("</i> GM</th>", table)
        counts = re.findall(r'<td data-order="(\d+)" class="[^"]*eos-auth-monitor-gm-count[^>]*>(\d+)</td>', table)
        # no link: the cockpit tile above opens eos-tax
        self.assertEqual(sorted(counts), [("0", "0"), ("2", "2")])
        self.assertNotIn(self.gm_page, table[:table.index("</table>")])

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
        self.assertIn(f'href="{self.gm_page}"', table)
