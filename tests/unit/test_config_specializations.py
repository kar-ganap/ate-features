"""Tests for specialization loading."""

import pytest

from ate_features.config import load_specialization

AGENT_FILENAMES = {
    1: "serde_types_and_state_channels.md",
    2: "serde_pydantic_and_state_reducers.md",
    3: "serde_enums_and_stream_emission.md",
    4: "serde_nested_and_stream_dedup.md",
}


class TestLoadSpecialization:
    @pytest.mark.parametrize("agent_num", [1, 2, 3, 4])
    def test_loads_all_agents(self, agent_num: int) -> None:
        content = load_specialization(agent_num)
        assert isinstance(content, str)
        assert len(content) > 100

    @pytest.mark.parametrize("agent_num", [1, 2, 3, 4])
    def test_content_starts_with_heading(self, agent_num: int) -> None:
        content = load_specialization(agent_num)
        assert content.startswith("# Agent")

    def test_agent_1_covers_serializer_and_state(self) -> None:
        content = load_specialization(1)
        assert "Serializer Subsystem" in content
        assert "State Subsystem" in content

    def test_agent_3_covers_serializer_and_streaming(self) -> None:
        content = load_specialization(3)
        assert "Serializer Subsystem" in content
        assert "Streaming Subsystem" in content

    def test_invalid_agent_number(self) -> None:
        with pytest.raises(ValueError, match="agent_num must be 1-4"):
            load_specialization(0)

    def test_invalid_agent_number_high(self) -> None:
        with pytest.raises(ValueError, match="agent_num must be 1-4"):
            load_specialization(5)
