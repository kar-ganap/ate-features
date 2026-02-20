# Agent 2 Specialization: Serializer + State

## Serializer Subsystem

### Architecture
The checkpoint serializer lives in `libs/checkpoint/langgraph/checkpoint/serde/`.
The primary class is `JsonPlusSerializer` in `jsonplus.py`.

### Key Files
- `jsonplus.py` — Core serializer with msgpack extension handling
- `base.py` — `SerializerProtocol` (defines `dumps_typed`/`loads_typed`)
- `types.py` — `SendProtocol`, `ChannelProtocol` type definitions

### Pydantic Handling
Pydantic models have dedicated ext codes:
- `EXT_PYDANTIC_V1 = 4` — Pydantic V1 `BaseModel` instances
- `EXT_PYDANTIC_V2 = 5` — Pydantic V2 `BaseModel` instances

In `_msgpack_default(obj)`, a Pydantic V2 model is detected via
`hasattr(obj, "model_dump")` and serialized as
`(module, class_name, model_dump_dict)`. The ext hook reconstructs via
`cls(**data)`.

### Round-trip Pattern
`dumps_typed(obj)` → ormsgpack with passthrough options → `_msgpack_default`
for unhandled types → ext bytes.
`loads_typed((type_tag, bytes))` → ormsgpack unpack → `_msgpack_ext_hook`
for ext codes → reconstructed object.

The `type_tag` is a string (`"msgpack"` or `"json"`) that selects the codec.

## State Subsystem

### Architecture
State management lives in `libs/langgraph/langgraph/graph/state.py` and
the `channels/` package.

### Key Files
- `graph/state.py` — Channel selection from type annotations
- `channels/binop.py` — `BinaryOperatorAggregate` (reducer channels)
- `channels/last_value.py` — `LastValue` (default non-reducer channel)
- `_internal/_fields.py` — `get_field_default()`, field introspection utilities

### BinaryOperatorAggregate Internals
`__init__(self, typ, operator, default=...)` stores the reduction function
and initializes `self.value = default if default is not EMPTY else typ()`.

`update(values)` folds: `self.value = reduce(operator, values, self.value)`.

`get()` returns the current accumulated value.

The `typ()` call for default initialization means the type must be
callable with zero arguments (e.g., `list`, `dict`, `int`). Custom types
that require constructor arguments need an explicit `default` parameter.

### Cross-subsystem Boundaries
- Serializer checkpoints state values that include channel contents
- `BinaryOperatorAggregate` stores accumulated values that the serializer
  must handle (lists, dicts, custom types)
- Agent 1 also works on state channels — the channel construction pipeline
  is shared between your work and theirs
