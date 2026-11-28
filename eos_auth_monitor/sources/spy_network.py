"""eos-spy-network: which characters its last calculation marked.

Read on every page view through the app's own ``eos_spy_network.api``, not
copied into this app's snapshot: the findings stay as fresh as eos-spy-network
keeps them, and nothing of them is stored where a viewer without its
permissions could reach it. The pages only show them - they are no problems
here and change no count, order or colour of the checks.
"""

from dataclasses import dataclass

from django.apps import apps

from ..permissions import own_corporation_id

APP = "eos_spy_network"
# eos-spy-network's full view: every Corporation (0.0.31 dropped view_evidence, which this needed too)
PERMISSIONS = ("eos_spy_network.view_suspects",)
# eos-spy-network's CEO role: suspects and evidence of the main's own Corporation
CEO_PERMISSION = "eos_spy_network.view_own_corporation"


@dataclass(frozen=True)
class SpyMarker:
    kind: str
    label: str
    description: str


def is_installed() -> bool:
    return apps.is_installed(APP)


def can_view(user) -> bool:
    return is_installed() and all(user.has_perm(perm) for perm in PERMISSIONS)


def ceo_corporation_id(user) -> int | None:
    """The Corporation eos-spy-network's CEO role shows this viewer; None with the full view or without the role."""
    if can_view(user) or not (is_installed() and user.has_perm(CEO_PERMISSION)):
        return None
    return own_corporation_id(user)


def _api():
    """eos-spy-network's read API; an older release raises ImportError, which the views show as a notice."""
    from eos_spy_network import api

    return api


def kinds() -> tuple[str, ...]:
    """The marker kinds in eos-spy-network's own order; () without the app."""
    if not is_installed():
        return ()
    return tuple(_api().KINDS)


def character_markers(corporation_id: int | None = None) -> dict[int, list[SpyMarker]]:
    """EVE character ID -> its markers, in eos-spy-network's order; {} without the app or a result.

    With ``corporation_id``, only what eos-spy-network shows that Corporation's CEO.
    """
    if not is_installed():
        return {}
    api = _api()
    markers = {kind: SpyMarker(kind, api.label(kind), api.description(kind)) for kind in api.KINDS}
    return {
        character_id: [markers[kind] for kind in kinds if kind in markers]
        for character_id, kinds in api.character_markers(corporation_id=corporation_id).items()
    }
