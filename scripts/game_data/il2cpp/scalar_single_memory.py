"""Selected legacy MOVSS memory transfers; upper vector state is unclaimed."""
from scripts.game_data.il2cpp.integer_addressing import _address, _prefix, _required
from scripts.game_data.il2cpp.integer_tag_dispatch import _row
from scripts.game_data.il2cpp.memory_moves import _finish_address


def decode_scalar_single_memory_move(data, offset, start_va):
    if not 0 <= offset < len(data) or data[offset] != 0xf3:
        return None
    at, rex = _prefix(data, offset+1)
    opcode = data[at:at+2]
    if opcode not in (b'\x0f\x10', b'\x0f\x11'):
        return None
    at += 2
    modrm = _required(data, at, 1, offset, 'scalar-single-memory')[0]
    at += 1
    if modrm >> 6 == 3:
        return None
    number = ((modrm >> 3) & 7) | ((rex & 4) << 1)
    address, at = _address(data, at, modrm, rex, offset, 'scalar-single-memory')
    term = _finish_address(address, at, start_va)
    register, load = f'xmm{number}', opcode[-1] == 0x10
    operands = f'{register}, [{term}]' if load else f'[{term}], {register}'
    return _row(data, offset, at, start_va, 'movss ' + operands,
        memoryOperation={'direction': 'load' if load else 'store', 'register': register, 'backingRegister': f'vector{number}',
            'registerBits': 128, 'registerBitOffset': 0, 'memoryBytes': 4, 'address': address,
            'valueExtension': None, 'upperRegisterEffect': 'not asserted by this low-DWORD reader',
            'requiredAlignmentBytes': 1, 'nonTemporalHint': False, 'rexWSelectsTransferWidth': False},
        scalarSingleMemoryTransfer={'lowDwordBitsTransferred': 32, 'upperVectorLaneEffectsProved': False,
            'numericConversionPerformed': False, 'wholeFieldOrFunctionMeaningProved': False})
