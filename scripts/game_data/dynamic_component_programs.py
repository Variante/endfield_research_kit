"""Small native programs for generated DynamicStreaming stored layouts.

These checks name stored reads and reverse builder writes. They grant no
runtime grid/entity, loading, visibility or condition-evaluation claims.
"""
from __future__ import annotations

import re
import struct

from scripts.game_data.il2cpp.integer_addressing import _address, _prefix, _required


SCALARS = {
    'System.Boolean': ('<B', 1), 'System.Int32': ('<i', 4),
    'System.UInt32': ('<I', 4), 'System.Single': ('<f', 4),
    'System.Int64': ('<q', 8), 'System.UInt64': ('<Q', 8),
}


def need(check, condition, detail=''):
    if not condition:
        raise ValueError('dynamicComponents.native.' + check + ': ' + str(detail)[:1000])


def instruction_offset(raw: bytes, kind: str) -> int:
    """Decode the actual displacement; a recorded layout offset is no input."""
    at, rex = _prefix(raw, 0)
    need('32-bit-position-arithmetic', not rex & 8)
    opcode = raw[at]; at += 1
    if kind == 'zero-position':
        need('zero-position-instruction', opcode == 0x8b and at + 1 == len(raw)
             and raw[at] >> 6 == 3)
        return 0
    modrm = _required(raw, at, 1, 0, 'dynamic-component-position')[0]; at += 1
    if kind == 'position-add':
        need('position-add-opcode', opcode in (0x81, 0x83) and modrm >> 6 == 3 and (modrm >> 3) & 7 == 0)
        size = 1 if opcode == 0x83 else 4
        need('position-add-complete', len(raw) == at + size)
        value = int.from_bytes(raw[at:], 'little', signed=True)
        need('positive-inline-displacement', value >= 0)
        return value
    need('position-lea-opcode', kind == 'position-lea' and opcode == 0x8d and modrm >> 6 != 3)
    address, end = _address(raw, at, modrm, rex, 0, 'dynamic-component-position')
    need('position-lea-complete', end == len(raw) and not address['ripRelative']
         and address['index'] is None and address['base'] is not None)
    return int(address['displacement'])


def constant_program(rows, targets, *, width, alignment, expected_writes):
    """Replay one straight-line generated struct Prep/Put/Pad sequence.

    Only constants survive, and ordinary calls clobber volatile registers.
    Every byte is charged to a typed Put or an explicit zero Pad. The caller
    supplies freshly decoded instructions from authenticated owned windows.
    """
    constants = {}; calls = []; cursor = width; began = False
    aliases = {'eax':'rax', 'ecx':'rcx', 'edx':'rdx', 'ebx':'rbx', 'esp':'rsp',
               'ebp':'rbp', 'esi':'rsi', 'edi':'rdi'}
    aliases.update({f'r{i}d': f'r{i}' for i in range(8, 16)})
    for parent,word,low in zip(('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi'),
                               ('ax','cx','dx','bx','sp','bp','si','di'),
                               ('al','cl','dl','bl','spl','bpl','sil','dil')):
        aliases[word]=parent;aliases[low]=parent
    aliases.update({name:'r'+name[1:-1]for n in range(8,16)for name in(f'r{n}w',f'r{n}b')})
    aliases.update(dict(ah='rax',ch='rcx',dh='rdx',bh='rbx'))
    def reg(name): return aliases.get(name, name)
    def value(text):
        if reg(text) in constants: return constants[reg(text)]
        try: return int(text, 0)
        except ValueError: return None
    def assign(name,v):
        constants.pop(reg(name),None)
        narrow=name in {'al','cl','dl','bl','spl','bpl','sil','dil','ah','ch','dh','bh','ax','cx','dx','bx','sp','bp','si','di'}or name.startswith('r')and name[-1:]in('b','w')
        if v is not None and not narrow:constants[reg(name)]=v&0xffffffff if name.startswith('e')or name.endswith('d')else v
    for row in rows:
        text = row['text']; head, _, operands = text.partition(' ')
        if head == 'call':
            try: target = int(operands, 16)
            except ValueError: target = None
            role = targets.get(target)
            if not began:
                need('first-call-is-struct-Prep', role == ('prep', None), text)
                need('own-struct-width-and-alignment', (value('edx'), value('r8d')) == (alignment, width), constants)
                began = True
            if role is not None and role[0] == 'prep':
                a, n = value('edx'), value('r8d')
                need('nested-Prep-arguments', type(a) is int and a > 0 and a & (a-1) == 0
                     and type(n) is int and 0 < n <= width and (cursor - n) % a == 0, (a,n,cursor))
            elif role is not None and role[0] in ('put', 'pad'):
                if role[0] == 'pad':
                    amount = value('edx')
                    need('constant-positive-Pad', type(amount) is int and 0 < amount <= width, constants)
                    wire_type = 'padding'
                else:
                    wire_type = role[1]; amount = SCALARS[wire_type][1]
                need('builder-no-underflow', 0 <= cursor - amount < cursor)
                calls.append((cursor-amount, cursor, wire_type)); cursor -= amount
                if cursor == 0:
                    need('all-and-only-typed-writes-and-zero-Pad', calls == expected_writes, (calls,expected_writes))
                    return dict(width=width, alignment=alignment, writes=calls, wholeStructBytesAccounted=True,
                                endVa=int(row['va'],16)+len(bytes.fromhex(row['bytes'])))
            else:
                need('only-Prep-Put-Pad-before-layout-closed', False, text)
            for name in list(constants):
                if reg(name) in {'rax','rcx','rdx','r8','r9','r10','r11'}: constants.pop(name)
            continue
        need('straight-line-layout-program', head not in ('ret','int3','jmp') and not head.startswith('j'), text)
        parts = operands.split(', ', 1)
        if head == 'xor' and len(parts) == 2 and parts[0] == parts[1]:
            assign(parts[0],0)
        elif head == 'mov' and len(parts) == 2 and '[' not in parts[0]:
            v = value(parts[1]); assign(parts[0],v)
        elif head == 'lea' and len(parts) == 2:
            match = re.fullmatch(r'\[([a-z0-9]+)([+-]0x[0-9a-f]+)?\]', parts[1])
            v=None
            if match:
                base_name = match[1]
                v = value(base_name)
                if v is not None:v += int(match[2] or '0',0)
            assign(parts[0],v)
        elif (row.get('write') or {}).get('register'):
            assign(row['write']['register'],None)
        elif head in ('add','sub','and','or','inc','dec','pop','movzx','movsx','movsxd')and'['not in parts[0]:
            assign(parts[0],None)
    need('complete-native-layout-write-program', False, cursor)


def leaf_fields(record, records, *, base=0):
    for field in record['fields']:
        offset = base + field['offset']
        if field['type'] in SCALARS:
            yield offset, offset + SCALARS[field['type']][1], field['type']
        else:
            yield from leaf_fields(records[field['type']], records, base=offset)


def expected_writes(record, records):
    """All nested fields plus explicit gaps, in the native reverse write order."""
    spans = list(leaf_fields(record, records)); result = []; cursor = 0
    for start, end, kind in spans:
        need('nonoverlapping-named-field-layout', cursor <= start < end <= record['width'], (record['type'],start,end))
        if start > cursor: result.append((cursor,start,'padding'))
        result.append((start,end,kind)); cursor=end
    if cursor < record['width']: result.append((cursor,record['width'],'padding'))
    return list(reversed(result))
