from allianceauth import hooks

from eos_auth_monitor.models import AccountProblemsFilter, Snapshot

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


class TestAccountProblemsFilter(MonitorTestCase):
    def setUp(self):
        super().setUp()
        self.fine = make_user("fine")
        self.broken = make_user("broken")
        self.outside = make_user("outside")
        store_snapshot(
            snapshot_data(
                [
                    corporation_row(2001, [account_row(self.fine.pk, 101)], problems=[NO_OWNER]),
                    corporation_row(
                        2002, [account_row(self.broken.pk, 201, [character_row(201, [AUDIT_MISSING])])]
                    ),
                ]
            )
        )

    def audit(self, **options):
        smart_filter = AccountProblemsFilter.objects.create(name="Monitor", description="test", **options)
        return smart_filter.audit_filter([self.fine, self.broken, self.outside])

    def test_should_pass_accounts_without_problems(self):
        result = self.audit()

        self.assertEqual(result[self.fine.pk], {"message": "No problems", "check": True})
        self.assertEqual(result[self.broken.pk], {"message": "Audit missing", "check": False})

    def test_should_pass_accounts_with_problems_when_reversed(self):
        result = self.audit(reversed_logic=True)

        self.assertFalse(result[self.fine.pk]["check"])
        self.assertTrue(result[self.broken.pk]["check"])

    def test_should_count_the_corporation_when_asked(self):
        result = self.audit(include_corporation=True)

        self.assertEqual(result[self.fine.pk], {"message": "No structure owner", "check": False})

    def test_should_fail_accounts_outside_the_overview_either_way(self):
        self.assertFalse(self.audit()[self.outside.pk]["check"])
        self.assertFalse(self.audit(reversed_logic=True)[self.outside.pk]["check"])

    def test_should_fail_everyone_without_a_snapshot(self):
        Snapshot.objects.all().delete()

        self.assertFalse(self.audit()[self.fine.pk]["check"])

    def test_should_answer_for_a_single_user(self):
        smart_filter = AccountProblemsFilter.objects.create(name="Monitor", description="test")

        self.assertTrue(smart_filter.process_filter(self.fine))
        self.assertFalse(smart_filter.process_filter(self.broken))

    def test_should_be_offered_to_securegroups(self):
        offered = [model for hook in hooks.get_hooks("secure_group_filters") for model in hook()]

        self.assertIn(AccountProblemsFilter, offered)
