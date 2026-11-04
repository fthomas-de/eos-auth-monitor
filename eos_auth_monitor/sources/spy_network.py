"""eos-spy-network: which characters its last calculation marked.

Read on every page view through the app's own ``eos_spy_network.api``, not
copied into this app's snapshot: the findings stay as fresh as eos-spy-network
keeps them, and nothing of them is stored where a viewer without its
permissions could reach it. The pages only show them - they are no problems
here and change no count, order or colour of the checks.
"""

from dataclasses import dataclass

from django.apps import apps

APP = "eos_spy_network"
# eos-spy-network shows the counterparts of mails, ISK and contracts only with both
PERMISSIONS = ("eos_spy_network.view_suspects", "eos_spy_network.view_evidence")


@dataclass(frozen=True)
class SpyMarker:
    kind: str
    label: str
    description: str


def is_installed() -> bool:
    """Installed and new enough: the read API came with eos-spy-network 0.0.10."""
    return apps.is_installed(APP) and _api() is not None


def can_view(user) -> bool:
    return is_installed() and all(user.has_perm(perm) for perm in PERMISSIONS)


def _api():
    """eos-spy-network's read API, or None where it is older than the API or lacks a part of it.

    Checked by what it offers, not by its version number: an older release
    then shows nothing instead of failing the pages of its viewers.
    """
    try:
        from eos_spy_network import api
    except ImportError:
        return None
    if not all(hasattr(api, name) for name in ("KINDS", "character_markers", "label", "description")):
        return None
    return api


def kinds() -> tuple[str, ...]:
    """The marker kinds in eos-spy-network's own order; () without the app."""
    if not is_installed():
        return ()
    return tuple(_api().KINDS)


def character_markers() -> dict[int, list[SpyMarker]]:
    """EVE character ID -> its markers, in eos-spy-network's order; {} without the app or a result."""
    if not is_installed():
        return {}
    api = _api()
    markers = {kind: SpyMarker(kind, api.label(kind), api.description(kind)) for kind in api.KINDS}
    return {
        character_id: [markers[kind] for kind in found if kind in markers]
        for character_id, found in api.character_markers().items()
    }
