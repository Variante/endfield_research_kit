"""Complete selected union false return and its actual disabled-barrier jump."""
from __future__ import annotations
from typing import Any, Callable

from scripts.game_data.memorypack.read_value_reference_sources import _profile
from scripts.game_data.memorypack.reference_conversion_sources import _target
from scripts.game_data.memorypack.buffered_reference_wrappers import validate_fast_reference_barrier


def validate_union_false_return(image: Any, proof: dict, helper_rva: int,
                                trampoline: dict, barrier: dict, *, fail: Callable) -> dict:
    fast = validate_fast_reference_barrier(image, barrier, fail=fail)
    rows = trampoline['program']
    windows = trampoline['codeWindows']
    if len(rows) != 1 or len(windows) != 1 or rows[0][0] != windows[0]['startRva']:
        fail('union-false-barrier-trampoline', 'actual one-instruction entry jump', trampoline)
    at, h = rows[0]
    raw = bytes.fromhex(h)
    image.check_windows(windows, label='unionFalseBarrierTrampoline')
    image.check_instruction_windows(rows, label='unionFalseBarrierTrampoline')
    if (len(raw) != 5 or raw[0] != 0xe9 or at + len(raw) != windows[0]['endRva']
            or _target(at, raw) != fast['entryRva']):
        fail('union-false-barrier-actual-jump', fast['entryRva'], rows[0])
    expected = ['48895C2408', '4889742418', '57', '4883EC20', None, '498BD8', '488BFA', None,
                '33F6', '488D542438', '4533C0', '6689742438', '488BCF', None,
                '84C0', None, '488933', '33D2', None, '488BCB', None,
                '488B5C2430', '488B742440', '4883C420', '5F', 'C3']
    _profile(image, proof, expected, {7: ('0F84', False), 15: ('0F84', True)},
             {13: 'tagHelper', 20: 'barrier'}, {4: '803D'}, (18,), (),
             {'tagHelper': helper_rva, 'barrier': at}, fail=fail)
    return {'completeUnionFalseReturnProved': True, 'sameCallerReaderPassed': True,
            'wrapperOutputClearBits': 64, 'zeroSourceRegister': 'rsi preserved by tag helper',
            'tagHelperPredicateBits': 'AL', 'directReaderWritesOutsideTagHelper': 0,
            'actualBarrierEntryJumpMatched': True, 'disabledBarrierFlagRva': fast['disabledFlagRva'],
            'selectedBarrierMemoryWrites': 0, 'selectedBarrierCalls': 0,
            'callerFrameBytesBelowEntry': 40, 'trampolineFullPhysicalExtentProved': False,
            'runtimeDisabledStateObserved': False, 'reservedMarkerCanonicalAdmission': False,
            'condition': 'initialized caller; tag helper returns AL false and preserves nonvolatile RSI/ABI; stable disjoint Reader/output/caller storage; disabled barrier state'}
