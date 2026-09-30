from django.urls import path

from . import views

app_name = "eos_auth_monitor"

urlpatterns = [
    path("", views.index, name="index"),
    path("corporation/<int:corporation_id>/", views.corporation, name="corporation"),
    path("corporation/<int:corporation_id>/export/", views.corporation_export, name="corporation_export"),
    path(
        "corporation/<int:corporation_id>/service/<str:service_key>/",
        views.corporation_service,
        name="corporation_service",
    ),
    path("account/<int:user_id>/", views.account, name="account"),
    path("account/own/", views.own_account, name="own_account"),
    path("service/<str:service_key>/", views.service, name="service"),
    path("character-audit/", views.character_audit, name="character_audit"),
    path("directors/<str:group_key>/", views.directors, name="directors"),
    path("settings/", views.settings, name="settings"),
    path("rebuild/", views.rebuild, name="rebuild"),
    path("rebuild/progress/", views.rebuild_progress, name="rebuild_progress"),
]
