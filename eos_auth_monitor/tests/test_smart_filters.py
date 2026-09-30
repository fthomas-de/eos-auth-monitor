from allianceauth import hooks

from eos_auth_monitor.models import CharacterProblemsFilter, Snapshot

from .base import (
    MonitorTestCase,
    account_row,
    character_row,
    corporation_row,
    make_user,
    snapshot_data,
    store_snapshot,
)

AUDIT_MISSING = {"check": "char_audit_missing", "detail": []}
NO_OWNER = {"check": "structures_no_owner", "detail": []}


class TestCharacterProblemsFilter(MonitorTestCase):
    def setUp(self):
        super().setUp()
        self.fine = make_user("fine")
        self.broken = make_user("broken")
        self.outside = make_user("outside")
        store_snapshot(
            snapshot_data(
                [
                    # the Corporation's own problem is not the character's
                    corporation_row(2001, [account_row(self.fine.pk, 101)], problems=[NO_OWNER]),
                    corporation_row(
                        2002,
                        [
                            account_row(
                                self.broken.pk,
                                201,
                                # the main is fine, its alt in the other Corporation is not
                                [character_row(201, corporation_id=2002), character_row(202, [AUDIT_MISSING])],
                                corporation_id=2002,
                            )
                        ],
                    ),
                ],
                checks=["char_audit_missing", "structures_no_owner"],
            )
        )

    def audit(self, **options):
        smart_filter = CharacterProblemsFilter.objects.create(name="Monitor", description="test", **options)
        return smart_filter.audit_filter([self.fine, self.broken, self.outside])

    def test_should_pass_accounts_without_character_problems(self):
        result = self.audit()

        self.assertEqual(result[self.fine.pk], {"message": "No problems", "check": True})
        self.assertEqual(result[self.broken.pk], {"message": "Audit missing", "check": False})

    def test_should_pass_accounts_with_character_problems_when_reversed(self):
        result = self.audit(reversed_logic=True)

        self.assertFalse(result[self.fine.pk]["check"])
        self.assertTrue(result[self.broken.pk]["check"])

    def test_should_fail_accounts_outside_the_overview_either_way(self):
        for reversed_logic in (False, True):
            with self.subTest(reversed_logic=reversed_logic):
                result = self.audit(reversed_logic=reversed_logic)[self.outside.pk]

                self.assertEqual(result, {"message": "Not in the Auth Monitor overview", "check": False})

    def test_should_fail_everyone_without_a_snapshot(self):
        Snapshot.objects.all().delete()

        for reversed_logic in (False, True):
            with self.subTest(reversed_logic=reversed_logic):
                result = self.audit(reversed_logic=reversed_logic)

                self.assertEqual(result[self.fine.pk], {"message": "No Auth Monitor result yet", "check": False})
                self.assertFalse(result[self.broken.pk]["check"])

    def test_should_answer_for_a_single_user(self):
        smart_filter = CharacterProblemsFilter.objects.create(name="Monitor", description="test")

        self.assertTrue(smart_filter.process_filter(self.fine))
        self.assertFalse(smart_filter.process_filter(self.broken))
        self.assertFalse(smart_filter.process_filter(self.outside))

    def test_should_be_offered_to_securegroups(self):
        offered = [model for hook in hooks.get_hooks("secure_group_filters") for model in hook()]

        self.assertIn(CharacterProblemsFilter, offered)
