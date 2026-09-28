from django.apps import AppConfig

from eos_auth_monitor import __version__


class EosAuthMonitorConfig(AppConfig):
    name = "eos_auth_monitor"
    label = "eos_auth_monitor"
    verbose_name = f"EOS Auth Monitor v{__version__}"
    default_auto_field = "django.db.models.BigAutoField"
