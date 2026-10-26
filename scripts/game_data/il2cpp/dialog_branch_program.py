"""Check the original branch selector, including its null-condition arm."""
from scripts.game_data.il2cpp.owned_partition import BranchGrammar
from scripts.game_data.il2cpp.consumer_entry_program import ordinary_consumer_entry
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins

def check_dialog_branch_program(rows, *, entry, ranges, conditions, result, calls=None):
    ordinary=ordinary_consumer_entry(rows,entry=entry,owned_ranges=ranges)
    refs=check_reference_origins(ordinary['rows'],entry=entry,owned_ranges=ordinary['ranges'],incoming_registers={'rdx':'branch-data'},incoming_stack_slots={},selected_call_returns={})
    load=f'mov rsi, [rbx+{conditions:#x}]';matches=[i for i,r in enumerate(rows) if r['text']==load]
    if len(matches)!=1:raise ValueError('dialogBranch.unique-conditions-load')
    start=matches[0]-3
    if refs['registerOrigins'][int(rows[matches[0]]['va'],16)].get('rbx')!=['branch-data']:raise ValueError('dialogBranch.selected-data-argument')
    if [r['text'] for r in rows[:5]]!=['mov [rsp+0x8], rbx','mov [rsp+0x10], rsi','mov [rsp+0x18], rdi','push r14','sub rsp, 0x50']:raise ValueError('dialogBranch.entry-frame')
    g=BranchGrammar(rows[start:],label='dialogBranch')
    selected={};expected=calls or {}
    def call(role):
        from scripts.game_data.il2cpp.initializer_control import control_transfer
        row=g.row();flow=control_transfer(row)
        if flow['kind']!='call':g.fail('direct-call:'+role,'original direct call',row)
        target=flow['target']
        if role in expected and target!=expected[role] or role in selected and target!=selected[role]:g.fail('call-identity:'+role,expected.get(role,selected.get(role)),target)
        selected[role]=target
        return row
    def rip(register):return g.pattern(r'mov '+register+r', \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    def dispose():g.take('lea rcx, [rsp+0x40]');call('dispose')
    g.take('mov qword [rsp+0x28], 0x0','test rbx, rbx');g.branch('je','nullData')
    g.take(load,'mov [rsp+0x30], rsi','xor edi, edi','mov [rsp+0x78], edi','xor ebx, ebx')
    g.mark('loop');g.take('mov [rsp+0x20], ebx');count_context=rip('rdx');g.take('mov rcx, rsi');count=call('count')
    g.take('cmp ebx, eax');g.branch('jge','finish');g.take('test rsi, rsi');g.branch('je','nullList')
    item_context=rip('r8');g.take('mov edx, ebx','mov rcx, rsi');item=call('item')
    g.take('mov [rsp+0x28], rax','mov qword [rsp+0x40], 0x0','lea rax, [rsp+0x28]','mov [rsp+0x48], rax','mov rcx, [rsp+0x28]','test rcx, rcx');g.branch('je','selectedNull')
    g.take('xor r8d, r8d');rip('rdx');activate=call('activate')
    g.take('mov rdx, [rsp+0x28]','test rdx, rdx');g.branch('je','nullAfterActivate')
    g.take(f'cmp dword [rdx+{result:#x}], 0x2');g.branch('jne','checkTrue')
    g.take('mov ecx, 0xa');call('conditionType');g.take('mov r14d, eax');rip('rcx');call('loggerPrepare')
    log_context=rip('r9');g.take('mov r8d, r14d');rip('rdx');g.take('mov cl, 0x9');call('logError');g.take('mov rdx, [rsp+0x28]')
    g.mark('checkTrue');g.take('test rdx, rdx');g.branch('je','nullBeforeCompare')
    g.take('mov ecx, 0x1b',f'cmp dword [rdx+{result:#x}], 0x1');g.branch('je','selectedTrue')
    call('scopeEnd');g.take('nop');dispose();g.branch('jmp','increment')
    g.mark('selectedTrue');g.take('mov edi, ebx','mov [rsp+0x78], ebx');call('scopeEnd');g.take('nop');dispose();g.branch('jmp','finish')
    g.mark('selectedNull');g.take('mov edi, ebx','mov [rsp+0x78], ebx');dispose();g.branch('jmp','finish')
    cleanup_start=int(g.rows[g.cursor]['va'],16);dispose();g.take('mov rsi, [rsp+0x30]','mov edi, [rsp+0x78]','mov ebx, [rsp+0x20]')
    if cleanup_start in ordinary['fullGraph']['reachableInstructions']:g.fail('cleanup-entry','unentered from ordinary entry',cleanup_start)
    g.mark('increment');g.take('inc ebx');g.branch('jmp','loop')
    g.mark('finish');g.take('mov eax, edi','mov rbx, [rsp+0x60]','mov rsi, [rsp+0x68]','mov rdi, [rsp+0x70]','add rsp, 0x50','pop r14','ret')
    g.mark('nullData');call('nullThrow');g.take('int3')
    g.mark('nullList');call('nullThrow');g.take('nop')
    g.mark('nullBeforeCompare');call('nullResultThrow');g.take('nop')
    g.mark('nullAfterActivate');call('nullResultThrow');g.take('int3','int3');g.finish()
    return dict(selectedCalls=selected,countContext=count_context,itemContext=item_context,logContext=log_context,countCall=count,itemCall=item,activateCall=activate,
        nullConditionSelectsOrdinal=True,trueResultSelectsOrdinal=True,firstMatchingOrdinal=True,noSelectionReturnsZero=True,
        unenteredOwnedInstructions=ordinary['unenteredOwnedByteCandidates'],evidenceBoundary='conditional',
        condition='Original ordinary entry, selected typed branch data, stable valid list/count/item implementations and frame, Win64 nonvolatile preservation and normally returning calls preserving the list, frame and condition identity; activation may update the result, while logging/cleanup preserve it. First null entry or post-activation True result selects its ordinal; no match returns zero. IFix, exception/resumption, generic runtime binding, activation meaning and live selection remain separate.')
