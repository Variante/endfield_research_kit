"""Checked current Inactive and PreActiveEndSendActiveState case fragments."""
from scripts.game_data.il2cpp.levelscript_runtime_program import runtime_case
from scripts.game_data.il2cpp.owned_partition import BranchGrammar
from scripts.game_data.il2cpp.initializer_control import control_transfer


def check_levelscript_selector_program(part,program,origins,*,entry,image_base,fields,enums,pointers):
    label='levelscriptSelector';rows=program['rows'];refs=origins['registerOrigins'];edges=program['control']['edges']
    def reaches(start,target,blocked=()):
        seen=set();pending=[start]
        while pending:
            at=pending.pop()
            if at in blocked or at in seen:continue
            if at==target:return True
            seen.add(at);pending.extend(edges[at]-seen)
        return False
    def case(name):return runtime_case(part,program,origins,entry=entry,image_base=image_base,fields=fields,enums=enums,case=name)
    inactive=case('Inactive');ending=case('PreActiveEndSendActiveState')
    candidates=[n for n,row in enumerate(rows) if row['text']==f'mov rax, [rdi+{fields["brief"]:#x}]']
    if len(candidates)!=1:raise ValueError(label+'.unique-inline-brief-read')
    start=candidates[0];g=BranchGrammar(rows[start:],label=label+'.inactive')
    g.take(f'mov rax, [rdi+{fields["brief"]:#x}]','test rax, rax');null=g.branch('je')
    type_read=g.take(f'mov ecx, [rax+{fields["type"]:#x}]');state=g.take(f'mov eax, [rdi+{fields["state"]:#x}]')
    g.take(f'cmp ecx, {enums["type"]["SubLevelScript"]:#x}');g.branch('je','sublevel')
    g.take('xor edx, edx','mov rcx, rdi',f'cmp eax, {enums["state"]["Enabled"]:#x}');disabled=g.branch('jne')
    area=g.call(pointers['UpdateWithinActiveArea']);g.take('test al, al');g.branch('jne','preActive');outside=g.branch('jmp','exit')
    g.mark('sublevel');substate=g.take(f'cmp eax, {enums["state"]["Active"]:#x}');g.branch('jne','exit')
    g.mark('preActive');g.take(f'mov edx, {enums["runtime"]["PreActive"]:#x}','mov rcx, rdi','xor r8d, r8d')
    setter=g.call(pointers['set_runtimeState']);g.branch('jmp','exit');g.labels['exit']=outside['target'];g.finish(prefix=True)
    first=int(rows[start]['va'],16);state_at=int(state['va'],16);setter_at=int(setter['va'],16)
    if (refs[first]['rdi']!=['this'] or refs[state_at]['rdi']!=['this']
            or not reaches(int(inactive['caseTargetVa'],16),first)
            or not reaches(first,setter_at) or reaches(int(inactive['caseTargetVa'],16),setter_at,{state_at})):
        raise ValueError(label+'.inactive-receiver-or-state-dominance')
    by_at={int(row['va'],16):row for row in rows}
    trap=by_at.get(null['target']);stop=by_at.get(null['target']+len(bytes.fromhex(trap['bytes']))) if trap else None
    if not trap or control_transfer(trap)['kind']!='call' or not stop or stop['bytes']!='cc':raise ValueError(label+'.null-trap')
    # The disabled notification joins the exit immediately after one direct call.
    notified=by_at.get(disabled['target']);following=disabled['target']+len(bytes.fromhex(notified['bytes'])) if notified else 0
    if not notified or control_transfer(notified)['kind']!='call' or following!=outside['target']:
        raise ValueError(label+'.disabled-exit')
    local={int(row['va'],16) for row in rows[start:rows.index(setter)+2]}
    for source,targets in edges.items():
        if source not in local and any(target in local-{first,state_at} for target in targets):
            raise ValueError(label+'.inactive-gate-bypass')
    offset=lambda row:int(row['va'],16)-entry
    at=int(ending['caseTargetVa'],16);position=next(i for i,row in enumerate(rows) if int(row['va'],16)==at)
    g=BranchGrammar(rows[position:],label=label+'.sendActive')
    g.take('xor edx, edx','mov rcx, rdi');getter=g.call(pointers['get_levelScriptType'])
    g.take('xor r8d, r8d','mov rcx, rdi',f'cmp eax, {enums["type"]["SubLevelScript"]:#x}');g.branch('je','subwait')
    g.take('mov dl, 0x1');request=g.call(pointers['_SendLevelScriptSetActive'])
    g.take(f'mov edx, {enums["runtime"]["WaitForStateActive"]:#x}','mov rcx, rdi','xor r8d, r8d')
    wait=g.call(pointers['set_runtimeState']);g.branch('jmp','exit');g.mark('subwait')
    g.take(f'mov edx, {enums["runtime"]["WaitForStateActive"]:#x}');subwait=g.call(pointers['set_runtimeState']);g.branch('jmp','exit')
    g.labels['exit']=outside['target'];g.finish(prefix=True)
    for row in (area,setter,getter,request,wait,subwait):
        if refs[int(row['va'],16)]['rcx']!=['this']:raise ValueError(label+'.callee-receiver')
    local={int(row['va'],16) for row in rows[position:rows.index(subwait)+2]}
    if any(source not in local and any(target in local-{at} for target in targets) for source,targets in edges.items()):
        raise ValueError(label+'.send-active-gate-bypass')
    return dict(runtimeCaseGates=[inactive,ending],inactiveLevelScriptTypeInstructionOffset=offset(type_read),
        nonSubLevelEnabledStateInstructionOffset=offset(state),subLevelActiveStateInstructionOffset=offset(substate),
        activeAreaGateCallOffset=offset(area),preActiveSetterCallOffset=offset(setter),preActiveLevelScriptTypeCallOffset=offset(getter),
        activeTrueRequestCallOffset=offset(request),waitForStateActiveSetterOffsets=[offset(wait),offset(subwait)],
        nonSubLevelRequiresEnabledAndActiveArea=True,subLevelRequiresPublicActive=True,
        nonSubLevelSendsActiveTrueAfterPreActive=True,subLevelSkipsActiveTrueRequest=True,
        evidenceBoundary='conditional',condition='Selected ordinary case fragments and typed original getter field returns with stable disjoint storage. Inlined replacement-property paths, exceptional/resumption entries, live state, request completion and recursive effects remain separate.')
