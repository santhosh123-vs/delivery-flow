"""
Test Stage - Runs automated tests.
"""

import subprocess
from rich.console import Console

console = Console()


class TestStage:
    """Runs automated tests with coverage."""

    def __init__(self, test_dir="tests/", coverage_threshold=80):
        self.test_dir = test_dir
        self.coverage_threshold = coverage_threshold

    def run_unit_tests(self) -> dict:
        """Run unit tests."""
        cmd = f"python3 -m pytest {self.test_dir}unit -v --tb=short"
        return self._run_tests("unit", cmd)

    def run_integration_tests(self) -> dict:
        """Run integration tests."""
        cmd = f"python3 -m pytest {self.test_dir}integration -v --tb=short"
        return self._run_tests("integration", cmd)

    def run_all_tests(self) -> dict:
        """Run all tests with coverage."""
        cmd = (
            f"python3 -m pytest {self.test_dir} -v "
            f"--cov=src --cov-report=term-missing --tb=short"
        )
        return self._run_tests("all", cmd)

    def _run_tests(self, test_type: str, cmd: str) -> dict:
        """Execute test command and return results."""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=300
            )
            return {
                "type": test_type,
                "passed": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
                "return_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "type": test_type,
                "passed": False,
                "errors": "Test execution timed out",
            }
        except Exception as e:
            return {"type": test_type, "passed": False, "errors": str(e)}
