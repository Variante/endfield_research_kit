"""Prove a bounded, straight-line Boolean literal argument to a named call."""
from __future__ import annotations
import re


def check_boolean_constant(index, body, spec):
    from .body_claims import _named_direct_call, _REGISTER_ROOT
    if type(spec.get('value')) is not bool:
        return 'Boolean call argument requires a bool value'
    rows=body.all_rows
    for position,row in enumerate(rows):
        target=_named_direct_call(index,row,spec['call'])
        if target is None:continue
        matches=[]
        for named in index.names_by_pointer.get(target,()):
            if f"{named.get('type')}.{named.get('method')}"!=spec['call']:continue
            method=index.metadata.methods[named['methodIndex']]
            matches.extend(index.metadata.metadata_type_name(p.type_index) for p in index.metadata.parameters_for(method)
                if index.metadata.string(p.name_index)==spec['parameter'])
        if not matches or set(matches)!={'System.Boolean'}:continue
        kind,register=index.parameter_location(target,spec['call'],spec['parameter'])
        if kind!='register':continue
        current=_REGISTER_ROOT.get(str(register));expected=int(spec['value'])
        if current is None:continue
        following=row
        for previous in reversed(rows[max(0,position-20):position]):
            # Split fragments and branch boundaries never become one path.
            try:
                contiguous=int(previous['va'],16)+len(bytes.fromhex(previous['bytes']))==int(following['va'],16)
            except (KeyError,ValueError,TypeError):
                contiguous=False
            if not contiguous:break
            text=str(previous.get('text') or '')
            if re.match(r'(?:call|j\w*|ret|int3|db)\b',text):break
            # Only instructions with a single explicit destination (or none)
            # may be traversed. MUL/DIV, XCHG, string operations and similar
            # implicit/multiple writes cannot preserve this register proof.
            mnemonic=text.split(' ',1)[0]
            if mnemonic not in ('mov','movzx','movsx','movsxd','xor','lea','add','sub','and','or',
                                'inc','dec','neg','not','shl','shr','sar','cmp','test','nop'):
                break
            destination=re.match(r'\w+ (\w+)(?:,|$)',text)
            if destination and _REGISTER_ROOT.get(destination.group(1))==current:
                alias=destination.group(1)
                if alias in ('ah','bh','ch','dh'):break
                literal=re.fullmatch(r'mov \w+, (0x[0-9a-f]+|\d+)',text)
                zero=re.fullmatch(r'xor (\w+), \1',text)
                move=re.fullmatch(r'mov \w+, (\w+)',text)
                if literal or zero:
                    value=int(literal.group(1),0) if literal else 0
                    if value==expected:return None
                    break
                if move and move.group(1) not in ('ah','bh','ch','dh') and move.group(1) in _REGISTER_ROOT:
                    current=_REGISTER_ROOT[move.group(1)]
                else:break
            following=previous
    return f"{spec['call']}.{spec['parameter']} has no contiguous Boolean literal {spec['value']} argument"
