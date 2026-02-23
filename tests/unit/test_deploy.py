"""Unit tests for deploy stage."""

import pytest
from src.delivery_flow.stages.deploy import DeployStage


class TestDeployStage:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.deployer = DeployStage(deploy_dir=str(tmp_path / "deployments"))

    def test_deploy_staging(self):
        result = self.deployer.deploy("staging", "1.0.0")
        assert result["passed"] is True
        assert result["environment"] == "staging"
        assert result["version"] == "1.0.0"

    def test_deploy_production(self):
        result = self.deployer.deploy("production", "1.0.0")
        assert result["passed"] is True
        assert result["environment"] == "production"

    def test_deploy_records_history(self):
        self.deployer.deploy("staging", "1.0.0")
        history = self.deployer.get_deploy_history("staging")
        assert len(history) == 1
        assert history[0].version == "1.0.0"

    def test_multiple_deploys(self):
        self.deployer.deploy("staging", "1.0.0")
        self.deployer.deploy("staging", "1.1.0")
        self.deployer.deploy("staging", "1.2.0")
        history = self.deployer.get_deploy_history("staging")
        assert len(history) == 3

    def test_rollback(self):
        self.deployer.deploy("staging", "1.0.0")
        self.deployer.deploy("staging", "1.1.0")
        result = self.deployer.rollback("staging")
        assert result["passed"] is True
        assert result["rolled_back_to"] == "1.0.0"

    def test_rollback_no_previous(self):
        self.deployer.deploy("staging", "1.0.0")
        result = self.deployer.rollback("staging")
        assert result["passed"] is False

    def test_rollback_no_deploys(self):
        result = self.deployer.rollback("staging")
        assert result["passed"] is False

    def test_health_check(self):
        result = self.deployer.health_check("staging")
        assert result["passed"] is True
        assert result["environment"] == "staging"
        assert all(result["checks"].values())

    def test_deploy_history_filter(self):
        self.deployer.deploy("staging", "1.0.0")
        self.deployer.deploy("production", "1.0.0")
        staging_history = self.deployer.get_deploy_history("staging")
        prod_history = self.deployer.get_deploy_history("production")
        assert len(staging_history) == 1
        assert len(prod_history) == 1

    def test_deploy_creates_id(self):
        result = self.deployer.deploy("staging", "1.0.0")
        assert "deploy_id" in result
        assert result["deploy_id"].startswith("deploy-")
