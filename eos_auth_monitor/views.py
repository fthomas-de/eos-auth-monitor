from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from kombu.exceptions import OperationalError

from . import __version__, progress
from . import snapshot as snapshots
from .forms import MonitorConfigurationForm
from .models import MonitorConfiguration
from .permissions import (
    APP_PERMISSIONS,
    BASIC_ACCESS,
    MANAGE_SETTINGS,
    VIEW_ALL,
    VIEW_OWN,
    any_permission_required,
    can_view_corporation,
    own_corporation_id,
)
from .report import PHASE_LABELS, Report
from .tasks import update_snapshot


# which page of the app this is, shown under its name; a service list is
# named after its service instead
LOCATIONS = {
    "eos_auth_monitor/index.html": _("Corporation overview"),
    "eos_auth_monitor/corporation.html": _("Corporation details"),
    "eos_auth_monitor/account.html": _("Main details"),
    "eos_auth_monitor/settings.html": _("Settings"),
}


def _render(request, template, context=None):
    return render(
        request,
        template,
        {"version": __version__, "location": LOCATIONS.get(template, ""), **(context or {})},
    )


def _report() -> Report | None:
    snapshot = snapshots.current()
    return Report(snapshot) if snapshot else None


def _state(report: Report | None) -> dict:
    """What every page says about the data before showing any."""
    config = MonitorConfiguration.get_solo()
    alliance = config.alliance
    return {
        "config": config,
        "report": report,
        # the snapshot is rebuilt after a change; until then it is of the old Alliance
        "outdated": bool(report and alliance and report.alliance_id != alliance.alliance_id),
    }


def _visible_corporation(request, report, corporation_id):
    """The Corporation from the snapshot, or None when it is not in it.

    None is not a 404: a CEO whose main is outside the Alliance, or whose
    Corporation joined after the last run, gets a notice instead.
    """
    if not can_view_corporation(request.user, corporation_id):
        raise PermissionDenied
    return report.corporation(corporation_id) if report else None


@any_permission_required(*APP_PERMISSIONS)
def index(request):
    user = request.user
    if not user.has_perm(VIEW_ALL):
        corporation_id = own_corporation_id(user)
        if user.has_perm(BASIC_ACCESS) and corporation_id:
            return redirect("eos_auth_monitor:corporation", corporation_id)
        if user.has_perm(VIEW_OWN):
            return redirect("eos_auth_monitor:own_account")
        return redirect("eos_auth_monitor:settings")

    report = _report()
    table_columns, table_lines = report.overview_table() if report else ([], [])
    return _render(
        request,
        "eos_auth_monitor/index.html",
        {
            **_state(report),
            "cockpit": report.cockpit() if report else [],
            "connections": report.connections() if report else [],
            "table_columns": table_columns,
            "table_lines": table_lines,
        },
    )


@any_permission_required(BASIC_ACCESS, VIEW_ALL)
def corporation(request, corporation_id):
    report = _report()
    context = _state(report)
    context["corporation"] = _visible_corporation(request, report, corporation_id)
    return _render(request, "eos_auth_monitor/corporation.html", context)


@any_permission_required(BASIC_ACCESS, VIEW_ALL)
def account(request, user_id):
    report = _report()
    if report is None:
        raise Http404
    corporation, account = report.account(user_id)
    if account is None:
        raise Http404
    if not can_view_corporation(request.user, corporation.id):
        raise PermissionDenied
    return _render(
        request,
        "eos_auth_monitor/account.html",
        {**_state(report), "corporation": corporation, "account": account},
    )


@any_permission_required(VIEW_OWN)
def own_account(request):
    """The viewer's own account, for members: their problems and what to do, nothing about others."""
    report = _report()
    corporation, account = report.account(request.user.pk) if report else (None, None)
    return _render(
        request,
        "eos_auth_monitor/account.html",
        {**_state(report), "corporation": corporation, "account": account, "own": True, "location": _("My account")},
    )


@any_permission_required(BASIC_ACCESS, VIEW_ALL)
def corporation_service(request, corporation_id, service_key):
    report = _report()
    corporation = _visible_corporation(request, report, corporation_id)
    service = report.service(service_key) if report else None
    if corporation is None or service is None:
        raise Http404
    return _render(
        request,
        "eos_auth_monitor/corporation_service.html",
        {**_state(report), "corporation": corporation, "service": service, "location": service.label},
    )


@any_permission_required(VIEW_ALL)
def service(request, service_key):
    report = _report()
    service = report.service(service_key) if report else None
    if service is None:
        raise Http404
    rows = sorted(
        ((corporation, account) for corporation in report.corporations for account in corporation.accounts),
        key=lambda row: (-row[1].problem_count, row[0].name.lower(), row[1].main_name.lower()),
    )
    return _render(
        request,
        "eos_auth_monitor/service.html",
        {
            **_state(report),
            "service": service,
            "location": service.label,
            "rows": rows,
            "linked": sum(account.is_linked(service.key) for _, account in rows),
        },
    )


@any_permission_required(MANAGE_SETTINGS)
def settings(request):
    form = MonitorConfigurationForm(request.POST or None, instance=MonitorConfiguration.get_solo())

    if request.method == "POST" and form.is_valid():
        form.save()
        if _start_rebuild():
            messages.success(request, _("Settings saved. The overview is being rebuilt."))
        else:
            messages.warning(
                request,
                _("Settings saved, but the task queue is not reachable: the overview is rebuilt once it is back."),
            )
        return redirect("eos_auth_monitor:settings")

    return _render(request, "eos_auth_monitor/settings.html", {**_state(_report()), "form": form})


def _start_rebuild() -> bool:
    """Queue the task; False when the broker cannot take it."""
    # shown at once, before a worker has picked the task up
    progress.queued()
    try:
        update_snapshot.delay()
    except OperationalError:
        # Redis or the broker is down; a 500 would hide that the settings were saved
        progress.withdrawn()
        return False
    return True


@any_permission_required(VIEW_ALL, MANAGE_SETTINGS)
@require_POST
def rebuild(request):
    if _start_rebuild():
        messages.info(request, _("The overview is being rebuilt."))
    else:
        messages.error(request, _("The rebuild could not be started: the task queue is not reachable."))
    # back to the page the button was on; only our own pages, never elsewhere
    target = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = "eos_auth_monitor:index"
    return redirect(target or "eos_auth_monitor:index")


@any_permission_required(*APP_PERMISSIONS)
def rebuild_progress(request):
    """State of the task for the progress bar; polled while it runs."""
    state = progress.get()
    return JsonResponse(
        {
            "state": state.get("state"),
            "percent": state.get("percent", 0),
            "phase": str(PHASE_LABELS.get(state.get("phase"), "")),
        }
    )
