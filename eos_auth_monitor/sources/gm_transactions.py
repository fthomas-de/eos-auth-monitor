"""eos-tax: which characters its GM Transactions page lists with the "GM X" box ticked.

Read on every page view from eos-tax's stored GM report, like the
eos-spy-network markers: nothing goes into this app's snapshot, so a viewer
without eos-tax's permission cannot reach it. Display only - never a problem.
"""

from django.apps import apps

APP = "eos_tax"
# either one shows eos-tax's GM Transactions tab (its base.html and views)
PERMISSIONS = ("eos_tax.admin_view", "eos_tax.gm_bots_access")


def is_installed() -> bool:
    return apps.is_installed(APP)


def can_view(user) -> bool:
    return is_installed() and any(user.has_perm(perm) for perm in PERMISSIONS)


def character_ids() -> set[int]:
    """The characters with a GM transaction against "GM X"; empty without eos-tax or before its first GM run.

    Taken from the page's own rows, so both apps agree on who the GM booked
    against - the side of a transaction depends on which party is a character.
    """
    if not is_installed():
        return set()
    from eos_tax.db.gm_transactions import FLAGGED_PARTY, get_gm_page, get_stored_gm_report

    stored = get_stored_gm_report()
    if stored is None:
        return set()
    # shortcut: builds eos-tax's whole page per view; ask eos-tax for a read API if it grows slow
    return {row["character_id"] for row in get_gm_page(stored)["rows"] if row["counterparty"] == FLAGGED_PARTY}
