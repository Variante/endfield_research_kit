"""Exact reader for the exported JsonData ``StringPool`` (``USPC``) pages.

Newer client builds stop inlining strings in compact JsonData payloads such as
``LevelConfig``: each string member becomes an ``i32`` global pool index. The
pool holds no empty string; ``-1`` stands for ``""`` and ``-2`` for null
(direct by corpus correspondence: every previous-build ``''`` LevelConfig
member is ``-1`` and every null water-audio member ``-2``, except levels whose
content changed between the builds). The pool ships as
``Json/StringPool/StringPool<N>.byte``.

Page framing (exact on every page of the build that introduced it):

* ``StringPool0.byte`` alone starts with a ``u32`` equal to the last page
  index; the other pages start directly at the header. The reader requires
  that value to name exactly the contiguous page set it finds (structural
  interpretation: it is consistent with one build, not native-proven).
* header ``<4sIIIII``: magic ``USPC``, two ``u32`` fields observed as 1, the
  string count, the decompressed size and the compressed size; then exactly
  that many bytes of one plain LZ4 block, with no trailing bytes.
* decompressed body: ``u32 count`` (equal to the header count), ``count`` ×
  ``u32`` offsets relative to the end of the offset table, and at each offset
  an ``i32`` byte length followed by UTF-8.

Global index ``i`` resolves to page ``i // pageSize`` entry ``i % pageSize``,
where ``pageSize`` is the shared count of every page but the last (direct:
LevelConfig indices resolve to the old build's inline strings for the same
level). ``StringPoolHashIndex.byte`` (``SHPI``) and ``StringPoolCounting.json``
are not read; the hash index is an unresolved lookup accelerator and the
counting file is developer statistics.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

from scripts.game_data.lz4_block import decompress_lz4

MAGIC = b"USPC"
HEADER = struct.Struct("<4sIIIII")
PAGE_RE = re.compile(r"StringPool(\d+)\.byte")
MAX_STRING_BYTES = 1 << 20
EMPTY_INDEX = -1
NULL_INDEX = -2


class StringPoolDecodeError(ValueError):
    """Raised when a StringPool page or index fails exact framing."""


def _page_header(data: bytes, page: int) -> tuple[int, int, int, int]:
    """Return ``(header_offset, count, uncompressed, compressed)`` for one page."""
    offset = 4 if page == 0 else 0
    if len(data) < offset + HEADER.size:
        raise StringPoolDecodeError(f"StringPool{page}: truncated header ({len(data)} bytes)")
    magic, v1, v2, count, uncompressed, compressed = HEADER.unpack_from(data, offset)
    if magic != MAGIC or (v1, v2) != (1, 1):
        raise StringPoolDecodeError(
            f"StringPool{page}: header mismatch magic={magic!r} fields=({v1}, {v2}) expected=(b'USPC', 1, 1)"
        )
    end = offset + HEADER.size + compressed
    if end != len(data):
        raise StringPoolDecodeError(
            f"StringPool{page}: compressed size {compressed} leaves {len(data) - end} trailing bytes"
        )
    return offset, count, uncompressed, compressed


def decode_string_pool_page(data: bytes, page: int) -> list[str]:
    """Decode one page's strings in entry order."""
    offset, count, uncompressed, compressed = _page_header(data, page)
    start = offset + HEADER.size
    try:
        body = decompress_lz4(data[start : start + compressed], uncompressed)
    except ValueError as exc:
        raise StringPoolDecodeError(f"StringPool{page}: LZ4 block: {exc}") from exc
    if len(body) != uncompressed or len(body) < 4:
        raise StringPoolDecodeError(f"StringPool{page}: decompressed {len(body)} bytes, expected {uncompressed}")
    (body_count,) = struct.unpack_from("<I", body, 0)
    if body_count != count:
        raise StringPoolDecodeError(f"StringPool{page}: body count {body_count} != header count {count}")
    table_end = 4 + 4 * count
    if table_end > len(body):
        raise StringPoolDecodeError(f"StringPool{page}: offset table overruns body")
    offsets = struct.unpack_from(f"<{count}I", body, 4)
    strings: list[str] = []
    for entry, rel in enumerate(offsets):
        cursor = table_end + rel
        if cursor + 4 > len(body):
            raise StringPoolDecodeError(f"StringPool{page}[{entry}]: offset {rel} outside body")
        (length,) = struct.unpack_from("<i", body, cursor)
        if length < 0 or length > MAX_STRING_BYTES or cursor + 4 + length > len(body):
            raise StringPoolDecodeError(f"StringPool{page}[{entry}]: invalid length {length}")
        try:
            strings.append(body[cursor + 4 : cursor + 4 + length].decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise StringPoolDecodeError(f"StringPool{page}[{entry}]: invalid UTF-8") from exc
    return strings


class StringPool:
    """Lazily decoded global string table over one export's pool pages."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        pages = sorted(
            int(match.group(1))
            for path in self.root.glob("StringPool*.byte")
            if (match := PAGE_RE.fullmatch(path.name))
        )
        if not pages:
            raise StringPoolDecodeError(f"{self.root}: no StringPool<N>.byte pages")
        if pages != list(range(len(pages))):
            raise StringPoolDecodeError(f"{self.root}: non-contiguous pages {pages}")
        first = self._read(0)
        if len(first) < 4:
            raise StringPoolDecodeError("StringPool0: truncated page-count prefix")
        (declared_last,) = struct.unpack_from("<I", first, 0)
        if declared_last != len(pages) - 1:
            raise StringPoolDecodeError(
                f"StringPool0 declares last page {declared_last}, found pages 0..{len(pages) - 1}"
            )
        self.counts = [
            _page_header(first if page == 0 else self._read(page), page)[1] for page in pages
        ]
        sizes = set(self.counts[:-1]) or {self.counts[0]}
        if len(sizes) != 1 or self.counts[-1] > next(iter(sizes)):
            raise StringPoolDecodeError(f"{self.root}: unequal page counts {self.counts}")
        self.page_size = next(iter(sizes))
        self._pages: dict[int, list[str]] = {}
        self._reverse: dict[str, tuple[int, ...]] | None = None

    def _read(self, page: int) -> bytes:
        path = self.root / f"StringPool{page}.byte"
        try:
            return path.read_bytes()
        except OSError as exc:
            raise StringPoolDecodeError(f"{path}: {exc}") from exc

    def __len__(self) -> int:
        return sum(self.counts)

    def resolve(self, index: int) -> str | None:
        """Return the string at a global index: ``""`` for ``-1``, ``None`` for ``-2``."""
        if index == EMPTY_INDEX:
            return ""
        if index == NULL_INDEX:
            return None
        if index < 0 or index >= len(self):
            raise StringPoolDecodeError(f"string index {index} outside pool of {len(self)}")
        page, entry = divmod(index, self.page_size)
        if page not in self._pages:
            self._pages[page] = decode_string_pool_page(self._read(page), page)
        return self._pages[page][entry]

    def indices_of(self, value: str) -> tuple[int, ...]:
        """Return every global index holding ``value``, for anchoring a byte scan.

        Decodes every page once; the pool does not promise unique entries.
        """
        if self._reverse is None:
            reverse: dict[str, list[int]] = {}
            for index in range(len(self)):
                reverse.setdefault(self.resolve(index), []).append(index)
            self._reverse = {key: tuple(found) for key, found in reverse.items()}
        return self._reverse.get(value, ())


def resolve_string_pool_index(index: int, strings: StringPool | None, field: str = 'string') -> str | None:
    """Resolve a proved signed pool index; missing pages never select inline text."""
    if type(index) is not int or not -2 <= index < 1 << 31:
        raise StringPoolDecodeError(f'{field}:invalid-pool-index={index!r}')
    if index == EMPTY_INDEX:return ''
    if index == NULL_INDEX:return None
    if strings is None:raise StringPoolDecodeError(f'{field}:matching-StringPool-required,index={index}')
    value=strings.resolve(index)
    if not isinstance(value,str):raise StringPoolDecodeError(f'{field}:invalid-pool-entry,index={index}')
    return value


def export_string_pool(json_dir: Path) -> StringPool | None:
    """Return the pool beside an export's JsonData families, or ``None`` when absent.

    Each call selects fresh pages. None means unavailable; the owning reader
    must select its proved encoding rather than infer inline storage from absence.
    """
    root = Path(json_dir) / "StringPool"
    return StringPool(root) if root.is_dir() else None
