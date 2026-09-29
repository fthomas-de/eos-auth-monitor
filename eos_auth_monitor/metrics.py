"""What one snapshot build cost, stored inside the snapshot and shown as a
footer on the pages, so a large Alliance shows where the time goes.

Measured around the build only; a page render reads the stored JSON and
costs one query.
"""

import json
import time
from contextlib import ExitStack

from django.db import connection


class Measurement:
    """Times the phases of a build and counts its database queries.

    Use as a context manager and pass `on_step` to the build; the phases are
    the ones `progress.step` already knows, each ending when the next begins.
    """

    def __init__(self, on_step):
        self._on_step = on_step
        self._stack = ExitStack()
        self._phase = None
        self._phase_started = None
        self.phases = {}
        self.queries = 0
        self.query_seconds = 0.0
        self._started = None
        self.seconds = 0.0

    def __enter__(self):
        self._stack.enter_context(connection.execute_wrapper(self._count_query))
        self._started = time.perf_counter()
        return self

    def __exit__(self, *exc_info):
        self._end_phase()
        self.seconds = time.perf_counter() - self._started
        self._stack.close()

    def _count_query(self, execute, sql, params, many, context):
        started = time.perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            self.queries += 1
            self.query_seconds += time.perf_counter() - started

    def _end_phase(self):
        if self._phase is not None:
            elapsed = time.perf_counter() - self._phase_started
            self.phases[self._phase] = self.phases.get(self._phase, 0.0) + elapsed

    def on_step(self, phase, done=0, total=1):
        # the members phase reports once per Corporation: only a change of phase closes one
        if phase != self._phase:
            self._end_phase()
            self._phase = phase
            self._phase_started = time.perf_counter()
        self._on_step(phase, done, total)

    def result(self, data: dict) -> dict:
        """The figures to store next to the snapshot data they describe."""
        corporations = data["corporations"]
        accounts = [account for row in corporations for account in row["accounts"]]
        return {
            "seconds": round(self.seconds, 2),
            "phases": {phase: round(seconds, 2) for phase, seconds in self.phases.items()},
            "queries": self.queries,
            "query_seconds": round(self.query_seconds, 2),
            "corporations": len(corporations),
            "accounts": len(accounts),
            "characters": sum(len(account["characters"]) for account in accounts),
            "member_lists": sum(1 for row in corporations if row.get("member_count") is not None),
            "payload_bytes": len(json.dumps(data)),
        }
