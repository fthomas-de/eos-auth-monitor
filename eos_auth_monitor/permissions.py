"""Who may use the app and which Corporations they see."""

from functools import wraps

from django.contrib.auth.decorators import login_required, user_passes_test

BASIC_ACCESS = "eos_auth_monitor.basic_access"
VIEW_ALL = "eos_auth_monitor.view_all"
MANAGE_SETTINGS = "eos_auth_monitor.manage_settings"

APP_PERMISSIONS = (BASIC_ACCESS, VIEW_ALL, MANAGE_SETTINGS)


def has_app_access(user) -> bool:
    # any one of them opens the app; what a page shows is up to its own check
    return any(user.has_perm(perm) for perm in APP_PERMISSIONS)


def any_permission_required(*perms):
    """login_required plus at least one of ``perms``."""

    def decorator(view):
        @login_required
        @user_passes_test(lambda user: any(user.has_perm(perm) for perm in perms))
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def own_corporation_id(user) -> int | None:
    main = user.profile.main_character
    return main.corporation_id if main else None


def can_view_corporation(user, corporation_id: int) -> bool:
    """view_all sees every Corporation, basic_access the one of the own main."""
    if user.has_perm(VIEW_ALL):
        return True
    return user.has_perm(BASIC_ACCESS) and own_corporation_id(user) == corporation_id
