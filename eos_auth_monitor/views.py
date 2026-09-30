import csv

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import get_valid_filename
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
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
from .report import CORPORATION_GROUP_LABELS, PHASE_LABELS, Report
from .tasks import update_snapshot


# which page of the app this is, shown under its name; a service list is
# named after its service instead
LOCATIONS = {
    "eos_auth_monitor/index.html": _("Corporation overview"),
    "eos_auth_monitor/corporation.html": _("Corporation details"),
    "eos_auth_monitor/account.html": _("Main details"),
    "eos_auth_monitor/settings.html": _("Settings"),
}


# the tab of the app navbar a page belongs to; the pages about one
# Corporation choose theirs by whose Corporation it is (_corporation_nav)
NAV_OWN = "own"
NAV_CORPORATION = "corporation"
NAV_ALLIANCE = "alliance"
NAV_SETTINGS = "settings"


def _render(request, template, context=None, nav=NAV_ALLIANCE):
    user = request.user
    return render(
        request,
        template,
        {
            "version": __version__,
            "location": LOCATIONS.get(template, ""),
            "nav": nav,
            # the My Corporation tab: whoever may see the own main's Corporation
            "nav_corporation_id": (
                own_corporation_id(user) if user.has_perm(BASIC_ACCESS) or user.has_perm(VIEW_ALL) else None
            ),
            **(context or {}),
        },
    )


def _corporation_nav(user, corporation_id) -> str:
    # leadership looking at another Corporation came from the Alliance overview
    return NAV_CORPORATION if corporation_id == own_corporation_id(user) else NAV_ALLIANCE


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
    context["charlink_url"] = _charlink_url()
    # the cards and to-dos of mains elsewhere link to their account only for those who may see it
    context["can_view_all"] = request.user.has_perm(VIEW_ALL)
    return _render(
        request, "eos_auth_monitor/corporation.html", context, _corporation_nav(request.user, corporation_id)
    )


@any_permission_required(BASIC_ACCESS, VIEW_ALL)
def corporation_export(request, corporation_id):
    """The names of the to-do list as a CSV file: one group (?group=) with a name per line, or all of it.

    For a spreadsheet or a mail merge, where the copy button's comma list does
    not fit. Only what the Corporation page shows, to the same viewers.
    """
    report = _report()
    corporation = _visible_corporation(request, report, corporation_id)
    if corporation is None:
        raise Http404
    group = request.GET.get("group")
    rows = [row for row in corporation.todo_rows if not group or row.group == group]
    if not rows:
        raise Http404

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    filename = get_valid_filename(f"{corporation.ticker}-{group or 'todo'}.csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    # the byte order mark makes Excel read the file as UTF-8
    response.write("\ufeff")
    writer = csv.writer(response)
    # Alliance Auth translates "Name" itself, and its catalogue would win
    name = pgettext_lazy("eos-auth-monitor", "Name")
    if group:
        writer.writerow([name])
        writer.writerows([_csv_cell(row.name)] for row in rows)
    else:
        writer.writerow([_("Problem"), name])
        writer.writerows([_csv_cell(str(row.label)), _csv_cell(row.name)] for row in rows)
    return response


def _csv_cell(value: str) -> str:
    # a spreadsheet runs a cell that starts like this as a formula
    return f"'{value}" if value[:1] in ("=", "+", "-", "@", "\t", "\r") else value


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
        {
            **_state(report),
            "corporation": corporation,
            "account": account,
            "own": False,
            # the player fixes their characters and the Director the Corporation's tokens in aa-charlink
            "charlink_url": _charlink_url(),
        },
        _corporation_nav(request.user, corporation.id),
    )


def _charlink_url() -> str | None:
    """aa-charlink's page, where a player adds a character to every app at once; None without the app."""
    try:
        return reverse("charlink:index")
    except NoReverseMatch:
        return None


@any_permission_required(VIEW_OWN)
def own_account(request):
    """The viewer's own account, for members: their problems and what to do, nothing about others."""
    report = _report()
    corporation, account = report.account(request.user.pk) if report else (None, None)
    return _render(
        request,
        "eos_auth_monitor/account.html",
        {
            **_state(report),
            "corporation": corporation,
            "account": account,
            "own": True,
            "location": _("My account"),
            # a member fixes their own tokens in aa-charlink; without it the check's own app stays the link
            "charlink_url": _charlink_url(),
        },
        NAV_OWN,
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
        {
            **_state(report),
            "corporation": corporation,
            "service": service,
            "location": service.label,
            # the Corporation header links its problems to aa-charlink, as on the Corporation page
            "charlink_url": _charlink_url(),
        },
        _corporation_nav(request.user, corporation_id),
    )


@any_permission_required(VIEW_ALL)
def service(request, service_key):
    report = _report()
    service = report.service(service_key) if report else None
    if service is None:
        raise Http404
    rows = report.accounts_by_problems()
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


@any_permission_required(VIEW_ALL)
def character_audit(request):
    """Every main of the Alliance with the character checks its account fails, like a service list."""
    report = _report()
    if report is None or not report.has_character_checks:
        raise Http404
    rows = report.accounts_by_problems()
    return _render(
        request,
        "eos_auth_monitor/character_audit.html",
        {
            **_state(report),
            "location": _("Character Audit"),
            "rows": rows,
            "complete": sum(not account.has_problems for _, account in rows),
        },
    )


@any_permission_required(VIEW_ALL)
def directors(request, group_key):
    """Every Director of the Alliance and whether it has the token of a Corporation-level app."""
    report = _report()
    if report is None or not report.has_director_list(group_key):
        raise Http404
    rows = report.directors(group_key)
    label = CORPORATION_GROUP_LABELS[group_key]
    return _render(
        request,
        "eos_auth_monitor/directors.html",
        {
            **_state(report),
            "location": label,
            "label": label,
            "rows": rows,
            "with_token": sum(has_token for _, _, has_token in rows),
            # Directors nobody could read the roles of are missing from the list
            "unreadable": [corporation for corporation in report.corporations if corporation.no_director_token],
        },
    )


@any_permission_required(MANAGE_SETTINGS)
def settings(request):
    form = MonitorConfigurationForm(request.POST or None, instance=MonitorConfiguration.get_solo())

    if request.method == "POST" and form.is_valid():
        form.save()
        # the pages read the notice straight from the settings: it alone is no reason to spend ESI calls
        if form.changed_data == ["member_notice"]:
            messages.success(request, _("Settings saved."))
        elif _start_rebuild():
            messages.success(request, _("Settings saved. The overview is being rebuilt."))
        else:
            messages.warning(
                request,
                _("Settings saved, but the task queue is not reachable: the overview is rebuilt once it is back."),
            )
        return redirect("eos_auth_monitor:settings")

    return _render(request, "eos_auth_monitor/settings.html", {**_state(_report()), "form": form}, NAV_SETTINGS)


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


# Widgets for Alliance Auth's own dashboard. Not URLs - its dashboard_hook
# calls them directly and drops an empty string, as eos-invoices does. They
# hide without the permission and wherever the snapshot has nothing about the
# viewer (no snapshot yet, main outside the Alliance): the app's pages explain
# those, a widget would only take room. Without problems they still show, so
# a glance tells "all fine" from "not loaded".


def dashboard_own(request):
    """The viewer's own account in short: which checks fail, which services are linked."""
    if not request.user.has_perm(VIEW_OWN):
        return ""
    report = _report()
    _corporation, account = report.account(request.user.pk) if report else (None, None)
    if account is None:
        return ""
    return render_to_string("eos_auth_monitor/dashboard.own.html", {"account": account}, request=request)


def dashboard_corporation(request):
    """The own main's Corporation in short, for its CEO: its problems and the to-do groups."""
    if not request.user.has_perm(BASIC_ACCESS):
        return ""
    corporation_id = own_corporation_id(request.user)
    report = _report()
    corporation = report.corporation(corporation_id) if report and corporation_id else None
    if corporation is None:
        return ""
    return render_to_string(
        "eos_auth_monitor/dashboard.corporation.html", {"corporation": corporation}, request=request
    )
