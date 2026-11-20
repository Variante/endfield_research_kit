"""Bounded original-path identity carriers; no request delivery or cast uniqueness."""
from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.skill_timing_runtime_native import _require,_validate_fields
SCHEMA='endfield.skill-input-execution-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-input-execution-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_input_execution_native.json'
PREFIX='Beyond.Gameplay.Core.'
METHODS={'assign':('AbilityAction','AssignData',['AbilityAction+AbilityActionData','IActionEnvironment'],'void'),'reassign':('AbilityAction','ReAssign',['IActionEnvironment'],'void'),'init':('Ability','Init',['Skill','ActionGroupData','@Beyond.ActionBlackboard'],'void'),'skillCastId':('Skill','get_skillCastId',[],'uint'),'abilityInstId':('Ability','get_instId',[],'ulong')}

def _json_equal(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(b,sort_keys=True,separators=(',',':'),allow_nan=False)

def _program(role,raw,offsets,operands):
    """Recognize register/field grammar; all native operands come from typed fields."""
    d=lambda key:offsets[key].to_bytes(1,'little',signed=True)
    dispatch=bytes.fromhex('488b48')+operands['dispatchTableOffset'].to_bytes(1,'little',signed=True)
    spill=bytes.fromhex('48897c24')+operands['savedRdiStackOffset'].to_bytes(1,'little',signed=True)
    if role=='assign':
        # this RCX->R10, then original-path store R8 environment.
        return raw[:3]==bytes.fromhex('4c8bd1') and raw[3:7]==dispatch and raw[7:12]==bytes.fromhex('4885c90f85') and raw[16:19]==bytes.fromhex('498d4a') and raw[19:20]==d('environment') and raw[20:25]==bytes.fromhex('41c642')+d('executeResult')+b'\0' and raw[25:28]==bytes.fromhex('4d8942') and raw[28:29]==d('environment') and len(raw)==29
    if role=='reassign':
        return raw[:6]==bytes.fromhex('4c8bd14c8bda') and raw[6:10]==dispatch and raw[10:15]==bytes.fromhex('4885c90f85') and raw[19:22]==bytes.fromhex('498d4a') and raw[22:23]==d('environment') and raw[23:26]==bytes.fromhex('4d895a') and raw[26:27]==d('environment') and len(raw)==27
    if role=='init':
        return raw[:12]==bytes.fromhex('488bd9498bf1498be84c8bd2') and raw[12:16]==dispatch and raw[16:21]==bytes.fromhex('4885c90f85') and raw[25:28]==bytes.fromhex('488d4b') and raw[28:29]==d('sourceSkill') and raw[29:34]==spill and raw[34:37]==bytes.fromhex('4c8953') and raw[37:38]==d('sourceSkill') and len(raw)==38
    if role=='skillCastId':
        return raw==bytes.fromhex('488b41')+d('ability')+bytes.fromhex('4885c074088b40')+d('castId')+bytes.fromhex('4883c428c3')
    if role=='abilityInstId':
        return raw==bytes.fromhex('488b41')+d('sourceSkill')+bytes.fromhex('4885c0740c488b80')+struct.pack('<i',offsets['instId'])+bytes.fromhex('4883c428c3')
    return False

def _entry_bridge(role,raw,operands):
    """Entry-to-span register preservation; stack/RIP displacements stay native data."""
    if role in ('assign','reassign'):
        return len(raw)==11 and raw[:3]==bytes.fromhex('4883ec') and raw[4:7]==bytes.fromhex('488b05')
    if role=='init':
        return len(raw)==22 and raw[:4]==bytes.fromhex('48895c24') and raw[5:9]==bytes.fromhex('48896c24') and raw[10:14]==bytes.fromhex('564883ec') and raw[15:18]==bytes.fromhex('488b05')
    # Getter path changes only RAX/R9 before its conditional replacement branch.
    return len(raw)==24 and raw[:3]==bytes.fromhex('4883ec') and raw[4:7]==bytes.fromhex('488b05') and raw[11:14]==bytes.fromhex('4c8b48') and raw[14]==operands['dispatchTableOffset'] and raw[15:20]==bytes.fromhex('4d85c90f85')

def _validate(image,contract):
    cx=NativeReferenceContext(image);fields=_validate_fields(image,contract['fields']);offsets={k:v['offset']for k,v in fields.items()}
    expected={'environment':('AbilityAction','<actionEnvironment>k__BackingField','IActionEnvironment'),'sourceSkill':('Ability','<sourceSkill>k__BackingField','Skill'),'ability':('Skill','m_ability','Ability'),'castId':('Ability','skillCastId','uint'),'instId':('Skill','<instId>k__BackingField','ulong'),'executeResult':('AbilityAction','m_executeResult','bool')}
    _require(set(fields)==set(expected),'execution-field-coverage',list(expected),list(fields))
    for key,(owner,name,ty)in expected.items():
        row=fields[key];_require(type(row['offset'])is int and type(row['ordinaryKind'])is int and row['ordinaryKind']=={'uint':9,'ulong':11,'bool':2}.get(ty,18),'execution-field-kind','ordinary exact scalar/reference kind',row);_require(row['type']==PREFIX+owner and row['name']==name and row['valueType']==(ty if ty in('uint','ulong','bool')else PREFIX+ty),'execution-field-nominal',expected[key],row)
    operands=contract['reviewedOperands']
    _require(set(operands)=={'dispatchTableOffset','savedRdiStackOffset'} and all(type(v)is int and -128<=v<=127 for v in operands.values()),'execution-operand-declarations','named signed-byte operands',operands)
    chain=contract['damageActionParents'];_require(chain==[PREFIX+'AbilityAction`1<'+PREFIX+'DamageAction+DamageActionData>',PREFIX+'AbilityAction'],'execution-parent-chain','selected nominal generic DamageAction ancestry',chain);current=PREFIX+'DamageAction'
    for name in chain:_require(cx.parent(current)==name,'execution-parent',name,cx.parent(current));current=name
    _require(chain and chain[-1]==PREFIX+'AbilityAction','execution-parent-owner','AbilityAction ancestor',chain)
    methods={r['id']:r for r in contract['methods']};_require(set(methods)==set(METHODS),'execution-method-coverage',list(METHODS),list(methods))
    for role,(owner,name,params,returns)in METHODS.items():
        row=methods[role];index=image.validate_method_row(row['identity'],label='skillInputExecution');method=image.metadata.methods[index]
        actual=[cx.type_name(p.type_index)for p in image.metadata.parameters_for(method)]
        expected_params=[p[1:]if p.startswith('@')else PREFIX+p for p in params]
        _require(row['identity'][1:3]==[PREFIX+owner,name] and actual==expected_params and cx.type_name(method.return_type)==returns and not method.flags&0x10,'execution-method-signature',(owner,name,expected_params,returns),row)
    image.check_windows(contract['codeWindows'],label='skillInputExecution')
    windows={}
    for window in contract['codeWindows']:windows.setdefault(window['owner'],[]).append(window)
    spans={r['owner']:r for r in contract['spans']}
    _require(set(windows)==set(methods)==set(spans),'execution-program-coverage','one window/span per method',list(spans))
    for role,row in spans.items():
        selected=windows[role];entry=methods[role]['identity'][3];family=image.unwind_index.family(entry)
        bounds=[r['runtimeTriple'][:2]for r in family['ranges']]
        _require([[w['startRva'],w['endRva']]for w in selected]==bounds,'execution-window-owner','complete selected unwind family intervals',selected)
        raw=bytes.fromhex(row['hex']);rva=row['rva']
        _require(entry<=rva and rva-entry<=64 and _entry_bridge(role,image.pe.bytes_at_va(image.pe.image_base+entry,rva-entry),operands),'execution-entry-bridge','parameter register preserved from selected entry',role)
        cursor=rva
        for a,b in sorted(bounds):
            if a<=cursor<b:cursor=min(b,rva+len(raw))
        _require(cursor==rva+len(raw) and image.pe.bytes_at_va(image.pe.image_base+rva,len(raw))==raw and _program(role,raw,offsets,operands),'execution-program',role,row)
    rules=dict(originalPathOnly=True,actionEnvironmentMayRebind=True,abilityInitStoresSourceSkill=True,skillCastIdReadsAbilityField=True,abilityInstIdReadsSourceSkillField=True,actionEnvironmentRuntimeTypeProved=False,requestToInstanceJoinProved=False,castOccurrenceUniqueProved=False,lifetimeProved=False,synchronousAncestorCrossTickProved=False,playerInputExecutionProved=False)
    _require(_json_equal(contract['rules'],rules),'execution-rules',rules,contract['rules'])
    return rules

def load_skill_input_execution(contract_path=CONTRACT_PATH,*,gameassembly=None,metadata=None):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',nativeInputs={},rows=[],rules={},failures=[])
    try:
        contract,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='skillInputExecution');pins=contract['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        rules=_validate(open_native_image(gate.gameassembly,gate.metadata),contract)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated'and hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'execution-bookend','unchanged native/contract',after.detail)
        audit.update(status='validated',nativeInputs=dict(pins),rules=rules,rows=[dict(id='originalIdentityCarriers',evidence='conditional',rules=rules)],detail='',evidenceBoundary=contract['evidenceBoundary'])
    except(OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError,struct.error)as error:
        audit.update(status='validation_failed',detail=str(error)[:1200],nativeInputs={},rows=[],rules={});audit['failures'].append(dict(check=str(error).split(':',1)[0],detail=str(error)[:1200]))
    return audit
