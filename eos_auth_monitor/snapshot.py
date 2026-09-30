"""Builds the snapshot the pages show: every account of the Alliance, per
Corporation of its main, with the problems of each character and Corporation,
and the members of each Corporation reduced to their mains.

Runs in the periodic task, never in a web request. The result is plain JSON;
labels are looked up when a page is rendered, in the viewer's language.
"""

from collections import Counter, defaultdict

from django.contrib.auth.models import User
from django.utils import timezone

from allianceauth.authentication.models import CharacterOwnership, UserProfile
from allianceauth.eveonline.models import EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger

from .checks import (
    CHARACTER,
    CHECKS_BY_KEY,
    DIRECTOR_GROUPS,
    enabled_checks,
    enabled_services,
    is_app_installed,
)
from .metrics import Measurement
from .models import MonitorConfiguration, Snapshot
from .sources import corptools as corptools_source
from .sources import members as members_source
from .sources import services as services_source
from .sources import structures as structures_source

logger = get_extension_logger(__name__)

IN_CHUNK = 1000


def _no_progress(phase, done=0, total=1):
    pass


def _keys_of_group(keys, *groups):
    return {key for key in keys if CHECKS_BY_KEY[key].group in groups}


def _chunks(items, size=IN_CHUNK):
    items = list(items)
    for start in range(0, len(items), size):
        yield items[start : start + size]


def stale_after_days(config):
    if config.stale_after_days:
        return config.stale_after_days
    if is_app_installed("corptools"):
        return corptools_source.max_inactive_days()
    return None


def _members(corporation_ids, accounts_by_corporation, on_step) -> dict[int, dict]:
    """Per Corporation: its member count and the members outside its accounts.

    A member that belongs to an account whose main is in another Corporation
    is reduced to that main; a member Auth does not know counts as a main of
    its own.
    """
    member_ids = {}
    for index, corporation_id in enumerate(corporation_ids):
        member_ids[corporation_id] = members_source.corporation_members(corporation_id)
        on_step("members", index + 1, len(corporation_ids) + 1)

    everyone = {member for members in member_ids.values() if members for member in members}
    ownerships = {}
    for chunk in _chunks(everyone):
        for ownership in CharacterOwnership.objects.filter(character__character_id__in=chunk).select_related(
            "character", "user__profile__main_character"
        ):
            ownerships[ownership.character.character_id] = ownership
    unknown = [member for member in everyone if member not in ownerships]
    names = members_source.names(unknown) if unknown else {}

    result = {}
    for corporation_id, members in member_ids.items():
        if members is None:
            result[corporation_id] = {"member_count": None, "other_mains": [], "unregistered": []}
            continue

        own_users = {account["user_id"] for account in accounts_by_corporation.get(corporation_id, [])}
        other_mains = {}
        unregistered = []
        for member in members:
            ownership = ownerships.get(member)
            main = ownership.user.profile.main_character if ownership else None
            if ownership and ownership.user_id in own_users:
                continue
            if main is None:
                # not in Auth, or an account without a main: nobody to reduce it to
                name = ownership.character.character_name if ownership else names.get(member, str(member))
                unregistered.append({"id": member, "name": name})
                continue
            entry = other_mains.setdefault(
                ownership.user_id,
                {
                    "user_id": ownership.user_id,
                    "main_id": main.character_id,
                    "main_name": main.character_name,
                    "main_corporation_name": main.corporation_name,
                    "characters": [],
                },
            )
            entry["characters"].append({"id": member, "name": ownership.character.character_name})

        result[corporation_id] = {
            "member_count": len(members),
            "other_mains": sorted(other_mains.values(), key=lambda entry: entry["main_name"].lower()),
            "unregistered": sorted(unregistered, key=lambda entry: entry["name"].lower()),
        }
    return result


def _directors(corporation_ids, from_esi, account_user_ids, groups, config) -> dict[int, list[dict]]:
    """Per Corporation its Directors: whose account they are and which token of each Director list they have.

    ESI names every Director of a Corporation where a Director's token could
    read the roles; corptools adds those whose roles it read itself. A
    Director unknown to Auth has no account and, as a rule, no token.
    """
    ids_by_corporation = defaultdict(set)
    for corporation_id, found in from_esi.items():
        ids_by_corporation[corporation_id] |= set(found)
    if is_app_installed("corptools"):
        for corporation_id, found in corptools_source.known_directors(corporation_ids).items():
            ids_by_corporation[corporation_id] |= found
    everyone = {character_id for found in ids_by_corporation.values() for character_id in found}
    if not everyone:
        return {}

    # Auth's names first; ESI only for Directors Auth does not know, who only come from ESI
    names = members_source.names(everyone)
    ownerships = {
        ownership.character.character_id: ownership
        for ownership in CharacterOwnership.objects.filter(character__character_id__in=everyone).select_related(
            "character", "user__profile__main_character"
        )
    }
    corporation_tokens = (
        corptools_source.corporation_token_holders(everyone, config.excluded_corporation_scopes)
        if "corptools_corporations" in groups
        else set()
    )
    owner_characters = structures_source.owner_characters(corporation_ids) if "structures" in groups else {}

    result = {}
    for corporation_id, found in ids_by_corporation.items():
        rows = []
        for character_id in found:
            ownership = ownerships.get(character_id)
            main = ownership.user.profile.main_character if ownership else None
            tokens = {}
            if "corptools_corporations" in groups:
                tokens["corptools_corporations"] = character_id in corporation_tokens
            if "structures" in groups:
                tokens["structures"] = character_id in owner_characters.get(corporation_id, set())
            rows.append(
                {
                    "id": character_id,
                    "name": names.get(character_id, str(character_id)),
                    "in_auth": ownership is not None,
                    # only an account of the overview has a page to link to
                    "user_id": ownership.user_id if ownership and ownership.user_id in account_user_ids else None,
                    "main_name": main.character_name if main else None,
                    "tokens": tokens,
                }
            )
        result[corporation_id] = sorted(rows, key=lambda row: row["name"].lower())
    return result


def build(config, on_step=_no_progress) -> dict | None:
    """The snapshot for the configured Alliance, or None without one."""
    alliance = config.alliance
    if alliance is None:
        return None

    on_step("accounts")
    alliance_id = alliance.alliance_id
    keys = [check.key for check in enabled_checks(config)]
    services = [service.key for service in enabled_services(config)]
    stale_days = stale_after_days(config)

    profiles = list(
        UserProfile.objects.filter(main_character__alliance_id=alliance_id).select_related("main_character")
    )
    users = User.objects.filter(profile__main_character__alliance_id=alliance_id)
    ownerships = CharacterOwnership.objects.filter(user__in=users).select_related("character")
    # per account, how many characters the pages leave out - so that they can say so
    left_out = Counter()
    if config.alliance_characters_only:
        left_out.update(ownerships.exclude(character__alliance_id=alliance_id).values_list("user_id", flat=True))
        # dropped here, an alt elsewhere is neither checked nor asked about nor counted
        ownerships = ownerships.filter(character__alliance_id=alliance_id)

    characters_by_user = defaultdict(list)
    for ownership in ownerships:
        characters_by_user[ownership.user_id].append(ownership.character)

    on_step("characters")
    character_problems = {}
    character_keys = {key for key in keys if CHECKS_BY_KEY[key].scope == CHARACTER}
    esi_directors = set()
    esi_directors_by_corporation = {}
    director_lists = [group for group in DIRECTOR_GROUPS if _keys_of_group(keys, group)]
    # Corporations where the roles were asked for and no Director token could read them
    roles_unreadable = set()
    # corptools says whose token may read the roles; the Director check and the Director lists need them
    asked_roles = (
        config.fetch_members
        and is_app_installed("corptools")
        and ("char_director_token_missing" in character_keys or bool(director_lists))
    )
    asked = set()

    def ask_roles(corporation_id):
        asked.add(corporation_id)
        found = members_source.corporation_directors(corporation_id)
        if found is None:
            roles_unreadable.add(corporation_id)
        else:
            esi_directors_by_corporation[corporation_id] = found
            esi_directors.update(found)

    if asked_roles:
        # one call per Corporation of the Alliance an account has a character in, and only where a
        # Director has a token; the Directors of a Corporation elsewhere are not the Alliance's concern
        for corporation_id in sorted(
            {c.corporation_id for chars in characters_by_user.values() for c in chars if c.alliance_id == alliance_id}
        ):
            ask_roles(corporation_id)
    if character_keys:
        character_ids = ownerships.values_list("character__character_id", flat=True)
        character_problems = corptools_source.character_problems(
            character_ids,
            character_keys,
            config.excluded_character_sections,
            config.excluded_character_scopes,
            config.excluded_corporation_scopes,
            esi_directors,
            director_ids=ownerships.filter(character__alliance_id=alliance_id).values_list(
                "character__character_id", flat=True
            ),
        )

    on_step("corporations")
    # The Alliance's Corporations as Auth knows them, and the Corporation of
    # every main on top - Auth may not have an EveCorporationInfo for each.
    corporations = {
        corporation.corporation_id: {
            "name": corporation.corporation_name,
            "ticker": corporation.corporation_ticker,
            # public ESI data that Auth keeps on the EveCorporationInfo; no token involved
            "member_total": corporation.member_count,
        }
        for corporation in EveCorporationInfo.objects.filter(alliance__alliance_id=alliance_id)
    }
    for profile in profiles:
        main = profile.main_character
        corporations.setdefault(
            main.corporation_id,
            {"name": main.corporation_name, "ticker": main.corporation_ticker, "member_total": None},
        )
    corporation_ids = sorted(corporations)
    if asked_roles:
        # a Corporation of the Alliance where nobody has a character yet still deserves its marker
        for corporation_id in corporation_ids:
            if corporation_id not in asked:
                ask_roles(corporation_id)

    corporation_problems = defaultdict(list)
    corptools_keys = _keys_of_group(keys, "corptools_corporations")
    if corptools_keys:
        found = corptools_source.corporation_problems(
            corporation_ids,
            corptools_keys,
            stale_days,
            config.excluded_corporation_sections,
            config.excluded_corporation_scopes,
        )
        for corporation_id, problems in found.items():
            corporation_problems[corporation_id] += problems
    structures_keys = _keys_of_group(keys, "structures")
    if structures_keys:
        found = structures_source.corporation_problems(corporation_ids, structures_keys)
        for corporation_id, problems in found.items():
            corporation_problems[corporation_id] += problems

    directors = (
        _directors(
            corporation_ids,
            esi_directors_by_corporation,
            {profile.user_id for profile in profiles},
            director_lists,
            config,
        )
        if director_lists
        else {}
    )

    on_step("services")
    links = {service: services_source.linked_user_ids(service, users) for service in services}

    accounts_by_corporation = defaultdict(list)
    for profile in profiles:
        main = profile.main_character
        characters = characters_by_user[profile.user_id]
        if all(character.character_id != main.character_id for character in characters):
            # a main without an ownership row (older installations) is still the account's
            characters = [main, *characters]
        characters = sorted(
            characters,
            key=lambda character: (character.character_id != main.character_id, character.character_name.lower()),
        )
        accounts_by_corporation[main.corporation_id].append(
            {
                "user_id": profile.user_id,
                "main_id": main.character_id,
                "main_name": main.character_name,
                "services": {service: profile.user_id in linked for service, linked in links.items()},
                "characters": [
                    {
                        "id": character.character_id,
                        "name": character.character_name,
                        "corporation_id": character.corporation_id,
                        "corporation_name": character.corporation_name,
                        "corporation_ticker": character.corporation_ticker,
                        "alliance_name": character.alliance_name or "",
                        "problems": character_problems.get(character.character_id, []),
                    }
                    for character in characters
                ],
                "left_out": left_out[profile.user_id],
            }
        )

    on_step("members")
    if config.fetch_members:
        members = _members(corporation_ids, accounts_by_corporation, on_step)
    else:
        members = {}

    on_step("store")
    no_members = {"member_count": None, "other_mains": [], "unregistered": []}
    return {
        "alliance_id": alliance_id,
        "alliance_name": alliance.alliance_name,
        "checks": keys,
        "services": services,
        "stale_after_days": stale_days,
        "members_fetched": bool(config.fetch_members),
        "corporations": sorted(
            (
                {
                    "id": corporation_id,
                    "name": corporations[corporation_id]["name"],
                    "ticker": corporations[corporation_id]["ticker"],
                    "member_total": corporations[corporation_id]["member_total"],
                    "problems": corporation_problems.get(corporation_id, []),
                    "no_director_token": corporation_id in roles_unreadable,
                    "directors": directors.get(corporation_id, []),
                    "accounts": sorted(
                        accounts_by_corporation.get(corporation_id, []),
                        key=lambda account: account["main_name"].lower(),
                    ),
                    **members.get(corporation_id, no_members),
                }
                for corporation_id in corporation_ids
            ),
            key=lambda corporation: corporation["name"].lower(),
        ),
    }


def update(on_step=_no_progress) -> Snapshot | None:
    """Rebuild and store the snapshot; without an Alliance the old one goes."""
    with Measurement(on_step) as measurement:
        data = build(MonitorConfiguration.get_solo(), measurement.on_step)
    if data is None:
        Snapshot.objects.all().delete()
        return None
    data["metrics"] = measurement.result(data)

    snapshot, _ = Snapshot.objects.update_or_create(pk=1, defaults={"built_at": timezone.now(), "data": data})
    logger.info(
        "Snapshot built for %s: %d Corporations",
        data["alliance_name"],
        len(data["corporations"]),
    )
    return snapshot


def current() -> Snapshot | None:
    return Snapshot.objects.filter(pk=1).first()
