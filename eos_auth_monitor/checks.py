"""Every check and service the app knows, and which of them are in use.

A check or service is *installed* when the app it reads from is installed,
and *enabled* when it is installed and not switched off on the settings page.
"""

from dataclasses import dataclass

from django.apps import apps
from django.utils.translation import gettext_lazy as _

CHARACTER = "character"
CORPORATION = "corporation"


@dataclass(frozen=True)
class Group:
    key: str
    app_label: str
    title: str

    @property
    def is_installed(self) -> bool:
        return is_app_installed(self.app_label)


@dataclass(frozen=True)
class Check:
    key: str
    group: str
    scope: str
    label: str
    description: str
    # what someone has to do about it, and the page of the app where it is done
    hint: str = ""
    fix_url: str | None = None

    @property
    def is_installed(self) -> bool:
        return GROUPS_BY_KEY[self.group].is_installed

    @property
    def app_title(self) -> str:
        return GROUPS_BY_KEY[self.group].title


@dataclass(frozen=True)
class Service:
    key: str
    app_label: str
    label: str
    icon: str

    @property
    def is_installed(self) -> bool:
        return is_app_installed(self.app_label)


def is_app_installed(app_label: str) -> bool:
    # by label: apps.is_installed() wants the module path, and the Discord
    # and Mumble services live deep inside allianceauth
    try:
        apps.get_app_config(app_label)
    except LookupError:
        return False
    return True


GROUPS = (
    Group("corptools_characters", "corptools", _("corptools - Character Audit")),
    Group("corptools_corporations", "corptools", _("corptools - Corporation Audit")),
    Group("structures", "structures", _("aa-structures")),
)
GROUPS_BY_KEY = {group.key: group for group in GROUPS}

CHECKS = (
    Check(
        "char_audit_missing",
        "corptools_characters",
        CHARACTER,
        _("Audit missing"),
        _("The character has no corptools Character Audit."),
        hint=_("The player adds this character in the corptools Character Audit."),
        fix_url="corptools:react",
    ),
    Check(
        "char_scopes_missing",
        "corptools_characters",
        CHARACTER,
        _("Scopes missing"),
        _("None of the character's tokens carries all scopes corptools asks for."),
        hint=_(
            "The player adds this character in the corptools Character Audit again "
            "and grants every scope it asks for."
        ),
        fix_url="corptools:react",
    ),
    Check(
        "char_audit_inactive",
        "corptools_characters",
        CHARACTER,
        _("Audit inactive"),
        _("corptools marks the audit inactive: a section has not updated for too long."),
        hint=_("The next corptools update usually clears this; if it stays, the player adds the character again."),
        fix_url="corptools:react",
    ),
    Check(
        "char_director_token_missing",
        "corptools_characters",
        CHARACTER,
        _("Director token missing"),
        _(
            "The character is a Director of its Corporation, but none of its tokens carries "
            "all scopes corptools needs for the Corporation audit."
        ),
        hint=_("The Director adds a Corporation token in the corptools Corporation Audit."),
        fix_url="corptools:corp_react",
    ),
    Check(
        "corp_audit_missing",
        "corptools_corporations",
        CORPORATION,
        _("Corporation audit missing"),
        _("The Corporation has no corptools Corporation Audit."),
        hint=_("A Director adds the Corporation in the corptools Corporation Audit."),
        fix_url="corptools:corp_react",
    ),
    Check(
        "corp_token_missing",
        "corptools_corporations",
        CORPORATION,
        _("Corporation token missing"),
        _("No character of the Corporation has a token with the scopes the Corporation audit needs."),
        hint=_("A Director adds a Corporation token in the corptools Corporation Audit."),
        fix_url="corptools:corp_react",
    ),
    Check(
        "corp_data_stale",
        "corptools_corporations",
        CORPORATION,
        _("Corporation data stale"),
        _("A section of the Corporation audit has not updated within the limit."),
        hint=_(
            "A Director checks the Corporation token in the corptools Corporation Audit "
            "and adds a new one if it lost its roles."
        ),
        fix_url="corptools:corp_react",
    ),
    Check(
        "structures_no_owner",
        "structures",
        CORPORATION,
        _("No structure owner"),
        _("The Corporation is not set up as an owner in aa-structures."),
        hint=_("A character with the Station Manager role adds the Corporation as an owner in aa-structures."),
        fix_url="structures:index",
    ),
    Check(
        "structures_owner_inactive",
        "structures",
        CORPORATION,
        _("Structure owner inactive"),
        _("The aa-structures owner of the Corporation is switched off."),
        hint=_("An admin switches the owner on again in the aa-structures admin."),
    ),
    Check(
        "structures_no_character",
        "structures",
        CORPORATION,
        _("No structure owner character"),
        _("The aa-structures owner has no enabled character left to fetch data with."),
        hint=_("A character with the Station Manager role adds itself to the owner in aa-structures."),
        fix_url="structures:index",
    ),
    Check(
        "structures_sync_failing",
        "structures",
        CORPORATION,
        _("Structure sync failing"),
        _("aa-structures reports a sync that is not up to date."),
        hint=_("Check the owner in aa-structures: its characters may have lost the Station Manager role."),
        fix_url="structures:index",
    ),
)
CHECKS_BY_KEY = {check.key: check for check in CHECKS}

SERVICES = (
    Service("discord", "discord", _("Discord"), "fab fa-discord"),
    Service("mumble", "mumble", _("Mumble"), "fas fa-headset"),
    Service("qq", "qqbot", _("QQ"), "fab fa-qq"),
    Service("telegram", "aa_discord_telegram_bridge", _("Telegram"), "fab fa-telegram"),
)
SERVICES_BY_KEY = {service.key: service for service in SERVICES}


def installed_checks() -> list[Check]:
    return [check for check in CHECKS if check.is_installed]


def enabled_checks(config) -> list[Check]:
    return [check for check in installed_checks() if check.key not in config.disabled_checks]


def installed_services() -> list[Service]:
    return [service for service in SERVICES if service.is_installed]


def enabled_services(config) -> list[Service]:
    return [service for service in installed_services() if service.key not in config.disabled_services]
