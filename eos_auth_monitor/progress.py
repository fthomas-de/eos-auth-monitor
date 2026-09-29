"""How far the snapshot task has got, for the progress bar on the pages.

One entry in the cache. That is enough because the task runs once at a time
(QueueOnce): there is never a second run that could write over the first.
"""

from django.core.cache import cache
from django.utils import timezone

KEY = "eos_auth_monitor:progress"
# long enough for a slow run, short enough that a crashed worker's "running"
# does not stay on the page for good
TIMEOUT = 60 * 60

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"

# the steps of snapshot.build(), in order; the bar moves on per step
PHASES = ("accounts", "characters", "corporations", "services", "members", "store")


def get() -> dict:
    return cache.get(KEY) or {"state": None}


def _set(**values):
    cache.set(KEY, {"updated_at": timezone.now().isoformat(), **values}, TIMEOUT)


def queued():
    # a run already going keeps its bar; the new request joins it
    if get().get("state") != RUNNING:
        _set(state=QUEUED, percent=0, phase=None)


def withdrawn():
    # the task never reached the broker: no worker will pick it up, so no bar
    if get().get("state") == QUEUED:
        cache.delete(KEY)


def step(phase: str, done: int = 0, total: int = 1):
    index = PHASES.index(phase)
    fraction = done / total if total else 1
    _set(state=RUNNING, percent=round(100 * (index + fraction) / len(PHASES)), phase=phase)


def finished():
    _set(state=DONE, percent=100, phase=None)


def failed():
    _set(state=FAILED, percent=0, phase=None)
