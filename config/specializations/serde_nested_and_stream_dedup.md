# Agent 4 Specialization: Serializer + Streaming

## Serializer Subsystem

### Architecture
The checkpoint serializer lives in `libs/checkpoint/langgraph/checkpoint/serde/`.
The primary class is `JsonPlusSerializer` in `jsonplus.py`.

### Key Files
- `jsonplus.py` — Core serializer with msgpack extension handling
- `base.py` — `SerializerProtocol` (defines `dumps_typed`/`loads_typed`)
- `types.py` — `SendProtocol`, `ChannelProtocol` type definitions

### Nested Type Reconstruction
`_msgpack_ext_hook(code, data)` handles reconstruction for all ext codes:
- `EXT_CONSTRUCTOR_SINGLE_ARG = 0` — `cls(arg)`
- `EXT_CONSTRUCTOR_POS_ARGS = 1` — `cls(*args)`
- `EXT_CONSTRUCTOR_KW_ARGS = 2` — `cls(**kwargs)`
- `EXT_METHOD_SINGLE_ARG = 3` — `getattr(cls, method)(arg)`

When types are nested (e.g., an Enum inside a dataclass inside a list),
ormsgpack processes ext codes bottom-up. Inner objects are deserialized
first, then the containing structure's ext hook receives already-
reconstructed inner values.

### Extension Mechanism
`_msgpack_default(obj)` uses cascading `isinstance`/`hasattr` checks. Each
handler wraps data in a tuple `(module_path, class_name, serialized_data)`
and packs it with `ormsgpack.Ext(code, encoded_bytes)`.

The tuple structure is consistent across all ext codes — the ext hook
always unpacks `(module, name, data)` and uses `importlib.import_module`
to locate the class.

## Streaming Subsystem

### Architecture
Stream message handling lives in
`libs/langgraph/langgraph/pregel/_messages.py`.

### Key Files
- `pregel/_messages.py` — `StreamMessagesHandler` callback handler
- `pregel/loop.py` — Pregel execution loop (invokes handlers)
- `types.py` — `StreamMode` enum and message type definitions

### Deduplication via Seen Set
`StreamMessagesHandler.__init__()` initializes `self.seen: set[str]` to
track message IDs that have already been emitted.

`on_chain_start(inputs)` populates the seen set from input state via
`_state_values(inputs)`: it scans input values for `BaseMessage` instances
and adds their `id` to `self.seen`.

When `_find_and_emit_messages()` encounters a message, it checks
`msg.id in self.seen` before emitting. This prevents re-emitting messages
that were already in the state when the node started.

The seen set is populated from **inputs** (start of node) and checked
during **outputs** (end of node), creating a before/after diff.

### Cross-subsystem Boundaries
- Serialized checkpoints include streaming state for resume scenarios
- Agent 3 also works on streaming — the emission logic that Agent 3
  modifies feeds into the deduplication logic you work on
