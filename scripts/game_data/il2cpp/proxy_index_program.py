"""Original external-index clamp/store and old/new callback lanes."""
from scripts.game_data.il2cpp.owned_partition import BranchGrammar
from scripts.game_data.il2cpp.initializer_control import control_transfer


def check_proxy_index_program(program,refs,*,field_offset,callback):
    rows=program['rows'];origins=refs['registerOrigins'];matches=[]
    for i,row in enumerate(rows):
        if row['text']!=f'mov eax, [rcx+{field_offset:#x}]':continue
        g=BranchGrammar(rows[i:i+9],label='proxyIndex.original')
        read=g.take(f'mov eax, [rcx+{field_offset:#x}]');g.take('test edx, edx');branch=g.row();flow=control_transfer(branch)
        if flow['kind']!='conditional' or flow.get('conditionCode')!=8:g.fail('negative-input-guard','JS',branch)
        g.take('lea r8d, [rdx-0x1]');join=g.take('xor r9d, r9d');store=g.take(f'mov [rcx+{field_offset:#x}], r8d')
        g.take('mov edx, eax','add rsp, 0x28');tail=g.branch('jmp');g.finish()
        if tail['target']!=callback:g.fail('callback-target',hex(callback),tail)
        position=next((j for j,r in enumerate(rows) if int(r['va'],16)==flow['target']),None)
        if position is None:g.fail('negative-input-target','owned block',flow)
        negative=BranchGrammar(rows[position:position+2],label='proxyIndex.negative')
        negative.take('mov r8d, 0xffffffff');jump=negative.branch('jmp');negative.finish()
        if jump['target']!=int(join['va'],16):g.fail('negative-store-join',join['va'],jump)
        if any(origins[int(r['va'],16)]['rcx']!=['this'] for r in (read,store,rows[i+8])):g.fail('incoming-receiver','same this',read)
        # Other ordinary entries may reach the read, but cannot skip its value,
        # sign guard or the exact negative-input substitution before the store.
        allowed={int(r['va'],16) for r in rows[i:i+9]+rows[position:position+2]};first=int(read['va'],16)
        if any(source not in allowed and any(target in allowed-{first} for target in targets) for source,targets in program['control']['edges'].items()):g.fail('normalization-bypass','read entry only',{})
        matches.append(dict(readVa=read['va'],storeVa=store['va'],callbackTailVa=tail['va']))
    if len(matches)!=1:raise ValueError('proxyIndex.unique-original-normalization')
    return dict(matches[0],negativeInputStoredValue=-1,nonnegativeInputStoredExpression='incomingInt32 - 1',
        callbackReceivesOldAndStoredIndices=True,evidenceBoundary='conditional',
        condition='Original ordinary path, stable disjoint typed storage and ordinary returning callees. Replacement code, callback effects, packet delivery and live active selection remain separate.')
