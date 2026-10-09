"""Owned byte-to-AL return proof after a named false Boolean guard."""
import re
from scripts.game_data.il2cpp.body_claims import Body,ClaimError
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.closed_data_fields import check_closed_data_field

def _complete_byte_return_load(row, data_register):
    match = re.fullmatch(r"(mov al|movzx eax), \[(\w+)\+0x([0-9a-f]+)\]", row.get('text') or '')
    if not match or match[2] != data_register:
        return False
    raw = bytes.fromhex(row.get('bytes') or '')
    rex = raw[0] if raw and 0x40 <= raw[0] <= 0x4f else 0
    if rex:
        raw = raw[1:]
    opcode = b'\x8a' if match[1] == 'mov al' else b'\x0f\xb6'
    if not raw.startswith(opcode) or rex & 0x0c or len(raw) <= len(opcode):
        return False
    modrm = raw[len(opcode)]
    mode = modrm >> 6
    if mode not in (1, 2) or modrm & 7 == 4 or (modrm >> 3) & 7:
        return False
    displacement_width = 1 if mode == 1 else 4
    if len(raw) != len(opcode) + 1 + displacement_width:
        return False
    registers = ('rax', 'rcx', 'rdx', 'rbx', 'rsp', 'rbp', 'rsi', 'rdi', *(f'r{n}' for n in range(8, 16)))
    return (registers[(modrm & 7) + (8 if rex & 1 else 0)] == data_register
        and int.from_bytes(raw[len(opcode)+1:], 'little', signed=True) == int(match[3], 16))

def check_byte_return(index,body,spec):
    label='owned-byte-return-after-false-call'
    def selected(pointer,symbol,context):
        declarations=[r for r in index.names_by_pointer.get(pointer,[])
                      if r.get('type')+'.'+r.get('method')==symbol]
        if len(declarations)!=1 or type(declarations[0].get('methodIndex')) is not int:
            raise ValueError('unique selected method declaration is missing')
        method=index.metadata.methods[declarations[0]['methodIndex']]
        owner=index.metadata.types[method.declaring_type]
        if (index.metadata.type_full_name(owner)+'.'+index.metadata.string(method.name_index)!=symbol
                or method.generic_container_index>=0 or owner.generic_container_index>=0):
            raise ValueError('selected method/owner identity or nongeneric ABI is missing')
        raw=index.pe.bytes_at_va(context.type_pointer(method.return_type),16)
        if len(raw)!=16 or raw[10]!=2 or raw[11]&0x7f:
            raise ValueError('undecorated Boolean return is missing')
        return method
    try:
        if not isinstance(spec,dict) or set(spec) not in (
            {'call','witnessType','dataField','valueField'},
            {'call','witnessType','dataField','valueField','concreteInstanceSuffix'}):
            return label+': explicit named guard and owned field profile required'
        context=NativeReferenceContext(index.image,index=index)
        caller=selected(body.pointer,body.symbol,context)
        if caller.flags&0x10 or list(index.metadata.parameters_for(caller)):
            return label+': no-argument Boolean instance caller required'
        if context.field(spec['valueField'])[1]!='bool':
            return label+': named bool Data member required'
        rows=body.rows
        addresses=[int(r['va'],16) for r in rows]
        if (len(set(addresses))!=len(rows) or addresses!=sorted(addresses)
                or not addresses or addresses[0]!=body.pointer):
            return label+': selected body instruction inventory differs'
        if ([(r['text'],bytes.fromhex(r['bytes'])) for r in rows[:3]] not in [
                [('push rbx',b'\x53'),('sub rsp, 0x20',bytes.fromhex('4883ec20')),('mov rbx, rcx',bytes.fromhex('488bd9'))],
                [('push rbx',bytes.fromhex('4053')),('sub rsp, 0x20',bytes.fromhex('4883ec20')),('mov rbx, rcx',bytes.fromhex('488bd9'))]]):
            return label+': selected incoming-this and complete stack frame profile differ'
        candidates=[]
        for at,row in enumerate(rows):
            match=re.fullmatch(r'call 0x([0-9a-f]+)',row.get('text') or '')
            raw=bytes.fromhex(row.get('bytes') or '')
            if not match or len(raw)!=5 or raw[0]!=0xe8:continue
            target=int(match[1],16)
            if (addresses[at]+5+int.from_bytes(raw[1:],'little',signed=True)==target
                    and spec['call'] in index.names_of(target)):
                selected(target,spec['call'],context);candidates.append(at)
        if len(candidates)!=1:return label+': unique complete named Boolean guard call required'
        at=candidates[0];tail=rows[at+1:]
        if len(tail)<9 or tail[0]['text']!='test al, al' or bytes.fromhex(tail[0]['bytes'])!=b'\x84\xc0':
            return label+': guard AL test is missing'
        def branch(row,short,near):
            raw=bytes.fromhex(row['bytes']);va=int(row['va'],16)
            if len(raw)==2 and raw[0]==short:relative=raw[1:]
            elif len(raw)==6 and raw[:2]==bytes([0x0f,near]):relative=raw[2:]
            else:raise ValueError('complete branch direction differs')
            target=va+len(raw)+int.from_bytes(relative,'little',signed=True)
            if row['text'] not in {f'jcc 0x{target:x}',f'{"jne" if short==0x75 else "je"} 0x{target:x}'}:
                raise ValueError('branch bytes and text disagree')
            return target
        guard_target=branch(tail[1],0x75,0x85)
        data_load=re.fullmatch(r'mov (\w+), \[(\w+)\+0x([0-9a-f]+)\]',tail[2]['text'])
        if not data_load:return label+': direct Data load after guard is missing'
        data_register=data_load[1]
        pointer_raw=bytes.fromhex(tail[2]['bytes'])
        if len(pointer_raw)<4 or not 0x48<=pointer_raw[0]<=0x4f or pointer_raw[1]!=0x8b:
            return label+': complete Data pointer load is missing'
        pointer_rex,pointer_modrm=pointer_raw[0],pointer_raw[2]
        pointer_mode=pointer_modrm>>6
        registers=('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi',*(f'r{n}' for n in range(8,16)))
        if (pointer_mode not in (1,2) or pointer_modrm&7==4
                or len(pointer_raw)!=(4 if pointer_mode==1 else 7)
                or registers[((pointer_modrm>>3)&7)+(8 if pointer_rex&4 else 0)]!=data_register
                or registers[(pointer_modrm&7)+(8 if pointer_rex&1 else 0)]!=data_load[2]
                or int.from_bytes(pointer_raw[3:],'little',signed=True)!=int(data_load[3],16)):
            return label+': Data pointer bytes and operands disagree'
        if tail[3]['text']!=f'test {data_register}, {data_register}':
            return label+': Data non-null test is missing'
        # Require the complete QWORD self TEST rather than a partial-register
        # expression whose text happens to name the same root.
        test_raw=bytes.fromhex(tail[3]['bytes'])
        if len(test_raw)!=3 or not test_raw[0]&8 or test_raw[1]!=0x85 or test_raw[2]>>6!=3:
            return label+': complete Data pointer test is missing'
        rex=test_raw[0];modrm=test_raw[2]
        if (not 0x48<=rex<=0x4f or registers[(modrm&7)+(8 if rex&1 else 0)]!=data_register
                or registers[((modrm>>3)&7)+(8 if rex&4 else 0)]!=data_register):
            return label+': Data pointer TEST operands differ'
        null_target=branch(tail[4],0x74,0x84)
        if not _complete_byte_return_load(tail[5], data_register):
            return label+': owned byte must directly supply AL'
        field_spec={k:v for k,v in spec.items() if k!='call'}
        load_index=at+6
        prefix=Body(body.symbol,body.pointer,body.size,body.token,rows[:load_index])
        through=Body(body.symbol,body.pointer,body.size,body.token,rows[:load_index+1])
        if check_closed_data_field(index,prefix,field_spec,forward=False) is None:
            return label+': an earlier read would make the selected return read ambiguous'
        ownership=check_closed_data_field(index,through,field_spec,forward=False)
        if ownership is not None:
            return label+': selected AL source lacks incoming-instance field ownership: '+str(ownership)
        # The return block is deliberately narrow: exact ADD RSP, POP RBX,
        # RET. Any call, result overwrite or alternate epilogue stays open.
        epilogue=tail[6:9]
        if [(r['text'],bytes.fromhex(r['bytes'])) for r in epilogue]!=[
            ('add rsp, 0x20',bytes.fromhex('4883c420')),('pop rbx',b'\x5b'),('ret',b'\xc3')]:
            return label+': complete unchanged AL return epilogue required'
        block=[rows[at],*tail[:9]]
        if any(int(a['va'],16)+len(bytes.fromhex(a['bytes']))!=int(b['va'],16) for a,b in zip(block,block[1:])):
            return label+': return program is not contiguous'
        # BodyIndex admits fragment rows only through this method's owned
        # native unwind fragments. A cold IFix path may be outside main rows;
        # this conditional proof still requires an owned instruction boundary.
        owned_addresses=[int(r['va'],16) for r in body.all_rows]
        if len(set(owned_addresses))!=len(owned_addresses):
            return label+': owned instruction inventory contains duplicates'
        start=int(tail[2]['va'],16);end=int(epilogue[-1]['va'],16)+1
        if any(target not in owned_addresses or start<=target<end for target in (guard_target,null_target)):
            return label+': guard/null alternative must leave the checked return block'
        return None
    except (ValueError,KeyError,IndexError,TypeError,ClaimError) as exc:
        return label+': selected proof failed: '+str(exc)
