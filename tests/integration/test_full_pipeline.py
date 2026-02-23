"""Integration tests for full pipeline execution."""

import pytest
from src.delivery_flow.config import PipelineConfig, StageConfig
from src.delivery_flow.pipeline import PipelineEngine
from src.delivery_flow.stages.deploy import DeployStage
from src.delivery_flow.plugins.notifications import NotificationManager


class TestFullPipelineExecution:
    def test_quick_pipeline_from_yaml(self):
        """Test running a pipeline from YAML config."""
        config = PipelineConfig.from_yaml("pipelines/quick-test.yaml")
        engine = PipelineEngine(config)
        result = engine.run()
        assert result.status == "passed"
        assert result.passed_stages == 4

    def test_pipeline_with_notifications(self):
        """Test pipeline with notification hooks."""
        config = PipelineConfig(
            name="notified-pipeline",
            stages=[
                StageConfig(name="step1", command="echo 'Step 1'"),
                StageConfig(name="step2", command="echo 'Step 2'", depends_on=["step1"]),
            ],
        )
        engine = PipelineEngine(config)
        notifier = NotificationManager()

        notifier.notify_start(config.name, "development")
        result = engine.run()
        notifier.notify_complete(config.name, result.status, result.duration)

        assert result.status == "passed"
        log = notifier.get_log()
        assert len(log) == 2

    def test_deploy_and_rollback_flow(self, tmp_path):
        """Test complete deploy and rollback cycle."""
        deployer = DeployStage(deploy_dir=str(tmp_path / "deployments"))

        # Deploy v1
        result1 = deployer.deploy("staging", "1.0.0")
        assert result1["passed"] is True

        # Deploy v2
        result2 = deployer.deploy("staging", "2.0.0")
        assert result2["passed"] is True

        # Rollback to v1
        rollback_result = deployer.rollback("staging")
        assert rollback_result["passed"] is True
        assert rollback_result["rolled_back_to"] == "1.0.0"

        # Verify history
        history = deployer.get_deploy_history("staging")
        assert len(history) == 3

    def test_multi_environment_deploy(self, tmp_path):
        """Test deploying to multiple environments."""
        deployer = DeployStage(deploy_dir=str(tmp_path / "deployments"))

        deployer.deploy("development", "1.0.0")
        deployer.deploy("staging", "1.0.0")
        deployer.deploy("production", "1.0.0")

        dev = deployer.get_deploy_history("development")
        staging = deployer.get_deploy_history("staging")
        prod = deployer.get_deploy_history("production")

        assert len(dev) == 1
        assert len(staging) == 1
        assert len(prod) == 1

    def test_pipeline_with_environment(self):
        """Test pipeline with environment variables."""
        config = PipelineConfig(
            name="env-pipeline",
            environment={"MY_VAR": "hello"},
            stages=[
                StageConfig(name="check_env", command="echo $MY_VAR"),
            ],
        )
        engine = PipelineEngine(config, environment="staging")
        result = engine.run()
        assert result.status == "passed"
        assert result.environment == "staging"

    def test_pipeline_chain_all_stages(self):
        """Test a pipeline that chains through all stages."""
        config = PipelineConfig(
            name="full-chain",
            stages=[
                StageConfig(name="lint", command="echo 'Linting...'"),
                StageConfig(name="test", command="echo 'Testing...'", depends_on=["lint"]),
                StageConfig(name="build", command="echo 'Building...'", depends_on=["test"]),
                StageConfig(name="deploy", command="echo 'Deploying...'", depends_on=["build"]),
                StageConfig(name="verify", command="echo 'Verifying...'", depends_on=["deploy"]),
            ],
        )
        engine = PipelineEngine(config)
        result = engine.run()
        assert result.status == "passed"
        assert result.passed_stages == 5
        assert result.pass_rate == 100.0
