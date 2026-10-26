"""Bounded incoming-reference spills on explicitly selected false-call paths.

Explore actual branch edges, preserving entry-RSP coordinates at joins. This
does not select a live IFix state. Normal Win64 callees and non-forged heap
references are conditions; escaped stack addresses and unknown code refuse.
"""
from __future__ import annotations
import re
from collections import deque
from .integer_source_operands import decode_source_operand_integer_instructions
from .memory_moves import decode_memory_move
from .integer_addressing import _address

VOLATILE = {'rax','rcx','rdx','r8','r9','r10','r11'}
GP = {'rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi',*(f'r{i}' for i in range(8,16))}


def is_reference_parameter(index,pointer,symbol,parameter):
    from .reference_layouts import NativeReferenceContext
    context=NativeReferenceContext(index.image,index=index);found=[]
    for named in index.names_by_pointer.get(pointer,()):
        if f"{named.get('type')}.{named.get('method')}"!=symbol:continue
        method=index.metadata.methods[named['methodIndex']]
        for p in index.metadata.parameters_for(method):
            if index.metadata.string(p.name_index)!=parameter:continue
            name=context.type_name(p.type_index);definition=name.split('<',1)[0]
            found.append(definition in index.types and not context.is_value_type(name))
    return bool(found) and all(found)


def decode_stack_flow(mapper, raw, start):
    class Adapter:
        def decode_one_x64(self,data,offset,at):
            move=decode_memory_move(data,offset,at)
            if move is not None:return move
            pos=offset;rex=0
            if 0x40<=data[pos]<=0x4f:rex=data[pos];pos+=1
            if data[pos:pos+2] in (b'\x0f\x10',b'\x0f\x11',b'\x0f\x28',b'\x0f\x29') and pos+2<len(data):
                opcode=data[pos+1];modrm=data[pos+2]
                if modrm>>6!=3:
                    address,end=_address(data,pos+3,modrm,rex,offset,'stack-vector')
                    # Supply exact operands to the audit; the legacy text is display only.
                    legacy,_=mapper.decode_one_x64(data,offset,at)
                    return {**legacy,'offset':offset,'va':hex(at+offset),'bytes':data[offset:end].hex(' '),
                        'memoryOperation':{'address':address,'memoryBytes':16,'registerBits':128,
                            'direction':'store' if opcode in (0x11,0x29) else 'load',
                            'register':f'xmm{((modrm>>3)&7)|((rex&4)<<1)}'}},end
            return mapper.decode_one_x64(data,offset,at)
    return decode_source_operand_integer_instructions(Adapter(),raw,start)


def _edge(row):
    raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    if len(raw)==2 and (raw[0]==0xeb or 0x70<=raw[0]<=0x7f):
        return at+2+int.from_bytes(raw[1:],'little',signed=True),raw[0]!=0xeb
    if len(raw)==5 and raw[0]==0xe9:
        return at+5+int.from_bytes(raw[1:],'little',signed=True),False
    if len(raw)==6 and raw[0]==0x0f and 0x80<=raw[1]<=0x8f:
        return at+6+int.from_bytes(raw[2:],'little',signed=True),True
    return None


def prove_spilled_argument(index,body,spec):
    from .body_claims import _REGISTER_ROOT,_writes_register,_named_direct_call
    label='stack-argument'
    def fail(reason):raise ValueError(f'{label}.{reason}')
    kind,source=index.parameter_location(body.pointer,body.symbol,spec['fromParameter'])
    if kind!='register' or source not in GP:fail('incoming-reference-register')
    if not is_reference_parameter(index,body.pointer,body.symbol,spec['fromParameter']):
        fail('incoming-reference-type')
    raw=index.pe.bytes_at_va(body.pointer,body.size)
    rows=decode_stack_flow(index.mapper,raw,body.pointer)
    by_va={int(r['va'],16):n for n,r in enumerate(rows)}
    if b''.join(bytes.fromhex(r['bytes']) for r in rows)!=raw:fail('instruction-coverage')
    guards=set(spec['falseCalls'])
    if not guards:fail('explicit-false-call-selection')
    selected={}
    last_call=max((n for n,r in enumerate(rows) if _named_direct_call(index,r,spec['call']) is not None),default=-1)
    for n,r in enumerate(rows[:last_call]):
        if any(_named_direct_call(index,r,name) is not None for name in guards):
            test_at=n+1
            while test_at<min(len(rows)-1,n+12) and rows[test_at]['text'].startswith(('mov ','lea ')):
                if _writes_register(rows[test_at],'rax'):fail('false-call-return-clobber')
                test_at+=1
            test,branch=rows[test_at:test_at+2];b=bytes.fromhex(branch['bytes'])
            if bytes.fromhex(test['bytes'])!=bytes.fromhex('84 c0') or not (
                    len(b)==2 and b[0]==0x75 or len(b)==6 and b[:2]==b'\x0f\x85'):
                fail(f'false-call-guard:{r["offset"]}')
            selected[test_at+1]=n
    candidates=[]
    for n,r in enumerate(rows):
        target=_named_direct_call(index,r,spec['call'])
        if target is None:continue
        k,dest=index.parameter_location(target,spec['call'],spec['toParameter'])
        if k=='register' and dest in GP and is_reference_parameter(index,target,spec['call'],spec['toParameter']):
            candidates.append((n,dest))
    failures=[]
    for stop,destination in candidates:
        try:
            queue=deque([(0,0,((source,('argument',0)),),())]);seen=set();hits=[];spills=set();used_guards=set()
            while queue:
                n,delta,regs_tuple,slots_tuple=queue.popleft()
                state=(n,delta,regs_tuple,slots_tuple)
                if state in seen:continue
                seen.add(state)
                if len(seen)>20000:fail('state-limit')
                if n>stop:continue
                regs=dict(regs_tuple);slots=dict(slots_tuple);r=rows[n];text=r['text'];b=bytes.fromhex(r['bytes'])
                if n==stop:
                    value=regs.get(destination)
                    if not value or value[0]!='spilled' or slots.get(value[1])!=('argument',0):
                        fail(f'callee-argument:{r["offset"]}')
                    if not slots:fail('no-retained-spill')
                    hits.append(delta);continue
                if text.startswith('db ') or text in ('db','int3') or text.startswith('jmp ') and _edge(r) is None:
                    fail(f'unknown-or-indirect-control:{r["offset"]}:{text}')
                if text.startswith('ret'):continue
                if _writes_register(r,'rsp') and not re.fullmatch(r'(sub|add) rsp, 0x[0-9a-f]+',text):
                    fail('unknown-rsp-write')
                edge=_edge(r)
                if edge:
                    target,conditional=edge
                    if n in selected:
                        used_guards.add(selected[n]);nexts=[n+1]
                    else:
                        nexts=[n+1] if conditional else []
                        if target in by_va:nexts.append(by_va[target])
                        elif body.pointer<=target<body.pointer+body.size:fail('branch-interior')
                    for nxt in nexts:
                        queue.append((nxt,delta,tuple(sorted(regs.items())),tuple(sorted(slots.items()))))
                    continue
                # Saves and loads are decoded with exact memory widths and SIB bases.
                operation=r.get('memoryOperation')
                if operation:
                    address=operation['address'];base=address['base'];pointer=regs.get(base)
                    if regs.get(address['index'],('',))[0]=='stack':fail('stack-address-index')
                    stack_offset=None
                    if base=='rsp':stack_offset=address['displacement']-delta
                    elif pointer and pointer[0]=='stack':stack_offset=pointer[1]+address['displacement']
                    if stack_offset is not None:
                        if address['index'] is not None:fail('indexed-stack-memory')
                        width=operation['memoryBytes'];register=operation['register'];root=_REGISTER_ROOT.get(register,register)
                        if operation['direction']=='store':
                            for slot in list(slots):
                                if stack_offset<slot+8 and slot<stack_offset+width:slots.pop(slot)
                            value=regs.get(register)
                            if value==('argument',0) and width==8 and operation['registerBits']==64:
                                slots[stack_offset]=value;spills.add(stack_offset)
                        else:
                            regs.pop(root,None)
                            if width==8 and operation['registerBits']==64 and stack_offset in slots:
                                regs[register]=('spilled',stack_offset)
                    elif operation['direction']=='store':
                        if regs.get(operation['register'],('',))[0]=='stack':fail('stack-address-store-escape')
                    else:regs.pop(_REGISTER_ROOT.get(operation['register'],operation['register']),None)
                elif match:=re.fullmatch(r'mov (\w+), (\w+)',text):
                    dest,src=match.groups();root=_REGISTER_ROOT.get(dest)
                    if root:
                        value=(('stack',-delta) if src=='rsp' else regs.get(src)) if dest in GP and src in GP else None
                        regs.pop(root,None)
                        if value is not None:regs[root]=value
                elif match:=re.fullmatch(r'lea (\w+), \[rsp(?:\+0x([0-9a-f]+))?\]',text):
                    regs[match[1]]=('stack',int(match[2] or '0',16)-delta)
                elif text.startswith('push '):
                    if text[5:] not in GP:fail('unsupported-push')
                    delta+=8
                    # A push is also a QWORD write in entry coordinates.
                    for slot in list(slots):
                        if -delta<slot+8 and slot<8-delta:slots.pop(slot)
                elif text.startswith('pop '):
                    if text[4:] not in GP:fail('unsupported-pop')
                    regs.pop(text[4:],None);delta-=8
                elif match:=re.fullmatch(r'(sub|add) rsp, (0x[0-9a-f]+)',text):
                    delta+=(1 if match[1]=='sub' else -1)*int(match[2],16)
                else:
                    stack_bases=['rsp',*(reg for reg,value in regs.items() if value[0]=='stack')]
                    if any(re.search(r'\[[^\]]*\b'+re.escape(reg)+r'\b',text) for reg in stack_bases):
                        fail(f'unhandled-stack-access:{r["offset"]}:{text}')
                    if _writes_register(r,'rsp'):fail('unknown-rsp-write')
                    for register in list(regs):
                        if _writes_register(r,register):regs.pop(register)
                if text.startswith('call '):
                    if any(value[0]=='stack' for reg,value in regs.items() if reg in VOLATILE):
                        fail(f'stack-address-call-escape:{r["offset"]}')
                    for slot in list(slots):
                        if slot<32-delta and -delta<slot+8:slots.pop(slot)
                    for register in VOLATILE:regs.pop(register,None)
                queue.append((n+1,delta,tuple(sorted(regs.items())),tuple(sorted(slots.items()))))
            if not hits or not spills or not used_guards:fail('no-selected-spilled-call-path')
            return {'callOffset':rows[stop]['offset'],'entryRelativeSpillOffsets':sorted(spills),
                'callStackDeltas':sorted(set(hits)),'falseGuardCallOffsets':sorted(rows[n]['offset'] for n in used_guards),
                'visitedStates':len(seen),'evidenceBoundary':'conditional',
                'condition':'Selected named false calls, normal Win64 callees, valid non-forged heap references; first arrival at this call on paths staying within its method prefix. Paths leaving the prefix and later re-entering are not claimed.'}
        except ValueError as exc:failures.append(str(exc))
    fail('no-call-witness:'+str(failures[:4]))


def check_spilled_argument(index,body,spec):
    try:prove_spilled_argument(index,body,spec)
    except (ValueError,KeyError,IndexError) as exc:return str(exc)
    return None
