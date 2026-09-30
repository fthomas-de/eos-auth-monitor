from django.utils.translation import gettext_lazy as _

from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

from . import urls
from .permissions import has_app_access
from .views import dashboard_corporation, dashboard_own


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


@hooks.register("secure_group_filters")
def register_filters():
    # read by allianceauth-securegroups; without it the hook is never asked
    from .models import CharacterProblemsFilter

    return [CharacterProblemsFilter]


# The same place on the dashboard as eos-invoices' widget. Alliance Auth sorts
# the widgets by this number and keeps the order of registration among equal
# ones, so the own account comes before the Corporation.
DASHBOARD_ORDER = 4


@hooks.register("dashboard_hook")
def register_dashboard_own():
    return hooks.DashboardItemHook(dashboard_own, DASHBOARD_ORDER)


@hooks.register("dashboard_hook")
def register_dashboard_corporation():
    return hooks.DashboardItemHook(dashboard_corporation, DASHBOARD_ORDER)

