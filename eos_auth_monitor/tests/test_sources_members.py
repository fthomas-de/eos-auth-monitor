from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from corptools.models import CharacterAudit, CharacterRoles

from eos_auth_monitor.sources import members

from .base import MonitorTestCase, make_token, make_user

SCOPE = members.MEMBERSHIP_SCOPE


class TestCorporationMembers(MonitorTestCase):
    def setUp(self):
        super().setUp()
        self.client_mock = MagicMock()
        patcher = patch("eos_auth_monitor.sources.members._client", return_value=self.client_mock)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.operation = self.client_mock.Corporation.GetCorporationsCorporationIdMembers

    def test_should_read_the_list_with_a_token_of_a_member(self):
        member = make_user("member", corporation_id=2001).profile.main_character
        token = make_token(member, [SCOPE])
        self.operation.return_value.result.return_value = [1, 2, 3]

        self.assertEqual(members.corporation_members(2001), [1, 2, 3])
        self.assertEqual(self.operation.call_args.kwargs, {"corporation_id": 2001, "token": token})

    def test_should_try_the_next_token_when_one_fails(self):
        first = make_user("first", corporation_id=2001).profile.main_character
        second = make_user("second", corporation_id=2001).profile.main_character
        make_token(first, [SCOPE])
        make_token(second, [SCOPE])
        self.operation.return_value.result.side_effect = [RuntimeError("403"), [7]]

        self.assertEqual(members.corporation_members(2001), [7])

    def test_should_give_none_without_a_usable_token(self):
        member = make_user("member", corporation_id=2001).profile.main_character
        make_token(member, ["publicData"])
        outsider = make_user("outsider", corporation_id=2002).profile.main_character
        make_token(outsider, [SCOPE])

        self.assertIsNone(members.corporation_members(2001))
        self.operation.assert_not_called()


class TestCorporationDirectors(MonitorTestCase):
    def setUp(self):
        super().setUp()
        self.client_mock = MagicMock()
        patcher = patch("eos_auth_monitor.sources.members._client", return_value=self.client_mock)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.operation = self.client_mock.Corporation.GetCorporationsCorporationIdRoles
        self.director = make_user("director", corporation_id=2001).profile.main_character
        audit = CharacterAudit.objects.create(character=self.director, update_timestamps={})
        CharacterRoles.objects.create(character=audit, director=True)

    def test_should_name_every_character_with_the_director_role(self):
        token = make_token(self.director, [SCOPE])
        self.operation.return_value.result.return_value = [
            SimpleNamespace(character_id=11, roles=["Director", "Accountant"]),
            SimpleNamespace(character_id=12, roles=["Accountant"]),
            SimpleNamespace(character_id=13, roles=[]),
        ]

        self.assertEqual(members.corporation_directors(2001), {11})
        self.assertEqual(self.operation.call_args.kwargs, {"corporation_id": 2001, "token": token})

    def test_should_read_role_enums_by_their_value(self):
        make_token(self.director, [SCOPE])
        self.operation.return_value.result.return_value = [
            SimpleNamespace(character_id=11, roles=[SimpleNamespace(value="Director")]),
        ]

        self.assertEqual(members.corporation_directors(2001), {11})

    def test_should_only_use_the_token_of_a_character_corptools_knows_as_director(self):
        # corptools has read this one's roles: no Director
        member = make_user("member", corporation_id=2001).profile.main_character
        audit = CharacterAudit.objects.create(character=member, update_timestamps={})
        CharacterRoles.objects.create(character=audit, director=False)
        make_token(member, [SCOPE])

        self.assertIsNone(members.corporation_directors(2001))
        self.operation.assert_not_called()

    def test_should_need_the_membership_scope(self):
        make_token(self.director, ["publicData"])

        self.assertIsNone(members.corporation_directors(2001))
        self.operation.assert_not_called()

    def test_should_try_the_next_token_when_one_fails(self):
        second = make_user("second", corporation_id=2001).profile.main_character
        audit = CharacterAudit.objects.create(character=second, update_timestamps={})
        CharacterRoles.objects.create(character=audit, director=True)
        make_token(self.director, [SCOPE])
        make_token(second, [SCOPE])
        self.operation.return_value.result.side_effect = [RuntimeError("403"), [SimpleNamespace(character_id=5, roles=["Director"])]]

        self.assertEqual(members.corporation_directors(2001), {5})


class TestNames(MonitorTestCase):
    def test_should_ask_esi_only_for_characters_auth_does_not_know(self):
        known = make_user("known").profile.main_character
        client = MagicMock()
        client.Universe.PostUniverseNames.return_value.result.return_value = [SimpleNamespace(id=5, name="Stranger")]
        with patch("eos_auth_monitor.sources.members._client", return_value=client):
            result = members.names([known.character_id, 5])

        self.assertEqual(result, {known.character_id: known.character_name, 5: "Stranger"})
        self.assertEqual(client.Universe.PostUniverseNames.call_args.kwargs, {"body": [5]})

    def test_should_keep_going_when_esi_fails(self):
        client = MagicMock()
        client.Universe.PostUniverseNames.return_value.result.side_effect = RuntimeError("down")
        with patch("eos_auth_monitor.sources.members._client", return_value=client):
            self.assertEqual(members.names([5]), {})
