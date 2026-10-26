"""Original NPC proxy stored-ordinal/list/dialog transfer component."""
from scripts.game_data.il2cpp.owned_partition import BranchGrammar
from scripts.game_data.il2cpp.initializer_control import control_transfer


def check_npc_proxy_selection_program(program, refs, *, entry, fields, pointers, count_offset):
    rows=program['rows'];edges=program['control']['edges'];origins=refs['registerOrigins']
    def fail(check):raise ValueError('npcProxySelection.'+check)
    def at(row):return int(row['va'],16)
    def reaches(source,target,blocked=()):
        seen=set();pending=[source]
        while pending:
            current=pending.pop()
            if current in seen or current in blocked:continue
            if current==target:return True
            seen.add(current);pending.extend(edges[current]-seen)
        return False
    calls=[i for i,r in enumerate(rows) if control_transfer(r).get('target')==pointers['lookup'] and control_transfer(r)['kind']=='call']
    if len(calls)!=1 or calls[0]<8:fail('unique-lookup-call')
    start=calls[0]-8;g=BranchGrammar(rows[start:],label='npcProxySelection.original')
    def rip(register):return g.pattern('mov '+register+r', \[rip[^\]]*\]')
    def branch(code,label):
        row=g.row();flow=control_transfer(row)
        if flow['kind']!='conditional' or flow.get('conditionCode')!=code:fail('conditional-byte-predicate')
        g.edges.append((flow['target'],label,row));return flow['target']
    g.take('mov rcx, rdi')
    npc_id=g.call(pointers['npcId']);g.take('test rbp, rbp');g.branch('je','nullThrow')
    g.take('xor r9d, r9d','lea r8, [rsp+0x20]','mov rdx, rax','mov rcx, rbp');lookup=g.call(pointers['lookup'])
    g.take('test al, al');g.branch('je','returnCheck');cast_context=rip('rdx')
    data=g.take(f'mov rcx, [rdi+{fields["data"]:#x}]');cast=g.call(pointers['cast'])
    g.take('mov r8, rax','test rax, rax');g.branch('je','returnCheck')
    g.take(f'mov rcx, [rax+{fields["rows"]:#x}]','test rcx, rcx');g.branch('je','noCount')
    count=g.take(f'mov ecx, [rcx+{count_offset:#x}]')
    g.take('mov [rsp+0x58], rsi','mov [rsp+0x5c], ecx','mov byte [rsp+0x58], 0x1','mov rcx, [rsp+0x58]');g.branch('jmp','joinCount')
    g.mark('noCount');no_count=g.take('mov rcx, rsi');g.mark('joinCount')
    g.take('mov [rsp+0x58], rcx','mov rdx, [rsp+0x20]','test rdx, rdx');g.branch('je','nullThrow')
    ordinal=g.take(f'mov eax, [rdx+{fields["index"]:#x}]')
    g.take('cmp dword [rsp+0x5c], eax','setg sil','test sil, cl');g.branch('je','returnCheck')
    g.take('cmp eax, -0x1');branch(14,'returnCheck')
    g.take(f'mov rcx, [r8+{fields["rows"]:#x}]','test rcx, rcx');g.branch('je','nullThrow')
    item_context=rip('r8');g.take('mov edx, eax');item=g.call(pointers['item'])
    g.take('test rax, rax');g.branch('je','nullThrow');dialog=g.take(f'mov rax, [rax+{fields["dialog"]:#x}]')
    g.take('mov rcx, rbx');store=g.take('mov [rbx], rax');barrier=g.row()
    if control_transfer(barrier)['kind']!='call':fail('output-barrier-call')
    g.take('nop');g.branch('jmp','returnCheck')
    returns=[r for r in rows if r['bytes']=='48 8b 03'];traps=[r for i,r in enumerate(rows[:-1]) if control_transfer(r)['kind']=='call' and rows[i+1]['bytes']=='cc']
    if len(returns)!=1 or len(traps)!=1:fail('unique-return-and-null-throw')
    g.labels.update(returnCheck=at(returns[0]),nullThrow=at(traps[0]));g.finish()
    if origins[at(npc_id)]['rcx']!=['this'] or origins[at(data)]['rdi']!=['this'] or origins[at(store)]['rbx']!=['dialog-output']:fail('incoming-receivers')
    if origins[at(no_count)]['rsi']!=['constant:0x0'] or origins[at(count)]['rsi']!=['constant:0x0']:fail('absent-count-zero-source')
    local={at(r) for r in rows[start:]};first=at(rows[start])
    if any(source not in local and any(target in local-{first} for target in targets) for source,targets in edges.items()):fail('original-path-gate-bypass')
    for source,target in ((at(lookup),at(ordinal)),(at(ordinal),at(item)),(at(item),at(store))):
        if not reaches(source,target) or reaches(entry,target,{source}):fail('selection-dominance')
    return dict(storedOrdinalReadVa=ordinal['va'],listItemCallVa=item['va'],dialogReadVa=dialog['va'],outputStoreVa=store['va'],
        castContextLoad=cast_context,itemContextLoad=item_context,listCountReadVa=count['va'],
        storedOrdinalPassedUnchanged=True,nonnegativeAndPresentCountBoundsProved=True,selectedDialogReferenceStoredToIncomingOutput=True,
        evidenceBoundary='conditional',condition='Original ordinary path, typed compatible proxy/list/cast storage, stable disjoint frame/object storage and ordinary Win64 callees. External index conversion, live selection, IFix, playback and Story order remain separate.')
