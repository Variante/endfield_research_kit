"""Complete ordinary keyed Float lookup: direct success, then entity fallback.

The original local branch targets and both identical keyed/out-parameter
lanes are checked. Typed parameter expressions, other overloads and live IFix
selection are outside this program profile.
"""
from __future__ import annotations
from .stack_argument_flow import decode_stack_flow
from .program_grammar import ProgramGrammar
from .body_claims import _named_direct_call,_virtual_getter_helper,_virtual_method_slot


def prove_float_query_order(index,body):
    label='blackboard-float-query'
    if body.symbol!='Beyond.ActionBlackboard.TryGetFloat':raise ValueError(label+'.owner')
    rows=decode_stack_flow(index.mapper,index.pe.bytes_at_va(body.pointer,body.size),body.pointer)
    g=ProgramGrammar(rows,label=label)
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rsi','push rdi','sub rsp, 0x30',
           'mov rsi, rdx','mov rbx, rcx','xor edx, edx')
    g.pattern(r'mov ecx, 0x[0-9a-f]+');g.take('mov rdi, r8')
    guard=g.row()
    if _named_direct_call(index,guard,'IFix.WrappersManagerImpl.IsPatched') is None:g.fail('guard','named IFix call',guard)
    g.take('test al, al');g.branch('jne')
    helper=None
    def getter(symbol):
        nonlocal helper
        slot=_virtual_method_slot(index,symbol)
        g.take(f'mov ecx, {hex(slot)}','mov rdx, rbx')
        call=g.row();pointer=int(call['text'].split()[-1],16)
        if helper is not None and pointer!=helper:g.fail('getter-helper',helper,pointer)
        if not _virtual_getter_helper(index,pointer):g.fail('getter-helper','bounded dispatch',call)
        helper=pointer
        g.take('test rax, rax')
    def query():
        g.take('xor r9d, r9d','mov r8, rdi','mov rdx, rsi','mov rcx, rax')
        row=g.row()
        if _named_direct_call(index,row,'Beyond.Blackboard.TryGetFloat') is None:g.fail('typed-query','Blackboard.TryGetFloat',row)
        g.take('test al, al')
    getter('Beyond.ActionBlackboard.get_directBlackboard');g.branch('je','null-error')
    query();g.branch('je','entity')
    g.mark('success');g.take('mov al, 0x1')
    g.mark('restore');g.take('mov rbx, [rsp+0x40]','mov rsi, [rsp+0x48]','add rsp, 0x30','pop rdi','ret')
    g.mark('entity');getter('Beyond.ActionBlackboard.get_entityBlackboard');g.branch('je','failure')
    getter('Beyond.ActionBlackboard.get_entityBlackboard');g.branch('je','null-error')
    query();g.branch('jne','success')
    g.mark('failure');g.take('mov [rdi], 0x0','xor al, al');g.branch('jmp','restore')
    g.mark('null-error');row=g.row()
    b=bytes.fromhex(row['bytes'])
    if len(b)!=5 or b[0]!=0xe8:g.fail('null-call','complete E8',row)
    g.take('int3');g.finish()
    return {'evidenceBoundary':'conditional','directSuccessBypassesEntity':True,
        'entityQueriedOnlyAfterDirectFalse':True,'sameKeyAndOutSlot':True,'failureZeroesFloat':True,
        'condition':'Selected false IFix guard, valid direct getter and ordinary Win64 calls; only the keyed Float program is covered.'}


def check_float_query_order(index,body):
    try:prove_float_query_order(index,body)
    except (ValueError,KeyError,IndexError) as exc:return str(exc)
    return None
