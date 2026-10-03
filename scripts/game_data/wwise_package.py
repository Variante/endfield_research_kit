"""Wwise AKPK header/BKHD identity framing and crypto below Audio semantics.

Header reads do not load media payloads or publish page data.
"""
from __future__ import annotations
import struct
from dataclasses import dataclass
from typing import BinaryIO

KEY_SEED_XOR = 0x9C5A0B29
KEY_MULTIPLIER = 81861667

def derive_vfs_key(seed: int) -> int:
    key = ((seed & 0xFF) ^ KEY_SEED_XOR) * KEY_MULTIPLIER
    key &= 0xFFFFFFFF
    for shift in (8, 16, 24):
        key = (key ^ ((seed >> shift) & 0xFF)) * KEY_MULTIPLIER
        key &= 0xFFFFFFFF
    return key


def decrypt_vfs_bytes(data: bytearray, start: int, length: int, seed: int, data_offset: int = 0) -> None:
    if start < 0 or length < 0 or start + length > len(data):
        raise ValueError('Wwise crypto range outside supplied bytes')
    key_index = (seed + (data_offset >> 2)) & 0xFFFFFFFF
    pos = start
    remaining = length
    alignment = data_offset & 3
    if alignment:
        key = derive_vfs_key(key_index)
        to_align = min(4 - alignment, remaining)
        for i in range(to_align):
            data[pos] ^= (key >> ((alignment + i) * 8)) & 0xFF
            pos += 1
        remaining -= to_align
        key_index = (key_index + 1) & 0xFFFFFFFF

    for _ in range(remaining // 4):
        key = derive_vfs_key(key_index)
        value = int.from_bytes(data[pos : pos + 4], "little") ^ key
        data[pos : pos + 4] = value.to_bytes(4, "little")
        pos += 4
        key_index = (key_index + 1) & 0xFFFFFFFF

    trailing = remaining & 3
    if trailing:
        key = derive_vfs_key(key_index)
        for i in range(trailing):
            data[pos + i] ^= (key >> (i * 8)) & 0xFF


def decrypt_akpk_bytes(raw_data: bytes, label: str) -> bytes:
    data = bytearray(raw_data)
    if data[:4] == b":)xD":
        if len(data) < 12:
            raise ValueError(f'truncated AKPK header: {label}')
        header_size = int.from_bytes(data[4:8], "little")
        if not 16 <= header_size <= len(data) - 8:
            raise ValueError(f'invalid AKPK header extent: {label}')
        decrypt_vfs_bytes(data, 12, header_size - 4, header_size)
        data[:4] = b"AKPK"
        data[8:12] = (1).to_bytes(4, "little")
    if data[:4] != b"AKPK":
        raise ValueError(f"invalid AKPK magic: {label}")
    return bytes(data)


@dataclass(frozen=True)
class PackageEntry:
    sector: str
    key: int
    block_bytes: int
    byte_length: int
    block_offset: int
    language: int

    @property
    def byte_offset(self) -> int:
        return self.block_offset * (self.block_bytes or 1)


def read_entry_bytes(stream: BinaryIO, payload_offset: int, payload_bytes: int,
                     entry: PackageEntry, *, max_entry_bytes: int = 64 << 20) -> bytes:
    """Read one already framed entry, with a caller-selected payload bound.

    The physical stream may contain other VFS payloads. This deliberately does
    not infer a file identity or an encryption mode from its contents.
    """
    if payload_offset < 0 or entry.byte_offset < 0 or entry.byte_length < 0:
        raise ValueError('negative AKPK selected-entry extent')
    if entry.byte_offset + entry.byte_length > payload_bytes:
        raise ValueError('AKPK selected-entry outside logical payload')
    if entry.byte_length > max_entry_bytes:
        raise ValueError('AKPK selected-entry exceeds caller byte limit')
    stream.seek(payload_offset + entry.byte_offset)
    raw = stream.read(entry.byte_length)
    if len(raw) != entry.byte_length:
        raise ValueError('truncated AKPK selected-entry bytes')
    return raw


def read_header(stream: BinaryIO, payload_bytes: int, *, max_header_bytes: int = 16 << 20) -> dict:
    """Read a logical, already VFS-decoded payload at the stream's cursor."""
    prefix = stream.read(8)
    if len(prefix) != 8 or prefix[:4] not in (b'AKPK', b':)xD'):
        raise ValueError('invalid or truncated AKPK prefix')
    extent = struct.unpack_from('<I', prefix, 4)[0] + 8
    if not 24 <= extent <= min(payload_bytes, max_header_bytes):
        raise ValueError(f'AKPK header extent outside bounds: extent={extent}, payload={payload_bytes}, limit={max_header_bytes}')
    remainder = stream.read(extent - 8)
    if len(remainder) != extent - 8:
        raise ValueError('truncated AKPK header bytes')
    return parse_header(prefix + remainder, payload_bytes)


def read_bank_identity(stream: BinaryIO, payload_offset: int, payload_bytes: int,
                       entry: PackageEntry) -> dict:
    """Read the bank's stored identity under the explicit offline XOR profile.

    The installed format's bank path uses the full UInt32 bank key as the XOR
    seed (AnimeStudio EndfieldAkpkPackage.ParseBnk). Only the first sixteen
    bytes are consumed: BKHD extent, version and bank ID. This neither parses
    the remaining bank nor establishes which package the game would load.
    """
    if entry.sector != 'banks' or not 0 <= entry.key <= 0xffffffff:
        raise ValueError('BKHD identity requires a bank-sector UInt32 key')
    if (payload_offset < 0 or entry.byte_offset < 0 or entry.byte_length < 16
            or entry.byte_offset + entry.byte_length > payload_bytes):
        raise ValueError('BKHD identity entry outside logical payload')
    stream.seek(payload_offset + entry.byte_offset)
    prefix = bytearray(stream.read(16))
    if len(prefix) != 16:
        raise ValueError('truncated BKHD identity prefix')
    decrypt_vfs_bytes(prefix, 0, len(prefix), entry.key)
    if prefix[:4] != b'BKHD':
        raise ValueError('bank XOR profile does not produce BKHD')
    body_bytes, version, bank_id = struct.unpack_from('<3I', prefix, 4)
    if not 8 <= body_bytes <= entry.byte_length - 8:
        raise ValueError('BKHD declared extent outside bank entry')
    if bank_id != entry.key:
        raise ValueError('BKHD stored bank ID differs from AKPK bank key')
    return {'prefixBytes': 16, 'bkhdBodyBytes': body_bytes,
            'bankVersion': version, 'bankId': bank_id, 'transform': 'bankKeyXor'}


def parse_language_sector(raw: bytes) -> dict:
    """Read stored IDs and UTF-16LE labels under the Windows header profile.

    Only the explicit UTF-16LE profile is read; there is no encoding
    autodetection. Unterminated or invalid UTF-16LE strings are refused.
    Unreferenced bytes remain
    bounded raw ranges rather than acquiring language semantics.
    """
    if len(raw) < 4:
        raise ValueError('AKPK language sector lacks count')
    count = struct.unpack_from('<I', raw)[0]
    table_end = 4 + count * 8
    if table_end > len(raw):
        raise ValueError('AKPK language table exceeds sector')
    rows, ids, claimed = [], set(), bytearray(len(raw))
    claimed[:table_end] = b'\x01' * table_end
    for ordinal in range(count):
        offset, language = struct.unpack_from('<2I', raw, 4 + ordinal * 8)
        if language in ids:
            raise ValueError('AKPK language ID is duplicated')
        ids.add(language)
        if offset < table_end or offset % 2 or offset + 2 > len(raw):
            raise ValueError('AKPK language label offset outside string area')
        end = offset
        while end + 2 <= len(raw) and raw[end:end + 2] != b'\x00\x00':
            end += 2
        if end + 2 > len(raw):
            raise ValueError('unterminated AKPK UTF-16LE language label')
        try:
            label = raw[offset:end].decode('utf-16-le', errors='strict')
        except UnicodeDecodeError as error:
            raise ValueError('invalid AKPK UTF-16LE language label') from error
        end += 2
        claimed[offset:end] = b'\x01' * (end - offset)
        rows.append({'ordinal': ordinal, 'id': language, 'label': label,
                     'stringOffset': offset, 'stringEnd': end})
    unclaimed, cursor = [], table_end
    while cursor < len(raw):
        if claimed[cursor]:
            cursor += 1
            continue
        start = cursor
        while cursor < len(raw) and not claimed[cursor]:
            cursor += 1
        unclaimed.append({'start': start, 'end': cursor, 'rawHex': raw[start:cursor].hex().upper()})
    return {'encoding': 'utf-16-le', 'byteLength': len(raw), 'rows': rows,
            'unclaimedRanges': unclaimed}


def parse_header(raw: bytes, payload_bytes: int) -> dict:
    """Frame all index sectors; payload extents are checked without reading media."""
    data = decrypt_akpk_bytes(raw, 'header')
    if len(data) < 24:
        raise ValueError('truncated AKPK header words')
    size, version, languages, banks, sounds = struct.unpack_from('<5I', data, 4)
    if version != 1 or len(data) != size + 8 or len(data) > payload_bytes:
        raise ValueError(f'AKPK header version/extent mismatch: version={version}, declared={size + 8}, supplied={len(data)}')
    has_external = languages + banks + sounds + 16 < size
    if has_external and len(data) < 28:
        raise ValueError('truncated AKPK external-sector size')
    external = struct.unpack_from('<I', data, 24)[0] if has_external else 0
    language_start = 28 if has_external else 24
    cursor = language_start + languages
    if cursor + banks + sounds + external != len(data):
        raise ValueError('AKPK sector sizes do not close the header')
    language_table = (parse_language_sector(data[language_start:cursor]) if languages else
                      {'encoding': 'utf-16-le', 'byteLength': 0, 'rows': [], 'unclaimedRanges': []})
    entries, counts = [], {}
    for name, sector_size in (('banks', banks), ('sounds', sounds), ('externals', external)):
        if not sector_size:
            counts[name] = 0
            continue
        if sector_size < 4:
            raise ValueError(f'AKPK {name} sector smaller than count')
        count = struct.unpack_from('<I', data, cursor)[0]
        counts[name] = count
        stride, tail = divmod(sector_size - 4, count) if count else (0, sector_size - 4)
        if tail or (count and stride not in (20, 24)):
            raise ValueError(f'AKPK {name} index stride mismatch: size={sector_size}, count={count}, stride={stride}')
        for index in range(count):
            at = cursor + 4 + index * stride
            if name == 'externals' and stride == 24:
                key, block, length, offset, language = struct.unpack_from('<Q4I', data, at)
            elif stride == 24:
                key, block, length, offset, language = struct.unpack_from('<IIQII', data, at)
            else:
                key, block, length, offset, language = struct.unpack_from('<5I', data, at)
            entry = PackageEntry(name, key, block, length, offset, language)
            if entry.byte_offset + length > payload_bytes:
                raise ValueError(f'AKPK {name} row outside payload: row={index}, offset={entry.byte_offset}, length={length}, payload={payload_bytes}')
            entries.append(entry)
        cursor += sector_size
    return {'headerBytes': len(data), 'encryptedHeader': raw[:4] == b':)xD',
            'counts': counts, 'entries': entries, 'languageTable': language_table}


