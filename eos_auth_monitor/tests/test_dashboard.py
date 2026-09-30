from django.test import RequestFactory
from django.urls import reverse

from allianceauth.hooks import get_hooks
from allianceauth.tests.auth_utils import AuthUtils

from eos_auth_monitor import auth_hooks
from eos_auth_monitor.models import Snapshot
from eos_auth_monitor.permissions import BASIC_ACCESS, VIEW_ALL, VIEW_OWN
from eos_auth_monitor.views import dashboard_corporation, dashboard_own

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

AUDIT_MISSING = {"check": "char_audit_missing", "detail": []}
SCOPES_MISSING = {"check": "char_scopes_missing", "detail": ["esi-skills.read_skills.v1"]}


def render(widget, user):
    request = RequestFactory().get("/")
    request.user = user
    return widget(request)


class DashboardTestCase(MonitorTestCase):
    """Corporation 2001 with a member whose main and alt fail checks; 2002 without problems."""

    def setUp(self):
        super().setUp()
        configure()
        self.member = make_user("member", VIEW_OWN, corporation_id=2001)
        self.ceo = make_user("ceo", BASIC_ACCESS, corporation_id=2001)
        main_id = self.member.profile.main_character.character_id
        store_snapshot(
            snapshot_data(
                [
                    corporation_row(
                        2001,
                        [
                            account_row(
                                self.member.pk,
                                main_id,
                                [
                                    character_row(main_id, [AUDIT_MISSING, SCOPES_MISSING]),
                                    character_row(9901, [AUDIT_MISSING]),
                                    character_row(9902),
                                ],
                                {"discord": True},
                            ),
                            account_row(33, 3301, [character_row(3301, [AUDIT_MISSING])], {}),
                        ],
                    ),
                    corporation_row(2002, [account_row(44, 4401, corporation_id=2002)]),
                ],
                checks=["char_audit_missing", "char_scopes_missing"],
                services=["discord"],
            )
        )
        self.snapshot = Snapshot.objects.get()
        self.snapshot.data["corporations"][0]["member_count"] = 4
        self.snapshot.data["corporations"][0]["unregistered"] = [{"id": 7001, "name": "Stranger A"}]
        self.snapshot.save()


class TestHooks(MonitorTestCase):
    def test_should_put_both_widgets_where_eos_invoices_has_its_own(self):
        ours = [hook() for hook in get_hooks("dashboard_hook") if hook.__module__ == auth_hooks.__name__]

        self.assertEqual([item.view_function for item in ours], [dashboard_own, dashboard_corporation])
        self.assertEqual({item.order for item in ours}, {4})


class TestOwnWidget(DashboardTestCase):
    def test_should_show_the_own_problems_in_short(self):
        html = render(dashboard_own, self.member)

        self.assertIn('id="eos-auth-monitor-dashboard-own"', html)
        self.assertIn(f"Char {self.member.profile.main_character.character_id}", html)
        # each failed check once, with the number of characters failing it
        self.assertRegex(html, r"Audit missing</span>\s*<span[^>]*>\s*2 characters")
        self.assertRegex(html, r"Scopes missing</span>\s*<span[^>]*>\s*1 character\s*<")
        self.assertIn("border-danger", html)
        # none of the other accounts of the Corporation
        self.assertNotIn("Char 3301", html)

    def test_should_show_which_services_are_linked(self):
        self.assertIn("Discord: linked", render(dashboard_own, self.member))

    def test_should_link_to_my_account(self):
        self.assertIn(f'href="{reverse("eos_auth_monitor:own_account")}"', render(dashboard_own, self.member))

    def test_should_be_named_after_my_account(self):
        self.assertRegex(render(dashboard_own, self.member), r"<h4[^>]*>\s*My account\s*</h4>")

    def test_should_say_when_there_is_no_problem(self):
        fine = make_user("fine", VIEW_OWN, corporation_id=2002)
        self.snapshot.data["corporations"][1]["accounts"].append(
            account_row(fine.pk, fine.profile.main_character.character_id, corporation_id=2002)
        )
        self.snapshot.save()

        html = render(dashboard_own, fine)

        self.assertIn("No character of this account has a problem.", html)
        self.assertNotIn("border-danger", html)

    def test_should_need_view_own(self):
        # in the snapshot, so only the missing permission can hide the widget
        main_id = self.ceo.profile.main_character.character_id
        self.snapshot.data["corporations"][0]["accounts"].append(
            account_row(self.ceo.pk, main_id, [character_row(8801, [AUDIT_MISSING])])
        )
        self.snapshot.save()

        self.assertEqual(render(dashboard_own, self.ceo), "")

    def test_should_hide_an_account_outside_the_overview(self):
        outsider = make_user("outsider", VIEW_OWN, corporation_id=2999)

        self.assertEqual(render(dashboard_own, outsider), "")

    def test_should_hide_without_a_snapshot(self):
        Snapshot.objects.all().delete()

        self.assertEqual(render(dashboard_own, self.member), "")


class TestCorporationWidget(DashboardTestCase):
    def test_should_show_the_to_do_groups_of_the_own_corporation(self):
        html = render(dashboard_corporation, self.ceo)

        self.assertIn('id="eos-auth-monitor-dashboard-corporation"', html)
        self.assertIn("Corp 2001", html)
        # mains per failed check, as on the Corporation page
        self.assertRegex(html, r"Audit missing</span>\s*<span[^>]*>Mains: 2<")
        self.assertRegex(html, r"Scopes missing</span>\s*<span[^>]*>Mains: 1<")
        self.assertRegex(html, r"Not registered in Auth</span>\s*<span[^>]*>Characters: 1<")
        # counts only, no names
        self.assertNotIn("Char 3301", html)
        self.assertNotIn("Stranger A", html)

    def test_should_be_named_after_my_corporation(self):
        self.assertRegex(render(dashboard_corporation, self.ceo), r"<h4[^>]*>\s*My Corporation\s*</h4>")

    def test_should_show_the_problems_of_the_corporation_itself(self):
        self.snapshot.data["corporations"][0]["problems"] = [{"check": "corp_audit_missing", "detail": []}]
        self.snapshot.save()

        self.assertIn("text-bg-warning", render(dashboard_corporation, self.ceo))

    def test_should_link_to_the_own_corporation(self):
        html = render(dashboard_corporation, self.ceo)

        self.assertIn(f'href="{reverse("eos_auth_monitor:corporation", args=[2001])}"', html)

    def test_should_say_when_there_is_nothing_to_do(self):
        ceo = make_user("ceo2", BASIC_ACCESS, corporation_id=2002)

        html = render(dashboard_corporation, ceo)

        self.assertIn("Nothing to do.", html)
        self.assertNotIn("border-danger", html)

    def test_should_need_basic_access(self):
        self.assertEqual(render(dashboard_corporation, self.member), "")
        self.assertEqual(render(dashboard_corporation, make_user("leader", VIEW_ALL, corporation_id=2001)), "")

    def test_should_hide_a_corporation_outside_the_overview(self):
        outsider = make_user("outsider", BASIC_ACCESS, corporation_id=2999)

        self.assertEqual(render(dashboard_corporation, outsider), "")

    def test_should_hide_without_a_snapshot(self):
        Snapshot.objects.all().delete()

        self.assertEqual(render(dashboard_corporation, self.ceo), "")


class TestDashboardPage(DashboardTestCase):
    def test_should_show_both_widgets_on_alliance_auths_dashboard(self):
        # the member of the snapshot, as their Corporation's CEO as well
        AuthUtils.add_permissions_to_user_by_name([BASIC_ACCESS], self.member)
        self.client.force_login(self.member)

        content = self.client.get(reverse("authentication:dashboard")).content.decode()

        self.assertLess(
            content.index("eos-auth-monitor-dashboard-own"), content.index("eos-auth-monitor-dashboard-corporation")
        )
