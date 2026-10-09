"""Complete selected buffered union-marker/UInt16 output programs."""
from __future__ import annotations
from typing import Any, Callable
from scripts.game_data.memorypack.read_value_reference_sources import _profile
from scripts.game_data.memorypack.reference_conversion_sources import _target


def validate_union_header_programs(image: Any, programs: dict, offsets: dict, *, fail: Callable) -> dict:
    if (set(programs) != {'shortTag', 'extendedTag', 'highMarkerFalse'}
            or set(offsets) != {'currentPtr', 'bufferLength', 'advancedCount', 'consumed'}
            or any(type(n) is not int or not 0 <= n < 128 for n in offsets.values())
            or len(set(offsets.values())) != 4):
        fail('union-header-program-scope', 'three complete buffered paths and four distinct Reader fields', programs.keys())
    b, p, a, c = (offsets[k] for k in ('bufferLength', 'currentPtr', 'advancedCount', 'consumed'))
    prefix = ['48895C2408', '4889742410', '48897C2418', '4156', '4883EC20', None,
              '4C8BF2', '488BD9', None, f'837B{b:02X}01', None, f'488B43{p:02X}',
              '0FB630', f'8B7B{b:02X}', '83EF01', None, f'48FF43{p:02X}',
              f'FF43{a:02X}', f'FF43{c:02X}', f'897B{b:02X}', '4080FEFA', None]
    epilogue = ['488B5C2430', '488B742438', '488B7C2440', '4883C420', '415E', 'C3']
    base_branches = {8: ('0F84', False), 10: ('0F8C', False), 15: ('0F88', False)}
    short = prefix + ['66418936', 'B001'] + epilogue
    extended = prefix + [None, f'837B{b:02X}02', None, f'488B43{p:02X}', '0FB700',
        '66418906', f'8B7B{b:02X}', '83EF02', None, f'488343{p:02X}02',
        f'8343{a:02X}02', f'8343{c:02X}02', f'897B{b:02X}', None, 'B001'] + epilogue
    high = prefix + [None, '33C0', '66418906', None] + epilogue
    _profile(image, programs['shortTag'], short, base_branches | {21: ('73', False)},
             {}, {5: '803D'}, (), (), {}, fail=fail)
    _profile(image, programs['extendedTag'], extended,
             base_branches | {21: ('73', True), 22: ('75', False), 24: ('0F8C', False), 30: ('0F88', False)},
             {}, {5: '803D'}, (35,), (), {}, fail=fail)
    _profile(image, programs['highMarkerFalse'], high,
             base_branches | {21: ('73', True), 22: ('75', True)},
             {}, {5: '803D'}, (25,), (), {}, fail=fail)
    if any(programs[key]['program'][:22] != programs['shortTag']['program'][:22] for key in programs):
        fail('union-header-common-byte-path', 'same current complete one-byte read/cursor/unsigned comparison', programs)
    return {
        'completeSelectedReturns': True, 'savedReaderRegister': 'rbx', 'savedTagOutputRegister': 'r14',
        'outputBits': 16, 'shortMarkerRange': [0, 249], 'shortWireBytes': 1,
        'extendedMarker': 250, 'extendedWireBytes': 3, 'extendedTagBits': 16,
        'extendedByteOrder': 'little-endian', 'highMarkerFalseRange': [251, 255],
        'highMarkerWireBytes': 1, 'highMarkerOutputValue': 0,
        'trueResultBitsProved': 'AL only', 'falseResult': 'full EAX/RAX zero',
        'cursorFieldsPerRead': 4, 'selectedCalls': 0, 'frameBytesBelowEntry': 40,
        'condition': 'warmed helper state; valid buffered/counter bounds; disjoint stable Reader/buffer/UInt16-output/caller storage; Win64 ABI',
        'reservedMarkerCanonicalAdmission': False,
    }


def validate_union_header_caller_prefix(image: Any, proof: dict, helper_rva: int, *, fail: Callable) -> dict:
    """Authenticate a bounded caller prefix without claiming its eventual return."""
    expected = ['48895C2408', '4889742418', '57', '4883EC20', None, '498BD8', '488BFA', None,
                '33F6', '488D542438', '4533C0', '6689742438', '488BCF', None,
                '84C0', None, '0FB7742438']
    rows, windows = proof['program'], proof['codeWindows']
    if not windows or len(rows) != len(expected) or rows[0][0] != windows[0]['startRva']:
        fail('union-caller-prefix-size', 'seventeen instructions from the owned caller entry', rows)
    image.check_windows(windows, label='unionHeaderCallerPrefix')
    image.check_instruction_windows(rows, label='unionHeaderCallerPrefix')
    for n, ((at, h), wanted) in enumerate(zip(rows, expected, strict=True)):
        raw = bytes.fromhex(h)
        if not raw or not any(w['startRva'] <= at < at + len(raw) <= w['endRva'] for w in windows):
            fail('union-caller-prefix-owner', 'one complete instruction in an owned window', rows[n])
        decoded = image.mapper.decode_x64_subset(raw, image.pe.image_base + at, stop_offset=len(raw))
        if len(decoded) != 1 or 'db ' in decoded[0]['text'] or wanted is not None and h != wanted:
            fail('union-caller-prefix-transfer', {'position': n, 'bytes': wanted}, rows[n])
        if n == 4 and (len(raw) != 7 or raw[:2] != b'\x80\x3d' or raw[-1] != 0):
            fail('union-caller-initialized-guard', 'RIP byte compared with zero', rows[n])
        if n in (7, 15) and (len(raw) != 6 or raw[:2] != b'\x0f\x84'):
            fail('union-caller-selected-guard', 'untaken initialization/AL-false JE', rows[n])
        if n == 13 and (len(raw) != 5 or raw[0] != 0xe8 or _target(at, raw) != helper_rva):
            fail('union-caller-actual-tag-helper', helper_rva, rows[n])
        if n < len(rows) - 1 and rows[n + 1][0] != at + len(raw):
            fail('union-caller-prefix-successor', 'unchanged complete fallthrough prefix', rows[n:n + 2])
    return {'sameCallerReaderPassed': True, 'savedCallerReaderRegister': 'rdi',
            'savedWrapperOutputRegister': 'rbx', 'tagLocalFromEntryRsp': 16,
            'tagLocalZeroInitializedBits': 16, 'observedReturnPredicateBits': 'AL',
            'tagReloadBits': 16, 'condition': 'caller initialized; helper returns AL true normally',
            'callerPrefixOnly': True, 'completeUnionDispatchOrReturnProved': False}
