"""
Pipeline Configuration Manager.
Loads and validates pipeline configurations from YAML files.
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from rich.console import Console

console = Console()


@dataclass
class StageConfig:
    """Configuration for a single pipeline stage."""
    name: str
    command: str
    timeout: int = 300
    retry_count: int = 0
    allow_failure: bool = False
    environment: Dict[str, str] = field(default_factory=dict)
    conditions: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Stage name is required")
        if not self.command:
            errors.append(f"Stage '{self.name}': command is required")
        if self.timeout < 0:
            errors.append(f"Stage '{self.name}': timeout must be >= 0")
        if self.retry_count < 0:
            errors.append(f"Stage '{self.name}': retry_count must be >= 0")
        return errors


@dataclass
class PipelineConfig:
    """Complete pipeline configuration."""
    name: str = "default-pipeline"
    version: str = "1.0.0"
    description: str = ""
    stages: List[StageConfig] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    notifications: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    trigger: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "PipelineConfig":
        """Load pipeline config from YAML file."""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Pipeline config not found: {yaml_path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        stages = []
        for stage_data in data.get("stages", []):
            stages.append(StageConfig(
                name=stage_data.get("name", "unnamed"),
                command=stage_data.get("command", ""),
                timeout=stage_data.get("timeout", 300),
                retry_count=stage_data.get("retry_count", 0),
                allow_failure=stage_data.get("allow_failure", False),
                environment=stage_data.get("environment", {}),
                conditions=stage_data.get("conditions", {}),
                depends_on=stage_data.get("depends_on", []),
            ))

        return cls(
            name=data.get("name", "default-pipeline"),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            stages=stages,
            environment=data.get("environment", {}),
            notifications=data.get("notifications", {}),
            artifacts=data.get("artifacts", []),
            trigger=data.get("trigger", {}),
        )

    def validate(self) -> List[str]:
        """Validate the entire pipeline configuration."""
        errors = []
        if not self.name:
            errors.append("Pipeline name is required")
        if not self.stages:
            errors.append("Pipeline must have at least one stage")

        stage_names = set()
        for stage in self.stages:
            if stage.name in stage_names:
                errors.append(f"Duplicate stage name: {stage.name}")
            stage_names.add(stage.name)
            errors.extend(stage.validate())

            for dep in stage.depends_on:
                if dep not in stage_names:
                    errors.append(
                        f"Stage '{stage.name}' depends on unknown stage: {dep}"
                    )

        return errors

    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "stages": [
                {
                    "name": s.name,
                    "command": s.command,
                    "timeout": s.timeout,
                    "retry_count": s.retry_count,
                    "allow_failure": s.allow_failure,
                }
                for s in self.stages
            ],
            "environment": self.environment,
        }


class EnvironmentManager:
    """Manages environment variables for different deployment targets."""

    ENVIRONMENTS = {
        "development": {
            "APP_ENV": "development",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
        },
        "staging": {
            "APP_ENV": "staging",
            "DEBUG": "false",
            "LOG_LEVEL": "INFO",
        },
        "production": {
            "APP_ENV": "production",
            "DEBUG": "false",
            "LOG_LEVEL": "WARNING",
        },
    }

    def __init__(self, env_name: str = "development"):
        self.env_name = env_name
        self.variables = self.ENVIRONMENTS.get(env_name, {}).copy()

    def get(self, key: str, default: str = "") -> str:
        return self.variables.get(key, os.getenv(key, default))

    def set(self, key: str, value: str):
        self.variables[key] = value

    def load_env_file(self, env_file: str = ".env"):
        """Load variables from .env file."""
        path = Path(env_file)
        if path.exists():
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        self.variables[key.strip()] = value.strip()

    def export(self):
        """Export all variables to os.environ."""
        for key, value in self.variables.items():
            os.environ[key] = value

    def display(self):
        """Display current environment."""
        console.print(f"\n  Environment: {self.env_name}", style="bold cyan")
        for key, value in sorted(self.variables.items()):
            console.print(f"   {key}={value}")
