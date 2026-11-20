"""Selected-build ABI witness for the named damage capture root."""
from __future__ import annotations

import hashlib
import struct

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.damage_process_formula_native import validate_windows
from scripts.game_data.il2cpp.native_image import read_reviewed_contract

CONTRACT = CONTRACTS_DIR / 'damage_runtime_branch_abi_native.json'
SCHEMA = 'endfield.damage-runtime-branch-abi-native-contract.v3'


def selected_contract(selected):
    from scripts.game_data.mission_trace_capture_prepare import PreparationError
    cached = getattr(selected, '_damage_branch_abi_contract', None)
    if cached is not None:
        return cached
    contract, _ = read_reviewed_contract(CONTRACT, schema=SCHEMA,
                                         label='damage_branch_abi', status='reviewed')
    image = selected.image
    for key, raw in (('gameAssemblySha256', image.pe.buf), ('metadataSha256', image.metadata.buf)):
        if hashlib.sha256(raw).hexdigest().lower() != contract['nativeInputs'][key].lower():
            raise PreparationError('damage_branch.abi: selected native input mismatch: ' + key)
    failures = validate_windows(image, contract)
    if failures:
        raise PreparationError('damage_branch.abi: reviewed native window mismatch: ' + str(failures[0]))
    part=contract.get('returnedPart')
    if part is not None and (not part.get('requiredWindows') or not set(part['requiredWindows']) <= {w['name'] for w in contract['windows']}):
        raise PreparationError('damage_branch.lock: required reviewed consumer windows missing')
    declarations=[contract.get('moduleSelector')]+contract.get('callbackCandidates',[])
    for declaration in declarations:
        if declaration is not None and (not declaration.get('requiredWindows') or not set(declaration['requiredWindows']) <= {w['name']for w in contract['windows']}):
            raise PreparationError('damage_branch.selector: required reviewed windows missing')
    selected._damage_branch_abi_contract = contract
    return contract


def validate_damage_branch_abi(selected, hook, parameter):
    """Use reviewed native consumers, never an arbitrary byte-pattern match."""
    from scripts.game_data.mission_trace_capture_prepare import PreparationError

    if (hook['type'], hook['method'], parameter['name'], parameter['type']) != (
            'Beyond.Gameplay.Core.DamageAction', '_ProcessDamage', 'transferredSource',
            'Beyond.ObjectPtr`1<Beyond.Gameplay.Core.AbilitySystem>'):
        raise PreparationError('damage_branch.abi: no reviewed native argument witness')
    contract = selected_contract(selected)
    image = selected.image
    witness = contract.get('captureAbi')
    if not isinstance(witness, dict) or witness.get('parameter') != parameter['name']:
        raise PreparationError('damage_branch.abi: reviewed native consumer declaration missing')
    _, _, entry = selected.resolve(hook)
    if entry - image.pe.image_base != int(witness['entryRva'], 16):
        raise PreparationError('damage_branch.abi: selected named entry differs')
    required = set(witness['requiredWindows'])
    if not required or not required <= {row['name'] for row in contract['windows']}:
        raise PreparationError('damage_branch.abi: required native windows missing')
    return dict(contractSchema=SCHEMA, **witness)


def prove_damage_lock_signature(selected, hook, method):
    from scripts.game_data.mission_trace_capture_prepare import PreparationError
    contract = selected_contract(selected); spec = contract['returnedPart']
    if (hook.get('name'), hook.get('type'), hook.get('method'), hook.get('returnType'), hook.get('static'), hook.get('parameters'), hook.get('genericEntry')) != (
            spec['hook'], spec['type'], spec['method'], spec['returnType'], False, [], dict(classArguments=spec['classArguments'], methodArguments=spec['methodArguments'])):
        raise PreparationError('damage_branch.lock: exact reviewed generic signature required')
    pe = selected.image.pe; metadata = selected.image.metadata
    pointer = pe.u64_at_va(int(selected.image.registration['types'], 16)+method.return_type*8)
    raw = pe.bytes_at_va(pointer, 16)
    td = selected.index.types[spec['type']]
    section = metadata.sections['genericContainers']
    owner, count, is_method, parameter = struct.unpack_from('<iiii', metadata.buf, section.offset+td.generic_container_index*16)
    if (raw[10] != 0x13 or raw[11]&0x7f or int.from_bytes(raw[:8],'little') != parameter
            or owner != td.index or count != 1 or is_method != 0 or method.parameter_count):
        raise PreparationError('damage_branch.lock: selected sole class VAR reference return differs')
    return dict(mode='selectedSharedGenericReference', returnType=spec['returnType'], closedReturnType=spec['closedReturnType'],
                nativeTypeRecordHex=raw.hex(), nativeTypeIndex=method.return_type, byref=False,
                sharedNativeEntryRva=spec['entryRva'], contractSchema=SCHEMA,
                evidence='Selected class VAR, registered Object reference instantiation and reviewed native RAX pointer/null return; runtime constructed receiver identity is not inferred')


def damage_lock_caller_returns(selected):
    return [int(x,16) for x in selected_contract(selected)['returnedPart']['callerReturnRvas']]


def compile_returned_part(selected, hook, field):
    from scripts.game_data.mission_trace_capture_prepare import PreparationError
    contract=selected_contract(selected); spec=contract['returnedPart']; image=selected.image
    if (hook.get('name')!=spec['hook'] or field.get('argument')!='returnValue' or field.get('type')!=spec['classType']
            or field.get('readMode')!='returnedExactClass' or field.get('path') or hook.get('captureCallerHooks')!=['damage.Action.ProcessDamage']):
        raise PreparationError('damage_branch.return: exact selected returned-part observer required')
    if not selected.is_owner(spec['classType'],spec['uidField'].split('::')[0]):
        raise PreparationError('damage_branch.return: UID owner is not an ancestor of selected EnemyPart')
    if selected.field(spec['uidField'])[1:] != ('uint',spec['uidOffset']) or selected.field(spec['ratioField'])[1:] != ('float',spec['ratioOffset']):
        raise PreparationError('damage_branch.return: selected UID/ratio metadata layout differs')
    from scripts.game_data.il2cpp.context import unresolved_usage_index
    cell=int(spec['classInfoRva'],16); raw=image.pe.bytes_at_va(image.pe.image_base+cell,8)
    type_index=unresolved_usage_index(raw,image.registration['typesCount'],tag=1,source='damageReturnedPart',offset=cell)
    if selected.type_name(type_index)!=spec['classType']:
        raise PreparationError('damage_branch.return: selected ClassInfo identity differs')
    header=struct.unpack_from('<I',image.pe.buf,0x3c)[0]
    image_bytes=struct.unpack_from('<I',image.pe.buf,header+24+56)[0]
    if not 0<cell<=image_bytes-8:
        raise PreparationError('damage_branch.return: ClassInfo cell outside selected module')
    return dict(label=field['label'],type=field['type'],valueBits=None,arg=0,kind=9,offset=0,chain0=4097,chain1=4097,
        classInfoRva=cell,uidOffset=spec['uidOffset'],ratioOffset=spec['ratioOffset'],imageBytes=image_bytes,
        byteCount=32,fieldPath=[],argumentName='returnValue',role=field.get('role','observation'),readMode='returnedExactClass',
        rawProof=dict(type=field['type'],offset=0,byteCount=32,fields=[],sourceWitness=dict(schema=SCHEMA,hook=spec['hook'],classType=spec['classType'],uidField=spec['uidField'],ratioField=spec['ratioField'],classInfoTypeIndex=type_index)),
        observation='original-normal-return; exact-class predicate; expected non-admission states carry no numeric ratio')


def resolve_damage_lock_entry(selected, hook, method):
    from scripts.game_data.mission_trace_capture_prepare import PreparationError
    spec=selected_contract(selected)['returnedPart']; pointer=selected.image.pe.image_base+int(spec['entryRva'],16)
    aliases=selected.index.names_by_pointer.get(pointer,[])
    matches=[row for row in aliases if row.get('genericInstantiation')is True
        and row.get('methodIndex')==method.index and row.get('type')==spec['type'] and row.get('method')==spec['method']
        and [a.get('typeName')for a in row.get('classInstantiation',{}).get('arguments',[])]==['System.Object']
        and row.get('methodInstantiation',{}).get('arguments')==[] and row.get('methodInstantiation',{}).get('genericInstIndex')==-1]
    if len(matches)!=1 or {r.get('methodIndex')for r in aliases}!={method.index}:
        raise PreparationError('damage_branch.lock: selected Object reference registration/unique method entry differs')
    row=matches[0]
    return dict(pointer=pointer,methodSpecIndex=row['methodSpecIndex'],genericMethodPointerSlot=row['genericMethodPointerSlot'],
        classInstantiation=row['classInstantiation'],methodInstantiation=row['methodInstantiation'],methodDefinitionIndices=[method.index],
        boundary='Selected normal shared generic function pointer; adjustor thunk entry is not hooked or inferred. Actual runtime MethodInfo/closed receiver remain unobserved.')


def compile_module_selector(selected, hook, field):
    from scripts.game_data.mission_trace_capture_prepare import PreparationError
    spec=selected_contract(selected)['moduleSelector'];image=selected.image
    if (hook.get('name')!=spec['hook'] or hook.get('observationMode')!='paired' or field.get('argument')!='module'
            or field.get('type')!='damage.defenderPoiseFactor.moduleSelector' or field.get('path')
            or spec['receiverOffset']!=spec['functionOffset']+8):
        raise PreparationError('damage_branch.selector: exact Process module selector required')
    header=struct.unpack_from('<I',image.pe.buf,0x3c)[0]
    size=struct.unpack_from('<I',image.pe.buf,header+24+56)[0];root=int(spec['rootRva'],16)
    if not 0<root<=size-8 or not 0<=spec['tableOffset']<=65528 or not 0<=spec['functionOffset']<=65520:
        raise PreparationError('damage_branch.selector: selected module/indirect read bounds differ')
    return dict(label=field['label'],type=field['type'],valueBits=None,arg=0,kind=10,offset=0,chain0=4097,chain1=4097,
        rootRva=root,tableOffset=spec['tableOffset'],functionOffset=spec['functionOffset'],imageBytes=size,
        byteCount=64,fieldPath=[],argumentName='module',role=field.get('role','observation'),readMode='moduleCallbackSelector',
        rawProof=dict(type=field['type'],offset=0,byteCount=64,fields=[],sourceWitness=dict(schema=SCHEMA,hook=spec['hook'],logicalGetter=spec['logicalGetter'])),
        observation='two physical selector reads at entry/normal-return; actual arithmetic selection and factor remain unobserved')


def callback_candidate_spec(selected, hook):
    from scripts.game_data.mission_trace_capture_prepare import PreparationError
    contract=selected_contract(selected)
    matches=[c for c in contract['callbackCandidates']if c['hook']==hook.get('name')]
    if len(matches)!=1:
        raise PreparationError('damage_branch.callback: no exact reviewed candidate')
    spec=matches[0]
    keys=('type','method','declaringImage','returnType','static','parameters')
    if (any(hook.get(k)!=spec[k]for k in keys) or hook.get('captureIndirectCaller')!='damage.defenderPoiseFactor'
            or hook.get('fields')!=[] or hook.get('opaqueByRefArguments')!=['P0']
            or hook.get('observationMode')!='paired' or hook.get('captureScope')!='paired-ancestor'
            or hook.get('captureCallerHooks')!=['damage.Action.ProcessDamage']):
        raise PreparationError('damage_branch.callback: candidate image/signature/indirect scope differs')
    return spec


def indirect_callback_proofs(selected, spec, target, caller, family, rows):
    from scripts.game_data.mission_trace_capture_prepare import PreparationError
    candidate=callback_candidate_spec(selected,spec);selector=selected_contract(selected)['moduleSelector']
    call=int(selector['callRva'],16);ret=int(selector['returnRva'],16);expected=bytes.fromhex(selector['callBytes'])
    target_rva=int(target['rva'],16)
    if target_rva!=int(candidate['entryRva'],16) or ret!=call+2 or expected!=b'\xff\xd0':
        raise PreparationError('damage_branch.callback: selected candidate target or indirect call declaration differs')
    matches=[(row,window)for row,window in rows if int(row['va'],16)-selected.image.pe.image_base==call]
    if len(matches)!=1 or bytes.fromhex(matches[0][0]['bytes'])!=expected or matches[0][1]is None:
        raise PreparationError('damage_branch.callback: reviewed indirect CALL RAX site missing')
    window=matches[0][1]
    return [dict(callerHook=caller['name'],callerMethodIndex=caller['methodIndex'],callerBodySha256=caller['bodySha256'],
        callRva=call,returnRva=ret,callBytes=expected.hex(),targetRva=target_rva,callKind='indirectCandidate',targetSelectionObserved=False,
        callerSourceFamilyIndex=0,callerWindowStartRva=window['startRva'],callerWindowEndRva=window['endRva'],callerWindowSha256=window['sha256'])]
