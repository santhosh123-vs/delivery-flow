"""
Notification Plugin.
Sends pipeline status notifications.
"""

import json
from datetime import datetime
from typing import Dict, Optional
from rich.console import Console

console = Console()


class NotificationManager:
    """Manages pipeline notifications."""

    def __init__(self):
        self.notifications_log = []

    def notify_start(self, pipeline_name: str, environment: str):
        """Notify pipeline start."""
        msg = {
            "type": "pipeline_start",
            "pipeline": pipeline_name,
            "environment": environment,
            "timestamp": datetime.now().isoformat(),
            "message": f"Pipeline '{pipeline_name}' started for {environment}",
        }
        self.notifications_log.append(msg)
        console.print(f"   [Notify] Pipeline started: {pipeline_name}", style="dim cyan")

    def notify_stage_complete(self, stage_name: str, status: str, duration: float):
        """Notify stage completion."""
        msg = {
            "type": "stage_complete",
            "stage": stage_name,
            "status": status,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
        }
        self.notifications_log.append(msg)

    def notify_complete(self, pipeline_name: str, status: str, duration: float):
        """Notify pipeline completion."""
        emoji = "SUCCESS" if status == "passed" else "FAILURE"
        msg = {
            "type": "pipeline_complete",
            "pipeline": pipeline_name,
            "status": status,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "message": f"Pipeline '{pipeline_name}' {emoji} in {duration:.2f}s",
        }
        self.notifications_log.append(msg)
        style = "dim green" if status == "passed" else "dim red"
        console.print(f"   [Notify] Pipeline {emoji}: {pipeline_name}", style=style)

    def notify_rollback(self, environment: str, from_version: str, to_version: str):
        """Notify rollback."""
        msg = {
            "type": "rollback",
            "environment": environment,
            "from_version": from_version,
            "to_version": to_version,
            "timestamp": datetime.now().isoformat(),
        }
        self.notifications_log.append(msg)
        console.print(
            f"   [Notify] ROLLBACK: {environment} {from_version} -> {to_version}",
            style="dim yellow",
        )

    def get_log(self) -> list:
        """Get all notifications."""
        return self.notifications_log

    def save_log(self, filepath: str = "logs/notifications.json"):
        """Save notifications to file."""
        from pathlib import Path
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self.notifications_log, f, indent=2)
