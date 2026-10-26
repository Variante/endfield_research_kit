"""Read AMD64 exception-table membership through exact unwind parent triples.

Version 1 and 2 share the header, padded code-slot array and parent/handler
framing. Code-slot semantics and language-specific handler data are outside
this reader. A selected-image caller owns native freshness gates.
"""
from __future__ import annotations

import hashlib
import struct
from collections import Counter
from dataclasses import dataclass
from typing import Callable


def _require(condition: bool, check: str, detail: object) -> None:
    if not condition:
        raise ValueError(f'unwind-chain.{check}: {str(detail)[:384]}')


def read_exception_directory(pe) -> tuple[int, int, bytes]:
    """Read the declared PE exception directory, without section-padding rows."""
    data = pe.buf
    _require(len(data) >= 64 and data[:2] == b'MZ', 'dos-header', len(data))
    header = struct.unpack_from('<I', data, 0x3c)[0]
    _require(64 <= header <= len(data)-24, 'pe-header-range', header)
    _require(data[header:header+4] == b'PE\0\0', 'pe-signature', header)
    _require(struct.unpack_from('<H', data, header+4)[0] == 0x8664, 'machine', header)
    size = struct.unpack_from('<H', data, header+20)[0]
    optional = header+24
    _require(size >= 144 and optional+size <= len(data), 'optional-header-range', size)
    _require(struct.unpack_from('<H', data, optional)[0] == 0x20b, 'pe32-plus', optional)
    base = struct.unpack_from('<Q', data, optional+24)[0]
    image_size = struct.unpack_from('<I', data, optional+56)[0]
    _require(type(pe.image_base) is int and base == pe.image_base and base+image_size <= 1 << 64,
             'image-coordinates', (base, image_size))
    _require(struct.unpack_from('<I', data, optional+108)[0] > 3, 'exception-directory-missing', optional)
    rva, length = struct.unpack_from('<II', data, optional+136)
    _require(rva > 0 and rva%4 == 0 and length > 0 and length%12 == 0
             and rva+length <= image_size, 'exception-directory-range', (rva, length, image_size))
    raw = pe.bytes_at_va(base+rva, length)
    _require(isinstance(raw, bytes) and len(raw) == length, 'exception-directory-read',
             len(raw) if isinstance(raw, bytes) else type(raw).__name__)
    return rva, image_size, raw


@dataclass(frozen=True, slots=True)
class UnwindRecord:
    version: int
    flags: int
    prologue_bytes: int
    code_slots: int
    frame_byte: int
    raw: bytes
    parent: tuple[int, int, int] | None
    handler_rva: int | None


class UnwindChainIndex:
    """Exhaust the declared runtime table and reject broken or cyclic parents.

    Membership describes code ranges named by unwind metadata. It is not a
    complete managed-method execution proof or an interpreter for unwind codes.
    """
    def __init__(self, raw: bytes, read_rva: Callable[[int, int], bytes], *,
                 table_rva: int, image_size: int) -> None:
        _require(isinstance(raw, bytes) and len(raw) > 0 and len(raw)%12 == 0,
                 'table-framing', len(raw) if isinstance(raw, bytes) else type(raw).__name__)
        _require(type(image_size) is int and 0 < image_size < 1 << 32,
                 'image-size', image_size)
        _require(type(table_rva) is int and table_rva > 0 and table_rva%4 == 0
                 and table_rva+len(raw) <= image_size, 'table-coordinate', table_rva)
        _require(callable(read_rva), 'reader', type(read_rva).__name__)
        self.raw = raw
        self.table_rva = table_rva
        self.image_size = image_size
        self.read_rva = read_rva
        self.entries: dict[int, tuple[int, int, int]] = {}
        self.row_indices: dict[int, int] = {}
        self.records: dict[int, UnwindRecord] = {}
        self.parents: dict[int, int | None] = {}
        self.owners: dict[int, int] = {}
        previous_end = 0
        for index, row in enumerate(struct.iter_unpack('<III', raw)):
            begin, end, info = row
            _require(0 < begin < end <= image_size and info > 0 and info%4 == 0
                     and info+4 <= image_size, 'runtime-triple', (index, row))
            _require(begin >= previous_end, 'table-order-or-overlap', (index, row, previous_end))
            self.entries[begin] = row
            self.row_indices[begin] = index
            previous_end = end
        for begin, row in self.entries.items():
            record = self.record(row[2])
            if record.parent is None:
                self.parents[begin] = None
                continue
            parent_begin = record.parent[0]
            _require(self.entries.get(parent_begin) == record.parent,
                     'complete-parent-triple', (row, record.parent, self.entries.get(parent_begin)))
            parent_record = self.record(record.parent[2])
            _require(record.frame_byte == parent_record.frame_byte,
                     'frame-byte-match', (row, record.frame_byte, parent_record.frame_byte))
            self.parents[begin] = parent_begin
        self.families = {}
        for begin,triple in self.entries.items():
            self.families.setdefault(self.resolve(begin),[]).append(triple)
        self.versions = dict(sorted(Counter(self.record(row[2]).version for row in self.entries.values()).items()))
        self.table_sha256 = hashlib.sha256(self.raw).hexdigest().upper()

    def _read(self, rva: int, size: int) -> bytes:
        _require(0 < rva and 0 < size and rva+size <= self.image_size,
                 'unwind-read-range', (rva, size, self.image_size))
        try:
            raw = self.read_rva(rva, size)
        except (ValueError, IndexError, OSError) as error:
            raise ValueError(f'unwind-chain.unwind-read: rva={rva:#x} size={size} {str(error)[:256]}') from error
        _require(isinstance(raw, bytes) and len(raw) == size, 'unwind-short-read',
                 (rva, size, len(raw) if isinstance(raw, bytes) else type(raw).__name__))
        return raw

    def record(self, rva: int) -> UnwindRecord:
        if rva in self.records:
            return self.records[rva]
        head = self._read(rva, 4)
        version, flags = head[0]&7, head[0]>>3
        _require(version in (1, 2), 'unwind-version', (rva, version))
        _require(flags <= 7 and not (flags&4 and flags&3), 'unwind-flags', (rva, flags))
        padded = 4+((head[2]+1)&~1)*2
        tail_size = 12 if flags&4 else 4 if flags&3 else 0
        raw = self._read(rva, max(8, padded+tail_size))
        _require(raw[:4] == head, 'unwind-header-changed', rva)
        parent = struct.unpack_from('<III', raw, padded) if flags&4 else None
        handler = struct.unpack_from('<I', raw, padded)[0] if flags&3 else None
        if handler is not None:
            _require(0 < handler < self.image_size, 'handler-rva', (rva, handler))
        value = UnwindRecord(version, flags, head[1], head[2], head[3], raw, parent, handler)
        self.records[rva] = value
        return value

    def resolve(self, begin: int) -> int:
        _require(type(begin) is int and begin in self.entries, 'entry-missing', begin)
        path = []
        visited = set()
        cursor = begin
        while cursor not in self.owners:
            _require(cursor not in visited, 'parent-cycle', (begin, path, cursor))
            visited.add(cursor)
            path.append(cursor)
            parent = self.parents[cursor]
            if parent is None:
                owner = cursor
                break
            cursor = parent
        else:
            owner = self.owners[cursor]
        for child in path:
            self.owners[child] = owner
        return owner

    def family(self, entry_rva: int) -> dict:
        _require(self.resolve(entry_rva) == entry_rva, 'selected-entry-not-primary', entry_rva)
        selected = []
        for triple in self.families[entry_rva]:
            begin = triple[0]
            record = self.record(triple[2])
            chain = []
            cursor = begin
            while self.parents[cursor] is not None:
                child = self.entries[cursor]
                parent = self.entries[self.parents[cursor]]
                chain.append({'child': list(child), 'parent': list(parent)})
                cursor = parent[0]
            selected.append({'runtimeTriple': list(triple),
                'tableRowRva': self.table_rva+self.row_indices[begin]*12,
                'runtimeTripleRawHex': struct.pack('<III', *triple).hex().upper(),
                'codeBytes': triple[1]-triple[0], 'unwindRawHex': record.raw.hex().upper(),
                'unwindVersion': record.version, 'unwindFlags': record.flags,
                'frameByte': record.frame_byte, 'parentChain': chain})
        return {'schema': 'endfield.amd64-unwind-chain-family.v1',
            'selectedPrimaryRva': entry_rva, 'tableRva': self.table_rva,
            'tableBytes': len(self.raw), 'tableSha256': self.table_sha256,
            'tableRowsChecked': len(self.entries), 'unwindVersionRows': dict(self.versions),
            'completeParentTriplesChecked': True, 'allParentChainsTerminated': True,
            'chainFrameBytesMatched': True, 'ranges': selected,
            'unwindOperationsOrFixedAllocationSemanticsProved': False,
            'handlerLanguageDataProved': False, 'wholeManagedMethodProgramProved': False,
            'runtimeExecutionKnown': False,
            'evidenceBoundary': 'Exact declared exception-table framing and complete parent triples establish selected-primary range membership, including nested and noncontiguous chains. Version 1/2 code-slot contents, fixed-allocation consistency, handlers, managed control flow, live MethodInfo and execution remain separate proofs; adjacency and start-address-only joins are not used.'}
