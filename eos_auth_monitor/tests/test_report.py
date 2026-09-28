from eos_auth_monitor.report import Report, describe

from .base import MonitorTestCase, account_row, character_row, corporation_row, snapshot_data, store_snapshot

AUDIT_MISSING = {"check": "char_audit_missing", "detail": []}
SCOPES_MISSING = {"check": "char_scopes_missing", "detail": ["a", "b"]}
CORP_TOKEN_MISSING = {"check": "corp_token_missing", "detail": []}
NO_OWNER = {"check": "structures_no_owner", "detail": []}


def report(corporations, **kwargs):
    return Report(store_snapshot(snapshot_data(corporations, **kwargs)))


class TestDescribe(MonitorTestCase):
    def test_should_join_the_detail(self):
        self.assertEqual(describe(SCOPES_MISSING), "a, b")

    def test_should_say_when_corporation_data_never_updated(self):
        self.assertEqual(describe({"check": "corp_data_stale", "detail": []}), "never updated")


class TestAccounts(MonitorTestCase):
    def test_should_name_each_failed_check_once(self):
        account = account_row(
            1,
            101,
            characters=[
                character_row(101, [SCOPES_MISSING]),
                character_row(102, [AUDIT_MISSING, SCOPES_MISSING]),
            ],
        )
        _, found = report([corporation_row(2001, [account])]).account(1)

        # in check order, not in the order the characters had them
        self.assertEqual([check.key for check in found.keywords], ["char_audit_missing", "char_scopes_missing"])
        self.assertTrue(found.characters[0].is_main)

    def test_should_put_accounts_with_problems_first(self):
        fine = account_row(1, 101)
        broken = account_row(2, 201, characters=[character_row(201, [AUDIT_MISSING])])
        corporation = report([corporation_row(2001, [fine, broken])]).corporation(2001)

        self.assertEqual([account.user_id for account in corporation.accounts_by_problems], [2, 1])
        self.assertEqual([account.user_id for account in corporation.problem_accounts], [2])

    def test_should_ignore_checks_an_old_snapshot_knows_but_this_release_not(self):
        account = account_row(1, 101, characters=[character_row(101, [{"check": "gone", "detail": []}])])
        _, found = report([corporation_row(2001, [account])]).account(1)

        self.assertFalse(found.has_problems)


class TestCockpit(MonitorTestCase):
    def gauges(self, corporations, **kwargs):
        return {str(gauge.label): (gauge.part, gauge.total, gauge.percent) for gauge in report(corporations, **kwargs).cockpit()}

    def test_should_count_linked_mains_per_service(self):
        corporations = [
            corporation_row(2001, [account_row(1, 101, services={"discord": True}), account_row(2, 201)]),
            corporation_row(2002, [account_row(3, 301, services={"discord": True})]),
        ]

        self.assertEqual(self.gauges(corporations, services=["discord"])["Discord"], (2, 3, 67))

    def test_should_count_complete_characters(self):
        account = account_row(1, 101, characters=[character_row(101), character_row(102, [AUDIT_MISSING])])

        gauges = self.gauges([corporation_row(2001, [account])], checks=["char_audit_missing"])

        self.assertEqual(gauges["Character Audit complete"], (1, 2, 50))

    def test_should_count_working_corporations_per_app(self):
        corporations = [
            corporation_row(2001, problems=[CORP_TOKEN_MISSING]),
            corporation_row(2002, problems=[NO_OWNER]),
            corporation_row(2003),
            corporation_row(2004),
        ]

        gauges = self.gauges(corporations, checks=["corp_token_missing", "structures_no_owner"])

        self.assertEqual(gauges["Corporation Audit working"], (3, 4, 75))
        self.assertEqual(gauges["Structures working"], (3, 4, 75))

    def test_should_count_registered_members_where_the_list_is_known(self):
        corporations = [
            {**corporation_row(2001), "member_count": 4, "unregistered": [{"id": 1, "name": "x"}]},
            {**corporation_row(2002), "member_count": None},
        ]

        self.assertEqual(self.gauges(corporations)["Members registered"], (3, 4, 75))

    def test_should_count_connections_per_service(self):
        corporations = [
            corporation_row(2001, [account_row(1, 101, services={"discord": True, "qq": True}), account_row(2, 201)]),
        ]

        connections = report(corporations, services=["discord", "qq"]).connections()

        self.assertEqual([(service.key, linked) for service, linked in connections], [("discord", 1), ("qq", 1)])

    def test_should_show_only_gauges_of_checks_that_ran(self):
        self.assertEqual(self.gauges([corporation_row(2001)]), {})

    def test_should_have_no_percentage_without_anything_to_count(self):
        gauges = self.gauges([corporation_row(2001)], services=["discord"])

        self.assertEqual(gauges["Discord"], (0, 0, None))


class TestTileRows(MonitorTestCase):
    def rows(self, row, **kwargs):
        corporation = report([row], **kwargs).corporations[0]
        return {str(item.label): (item.part, item.total, item.percent) for item in corporation.rows}

    def test_should_list_each_app_with_its_share(self):
        account = account_row(
            1, 101, characters=[character_row(101), character_row(102, [AUDIT_MISSING])], services={"discord": True}
        )
        row = {**corporation_row(2001, [account], problems=[NO_OWNER]), "member_count": 3, "unregistered": []}

        rows = self.rows(
            row, checks=["char_audit_missing", "corp_token_missing", "structures_no_owner"], services=["discord"]
        )

        self.assertEqual(
            rows,
            {
                "Registered in Auth": (3, 3, 100),
                "Character Audit": (1, 2, 50),
                "Corporation Audit": (None, None, 100),
                "Structures": (None, None, 0),
                "Discord": (1, 1, 100),
            },
        )

    def test_should_leave_out_what_did_not_run(self):
        self.assertEqual(self.rows(corporation_row(2001)), {})
