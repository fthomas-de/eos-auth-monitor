import datetime
from unittest.mock import patch

from corptools import app_settings
from corptools.models import CharacterAudit, CharacterRoles, CorporationAudit, CorptoolsConfiguration

from django.utils import timezone

from allianceauth.eveonline.models import EveCharacter

from eos_auth_monitor.sources import corptools

from .base import MonitorTestCase, add_alt, make_corporation, make_token, make_user

CHARACTER_KEYS = {"char_audit_missing", "char_scopes_missing", "char_audit_inactive"}
DIRECTOR_KEY = "char_director_token_missing"
CORPORATION_KEYS = {"corp_audit_missing", "corp_token_missing", "corp_data_stale"}
# fixed, so the tests do not depend on which corptools modules this instance runs
SECTIONS = ["assets", "skills"]


def ago(days):
    return (timezone.now() - datetime.timedelta(days=days)).isoformat()


def fresh():
    return {key: ago(0) for key in SECTIONS}


@patch("eos_auth_monitor.sources.corptools.character_sections", return_value=SECTIONS)
class TestCharacterProblems(MonitorTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("pilot")
        self.main = self.user.profile.main_character
        self.scopes = corptools.character_scopes()

    def problems(self, keys=CHARACTER_KEYS, **excluded):
        ids = EveCharacter.objects.filter(character_id=self.main.character_id).values_list("character_id", flat=True)
        return corptools.character_problems(ids, keys, **excluded).get(self.main.character_id, [])

    def checks(self, keys=CHARACTER_KEYS):
        return [item["check"] for item in self.problems(keys)]

    def test_should_pass_a_complete_character(self, _):
        CharacterAudit.objects.create(character=self.main, update_timestamps=fresh())
        make_token(self.main, self.scopes)

        self.assertEqual(self.problems(), [])

    def test_should_report_a_missing_audit(self, _):
        make_token(self.main, self.scopes)

        self.assertEqual(self.checks(), ["char_audit_missing"])

    def test_should_name_the_stale_and_the_never_updated_sections(self, _):
        CharacterAudit.objects.create(character=self.main, update_timestamps={"assets": ago(30)})
        make_token(self.main, self.scopes)

        self.assertEqual(self.problems(), [{"check": "char_audit_inactive", "detail": ["Assets", "Skills"]}])

    def test_should_not_count_a_section_corptools_does_not_count(self, _):
        CharacterAudit.objects.create(character=self.main, update_timestamps={**fresh(), "mails": ago(30)})
        make_token(self.main, self.scopes)

        self.assertEqual(self.problems(), [])

    def test_should_leave_out_excluded_sections(self, _):
        CharacterAudit.objects.create(character=self.main, update_timestamps={"skills": ago(0), "assets": ago(30)})
        make_token(self.main, self.scopes)

        self.assertEqual(self.problems(excluded_sections=["assets"]), [])

    def test_should_not_write_to_corptools(self, _):
        # is_active() would save the audit; the stored flag must stay as it was
        audit = CharacterAudit.objects.create(character=self.main, active=True, update_timestamps={})
        make_token(self.main, self.scopes)

        self.assertEqual(self.checks(), ["char_audit_inactive"])
        audit.refresh_from_db()
        self.assertTrue(audit.active)

    def test_should_report_missing_scopes_of_the_best_token(self, _):
        CharacterAudit.objects.create(character=self.main, update_timestamps=fresh())
        make_token(self.main, self.scopes[:1])
        make_token(self.main, self.scopes[:-1])

        self.assertEqual(self.problems(), [{"check": "char_scopes_missing", "detail": self.scopes[-1:]}])

    def test_should_report_all_scopes_without_a_token(self, _):
        CharacterAudit.objects.create(character=self.main, update_timestamps=fresh())

        self.assertEqual(self.problems(), [{"check": "char_scopes_missing", "detail": self.scopes}])

    def test_should_leave_out_excluded_scopes(self, _):
        CharacterAudit.objects.create(character=self.main, update_timestamps=fresh())
        make_token(self.main, self.scopes[:-1])

        self.assertEqual(self.problems(excluded_scopes=self.scopes[-1:]), [])

    def director(self, director=True):
        audit = CharacterAudit.objects.create(character=self.main, update_timestamps=fresh())
        CharacterRoles.objects.create(character=audit, director=director)

    def test_should_report_a_director_without_a_corporation_token(self, _):
        self.director()
        make_token(self.main, self.scopes)

        problems = self.problems({DIRECTOR_KEY})

        self.assertEqual([item["check"] for item in problems], [DIRECTOR_KEY])
        # the character token already covers some of them; only the rest is named
        self.assertEqual(problems[0]["detail"], sorted(set(corptools.corporation_scopes()) - set(self.scopes)))

    def test_should_name_what_the_best_token_of_a_director_lacks(self, _):
        self.director()
        make_token(self.main, corptools.corporation_scopes()[:-1])

        self.assertEqual(
            self.problems({DIRECTOR_KEY}),
            [{"check": DIRECTOR_KEY, "detail": corptools.corporation_scopes()[-1:]}],
        )

    def test_should_pass_a_director_with_a_complete_corporation_token(self, _):
        self.director()
        make_token(self.main, corptools.corporation_scopes())

        self.assertEqual(self.problems({DIRECTOR_KEY}), [])

    def test_should_not_ask_a_character_that_is_no_director_for_a_corporation_token(self, _):
        self.director(director=False)
        make_token(self.main, self.scopes)

        self.assertEqual(self.problems({DIRECTOR_KEY}), [])

    def test_should_know_a_director_esi_named_although_corptools_never_read_the_roles(self, _):
        CharacterAudit.objects.create(character=self.main, update_timestamps=fresh())
        make_token(self.main, self.scopes)
        ids = EveCharacter.objects.filter(character_id=self.main.character_id).values_list("character_id", flat=True)

        found = corptools.character_problems(ids, {DIRECTOR_KEY}, esi_directors={self.main.character_id})

        self.assertEqual([item["check"] for item in found[self.main.character_id]], [DIRECTOR_KEY])

    def test_should_not_apply_esi_directors_when_the_check_is_off(self, _):
        ids = EveCharacter.objects.filter(character_id=self.main.character_id).values_list("character_id", flat=True)

        self.assertEqual(
            corptools.character_problems(ids, CHARACTER_KEYS - {DIRECTOR_KEY}, esi_directors={self.main.character_id}).get(
                self.main.character_id, []
            ),
            [{"check": "char_audit_missing", "detail": []}, {"check": "char_scopes_missing", "detail": self.scopes}],
        )

    def test_should_not_know_a_director_whose_roles_corptools_never_read(self, _):
        CharacterAudit.objects.create(character=self.main, update_timestamps=fresh())

        self.assertEqual(self.problems({DIRECTOR_KEY}), [])

    def test_should_leave_out_excluded_corporation_scopes_for_a_director(self, _):
        self.director()
        make_token(self.main, corptools.corporation_scopes()[:-1])

        self.assertEqual(
            self.problems({DIRECTOR_KEY}, excluded_corporation_scopes=corptools.corporation_scopes()[-1:]), []
        )

    def test_should_skip_the_director_check_when_it_is_switched_off(self, _):
        self.director()

        self.assertEqual(self.problems(CHARACTER_KEYS - {DIRECTOR_KEY}), [{"check": "char_scopes_missing", "detail": self.scopes}])

    def test_should_skip_checks_that_are_switched_off(self, _):
        self.assertEqual(self.checks({"char_scopes_missing"}), ["char_scopes_missing"])
        self.assertEqual(self.checks({"char_audit_missing"}), ["char_audit_missing"])

    def test_should_check_every_character_it_is_given(self, _):
        alt = add_alt(self.user, 9001, "Alt")
        CharacterAudit.objects.create(character=self.main, update_timestamps=fresh())
        make_token(self.main, self.scopes)

        ids = EveCharacter.objects.filter(character_id__in=[self.main.character_id, 9001]).values_list(
            "character_id", flat=True
        )
        result = corptools.character_problems(ids, CHARACTER_KEYS)

        self.assertEqual(sorted(result), [alt.character_id])


class TestCharacterSections(MonitorTestCase):
    """The sections follow the conditions of corptools' is_active()."""

    def sections(self, **settings):
        defaults = {"CT_CHAR_ASSETS_MODULE": True, "CT_CHAR_ACTIVE_IGNORE_ASSETS_MODULE": False}
        with patch.multiple(app_settings, **{**defaults, **settings}):
            return corptools.character_sections()

    def test_should_count_a_module_that_runs(self):
        self.assertIn("assets", self.sections())

    def test_should_not_count_a_module_that_is_off_or_ignored(self):
        self.assertNotIn("assets", self.sections(CT_CHAR_ASSETS_MODULE=False))
        self.assertNotIn("assets", self.sections(CT_CHAR_ACTIVE_IGNORE_ASSETS_MODULE=True))

    def test_should_not_count_a_module_switched_off_in_corptools(self):
        config = CorptoolsConfiguration.objects.first() or CorptoolsConfiguration.objects.create()
        config.disable_update_assets = True
        config.save()

        self.assertNotIn("assets", self.sections())


class TestCorporationProblems(MonitorTestCase):
    def setUp(self):
        super().setUp()
        self.corporation = make_corporation(2001)
        self.member = make_user("director", corporation_id=2001).profile.main_character
        self.scopes = corptools.corporation_scopes()

    def problems(self, keys=CORPORATION_KEYS, stale_after_days=3, **excluded):
        return corptools.corporation_problems([2001], keys, stale_after_days, **excluded).get(2001, [])

    def checks(self, **kwargs):
        return [item["check"] for item in self.problems(**kwargs)]

    def test_should_pass_a_working_corporation(self):
        CorporationAudit.objects.create(corporation=self.corporation, update_timestamps={"assets": ago(1)})
        make_token(self.member, self.scopes)

        self.assertEqual(self.problems(), [])

    def test_should_report_a_missing_audit_and_token(self):
        self.assertEqual(self.checks(), ["corp_audit_missing", "corp_token_missing"])

    def test_should_want_every_scope_on_one_token(self):
        CorporationAudit.objects.create(corporation=self.corporation, update_timestamps={"assets": ago(1)})
        make_token(self.member, self.scopes[:-1])
        make_token(self.member, self.scopes[-1:])

        self.assertEqual(self.checks(), ["corp_token_missing"])

    def test_should_leave_out_excluded_scopes(self):
        CorporationAudit.objects.create(corporation=self.corporation, update_timestamps={"assets": ago(1)})
        make_token(self.member, self.scopes[:-1])

        self.assertEqual(self.problems(excluded_scopes=self.scopes[-1:]), [])

    def test_should_not_count_a_token_of_another_corporation(self):
        CorporationAudit.objects.create(corporation=self.corporation, update_timestamps={"assets": ago(1)})
        outsider = make_user("outsider", corporation_id=2002).profile.main_character
        make_token(outsider, self.scopes)

        self.assertEqual(self.checks(), ["corp_token_missing"])

    def test_should_name_the_stale_sections(self):
        CorporationAudit.objects.create(
            corporation=self.corporation,
            update_timestamps={"assets": ago(10), "wallet": ago(1), "tracking": ago(10)},
        )
        make_token(self.member, self.scopes)

        self.assertEqual(self.problems(), [{"check": "corp_data_stale", "detail": ["Assets", "Tracking"]}])

    def test_should_leave_out_excluded_sections(self):
        CorporationAudit.objects.create(
            corporation=self.corporation, update_timestamps={"observers": ago(10), "assets": ago(1)}
        )
        make_token(self.member, self.scopes)

        self.assertEqual(self.checks(), ["corp_data_stale"])
        self.assertEqual(self.problems(excluded_sections=["observers"]), [])

    def test_should_follow_the_configured_limit(self):
        CorporationAudit.objects.create(corporation=self.corporation, update_timestamps={"assets": ago(10)})
        make_token(self.member, self.scopes)

        self.assertEqual(self.problems(stale_after_days=14), [])
        self.assertEqual(self.checks(stale_after_days=7), ["corp_data_stale"])

    def test_should_report_an_audit_that_never_updated(self):
        CorporationAudit.objects.create(corporation=self.corporation)
        make_token(self.member, self.scopes)

        self.assertEqual(self.problems(), [{"check": "corp_data_stale", "detail": []}])
