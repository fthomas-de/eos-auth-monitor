"""aa-structures: is a Corporation set up as a working structure owner?"""

from django.apps import apps

from . import problem

# Owner properties aa-structures itself combines into are_all_syncs_ok
SYNCS = (
    ("Structures", "is_structure_sync_fresh"),
    ("Notifications", "is_notification_sync_fresh"),
    ("Forwarding", "is_forwarding_sync_fresh"),
    ("Assets", "is_assets_sync_fresh"),
)


def corporation_problems(corporation_ids, keys) -> dict[int, list[dict]]:
    Owner = apps.get_model("structures", "Owner")

    owners = {
        owner.corporation.corporation_id: owner
        for owner in Owner.objects.filter(corporation__corporation_id__in=corporation_ids).select_related("corporation")
    }
    result = {}

    for corporation_id in corporation_ids:
        found = []
        owner = owners.get(corporation_id)

        if owner is None:
            if "structures_no_owner" in keys:
                found.append(problem("structures_no_owner"))
        elif not owner.is_active:
            # a switched off owner does not sync; its characters and syncs say nothing
            if "structures_owner_inactive" in keys:
                found.append(problem("structures_owner_inactive"))
        else:
            if "structures_no_character" in keys and not owner.characters.filter(is_enabled=True).exists():
                found.append(problem("structures_no_character"))
            if "structures_sync_failing" in keys and not owner.are_all_syncs_ok:
                failing = [label for label, attribute in SYNCS if not getattr(owner, attribute)]
                found.append(problem("structures_sync_failing", failing))

        if found:
            result[corporation_id] = found

    return result
