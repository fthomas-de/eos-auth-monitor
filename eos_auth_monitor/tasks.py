from celery import shared_task

from allianceauth.services.hooks import get_extension_logger
from allianceauth.services.tasks import QueueOnce

from . import progress, snapshot

logger = get_extension_logger(__name__)


# once: a click on "Rebuild now" while the scheduled run is still going would
# only compute the same thing twice
@shared_task(base=QueueOnce, once={"graceful": True})
def update_snapshot():
    """Rebuild the overview from the data of the other apps."""
    try:
        snapshot.update(on_step=progress.step)
    except Exception:
        progress.failed()
        raise
    progress.finished()
