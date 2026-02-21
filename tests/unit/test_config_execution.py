"""Tests for execution config loading."""

from ate_features.config import load_execution_config


class TestLoadExecutionConfig:
    def test_returns_dict(self) -> None:
        config = load_execution_config()
        assert isinstance(config, dict)

    def test_has_escape_threshold(self) -> None:
        config = load_execution_config()
        assert "escape_threshold_minutes" in config
        assert config["escape_threshold_minutes"] == 45

    def test_has_transcript_path_hint(self) -> None:
        config = load_execution_config()
        assert "transcript_path_hint" in config
        assert isinstance(config["transcript_path_hint"], str)

    def test_no_claude_code_version(self) -> None:
        """CC version is recorded at runtime, not pinned in config."""
        config = load_execution_config()
        assert "claude_code_version" not in config
