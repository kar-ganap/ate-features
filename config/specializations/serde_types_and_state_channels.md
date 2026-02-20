# Agent 1 Specialization: Serializer + State

## Serializer Subsystem

### Architecture
The checkpoint serializer lives in `libs/checkpoint/langgraph/checkpoint/serde/`.
The primary class is `JsonPlusSerializer` in `jsonplus.py`.

### Key Files
- `jsonplus.py` — Core serializer with msgpack extension handling
- `base.py` — `SerializerProtocol` (defines `dumps_typed`/`loads_typed`)
- `types.py` — `SendProtocol`, `ChannelProtocol` type definitions

### Extension Mechanism
Custom types are handled via msgpack ext codes defined at module level:
- `EXT_CONSTRUCTOR_SINGLE_ARG = 0` — constructor with 1 arg
- `EXT_CONSTRUCTOR_POS_ARGS = 1` — constructor with *args
- `EXT_CONSTRUCTOR_KW_ARGS = 2` — constructor with **kwargs
- `EXT_METHOD_SINGLE_ARG = 3` — class method with 1 arg
- `EXT_PYDANTIC_V1 = 4`, `EXT_PYDANTIC_V2 = 5`, `EXT_NUMPY_ARRAY = 6`

### Adding New Types
`_msgpack_default(obj)` uses cascading `isinstance`/`hasattr` checks. Each
handler wraps data in a tuple `(module_path, class_name, serialized_data)`
and packs it with `ormsgpack.Ext(code, encoded_bytes)`.

`_msgpack_ext_hook(code, data)` reverses the process: unpacks the tuple,
imports the class via `importlib.import_module`, and reconstructs the object.

### Passthrough Options
The serializer uses `OPT_PASSTHROUGH_DATACLASS | OPT_PASSTHROUGH_DATETIME |
OPT_PASSTHROUGH_ENUM | OPT_PASSTHROUGH_UUID` to route these types through
`_msgpack_default()` instead of ormsgpack's built-in handling.

## State Subsystem

### Architecture
State management lives in `libs/langgraph/langgraph/graph/state.py` and
the `channels/` package.

### Key Files
- `graph/state.py` — Channel selection from type annotations
- `channels/binop.py` — `BinaryOperatorAggregate` (reducer channels)
- `channels/last_value.py` — `LastValue` (default non-reducer channel)
- `_internal/_fields.py` — `get_field_default()`, field introspection utilities

### Channel Creation Pipeline
1. `_get_channels(schema)` extracts type hints via `get_type_hints(schema, include_extras=True)`
2. For each field, `_get_channel(name, typ)` decides the channel type:
   - `_is_field_managed_value()` → managed value
   - `_is_field_channel()` → explicit channel annotation
   - `_is_field_binop()` → `BinaryOperatorAggregate` (has a reducer)
   - Default → `LastValue`
3. `_is_field_binop(typ)` inspects `Annotated` metadata for a callable with
   a 2-parameter signature to use as the binary reduction operator

### Cross-subsystem Boundaries
- Serializer checkpoints state values that include channel contents
- `BinaryOperatorAggregate` stores accumulated values that the serializer
  must handle (lists, dicts, custom types)
- Agent 2 also works on state channels — the channel construction pipeline
  is shared between your work and theirs
