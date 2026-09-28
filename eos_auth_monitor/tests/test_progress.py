from unittest.mock import patch

from eos_auth_monitor import progress
from eos_auth_monitor.tasks import update_snapshot

from .base import MonitorTestCase


class TestProgress(MonitorTestCase):
    def test_should_know_nothing_before_a_run(self):
        self.assertEqual(progress.get(), {"state": None})

    def test_should_move_on_per_phase(self):
        progress.step("accounts")
        self.assertEqual(progress.get()["percent"], 0)

        progress.step("members", 1, 2)
        # members is the fifth of six phases, half done
        self.assertEqual(progress.get()["percent"], round(100 * 4.5 / 6))
        self.assertEqual(progress.get()["state"], progress.RUNNING)

    def test_should_not_reset_a_running_bar_when_queued_again(self):
        progress.step("services")
        progress.queued()

        self.assertEqual(progress.get()["state"], progress.RUNNING)

    def test_should_report_the_end_of_the_task(self):
        with patch("eos_auth_monitor.tasks.snapshot.update") as update:
            update_snapshot.run()

        self.assertEqual(update.call_args.kwargs, {"on_step": progress.step})
        self.assertEqual(progress.get()["state"], progress.DONE)

    def test_should_report_a_failed_task(self):
        with patch("eos_auth_monitor.tasks.snapshot.update", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                update_snapshot.run()

        self.assertEqual(progress.get()["state"], progress.FAILED)
