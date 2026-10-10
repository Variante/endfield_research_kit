"""Bounded PE32+ AMD64 selected name/ordinal/function export joins.

Only the on-disk declaration is resolved. A direct RVA need not denote code;
function ownership and implementation belong to the consumer. Forwarders are
classified from the export-directory extent, not executed or followed.
"""
from __future__ import annotations
import hashlib
import struct
from scripts.game_data.il2cpp.pe_imports import _directory, _read, _string


def resolve_named_exports(image, wanted, *, name_limit=65536, function_limit=65536):
    wanted = list(wanted)
    if any(type(name) != str or not name or '\0' in name or not name.isascii() for name in wanted):
        raise ValueError('peExports.selected-name')
    wanted = sorted(set(wanted))
    if any(type(v) != int or not 0 < v <= 1 << 20 for v in (name_limit, function_limit)):
        raise ValueError('peExports.limits')
    directory, size, header = _directory(image, 0)
    if not directory or not 40 <= size <= 1 << 24 or directory + size > 1 << 32:
        raise ValueError('peExports.directory-range')
    raw = _read(image, directory, 40)
    flags, stamp, major, minor, dll, ordinal_base, functions, names, eat, name_table, ordinal_table = struct.unpack('<IIHHIIIIIII', raw)
    if flags or not dll or not 0 < functions <= function_limit or not 0 < names <= name_limit:
        raise ValueError('peExports.header-counts-or-required-fields')
    if ordinal_base + functions - 1 >= 1 << 32 or not eat or not name_table or not ordinal_table:
        raise ValueError('peExports.ordinal-range-or-tables')
    library, library_raw = _string(image, dll, 512)
    function_bytes = _read(image, eat, functions * 4)
    name_bytes = _read(image, name_table, names * 4)
    ordinal_bytes = _read(image, ordinal_table, names * 2)
    selected = {}; previous = None
    for n in range(names):
        name_rva = struct.unpack_from('<I', name_bytes, n * 4)[0]
        if not name_rva:
            raise ValueError('peExports.null-name-rva')
        name, name_raw = _string(image, name_rva, 2048)
        if previous is not None and name <= previous:
            raise ValueError('peExports.unsorted-or-duplicate-names')
        previous = name
        index = struct.unpack_from('<H', ordinal_bytes, n * 2)[0]
        if index >= functions:
            raise ValueError('peExports.ordinal-index-outside-functions')
        if name not in wanted:
            continue
        target = struct.unpack_from('<I', function_bytes, index * 4)[0]
        if not target:
            raise ValueError('peExports.selected-null-function')
        forwarded = directory <= target < directory + size
        if forwarded:
            forwarder, forwarder_raw = _string(image, target, min(2048, directory + size - target))
        else:
            _read(image, target, 1)  # Require raw-backed data; do not infer code.
            forwarder = None; forwarder_raw = b''
        selected[name] = {'symbolName': name, 'nameIndex': n,
            'namePointerSlotRva': name_table + n * 4, 'namePointerHex': name_bytes[n*4:n*4+4].hex(' '),
            'nameRva': name_rva, 'nameHex': name_raw.hex(' '),
            'ordinalIndexSlotRva': ordinal_table + n * 2, 'ordinalIndexHex': ordinal_bytes[n*2:n*2+2].hex(' '),
            'ordinalIndex': index, 'ordinal': ordinal_base + index,
            'functionSlotRva': eat + index * 4, 'functionSlotHex': function_bytes[index*4:index*4+4].hex(' '),
            'targetRva': target, 'isForwarder': forwarded, 'forwarder': forwarder,
            'forwarderHex': forwarder_raw.hex(' '), 'implementationOrLiveBindingProved': False}
    if set(selected) != set(wanted):
        raise ValueError('peExports.selected-name-missing:' + str(sorted(set(wanted)-set(selected)))[:512])
    return {'selectedExports': [selected[name] for name in wanted],
        'exportDirectoryRva': directory, 'exportDirectoryBytes': size, 'exportDirectoryHeader': header,
        'exportDirectoryHex': raw.hex(' '), 'libraryNameRva': dll, 'libraryName': library,
        'libraryNameHex': library_raw.hex(' '), 'ordinalBase': ordinal_base,
        'declaredFunctionCount': functions, 'declaredNameCount': names,
        'functionTableRva': eat, 'functionTableSha256': hashlib.sha256(function_bytes).hexdigest().upper(),
        'nameTableRva': name_table, 'nameTableSha256': hashlib.sha256(name_bytes).hexdigest().upper(),
        'ordinalTableRva': ordinal_table, 'ordinalTableSha256': hashlib.sha256(ordinal_bytes).hexdigest().upper(),
        'allDeclaredNameOrderAndOrdinalIndicesChecked': True,
        'completeExportImplementationCatalogProved': False, 'liveLoadedLibraryOrBindingProved': False}
