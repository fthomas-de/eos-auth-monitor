"""eos-tax: which characters its GM Transactions page lists with the "GM X" box ticked.

Read on every page view from eos-tax's stored GM report, like the
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


def ceo_corporation_id(user) -> int | None:
    """The Corporation eos-tax's CEO role shows this viewer; None with the full view, without the role or
    with an eos-tax that cannot filter by Corporation yet."""
    if can_view(user) or not (is_installed() and user.has_perm(CEO_PERMISSION)):
        return None
    from eos_tax.db.gm_transactions import get_gm_page

    if "corporation_id" not in inspect.signature(get_gm_page).parameters:
        return None
    return own_corporation_id(user)


def character_ids(corporation_id: int | None = None) -> set[int]:
    """The characters with a GM transaction against "GM X"; empty without eos-tax or before its first GM run.

    Taken from the page's own rows, so both apps agree on who the GM booked
    against - the side of a transaction depends on which party is a character.
    With ``corporation_id``, only the rows eos-tax shows that Corporation's CEO.
    """
    if not is_installed():
        return set()
    from eos_tax.db.gm_transactions import FLAGGED_PARTY, get_gm_page, get_stored_gm_report

    stored = get_stored_gm_report()
    if stored is None:
        return set()
    # an older eos-tax lacks corporation_id; ceo_corporation_id() never hands one out then
    page = get_gm_page(stored, corporation_id=corporation_id) if corporation_id else get_gm_page(stored)
    # shortcut: builds eos-tax's whole page per view; ask eos-tax for a read API if it grows slow
    return {row["character_id"] for row in page["rows"] if row["counterparty"] == FLAGGED_PARTY}
