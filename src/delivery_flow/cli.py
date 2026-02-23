"""
CLI Interface for DeliveryFlow.
"""

import click
from rich.console import Console
from .config import PipelineConfig, EnvironmentManager
from .pipeline import PipelineEngine
from .stages.deploy import DeployStage
from .plugins.notifications import NotificationManager

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="DeliveryFlow")
def main():
    """DeliveryFlow - Automated CI/CD Pipeline Tools"""
    pass


@main.command()
@click.argument("config_file", default="pipelines/default.yaml")
@click.option("--env", default="development", help="Target environment")
@click.option("--dry-run", is_flag=True, help="Validate without executing")
def run(config_file, env, dry_run):
    """Run a pipeline from config file."""
    try:
        config = PipelineConfig.from_yaml(config_file)

        if dry_run:
            console.print("\n  DRY RUN - Validating pipeline...", style="yellow")
            errors = config.validate()
            if errors:
                for error in errors:
                    console.print(f"   {error}", style="red")
            else:
                console.print("   Pipeline config is valid!", style="green")
                for stage in config.stages:
                    console.print(f"   Stage: {stage.name} -> {stage.command}", style="dim")
            return

        engine = PipelineEngine(config, environment=env)

        # Register notification hooks
        notifier = NotificationManager()
        notifier.notify_start(config.name, env)

        result = engine.run()
        notifier.notify_complete(config.name, result.status, result.duration)
        notifier.save_log()

    except FileNotFoundError as e:
        console.print(f"\n   Error: {e}", style="red")
    except Exception as e:
        console.print(f"\n   Error: {e}", style="red")


@main.command()
@click.option("--env", required=True, help="Target environment")
@click.option("--version", "ver", default="1.0.0", help="Version to deploy")
def deploy(env, ver):
    """Deploy to an environment."""
    deployer = DeployStage()
    result = deployer.deploy(env, ver)
    if result["passed"]:
        console.print(f"\n   Deployment successful!", style="bold green")
    else:
        console.print(f"\n   Deployment failed!", style="bold red")


@main.command()
@click.option("--env", required=True, help="Environment to rollback")
def rollback(env):
    """Rollback to previous deployment."""
    deployer = DeployStage()
    result = deployer.rollback(env)
    if result["passed"]:
        console.print(f"\n   Rollback successful!", style="bold green")
    else:
        console.print(f"\n   {result.get('error', 'Rollback failed')}", style="red")


@main.command()
@click.option("--env", default="development", help="Environment to check")
def status(env):
    """Show environment status and deploy history."""
    deployer = DeployStage()

    # Health check
    health = deployer.health_check(env)
    console.print(f"\n  Health Check: {env}", style="bold cyan")
    for check, passed in health["checks"].items():
        icon = "PASS" if passed else "FAIL"
        style = "green" if passed else "red"
        console.print(f"   {icon} {check}", style=style)

    # Deploy history
    history = deployer.get_deploy_history(env)
    if history:
        console.print(f"\n  Deploy History: {env}", style="bold cyan")
        for record in history[-5:]:
            console.print(
                f"   [{record.timestamp}] {record.deploy_id} "
                f"v{record.version} - {record.status}",
                style="dim",
            )


@main.command()
@click.argument("env_name", default="development")
def env(env_name):
    """Show environment configuration."""
    manager = EnvironmentManager(env_name)
    manager.display()


if __name__ == "__main__":
    main()
