"""Member lists and Director roles of Corporations from ESI - the app's only ESI calls.

No installed app stores who is in a Corporation: corptools' member tracking
only updates characters it already audits. The list is read with a token
corptools already holds (its Corporation audit requires the membership
scope), from any character of the Corporation; the endpoint needs no role.
Names come from Auth where it knows the character, else from ESI.

The roles of all members come from one call with the token of a character
corptools knows as a Director: corptools only reads the roles of characters
that have a token, so a Director without one is invisible to it, but the
Director who has a token can see everybody's roles.

django-esi caches the responses and honours their expiry, so the half-hourly
task does not ask ESI more often than the data changes.
"""

from allianceauth.eveonline.models import EveCharacter
from allianceauth.services.hooks import get_extension_logger

from .. import __version__

logger = get_extension_logger(__name__)

MEMBERSHIP_SCOPE = "esi-corporations.read_corporation_membership.v1"
DIRECTOR = "Director"
COMPATIBILITY_DATE = "2026-08-18"
NAMES_PER_REQUEST = 1000

_provider = None


def _client():
    global _provider
    if _provider is None:
        from esi.openapi_clients import ESIClientProvider

        _provider = ESIClientProvider(
            compatibility_date=COMPATIBILITY_DATE,
            ua_appname="eos-auth-monitor",
            ua_version=__version__,
            ua_url="https://github.com/fthomas-de/eos-auth-monitor",
            operations=[
                "GetCorporationsCorporationIdMembers",
                "GetCorporationsCorporationIdRoles",
                "PostUniverseNames",
            ],
        )
    return _provider.client


def corporation_members(corporation_id: int) -> list[int] | None:
    """EVE character IDs of all members, or None when no token could read them."""
    from esi.models import Token

    characters = EveCharacter.objects.filter(corporation_id=corporation_id).values("character_id")
    for token in Token.objects.filter(character_id__in=characters).require_scopes([MEMBERSHIP_SCOPE]):
        try:
            members = (
                _client()
                .Corporation.GetCorporationsCorporationIdMembers(corporation_id=corporation_id, token=token)
                .result(use_etag=False)
            )
        except Exception as error:  # noqa: BLE001 - a broken token must not stop the other Corporations
            # a character who left keeps its token; try the next one
            logger.warning("Member list of %s not readable with a token: %s", corporation_id, type(error).__name__)
            continue
        return [int(member) for member in members]
    return None


def corporation_directors(corporation_id: int) -> set[int] | None:
    """EVE character IDs of every Director, or None when no Director's token could read the roles.

    Only called with corptools installed: it says whose token to use.
    """
    from corptools.models import CharacterRoles
    from esi.models import Token

    directors = CharacterRoles.objects.filter(
        director=True, character__character__corporation_id=corporation_id
    ).values("character__character__character_id")
    for token in Token.objects.filter(character_id__in=directors).require_scopes([MEMBERSHIP_SCOPE]):
        try:
            found = (
                _client()
                .Corporation.GetCorporationsCorporationIdRoles(corporation_id=corporation_id, token=token)
                .result(use_etag=False)
            )
        except Exception as error:  # noqa: BLE001 - a broken token must not stop the other Corporations
            logger.warning("Roles of %s not readable with a token: %s", corporation_id, type(error).__name__)
            continue
        return {
            int(item.character_id)
            for item in found
            if DIRECTOR in [getattr(role, "value", role) for role in item.roles]
        }
    return None


def names(character_ids) -> dict[int, str]:
    character_ids = list(dict.fromkeys(character_ids))
    known = {}
    for start in range(0, len(character_ids), NAMES_PER_REQUEST):
        chunk = character_ids[start : start + NAMES_PER_REQUEST]
        known.update(
            EveCharacter.objects.filter(character_id__in=chunk).values_list("character_id", "character_name")
        )

    missing = [character_id for character_id in character_ids if character_id not in known]
    for start in range(0, len(missing), NAMES_PER_REQUEST):
        chunk = missing[start : start + NAMES_PER_REQUEST]
        try:
            for item in _client().Universe.PostUniverseNames(body=chunk).result():
                known[int(item.id)] = item.name
        except Exception as error:  # noqa: BLE001 - names are a nicety, the IDs still count
            logger.warning("Names of %d characters not readable: %s", len(chunk), type(error).__name__)
    return known
