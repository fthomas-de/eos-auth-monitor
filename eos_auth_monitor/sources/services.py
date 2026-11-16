"""Which Auth accounts have linked Discord, Mumble, QQ or Telegram."""

from django.apps import apps

# service key -> (app label, model, filter for "linked"); every model has a
# one-to-one "user" field
MODELS = {
    "discord": ("discord", "DiscordUser", {}),
    "mumble": ("mumble", "MumbleUser", {}),
    # a Binding row only exists once verified or trusted; pending ones are BindCodes
    "qq": ("qqbot", "Binding", {}),
    # a TelegramUser row appears when linking starts; is_active is about
    # notifications, not the link
    "telegram": ("aa_discord_telegram_bridge", "TelegramUser", {"telegram_user_id__isnull": False}),
}


def linked_user_ids(service_key: str, users) -> set[int]:
    app_label, model_name, filters = MODELS[service_key]
    model = apps.get_model(app_label, model_name)
    return set(model.objects.filter(user__in=users, **filters).values_list("user_id", flat=True))


def mumble_connections(user_ids) -> dict[int, tuple]:
    """Per account with Mumble linked: when it last connected and disconnected, as Auth's authenticator wrote it."""
    model = apps.get_model("mumble", "MumbleUser")
    return {
        user_id: (connect, disconnect)
        for user_id, connect, disconnect in model.objects.filter(user_id__in=user_ids).values_list(
            "user_id", "last_connect", "last_disconnect"
        )
    }
