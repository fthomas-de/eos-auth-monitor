"""The aa-charlink box the Director check sends a Director to: CharLink's Corporation Audit plus sovereignty.

CharLink's own Corporation Audit box asks for `corptools.views.CORP_REQUIRED_SCOPES`, which lacks the
sovereignty scope the Director check demands (`corptools.app_settings`' list). aa-charlink loads this
module through the `charlink` hook in `auth_hooks.py`, registered only with corptools and charlink installed.
"""

from dataclasses import replace

from charlink.app_imports.utils import AppImport
from charlink.imports.corptools import app_import as corptools_import

from .checks import SOVEREIGNTY_SCOPE

FIELD_LABEL = "Corporation Audit (Sovereignty)"

corporation_audit = corptools_import.get("structures")

# shortcut: everything but the scopes is CharLink's own box, "added" included (the Corporation is in the
# audit, not this token); drop the box once corptools.views.CORP_REQUIRED_SCOPES carries the scope
app_import = AppImport(
    "eos_auth_monitor",
    [
        replace(
            corporation_audit,
            app_label="eos_auth_monitor",
            unique_id="sovereignty",
            field_label=FIELD_LABEL,
            scopes=[*corporation_audit.scopes, SOVEREIGNTY_SCOPE],
        )
    ],
)
