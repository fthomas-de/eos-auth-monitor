from django.utils.translation import gettext_lazy as _

from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

from . import urls
from .permissions import has_app_access


class AuthMonitorMenuItem(MenuItemHook):
    def __init__(self):
        MenuItemHook.__init__(
            self,
            _("Auth Monitor"),
            "fas fa-user-shield",
            "eos_auth_monitor:index",
            navactive=["eos_auth_monitor:"],
        )

    def render(self, request):
        if not has_app_access(request.user):
            return ""

        return MenuItemHook.render(self, request)


@hooks.register("menu_item_hook")
def register_menu():
    return AuthMonitorMenuItem()


@hooks.register("url_hook")
def register_urls():
    return UrlHook(urls, "eos_auth_monitor", r"^eos_auth_monitor/")

