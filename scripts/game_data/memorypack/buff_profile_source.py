"""Strict source programs shared by named, method-scoped Buff role proofs.

These helpers inspect current complete unwind families. They do not attribute
historical disjoint windows or select a live formatter.
"""
from __future__ import annotations

import re

from scripts.game_data.buff_frontiers_regenerate import _method_row
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import buff_ec_profiles_native as ec
from scripts.game_data.memorypack.pooled_inline_sources import _Path
from scripts.game_data.skill_timeline_routes_regenerate import check_read_setter_transfers

LABEL = 'buffProfileSource'


def need(check, condition, detail=None):
    if not condition:
        raise ValueError(f'{LABEL}.{check}:{str(detail)[:700]}')


def object_header_program(rows, entry, offsets):
    """Prove the actual callee's buffered byte/output/FF Boolean program."""
    g = _Path(rows)
    g.at = entry
    g.take('mov [rsp+0x8], rbx', 'mov [rsp+0x10], rsi', 'push rdi', 'sub rsp, 0x20',
           f"cmp dword [rcx+{offsets['bufferLength']:#x}], 0x1", 'mov rdi, rdx', 'mov rbx, rcx')
    g.branch(12, False)
    g.take(f"mov rax, [rbx+{offsets['currentPtr']:#x}]", 'movzx ecx, byte [rax]',
           'mov [rdi], cl', f"mov esi, [rbx+{offsets['bufferLength']:#x}]", 'sub esi, 0x1')
    g.branch(8, False)
    g.take(f"inc qword [rbx+{offsets['currentPtr']:#x}]",
           f"inc dword [rbx+{offsets['advancedCount']:#x}]",
           f"inc dword [rbx+{offsets['consumed']:#x}]",
           f"mov [rbx+{offsets['bufferLength']:#x}], esi", 'cmp byte [rdi], 0xff',
           'mov rbx, [rsp+0x30]', 'mov rsi, [rsp+0x38]', 'setne al',
           'add rsp, 0x20', 'pop rdi', 'ret')
    return g.seen


def caller_header(image, rows, count_row, reader, offsets, barrier):
    """Bind a stack header result, actual helper, false clear and return frame."""
    base = image.pe.image_base
    by_at = {ec.va(r): r for r in rows}
    def is_header(pair):
        index,row=pair
        argument=ec.last_write(rows,index,'rdx')
        return row['text'].startswith('call 0x') and ec.va(row)<ec.va(count_row) and index>=2 and \
            rows[index-1]['text']==f'mov rcx, {reader}' and argument is not None and \
            re.fullmatch(r'lea rdx, \[rsp\+0x[0-9a-f]+\]',argument['text'])
    header = ec.one(list(enumerate(rows)),is_header,'objectHeader.call')
    index, call = header
    output = ec.last_write(rows,index,'rdx')['text'].removeprefix('lea rdx, ')
    displacement=int(output.removeprefix('[rsp+').removesuffix(']'),16)
    need('objectHeader.disjoint-stack-byte',displacement in (0x30,0x38),output)
    need('objectHeader.output-zero', any(r['text'] == f'mov byte {output}, 0x0' for r in rows[:index]))
    need('objectHeader.test', rows[index+1]['text'] == 'test al, al')
    false = control_transfer(rows[index+2])
    need('objectHeader.false-branch', false['kind'] == 'conditional' and false['conditionCode'] == 4)
    loaded = ec.one(rows, lambda r: ec.va(call) < ec.va(r) < ec.va(count_row)
        and r['text'] == f'movzx esi, byte {output}', 'objectHeader.result-load')
    count_index=next(i for i,r in enumerate(rows) if ec.va(r)==ec.va(count_row))
    need('objectHeader.result-provenance',ec.last_write(rows,count_index,'rsi') is loaded)
    for row in rows[index+1:next(i for i,r in enumerate(rows) if r is loaded)]:
        memory=row.get('memoryOperation',{});address=memory.get('address',{})
        need('objectHeader.local-not-overwritten',not(memory.get('direction')=='store' and
             address.get('base')=='rsp' and address.get('index') is None and
             address.get('displacement',-1)<=displacement<address.get('displacement',-1)+memory.get('memoryBytes',0)),row)
    need('objectHeader.same-result', count_row['text'].startswith('cmp sil, '))
    target = control_transfer(call)['target']
    selected, windows, body = ec.family(image, target-base)
    program = object_header_program(body, target, offsets)
    g = _Path(rows)
    g.at = false['target']
    output_save = ec.one(rows[:index], lambda r: r['text'] == 'mov rbx, rdx', 'objectHeader.output-save')
    need('objectHeader.output-provenance',ec.last_write(rows,index,'rbx') is output_save)
    g.take('mov rcx, rbx', 'mov qword [rbx], 0x0')
    g.call(base+barrier)
    if g.rows[g.at]['text'] == 'nop':
        g.take('nop')
    g.jump()
    g.take('mov rbx, [rsp+0x40]', 'add rsp, 0x20', 'pop rdi', 'ret')
    # The null path precedes any RSI save. Authenticate its complete frame and
    # original output/reader homes rather than inheriting a neighboring epilogue.
    start = sorted(rows, key=ec.va)[:3]
    need('objectHeader.caller-frame', [r['text'] for r in start] ==
         ['mov [rsp+0x18], rbx', 'push rdi', 'sub rsp, 0x20'])
    return dict(call=ec.site(call, base), resultLoad=ec.site(loaded, base),
        outputSave=ec.site(output_save, base), falseEdge=ec.site(rows[index+2], base),
        falseProgram=[ec.site(by_at[a], base) for a in g.seen], helperFamily=selected,
        helperWindows=windows, helperProgram=[ec.site(next(r for r in body if ec.va(r)==a),base) for a in program],
        condition='one buffered source byte, ordinary native ABI and compatible caller output storage')


def float32_program(rows,entry,offsets):
    """Prove a buffered raw Single read into XMM0, with its complete frame."""
    g=_Path(rows);g.at=entry
    b,r,c,s=(offsets[n] for n in ('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('mov [rsp+0x8], rbx','push rdi','sub rsp, 0x30',
        f'cmp dword [rcx+{r:#x}], 0x4','mov rbx, rcx','movaps [rsp+0x20], xmm6')
    g.branch(12,False)
    g.take(f'mov rax, [rbx+{b:#x}]','movss xmm6, [rax]',f'mov edi, [rbx+{r:#x}]','add edi, -0x4')
    g.branch(8,False)
    g.take(f'add qword [rbx+{b:#x}], 0x4',f'add dword [rbx+{c:#x}], 0x4',
        f'add dword [rbx+{s:#x}], 0x4',f'mov [rbx+{r:#x}], edi','mov rbx, [rsp+0x40]',
        'movaps xmm0, xmm6','movaps xmm6, [rsp+0x20]','add rsp, 0x30','pop rdi','ret')
    return g.seen


def inline_word_program(rows,entry,offsets):
    """Prove one raw DWORD into EAX and all four reader updates."""
    g=_Path(rows);g.at=entry
    b,r,c,s=(offsets[n] for n in ('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rsi','push rdi','sub rsp, 0x20',
        f'cmp dword [rcx+{r:#x}], 0x4','mov rdi, rcx');g.branch(12,False)
    g.take(f'mov rbx, [rdi+{b:#x}]','mov ebx, [rbx]',f'mov esi, [rdi+{r:#x}]','add esi, -0x4')
    g.branch(8,False)
    g.take(f'add qword [rdi+{b:#x}], 0x4',f'add dword [rdi+{c:#x}], 0x4',
        f'add dword [rdi+{s:#x}], 0x4',f'mov [rdi+{r:#x}], esi','mov rsi, [rsp+0x38]',
        'mov eax, ebx','mov rbx, [rsp+0x30]','add rsp, 0x20','pop rdi','ret')
    return g.seen


def advance_word_program(rows,entry,offsets):
    """Read a DWORD, pass exactly four to Advance, retain EBX and return EAX."""
    g=_Path(rows);g.at=entry;b,r=(offsets[n] for n in ('currentPtr','bufferLength'))
    g.take('mov [rsp+0x8], rbx','push rdi','sub rsp, 0x20',
        f'cmp dword [rcx+{r:#x}], 0x4','mov rdi, rcx');g.branch(12,False)
    g.take(f'mov rbx, [rdi+{b:#x}]','mov edx, 0x4','mov rcx, rdi','mov ebx, [rbx]')
    call=g.row();flow=control_transfer(call);need('word.advance-direct-call',flow['kind']=='call')
    g.take('mov eax, ebx','mov rbx, [rsp+0x30]','add rsp, 0x20','pop rdi','ret')
    return g.seen,flow['target']


def advance_four_program(rows,entry,offsets):
    """Prove the actual callee for EDX=4, including saved EBX and reader homes."""
    g=_Path(rows);g.at=entry;b,r,c,s=(offsets[n] for n in ('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('test edx, edx');g.branch(4,False)
    g.take('mov [rsp+0x10], rbx','push rdi','sub rsp, 0x20','movsxd rdi, edx',
        'mov rbx, rcx','mov [rsp+0x30], rsi',f'mov esi, [rcx+{r:#x}]','sub esi, edi')
    g.branch(8,False)
    g.take(f'add qword [rbx+{b:#x}], rdi',f'add dword [rbx+{c:#x}], edi',
        f'add dword [rbx+{s:#x}], edi',f'mov [rbx+{r:#x}], esi','mov rsi, [rsp+0x30]',
        'mov rbx, [rsp+0x38]','add rsp, 0x20','pop rdi','ret')
    return g.seen


def direct_profile_events(image,claim,path,contexts,reader,offsets,targets,aliases):
    """Bind every direct source call, including actual Single/value4 ABIs."""
    base=image.pe.image_base;selected=NativeReferenceContext(image)
    source=[]
    for index,row in enumerate(path):
        memory=row.get('memoryOperation',{})
        address=memory.get('address',{})
        need('direct.no-inline-source',not(memory.get('direction')=='load' and
            address.get('base')==reader and address.get('displacement')==offsets['currentPtr']))
        flow=control_transfer(row);argument=ec.last_write(path,index,'rcx')
        if argument and argument['text']==f'mov rcx, {reader}' and flow['kind'] in ('call','indirectCall','registerCall'):
            need('direct.source-call',flow['kind']=='call',row)
            source.append((index,row,flow['target']))
    need('direct.read-count',len(source)==len(claim['members'])==len(claim['anonymousReadOrder']),len(source))
    by_context={base+c['instructionRva']:c for c in contexts};used=set();events=[]
    for (index,row,target),member,kind in zip(source,claim['members'],claim['anonymousReadOrder']):
        declared=member['declaredType'];load=ec.last_write(path,index,'rdx')
        context=by_context.get(ec.va(load)) if load else None
        expected=None;mode=None;width=None
        if declared=='bool':expected,mode,width=targets['bool'],'proved-primitive',1;actual='byte'
        elif declared=='int' or selected.is_enum(declared):
            expected,mode,width=targets['int32'],'proved-primitive',4;actual='scalar32'
        elif declared=='float':expected,mode,width=targets['float32'],'proved-float32',4;actual='raw4'
        elif declared=='string':expected,mode,width=targets['string'],'proved-pooled-string',4;actual='byte-payload'
        elif declared in targets.get('value4',{}):
            expected,mode,width=targets['value4'][declared],'proved-value4',4;actual='scalar32'
        else:
            actual=aliases.get(declared)
            need('direct.reference-role',actual is not None and context is not None,declared)
            method=context['methodName']
            need('direct.reference-method',method in ('ReadValue','ReadPackable') and context['typeKind']==0x12)
            expected=base+targets[method]['targetRva'];mode='proved-reference-clone'
        need('direct.kind-target',kind==actual and target==expected,
             dict(member=member,kind=kind,actual=actual,target=hex(target-base),expected=hex(expected-base)))
        event=dict(kind=kind,instruction=ec.site(row,base),mode=mode)
        if width is not None:event['wireBytes']=width
        if context is not None:
            need('direct.context-owner-type',context['methodOwner']=='MemoryPack.MemoryPackReader' and
                 context['fullTypeName']==declared,context)
            if width is not None:
                need('direct.unmanaged-context',context['methodName']=='ReadUnmanaged' and context['typeKind']==0x11)
            event['context']=context;used.add(context['instructionRva'])
        elif selected.is_enum(declared) or declared in targets.get('value4',{}):
            need('direct.context-required',False,declared)
        events.append(event)
    need('direct.all-contexts-bound',used=={c['instructionRva'] for c in contexts})
    return events


def derive_profile(image, claim, targets, aliases, barrier, *, event_builder=ec.profile_events):
    """Prove one named static reader's exact current member/read/setter scope."""
    base = image.pe.image_base
    method = _method_row(image, [0, claim['ownerType'], claim['methodName'], 1])
    wrapper = ec.one(list(image.memorypack_wrappers.values()), lambda w:w.name==claim['ownerType'], 'role.wrapper')
    members = [{'name':m.name, 'declaredType':m.declared_type} for m in wrapper.members]
    need('declarations', members == claim['members'], members)
    selected, windows, rows = ec.family(image, method[3])
    need('decode', not any(r['text'].startswith('db ') for r in rows))
    header = ec.one(rows, lambda r:r['text'].startswith('cmp ') and
        r['text'].endswith(', '+hex(len(members))) and ec.raw(r)[-1]==len(members), 'role.member-count')
    reader_save=ec.one(rows[:10], lambda r:r['text']=='mov rdi, rcx', 'role.reader-save')
    reader=reader_save['text'].split()[1].rstrip(',')
    need('reader-provenance',ec.last_write(rows,rows.index(header),reader) is reader_save)
    offsets = ec.source_offsets(image)
    path, choices = ec.fast_path(rows, header, reader, offsets)
    contexts = ec.contexts(image, rows)
    events = event_builder(image, claim, path, contexts, reader, offsets, targets, aliases)
    kinds = {'byte':'bool-byte', 'scalar32':'int32', 'byte-payload':'byte-payload','raw4':'float32-bits'}
    reads = [dict(memberIndex=i, sourceCallsiteRva=e['instruction'][0],
                  readKind=kinds.get(e['kind'], 'nested-generic')) for i,e in enumerate(events)]
    numeric_rows = [dict(r, va=ec.va(r)) for r in rows]
    setter_targets = [image.method_pointer_va(image.metadata.methods[m.method_index]) for m in wrapper.members]
    check_read_setter_transfers(numeric_rows, reads, setter_targets, base=base)
    callsites={base+e['instruction'][0] for e in events}
    by_index={ec.va(r):i for i,r in enumerate(rows)}
    callsites.update(ec.va(rows[by_index[base+e['instruction'][0]]+6]) for e in events)
    need('complete-normal-call-set',callsites=={ec.va(r) for r in path if control_transfer(r)['kind'] in
        ('call','indirectCall','registerCall')})
    header_proof = caller_header(image, rows, header, reader, offsets, barrier)
    return dict(profile=claim['profile'], method=method, family=selected, codeWindows=windows,
        header=ec.site(header,base), headerProof=header_proof, readerRegister=reader,
        contexts=contexts, events=events, setterMethods=image.setter_methods(
            image.metadata.types[wrapper.type_definition], parameter='typeName', label=LABEL),
        selectedProgram=[ec.site(r,base) for r in path],
        selectedConditions=[dict(instruction=ec.site(d['instruction'],base),
            condition=d['condition'],taken=d['taken']) for d in choices])
