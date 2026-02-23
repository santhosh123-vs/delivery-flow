"""Unit tests for notification plugin."""

import pytest
from src.delivery_flow.plugins.notifications import NotificationManager


class TestNotificationManager:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.notifier = NotificationManager()

    def test_notify_start(self):
        self.notifier.notify_start("test-pipeline", "staging")
        log = self.notifier.get_log()
        assert len(log) == 1
        assert log[0]["type"] == "pipeline_start"
        assert log[0]["pipeline"] == "test-pipeline"

    def test_notify_complete_success(self):
        self.notifier.notify_complete("test-pipeline", "passed", 5.0)
        log = self.notifier.get_log()
        assert len(log) == 1
        assert log[0]["status"] == "passed"

    def test_notify_complete_failure(self):
        self.notifier.notify_complete("test-pipeline", "failed", 3.0)
        log = self.notifier.get_log()
        assert log[0]["status"] == "failed"

    def test_notify_stage_complete(self):
        self.notifier.notify_stage_complete("build", "passed", 2.5)
        log = self.notifier.get_log()
        assert log[0]["type"] == "stage_complete"
        assert log[0]["stage"] == "build"

    def test_notify_rollback(self):
        self.notifier.notify_rollback("staging", "1.1.0", "1.0.0")
        log = self.notifier.get_log()
        assert log[0]["type"] == "rollback"

    def test_multiple_notifications(self):
        self.notifier.notify_start("pipeline", "staging")
        self.notifier.notify_stage_complete("lint", "passed", 1.0)
        self.notifier.notify_stage_complete("test", "passed", 3.0)
        self.notifier.notify_complete("pipeline", "passed", 4.0)
        log = self.notifier.get_log()
        assert len(log) == 4

    def test_save_log(self, tmp_path):
        self.notifier.notify_start("pipeline", "staging")
        log_file = str(tmp_path / "logs" / "notifications.json")
        self.notifier.save_log(log_file)
        import json
        from pathlib import Path
        assert Path(log_file).exists()
        with open(log_file, "r") as f:
            data = json.load(f)
        assert len(data) == 1

    def test_empty_log(self):
        log = self.notifier.get_log()
        assert len(log) == 0

    def test_notification_has_timestamp(self):
        self.notifier.notify_start("pipeline", "dev")
        log = self.notifier.get_log()
        assert "timestamp" in log[0]

    def test_notification_has_message(self):
        self.notifier.notify_start("my-pipeline", "staging")
        log = self.notifier.get_log()
        assert "message" in log[0]
        assert "my-pipeline" in log[0]["message"]
