from unittest.mock import patch

from django.test import RequestFactory
from django.urls import reverse

import eos_auth_monitor
from eos_auth_monitor import progress
from eos_auth_monitor.auth_hooks import AuthMonitorMenuItem
from eos_auth_monitor.models import MonitorConfiguration
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

        self.assertContains(response, reverse("eos_auth_monitor:service", args=["discord"]))
        self.assertContains(response, "50&nbsp;%")
        for corporation_id in (2001, 2002):
            self.assertContains(response, reverse("eos_auth_monitor:corporation", args=[corporation_id]))

    def test_should_name_the_problems_of_a_main(self):
        response = self.get(self.leader, "corporation", 2002)

        self.assertContains(response, reverse("eos_auth_monitor:account", args=[22]))
        self.assertContains(response, "Audit missing")

    def test_should_show_every_character_of_an_account(self):
        response = self.get(self.leader, "account", 22)

        self.assertContains(response, "Char 2201")
        self.assertContains(response, "The character has no corptools Character Audit.")

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

        self.assertContains(response, "Stranger")
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
        # aa-structures is not installed here
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
