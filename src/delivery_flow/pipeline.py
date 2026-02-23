"""
Pipeline Engine.
Core engine that executes pipeline stages in order.
"""

import time
import subprocess
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import PipelineConfig, StageConfig, EnvironmentManager

console = Console()


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class StageResult:
    """Result of a single stage execution."""
    name: str
    status: StageStatus = StageStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    output: str = ""
    error: str = ""
    return_code: int = 0
    attempt: int = 1
    max_attempts: int = 1

    @property
    def is_success(self) -> bool:
        return self.status == StageStatus.PASSED


@dataclass
class PipelineResult:
    """Complete pipeline execution result."""
    pipeline_id: str = ""
    pipeline_name: str = ""
    status: str = "pending"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    stage_results: List[StageResult] = field(default_factory=list)
    environment: str = "development"

    @property
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def passed_stages(self) -> int:
        return sum(1 for s in self.stage_results if s.is_success)

    @property
    def failed_stages(self) -> int:
        return sum(1 for s in self.stage_results if s.status == StageStatus.FAILED)

    @property
    def total_stages(self) -> int:
        return len(self.stage_results)

    @property
    def pass_rate(self) -> float:
        if self.total_stages == 0:
            return 0.0
        return (self.passed_stages / self.total_stages) * 100


class PipelineEngine:
    """Core pipeline execution engine."""

    def __init__(self, config: PipelineConfig, environment: str = "development"):
        self.config = config
        self.env_manager = EnvironmentManager(environment)
        self.pipeline_id = str(uuid.uuid4())[:8]
        self.hooks: Dict[str, List[Callable]] = {
            "before_pipeline": [],
            "after_pipeline": [],
            "before_stage": [],
            "after_stage": [],
        }

    def register_hook(self, event: str, callback: Callable):
        """Register a hook for pipeline events."""
        if event in self.hooks:
            self.hooks[event].append(callback)

    def _trigger_hooks(self, event: str, **kwargs):
        """Trigger all registered hooks for an event."""
        for callback in self.hooks.get(event, []):
            try:
                callback(**kwargs)
            except Exception as e:
                console.print(f"   Hook error: {e}", style="dim red")

    def run(self) -> PipelineResult:
        """Execute the complete pipeline."""
        result = PipelineResult(
            pipeline_id=self.pipeline_id,
            pipeline_name=self.config.name,
            environment=self.env_manager.env_name,
        )

        # Validate config
        errors = self.config.validate()
        if errors:
            console.print("\n  Configuration Errors:", style="bold red")
            for error in errors:
                console.print(f"   {error}", style="red")
            result.status = "failed"
            return result

        # Start pipeline
        result.start_time = datetime.now()
        self._print_pipeline_header()
        self._trigger_hooks("before_pipeline", config=self.config)

        # Export environment
        self.env_manager.export()

        # Execute stages
        all_passed = True
        for stage_config in self.config.stages:
            # Check dependencies
            if not self._check_dependencies(stage_config, result):
                stage_result = StageResult(
                    name=stage_config.name,
                    status=StageStatus.SKIPPED,
                )
                result.stage_results.append(stage_result)
                console.print(
                    f"\n   SKIP  {stage_config.name} (dependency not met)",
                    style="yellow",
                )
                continue

            # Execute stage
            stage_result = self._execute_stage(stage_config)
            result.stage_results.append(stage_result)

            if not stage_result.is_success:
                if stage_config.allow_failure:
                    console.print(
                        f"   Allowed failure for: {stage_config.name}",
                        style="yellow",
                    )
                else:
                    all_passed = False
                    console.print(
                        f"\n   Pipeline stopping due to stage failure: {stage_config.name}",
                        style="bold red",
                    )
                    break

        # Complete pipeline
        result.end_time = datetime.now()
        result.status = "passed" if all_passed else "failed"
        self._trigger_hooks("after_pipeline", result=result)
        self._print_pipeline_summary(result)

        return result

    def _execute_stage(self, stage_config: StageConfig) -> StageResult:
        """Execute a single pipeline stage with retry logic."""
        max_attempts = stage_config.retry_count + 1
        stage_result = StageResult(
            name=stage_config.name,
            max_attempts=max_attempts,
        )

        for attempt in range(1, max_attempts + 1):
            stage_result.attempt = attempt
            stage_result.start_time = datetime.now()

            if attempt > 1:
                console.print(
                    f"   Retry {attempt}/{max_attempts}: {stage_config.name}",
                    style="yellow",
                )
                stage_result.status = StageStatus.RETRYING

            console.print(
                f"\n   RUN   {stage_config.name} (attempt {attempt}/{max_attempts})",
                style="bold cyan",
            )
            console.print(f"         Command: {stage_config.command}", style="dim")

            self._trigger_hooks("before_stage", stage=stage_config, attempt=attempt)

            try:
                # Merge environments
                env = dict(list(dict(__import__('os').environ).items()))
                env.update(self.config.environment)
                env.update(stage_config.environment)

                # Execute command
                process = subprocess.run(
                    stage_config.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=stage_config.timeout,
                    env=env,
                )

                stage_result.output = process.stdout
                stage_result.error = process.stderr
                stage_result.return_code = process.returncode
                stage_result.end_time = datetime.now()
                stage_result.duration = (
                    stage_result.end_time - stage_result.start_time
                ).total_seconds()

                if process.returncode == 0:
                    stage_result.status = StageStatus.PASSED
                    console.print(
                        f"   PASS  {stage_config.name} ({stage_result.duration:.2f}s)",
                        style="bold green",
                    )
                    if process.stdout.strip():
                        for line in process.stdout.strip().split("\n")[:5]:
                            console.print(f"         {line}", style="dim")
                    break
                else:
                    stage_result.status = StageStatus.FAILED
                    console.print(
                        f"   FAIL  {stage_config.name} (exit code: {process.returncode})",
                        style="bold red",
                    )
                    if process.stderr.strip():
                        for line in process.stderr.strip().split("\n")[:3]:
                            console.print(f"         {line}", style="red dim")

            except subprocess.TimeoutExpired:
                stage_result.status = StageStatus.FAILED
                stage_result.error = f"Timed out after {stage_config.timeout}s"
                stage_result.end_time = datetime.now()
                stage_result.duration = stage_config.timeout
                console.print(
                    f"   TIMEOUT  {stage_config.name} ({stage_config.timeout}s)",
                    style="bold red",
                )

            except Exception as e:
                stage_result.status = StageStatus.FAILED
                stage_result.error = str(e)
                stage_result.end_time = datetime.now()
                console.print(
                    f"   ERROR  {stage_config.name}: {e}",
                    style="bold red",
                )

            self._trigger_hooks("after_stage", stage=stage_config, result=stage_result)

            # Wait before retry
            if attempt < max_attempts:
                time.sleep(2)

        return stage_result

    def _check_dependencies(
        self, stage: StageConfig, result: PipelineResult
    ) -> bool:
        """Check if all dependencies for a stage are met."""
        if not stage.depends_on:
            return True

        for dep_name in stage.depends_on:
            dep_result = next(
                (r for r in result.stage_results if r.name == dep_name), None
            )
            if dep_result is None or not dep_result.is_success:
                return False
        return True

    def _print_pipeline_header(self):
        """Print pipeline execution header."""
        console.print(
            Panel(
                f"Pipeline: [bold]{self.config.name}[/bold]\n"
                f"ID: {self.pipeline_id}\n"
                f"Environment: {self.env_manager.env_name}\n"
                f"Stages: {len(self.config.stages)}",
                title="DeliveryFlow - Pipeline Started",
                style="cyan",
            )
        )

    def _print_pipeline_summary(self, result: PipelineResult):
        """Print pipeline execution summary."""
        status_style = "bold green" if result.status == "passed" else "bold red"
        status_icon = "PASSED" if result.status == "passed" else "FAILED"

        # Stage results table
        table = Table(title="Pipeline Results", show_lines=True)
        table.add_column("#", style="dim", justify="center", width=4)
        table.add_column("Stage", style="white", min_width=20)
        table.add_column("Status", justify="center", width=12)
        table.add_column("Duration", justify="right", width=10)
        table.add_column("Attempts", justify="center", width=10)

        status_icons = {
            StageStatus.PASSED: ("PASS", "green"),
            StageStatus.FAILED: ("FAIL", "red"),
            StageStatus.SKIPPED: ("SKIP", "yellow"),
            StageStatus.PENDING: ("PEND", "dim"),
        }

        for i, sr in enumerate(result.stage_results, 1):
            icon, style = status_icons.get(sr.status, ("???", "dim"))
            table.add_row(
                str(i),
                sr.name,
                icon,
                f"{sr.duration:.2f}s",
                f"{sr.attempt}/{sr.max_attempts}",
                style=style,
            )

        console.print(table)

        # Summary panel
        console.print(
            Panel(
                f"Status: {status_icon}\n"
                f"Stages: {result.passed_stages}/{result.total_stages} passed\n"
                f"Duration: {result.duration:.2f}s\n"
                f"Pass Rate: {result.pass_rate:.1f}%",
                title="Pipeline Summary",
                style=status_style,
            )
        )
