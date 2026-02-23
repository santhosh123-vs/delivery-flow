"""Unit tests for pipeline configuration."""

import os
import pytest
import yaml
from pathlib import Path
from src.delivery_flow.config import PipelineConfig, StageConfig, EnvironmentManager


class TestStageConfig:
    def test_create_stage(self):
        stage = StageConfig(name="test", command="echo hello")
        assert stage.name == "test"
        assert stage.command == "echo hello"
        assert stage.timeout == 300
        assert stage.retry_count == 0

    def test_stage_validation_pass(self):
        stage = StageConfig(name="test", command="echo hello")
        errors = stage.validate()
        assert len(errors) == 0

    def test_stage_validation_no_name(self):
        stage = StageConfig(name="", command="echo hello")
        errors = stage.validate()
        assert len(errors) > 0

    def test_stage_validation_no_command(self):
        stage = StageConfig(name="test", command="")
        errors = stage.validate()
        assert len(errors) > 0

    def test_stage_validation_negative_timeout(self):
        stage = StageConfig(name="test", command="echo hello", timeout=-1)
        errors = stage.validate()
        assert len(errors) > 0

    def test_stage_with_environment(self):
        stage = StageConfig(
            name="deploy",
            command="deploy.sh",
            environment={"ENV": "staging"},
        )
        assert stage.environment["ENV"] == "staging"

    def test_stage_with_dependencies(self):
        stage = StageConfig(
            name="deploy",
            command="deploy.sh",
            depends_on=["build", "test"],
        )
        assert "build" in stage.depends_on
        assert "test" in stage.depends_on


class TestPipelineConfig:
    def test_create_pipeline(self):
        config = PipelineConfig(
            name="test-pipeline",
            stages=[StageConfig(name="test", command="echo hello")],
        )
        assert config.name == "test-pipeline"
        assert len(config.stages) == 1

    def test_pipeline_validation_pass(self):
        config = PipelineConfig(
            name="test-pipeline",
            stages=[StageConfig(name="test", command="echo hello")],
        )
        errors = config.validate()
        assert len(errors) == 0

    def test_pipeline_validation_no_stages(self):
        config = PipelineConfig(name="test-pipeline", stages=[])
        errors = config.validate()
        assert any("at least one stage" in e for e in errors)

    def test_pipeline_validation_duplicate_stages(self):
        config = PipelineConfig(
            name="test-pipeline",
            stages=[
                StageConfig(name="test", command="echo 1"),
                StageConfig(name="test", command="echo 2"),
            ],
        )
        errors = config.validate()
        assert any("Duplicate" in e for e in errors)

    def test_pipeline_from_yaml(self, tmp_path):
        yaml_content = {
            "name": "yaml-pipeline",
            "version": "2.0.0",
            "stages": [
                {"name": "lint", "command": "echo lint"},
                {"name": "test", "command": "echo test", "depends_on": ["lint"]},
            ],
        }
        yaml_file = tmp_path / "pipeline.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        config = PipelineConfig.from_yaml(str(yaml_file))
        assert config.name == "yaml-pipeline"
        assert len(config.stages) == 2
        assert config.stages[1].depends_on == ["lint"]

    def test_pipeline_from_yaml_not_found(self):
        with pytest.raises(FileNotFoundError):
            PipelineConfig.from_yaml("nonexistent.yaml")

    def test_pipeline_to_dict(self):
        config = PipelineConfig(
            name="test",
            stages=[StageConfig(name="s1", command="echo 1")],
        )
        d = config.to_dict()
        assert d["name"] == "test"
        assert len(d["stages"]) == 1


class TestEnvironmentManager:
    def test_default_environment(self):
        env = EnvironmentManager("development")
        assert env.get("APP_ENV") == "development"
        assert env.get("DEBUG") == "true"

    def test_staging_environment(self):
        env = EnvironmentManager("staging")
        assert env.get("APP_ENV") == "staging"
        assert env.get("DEBUG") == "false"

    def test_production_environment(self):
        env = EnvironmentManager("production")
        assert env.get("APP_ENV") == "production"
        assert env.get("LOG_LEVEL") == "WARNING"

    def test_set_variable(self):
        env = EnvironmentManager("development")
        env.set("CUSTOM_VAR", "custom_value")
        assert env.get("CUSTOM_VAR") == "custom_value"

    def test_get_default_value(self):
        env = EnvironmentManager("development")
        assert env.get("NONEXISTENT", "default") == "default"

    def test_load_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("DB_HOST=localhost\nDB_PORT=5432\n# comment\n")

        env = EnvironmentManager("development")
        env.load_env_file(str(env_file))
        assert env.get("DB_HOST") == "localhost"
        assert env.get("DB_PORT") == "5432"

    def test_export_to_environ(self):
        env = EnvironmentManager("development")
        env.set("TEST_EXPORT_VAR", "exported")
        env.export()
        assert os.environ.get("TEST_EXPORT_VAR") == "exported"
        # Cleanup
        del os.environ["TEST_EXPORT_VAR"]
