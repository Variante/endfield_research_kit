"""Check selected cast-identity field and branch projections in closed consumers.

The caller authenticates names, field types/offsets and enum literals. These
programs prove conditional static paths; patch returns and callee effects are
not substituted with fabricated values.
"""
from .consumer_control import check_consumer_control
from .consumer_reference_origins import check_reference_origins
from .initializer_control import control_transfer
from .memory_moves import decode_memory_move
from .initializer_instructions import decode_initializer_move
from .scalar_double_memory import decode_scalar_double_memory_move
from .owned_partition import BranchGrammar

LABEL='selectorIdentityProgram'

def _at(row):return int(row['va'],16)

def _grammar(rows):
    if any(_at(a)+len(bytes.fromhex(a['bytes']))!=_at(b) for a,b in zip(rows,rows[1:])):
        raise ValueError(LABEL+'.projection-contiguity')
    return BranchGrammar(rows,label=LABEL)

def _load(g,decoder,register,base,offset,width):
    row=g.row();raw=bytes.fromhex(row['bytes']);decoded=decoder(raw,0,_at(row))
    fact=decoded[0].get('memoryOperation',{}) if decoded and decoded[1]==len(raw) else {}
    address=fact.get('address',{})
    if (fact.get('direction'),fact.get('register'),fact.get('memoryBytes'),address.get('base'),address.get('index'),address.get('ripRelative'),address.get('displacement'))!=('load',register,width,base,None,False,offset):
        g.fail('typed-load',(register,base,offset,width),fact)
    return row

def _unique_position(rows,predicate,label):
    positions=[i for i,r in enumerate(rows) if predicate(r)]
    if len(positions)!=1:raise ValueError(LABEL+'.unique-'+label+':'+str(len(positions)))
    return positions[0]

def _branch_target(rows,i,code):
    flow=control_transfer(rows[i])
    if flow['kind']!='conditional' or flow['conditionCode']!=code:raise ValueError(LABEL+'.branch-predicate')
    return flow['target']

def _entry_edges(control,block,allowed):
    interior={_at(r) for r in block[1:]};inside={_at(r) for r in block}
    for site,targets in control['edges'].items():
        if site not in inside and any(target in interior and target not in allowed for target in targets):
            raise ValueError(LABEL+'.projection-entry-bypass')

def check_selector_identity_program(rows,*,entry,owned_ranges,calls,targets,fields,
        owner_register,action_stack_slot,ability_entity_literal,getter_rows,getter_entry,getter_ranges):
    control=check_consumer_control(rows,entry=entry,owned_ranges=owned_ranges)
    origins=check_reference_origins(rows,entry=entry,owned_ranges=owned_ranges,
        incoming_registers={owner_register:'parameter:owner'},
        incoming_stack_slots={action_stack_slot:'parameter:abilityAction'},
        selected_call_returns={calls['lock']:'return:Lock'})['registerOrigins']
    positions={role:_unique_position(rows,lambda r:_at(r)==site,role) for role,site in calls.items()}
    clear_start=_at(rows[positions['clear']-7]);remove_start=_at(rows[positions['remove']-3])
    step_i=_unique_position(rows,lambda r:r['bytes']=='83 eb 01' and
        (_at(r)+3 in { _at(n) for n in rows if control_transfer(n).get('conditionCode')==9}),'signed-step')
    step=_at(rows[step_i]);step_flow=control_transfer(rows[step_i+1])
    if step_flow['conditionCode']!=9:raise ValueError(LABEL+'.signed-step-predicate')
    trap_i=_unique_position(rows,lambda r:r['bytes']=='cc','caller-trap')
    trap=_at(rows[trap_i-1])
    if control_transfer(rows[trap_i-1])['kind']!='call':raise ValueError(LABEL+'.trap-entry')
    clear_block=rows[positions['clear']-7:positions['clear']+1];g=_grammar(clear_block)
    load=g.row();decoded=decode_memory_move(bytes.fromhex(load['bytes']),0,_at(load))
    fact=decoded[0].get('memoryOperation',{}) if decoded and decoded[1]==len(bytes.fromhex(load['bytes'])) else {};address=fact.get('address',{})
    if (fact.get('direction'),fact.get('register'),fact.get('memoryBytes'),address.get('base'),address.get('index'),address.get('ripRelative'))!=('load','rcx',8,'rsp',None,False):
        g.fail('clear-reference-load','stack QWORD to RCX',load)
    g.labels['trap']=trap;g.take('test rcx, rcx');g.branch('je','trap')
    for expected in ('41 b1 01','48 c7 44 24 20 00 00 00 00','45 0f b6 c1','41 0f b6 d1'):
        row=g.row()
        if row['bytes']!=expected:g.fail('clear-literal-argument',expected,row)
    g.call(targets['clear']);g.finish();_entry_edges(control,clear_block,set())
    remove_block=rows[positions['remove']-3:positions['remove']+1];g=_grammar(remove_block)
    for expected in ('45 33 c0','49 8b d6','48 8b cf'):
        row=g.row()
        if row['bytes']!=expected:g.fail('remove-reference-argument',expected,row)
    g.call(targets['remove']);g.finish();_entry_edges(control,remove_block,set())
    expected_i=_unique_position(rows,lambda r:r['bytes']=='85 ed','expected-zero-test')
    if _branch_target(rows,expected_i+1,4)!=clear_start:raise ValueError(LABEL+'.expected-zero-clear-join')
    # The non-null locked reference reaches both the type getter and entity load.
    type_i=positions['objectType'];null_block=rows[type_i-4:type_i+3];g=_grammar(null_block)
    g.labels.update(step=step,remove=remove_start)
    g.take('test rax, rax');g.branch('je','step');g.take('xor edx, edx','mov rcx, rax');g.call(targets['objectType'])
    compare=g.row()
    if bytes.fromhex(compare['bytes'])!=b'\x3d'+ability_entity_literal.to_bytes(4,'little',signed=True):g.fail('object-type-compare',ability_entity_literal,compare)
    g.branch('jne','remove');g.finish()
    if origins[calls['objectType']]['rcx']!=['return:Lock']:raise ValueError(LABEL+'.type-getter-receiver')
    first_i=type_i+3;candidate=rows[first_i:first_i+17];g=_grammar(candidate)
    g.labels.update(trap=trap,remove=remove_start)
    if origins[_at(candidate[0])]['r14']!=['return:Lock']:raise ValueError(LABEL+'.entity-receiver-origin')
    _load(g,decode_memory_move,'rsi','r14',fields['entity'],8)
    g.take('test rsi, rsi');g.branch('je','trap')
    _load(g,decode_memory_move,'rsi','rsi',fields['controller'],8)
    g.take('test rsi, rsi');g.branch('je','trap')
    g.take('xor edx, edx');guard_id=g.pattern(r'mov ecx, 0x[0-9a-f]+')
    g.call(targets['isPatched']);g.take('test al, al');patch=g.branch('jne')
    _load(g,decode_initializer_move,'xmm1','rsi',fields['castInfo'],16)
    _load(g,decode_scalar_double_memory_move,'xmm0','rsi',fields['castInfo']+16,8)
    transfer=g.take('movd eax, xmm1')
    if transfer['bytes']!='66 0f 7e c8':g.fail('candidate-low-dword-transfer','66 0f 7e c8',transfer)
    g.pattern(r'movsd \[rsp\+0x[0-9a-f]+\], xmm0');compare=g.take('cmp eax, ebp')
    if compare['bytes']!='3b c5':g.fail('candidate-expected-dword-compare','3b c5',compare)
    g.branch('jne','remove');g.finish()
    _entry_edges(control,candidate,{_at(transfer)})
    # The owner fallback reads curSkill, and a null skill selects Clear.
    skill_i=positions['skillCastId'];fallback=rows[skill_i-6:skill_i+3];g=_grammar(fallback)
    g.labels.update(trap=trap,clear=clear_start,expected=_at(rows[expected_i]))
    g.take('test rbp, rbp');g.branch('je','trap')
    load=_load(g,decode_memory_move,'rcx','rbp',fields['curSkill'],8)
    if origins[_at(load)]['rbp']!=['parameter:owner']:raise ValueError(LABEL+'.fallback-owner-origin')
    g.take('test rcx, rcx');g.branch('je','clear');g.take('xor edx, edx');g.call(targets['skillCastId'])
    scalar=g.take('mov ebp, eax')
    if scalar['bytes']!='8b e8':g.fail('fallback-uint-result','8b e8',scalar)
    g.branch('jmp','expected');g.finish();_entry_edges(control,fallback,set())
    # This branch is selected by the incoming abilityAction being null.
    action_i=_unique_position(rows,lambda r:r['text']=='test rdx, rdx' and
        control_transfer(rows[rows.index(r)+1]).get('target')==_at(fallback[0]),'action-null')
    if origins[_at(rows[action_i])]['rdx']!=['parameter:abilityAction'] or _branch_target(rows,action_i+1,4)!=_at(fallback[0]):
        raise ValueError(LABEL+'.action-null-fallback-origin')
    getter_control=check_consumer_control(getter_rows,entry=getter_entry,owned_ranges=getter_ranges)
    getter_origins=check_reference_origins(getter_rows,entry=getter_entry,owned_ranges=getter_ranges,
        incoming_registers={'rcx':'parameter:this'},incoming_stack_slots={},selected_call_returns={})['registerOrigins']
    def getter_load(row):
        raw=bytes.fromhex(row['bytes']);d=decode_memory_move(raw,0,_at(row))
        f=d[0].get('memoryOperation',{}) if d and d[1]==len(raw) else {};a=f.get('address',{})
        return (f.get('direction'),f.get('register'),a.get('base'),a.get('displacement'))==('load','rax','rbx',fields['ability'])
    getter_i=_unique_position(getter_rows,getter_load,'getter-ability-load')
    projection=getter_rows[getter_i-4:getter_i+7];g=_grammar(projection)
    getter_trap_i=_unique_position(getter_rows,lambda r:r['bytes']=='cc','getter-trap')
    g.labels['trap']=_at(getter_rows[getter_trap_i-1])
    g.pattern(r'mov ecx, 0x[0-9a-f]+');g.call(targets['isPatched']);g.take('test al, al');getter_patch=g.branch('jne')
    load=_load(g,decode_memory_move,'rax','rbx',fields['ability'],8)
    if getter_origins[_at(load)]['rbx']!=['parameter:this']:raise ValueError(LABEL+'.getter-receiver-origin')
    g.take('test rax, rax');g.branch('je','trap')
    _load(g,decode_memory_move,'eax','rax',fields['abilityCastId'],4)
    g.take('add rsp, 0x20','pop rbx','ret');g.finish()
    _entry_edges(getter_control,projection,{_at(projection[-3])})
    return {'callerInstructionsChecked':len(rows),'getterInstructionsChecked':len(getter_rows),
        'candidateFieldReadSite':_at(candidate[0]),'candidateInnerPatchBranch':patch,
        'candidateGuardIdInstruction':guard_id,'getterPatchBranch':getter_patch,
        'objectTypeMismatchCallsRemoveTarget':True,'candidateDwordMismatchCallsRemoveTarget':True,
        'expectedDwordZeroSelectsClearPath':True,'nullCurrentSkillSelectsClearPathOnNullActionFallback':True,
        'clearPathRequiresNonNullHandleOtherwiseTraps':True,
        'nullLockSkipsRemovalAndSteps':True,'signedDwordDecrementBackedge':step_flow,
        'evidenceBoundary':'conditional','runtimeExecutionKnown':False,
        'unresolved':['abilityAction helper result type and source','patched candidate/getter results','opaque callee effects','Selector invocation','live values and branch outcomes']}
