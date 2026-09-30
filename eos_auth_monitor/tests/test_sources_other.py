"""aa-structures and the service apps are not installed in the test instance;
their models are stood in for by fakes that answer the same queries."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from eos_auth_monitor.sources import services, structures

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
