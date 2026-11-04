"""aa-structures and the service apps are not installed in the test instance;
their models are stood in for by fakes that answer the same queries."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from unittest import skipUnless

from django.apps import apps
from django.test import SimpleTestCase

from eos_auth_monitor.sources import services, spy_network, structures

from .base import MonitorTestCase, make_user

STRUCTURES_KEYS = {
    "structures_no_owner",
    "structures_owner_inactive",
    "structures_no_character",
    "structures_sync_failing",
}


def fake_owner(corporation_id, is_active=True, characters=1, **syncs):
    fresh = {attribute: syncs.get(attribute, True) for _, attribute in structures.SYNCS}
    owner = SimpleNamespace(
        corporation=SimpleNamespace(corporation_id=corporation_id),
        is_active=is_active,
        are_all_syncs_ok=all(fresh.values()),
        characters=MagicMock(),
        **fresh,
    )
    owner.characters.filter.return_value.exists.return_value = characters > 0
    return owner


class TestStructures(SimpleTestCase):
    def problems(self, *owners, keys=STRUCTURES_KEYS):
        model = MagicMock()
        model.objects.filter.return_value.select_related.return_value = list(owners)
        with patch("eos_auth_monitor.sources.structures.apps.get_model", return_value=model) as get_model:
            result = structures.corporation_problems([2001], keys)
        get_model.assert_called_once_with("structures", "Owner")
        return result.get(2001, [])

    def checks(self, *owners, **kwargs):
        return [item["check"] for item in self.problems(*owners, **kwargs)]

    def test_should_pass_a_working_owner(self):
        self.assertEqual(self.problems(fake_owner(2001)), [])

    def test_should_report_a_missing_owner(self):
        self.assertEqual(self.checks(fake_owner(2002)), ["structures_no_owner"])

    def test_should_report_only_that_an_owner_is_inactive(self):
        owner = fake_owner(2001, is_active=False, characters=0, is_assets_sync_fresh=False)

        self.assertEqual(self.checks(owner), ["structures_owner_inactive"])

    def test_should_report_an_owner_without_enabled_characters(self):
        self.assertEqual(self.checks(fake_owner(2001, characters=0)), ["structures_no_character"])

    def test_should_name_the_failing_syncs(self):
        owner = fake_owner(2001, is_notification_sync_fresh=False, is_assets_sync_fresh=False)

        self.assertEqual(
            self.problems(owner),
            [{"check": "structures_sync_failing", "detail": ["Notifications", "Assets"]}],
        )

    def test_should_skip_checks_that_are_switched_off(self):
        owner = fake_owner(2001, characters=0, is_assets_sync_fresh=False)

        self.assertEqual(self.checks(owner, keys={"structures_sync_failing"}), ["structures_sync_failing"])
        self.assertEqual(self.checks(fake_owner(2002), keys={"structures_sync_failing"}), [])

    def test_should_group_the_enabled_owner_characters_by_corporation(self):
        model = MagicMock()
        model.objects.filter.return_value.values_list.return_value = [(2001, 11), (2001, 12), (2002, 21)]
        with patch("eos_auth_monitor.sources.structures.apps.get_model", return_value=model) as get_model:
            result = structures.owner_characters([2001, 2002])

        get_model.assert_called_once_with("structures", "OwnerCharacter")
        self.assertEqual(
            model.objects.filter.call_args.kwargs,
            {"owner__corporation__corporation_id__in": [2001, 2002], "is_enabled": True},
        )
        self.assertEqual(result, {2001: {11, 12}, 2002: {21}})


class TestServices(SimpleTestCase):
    def linked(self, service_key):
        model = MagicMock()
        model.objects.filter.return_value.values_list.return_value = [7, 8]
        users = object()
        with patch("eos_auth_monitor.sources.services.apps.get_model", return_value=model) as get_model:
            result = services.linked_user_ids(service_key, users)
        return result, get_model.call_args.args, model.objects.filter.call_args.kwargs, users

    def test_should_read_each_service_from_its_app(self):
        expected = {
            "discord": ("discord", "DiscordUser"),
            "mumble": ("mumble", "MumbleUser"),
            "qq": ("qqbot", "Binding"),
            "telegram": ("aa_discord_telegram_bridge", "TelegramUser"),
        }
        for service_key, model in expected.items():
            with self.subTest(service_key):
                result, args, _, _ = self.linked(service_key)

                self.assertEqual(result, {7, 8})
                self.assertEqual(args, model)

    def test_should_limit_to_the_given_users(self):
        _, _, filters, users = self.linked("discord")

        self.assertIs(filters["user__in"], users)

    def test_should_count_telegram_only_once_the_link_is_done(self):
        _, _, filters, _ = self.linked("telegram")

        self.assertEqual(filters["telegram_user_id__isnull"], False)


SPY_INSTALLED = apps.is_installed("eos_spy_network")
VIEW_SUSPECTS = "eos_spy_network.view_suspects"
VIEW_EVIDENCE = "eos_spy_network.view_evidence"


def fake_spy_api(found):
    return SimpleNamespace(
        KINDS=("membership", "mails", "wallet"),
        label=lambda kind: f"Label {kind}",
        description=lambda kind: f"Description {kind}",
        character_markers=lambda: found,
    )


class TestSpyNetworkReader(SimpleTestCase):
    def test_should_turn_the_kinds_into_markers_in_the_apps_order(self):
        api = fake_spy_api({9001: ["membership", "wallet"], 9002: ["mails", "gone"]})
        with patch.object(spy_network, "is_installed", return_value=True), patch.object(
            spy_network, "_api", return_value=api
        ):
            found = spy_network.character_markers()
            kinds = spy_network.kinds()

        self.assertEqual(kinds, ("membership", "mails", "wallet"))
        self.assertEqual(
            found,
            {
                9001: [
                    spy_network.SpyMarker("membership", "Label membership", "Description membership"),
                    spy_network.SpyMarker("wallet", "Label wallet", "Description wallet"),
                ],
                # a kind a later release dropped is left out
                9002: [spy_network.SpyMarker("mails", "Label mails", "Description mails")],
            },
        )

    def test_should_read_nothing_without_the_app(self):
        with patch.object(spy_network, "is_installed", return_value=False), patch.object(
            spy_network, "_api", side_effect=AssertionError("imported")
        ):
            self.assertEqual(spy_network.character_markers(), {})
            self.assertEqual(spy_network.kinds(), ())


class TestSpyNetworkPermissions(MonitorTestCase):
    def test_should_not_show_anything_without_the_app(self):
        user = make_user("nobody")
        with patch.object(spy_network, "is_installed", return_value=False):
            self.assertFalse(spy_network.can_view(user))

    @skipUnless(SPY_INSTALLED, "eos-spy-network is not installed")
    def test_should_ignore_a_release_without_the_read_api(self):
        import sys

        import eos_spy_network

        user = make_user("both", VIEW_SUSPECTS, VIEW_EVIDENCE)
        real = sys.modules.get("eos_spy_network.api")
        # before 0.0.10: no module at all - the import must fail, not reuse the loaded one
        with patch.dict(sys.modules, {"eos_spy_network.api": None}):
            had = hasattr(eos_spy_network, "api")
            if had:
                delattr(eos_spy_network, "api")
            try:
                self.assertFalse(spy_network.is_installed())
                self.assertFalse(spy_network.can_view(user))
                self.assertEqual(spy_network.character_markers(), {})
            finally:
                if had:
                    eos_spy_network.api = real
        # a module that lacks a part of the contract counts as missing as well
        with patch.dict(sys.modules, {"eos_spy_network.api": SimpleNamespace(KINDS=())}):
            had = hasattr(eos_spy_network, "api")
            if had:
                delattr(eos_spy_network, "api")
            try:
                self.assertFalse(spy_network.can_view(user))
            finally:
                if had:
                    eos_spy_network.api = real
        self.assertTrue(spy_network.can_view(user))

    @skipUnless(SPY_INSTALLED, "eos-spy-network is not installed")
    def test_should_need_both_view_permissions(self):
        self.assertTrue(spy_network.can_view(make_user("both", VIEW_SUSPECTS, VIEW_EVIDENCE)))
        self.assertFalse(spy_network.can_view(make_user("suspects", VIEW_SUSPECTS)))
        self.assertFalse(spy_network.can_view(make_user("evidence", VIEW_EVIDENCE)))
