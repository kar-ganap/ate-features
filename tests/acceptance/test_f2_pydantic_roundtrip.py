"""F2: Generic Pydantic v2 type round-trip in checkpoint serde.

The serializer handles basic Pydantic V2 via EXT_PYDANTIC_V2, but Generic
BaseModel subclasses and complex field configurations don't survive round-trips.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field, field_validator


class SimpleModel(BaseModel):
    name: str
    count: int


class NestedOuter(BaseModel):
    inner: SimpleModel
    label: str


class OptionalModel(BaseModel):
    required: str
    optional_field: str | None = None


class ValidatedModel(BaseModel):
    value: int

    @field_validator("value")
    @classmethod
    def must_be_positive(cls, v: int) -> int:
        if v <= 0:
            msg = "must be positive"
            raise ValueError(msg)
        return v


T = TypeVar("T")


class GenericModel(BaseModel, Generic[T]):
    data: T
    label: str


class FrozenModel(BaseModel):
    model_config = {"frozen": True}
    x: int
    y: str


class TestT1Basic:
    """Basic functionality — any first-attempt solution should pass these."""

    def test_simple_model_round_trip(self) -> None:
        """Simple BaseModel with str/int fields round-trips."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        obj = SimpleModel(name="test", count=42)

        serialized = serde.dumps({"m": obj})
        result = serde.loads(serialized)

        assert isinstance(result["m"], SimpleModel)
        assert result["m"].name == "test"
        assert result["m"].count == 42

    def test_type_preserved(self) -> None:
        """Deserialized object is an instance of the original class."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        obj = SimpleModel(name="a", count=1)

        serialized = serde.dumps({"m": obj})
        result = serde.loads(serialized)

        assert type(result["m"]) is SimpleModel

    def test_field_values_match(self) -> None:
        """All field values match after round-trip."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        obj = SimpleModel(name="hello", count=99)

        serialized = serde.dumps({"m": obj})
        result = serde.loads(serialized)

        assert result["m"].model_dump() == obj.model_dump()


class TestT2EdgeCases:
    """Edge cases — a naive first attempt may miss these."""

    def test_nested_model(self) -> None:
        """Nested BaseModel (model containing another model) round-trips."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        obj = NestedOuter(inner=SimpleModel(name="inner", count=1), label="outer")

        serialized = serde.dumps({"m": obj})
        result = serde.loads(serialized)

        assert isinstance(result["m"], NestedOuter)
        assert isinstance(result["m"].inner, SimpleModel)
        assert result["m"].inner.name == "inner"

    def test_optional_fields_none(self) -> None:
        """Optional field set to None round-trips."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        obj = OptionalModel(required="yes", optional_field=None)

        serialized = serde.dumps({"m": obj})
        result = serde.loads(serialized)

        assert isinstance(result["m"], OptionalModel)
        assert result["m"].optional_field is None

    def test_optional_fields_set(self) -> None:
        """Optional field set to a value round-trips."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        obj = OptionalModel(required="yes", optional_field="present")

        serialized = serde.dumps({"m": obj})
        result = serde.loads(serialized)

        assert result["m"].optional_field == "present"

    def test_model_with_validators(self) -> None:
        """Model with field_validator round-trips and validates on reconstruction."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        obj = ValidatedModel(value=5)

        serialized = serde.dumps({"m": obj})
        result = serde.loads(serialized)

        assert isinstance(result["m"], ValidatedModel)
        assert result["m"].value == 5

    def test_model_with_default_factory(self) -> None:
        """Model with Field(default_factory=...) preserves defaults."""

        class ModelWithFactory(BaseModel):
            tags: list[str] = Field(default_factory=list)
            name: str = "default"

        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        obj = ModelWithFactory(tags=["a", "b"], name="custom")

        serialized = serde.dumps({"m": obj})
        result = serde.loads(serialized)

        assert isinstance(result["m"], ModelWithFactory)
        assert result["m"].tags == ["a", "b"]
        assert result["m"].name == "custom"


class TestT3Quality:
    """Quality constraints — first approach probably fails these."""

    def test_generic_model(self) -> None:
        """Generic BaseModel subclass (Generic[T]) round-trips with concrete type."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        obj = GenericModel[int](data=42, label="number")

        serialized = serde.dumps({"m": obj})
        result = serde.loads(serialized)

        assert isinstance(result["m"], GenericModel)
        assert result["m"].data == 42
        assert result["m"].label == "number"

    def test_frozen_model(self) -> None:
        """Frozen BaseModel (immutable) round-trips correctly."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        obj = FrozenModel(x=10, y="hello")

        serialized = serde.dumps({"m": obj})
        result = serde.loads(serialized)

        assert isinstance(result["m"], FrozenModel)
        assert result["m"].x == 10
        assert result["m"].y == "hello"

    def test_model_fields_set_preserved(self) -> None:
        """Round-trip preserves model_fields_set information."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        obj = OptionalModel(required="yes")  # optional_field not explicitly set

        serialized = serde.dumps({"m": obj})
        result = serde.loads(serialized)

        assert isinstance(result["m"], OptionalModel)
        # The fields that were explicitly set should be tracked
        assert "required" in result["m"].model_fields_set


class TestT4Smoke:
    """Smoke/integration tests — realistic multi-node workflows."""

    def test_pydantic_model_survives_graph_checkpoint(self) -> None:
        """Nested Pydantic model in state survives checkpoint round-trip."""
        import operator
        from typing import Annotated

        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.graph import StateGraph
        from typing_extensions import TypedDict

        class State(TypedDict):
            log: Annotated[list[str], operator.add]
            model: NestedOuter

        def step_1(state: State) -> dict:
            inner = SimpleModel(name="from_step1", count=42)
            return {
                "log": ["step_1"],
                "model": NestedOuter(inner=inner, label="outer"),
            }

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
        config = {"configurable": {"thread_id": "f2-smoke"}}

        init_model = NestedOuter(
            inner=SimpleModel(name="init", count=0), label="init"
        )
        result = compiled.invoke(
            {"log": [], "model": init_model}, config=config
        )
        assert result["log"] == ["step_1", "step_2"]
        assert isinstance(result["model"], NestedOuter)
        assert isinstance(result["model"].inner, SimpleModel)
        assert result["model"].inner.name == "from_step1"

        state = compiled.get_state(config)
        assert isinstance(state.values["model"], NestedOuter)

    def test_generic_model_survives_graph_execution(self) -> None:
        """Generic Pydantic model in state survives graph execution."""
        from langgraph.graph import END, StateGraph
        from typing_extensions import TypedDict

        class State(TypedDict):
            model: GenericModel[int]
            done: bool

        def produce(state: State) -> dict:
            return {
                "model": GenericModel[int](data=99, label="produced"),
                "done": True,
            }

        def route(state: State) -> str:
            return END if state["done"] else "produce"

        graph = StateGraph(State)
        graph.add_node("produce", produce)
        graph.add_conditional_edges("produce", route)
        graph.set_entry_point("produce")
        compiled = graph.compile()

        result = compiled.invoke(
            {"model": GenericModel[int](data=0, label="init"), "done": False}
        )
        assert isinstance(result["model"], GenericModel)
        assert result["model"].data == 99
