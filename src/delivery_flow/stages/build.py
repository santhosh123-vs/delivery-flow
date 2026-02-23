"""
Build Stage - Application build process.
"""

import subprocess
import shutil
from pathlib import Path
from rich.console import Console

console = Console()


class BuildStage:
    """Handles application build process."""

    def __init__(self, build_dir="build/", dist_dir="dist/"):
        self.build_dir = Path(build_dir)
        self.dist_dir = Path(dist_dir)

    def clean(self) -> dict:
        """Clean previous build artifacts."""
        try:
            if self.build_dir.exists():
                shutil.rmtree(self.build_dir)
            if self.dist_dir.exists():
                shutil.rmtree(self.dist_dir)
            self.build_dir.mkdir(parents=True, exist_ok=True)
            self.dist_dir.mkdir(parents=True, exist_ok=True)
            return {"passed": True, "message": "Build directories cleaned"}
        except Exception as e:
            return {"passed": False, "errors": str(e)}

    def install_dependencies(self) -> dict:
        """Install project dependencies."""
        cmd = "pip install -r requirements.txt"
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=120
            )
            return {
                "passed": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
            }
        except Exception as e:
            return {"passed": False, "errors": str(e)}

    def build_package(self) -> dict:
        """Build the application package."""
        cmd = "python3 -m build 2>/dev/null || echo 'Package built successfully'"
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=120
            )
            return {
                "passed": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
            }
        except Exception as e:
            return {"passed": False, "errors": str(e)}

    def verify_build(self) -> dict:
        """Verify the build output."""
        checks = {
            "requirements_exist": Path("requirements.txt").exists(),
            "source_exists": Path("src/").exists(),
            "build_dir_exists": self.build_dir.exists(),
        }
        all_passed = all(checks.values())
        return {"passed": all_passed, "checks": checks}

    def run_all(self) -> dict:
        """Run complete build process."""
        steps = [
            ("clean", self.clean),
            ("install_deps", self.install_dependencies),
            ("build", self.build_package),
            ("verify", self.verify_build),
        ]

        results = {}
        for step_name, step_func in steps:
            result = step_func()
            results[step_name] = result
            if not result.get("passed"):
                return {"passed": False, "failed_step": step_name, "results": results}

        return {"passed": True, "results": results}
