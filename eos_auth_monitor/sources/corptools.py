"""corptools: Character Audit and Corporation Audit.

The rules mirror corptools' own, so both apps agree on who is complete - with
the sections and scopes an admin left out on the settings page taken away.

"Audit inactive" is worked out here rather than read from
``CharacterAudit.active``: the stored flag cannot leave a section out, and
``CharacterAudit.is_active()`` saves the audit, while this app must not write
to corptools. ``character_sections()`` repeats the conditions of
``is_active()`` for that reason; compare it with corptools after an upgrade.
"""

import datetime
from collections import defaultdict

from django.utils import timezone

from . import problem

ROLES_SCOPE = "esi-characters.read_corporation_roles.v1"

# update_timestamps key -> label, in the order of CharacterAudit.is_active()
CHARACTER_SECTION_LABELS = {
    "pub_data": "Public data",
    "assets": "Assets",
    "clones": "Clones",
    "skills": "Skills",
    "skill_que": "Skill queue",
    "wallet": "Wallet",
    "orders": "Market orders",
    "notif": "Notifications",
    "roles": "Roles",
    "mails": "Mails",
    "loyaltypoints": "Loyalty points",
    "mining": "Mining",
    "mercenary_dens": "Mercenary dens",
    "mercenary_tactical_operations": "Mercenary tactical operations",
}

# (keys, module setting, ignore setting, CorptoolsConfiguration switch)
_CHARACTER_SECTION_RULES = (
    (("assets",), "CT_CHAR_ASSETS_MODULE", "CT_CHAR_ACTIVE_IGNORE_ASSETS_MODULE", "disable_update_assets"),
    (("clones",), "CT_CHAR_CLONES_MODULE", "CT_CHAR_ACTIVE_IGNORE_CLONES_MODULE", "disable_update_clones"),
    (("skills", "skill_que"), "CT_CHAR_SKILLS_MODULE", "CT_CHAR_ACTIVE_IGNORE_SKILLS_MODULE", "disable_update_skills"),
    (("wallet", "orders"), "CT_CHAR_WALLET_MODULE", "CT_CHAR_ACTIVE_IGNORE_WALLET_MODULE", "disable_update_wallet"),
    (
        ("notif",),
        "CT_CHAR_NOTIFICATIONS_MODULE",
        "CT_CHAR_ACTIVE_IGNORE_NOTIFICATIONS_MODULE",
        "disable_update_notif",
    ),
    (("roles",), "CT_CHAR_ROLES_MODULE", "CT_CHAR_ACTIVE_IGNORE_ROLES_MODULE", "disable_update_roles"),
    (("mails",), "CT_CHAR_MAIL_MODULE", "CT_CHAR_ACTIVE_IGNORE_MAIL_MODULE", "disable_update_mails"),
    (
        ("loyaltypoints",),
        "CT_CHAR_LOYALTYPOINTS_MODULE",
        "CT_CHAR_ACTIVE_IGNORE_LOYALTYPOINTS_MODULE",
        "disable_update_loyaltypoints",
    ),
    (("mining",), "CT_CHAR_MINING_MODULE", "CT_CHAR_ACTIVE_IGNORE_MINING_MODULE", "disable_update_mining"),
    (
        ("mercenary_dens",),
        "CT_CHAR_STRUCTURES_MODULE",
        "CT_CHAR_ACTIVE_IGNORE_MERCENARY_DENS_MODULE",
        "disable_update_mercenary_dens",
    ),
    (
        ("mercenary_tactical_operations",),
        "CT_CHAR_STRUCTURES_MODULE",
        "CT_CHAR_ACTIVE_IGNORE_MERCENARY_TACTICAL_OPERATIONS_MODULE",
        "disable_update_mercenary_tactical_operations",
    ),
)


def max_inactive_days() -> int:
    from corptools.app_settings import CT_CHAR_MAX_INACTIVE_DAYS

    return CT_CHAR_MAX_INACTIVE_DAYS


def character_sections() -> list[str]:
    """The update_timestamps keys corptools' is_active() counts right now."""
    from corptools import app_settings
    from corptools.models import CorptoolsConfiguration

    # first(), not get_solo(): get_solo() creates the row when it is missing
    config = CorptoolsConfiguration.objects.first()

    def switched_off(name):
        return bool(config is not None and getattr(config, name, False))

    def setting(name):
        return getattr(app_settings, name, False)

    sections = []
    # corptools' own condition, odd as it reads: public data counts when
    # corporation history is *ignored*
    if setting("CT_CHAR_ACTIVE_IGNORE_CORP_HISTORY") and not switched_off("disable_update_pub_data"):
        sections.append("pub_data")
    for keys, module, ignore, switch in _CHARACTER_SECTION_RULES:
        if setting(module) and not setting(ignore) and not switched_off(switch):
            sections += keys
    return sections


def character_scopes() -> list[str]:
    from corptools.app_settings import get_character_scopes

    return sorted(set(get_character_scopes()))


def corporation_sections() -> list[tuple[str, str]]:
    """(key, label) of every section of the Corporation audit."""
    from corptools.app_settings import get_corp_update_attributes

    return [(key, label) for label, key, *_ in get_corp_update_attributes()]


def corporation_scopes() -> list[str]:
    from corptools.app_settings import CORP_REQUIRED_SCOPES

    # corptools' get_corp_token adds the roles scope to every request
    return sorted(set(CORP_REQUIRED_SCOPES) | {ROLES_SCOPE})


def _parse(value):
    if not value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, datetime.timezone.utc)
    return parsed


def _is_fresh(value, time_ref) -> bool:
    # corptools' check_date(): a section never updated counts as old
    updated = _parse(value)
    return updated is not None and updated > time_ref


def character_problems(
    character_ids,
    keys,
    excluded_sections=(),
    excluded_scopes=(),
    excluded_corporation_scopes=(),
    esi_directors=(),
) -> dict[int, list[dict]]:
    """Problems per EVE character ID.

    ``character_ids`` is a flat ``values_list`` queryset: used as a subquery
    in the filters below, so an Alliance of thousands of characters never
    becomes a long IN list.

    ``esi_directors`` are Directors ESI named that corptools does not know
    as such, e.g. because it never read their roles.
    """
    from corptools.models import CharacterAudit, CharacterRoles
    from esi.models import Token

    audits = {
        row["character__character_id"]: row["update_timestamps"]
        for row in CharacterAudit.objects.filter(character__character_id__in=character_ids).values(
            "character__character_id", "update_timestamps"
        )
    }

    directors = set()
    if "char_director_token_missing" in keys:
        directors = set(esi_directors)
        directors |= set(
            CharacterRoles.objects.filter(
                character__character__character_id__in=character_ids, director=True
            ).values_list("character__character__character_id", flat=True)
        )

    scopes_per_token = defaultdict(dict)
    if "char_scopes_missing" in keys or directors:
        rows = Token.objects.filter(character_id__in=character_ids).values_list("pk", "character_id", "scopes__name")
        for token_id, character_id, scope in rows:
            scopes = scopes_per_token[character_id].setdefault(token_id, set())
            if scope:
                scopes.add(scope)

    required = set(character_scopes()) - set(excluded_scopes)
    required_corporation = set(corporation_scopes()) - set(excluded_corporation_scopes)
    sections = [key for key in character_sections() if key not in set(excluded_sections)]
    time_ref = timezone.now() - datetime.timedelta(days=max_inactive_days())
    result = {}

    for character_id in character_ids:
        found = []

        if character_id not in audits:
            if "char_audit_missing" in keys:
                found.append(problem("char_audit_missing"))
        elif "char_audit_inactive" in keys:
            timestamps = audits[character_id] or {}
            stale = [key for key in sections if not _is_fresh(timestamps.get(key), time_ref)]
            if stale:
                found.append(problem("char_audit_inactive", [CHARACTER_SECTION_LABELS.get(key, key) for key in stale]))

        if "char_scopes_missing" in keys:
            tokens = scopes_per_token.get(character_id, {}).values()
            if not any(required <= scopes for scopes in tokens):
                # the token closest to complete says what re-adding one would fix
                best = max(tokens, key=lambda scopes: len(scopes & required), default=set())
                found.append(problem("char_scopes_missing", sorted(required - best)))

        if character_id in directors:
            tokens = scopes_per_token.get(character_id, {}).values()
            if not any(required_corporation <= scopes for scopes in tokens):
                best = max(tokens, key=lambda scopes: len(scopes & required_corporation), default=set())
                found.append(problem("char_director_token_missing", sorted(required_corporation - best)))

        if found:
            result[character_id] = found

    return result


def corporation_problems(
    corporation_ids, keys, stale_after_days: int, excluded_sections=(), excluded_scopes=()
) -> dict[int, list[dict]]:
    """Problems per EVE Corporation ID; a Corporation has few rows, a list is fine."""
    from corptools.models import CorporationAudit
    from esi.models import Token

    from allianceauth.eveonline.models import EveCharacter

    audits = {
        audit.corporation.corporation_id: audit
        for audit in CorporationAudit.objects.filter(corporation__corporation_id__in=corporation_ids).select_related(
            "corporation"
        )
    }
    required = [scope for scope in corporation_scopes() if scope not in set(excluded_scopes)]
    sections = [(key, label) for key, label in corporation_sections() if key not in set(excluded_sections)]
    time_ref = timezone.now() - datetime.timedelta(days=stale_after_days)
    result = {}

    for corporation_id in corporation_ids:
        found = []
        audit = audits.get(corporation_id)

        if audit is None and "corp_audit_missing" in keys:
            found.append(problem("corp_audit_missing"))

        if "corp_token_missing" in keys:
            members = EveCharacter.objects.filter(corporation_id=corporation_id).values("character_id")
            if not Token.objects.filter(character_id__in=members).require_scopes(required).exists():
                found.append(problem("corp_token_missing"))

        if audit is not None and "corp_data_stale" in keys:
            if not audit.update_timestamps:
                # never updated at all: an empty detail, see report.describe()
                found.append(problem("corp_data_stale"))
            else:
                # sections without any timestamp are left alone: corptools only
                # writes one once a module has run, and some never apply
                stale = [
                    label
                    for key, label in sections
                    if (updated := _parse(audit.update_timestamps.get(key))) and updated < time_ref
                ]
                if stale:
                    found.append(problem("corp_data_stale", stale))

        if found:
            result[corporation_id] = found

    return result
