"""Prove the selected Blackboard matched-slot replacement program.

This checks the true-comparison fallthrough, full pair stores, retained dynamic
flag and immediate return. Key comparison, scan coverage and live selection
remain separate; a caller cannot turn this into a universal list merge claim.
"""
from __future__ import annotations
from .reference_layouts import NativeReferenceContext
from .stack_argument_flow import decode_stack_flow
from .program_grammar import ProgramGrammar
from .owned_partition import BranchGrammar


def prove_matched_pair_replacement(index,body):
    label='blackboard-matched-pair'
    if body.symbol!='Beyond.Blackboard._AssignInternal':raise ValueError(label+'.owner')
    context=NativeReferenceContext(index.image,index=index);pair='Beyond.Blackboard+DataPair'
    if (context.parent('Beyond.Blackboard')!='System.Collections.Generic.List`1<'+pair+'>'
            or not context.is_value_type(pair)):
        raise ValueError(label+'.declared-list-and-value-pair')
    fields=[context.field(pair+'::'+name) for name in ('key','valueDouble','valueStr','isDynamic')]
    if [(t,o) for _,t,o in fields]!=[('string',16),('double',24),('string',32),('bool',40)]:
        raise ValueError(label+'.complete-pair-fields')
    td=index.types[pair];registration=index.image.registration
    if not 0<=td.index<int(registration['typeDefinitionsSizesCount']):raise ValueError(label+'.size-index')
    size_pointer=index.pe.u64_at_va(int(registration['typeDefinitionsSizes'],16)+td.index*8)
    sizes=index.pe.bytes_at_va(size_pointer,16)
    if len(sizes)!=16 or int.from_bytes(sizes[:4],'little')!=48:raise ValueError(label+'.boxed-size')
    rows=decode_stack_flow(index.mapper,index.pe.bytes_at_va(body.pointer,body.size),body.pointer)
    # Incoming list and indirect Win64 DataPair argument are retained before
    # any branch or call. A selected program cannot substitute other bases.
    g=ProgramGrammar(rows[:5],label=label+'.entry')
    g.take('push rbp','push rdi','sub rsp, 0x68','mov rdi, rcx','mov rbp, rdx');g.finish()
    possible=[n for n,r in enumerate(rows) if r['text']=='call rax' and n+2<len(rows)
              and rows[n+1]['bytes']=='84 c0' and bytes.fromhex(rows[n+2]['bytes'])[:2]==b'\x0f\x84']
    failures=[]
    for n in possible:
        try:
            g=BranchGrammar(rows[n+1:],label=label)
            g.take('test al, al');g.branch('je')
            g.take('cmp ebx, [rdi+0x18]');g.branch('jae')
            g.take('mov rcx, [rdi+0x10]','test rcx, rcx');g.branch('je')
            g.take('cmp ebx, [rcx+0x18]');g.branch('jae')
            g.take('movsxd rax, ebx','inc rax','shl rax, 0x5',
                   'mov eax, [rax+rcx*1+0x18]','mov [rbp+0x18], al')
            g.take('cmp ebx, [rdi+0x18]');g.branch('jae')
            g.take('mov rdx, rcx','test rcx, rcx');g.branch('je')
            g.take('movsxd rcx, ebx','cmp ebx, [rdx+0x18]');g.branch('jae')
            g.take('movups xmm0, [rbp+0x0]','lea rax, [rcx+0x1]',
                   'movups xmm1, [rbp+0x10]','shl rax, 0x5','inc rcx',
                   'shl rcx, 0x5','add rcx, rdx','movups [rax+rdx*1], xmm0',
                   'movups [rax+0x10+rdx*1], xmm1')
            call=g.row();b=bytes.fromhex(call['bytes'])
            if len(b)!=5 or b[0]!=0xe8:g.fail('barrier-call','complete E8',call)
            g.take('inc [rdi+0x1c]','mov r15, [rsp+0x60]','mov r14, [rsp+0x98]',
                   'mov r12, [rsp+0x90]','mov rsi, [rsp+0x88]','mov rbx, [rsp+0x80]',
                   'add rsp, 0x68','pop rdi','pop rbp','ret')
            g.finish(prefix=True)
            return {'comparisonCallOffset':rows[n]['offset'],'pairBytes':32,'retainsExistingDynamicFlag':True,
                'replacesWholeMatchedSlot':True,'returnsAfterReplacement':True,'evidenceBoundary':'conditional',
                'condition':'True comparison and successful list/array checks, unchanged incoming list/item bases and normal barrier call; key comparator, complete scan and live IFix selection are separate.'}
        except ValueError as exc:failures.append(str(exc))
    raise ValueError(label+'.no-program:'+str(failures[:2]))


def check_matched_pair_replacement(index,body):
    try:prove_matched_pair_replacement(index,body)
    except (ValueError,KeyError,IndexError) as exc:return str(exc)
    return None


def prove_dynamic_pair_filter(index,body):
    from .body_claims import _named_direct_call
    label='blackboard-dynamic-filter'
    if body.symbol!='Beyond.Blackboard._AssignDynamicInternal':raise ValueError(label+'.owner')
    context=NativeReferenceContext(index.image,index=index)
    owner,kind,offset=context.field('Beyond.Blackboard+DataPair::isDynamic')
    if kind!='bool' or offset!=40 or not context.is_value_type(owner):raise ValueError(label+'.pair-flag')
    rows=decode_stack_flow(index.mapper,index.pe.bytes_at_va(body.pointer,body.size),body.pointer)
    g=ProgramGrammar(rows,label=label)
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rbp','mov [rsp+0x18], rsi',
           'push rdi','sub rsp, 0x40','mov rbp, rdx','mov rdi, rcx','xor edx, edx')
    g.pattern(r'mov ecx, 0x[0-9a-f]+');guard=g.row()
    if _named_direct_call(index,guard,'IFix.WrappersManagerImpl.IsPatched') is None:
        g.fail('guard','named IFix call',guard)
    g.take('test al, al');g.branch('jne')
    g.take('movups xmm0, [rbp+0x0]','movups [rsp+0x20], xmm0','cmp [rbp+0x18], al')
    g.branch('jne','dynamic')
    g.take('mov rbx, [rsp+0x50]','mov rbp, [rsp+0x58]','mov rsi, [rsp+0x60]',
           'add rsp, 0x40','pop rdi','ret')
    g.mark('dynamic');g.finish(prefix=True)
    return {'evidenceBoundary':'conditional','nonDynamicReturnsFalseBeforeScan':True,
        'condition':'False IFix guard and ordinary Win64 indirect DataPair argument. Dynamic continuation and duplicate scan are separate.'}


def check_dynamic_pair_filter(index,body):
    try:prove_dynamic_pair_filter(index,body)
    except (ValueError,KeyError,IndexError) as exc:return str(exc)
    return None
