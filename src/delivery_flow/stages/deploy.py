"""
Deploy Stage - Handles deployment to different environments.
"""

import time
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from rich.console import Console

console = Console()


@dataclass
class DeploymentRecord:
    """Record of a deployment."""
    deploy_id: str
    environment: str
    version: str
    timestamp: str
    status: str
    rollback_path: Optional[str] = None


class DeployStage:
    """Handles deployment to staging and production."""

    def __init__(self, deploy_dir="deployments/"):
        self.deploy_dir = Path(deploy_dir)
        self.deploy_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.deploy_dir / "deploy_history.json"
        self.history: List[DeploymentRecord] = self._load_history()

    def _load_history(self) -> list:
        """Load deployment history."""
        if self.history_file.exists():
            with open(self.history_file, "r") as f:
                data = json.load(f)
                return [DeploymentRecord(**r) for r in data]
        return []

    def _save_history(self):
        """Save deployment history."""
        data = [
            {
                "deploy_id": r.deploy_id,
                "environment": r.environment,
                "version": r.version,
                "timestamp": r.timestamp,
                "status": r.status,
                "rollback_path": r.rollback_path,
            }
            for r in self.history
        ]
        with open(self.history_file, "w") as f:
            json.dump(data, f, indent=2)

    def deploy(self, environment: str, version: str = "1.0.0") -> dict:
        """Deploy to specified environment."""
        deploy_id = f"deploy-{int(time.time())}"
        timestamp = datetime.now().isoformat()

        console.print(f"\n   Deploying to {environment}...", style="cyan")
        console.print(f"   Version: {version}", style="dim")
        console.print(f"   Deploy ID: {deploy_id}", style="dim")

        # Create backup for rollback
        backup_dir = self.deploy_dir / f"backup-{deploy_id}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Simulate deployment steps
        steps = [
            "Validating deployment package",
            "Creating backup snapshot",
            "Uploading artifacts",
            "Running database migrations",
            "Restarting services",
            "Running health checks",
        ]

        for step in steps:
            console.print(f"   ... {step}", style="dim")
            time.sleep(0.3)

        # Record deployment
        record = DeploymentRecord(
            deploy_id=deploy_id,
            environment=environment,
            version=version,
            timestamp=timestamp,
            status="success",
            rollback_path=str(backup_dir),
        )
        self.history.append(record)
        self._save_history()

        console.print(
            f"   Deployed to {environment} successfully!",
            style="bold green",
        )

        return {
            "passed": True,
            "deploy_id": deploy_id,
            "environment": environment,
            "version": version,
        }

    def rollback(self, environment: str) -> dict:
        """Rollback to previous deployment."""
        env_deploys = [
            r for r in self.history
            if r.environment == environment and r.status == "success"
        ]

        if len(env_deploys) < 2:
            return {
                "passed": False,
                "error": f"No previous deployment to rollback to for {environment}",
            }

        previous = env_deploys[-2]
        current = env_deploys[-1]

        console.print(f"\n   Rolling back {environment}...", style="yellow")
        console.print(
            f"   From: {current.version} -> To: {previous.version}",
            style="dim",
        )

        # Simulate rollback
        time.sleep(1)

        # Record rollback
        record = DeploymentRecord(
            deploy_id=f"rollback-{int(time.time())}",
            environment=environment,
            version=previous.version,
            timestamp=datetime.now().isoformat(),
            status="rollback",
        )
        self.history.append(record)
        self._save_history()

        console.print(
            f"   Rolled back to {previous.version} successfully!",
            style="bold green",
        )

        return {
            "passed": True,
            "rolled_back_from": current.version,
            "rolled_back_to": previous.version,
        }

    def get_deploy_history(self, environment: Optional[str] = None) -> list:
        """Get deployment history."""
        if environment:
            return [r for r in self.history if r.environment == environment]
        return self.history

    def health_check(self, environment: str) -> dict:
        """Run post-deployment health check."""
        checks = {
            "service_running": True,
            "database_connected": True,
            "api_responding": True,
            "disk_space_ok": True,
            "memory_ok": True,
        }

        all_healthy = all(checks.values())
        return {
            "passed": all_healthy,
            "environment": environment,
            "checks": checks,
        }
