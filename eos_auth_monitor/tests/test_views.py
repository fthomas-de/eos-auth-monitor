import csv
import io
import re
from unittest import skipUnless
from unittest.mock import patch

from kombu.exceptions import OperationalError

from django.apps import apps
from django.test import RequestFactory
from django.urls import reverse

import eos_auth_monitor
from eos_auth_monitor import progress
from eos_auth_monitor.auth_hooks import AuthMonitorMenuItem
from eos_auth_monitor.checks import is_app_installed
from eos_auth_monitor.forms import MonitorConfigurationForm
from eos_auth_monitor.models import MonitorConfiguration, Snapshot
from eos_auth_monitor.permissions import APP_PERMISSIONS, BASIC_ACCESS, MANAGE_SETTINGS, VIEW_ALL, VIEW_OWN

from .base import (
    ALLIANCE_ID,
    MonitorTestCase,
    account_row,
    character_row,
    configure,
    corporation_row,
    make_alliance,
    make_user,
    snapshot_data,
    store_snapshot,
)

AUDIT_MISSING = {"check": "char_audit_missing", "detail": []}


class TestMenu(MonitorTestCase):
    def render(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return AuthMonitorMenuItem().render(request)

    def test_should_hide_the_menu_entry_without_a_permission(self):
        self.assertEqual(self.render(make_user("nobody")), "")

    def test_should_show_the_menu_entry_with_any_one_permission(self):
        for perm in APP_PERMISSIONS:
            with self.subTest(perm):
                user = make_user(perm.split(".")[1], perm)

                self.assertIn(f'href="{reverse("eos_auth_monitor:index")}"', self.render(user))


class ViewTestCase(MonitorTestCase):
    """Two Corporations of the Alliance, one account each; 2002's has a problem."""

    def setUp(self):
        super().setUp()
        configure()
        self.ceo = make_user("ceo", BASIC_ACCESS, corporation_id=2001)
        self.leader = make_user("leader", VIEW_ALL, corporation_id=2001)
        self.admin = make_user("admin", MANAGE_SETTINGS, corporation_id=2001)
        store_snapshot(
            snapshot_data(
                [
                    corporation_row(2001, [account_row(11, 1101, services={"discord": True})]),
                    corporation_row(
                        2002,
                        [account_row(22, 2201, [character_row(2201, [AUDIT_MISSING], corporation_id=2002)], {})],
                    ),
                ],
                checks=["char_audit_missing"],
                services=["discord"],
            )
        )

    def get(self, user, name, *args):
        self.client.force_login(user)
        return self.client.get(reverse(f"eos_auth_monitor:{name}", args=args))


class TestAccess(ViewTestCase):
    def test_should_send_anonymous_users_to_the_login(self):
        response = self.client.get(reverse("eos_auth_monitor:index"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_should_keep_users_without_permission_out(self):
        nobody = make_user("nobody")
        pages = [
            ("index",),
            ("corporation", 2001),
            ("account", 11),
            ("corporation_service", 2001, "discord"),
            ("service", "discord"),
            ("settings",),
        ]
        for name, *args in pages:
            with self.subTest(name):
                self.assertEqual(self.get(nobody, name, *args).status_code, 302)

    def test_should_send_a_ceo_to_the_own_corporation(self):
        response = self.get(self.ceo, "index")

        self.assertRedirects(response, reverse("eos_auth_monitor:corporation", args=[2001]))

    def test_should_send_an_admin_to_the_settings(self):
        self.assertRedirects(self.get(self.admin, "index"), reverse("eos_auth_monitor:settings"))

    def test_should_show_a_ceo_only_the_own_corporation(self):
        self.assertEqual(self.get(self.ceo, "corporation", 2001).status_code, 200)
        self.assertEqual(self.get(self.ceo, "account", 11).status_code, 200)
        self.assertEqual(self.get(self.ceo, "corporation_service", 2001, "discord").status_code, 200)

        self.assertEqual(self.get(self.ceo, "corporation", 2002).status_code, 403)
        self.assertEqual(self.get(self.ceo, "account", 22).status_code, 403)
        self.assertEqual(self.get(self.ceo, "corporation_service", 2002, "discord").status_code, 403)

    def test_should_keep_a_ceo_out_of_the_alliance_wide_pages(self):
        self.assertEqual(self.get(self.ceo, "service", "discord").status_code, 302)
        self.assertEqual(self.get(self.ceo, "settings").status_code, 302)

    def test_should_show_leadership_every_corporation(self):
        for name, *args in [("index",), ("corporation", 2002), ("account", 22), ("service", "discord")]:
            with self.subTest(name):
                self.assertEqual(self.get(self.leader, name, *args).status_code, 200)

    def test_should_keep_leadership_out_of_the_settings(self):
        self.assertEqual(self.get(self.leader, "settings").status_code, 302)

    def test_should_not_find_what_the_snapshot_does_not_have(self):
        self.assertEqual(self.get(self.leader, "account", 99).status_code, 404)
        self.assertEqual(self.get(self.leader, "service", "mumble").status_code, 404)
        self.assertEqual(self.get(self.leader, "corporation_service", 2001, "mumble").status_code, 404)


class TestPages(ViewTestCase):
    def test_should_use_alliance_auths_page_header(self):
        response = self.get(self.leader, "index")

        self.assertContains(response, 'class="aa-page-header')
        self.assertContains(response, eos_auth_monitor.__version__)

    def test_should_put_the_version_beside_the_name(self):
        response = self.get(self.leader, "index")

        self.assertContains(response, f"Auth Monitor ({eos_auth_monitor.__version__})")

    def test_should_say_which_page_this_is_under_the_name(self):
        pages = [
            ("Corporation overview", "index"),
            ("Corporation details", "corporation", 2001),
            ("Main details", "account", 22),
            ("Discord", "corporation_service", 2002, "discord"),
            ("Discord", "service", "discord"),
        ]
        for location, name, *args in pages:
            with self.subTest(name):
                self.assertContains(
                    self.get(self.leader, name, *args), f'<small class="text-muted">{location}</small>', html=False
                )
        self.assertContains(self.get(self.admin, "settings"), '<small class="text-muted">Settings</small>')

    def test_should_show_the_cockpit_and_one_tile_per_corporation(self):
        response = self.get(self.leader, "index")

        url = reverse("eos_auth_monitor:service", args=["discord"])
        self.assertContains(response, f'href="{url}" class="stretched-link" aria-label="Discord"')
        self.assertContains(response, "50&nbsp;%")
        for corporation_id in (2001, 2002):
            self.assertContains(response, reverse("eos_auth_monitor:corporation", args=[corporation_id]))

    def test_should_link_the_audit_gauges_to_their_lists(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["checks"] = ["char_audit_missing", "corp_token_missing", "structures_no_owner"]
        snapshot.save()

        response = self.get(self.leader, "index")

        targets = {
            "Character Audit complete": reverse("eos_auth_monitor:character_audit"),
            "Corporation Audit working": reverse("eos_auth_monitor:directors", args=["corptools_corporations"]),
            "Structures working": reverse("eos_auth_monitor:directors", args=["structures"]),
        }
        for label, url in targets.items():
            with self.subTest(label):
                self.assertContains(response, f'href="{url}" class="stretched-link" aria-label="{label}"')
        self.assertNotContains(response, reverse("services:services"))

    def test_should_leave_the_members_registered_gauge_unlinked(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["corporations"][0].update(member_count=1, unregistered=[])
        snapshot.save()

        response = self.get(self.leader, "index")

        self.assertContains(response, "Members registered")
        self.assertNotContains(response, 'aria-label="Members registered"')

    def test_should_mark_a_corporation_without_a_director_token(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["corporations"][0]["no_director_token"] = True
        snapshot.save()

        overview = self.get(self.leader, "index")
        page = self.get(self.leader, "corporation", 2001)
        other = self.get(self.leader, "corporation", 2002)

        # a quiet mark with the explanation as tooltip: on the tile and in the table line
        self.assertContains(overview, "eos-auth-monitor-no-director", count=2)
        self.assertContains(page, "eos-auth-monitor-no-director", count=1)
        self.assertContains(page, 'title="No Director token: No Director of this Corporation')
        self.assertNotContains(overview, 'badge text-bg-info text-wrap">No Director token')
        self.assertNotContains(other, "No Director token")

    def test_should_not_mark_a_corporation_by_default(self):
        self.assertNotContains(self.get(self.leader, "index"), "No Director token")

    def test_should_tag_a_main_whose_director_has_no_corporation_token(self):
        snapshot = Snapshot.objects.get()
        problem = {"check": "char_director_token_missing", "detail": ["esi-wallet.read_corporation_wallets.v1"]}
        snapshot.data["corporations"][0]["accounts"][0]["characters"][0]["problems"] = [problem]
        snapshot.data["checks"] = ["char_director_token_missing"]
        snapshot.save()

        response = self.get(self.leader, "corporation", 2001)

        self.assertContains(response, "Director token missing")
        self.assertContains(response, 'badge text-bg-danger text-wrap">Director token missing')

    def test_should_show_a_tile_per_service_on_the_corporation_page(self):
        response = self.get(self.leader, "corporation", 2001)

        url = reverse("eos_auth_monitor:corporation_service", args=[2001, "discord"])
        self.assertContains(response, f'href="{url}" class="stretched-link" aria-label="Discord"')
        self.assertContains(response, "1 of 1")

    def test_should_show_each_service_once_on_the_corporation_page(self):
        response = self.get(self.leader, "corporation", 2001)

        # the header's buttons would be a second link to the same list
        url = reverse("eos_auth_monitor:corporation_service", args=[2001, "discord"])
        self.assertContains(response, f'href="{url}"', count=1)

    def test_should_keep_the_service_buttons_on_the_other_pages_of_a_corporation(self):
        response = self.get(self.leader, "corporation_service", 2001, "discord")

        url = reverse("eos_auth_monitor:corporation_service", args=[2001, "discord"])
        self.assertContains(response, f'href="{url}" class="btn btn-sm btn-outline-secondary')

    def test_should_count_only_the_mains_of_the_corporation_in_its_tile(self):
        response = self.get(self.leader, "corporation", 2002)

        self.assertContains(response, "0 of 1")

    def test_should_show_no_service_tiles_when_no_service_is_in_use(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["services"] = []
        snapshot.save()

        response = self.get(self.leader, "corporation", 2001)

        self.assertNotContains(response, reverse("eos_auth_monitor:corporation_service", args=[2001, "discord"]))

    def test_should_name_the_problems_of_a_main(self):
        response = self.get(self.leader, "corporation", 2002)

        self.assertContains(response, reverse("eos_auth_monitor:account", args=[22]))
        self.assertContains(response, "Audit missing")

    def test_should_show_every_character_of_an_account(self):
        response = self.get(self.leader, "account", 22)

        self.assertContains(response, "Char 2201")
        self.assertContains(response, "The character has no corptools Character Audit.")

    def test_should_show_a_green_tile_for_a_linked_service_on_the_account_page(self):
        response = self.get(self.leader, "account", 11)

        self.assertContains(response, 'card h-100 text-center border-success')
        self.assertNotContains(response, 'card h-100 text-center border-danger')

    def test_should_show_a_red_tile_for_a_service_that_is_not_linked(self):
        response = self.get(self.leader, "account", 22)

        self.assertContains(response, 'card h-100 text-center border-danger')
        self.assertNotContains(response, 'card h-100 text-center border-success')
        self.assertContains(response, "not linked")

    def test_should_link_the_account_tile_to_the_corporations_list_not_the_alliance_wide_one(self):
        response = self.get(self.leader, "account", 22)

        url = reverse("eos_auth_monitor:corporation_service", args=[2002, "discord"])
        self.assertContains(response, f'href="{url}" class="stretched-link" aria-label="Discord"')
        # once: the header's own button to the same list would be a duplicate
        self.assertContains(response, f'href="{url}"', count=1)
        self.assertNotContains(response, reverse("eos_auth_monitor:service", args=["discord"]))

    def test_should_show_how_many_characters_each_corporation_has(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["corporations"][0]["member_total"] = 290
        snapshot.save()

        response = self.get(self.leader, "index")

        self.assertContains(response, "Characters")
        self.assertContains(response, "<span>290</span>", html=True)

    def test_should_not_show_a_character_count_where_it_is_not_known(self):
        # the tile's row; the table has the column in any case, with "-" where the count is missing
        tile_row = '<span><i class="fas fa-users fa-fw"></i> Characters</span>'
        self.assertNotContains(self.get(self.leader, "index"), tile_row)

    def test_should_offer_a_filter_for_the_corporation_tiles(self):
        response = self.get(self.leader, "index")

        self.assertContains(response, 'data-eos-auth-monitor-filter=".eos-auth-monitor-corporation"')
        self.assertRegex(response.content.decode(), r"eos_auth_monitor/js/filter[^\"]*\.js")
        # name and ticker are what the filter searches
        self.assertContains(response, 'data-eos-auth-monitor-filter-text="Corp 2002 C2002"')
        self.assertContains(response, 'data-eos-auth-monitor-filter-text="Corp 2001 C2001"')

    def test_should_have_no_filter_without_corporations(self):
        store_snapshot(snapshot_data([]))

        response = self.get(self.leader, "index")

        self.assertNotContains(response, "data-eos-auth-monitor-filter=")

    def test_should_put_the_corporation_with_the_most_problems_first_on_the_overview(self):
        response = self.get(self.leader, "index")
        content = response.content.decode()

        # 2002 has the account with a problem, 2001 none
        first = reverse("eos_auth_monitor:corporation", args=[2002])
        second = reverse("eos_auth_monitor:corporation", args=[2001])
        self.assertLess(content.index(f'href="{first}" class="stretched-link'), content.index(f'href="{second}" class="stretched-link'))

    def test_should_put_the_mains_with_the_most_problems_first_on_the_alliance_wide_service_list(self):
        response = self.get(self.leader, "service", "discord")

        # Char 2201 (Corp 2002) has a problem, Char 1101 (Corp 2001) none
        content = response.content.decode()
        self.assertLess(content.index("Char 2201"), content.index("Char 1101"))

    def test_should_list_only_the_mains_in_the_service_list_of_a_corporation(self):
        snapshot = Snapshot.objects.get()
        alt = character_row(2202, [AUDIT_MISSING], corporation_id=2002)
        snapshot.data["corporations"][1]["accounts"][0]["characters"].append(alt)
        snapshot.save()

        response = self.get(self.leader, "corporation_service", 2002, "discord")

        self.assertContains(response, reverse("eos_auth_monitor:account", args=[22]), count=1)
        self.assertContains(response, "Char 2201")
        self.assertNotContains(response, "Char 2202")
        self.assertContains(response, "not linked")

    def test_should_show_no_problems_in_the_service_list_of_a_corporation(self):
        response = self.get(self.leader, "corporation_service", 2002, "discord")

        self.assertNotContains(response, "eos-auth-monitor-problem")
        self.assertNotContains(response, "text-bg-danger")
        self.assertNotContains(response, "<th>Problems</th>")

    def test_should_count_connections_across_the_alliance(self):
        response = self.get(self.leader, "index")

        self.assertContains(response, "Connections")

    def test_should_make_the_tables_sortable(self):
        pages = [("account", 22), ("corporation_service", 2002, "discord"), ("service", "discord"), ("index",)]
        for name, *args in pages:
            with self.subTest(name):
                self.assertContains(self.get(self.leader, name, *args), "eos-auth-monitor-sortable")

    def test_should_list_every_member_of_a_corporation(self):
        from eos_auth_monitor.models import Snapshot

        snapshot = Snapshot.objects.get(pk=1)
        row = snapshot.data["corporations"][0]
        row["member_count"] = 3
        row["unregistered"] = [{"id": 7777, "name": "Stranger"}]
        row["other_mains"] = [
            {
                "user_id": 99,
                "main_id": 9900,
                "main_name": "Visitor main",
                "main_corporation_name": "Corp 5005",
                "characters": [{"id": 9002, "name": "Visitor alt"}],
            }
        ]
        snapshot.save()

        response = self.get(self.leader, "corporation", 2001)

        # a character Auth does not know gets a line of the compact list, not a card
        self.assertContains(response, '<span class="text-truncate">Stranger</span>', html=False)
        self.assertNotContains(response, '<h6 class="mb-1 text-truncate">Stranger</h6>')
        self.assertContains(response, 'class="badge text-bg-danger text-wrap">Not registered in Auth</span>')
        self.assertNotContains(response, "eos-auth-monitor-sortable")
        self.assertContains(response, "Visitor main")
        self.assertContains(response, "Visitor alt")
        self.assertContains(response, "Registered in Auth")

    def test_should_leave_the_members_registered_gauge_without_a_link(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["corporations"][0]["member_count"] = 3
        snapshot.save()

        response = self.get(self.leader, "index")

        # it follows the Discord gauge, whose link must not carry over
        self.assertContains(response, "Members registered")
        self.assertNotContains(response, 'aria-label="Members registered"')

    def test_should_say_which_corporation_has_how_many_problem_accounts(self):
        response = self.get(self.leader, "index")

        self.assertContains(response, 'class="fs-4 fw-bold lh-1 text-danger">1</span>')
        self.assertContains(response, '<span class="small">account with problems</span>')
        self.assertContains(response, '<i class="fas fa-circle-check"></i> No problems', count=1)

    def test_should_count_the_problems_of_the_corporation_itself(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["checks"].append("corp_token_missing")
        snapshot.data["corporations"][0]["problems"] = [{"check": "corp_token_missing", "detail": []}]
        snapshot.save()

        response = self.get(self.leader, "index")

        self.assertContains(response, "+ 1 Corporation problem")

    def test_should_show_the_overview_as_a_table_too(self):
        response = self.get(self.leader, "index")
        content = response.content.decode()

        self.assertContains(response, 'data-eos-auth-monitor-view-pane="table"')
        self.assertContains(response, "eos-auth-monitor-overview-table")
        # a line per Corporation, most problems first, marked for the filter like the tiles
        self.assertContains(response, '<tr class="eos-auth-monitor-corporation"', count=2)
        table = content[content.index("eos-auth-monitor-overview-table"):]
        self.assertLess(table.index("Corp 2002"), table.index("Corp 2001"))
        self.assertRegex(content, r"eos_auth_monitor/js/view[^\"]*\.js")

    def test_should_offer_to_show_only_corporations_with_problems(self):
        response = self.get(self.leader, "index")

        self.assertContains(response, 'data-eos-auth-monitor-filter-problems="#eos-auth-monitor-problems-only"')
        self.assertContains(response, 'id="eos-auth-monitor-problems-only"')
        # tile and table line of each Corporation
        self.assertContains(response, 'data-eos-auth-monitor-problems="1"', count=2)
        self.assertContains(response, 'data-eos-auth-monitor-problems="0"', count=2)

    def test_should_list_what_to_do_on_the_corporation_page(self):
        snapshot = Snapshot.objects.get()
        row = snapshot.data["corporations"][1]
        row["accounts"].append(account_row(33, 3301, [character_row(3301, [AUDIT_MISSING], corporation_id=2002)], {}))
        row["accounts"].append(account_row(44, 4401, corporation_id=2002))
        row["member_count"] = 5
        row["unregistered"] = [{"id": 7001, "name": "Stranger A"}, {"id": 7002, "name": "Stranger B"}]
        snapshot.save()

        # without aa-charlink, whether or not this instance has it
        with patch("eos_auth_monitor.views._charlink_url", return_value=None):
            response = self.get(self.leader, "corporation", 2002)
        content = response.content.decode()

        todos = content[content.index("eos-auth-monitor-todos"):content.index("Mains of this Corporation")]
        # one group per failed check, with the mains concerned and their names ready to copy
        self.assertIn("Audit missing", todos)
        self.assertIn('data-eos-auth-monitor-copy="Char 2201, Char 3301"', todos)
        self.assertIn(reverse("eos_auth_monitor:account", args=[33]), todos)
        self.assertNotIn("Char 4401", todos)
        self.assertIn("The player adds this character in the corptools Character Audit.", todos)
        # and the members Auth does not know
        self.assertIn('data-eos-auth-monitor-copy="Stranger A, Stranger B"', todos)
        self.assertRegex(content, r"eos_auth_monitor/js/copy[^\"]*\.js")

    def test_should_name_charlink_in_the_to_do_list_where_it_is_installed(self):
        with patch("eos_auth_monitor.views._charlink_url", return_value="/charlink/"):
            response = self.get(self.leader, "corporation", 2002)
        content = response.content.decode()

        todos = content[content.index("eos-auth-monitor-todos"):content.index("Mains of this Corporation")]
        self.assertIn("The player ticks Character Audit in CharLink and logs in with this character.", todos)
        self.assertNotIn("The player adds this character in the corptools Character Audit.", todos)

    def test_should_have_nothing_to_do_where_nothing_is_wrong(self):
        self.assertNotContains(self.get(self.leader, "corporation", 2001), "eos-auth-monitor-todos")

    def test_should_give_only_the_mains_with_problems_a_card(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["corporations"][1]["accounts"].append(account_row(44, 4401, corporation_id=2002))
        snapshot.save()

        response = self.get(self.leader, "corporation", 2002)
        content = response.content.decode()

        fine = content[content.index("eos-auth-monitor-problem-free"):]
        self.assertIn("Char 4401", fine)
        self.assertNotIn("Char 2201", fine)
        self.assertContains(response, 'class="card h-100 border-danger"', count=1)

    def test_should_put_a_hint_and_the_app_to_each_problem_of_an_account(self):
        # without aa-charlink, whether or not this instance has it
        with patch("eos_auth_monitor.views._charlink_url", return_value=None):
            response = self.get(self.leader, "account", 22)

        self.assertContains(response, "The player adds this character in the corptools Character Audit.")
        url = reverse("corptools:react")
        self.assertContains(response, f'<a href="{url}" class="text-nowrap eos-auth-monitor-fix">')

    def test_should_put_a_hint_to_each_problem_of_the_corporation(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["checks"].append("corp_token_missing")
        snapshot.data["corporations"][1]["problems"] = [{"check": "corp_token_missing", "detail": []}]
        snapshot.save()

        # without aa-charlink, whether or not this instance has it
        with patch("eos_auth_monitor.views._charlink_url", return_value=None):
            response = self.get(self.leader, "corporation", 2002)

        self.assertContains(response, "A Director adds a Corporation token in the corptools Corporation Audit.")
        url = reverse("corptools:corp_react")
        self.assertContains(response, f'<a href="{url}" class="text-nowrap eos-auth-monitor-fix">')

    CORPORATION_PROBLEMS = ["corp_token_missing", "structures_no_owner", "structures_owner_inactive"]

    def header(self, name, *args, charlink):
        snapshot = Snapshot.objects.get()
        snapshot.data["checks"] += self.CORPORATION_PROBLEMS
        snapshot.data["corporations"][1]["problems"] = [{"check": key, "detail": []} for key in self.CORPORATION_PROBLEMS]
        snapshot.save()
        with patch("eos_auth_monitor.views._charlink_url", return_value=charlink):
            content = self.get(self.leader, name, *args).content.decode()
        header = content[content.index('<div class="card mb-3">'):content.index("row row-cols-1 row-cols-sm-2")]
        links = re.findall(r'<a href="([^"]*)" class="text-nowrap eos-auth-monitor-fix">\s*([^<]*?)\s*<', header)
        return header, links

    def test_should_link_the_corporations_problems_to_charlink(self):
        for name, *args in [("corporation", 2002), ("corporation_service", 2002, "discord"), ("account", 22)]:
            with self.subTest(name):
                header, links = self.header(name, *args, charlink="/charlink/")

                # the owner an admin switched off is nothing CharLink can do: its hint stays, without a link
                self.assertEqual(links, [("/charlink/", "CharLink"), ("/charlink/", "CharLink")])
                self.assertIn(
                    "A Director ticks Corporation Audit in CharLink and logs in with the Director character.", header
                )
                self.assertIn(
                    "A character with the Station Manager role ticks Structures in CharLink and logs in.", header
                )
                self.assertIn("An admin switches the owner on again in the aa-structures admin.", header)
                self.assertNotIn("in the corptools Corporation Audit.", header)
                self.assertNotIn("adds the Corporation as an owner in aa-structures.", header)

    def test_should_link_the_corporations_problems_to_their_apps_without_charlink(self):
        # whether or not this instance has aa-charlink
        header, links = self.header("corporation", 2002, charlink=None)

        self.assertEqual(
            links,
            [
                (reverse("corptools:corp_react"), "corptools - Corporation Audit"),
                (reverse("structures:index"), "aa-structures"),
            ],
        )
        self.assertNotIn("CharLink", header)

    def gauge(self, content, icon, label):
        """Percentage and the line below it of the statistic tile with `icon` and `label`."""
        match = re.search(
            rf'<i class="{icon} fa-lg mb-2"></i>\s*<div class="fs-3 fw-bold [^"]+">\s*(\S+)&nbsp;%\s*</div>\s*'
            rf'<div class="small">{label}</div>\s*<div class="small text-body-secondary">\s*(.*?)\s*</div>',
            content,
            re.DOTALL,
        )
        return match.groups() if match else None

    def test_should_show_the_checks_apps_as_tiles_on_the_corporation_page(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["checks"] += ["corp_token_missing", "structures_no_owner"]
        snapshot.data["corporations"][1]["problems"] = [{"check": "corp_token_missing", "detail": []}]
        snapshot.save()

        content = self.get(self.leader, "corporation", 2002).content.decode()

        self.assertEqual(self.gauge(content, "fas fa-user-check", "Character Audit"), ("0", "0 of 1"))
        self.assertEqual(
            self.gauge(content, "fas fa-building-circle-check", "Corporation Audit"), ("0", "Corporation token missing")
        )
        self.assertEqual(self.gauge(content, "fas fa-tower-broadcast", "Structures"), ("100", "No problems"))
        # the apps come before the services, and no longer as lines in the header
        self.assertLess(content.index('<div class="small">Structures</div>'), content.index('<div class="small">Discord</div>'))
        header = content[content.index('<div class="card mb-3">'):content.index("row row-cols-2 row-cols-md-4")]
        self.assertNotIn("fas fa-user-check", header)

    def test_should_keep_the_checks_apps_as_lines_on_the_account_page(self):
        content = self.get(self.leader, "account", 22).content.decode()

        self.assertIsNone(self.gauge(content, "fas fa-user-check", "Character Audit"))
        self.assertIn('<span class="text-truncate"><i class="fas fa-user-check fa-fw"></i> Character Audit</span>', content)

    def test_should_fold_away_the_characters_without_problems(self):
        snapshot = Snapshot.objects.get()
        account = snapshot.data["corporations"][1]["accounts"][0]
        account["characters"].append(character_row(2202, corporation_id=2002))
        snapshot.save()

        response = self.get(self.leader, "account", 22)
        content = response.content.decode()

        table = content[content.index("eos-auth-monitor-sortable"):content.index("</table>")]
        folded = content[content.index("eos-auth-monitor-problem-free"):content.index("</details>")]
        self.assertIn("Char 2201", table)
        self.assertNotIn("Char 2202", table)
        self.assertIn("Char 2202", folded)
        self.assertIn("1 character without problems", folded)

    def test_should_link_each_character_to_its_character_audit(self):
        snapshot = Snapshot.objects.get()
        account = snapshot.data["corporations"][1]["accounts"][0]
        account["characters"].append(character_row(2202, corporation_id=2002))
        snapshot.save()

        response = self.get(self.leader, "account", 22)
        content = response.content.decode()

        table = content[content.index("eos-auth-monitor-sortable"):content.index("</table>")]
        folded = content[content.index("eos-auth-monitor-problem-free"):content.index("</details>")]
        problem_url = reverse("corptools:reactmain", args=[2201])
        fine_url = reverse("corptools:reactmain", args=[2202])
        self.assertIn(f'<a href="{problem_url}" class="text-break">Char 2201</a>', table)
        self.assertIn(f'<a href="{fine_url}" class="text-break">Char 2202</a>', folded)

    def test_should_say_when_no_character_of_an_account_has_a_problem(self):
        response = self.get(self.leader, "account", 11)

        self.assertContains(response, "No character of this account has a problem.")
        self.assertNotContains(response, "eos-auth-monitor-sortable")
        self.assertContains(response, "1 character without problems")

    def test_should_say_how_many_characters_were_left_out(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["corporations"][0]["accounts"][0]["left_out"] = 2
        snapshot.save()

        response = self.get(self.leader, "account", 11)

        self.assertContains(response, "2 characters outside the Alliance are neither shown nor checked here.")

    def test_should_not_mention_left_out_characters_when_there_are_none(self):
        # also a snapshot from before the count existed
        response = self.get(self.leader, "account", 11)

        self.assertNotContains(response, "eos-auth-monitor-left-out")

    def test_should_say_when_a_corporation_is_not_in_the_overview(self):
        outsider = make_user("outsider", BASIC_ACCESS, corporation_id=2999)

        response = self.get(outsider, "corporation", 2999)

        self.assertContains(response, "This Corporation is not part of the overview.")

    def test_should_say_when_there_is_no_snapshot_yet(self):
        from eos_auth_monitor.models import Snapshot

        Snapshot.objects.all().delete()

        self.assertContains(self.get(self.leader, "index"), "The overview has not been built yet.")

    def test_should_say_when_the_snapshot_is_of_another_alliance(self):
        configure(alliance_id=ALLIANCE_ID + 1)

        self.assertContains(self.get(self.leader, "index"), "The Alliance was changed.")


class TestMetricsFooter(ViewTestCase):
    def setUp(self):
        super().setUp()
        snapshot = Snapshot.objects.get()
        snapshot.data["metrics"] = {
            "seconds": 3.5,
            "phases": {"accounts": 0.5},
            "queries": 40,
            "query_seconds": 1.25,
            "corporations": 2,
            "accounts": 5,
            "characters": 9,
            "member_lists": 1,
            "payload_bytes": 20480,
        }
        snapshot.save()

    def test_should_show_the_cost_of_the_last_rebuild_to_leadership(self):
        response = self.get(self.leader, "index")

        self.assertContains(response, "Last rebuild 3.5 s, 40 queries (1.25 s)")
        self.assertContains(response, "2 Corporations, 5 accounts, 9 characters")
        self.assertContains(response, "20 KB stored")
        self.assertContains(response, "Reading accounts: 0.5 s")

    def test_should_show_the_member_lists_only_when_they_are_fetched(self):
        self.assertNotContains(self.get(self.leader, "index"), "member lists 1/2")

        data = Snapshot.objects.get()
        data.data["members_fetched"] = True
        data.save()

        self.assertContains(self.get(self.leader, "index"), "member lists 1/2")

    def test_should_keep_it_from_a_ceo(self):
        self.assertNotContains(self.get(self.ceo, "corporation", 2001), "Last rebuild")

    def test_should_show_nothing_for_a_snapshot_without_figures(self):
        snapshot = Snapshot.objects.get()
        del snapshot.data["metrics"]
        snapshot.save()

        self.assertNotContains(self.get(self.leader, "index"), "Last rebuild")


class TestSettings(ViewTestCase):
    def post(self, data):
        self.client.force_login(self.admin)
        with patch("eos_auth_monitor.views.update_snapshot") as task:
            response = self.client.post(reverse("eos_auth_monitor:settings"), data)
        return response, task

    def test_should_offer_the_alliance_as_a_searchable_dropdown(self):
        response = self.get(self.admin, "settings")

        self.assertContains(response, "data-eos-auth-monitor-search")
        self.assertContains(response, "tom-select")

    def test_should_group_the_checks_by_app(self):
        response = self.get(self.admin, "settings")

        self.assertContains(response, "corptools - Character Audit")
        self.assertContains(response, "corptools - Corporation Audit")
        # a group is offered only when the app it reads from is installed
        if is_app_installed("structures"):
            self.assertContains(response, "aa-structures")
        else:
            self.assertNotContains(response, "aa-structures")

    def test_should_store_the_switched_off_checks_and_rebuild(self):
        alliance = make_alliance(ALLIANCE_ID + 5)
        data = {"alliance": alliance.pk, "stale_after_days": "7", "check_char_audit_missing": "on"}

        response, task = self.post(data)

        self.assertRedirects(response, reverse("eos_auth_monitor:settings"))
        config = MonitorConfiguration.get_solo()
        self.assertEqual(config.alliance, alliance)
        self.assertEqual(config.stale_after_days, 7)
        self.assertNotIn("char_audit_missing", config.disabled_checks)
        self.assertIn("char_scopes_missing", config.disabled_checks)
        task.delay.assert_called_once_with()

    def test_should_offer_and_store_the_limit_to_the_alliance_characters(self):
        response = self.get(self.admin, "settings")
        self.assertContains(response, 'name="alliance_characters_only"')
        self.assertFalse(MonitorConfiguration.get_solo().alliance_characters_only)

        self.post({"alliance": make_alliance().pk, "alliance_characters_only": "on"})

        self.assertTrue(MonitorConfiguration.get_solo().alliance_characters_only)

    def test_should_offer_the_corptools_sections_and_scopes(self):
        response = self.get(self.admin, "settings")

        self.assertContains(response, "Corporation Audit: sections that count")
        self.assertContains(response, 'value="observers"')
        self.assertContains(response, "esi-industry.read_corporation_mining.v1")

    def test_should_store_what_is_left_out_of_the_corptools_checks(self):
        from eos_auth_monitor.sources import corptools

        sections = [key for key, _label in corptools.corporation_sections() if key != "observers"]
        scopes = [scope for scope in corptools.corporation_scopes() if scope != "esi-industry.read_corporation_mining.v1"]

        self.post(
            {
                "alliance": make_alliance().pk,
                "corporation_sections": sections,
                "corporation_scopes": scopes,
                "character_sections": [key for key in corptools.character_sections()],
                "character_scopes": corptools.character_scopes(),
            }
        )

        config = MonitorConfiguration.get_solo()
        self.assertEqual(config.excluded_corporation_sections, ["observers"])
        self.assertEqual(config.excluded_corporation_scopes, ["esi-industry.read_corporation_mining.v1"])
        self.assertEqual(config.excluded_character_sections, [])
        self.assertEqual(config.excluded_character_scopes, [])

    def test_should_keep_the_state_of_checks_whose_app_is_missing(self):
        configure(disabled_checks=["structures_no_owner"])

        self.post({"alliance": make_alliance().pk})

        self.assertIn("structures_no_owner", MonitorConfiguration.get_solo().disabled_checks)

    def unchanged(self, **changes):
        """The settings form as the page posts it untouched, with `changes` on top."""
        form = MonitorConfigurationForm(instance=MonitorConfiguration.get_solo())
        data = {name: form[name].value() for name in form.fields}
        data.update(changes)
        # the test client cannot send None; an empty field is left out by the browser too
        return {name: value for name, value in data.items() if value is not None}

    def test_should_store_the_notice_without_a_rebuild(self):
        response, task = self.post(self.unchanged(member_notice="  Read the wiki.  "))

        self.assertRedirects(response, reverse("eos_auth_monitor:settings"))
        self.assertEqual(MonitorConfiguration.get_solo().member_notice, "Read the wiki.")
        task.delay.assert_not_called()

    def test_should_rebuild_when_more_than_the_notice_changed(self):
        _response, task = self.post(self.unchanged(member_notice="Read the wiki.", alliance_characters_only=True))

        task.delay.assert_called_once_with()

    def test_should_store_a_notice_of_blanks_empty(self):
        configure(member_notice="Old")

        self.post(self.unchanged(member_notice="  \n "))

        self.assertEqual(MonitorConfiguration.get_solo().member_notice, "")


class TestMemberNotice(ViewTestCase):
    """The notice from the settings on My account and My Corporation, and nowhere else."""

    NOTICE = "Read the wiki.\n<b>Now</b>"
    BOX = "eos-auth-monitor-notice"

    def setUp(self):
        super().setUp()
        self.member = make_user("member", VIEW_OWN, corporation_id=2002)
        configure(member_notice=self.NOTICE)

    def test_should_show_the_notice_on_my_account(self):
        response = self.get(self.member, "own_account")

        self.assertContains(response, self.BOX)
        # line breaks kept, markup escaped
        self.assertContains(response, "Read the wiki.<br>&lt;b&gt;Now&lt;/b&gt;")

    def test_should_show_the_notice_on_my_corporation(self):
        for user in (self.ceo, self.leader):
            with self.subTest(user.username):
                self.assertContains(self.get(user, "corporation", 2001), self.BOX)

    def test_should_not_show_the_notice_elsewhere(self):
        pages = [
            (self.leader, "corporation", 2002),
            (self.leader, "index"),
            (self.ceo, "account", 11),
            (self.ceo, "corporation_service", 2001, "discord"),
            (self.admin, "settings"),
        ]
        for user, name, *args in pages:
            with self.subTest(name):
                self.assertNotContains(self.get(user, name, *args), self.BOX)

    def test_should_show_no_box_while_the_notice_is_empty(self):
        configure(member_notice="")

        self.assertNotContains(self.get(self.member, "own_account"), self.BOX)
        self.assertNotContains(self.get(self.ceo, "corporation", 2001), self.BOX)


class TestScopeDetail(ViewTestCase):
    def test_should_name_two_scopes_and_keep_the_list_as_tooltip(self):
        scopes = ["esi-a.v1", "esi-b.v1", "esi-c.v1", "esi-d.v1"]
        snapshot = Snapshot.objects.get()
        snapshot.data["corporations"][0]["accounts"][0]["characters"] = [
            character_row(1101, [{"check": "char_scopes_missing", "detail": scopes}])
        ]
        snapshot.save()

        response = self.get(self.leader, "account", 11)

        self.assertContains(
            response, 'title="esi-a.v1, esi-b.v1, esi-c.v1, esi-d.v1">esi-a.v1, esi-b.v1 and 2 more</div>'
        )


class TestOwnAccount(ViewTestCase):
    """A member with view_own: their own account and nothing else."""

    def setUp(self):
        super().setUp()
        self.member = make_user("member", VIEW_OWN, corporation_id=2002)
        snapshot = Snapshot.objects.get()
        main_id = self.member.profile.main_character.character_id
        problem = character_row(main_id, [AUDIT_MISSING], corporation_id=2002)
        snapshot.data["corporations"][1]["accounts"].append(
            account_row(self.member.pk, main_id, [problem, character_row(9901, corporation_id=2002)], {})
        )
        snapshot.save()

    def test_should_send_a_member_to_their_own_account(self):
        response = self.get(self.member, "index")

        self.assertRedirects(response, reverse("eos_auth_monitor:own_account"))

    def test_should_show_the_own_problems_and_what_to_do(self):
        response = self.get(self.member, "own_account")

        self.assertContains(response, f"Char {self.member.profile.main_character.character_id}")
        self.assertContains(response, "eos-auth-monitor-fix")
        self.assertContains(response, '<small class="text-muted">My account</small>')
        self.assertContains(response, "1 character without problems")

    def test_should_tell_a_member_about_their_characters_left_out(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["corporations"][1]["accounts"][-1]["left_out"] = 1
        snapshot.save()

        response = self.get(self.member, "own_account")

        self.assertContains(
            response, "1 of your characters is outside the Alliance and neither shown nor checked here."
        )

    def test_should_ask_a_member_whether_a_character_is_missing(self):
        with patch("eos_auth_monitor.views._charlink_url", return_value="/charlink/"):
            with_charlink = self.get(self.member, "own_account")
        with patch("eos_auth_monitor.views._charlink_url", return_value=None):
            without = self.get(self.member, "own_account")

        question = "Is one of your characters missing here?"
        self.assertContains(with_charlink, question)
        self.assertContains(with_charlink, '<a href="/charlink/" class="btn btn-sm btn-primary text-nowrap">CharLink')
        # without aa-charlink, Alliance Auth's own page adds the character
        self.assertContains(without, question)
        self.assertContains(without, f'<a href="{reverse("authentication:add_character")}"')

    def test_should_ask_about_missing_characters_also_without_an_account_in_the_overview(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["corporations"][1]["accounts"].pop()
        snapshot.save()

        response = self.get(self.member, "own_account")

        self.assertContains(response, "Your account is not part of the overview")
        self.assertContains(response, "Is one of your characters missing here?")

    def test_should_not_ask_leadership_about_someone_elses_characters(self):
        response = self.get(self.leader, "account", self.member.pk)

        self.assertNotContains(response, "Is one of your characters missing here?")
        self.assertNotContains(response, "of your characters")

    def test_should_speak_to_the_member_when_nothing_is_wrong(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["corporations"][1]["accounts"][-1]["characters"][0]["problems"] = []
        snapshot.save()

        own = self.get(self.member, "own_account")
        other = self.get(self.leader, "account", self.member.pk)

        self.assertContains(own, "None of your characters has a problem.")
        self.assertContains(other, "No character of this account has a problem.")

    def fix_links(self, response):
        return re.findall(r'<a href="([^"]*)" class="text-nowrap eos-auth-monitor-fix">\s*([^<]*?)\s*<', response.content.decode())

    def test_should_link_the_own_problems_to_charlink(self):
        with patch("eos_auth_monitor.views._charlink_url", return_value="/charlink/"):
            response = self.get(self.member, "own_account")

        self.assertEqual(self.fix_links(response), [("/charlink/", "CharLink")])

    CHARLINK_HINT = "Tick Character Audit in CharLink and log in with this character."
    CHARLINK_HINT_ABOUT = "The player ticks Character Audit in CharLink and logs in with this character."
    CORPTOOLS_HINT = "The player adds this character in the corptools Character Audit."

    def test_should_tell_a_member_what_to_do_in_charlink(self):
        with patch("eos_auth_monitor.views._charlink_url", return_value="/charlink/"):
            response = self.get(self.member, "own_account")

        self.assertContains(response, self.CHARLINK_HINT)
        self.assertNotContains(response, self.CHARLINK_HINT_ABOUT)
        self.assertNotContains(response, self.CORPTOOLS_HINT)

    @skipUnless(apps.is_installed("charlink"), "aa-charlink is not installed")
    def test_should_find_the_page_of_the_installed_charlink(self):
        response = self.get(self.member, "own_account")

        self.assertEqual(self.fix_links(response), [(reverse("charlink:index"), "CharLink")])

    def test_should_link_the_own_problems_to_the_checks_app_without_charlink(self):
        # whether or not this instance has aa-charlink
        with patch("eos_auth_monitor.views._charlink_url", return_value=None):
            response = self.get(self.member, "own_account")

        self.assertEqual(self.fix_links(response), [(reverse("corptools:react"), "corptools - Character Audit")])
        # still to the member, not about them
        self.assertContains(response, "Add this character in the corptools Character Audit.")
        self.assertNotContains(response, self.CORPTOOLS_HINT)
        self.assertNotContains(response, self.CHARLINK_HINT)

    def test_should_link_someone_elses_problems_to_charlink(self):
        with patch("eos_auth_monitor.views._charlink_url", return_value="/charlink/"):
            response = self.get(self.leader, "account", self.member.pk)

        self.assertEqual(self.fix_links(response), [("/charlink/", "CharLink")])
        # about the player, not to them
        self.assertContains(response, self.CHARLINK_HINT_ABOUT)
        self.assertNotContains(response, self.CHARLINK_HINT)
        self.assertNotContains(response, self.CORPTOOLS_HINT)

    def test_should_link_the_corporations_problems_to_charlink_on_an_account(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["checks"].append("corp_token_missing")
        snapshot.data["corporations"][1]["problems"] = [{"check": "corp_token_missing", "detail": []}]
        snapshot.save()

        with patch("eos_auth_monitor.views._charlink_url", return_value="/charlink/"):
            response = self.get(self.leader, "account", self.member.pk)

        self.assertEqual(self.fix_links(response), [("/charlink/", "CharLink"), ("/charlink/", "CharLink")])

    def test_should_show_nothing_of_the_other_accounts(self):
        response = self.get(self.member, "own_account")

        # no header with the Corporation's figures, no link to its lists
        self.assertNotContains(response, "Accounts with problems")
        self.assertNotContains(response, "Char 2201")
        self.assertNotContains(response, reverse("eos_auth_monitor:corporation", args=[2002]))
        self.assertNotContains(response, reverse("eos_auth_monitor:corporation_service", args=[2002, "discord"]))

    def test_should_keep_a_member_out_of_the_other_pages(self):
        pages = [
            ("account", 22),
            ("corporation", 2002),
            ("corporation_service", 2002, "discord"),
            ("service", "discord"),
            ("settings",),
        ]
        for name, *args in pages:
            with self.subTest(name):
                response = self.get(self.member, name, *args)
                self.assertEqual(response.status_code, 302)
                self.assertIn("login", response.url)

    def test_should_say_when_the_own_account_is_not_in_the_overview(self):
        outsider = make_user("outsider", VIEW_OWN, corporation_id=2999)

        response = self.get(outsider, "own_account")

        self.assertContains(response, "Your account is not part of the overview")

    def test_should_offer_the_own_account_in_the_navigation(self):
        response = self.get(self.member, "own_account")

        self.assertContains(response, f'href="{reverse("eos_auth_monitor:own_account")}"')
        self.assertNotContains(response, f'href="{reverse("eos_auth_monitor:index")}" class="nav-link')

    def test_should_let_a_member_follow_the_progress_bar(self):
        # every page polls it while a rebuild runs
        self.assertEqual(self.get(self.member, "rebuild_progress").status_code, 200)

    def test_should_keep_the_own_account_to_holders_of_view_own(self):
        response = self.get(self.ceo, "own_account")

        self.assertEqual(response.status_code, 302)


class TestBrokerDown(ViewTestCase):
    def post(self, user, name, data):
        self.client.force_login(user)
        with patch("eos_auth_monitor.views.update_snapshot") as task:
            task.delay.side_effect = OperationalError("broker down")
            return self.client.post(reverse(f"eos_auth_monitor:{name}"), data, follow=True)

    def test_should_save_the_settings_and_say_the_rebuild_waits(self):
        alliance = make_alliance(ALLIANCE_ID + 7)

        response = self.post(self.admin, "settings", {"alliance": alliance.pk})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(MonitorConfiguration.get_solo().alliance, alliance)
        self.assertContains(response, "the task queue is not reachable")
        self.assertIsNone(progress.get()["state"])

    def test_should_say_the_rebuild_could_not_start(self):
        response = self.post(self.leader, "rebuild", {})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The rebuild could not be started")
        self.assertIsNone(progress.get()["state"])

    def test_should_keep_a_running_bar_when_a_second_start_fails(self):
        progress.step("members", 1, 2)

        self.post(self.leader, "rebuild", {})

        self.assertEqual(progress.get()["state"], progress.RUNNING)


class TestRebuild(ViewTestCase):
    def post(self, user, data=None):
        self.client.force_login(user)
        with patch("eos_auth_monitor.views.update_snapshot") as task:
            response = self.client.post(reverse("eos_auth_monitor:rebuild"), data or {})
        return response, task

    def test_should_go_back_to_the_page_it_came_from(self):
        page = reverse("eos_auth_monitor:corporation", args=[2002])

        response, _ = self.post(self.leader, {"next": page})

        self.assertRedirects(response, page)

    def test_should_never_send_anyone_elsewhere(self):
        response, _ = self.post(self.leader, {"next": "https://evil.example/"})

        self.assertRedirects(response, reverse("eos_auth_monitor:index"))

    def test_should_show_the_run_as_queued_at_once(self):
        self.post(self.leader)

        response = self.get(self.leader, "rebuild_progress")

        self.assertEqual(response.json()["state"], progress.QUEUED)

    def test_should_offer_the_button_and_the_progress_bar(self):
        response = self.get(self.leader, "index")

        self.assertContains(response, "eos-auth-monitor-rebuild")
        self.assertContains(response, reverse("eos_auth_monitor:rebuild_progress"))

    def test_should_report_the_phase_of_a_running_task(self):
        progress.step("members", 1, 2)

        data = self.get(self.ceo, "rebuild_progress").json()

        self.assertEqual(data, {"state": progress.RUNNING, "percent": 75, "phase": "Reading member lists"})

    def test_should_keep_users_without_permission_away_from_the_progress(self):
        self.assertEqual(self.get(make_user("nobody"), "rebuild_progress").status_code, 302)

    def test_should_start_the_task(self):
        response, task = self.post(self.leader)

        self.assertRedirects(response, reverse("eos_auth_monitor:index"))
        task.delay.assert_called_once_with()

    def test_should_not_let_a_ceo_start_it(self):
        response, task = self.post(self.ceo)

        self.assertEqual(response.status_code, 302)
        task.delay.assert_not_called()

    def test_should_only_start_it_on_post(self):
        self.client.force_login(self.leader)

        self.assertEqual(self.client.get(reverse("eos_auth_monitor:rebuild")).status_code, 405)


NAV_LINK = re.compile(r'<a class="nav-link ?(active)?" href="([^"]+)"')


class TestNavigation(ViewTestCase):
    def tabs(self, response):
        """(href, active) of each tab of the app navbar, in order."""
        return [
            (href, bool(active))
            for active, href in NAV_LINK.findall(response.content.decode())
            if href.startswith("/eos_auth_monitor/")
        ]

    def test_should_order_the_tabs_from_the_own_main_to_the_alliance(self):
        everyone = make_user("everyone", VIEW_OWN, BASIC_ACCESS, VIEW_ALL, MANAGE_SETTINGS, corporation_id=2001)

        hrefs = [href for href, _ in self.tabs(self.get(everyone, "settings"))]

        self.assertEqual(
            hrefs,
            [
                reverse("eos_auth_monitor:own_account"),
                reverse("eos_auth_monitor:corporation", args=[2001]),
                reverse("eos_auth_monitor:index"),
                reverse("eos_auth_monitor:settings"),
            ],
        )

    def test_should_give_each_permission_its_tab(self):
        member = make_user("member", VIEW_OWN, corporation_id=2002)
        cases = [
            (member, "own_account", [reverse("eos_auth_monitor:own_account")]),
            (self.ceo, "corporation", [reverse("eos_auth_monitor:corporation", args=[2001])]),
            (self.admin, "settings", [reverse("eos_auth_monitor:settings")]),
        ]
        for user, page, expected in cases:
            with self.subTest(user.username):
                args = [2001] if page == "corporation" else []
                self.assertEqual([href for href, _ in self.tabs(self.get(user, page, *args))], expected)

    def test_should_offer_leadership_the_own_corporation_as_well(self):
        hrefs = [href for href, _ in self.tabs(self.get(self.leader, "index"))]

        self.assertEqual(
            hrefs, [reverse("eos_auth_monitor:corporation", args=[2001]), reverse("eos_auth_monitor:index")]
        )

    def test_should_mark_the_tab_of_the_page(self):
        own_corporation = reverse("eos_auth_monitor:corporation", args=[2001])
        overview = reverse("eos_auth_monitor:index")
        cases = [
            (("index",), overview),
            (("service", "discord"), overview),
            (("corporation", 2001), own_corporation),
            (("account", 11), own_corporation),
            (("corporation_service", 2001, "discord"), own_corporation),
            # another Corporation is reached from the Alliance overview
            (("corporation", 2002), overview),
            (("account", 22), overview),
        ]
        for (name, *args), expected in cases:
            with self.subTest(name=name, args=args):
                active = [href for href, is_active in self.tabs(self.get(self.leader, name, *args)) if is_active]
                self.assertEqual(active, [expected])

    def test_should_mark_the_own_account_and_the_settings(self):
        member = make_user("member", VIEW_OWN, corporation_id=2002)

        own = [href for href, is_active in self.tabs(self.get(member, "own_account")) if is_active]
        settings = [href for href, is_active in self.tabs(self.get(self.admin, "settings")) if is_active]

        self.assertEqual(own, [reverse("eos_auth_monitor:own_account")])
        self.assertEqual(settings, [reverse("eos_auth_monitor:settings")])


class TestOwnAccountServices(ViewTestCase):
    def test_should_link_the_own_services_to_alliance_auths_services_page(self):
        member = make_user("member", VIEW_OWN, corporation_id=2001)
        snapshot = Snapshot.objects.get()
        main_id = member.profile.main_character.character_id
        snapshot.data["corporations"][0]["accounts"].append(account_row(member.pk, main_id, services={}))
        snapshot.save()

        response = self.get(member, "own_account")

        self.assertContains(response, f'<a href="{reverse("services:services")}" class="stretched-link"', count=1)

    def test_should_keep_the_corporation_list_on_someone_elses_account(self):
        response = self.get(self.ceo, "account", 11)

        self.assertNotContains(response, f'<a href="{reverse("services:services")}" class="stretched-link"')
        self.assertContains(
            response, f'<a href="{reverse("eos_auth_monitor:corporation_service", args=[2001, "discord"])}"'
        )


class TestCorporationExport(ViewTestCase):
    """The to-do list of 2002 as CSV: two mains without an audit, two members Auth does not know."""

    def setUp(self):
        super().setUp()
        snapshot = Snapshot.objects.get()
        row = snapshot.data["corporations"][1]
        row["accounts"].append(account_row(33, 3301, [character_row(3301, [AUDIT_MISSING], corporation_id=2002)], {}))
        row["member_count"] = 5
        # a name a spreadsheet would run as a formula
        row["unregistered"] = [{"id": 7001, "name": "Stranger A"}, {"id": 7002, "name": "=Stranger B"}]
        snapshot.save()

    def export(self, user, corporation_id=2002, group=None):
        self.client.force_login(user)
        url = reverse("eos_auth_monitor:corporation_export", args=[corporation_id])
        return self.client.get(url, {"group": group} if group else {})

    @staticmethod
    def lines(response):
        return list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))

    def test_should_export_one_group_as_a_name_per_line(self):
        response = self.export(self.leader, group="char_audit_missing")

        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="C2002-char_audit_missing.csv"')
        self.assertEqual(self.lines(response), [["Name"], ["Char 2201"], ["Char 3301"]])

    def test_should_export_the_unregistered_members(self):
        response = self.export(self.leader, group="unregistered")

        self.assertEqual(self.lines(response), [["Name"], ["Stranger A"], ["'=Stranger B"]])

    def test_should_export_the_whole_list_with_the_problem_of_each_name(self):
        response = self.export(self.leader)

        self.assertEqual(response["Content-Disposition"], 'attachment; filename="C2002-todo.csv"')
        self.assertEqual(
            self.lines(response),
            [
                ["Problem", "Name"],
                ["Audit missing", "Char 2201"],
                ["Audit missing", "Char 3301"],
                ["Not registered in Auth", "Stranger A"],
                ["Not registered in Auth", "'=Stranger B"],
            ],
        )

    def test_should_start_with_a_byte_order_mark_for_excel(self):
        self.assertTrue(self.export(self.leader).content.startswith("\ufeff".encode()))

    def test_should_export_only_what_the_viewer_may_see(self):
        self.assertEqual(self.export(self.ceo).status_code, 403)
        self.assertEqual(self.export(make_user("nobody")).status_code, 302)
        self.assertEqual(self.export(make_user("member", VIEW_OWN, corporation_id=2002)).status_code, 302)

    def test_should_let_the_ceo_export_the_own_corporation(self):
        ceo = make_user("ceo2", BASIC_ACCESS, corporation_id=2002)

        self.assertEqual(self.export(ceo).status_code, 200)

    def test_should_not_find_an_empty_or_unknown_group(self):
        self.assertEqual(self.export(self.leader, group="nonsense").status_code, 404)
        self.assertEqual(self.export(self.leader, corporation_id=2001).status_code, 404)
        self.assertEqual(self.export(self.leader, corporation_id=2999).status_code, 404)

    def test_should_offer_a_csv_button_beside_each_copy_button_and_for_the_whole_list(self):
        content = self.get(self.leader, "corporation", 2002).content.decode()
        url = reverse("eos_auth_monitor:corporation_export", args=[2002])

        todos = content[content.index("eos-auth-monitor-todos"):content.index("Mains of this Corporation")]
        self.assertIn(f'href="{url}"', todos)
        self.assertIn(f'href="{url}?group=char_audit_missing"', todos)
        self.assertIn(f'href="{url}?group=unregistered"', todos)
        # and once more beside the list of the unregistered members further down
        self.assertEqual(content.count(f'href="{url}?group=unregistered"'), 2)


class TestAltsInAnotherCorporation(ViewTestCase):
    """An alt counts in the Corporation it is in: its problems show there, beside its main's name."""

    def setUp(self):
        super().setUp()
        self.ceo_2002 = make_user("ceo2002", BASIC_ACCESS, corporation_id=2002)
        snapshot = Snapshot.objects.get()
        # account 11's main is in 2001; its alt with a problem is in 2002
        snapshot.data["corporations"][0]["accounts"][0]["characters"].append(
            character_row(1102, [AUDIT_MISSING], corporation_id=2002)
        )
        snapshot.save()

    def test_should_show_the_alt_on_the_page_of_its_corporation(self):
        response = self.get(self.leader, "corporation", 2002)
        content = response.content.decode()

        todos = content[content.index("eos-auth-monitor-todos"):content.index("Mains of this Corporation")]
        self.assertIn('data-eos-auth-monitor-copy="Char 1101, Char 2201"', todos)
        self.assertContains(response, 'class="card h-100 border-danger"', count=2)
        self.assertContains(response, "Main in Corp 2001")
        self.assertContains(response, reverse("eos_auth_monitor:account", args=[11]))

    def test_should_keep_the_main_corporation_free_of_the_alts_problem(self):
        response = self.get(self.leader, "corporation", 2001)

        self.assertNotContains(response, "eos-auth-monitor-todos")
        self.assertNotContains(response, 'class="card h-100 border-danger"')

    def test_should_not_link_a_ceo_to_an_account_of_another_corporation(self):
        response = self.get(self.ceo_2002, "corporation", 2002)

        self.assertContains(response, "Main in Corp 2001")
        self.assertNotContains(response, reverse("eos_auth_monitor:account", args=[11]))
        self.assertContains(response, reverse("eos_auth_monitor:account", args=[22]))


class TestCharacterAuditList(ViewTestCase):
    """Behind the Character Audit tile: every main with the checks its account fails."""

    def test_should_list_every_main_with_its_failed_checks(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["corporations"][1]["accounts"][0]["characters"].append(
            character_row(2202, [AUDIT_MISSING], corporation_id=2002)
        )
        snapshot.save()

        response = self.get(self.leader, "character_audit")

        content = response.content.decode()
        self.assertContains(response, "1 of 2 mains complete")
        self.assertContains(response, '<small class="text-muted">Character Audit</small>')
        # most problems first, each account linked; two characters fail the same check
        self.assertLess(content.index("Char 2201"), content.index("Char 1101"))
        self.assertContains(response, reverse("eos_auth_monitor:account", args=[11]))
        tags = content[content.index("eos-auth-monitor-tags"):]
        self.assertIn("Audit missing &times;2</span>", tags)
        self.assertContains(response, '<span class="badge text-bg-success">complete</span>', count=1)

    def test_should_not_exist_without_character_checks(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["checks"] = ["corp_token_missing"]
        snapshot.save()

        self.assertEqual(self.get(self.leader, "character_audit").status_code, 404)

    def test_should_keep_everyone_but_leadership_out(self):
        self.assertEqual(self.get(self.ceo, "character_audit").status_code, 302)
        self.assertEqual(self.get(self.leader, "character_audit").status_code, 200)


class TestDirectorList(ViewTestCase):
    """Behind the Corporation Audit and Structures tiles: every Director and whether it has the token."""

    def setUp(self):
        super().setUp()
        snapshot = Snapshot.objects.get()
        snapshot.data["checks"] += ["corp_token_missing", "structures_no_owner"]
        snapshot.data["members_fetched"] = True
        snapshot.data["corporations"][0]["directors"] = [
            {
                "id": 1101,
                "name": "Char 1101",
                "in_auth": True,
                "user_id": 11,
                "main_name": "Char 1101",
                "tokens": {"corptools_corporations": True, "structures": False},
            }
        ]
        snapshot.data["corporations"][1]["directors"] = [
            {
                "id": 9001,
                "name": "Stranger",
                "in_auth": False,
                "user_id": None,
                "main_name": None,
                "tokens": {"corptools_corporations": False, "structures": False},
            }
        ]
        snapshot.save()

    def test_should_list_the_directors_without_the_token_first(self):
        response = self.get(self.leader, "directors", "corptools_corporations")

        content = response.content.decode()
        self.assertContains(response, "1 of 2 Directors with a token")
        self.assertContains(response, '<small class="text-muted">Corporation Audit</small>')
        self.assertLess(content.index("Stranger"), content.index("Char 1101"))
        self.assertContains(response, 'eos-auth-monitor-no-token">no token</span>', count=1)
        self.assertContains(response, 'eos-auth-monitor-not-in-auth">not in Auth</span>', count=1)
        self.assertContains(response, f'<a href="{reverse("eos_auth_monitor:account", args=[11])}">Char 1101</a>')

    def test_should_ask_each_list_for_its_own_token(self):
        response = self.get(self.leader, "directors", "structures")

        self.assertContains(response, "0 of 2 Directors with a token")
        self.assertContains(response, 'eos-auth-monitor-no-token">no token</span>', count=2)

    def test_should_not_exist_for_a_group_without_a_director_list(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["checks"] = ["char_audit_missing", "corp_token_missing"]
        snapshot.save()

        for group in ("structures", "corptools_characters", "nothing"):
            with self.subTest(group):
                self.assertEqual(self.get(self.leader, "directors", group).status_code, 404)

    def test_should_say_that_only_corptools_directors_are_known_without_esi(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["members_fetched"] = False
        snapshot.save()

        response = self.get(self.leader, "directors", "corptools_corporations")

        self.assertContains(response, "Only the Directors corptools knows are listed")

    def test_should_say_where_the_roles_could_not_be_read(self):
        snapshot = Snapshot.objects.get()
        snapshot.data["corporations"][1]["no_director_token"] = True
        snapshot.save()

        with_marker = self.get(self.leader, "directors", "corptools_corporations")
        snapshot.data["corporations"][1]["no_director_token"] = False
        snapshot.save()
        without = self.get(self.leader, "directors", "corptools_corporations")

        self.assertContains(with_marker, "No Director token could read the roles of 1 Corporation")
        self.assertNotContains(without, "No Director token could read the roles")

    def test_should_keep_everyone_but_leadership_out(self):
        self.assertEqual(self.get(self.ceo, "directors", "corptools_corporations").status_code, 302)
        self.assertEqual(self.get(self.leader, "directors", "corptools_corporations").status_code, 200)


class TestVoluntaryServices(ViewTestCase):
    """Discord, QQ and Telegram are up to the member: the overview's Corporations show their share without rating it."""

    def setUp(self):
        super().setUp()
        snapshot = Snapshot.objects.get()
        snapshot.data = snapshot_data([corporation_row(2001, [account_row(11, 1101)])], services=["discord", "mumble"])
        snapshot.save()

    def test_should_show_a_voluntary_share_uncoloured_on_the_tile(self):
        content = self.get(self.leader, "index").content.decode()

        def tile_class(icon, label):
            match = re.search(
                rf'<i class="{icon} fa-fw"></i> {label}</span>\s*<span class="text-nowrap fw-semibold ([^"]+)">', content
            )
            return match.group(1)

        self.assertEqual(tile_class("fab fa-discord", "Discord"), "text-body-secondary")
        self.assertEqual(tile_class("fas fa-headset", "Mumble"), "text-danger")

    def test_should_show_a_voluntary_share_uncoloured_in_the_table(self):
        content = self.get(self.leader, "index").content.decode()

        table = content[content.index("eos-auth-monitor-overview-table"):]
        table = table[:table.index("</table>")]
        # the columns in service order: Discord, then Mumble
        self.assertEqual(
            re.findall(r'class="fw-semibold text-nowrap ([^"]+)"', table), ["text-body-secondary", "text-danger"]
        )

    def test_should_keep_the_cockpit_coloured(self):
        content = self.get(self.leader, "index").content.decode()

        match = re.search(r'<i class="fab fa-discord fa-lg mb-2"></i>\s*<div class="fs-3 fw-bold ([^"]+)">', content)
        self.assertEqual(match.group(1), "text-danger")
