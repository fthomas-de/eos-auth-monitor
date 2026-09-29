from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from . import __version__, progress
from . import snapshot as snapshots
from .forms import MonitorConfigurationForm
from .models import MonitorConfiguration
from .permissions import (
    BASIC_ACCESS,
    MANAGE_SETTINGS,
    VIEW_ALL,
    any_permission_required,
    can_view_corporation,
    own_corporation_id,
)
from .report import PHASE_LABELS, Report
from .tasks import update_snapshot


def _render(request, template, context=None):
    return render(request, template, {"version": __version__, **(context or {})})


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


@any_permission_required(BASIC_ACCESS, VIEW_ALL, MANAGE_SETTINGS)
def index(request):
    user = request.user
    if not user.has_perm(VIEW_ALL):
        corporation_id = own_corporation_id(user)
        if user.has_perm(BASIC_ACCESS) and corporation_id:
            return redirect("eos_auth_monitor:corporation", corporation_id)
        return redirect("eos_auth_monitor:settings")

    report = _report()
    return _render(
        request,
        "eos_auth_monitor/index.html",
        {
            **_state(report),
            "cockpit": report.cockpit() if report else [],
            "connections": report.connections() if report else [],
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
        {**_state(report), "corporation": corporation, "service": service},
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
            "rows": rows,
            "linked": sum(account.is_linked(service.key) for _, account in rows),
        },
    )


@any_permission_required(MANAGE_SETTINGS)
def settings(request):
    form = MonitorConfigurationForm(request.POST or None, instance=MonitorConfiguration.get_solo())

    if request.method == "POST" and form.is_valid():
        form.save()
        _start_rebuild()
        messages.success(request, _("Settings saved. The overview is being rebuilt."))
        return redirect("eos_auth_monitor:settings")

    return _render(request, "eos_auth_monitor/settings.html", {**_state(_report()), "form": form})


def _start_rebuild():
    # shown at once, before a worker has picked the task up
    progress.queued()
    update_snapshot.delay()


@any_permission_required(VIEW_ALL, MANAGE_SETTINGS)
@require_POST
def rebuild(request):
    _start_rebuild()
    messages.info(request, _("The overview is being rebuilt."))
    # back to the page the button was on; only our own pages, never elsewhere
    target = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = "eos_auth_monitor:index"
    return redirect(target or "eos_auth_monitor:index")


@any_permission_required(BASIC_ACCESS, VIEW_ALL, MANAGE_SETTINGS)
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
