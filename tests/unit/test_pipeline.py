"""Unit tests for pipeline engine."""

import pytest
from src.delivery_flow.config import PipelineConfig, StageConfig
from src.delivery_flow.pipeline import PipelineEngine, StageStatus, StageResult, PipelineResult


class TestStageStatus:
    def test_status_values(self):
        assert StageStatus.PENDING.value == "pending"
        assert StageStatus.RUNNING.value == "running"
        assert StageStatus.PASSED.value == "passed"
        assert StageStatus.FAILED.value == "failed"
        assert StageStatus.SKIPPED.value == "skipped"


class TestStageResult:
    def test_create_result(self):
        result = StageResult(name="test")
        assert result.name == "test"
        assert result.status == StageStatus.PENDING

    def test_is_success_passed(self):
        result = StageResult(name="test", status=StageStatus.PASSED)
        assert result.is_success is True

    def test_is_success_failed(self):
        result = StageResult(name="test", status=StageStatus.FAILED)
        assert result.is_success is False


class TestPipelineResult:
    def test_create_result(self):
        result = PipelineResult(pipeline_name="test")
        assert result.total_stages == 0
        assert result.pass_rate == 0.0

    def test_pass_rate_calculation(self):
        result = PipelineResult(
            stage_results=[
                StageResult(name="s1", status=StageStatus.PASSED),
                StageResult(name="s2", status=StageStatus.PASSED),
                StageResult(name="s3", status=StageStatus.FAILED),
            ]
        )
        assert result.passed_stages == 2
        assert result.failed_stages == 1
        assert result.total_stages == 3
        assert abs(result.pass_rate - 66.67) < 1

    def test_all_passed(self):
        result = PipelineResult(
            stage_results=[
                StageResult(name="s1", status=StageStatus.PASSED),
                StageResult(name="s2", status=StageStatus.PASSED),
            ]
        )
        assert result.pass_rate == 100.0


class TestPipelineEngine:
    def test_create_engine(self):
        config = PipelineConfig(
            name="test",
            stages=[StageConfig(name="s1", command="echo hello")],
        )
        engine = PipelineEngine(config)
        assert engine.config.name == "test"

    def test_run_simple_pipeline(self):
        config = PipelineConfig(
            name="simple-test",
            stages=[
                StageConfig(name="hello", command="echo 'Hello World'"),
                StageConfig(name="date", command="date"),
            ],
        )
        engine = PipelineEngine(config)
        result = engine.run()
        assert result.status == "passed"
        assert result.passed_stages == 2

    def test_run_failing_stage(self):
        config = PipelineConfig(
            name="fail-test",
            stages=[
                StageConfig(name="good", command="echo 'OK'"),
                StageConfig(name="bad", command="exit 1"),
            ],
        )
        engine = PipelineEngine(config)
        result = engine.run()
        assert result.status == "failed"
        assert result.failed_stages >= 1

    def test_allow_failure(self):
        config = PipelineConfig(
            name="allow-fail-test",
            stages=[
                StageConfig(name="good", command="echo 'OK'"),
                StageConfig(name="bad", command="exit 1", allow_failure=True),
                StageConfig(name="after", command="echo 'Still running'"),
            ],
        )
        engine = PipelineEngine(config)
        result = engine.run()
        assert result.status == "passed"

    def test_stage_dependencies(self):
        config = PipelineConfig(
            name="dep-test",
            stages=[
                StageConfig(name="first", command="echo 'first'"),
                StageConfig(
                    name="second",
                    command="echo 'second'",
                    depends_on=["first"],
                ),
            ],
        )
        engine = PipelineEngine(config)
        result = engine.run()
        assert result.status == "passed"
        assert result.passed_stages == 2

    def test_skip_on_failed_dependency(self):
        config = PipelineConfig(
            name="skip-test",
            stages=[
                StageConfig(name="first", command="exit 1"),
                StageConfig(
                    name="second",
                    command="echo 'should be skipped'",
                    depends_on=["first"],
                ),
            ],
        )
        engine = PipelineEngine(config)
        result = engine.run()
        assert result.status == "failed"

    def test_register_hook(self):
        config = PipelineConfig(
            name="hook-test",
            stages=[StageConfig(name="s1", command="echo test")],
        )
        engine = PipelineEngine(config)

        hook_called = []
        engine.register_hook("before_pipeline", lambda **kw: hook_called.append("before"))
        engine.register_hook("after_pipeline", lambda **kw: hook_called.append("after"))

        engine.run()
        assert "before" in hook_called
        assert "after" in hook_called

    def test_invalid_config(self):
        config = PipelineConfig(name="", stages=[])
        engine = PipelineEngine(config)
        result = engine.run()
        assert result.status == "failed"

    def test_stage_with_retry(self):
        config = PipelineConfig(
            name="retry-test",
            stages=[
                StageConfig(name="s1", command="echo 'OK'", retry_count=2),
            ],
        )
        engine = PipelineEngine(config)
        result = engine.run()
        assert result.status == "passed"

    def test_environment_setting(self):
        config = PipelineConfig(
            name="env-test",
            stages=[StageConfig(name="s1", command="echo test")],
        )
        engine = PipelineEngine(config, environment="staging")
        assert engine.env_manager.env_name == "staging"
