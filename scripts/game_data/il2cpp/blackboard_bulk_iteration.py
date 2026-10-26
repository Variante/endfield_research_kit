"""Checked list-loop framing and its selected on-disk SafeCount context.

This proves ascending indices bounded by the captured helper return, not a
live immutable collection, resolved MethodInfo or interface implementation.
"""
from __future__ import annotations
from .blackboard_vector_transfers import decode_blackboard_vectors,prove_dynamic_pair_field_copy
from .owned_partition import BranchGrammar
from .context import usage_method_spec
from .generic_entries import GenericEntries
from .memory_moves import decode_memory_move
from .protocol import runtime_type_name


def count_context(index,body,load,call):
    raw=index.pe.bytes_at_va(body.pointer,body.size)
    result=decode_memory_move(raw,load['offset'],body.pointer)
    if result is None:raise ValueError('blackboard-list-count: missing MethodInfo load')
    op=result[0]['memoryOperation'];address=op['address']
    if op['direction']!='load' or op['register']!='rdx' or op['memoryBytes']!=8 or not address['ripRelative']:
        raise ValueError('blackboard-list-count: full RIP-relative RDX load required')
    cell=address['absoluteAddress'];image=index.image;reg=image.registration;table=int(reg['methodSpecs'],16)
    spec=usage_method_spec(index.pe.bytes_at_va(cell,8),index.pe.bytes_at_va(table,reg['methodSpecsCount']*12),
        len(index.metadata.methods),reg['genericInstsCount'],source=str(image.gameassembly),usage_offset=cell,records_offset=table)
    method=index.metadata.methods[spec['definition']]
    symbol=index.metadata.type_full_name(index.metadata.types[method.declaring_type])+'.'+index.metadata.string(method.name_index)
    arguments=[]
    for key in ('classInstantiationIndex','methodInstantiationIndex'):
        inst=image.instantiations.resolve(spec[key])
        arguments.append([runtime_type_name(index.pe,index.metadata,a.type_pointer_va) for a in inst.arguments])
    if symbol!='Beyond.CollectionExtensions.SafeCount' or arguments!=[[],['Beyond.Blackboard+DataPair']]:
        raise ValueError('blackboard-list-count: selected SafeCount<DataPair> context required')
    ret=image.pe.u64_at_va(int(reg['types'],16)+method.return_type*8)
    type_record=image.pe.bytes_at_va(ret,16)
    if (len(type_record)!=16 or type_record[10]!=8 or type_record[11]&0x7f or
            runtime_type_name(index.pe,index.metadata,ret)!='int' or not method.flags&0x10):
        raise ValueError('blackboard-list-count: Int32 return required')
    b=bytes.fromhex(call['bytes'])
    if len(b)!=5 or b[0]!=0xe8:raise ValueError('blackboard-list-count: direct Count call required')
    pointer=int(call['va'],16)+5+int.from_bytes(b[1:],'little',signed=True)
    entries=GenericEntries(image)._matching_registrations(method.index,*arguments)
    matching=[e for e in entries if e['methodSpecIndex']==spec['index'] and e['pointer']
              and e['registration']['indices'][-1]==-1]
    if len(matching)!=1:raise ValueError('blackboard-list-count: context has no unique ordinary registered entry')
    return {'symbol':symbol,'methodArguments':arguments[1],'runtimeSelectionObserved':False,
            'usageVa':cell,'methodSpecIndex':spec['index'],'callPointer':pointer,
            'registeredEntryPointer':matching[0]['pointer'],
            'callsRegisteredEntry':pointer==matching[0]['pointer'],
            'boundary':'Selected on-disk MethodSpec, ordinary registration and separate compiled call target. Different pointers are not joined by a name or body resemblance. Resolved live MethodInfo and helper/interface Count semantics remain conditional.'}


def prove_dynamic_list_iteration(index,body):
    from .body_claims import _named_direct_call
    label='blackboard-list-iteration'
    if body.symbol!='Beyond.Blackboard.AssignDynamic' or not index.matches_parameters(body.pointer,
            ['System.Collections.Generic.List`1<Beyond.Blackboard+DataPair>']):raise ValueError(label+'.typed-list')
    copy=prove_dynamic_pair_field_copy(index,body)
    rows=decode_blackboard_vectors(index.mapper,index.pe.bytes_at_va(body.pointer,body.size),body.pointer)
    g=BranchGrammar(rows,label=label)
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rbp','mov [rsp+0x18], rsi',
           'push rdi','sub rsp, 0x80','xorps xmm0, xmm0','mov rbx, rdx','mov rbp, rcx','xor edx, edx')
    g.pattern(r'mov ecx, 0x[0-9a-f]+');g.take('movups [rsp+0x20], xmm0','movups [rsp+0x30], xmm0')
    guard=g.row()
    if _named_direct_call(index,guard,'IFix.WrappersManagerImpl.IsPatched') is None:g.fail('guard','named IFix call',guard)
    g.take('test al, al');g.branch('jne')
    load=g.row();g.take('mov rcx, rbx','xor edi, edi');call=g.row()
    count=count_context(index,body,load,call)
    g.take('mov esi, eax','test eax, eax');g.branch('jg','loop')
    g.mark('restore');g.take('lea r11, [rsp+0x80]','mov rbx, [r11+0x10]','mov rbp, [r11+0x18]',
        'mov rsi, [r11+0x20]','mov rsp, r11','pop rdi','ret','nop')
    g.mark('loop');g.take('test rbx, rbx');g.branch('je','null')
    g.take('cmp edi, [rbx+0x18]');g.branch('jae')
    g.take('mov rcx, [rbx+0x10]','test rcx, rcx');g.branch('je','null')
    g.take('cmp edi, [rcx+0x18]');g.branch('jae','bounds')
    g.take('movsxd rax, edi','inc rax','shl rax, 0x5')
    if g.rows[g.cursor]['offset']!=copy['fieldCopyStartOffset']:g.fail('copy-entry',copy['fieldCopyStartOffset'],g.rows[g.cursor])
    while g.cursor<len(rows) and rows[g.cursor]['offset']<copy['fieldCopyEndOffset']:g.row()
    if g.cursor==len(rows) or rows[g.cursor]['offset']!=copy['fieldCopyEndOffset']:g.fail('copy-end',copy['fieldCopyEndOffset'],'outside boundary')
    increment=g.take('inc rdi')
    if bytes.fromhex(increment['bytes'])!=b'\xff\xc7':g.fail('increment-width','Int32 INC EDI',increment)
    g.take('cmp edi, esi');g.branch('jl','loop');g.branch('jmp','restore')
    g.mark('bounds');bounds=g.row();g.take('int3');g.mark('null');null=g.row();g.take('int3');g.finish()
    for row in (bounds,null):
        b=bytes.fromhex(row['bytes'])
        if len(b)!=5 or b[0]!=0xe8:g.fail('error-call','direct E8',row)
    return {'evidenceBoundary':'conditional','countContext':count,'startsAtZero':True,
        'ascendingCapturedBound':True,'recordStrideBytes':32,'fieldCopy':copy,
        'condition':'False IFix selection; Count returns a correct nonnegative bound; each source bound check succeeds; source list, items and frame remain valid and unchanged by helpers or aliases. Exception/replacement routes, live collection mutation and baseline consumption remain separate.'}


def check_dynamic_list_iteration(index,body):
    try:prove_dynamic_list_iteration(index,body)
    except (ValueError,KeyError,IndexError) as exc:return str(exc)
    return None
