from unittest.mock import patch

from django.test import RequestFactory
from django.urls import reverse

import eos_auth_monitor
from eos_auth_monitor import progress
from eos_auth_monitor.auth_hooks import AuthMonitorMenuItem
from eos_auth_monitor.checks import is_app_installed
from eos_auth_monitor.models import MonitorConfiguration, Snapshot
from eos_auth_monitor.permissions import APP_PERMISSIONS, BASIC_ACCESS, MANAGE_SETTINGS, VIEW_ALL

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

    def test_should_show_the_cockpit_and_one_tile_per_corporation(self):
        response = self.get(self.leader, "index")

        url = reverse("eos_auth_monitor:service", args=["discord"])
        self.assertContains(response, f'href="{url}" class="stretched-link" aria-label="Discord"')
        self.assertContains(response, "50&nbsp;%")
        for corporation_id in (2001, 2002):
            self.assertContains(response, reverse("eos_auth_monitor:corporation", args=[corporation_id]))

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
        self.assertNotContains(self.get(self.leader, "index"), 'fa-users fa-fw"></i> Characters')

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

    def test_should_mark_problem_characters_in_the_service_list(self):
        response = self.get(self.leader, "corporation_service", 2002, "discord")

        self.assertContains(response, "eos-auth-monitor-problem", count=1)
        self.assertContains(response, "not linked")

    def test_should_count_connections_across_the_alliance(self):
        response = self.get(self.leader, "index")

        self.assertContains(response, "Connections")

    def test_should_make_the_tables_sortable(self):
        for name, *args in [("account", 22), ("corporation_service", 2002, "discord"), ("service", "discord")]:
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

        # a character Auth does not know gets the card of a main, not a table row
        self.assertContains(response, '<h6 class="mb-1 text-truncate">Stranger</h6>', html=False)
        self.assertContains(response, 'class="badge text-bg-danger text-wrap">Not registered in Auth</span>')
        self.assertNotContains(response, "eos-auth-monitor-sortable")
        self.assertContains(response, "Visitor main")
        self.assertContains(response, "Visitor alt")
        self.assertContains(response, "Registered in Auth")

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
