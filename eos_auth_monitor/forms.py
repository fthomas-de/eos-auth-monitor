from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from allianceauth.eveonline.models import EveAllianceInfo

from .checks import GROUPS, installed_checks, installed_services, is_app_installed
from .models import MonitorConfiguration

# (form field, model field, label, help text, where the choices come from)
CORPTOOLS_OPTIONS = (
    (
        "character_sections",
        "excluded_character_sections",
        _("Character Audit: sections that count"),
        _("A character is inactive when one of these has not updated within corptools' limit."),
        "character",
    ),
    (
        "character_scopes",
        "excluded_character_scopes",
        _("Character Audit: required scopes"),
        _("A character's token must carry all of these."),
        "character",
    ),
    (
        "corporation_sections",
        "excluded_corporation_sections",
        _("Corporation Audit: sections that count"),
        _("A Corporation's data is stale when one of these has not updated within the limit above."),
        "corporation",
    ),
    (
        "corporation_scopes",
        "excluded_corporation_scopes",
        _("Corporation Audit: required scopes"),
        _("One token of a Corporation member must carry all of these."),
        "corporation",
    ),
)


def _corptools_choices(field_name):
    from .sources import corptools

    if field_name == "character_sections":
        return [(key, corptools.CHARACTER_SECTION_LABELS.get(key, key)) for key in corptools.character_sections()]
    if field_name == "character_scopes":
        return [(scope, scope) for scope in corptools.character_scopes()]
    if field_name == "corporation_sections":
        return corptools.corporation_sections()
    return [(scope, scope) for scope in corptools.corporation_scopes()]


class MonitorConfigurationForm(forms.ModelForm):
    alliance = forms.ModelChoiceField(
        label=pgettext_lazy("EVE jargon", "Alliance"),
        queryset=EveAllianceInfo.objects.order_by("alliance_name"),
        required=False,
        help_text=MonitorConfiguration._meta.get_field("alliance").help_text,
        widget=forms.Select(attrs={"data-eos-auth-monitor-search": ""}),
    )

    class Meta:
        model = MonitorConfiguration
        fields = ["alliance", "stale_after_days", "fetch_members", "alliance_characters_only"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # one switch per check and service of an installed app; the others
        # keep whatever state they had, for the day their app comes back
        for check in installed_checks():
            self.fields[f"check_{check.key}"] = forms.BooleanField(
                label=check.label,
                help_text=check.description,
                required=False,
                initial=check.key not in self.instance.disabled_checks,
            )
        for service in installed_services():
            self.fields[f"service_{service.key}"] = forms.BooleanField(
                label=service.label,
                required=False,
                initial=service.key not in self.instance.disabled_services,
            )

        self._corptools_fields = []
        if is_app_installed("corptools"):
            for name, model_field, label, help_text, _scope in CORPTOOLS_OPTIONS:
                choices = _corptools_choices(name)
                excluded = set(getattr(self.instance, model_field))
                self.fields[name] = forms.MultipleChoiceField(
                    label=label,
                    help_text=help_text,
                    choices=choices,
                    required=False,
                    widget=forms.CheckboxSelectMultiple,
                    initial=[key for key, _label in choices if key not in excluded],
                )
                self._corptools_fields.append((name, model_field, [key for key, _label in choices]))
        else:
            del self.fields["stale_after_days"]

    def check_groups(self):
        """[(group, [bound field, ...]), ...] for the installed groups."""
        checks = installed_checks()
        return [
            (group, [self[f"check_{check.key}"] for check in checks if check.group == group.key])
            for group in GROUPS
            if group.is_installed
        ]

    def service_fields(self):
        return [self[f"service_{service.key}"] for service in installed_services()]

    def corptools_option_fields(self):
        return [self[name] for name, _model_field, _choices in self._corptools_fields]

    @staticmethod
    def _still_off(stored, offered, switched_off):
        # entries corptools no longer offers keep their state, like checks of a missing app
        return sorted({key for key in stored if key not in offered} | set(switched_off))

    def save(self, commit=True):
        instance = super().save(commit=False)
        installed = {check.key for check in installed_checks()}
        instance.disabled_checks = self._still_off(
            instance.disabled_checks, installed, (key for key in installed if not self.cleaned_data[f"check_{key}"])
        )
        installed = {service.key for service in installed_services()}
        instance.disabled_services = self._still_off(
            instance.disabled_services,
            installed,
            (key for key in installed if not self.cleaned_data[f"service_{key}"]),
        )
        for name, model_field, offered in self._corptools_fields:
            kept = set(self.cleaned_data[name])
            setattr(
                instance,
                model_field,
                self._still_off(getattr(instance, model_field), set(offered), (key for key in offered if key not in kept)),
            )
        if commit:
            instance.save()
        return instance
