from solo.models import SingletonModel

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from allianceauth.eveonline.models import EveAllianceInfo


class General(models.Model):
    """Meta model for app permissions"""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access", "Can view the accounts of the Corporation of their own main"),
            ("view_all", "Can view all accounts and Corporations of the Alliance"),
            ("manage_settings", "Can change the Alliance and the checks"),
            ("view_own", "Can view their own account"),
        )


class MonitorConfiguration(SingletonModel):
    """App wide settings, maintained on the settings page."""

    alliance = models.ForeignKey(
        EveAllianceInfo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=pgettext_lazy("EVE jargon", "Alliance"),
        help_text=_("The Alliance whose accounts and Corporations are monitored."),
    )
    # Empty follows corptools' CT_CHAR_MAX_INACTIVE_DAYS at the time the
    # snapshot is built; a number fixed here would silently drift from it.
    stale_after_days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Stale after (days)"),
        help_text=_(
            "Days after which a section of the corptools Corporation audit counts as stale. "
            "Empty: the same limit corptools uses for characters."
        ),
    )
    # Keys of switched off checks and services. Stored as "off" rather than
    # "on" so a check added in a later release starts switched on.
    disabled_checks = models.JSONField(default=list, blank=True)
    disabled_services = models.JSONField(default=list, blank=True)
    # What the corptools checks leave out, e.g. Moon Observations for an
    # Alliance without moons - again stored as "off", for the same reason.
    excluded_character_sections = models.JSONField(default=list, blank=True)
    excluded_character_scopes = models.JSONField(default=list, blank=True)
    excluded_corporation_sections = models.JSONField(default=list, blank=True)
    excluded_corporation_scopes = models.JSONField(default=list, blank=True)
    fetch_members = models.BooleanField(
        default=True,
        verbose_name=_("Fetch data from ESI"),
        help_text=_(
            "Reads each Corporation's member list and Director roles with tokens corptools already has, "
            "to show members that are not registered in Auth and Directors without a token."
        ),
    )
    alliance_characters_only = models.BooleanField(
        default=False,
        verbose_name=_("Only characters in the Alliance"),
        help_text=_(
            "Checks, shows and counts only the characters of an account that are in the Alliance; "
            "alts elsewhere are left out."
        ),
    )
    member_notice = models.TextField(
        blank=True,
        verbose_name=_("Notice to members"),
        help_text=_("Shown as an info box on My account and My Corporation. Leave it empty to show none."),
    )

    class Meta:
        default_permissions = ()
        verbose_name = _("Configuration")

    def __str__(self):
        return str(_("Configuration"))


class Snapshot(models.Model):
    """The last result of the periodic task; one row, overwritten each run.

    Not a solo model on purpose: SOLO_CACHE would put the whole result into the
    cache on every read.
    """

    built_at = models.DateTimeField()
    data = models.JSONField(default=dict)

    class Meta:
        default_permissions = ()

    def __str__(self):
        return f"Snapshot {self.built_at:%Y-%m-%d %H:%M}"


class CharacterProblemsFilter(models.Model):
    """Smart filter for allianceauth-securegroups: has any character of the account a problem?

    Reads the snapshot, so it is as current as the last run of the task.
    Same fields and methods as securegroups' own FilterBase, which is not
    imported so the app works without securegroups. A new name rather than
    the AccountProblemsFilter that 0005 dropped: a binding left behind from
    0.0.1 must not come back to life on a new filter.
    """

    name = models.CharField(max_length=500)
    description = models.CharField(max_length=500)
    reversed_logic = models.BooleanField(
        default=False,
        help_text=_("Pass accounts whose characters HAVE problems instead of those without."),
    )

    class Meta:
        verbose_name = _("Smart Filter: Auth Monitor character problems")
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name}: {self.description}"

    def process_filter(self, user) -> bool:
        return self.audit_filter([user])[user.pk]["check"]

    def audit_filter(self, users) -> dict:
        from .smart_filters import audit_accounts

        return audit_accounts(users, self.reversed_logic)

