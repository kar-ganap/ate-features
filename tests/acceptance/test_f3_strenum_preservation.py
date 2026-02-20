"""F3: StrEnum preservation in checkpoint serde.

Currently StrEnum values may be downcast to plain strings during serialization.
The EXT_CONSTRUCTOR mechanism should preserve the enum type through round-trips.
"""

from __future__ import annotations

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
