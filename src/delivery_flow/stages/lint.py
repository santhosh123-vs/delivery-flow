"""
Lint Stage - Code quality checks.
"""

import subprocess
from rich.console import Console

console = Console()


class LintStage:
    """Runs code linting and style checks."""

    def __init__(self, paths=None, config=None):
        self.paths = paths or ["src/", "tests/"]
        self.config = config or {}

    def run_flake8(self) -> dict:
        """Run flake8 linter."""
        paths_str = " ".join(self.paths)
        cmd = f"flake8 {paths_str} --max-line-length=120 --statistics"

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=60
            )
            return {
                "tool": "flake8",
                "passed": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
            }
        except Exception as e:
            return {"tool": "flake8", "passed": False, "errors": str(e)}

    def run_black_check(self) -> dict:
        """Run black formatter check."""
        paths_str = " ".join(self.paths)
        cmd = f"black --check {paths_str}"

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=60
            )
            return {
                "tool": "black",
                "passed": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
            }
        except Exception as e:
            return {"tool": "black", "passed": False, "errors": str(e)}

    def run_all(self) -> dict:
        """Run all lint checks."""
        results = {
            "flake8": self.run_flake8(),
            "black": self.run_black_check(),
        }

        all_passed = all(r["passed"] for r in results.values())
        return {"passed": all_passed, "results": results}
