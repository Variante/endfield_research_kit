"""Indexed union selection and complete new-child route/return below admission."""
from __future__ import annotations
from typing import Any, Callable

from scripts.game_data.memorypack.read_value_reference_sources import _profile
from scripts.game_data.memorypack.reference_conversion_sources import _target


def validate_indexed_union_prefix(image: Any, proof: dict, dispatcher: dict,
                                   helper_rva: int, *, fail: Callable) -> dict:
    count, tag, table = (dispatcher[k] for k in ('switchEntryCount', 'unionTag', 'switchTableRva'))
    if (type(count) is not int or not 1 <= count <= 65536 or type(tag) is not int or not 0 <= tag < count
            or type(table) is not int or not 0 <= table < 2 ** 32):
        fail('indexed-union-scope', 'bounded UInt16 tag and four-byte RVA table', dispatcher)
    rows, windows = proof['program'], proof['codeWindows']
    expected = ['48895C2408', '4889742418', '57', '4883EC20', None, '498BD8', '488BFA', None,
                '33F6', '488D542438', '4533C0', '6689742438', '488BCF', None,
                '84C0', None, '0FB7742438', '81FE' + (count - 1).to_bytes(4, 'little').hex().upper(),
                None, None, '8B8CB2' + table.to_bytes(4, 'little').hex().upper(), '4803CA', 'FFE1']
    if not windows or len(rows) != len(expected) or rows[0][0] != windows[0]['startRva']:
        fail('indexed-union-prefix', 'complete entry through the computed table jump', rows)
    image.check_windows(windows, label='indexedUnionPrefix')
    image.check_instruction_windows(rows, label='indexedUnionPrefix')
    for n, ((at, h), wanted) in enumerate(zip(rows, expected, strict=True)):
        raw = bytes.fromhex(h)
        if not raw or not any(w['startRva'] <= at < at + len(raw) <= w['endRva'] for w in windows):
            fail('indexed-union-owner', 'one complete owned instruction', rows[n])
        if wanted is not None and h != wanted:
            fail('indexed-union-transfer', {'position': n, 'bytes': wanted}, rows[n])
        if h != '4803CA':
            decoded = image.mapper.decode_x64_subset(raw, image.pe.image_base + at, stop_offset=len(raw))
            if len(decoded) != 1 or 'db ' in decoded[0]['text']:
                fail('indexed-union-instruction', 'complete understood x64 instruction', rows[n])
        if n == 4 and (len(raw) != 7 or raw[:2] != b'\x80\x3d' or raw[-1] != 0):
            fail('indexed-union-initialization', 'warmed RIP byte guard', rows[n])
        if n in (7, 15, 18) and (len(raw) != 6 or raw[:2] != (b'\x0f\x87' if n == 18 else b'\x0f\x84')):
            fail('indexed-union-selected-guards', 'untaken initialization/false/unsigned range guards', rows[n])
        if n == 13 and (len(raw) != 5 or raw[0] != 0xe8 or _target(at, raw) != helper_rva):
            fail('indexed-union-actual-tag-helper', helper_rva, rows[n])
        if n == 19 and (len(raw) != 7 or raw[:3] != b'\x48\x8d\x15'
                        or at + 7 + int.from_bytes(raw[3:], 'little', signed=True) != 0):
            fail('indexed-union-image-base', 'actual RIP LEA resolves to image base', rows[n])
        if n < len(rows) - 1 and rows[n + 1][0] != at + len(raw):
            fail('indexed-union-prefix-successor', 'complete selected fallthrough prefix', rows[n:n + 2])
    target = image.pe.u32_at_va(image.pe.image_base + table + tag * 4)
    if target != dispatcher['switchTargetRva']:
        fail('indexed-union-actual-table-successor', dispatcher['switchTargetRva'], target)
    return {'selectedTag': tag, 'tableEntryBits': 32, 'tableEntrySigned': False,
            'indexScale': 4, 'computedTargetRva': target, 'rangeComparison': 'unsigned',
            'savedReaderRegister': 'rdi', 'savedWrapperOutputRegister': 'rbx',
            'sameInitializedUInt16Local': True, 'callerPrefixOnly': True,
            'condition': 'warmed caller; helper returns AL true with the selected UInt16 tag; stable Reader/output/local aliases and Win64 ABI'}


def validate_null_cast_return(image: Any, proof: dict, *, fail: Callable) -> dict:
    expected = ['4053', '4883EC20', '488BD9', '4885C9', None, '33C0', '4883C420', '5B', 'C3']
    _profile(image, proof, expected, {4: ('74', True)}, {}, {}, (), (), {}, fail=fail)
    return {'completeNullCastReturn': True, 'inputRegister': 'rcx', 'returnBits': 64,
            'returnValue': 0, 'selectedCalls': 0, 'selectedMemoryWrites': 0,
            'classOrReaderDereferences': 0, 'condition': 'entry reference is null; ordinary Win64 ABI'}


def validate_new_child_union_route(image: Any, proof: dict, cast_usage: dict, child_usage: dict,
                                   calls: dict, *, fail: Callable) -> dict:
    expected = [None, '488B0B', None, '488BCF', '4885C0', None, None, None,
                '488903', '488BD0', None, '488BCB', None, '488B5C2430',
                '488B742440', '4883C420', '5F', 'C3']
    _profile(image, proof, expected, {5: ('0F85', False)},
             {2: 'cast', 7: 'child', 12: 'barrier'}, {0: '488B15', 6: '488B15'},
             (10,), (), calls, fail=fail)
    rows = proof['program']
    for n, usage in ((0, cast_usage), (6, child_usage)):
        if rows[n] != [usage['instructionRva'], usage['instructionHex']]:
            fail('union-new-child-owned-usage', 'same current exact usage load', rows[n])
    return {'completeNewChildRouteReturn': True, 'callerReaderRegister': 'rdi',
            'childReaderRegister': 'rcx', 'childContextRegister': 'rdx', 'childReturnRegister': 'rax',
            'wrapperOutputReferenceBits': 64, 'sameChildReturnStoredAndBarrierValue': True,
            'directReaderCursorWrites': 0, 'runtimeCallbackSelectionObserved': False,
            'condition': 'saved caller Reader/output live; entry wrapper null and complete null-cast return; child obeys closed typed ReadPackable contract and returns normally; barrier returns normally; stable aliases and Win64 ABI'}


def validate_packable_thunk(image: Any, proof: dict, usage: dict, target_rva: int, *, fail: Callable) -> dict:
    rows, windows = proof['program'], proof['codeWindows']
    if len(rows) != 2 or len(windows) != 1 or rows[0][0] != windows[0]['startRva']:
        fail('union-child-thunk-scope', 'actual closed-context load and one direct jump', proof)
    image.check_windows(windows, label='unionChildPackableThunk')
    image.check_instruction_windows(rows, label='unionChildPackableThunk')
    first = bytes.fromhex(rows[0][1])
    at, h = rows[1]
    raw = bytes.fromhex(h)
    if (rows[0] != [usage['instructionRva'], usage['instructionHex']] or len(first) != 7
            or first[:3] != b'\x48\x8b\x15' or at != rows[0][0] + 7
            or len(raw) != 5 or raw[0] != 0xe9 or _target(at, raw) != target_rva
            or at + len(raw) != windows[0]['endRva']):
        fail('union-child-thunk-context-and-target', 'same closed RDX context and actual shared packable entry', proof)
    return {'sameReaderRegister': 'rcx', 'closedContextRegister': 'rdx', 'sharedTargetRva': target_rva,
            'selectedCalls': 0, 'selectedMemoryWrites': 0, 'directReaderCursorWrites': 0,
            'fullThunkPhysicalExtentProved': False}
