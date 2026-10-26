"""Checked ordinary action Branch dispatch suffix, with declared field offsets."""
from scripts.game_data.il2cpp.consumer_control import check_consumer_control
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.owned_partition import BranchGrammar


def check_action_branch_program(rows, *, entry, owned_ranges, fields, count_offset, item_pointer):
    control=check_consumer_control(rows,entry=entry,owned_ranges=owned_ranges)
    refs=check_reference_origins(rows,entry=entry,owned_ranges=owned_ranges,
        incoming_registers={'rcx':'this'},incoming_stack_slots={},selected_call_returns={})
    if set(fields)!={'list','index','id','reserved','next'} or any(type(x) is not int or x<16 for x in fields.values()):
        raise ValueError('actionBranch.declared-fields')
    listing=f'[rbx+{fields["list"]:#x}]'; index=f'[rbx+{fields["index"]:#x}]';count=f'[rcx+{count_offset:#x}]'
    candidates=[n for n,r in enumerate(rows) if r['text']=='mov rcx, '+listing]
    # The first field load starts the complete ordinary dispatch suffix.
    if len(candidates)!=3:raise ValueError('actionBranch.three-list-loads')
    start=candidates[0]; suffix=rows[start:]
    if refs['registerOrigins'][int(suffix[0]['va'],16)].get('rbx')!=['this']:
        raise ValueError('actionBranch.incoming-receiver')
    g=BranchGrammar(suffix,label='actionBranch')
    def jle(label):
        r=g.row();b=bytes.fromhex(r['bytes']);flow=control_transfer(r)
        if not (b[:1]==b'\x7e' or b[:2]==b'\x0f\x8e') or flow['kind']!='conditional':
            g.fail('signed-less-or-equal','JLE',r)
        g.edges.append((flow['target'],label,r))
    g.take('mov rcx, '+listing,'test rcx, rcx');g.branch('je','null')
    g.take('mov eax, '+index,'cmp dword '+count+', eax');jle('advance')
    g.take('mov ecx, '+count,'dec ecx','cmp ecx, eax');jle('item')
    g.take(f'mov eax, [rbx+{fields["id"]:#x}]',f'mov [rbx+{fields["reserved"]:#x}], eax')
    g.mark('item');g.take('mov rcx, '+listing,'test rcx, rcx');g.branch('je','null')
    context=g.pattern(r'mov r8, \[rip\+0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.take('mov edx, '+index);call=g.call(item_pointer)
    g.take(f'mov [rbx+{fields["next"]:#x}], eax');g.mark('advance')
    g.take('mov eax, '+index,'mov rcx, '+listing,
           'inc eax','mov '+index+', eax','test rcx, rcx');g.branch('je','null')
    g.take('cmp dword '+count+', eax');epilogue=g.branch('jg')
    g.mark('reset');g.take('mov dword '+index+', 0x0');reset=g.branch('jmp')
    g.mark('null');null=g.pattern(r'call 0x[0-9a-f]+');g.take('int3');g.finish()
    if epilogue['target']!=reset['target']:raise ValueError('actionBranch.common-return')
    by={int(r['va'],16):r for r in rows};at=reset['target']
    for text in ('mov rbx, [rsp+0x40]','movaps xmm6, [rsp+0x20]','add rsp, 0x30','pop rdi','ret'):
        r=by.get(at)
        if r is None or r['text']!=text:raise ValueError('actionBranch.return-frame')
        at+=len(bytes.fromhex(r['bytes']))
    return dict(contextLoad=context,itemCall=call,control=control,referenceOrigins=refs,
        evidenceBoundary='conditional',condition='Ordinary incoming receiver, typed item call and stable list storage. For a valid nonnegative index below the selected count, stores the item call Int32 result as next; reserves this action id when another item follows, increments the index, and resets it at count. Invalid-index behavior, IFix replacements, callee semantics and runtime scheduling are separate.')
