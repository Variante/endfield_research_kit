# The native read path, from `ResourceManager` down to `ReadFile`

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, cross-lane.** How the game actually obtains the bytes of a logical
file, proven statically through the managed stream stack to the Win32 import. It
matters because it is the only route to an *authenticated* file receipt -- and the
chain does not currently provide one, which is why so many claims above stay
conditional.

## From the manager entry to `System.IO.Stream`

The manager entry's declared input independently joins `System.IO.Stream`.
Native slot addressing connects its length calls and buffer-fill slot to the
metadata virtual slots for `get_Length` and `Read`. Both allocation branches
perform one `Read` and discard its returned count before parsing the requested
carrier extent. Repeated length results also undergo unchecked 32-bit narrowing;
no stability, allocation/filled-length equality or full-read guarantee follows.

## `VFSFileReadStream`, its descriptor, and the chunk-name branch

The normal VFS allocation usage, constructor token and Stream parent now join
`VFSFileReadStream`. Its constructor copies a 32-byte descriptor and retains
the inner stream. Normal getters expose a descriptor length word and inner
position minus a descriptor base word. Read returns the inner stream's actual
count after a request-limit branch and optional prefix transformation, without
a full-fill loop. Normal inner-stream allocation joins `FileStream`; the two
selected helpers sign-extend the descriptor offset and seek with numeric origin
zero, but one requires a positive offset and the other any nonzero offset.
They discard the seek result. The normal mode getter shifts a packed dword;
its caller retains only eight bits, not the entire getter result. The relative
path's normal chunk-name branch uses a descriptor integer as a container
lookup key and copies a checked, indexed 16-byte result, not an inline hash
from the descriptor's leading bytes. Negative keys/results divert through a
helper; if it returns, the getter emits 16 zero bytes, not a proven exception.
Do not conflate this native descriptor with the serialized BLC file record.
The normal setter uses paired static containers: a lookup-hit integer or a
count-difference candidate reaches the descriptor; the miss path supplies the
integer and 16-byte input in opposite orders to two insertion helpers without
checking their returns. Original usage cells join Dictionary `TryGetValue` and
`set_Item` contexts with reversed Int32/UInt128 arguments, not the helper
identities suggested by inlined call targets. This is a conditional producer
path, not proof of successful insertion, reciprocal live contents or BLC MD5
provenance. Preserve the distinct seek predicates; complete container
mutation/initialization, alternate path branches, path encoding/root selection,
constructor/seek internals, replacements and the descriptor-to-authenticated
logical-file identity/hash remain unproved. This is not a runtime receipt.

## `ReadFromByteBuf`, the main info reader, and the XOR transform

`ReadFromByteBuf` now connects a mutable ByteBufStream cursor/array carrier to
the 16-byte lookup input and descriptor result on its normal path. Its initial
skip adds two in 16 bits before sign extension. The selected little-endian
eight-byte helper can return zero for insufficient length while the caller
still advances; do not treat successful return as byte provenance or reuse
this permissiveness in maintained parsers. The array's authenticated source,
later version/flag branches and final cursor still require independent proof.
Main-info construction now preserves the original array and supplied starting
index in that carrier, shared by nested chunk/file loops. The main reader's
pre-parse tail comparison is distinct from consumption: its normal final
remainder calculation clamps nonpositive values to zero, and the selected
legacy branch performs one extra integer read without a subsequent EOF
equality check. A returned object therefore cannot certify full consumption.
Its upstream block-group entry retains the original array through an in-place
transform and forwards that same array to the main reader. The normal worker
XORs input bytes with a state-buffer byte; its adapter aliases both arrays and
offsets. Nonpositive counts return without validation. The transform offset
and subsequent parse start are separate loads from the same static storage,
not a demonstrated immutable value. Key/span/constructor ABI, state-block
generation, complete cipher parity and replacement paths remain open; array

## Down through `File.ReadAllBytes` and MonoIO to `ReadFile`

aliasing alone is not a decryption or EOF proof. Both block-construction
branches now retain the array returned by their normal file-helper path
through that entry. Those helpers converge on `File.ReadAllBytes`, whose
positive-length loop accumulates actual read counts and reduces remaining
bytes; zero returns leave the normal loop for error helpers. Its array/offset/
count overload uses slot 34, distinct from the previously reviewed slot 35.
Its normal FileStream overload reaches MonoIO, then a PE import-name join to
`ReadFile`; the supplied out DWORD, not the API boolean, supplies the read
count. The error word is populated through `GetLastError` on the failure
branch and selects count versus -1. Keep API status, error, byte count and
accumulated count distinct. This static join does not prove live IAT contents,
handle provenance or buffered-state invariants; full-fill remains conditional.

## Building the path: carriers, `AppendPathInfo`, the format resolver

The two file-helper checks copy a 32-byte/four-slot path carrier from distinct
builders. Slot +8 comes from their respective getter; null/empty first input
shifts the second candidate into +0x10 and leaves +0x18 zero. AppendPathInfo
forwards the slots in order after null substitution. Its original AppendFormat
MethodSpec has three ordered string arguments; shared-code type candidates
cannot replace this companion. The temporary cursor and subsequent append
count use two-byte units: append doubles count for copying but advances its
cursor by the original count, writing a zero terminator only below capacity.
The native tag-5 resolver independently connects selected first-slot loads to
bounded literal-table/pool bytes: four brace/slash patterns are static format
inputs, not executed output paths. The literal sweep validates every row while
allowing shared pool ranges; it does not claim exclusive metadata coverage.
The format-item helper and its separate cold fragment establish a local
32-byte return: selector, optional bounded colon span, index after the closing
brace and comma-derived numeric value. This cursor is not whole-format EOF;
The character helper bounds the DWORD index against carrier length and reads
two-byte elements. Literal construction independently joins ASCII widening,
element-count forwarding and the same length/data offsets in the output carrier.
Allocation/copy/capacity helpers, non-ASCII cold paths and complete arbitrary-input
grammar remain open; this does not establish Unicode conversion parity.

## The streaming-assets interface request, and the loader

The normal streaming-path getter requests the exact Unity streaming-assets
interface name through a cached indirect-call resolver and stores its return.
This proves the static request, not the resolved implementation or directory;
The resolver reads a runtime tree, can retry with a helper-transformed query,
and returns a candidate value or zero on the final sentinel. A writer independently
stores its second argument into the same candidate value slot; a separate initializer
seeds a self-linked sentinel. A selected PE export chain connects
`il2cpp_add_internal_call` through an argument-preserving tail stub to this writer;
this is not complete export coverage or a concrete registration receipt.
Exact-build UnityPlayer additionally requests that export into a function cache;
a reviewed forwarder passes its original pair through optional callbacks before
tail-calling the cache. The loader's shared module-handle cell receives either
a helper-supplied cached qword or the preserved return from the static
`LoadLibraryW` import after representation conversion and slash replacement.
The lookup helper forwards module/name to the static `GetProcAddress` import;
its zero-result cold path rejoins the saved zero if diagnostic calls return.
Selected import descriptor/name-thunk joins prove these request identities,
not live IAT contents, conversion validity, input path or loaded image identity.
A selected caller independently constructs the exact inline `GameAssembly.dll`
basename, writes its terminator, sets the length representation and passes that
carrier to the loader. This proves requested bytes, not Windows search-path
resolution or the loaded image's absolute path/hash.
The conversion helper calls the static `MultiByteToWideChar` import first with
null output, then with a prepared output/count. Its first result sets the
representation length and prewritten terminator; the module caller does not
inspect the second result before deriving data plus twice that representation
length as the slash-loop end. Capacity/reset helpers and actual conversion
success remain open; the end pointer is not a verified converted-byte receipt.
Successful resolution and callback contents remain unknown.
A complete native loop now proves one static name/value pair by
loading both arrays with the same advancing byte offset; complete pointer vectors
are bounded, not fully decoded strings/functions. Its registered name omits the
request's parentheses. On successful delimiter search, the resolver constructs
a bounded prefix before the first left parenthesis, then moves that representation
into its second query. The comparator uses unsigned byte lexicographic ordering;
callers compare the shorter prefix then break ties by length, so equal prefixes
do not establish equal keys. Copy semantics, pointer validity and actual lookup remain open;
this is not arbitrary suffix stripping or a no-match guarantee. This is not evidence
of invocation, final registration ownership or target behavior. Insertion/query helpers, live contents
and the Unity implementation join remain open; static producer code is not execution.
The selected target returns a converter output slot after temporary cleanup.
The converter's tagged inline/pointer representation and length extraction are
directly connected. Loader requests and selected exports connect its dynamic
calls to string construction and an output-slot write barrier; the latter
stores the former's result. This is conditional on actual module/cache binding,
not proof of runtime construction, active GC state or directory value.
A static `StreamingAssets` literal is an input to a joining helper, not proof
of a concrete directory or validated managed-string construction.
Nested dispatch, capacity/copy helpers, getter values, final path/root,
on-disk identity/hash, zero-length alternate behavior and concrete execution
remain unresolved; neither four pointer slots nor getter names prove a path.
Multi-segment conversion, the complete ResourceManager-to-reader path and authenticated input
