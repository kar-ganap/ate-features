"""F1: Pandas DataFrame/Series msgpack serialization in JsonPlusSerializer.

Currently pandas types only work with pickle_fallback=True. This feature adds
first-class msgpack ext type handlers for DataFrame and Series.
"""

import pytest


class TestT1Basic:
    """Basic functionality — any first-attempt solution should pass these."""

    def test_dataframe_round_trip(self) -> None:
        """Simple DataFrame survives serialize/deserialize."""
        import pandas as pd
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        data = {"df": df}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        pd.testing.assert_frame_equal(result["df"], df)

    def test_series_round_trip(self) -> None:
        """Simple Series survives serialize/deserialize."""
        import pandas as pd
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        s = pd.Series([10, 20, 30], name="values")
        data = {"s": s}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        pd.testing.assert_series_equal(result["s"], s)

    def test_no_pickle_fallback(self) -> None:
        """DataFrame serialization works without pickle fallback."""
        import pandas as pd
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        df = pd.DataFrame({"a": [1, 2, 3]})

        # Serialize — should not require pickle
        serialized = serde.dumps({"df": df})
        result = serde.loads(serialized)

        assert isinstance(result["df"], pd.DataFrame)
        pd.testing.assert_frame_equal(result["df"], df)


class TestT2EdgeCases:
    """Edge cases — a naive first attempt may miss these."""

    def test_multiindex_dataframe(self) -> None:
        """DataFrame with MultiIndex on rows."""
        import pandas as pd
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        arrays = [["bar", "bar", "baz"], ["one", "two", "one"]]
        index = pd.MultiIndex.from_arrays(arrays, names=["first", "second"])
        df = pd.DataFrame({"A": [1, 2, 3]}, index=index)

        serialized = serde.dumps({"df": df})
        result = serde.loads(serialized)

        pd.testing.assert_frame_equal(result["df"], df)

    def test_mixed_dtypes(self) -> None:
        """DataFrame with int64, float64, string, and datetime columns."""
        import pandas as pd
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        df = pd.DataFrame(
            {
                "int_col": pd.array([1, 2, 3], dtype="int64"),
                "float_col": [1.1, 2.2, 3.3],
                "str_col": ["a", "b", "c"],
                "dt_col": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
            }
        )

        serialized = serde.dumps({"df": df})
        result = serde.loads(serialized)

        pd.testing.assert_frame_equal(result["df"], df)

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame round-trips correctly."""
        import pandas as pd
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        df = pd.DataFrame()

        serialized = serde.dumps({"df": df})
        result = serde.loads(serialized)

        pd.testing.assert_frame_equal(result["df"], df)

    def test_series_with_named_index(self) -> None:
        """Series with a named index preserves the index name."""
        import pandas as pd
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        s = pd.Series([10, 20], index=pd.Index(["a", "b"], name="keys"), name="vals")

        serialized = serde.dumps({"s": s})
        result = serde.loads(serialized)

        pd.testing.assert_series_equal(result["s"], s)

    def test_dataframe_with_nan(self) -> None:
        """DataFrame with NaN values preserves them."""
        import numpy as np
        import pandas as pd
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0], "b": [np.nan, 2.0, np.nan]})

        serialized = serde.dumps({"df": df})
        result = serde.loads(serialized)

        pd.testing.assert_frame_equal(result["df"], df)


class TestT3Quality:
    """Quality constraints — first approach probably fails these."""

    def test_dtype_preservation(self) -> None:
        """Round-trip preserves exact dtypes (no silent float->object conversion)."""
        import pandas as pd
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        df = pd.DataFrame(
            {
                "int32": pd.array([1, 2], dtype="int32"),
                "float32": pd.array([1.0, 2.0], dtype="float32"),
                "int64": pd.array([10, 20], dtype="int64"),
            }
        )

        serialized = serde.dumps({"df": df})
        result = serde.loads(serialized)

        for col in df.columns:
            assert result["df"][col].dtype == df[col].dtype, (
                f"Column {col}: expected {df[col].dtype}, got {result['df'][col].dtype}"
            )

    @pytest.mark.timeout(5)
    def test_performance_10k_rows(self) -> None:
        """Round-trip of 10K-row DataFrame completes in <5 seconds."""
        import pandas as pd
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        df = pd.DataFrame(
            {
                "a": range(10_000),
                "b": [f"val_{i}" for i in range(10_000)],
                "c": [float(i) * 0.1 for i in range(10_000)],
            }
        )

        serialized = serde.dumps({"df": df})
        result = serde.loads(serialized)

        pd.testing.assert_frame_equal(result["df"], df)

    def test_column_multiindex(self) -> None:
        """DataFrame with MultiIndex on columns."""
        import pandas as pd
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        cols = pd.MultiIndex.from_tuples([("a", "x"), ("a", "y"), ("b", "x")])
        df = pd.DataFrame([[1, 2, 3], [4, 5, 6]], columns=cols)

        serialized = serde.dumps({"df": df})
        result = serde.loads(serialized)

        pd.testing.assert_frame_equal(result["df"], df)


class TestT4Smoke:
    """Smoke/integration tests — realistic multi-node workflows."""

    def test_dataframe_survives_graph_checkpoint(self) -> None:
        """DataFrame in state survives checkpoint round-trip in multi-node graph."""
        import operator
        from typing import Annotated

        import pandas as pd
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.graph import StateGraph
        from typing_extensions import TypedDict

        class State(TypedDict):
            log: Annotated[list[str], operator.add]
            df: pd.DataFrame

        def step_1(state: State) -> dict:
            return {
                "log": ["step_1"],
                "df": pd.DataFrame({"a": [1, 2], "b": [3.0, 4.0]}),
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
        config = {"configurable": {"thread_id": "f1-smoke"}}

        result = compiled.invoke({"log": [], "df": pd.DataFrame()}, config=config)
        assert result["log"] == ["step_1", "step_2"]
        assert isinstance(result["df"], pd.DataFrame)
        assert list(result["df"]["a"]) == [1, 2]

        state = compiled.get_state(config)
        assert isinstance(state.values["df"], pd.DataFrame)

    def test_series_survives_graph_execution(self) -> None:
        """Series in state survives graph execution."""
        import pandas as pd
        from langgraph.graph import END, StateGraph
        from typing_extensions import TypedDict

        class State(TypedDict):
            series: pd.Series
            count: int

        def produce(state: State) -> dict:
            return {
                "series": pd.Series([10, 20, 30], name="values"),
                "count": state["count"] + 1,
            }

        def route(state: State) -> str:
            return END if state["count"] >= 1 else "produce"

        graph = StateGraph(State)
        graph.add_node("produce", produce)
        graph.add_conditional_edges("produce", route)
        graph.set_entry_point("produce")
        compiled = graph.compile()

        result = compiled.invoke({"series": pd.Series(dtype=float), "count": 0})
        assert isinstance(result["series"], pd.Series)
        assert result["series"].name == "values"
        assert list(result["series"]) == [10, 20, 30]
