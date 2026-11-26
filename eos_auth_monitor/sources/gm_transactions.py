"""eos-tax: which characters its GM Transactions page lists with the "GM X" box ticked.

Read on every page view through eos-tax's ``eos_tax.api``, like the
eos-spy-network markers: nothing goes into this app's snapshot, so a viewer
without eos-tax's permission cannot reach it. Display only - never a problem.
"""

import inspect

from django.apps import apps

from ..permissions import own_corporation_id

APP = "eos_tax"
# either one shows eos-tax's GM Transactions tab (its base.html and views)
PERMISSIONS = ("eos_tax.admin_view", "eos_tax.gm_bots_access")
# eos-tax's CEO role: the tab with the main's own Corporation only
CEO_PERMISSION = "eos_tax.basic_access"


def is_installed() -> bool:
    return apps.is_installed(APP)


def can_view(user) -> bool:
    return is_installed() and any(user.has_perm(perm) for perm in PERMISSIONS)


def _api():
    """eos-tax's read API, or None with an eos-tax older than it."""
    try:
        from eos_tax import api
    except ImportError:
        return None
    return api


def ceo_corporation_id(user) -> int | None:
    """The Corporation eos-tax's CEO role shows this viewer; None with the full view, without the role or
    with an eos-tax that cannot filter by Corporation yet."""
    if can_view(user) or not (is_installed() and user.has_perm(CEO_PERMISSION)):
        return None
    if _api() is None:
        from eos_tax.db.gm_transactions import get_gm_page

        if "corporation_id" not in inspect.signature(get_gm_page).parameters:
            return None
    return own_corporation_id(user)


def character_ids(corporation_id: int | None = None) -> set[int]:
    """The characters with a GM transaction against "GM X"; empty without eos-tax or before its first GM run.

    eos-tax reads them off its GM Transactions rows, so both apps agree on who
    the GM booked against. With ``corporation_id``, only the rows eos-tax shows
    that Corporation's CEO.
    """
    if not is_installed():
        return set()
    if (api := _api()) is not None:
        return api.gm_x_character_ids(corporation_id=corporation_id)

    # shortcut: an eos-tax before its read API builds its whole page per view; drop once production runs it
    from eos_tax.db.gm_transactions import FLAGGED_PARTY, get_gm_page, get_stored_gm_report

    stored = get_stored_gm_report()
    if stored is None:
        return set()
    # an older eos-tax lacks corporation_id; ceo_corporation_id() never hands one out then
    page = get_gm_page(stored, corporation_id=corporation_id) if corporation_id else get_gm_page(stored)
    return {row["character_id"] for row in page["rows"] if row["counterparty"] == FLAGGED_PARTY}
