"""F3: StrEnum preservation in checkpoint serde.

Currently StrEnum values may be downcast to plain strings during serialization.
The EXT_CONSTRUCTOR mechanism should preserve the enum type through round-trips.
"""

from enum import StrEnum

from pydantic import BaseModel


class Color(StrEnum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class ColorWithMethod(StrEnum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

    def is_primary(self) -> bool:
        return self in (ColorWithMethod.RED, ColorWithMethod.GREEN, ColorWithMethod.BLUE)


class Size(StrEnum):
    SMALL = "small"
    LARGE = "large"


class TestT1Basic:
    """Basic functionality — any first-attempt solution should pass these."""

    def test_strenum_round_trip(self) -> None:
        """StrEnum value survives serialize/deserialize."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"color": Color.RED}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert result["color"] == Color.RED

    def test_isinstance_preserved(self) -> None:
        """isinstance() check works after round-trip."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"color": Color.GREEN}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert isinstance(result["color"], Color)

    def test_name_and_value(self) -> None:
        """.name and .value attributes work after round-trip."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"color": Color.BLUE}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert result["color"].name == "BLUE"
        assert result["color"].value == "blue"


class TestT2EdgeCases:
    """Edge cases — a naive first attempt may miss these."""

    def test_strenum_in_dict_value(self) -> None:
        """StrEnum as a dict value round-trips."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"config": {"theme": Color.RED, "size": Size.LARGE}}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert isinstance(result["config"]["theme"], Color)
        assert isinstance(result["config"]["size"], Size)

    def test_strenum_in_list(self) -> None:
        """StrEnum as a list element round-trips."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"colors": [Color.RED, Color.GREEN, Color.BLUE]}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert all(isinstance(c, Color) for c in result["colors"])

    def test_strenum_in_dataclass(self) -> None:
        """StrEnum as a dataclass field round-trips."""
        import dataclasses

        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        @dataclasses.dataclass
        class Config:
            color: Color
            size: Size

        serde = JsonPlusSerializer()
        data = {"cfg": Config(color=Color.RED, size=Size.SMALL)}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert isinstance(result["cfg"].color, Color)
        assert isinstance(result["cfg"].size, Size)

    def test_strenum_in_pydantic_model(self) -> None:
        """StrEnum as a Pydantic field round-trips."""

        class Theme(BaseModel):
            primary: Color
            secondary: Color

        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"theme": Theme(primary=Color.RED, secondary=Color.BLUE)}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert isinstance(result["theme"].primary, Color)
        assert isinstance(result["theme"].secondary, Color)

    def test_multiple_enum_types(self) -> None:
        """Multiple different StrEnum types in the same object."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"color": Color.RED, "size": Size.LARGE}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert isinstance(result["color"], Color)
        assert isinstance(result["size"], Size)


class TestT3Quality:
    """Quality constraints — first approach probably fails these."""

    def test_custom_method_preserved(self) -> None:
        """StrEnum subclass with custom methods is preserved."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"color": ColorWithMethod.RED}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert isinstance(result["color"], ColorWithMethod)
        assert result["color"].is_primary()

    def test_no_false_positive_with_plain_string(self) -> None:
        """StrEnum with value matching a plain string doesn't cause confusion."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"enum_val": Color.RED, "plain_str": "red"}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert isinstance(result["enum_val"], Color)
        assert type(result["plain_str"]) is str
        assert not isinstance(result["plain_str"], Color)

    def test_backward_compat_regular_enum(self) -> None:
        """Regular Enum (non-Str) still works after StrEnum changes."""
        from enum import Enum

        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        class Priority(Enum):
            LOW = 1
            HIGH = 2

        serde = JsonPlusSerializer()
        data = {"p": Priority.HIGH}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert isinstance(result["p"], Priority)
        assert result["p"] == Priority.HIGH


class TestT4Smoke:
    """Smoke/integration tests — realistic multi-node workflows."""

    def test_strenum_survives_graph_checkpoint(self) -> None:
        """StrEnum value in state survives checkpoint round-trip."""
        import operator
        from typing import Annotated

        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.graph import StateGraph
        from typing_extensions import TypedDict

        class State(TypedDict):
            log: Annotated[list[str], operator.add]
            color: Color

        def step_1(state: State) -> dict:
            return {"log": ["step_1"], "color": Color.GREEN}

        def step_2(state: State) -> dict:
            return {"log": ["step_2"]}

        graph = StateGraph(State)
        graph.add_node("step_1", step_1)
        graph.add_node("step_2", step_2)
        graph.add_edge("step_1", "step_2")
        graph.set_entry_point("step_1")
        graph.set_finish_point("step_2")

        memory = InMemorySaver()
        compiled = graph.compile(checkpointer=memory)
        config = {"configurable": {"thread_id": "f3-smoke"}}

        result = compiled.invoke(
            {"log": [], "color": Color.RED}, config=config
        )
        assert result["log"] == ["step_1", "step_2"]
        assert isinstance(result["color"], Color)
        assert result["color"] == Color.GREEN

        state = compiled.get_state(config)
        assert isinstance(state.values["color"], Color)

    def test_strenum_list_accumulates_in_graph(self) -> None:
        """StrEnum values accumulate in list reducer across graph nodes."""
        import operator
        from typing import Annotated

        from langgraph.graph import END, StateGraph
        from typing_extensions import TypedDict

        class State(TypedDict):
            colors: Annotated[list[Color], operator.add]
            count: int

        def add_color(state: State) -> dict:
            color = [Color.RED, Color.GREEN, Color.BLUE][state["count"]]
            return {"colors": [color], "count": state["count"] + 1}

        def route(state: State) -> str:
            return END if state["count"] >= 3 else "add_color"

        graph = StateGraph(State)
        graph.add_node("add_color", add_color)
        graph.add_conditional_edges("add_color", route)
        graph.set_entry_point("add_color")
        compiled = graph.compile()

        result = compiled.invoke({"colors": [], "count": 0})
        assert len(result["colors"]) == 3
        assert all(isinstance(c, Color) for c in result["colors"])
        assert result["colors"] == [Color.RED, Color.GREEN, Color.BLUE]


class TestT5Robustness:
    """Robustness edge cases — spec-derived tests a QA engineer would flag."""

    def test_strenum_as_dict_key(self) -> None:
        """StrEnum used as a dict key preserves type after round-trip."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"mapping": {Color.RED: "warm", Color.BLUE: "cool"}}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        keys = list(result["mapping"].keys())
        # At minimum, the key values should be correct
        assert set(result["mapping"].values()) == {"warm", "cool"}
        # Ideally, keys are still Color instances
        for key in keys:
            assert isinstance(key, Color), (
                f"Dict key should be Color enum, got {type(key)}: {key!r}"
            )

    def test_overlapping_strenum_values_distinguished(self) -> None:
        """Two StrEnum types with identical string values are distinguished."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        class Tag(StrEnum):
            RED = "red"
            BLUE = "blue"

        serde = JsonPlusSerializer()
        # Color.RED.value == "red" and Tag.RED.value == "red" — same string
        data = {"color": Color.RED, "tag": Tag.RED}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert isinstance(result["color"], Color), (
            f"Expected Color, got {type(result['color'])}"
        )
        assert isinstance(result["tag"], Tag), (
            f"Expected Tag, got {type(result['tag'])}"
        )
