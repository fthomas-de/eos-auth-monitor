from esi.models import Scope, Token

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveAllianceInfo, EveCharacter, EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from eos_auth_monitor.models import MonitorConfiguration, Snapshot

ALLIANCE_ID = 3001
OTHER_ALLIANCE_ID = 3999


# django-solo keeps the configuration in the cache named by SOLO_CACHE, and
# the progress bar keeps its state in the default cache - on the dev instance
# both are its own Redis. The test transaction rolls back, the cache does
# not: what one test stored would leak into the next, and into the running
# instance. A cache in memory, emptied before every test, keeps them apart.
@override_settings(
    SOLO_CACHE=None,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "eos-auth-monitor"}},
)
class MonitorTestCase(TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()


def make_alliance(alliance_id=ALLIANCE_ID):
    alliance, _ = EveAllianceInfo.objects.get_or_create(
        alliance_id=alliance_id,
        defaults={
            "alliance_name": f"Alliance {alliance_id}",
            "alliance_ticker": f"A{alliance_id}",
        },
    )
    return alliance


def make_corporation(corporation_id, alliance_id=ALLIANCE_ID):
    alliance = make_alliance(alliance_id) if alliance_id else None
    corporation, _ = EveCorporationInfo.objects.get_or_create(
        corporation_id=corporation_id,
        defaults={
            "corporation_name": f"Corp {corporation_id}",
            "corporation_ticker": f"C{corporation_id}",
            "member_count": 1,
            "alliance": alliance,
        },
    )
    return corporation


def make_user(name, *perms, corporation_id=2001, alliance_id=ALLIANCE_ID):
    """A user with a main character; permissions as 'app.codename'."""
    user = AuthUtils.create_user(name)
    # Alliance Auth wraps every url_hook view in main_character_required:
    # without a main, a permitted user is sent to the dashboard as well
    main = AuthUtils.add_main_character_2(
        user,
        f"{name} main",
        character_id=user.pk + 1000,
        corp_id=corporation_id,
        corp_name=f"Corp {corporation_id}",
        corp_ticker=f"C{corporation_id}",
        alliance_id=alliance_id,
        alliance_name=f"Alliance {alliance_id}" if alliance_id else "",
    )
    # AuthUtils leaves the ownership out; a real account always has it
    CharacterOwnership.objects.create(user=user, character=main, owner_hash=f"hash-{main.character_id}")
    if perms:
        AuthUtils.add_permissions_to_user_by_name(list(perms), user)
    # has_perm caches on the instance; tests want the stored permissions
    return type(user).objects.get(pk=user.pk)


def add_alt(user, character_id, name, corporation_id=2001, alliance_id=ALLIANCE_ID):
    character = EveCharacter.objects.create(
        character_id=character_id,
        character_name=name,
        corporation_id=corporation_id,
        corporation_name=f"Corp {corporation_id}",
        corporation_ticker=f"C{corporation_id}",
        alliance_id=alliance_id,
        alliance_name=f"Alliance {alliance_id}" if alliance_id else "",
    )
    CharacterOwnership.objects.create(user=user, character=character, owner_hash=f"hash-{character_id}")
    return character


def make_token(character, scopes, user=None):
    token = Token.objects.create(
        character_id=character.character_id,
        character_name=character.character_name,
        character_owner_hash=f"hash-{character.character_id}",
        access_token="access",
        user=user,
    )
    token.scopes.set([Scope.objects.get_or_create(name=scope, defaults={"help_text": ""})[0] for scope in scopes])
    return token


def configure(alliance_id=ALLIANCE_ID, **fields):
    """The configuration, with the ESI member lists off unless asked for."""
    fields.setdefault("fetch_members", False)
    config = MonitorConfiguration.get_solo()
    config.alliance = make_alliance(alliance_id) if alliance_id else None
    for name, value in fields.items():
        setattr(config, name, value)
    config.save()
    return config


def store_snapshot(data):
    return Snapshot.objects.update_or_create(pk=1, defaults={"built_at": timezone.now(), "data": data})[0]


def snapshot_data(corporations, checks=(), services=(), alliance_id=ALLIANCE_ID):
    return {
        "alliance_id": alliance_id,
        "alliance_name": f"Alliance {alliance_id}",
        "checks": list(checks),
        "services": list(services),
        "stale_after_days": 3,
        "corporations": corporations,
    }


def corporation_row(corporation_id, accounts=(), problems=()):
    return {
        "id": corporation_id,
        "name": f"Corp {corporation_id}",
        "ticker": f"C{corporation_id}",
        "problems": list(problems),
        "accounts": list(accounts),
    }


def account_row(user_id, main_id, characters=None, services=None, corporation_id=2001):
    characters = characters or [character_row(main_id, corporation_id=corporation_id)]
    return {
        "user_id": user_id,
        "main_id": main_id,
        "main_name": f"Char {main_id}",
        "services": dict(services or {}),
        "characters": characters,
    }


def character_row(character_id, problems=(), corporation_id=2001):
    return {
        "id": character_id,
        "name": f"Char {character_id}",
        "corporation_id": corporation_id,
        "corporation_name": f"Corp {corporation_id}",
        "corporation_ticker": f"C{corporation_id}",
        "alliance_name": f"Alliance {ALLIANCE_ID}",
        "problems": list(problems),
    }
