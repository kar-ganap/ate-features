# Agent 3 Specialization: Serializer + Streaming

## Serializer Subsystem

### Architecture
The checkpoint serializer lives in `libs/checkpoint/langgraph/checkpoint/serde/`.
The primary class is `JsonPlusSerializer` in `jsonplus.py`.

### Key Files
- `jsonplus.py` — Core serializer with msgpack extension handling
- `base.py` — `SerializerProtocol` (defines `dumps_typed`/`loads_typed`)
- `types.py` — `SendProtocol`, `ChannelProtocol` type definitions

### Enum Handling
Standard `Enum` and `StrEnum` instances are routed through `_msgpack_default()`
via the `OPT_PASSTHROUGH_ENUM` option. They are serialized with
`EXT_CONSTRUCTOR_SINGLE_ARG = 0`: the ext payload is
`(module, class_name, member_value)`.

Reconstruction in `_msgpack_ext_hook()` imports the class and calls
`cls(value)` to get the enum member back.

The passthrough option is critical — without it, ormsgpack serializes enums
as their raw value (string/int) and type identity is lost on deserialization.

### Passthrough Options
The serializer uses `OPT_PASSTHROUGH_DATACLASS | OPT_PASSTHROUGH_DATETIME |
OPT_PASSTHROUGH_ENUM | OPT_PASSTHROUGH_UUID` to route these types through
`_msgpack_default()` instead of ormsgpack's built-in handling.

## Streaming Subsystem

### Architecture
Stream message handling lives in
`libs/langgraph/langgraph/pregel/_messages.py`.

### Key Files
- `pregel/_messages.py` — `StreamMessagesHandler` callback handler
- `pregel/loop.py` — Pregel execution loop (invokes handlers)
- `types.py` — `StreamMode` enum and message type definitions

### Message Emission Pipeline
`StreamMessagesHandler` implements LangChain's `BaseCallbackHandler`.

`_find_and_emit_messages(values)` is the core scanning method:
1. Iterates over values in a state dict
2. For each value that is a sequence (list/tuple), checks items
3. Items that are `BaseMessage` instances get emitted via the `stream` callback
4. Scanning depth is limited — only top-level state keys and their
   immediate sequence contents are checked

The `on_chain_end(outputs)` callback triggers `_find_and_emit_messages`
after each node completes, extracting messages from the node's output state.

### Cross-subsystem Boundaries
- Serialized checkpoints include streaming state (which messages have been
  emitted) for resume scenarios
- Agent 4 also works on streaming — message deduplication depends on the
  emission scanning logic you work on
