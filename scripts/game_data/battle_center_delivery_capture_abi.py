"""Narrow ABI and physical read witnesses for the Center delivery experiment.

Only the reviewed canonical selector/executor/condition/Tick roles are admitted.
Their entry pointers do not identify a live Center instance. Reads are guarded,
bounded, non-atomic physical observations; no callback is invoked by sampling.
"""
from __future__ import annotations
import hashlib
import json
import re
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data import skill_center_dispatch_native as dispatch
from scripts.game_data import skill_center_delegate_native as delegate
from scripts.game_data import skill_center_method_info_native as method_info
from scripts.game_data import skill_center_lifecycle_native as lifecycle

SCHEMA='endfield.battle-center-delivery-capture-abi.v1'
MACHINE='Beyond.Gameplay.StateMachine`2'
STATE='Beyond.Gameplay.FSMState`1'
TRANSITION='Beyond.Gameplay.FSMTransition`1'
CONCRETE='Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterStateMachine'
ROLES={
    'tick':('battle.Delivery.Tick',MACHINE,'Tick','void',[dict(name='deltaTime',type='float')],['System.Int32Enum','object']),
    'selector':('battle.Delivery.Select',STATE,'CheckTransition',TRANSITION,[],['System.Int32Enum']),
    'executor':('battle.Delivery.Transit',TRANSITION,'Transit','void',[dict(name='curState',type=STATE)],['System.Int32Enum']),
    'condition':('battle.Delivery.Condition',TRANSITION,'CheckCondition','bool',[],['System.Int32Enum']),
    'predicate':('battle.Center.ToSkill',CONCRETE,'_ToSkill','bool',[],None),
}
READS={
    'tick':('machineCurrent','machineBlackboard','machineRunning'),
    'selector':('stateTransitions',),
    'executor':('transitionFromTo','transitionChecker','currentSlot'),
    'condition':('transitionFromTo','transitionChecker','checkerDispatch','checkerMethodCodePair','checkerMethodFlags'),
    'predicate':('methodCodePair','methodFlags'),
}
CALLERS={'selector':['battle.Delivery.Tick'],'executor':['battle.Delivery.Tick'],
         'condition':['battle.Delivery.Select']}
SOURCES={'dispatch':(dispatch.CONTRACT_PATH,dispatch.SCHEMA),
         'delegate':(delegate.CONTRACT_PATH,delegate.SCHEMA),
         'methodInfo':(method_info.CONTRACT_PATH,method_info.SCHEMA),
         'lifecycle':(lifecycle.CONTRACT_PATH,lifecycle.SCHEMA)}


def need(ok,message):
    if not ok:raise ValueError('battle_center.delivery: '+message)


def declarations():
    docs={};saved={}
    for role,(path,schema)in SOURCES.items():
        docs[role],saved[path]=read_reviewed_contract(path,schema=schema,status='reviewed',label='centerDelivery.'+role)
    pins=docs['dispatch']['nativeInputs']
    need(all(d['nativeInputs']==pins for d in docs.values()),'native declaration inputs differ')
    return docs,saved


def selected_sources(selected):
    cached=getattr(selected,'_center_delivery_sources',None)
    if cached is not None:return cached
    docs,saved=declarations();image=selected.image;pins=docs['dispatch']['nativeInputs']
    for name,data in [('GameAssembly.dll',image.pe.buf),('global-metadata.dat',image.metadata.buf)]:
        need(hashlib.sha256(data).hexdigest().upper()==pins[name].upper(),'selected native inputs differ: '+name)
    # Each validator authenticates the selected bytes, framing, ABI carriers and
    # metadata/physical field joins. A report's prior status is never admission.
    delegate._validate(image,docs['delegate'],dict(dispatch=docs['dispatch'],lifecycle=docs['lifecycle']))
    method_info._validate(image,docs['methodInfo'],docs['delegate'])
    image.check_windows(docs['lifecycle']['codeWindows'],label='centerDelivery.lifecycle')
    need(all(hashlib.sha256(p.read_bytes()).hexdigest().upper()==d for p,d in saved.items()),'declarations changed during validation')
    selected._center_delivery_sources=docs
    selected._center_delivery_bookends=saved
    return docs


def bookend(selected):
    saved=getattr(selected,'_center_delivery_bookends',{})
    need(all(hashlib.sha256(p.read_bytes()).hexdigest().upper()==d for p,d in saved.items()),'declarations changed during preparation')


def role_of(hook):
    role=hook.get('centerDeliveryRole')
    need(role in ROLES,'unknown or absent role')
    return role


def signature_matches(role,returns,params):
    expected_return=ROLES[role][3];expected_params=ROLES[role][4]
    if role=='selector':
        return isinstance(returns,str)and re.fullmatch(re.escape(expected_return)+r'<VAR\[\d+\]>',returns)is not None and params==[]
    if role=='executor':
        return returns=='void'and isinstance(params,list)and len(params)==1 and params[0].get('name')=='curState'and isinstance(params[0].get('type'),str)and re.fullmatch(re.escape(STATE)+r'<VAR\[\d+\]>',params[0]['type'])is not None
    return returns==expected_return and params==expected_params


def validate_spec(hook):
    role=role_of(hook);name,owner,method,returns,params,args=ROLES[role]
    need((hook.get('name'),hook.get('type'),hook.get('method'))==(name,owner,method)
         and signature_matches(role,hook.get('returnType'),hook.get('parameters'))
         and hook.get('static')is False and hook.get('observationMode')=='paired',
         'exact selected role/signature required')
    need(hook.get('anonymousEntry')is None and hook.get('captureIndirectCaller')is None,'anonymous/indirect substitute refused')
    expected=None if args is None else dict(classArguments=args,methodArguments=[])
    need(hook.get('genericEntry')==expected,'canonical instantiation required')
    need(hook.get('captureScope')==('paired-ancestor' if role in CALLERS else None)
         and hook.get('captureCallerHooks')==CALLERS.get(role),'exact selected direct-caller scope required')
    custom=[f for f in hook.get('fields',[])if f.get('readMode')=='centerDelivery']
    need([f.get('deliveryRead')for f in custom]==list(READS[role]),'exact bounded native read selection required')
    for f in custom:
        need(set(f)=={'label','argument','type','readMode','deliveryRead'} and f['label']==f['deliveryRead']
             and f['argument']=='native' and f['type']=='native.center-delivery.'+f['deliveryRead'],
             'custom raw field declaration differs')
    if role=='tick':
        rest=[f for f in hook['fields']if f not in custom]
        need(rest==[dict(label='deltaTime',argument='deltaTime',type='float',argumentRepresentation=dict(mode='scalarRegister',type='float'))],
             'sole original Single positional argument required')
    else:need(len(hook['fields'])==len(custom),'unexpected field outside native projection')
    return role


def _type_symbol(selected,index):
    pointer=selected.image.pe.u64_at_va(int(selected.image.registration['types'],16)+index*8)
    need(bool(pointer),'selected native type pointer missing')
    return ContextSymbols(selected.image).type(pointer)


def _generic_reference(symbol,definition,owner,byref):
    raw=bytes.fromhex(symbol.get('rawHex',''));base=symbol.get('definition',{});args=symbol.get('classArguments',[])
    need(len(raw)==16 and raw[10]==0x15 and raw[11]&0x7f==(0x20 if byref else 0)
         and base.get('name')==definition and len(args)==1,'selected generic reference declaration differs')
    base_raw=bytes.fromhex(base.get('rawHex',''))
    need(len(base_raw)==16 and base_raw[10:12]==b'\x12\0','generic definition must be reference class')
    var=bytes.fromhex(args[0].get('rawHex',''));parameter=args[0].get('parameterOwner',{})
    need(len(var)==16 and var[10:12]==b'\x13\0' and parameter.get('typeName')==owner
         and parameter.get('ordinal')==0,'exact reciprocal generic parameter owner required')


def prove_signature(selected,hook,method):
    role=validate_spec(hook);docs=selected_sources(selected)
    if role=='predicate':
        expected=docs['methodInfo']['predicate'][0]
    else:expected=next(r['methodIndex'] for r in docs['dispatch']['registrations']if r['id']==role)
    need(method.index==expected,'selected method definition differs')
    returns=_type_symbol(selected,method.return_type)
    parameters=[_type_symbol(selected,p.type_index)for p in selected.image.metadata.parameters_for(method)]
    if role=='selector':_generic_reference(returns,TRANSITION,STATE,False)
    else:
        raw=bytes.fromhex(returns['rawHex'])
        need(raw[10]==(2 if role in ('condition','predicate')else 1)and raw[11]&0x7f==0,'ordinary primitive return required')
    if role=='executor':_generic_reference(parameters[0],STATE,TRANSITION,True)
    if role=='tick':
        raw=bytes.fromhex(parameters[0]['rawHex']);need(raw[10]==12 and raw[11]&0x7f==0,'ordinary positional Single required')
    proof=dict(schema=SCHEMA,role=role,methodIndex=method.index,returnDeclaration=returns,
               parameterDeclarations=parameters,nativeInputs=docs['dispatch']['nativeInputs'],
               runtimeClosedTypeProved=False,liveCenterSelectionProved=False,atomicSnapshotProved=False)
    if not hasattr(selected,'_center_delivery_proofs'):selected._center_delivery_proofs={}
    selected._center_delivery_proofs[hook['name']]=proof
    if role=='selector':
        if not hasattr(selected,'_return_abi_proofs'):selected._return_abi_proofs={}
        selected._return_abi_proofs[hook['name']]=dict(mode='centerDeliveryReference',returnType=hook['returnType'],
            nativeTypeRecordHex=returns['rawHex'].lower(),contractSchema=SCHEMA,byref=False)
    return proof


def validate_entry(selected,hook,proof,pointer):
    role=role_of(hook);docs=selected_sources(selected)
    if role=='predicate':entry=docs['methodInfo']['predicate'][3]
    else:
        row=next(r for r in docs['dispatch']['registrations']if r['id']==role);entry=row['entryRva']
        need(proof is not None and proof.get('methodDefinitionIndices')==[row['methodIndex']]
             and proof.get('registration',{}).get('tableIndex')==row['tableIndex']
             and proof['registration'].get('indices',[None])[0]==row['pointerIndex'],
             'canonical registration/unique method definition differs')
    need(pointer-selected.image.pe.image_base==entry,'selected physical entry differs')
    if role=='predicate':
        # The nongeneric predicate is still subject to the ordinary unique
        # named-body rule; canonical generic proof is not its escape hatch.
        aliases=selected.index.names_by_pointer.get(pointer)or[]
        need({r.get('methodIndex')for r in aliases}=={docs['methodInfo']['predicate'][0]},
             'nongeneric predicate has incompatible body aliases')


def validate_caller_entry(selected,caller):
    proof=caller.get('centerDeliveryProof')or{}
    need(proof==getattr(selected,'_center_delivery_proofs',{}).get(caller.get('name')),
         'caller lacks this preparation selected role proof')
    validate_entry(selected,dict(centerDeliveryRole=proof['role']),caller.get('genericEntryProof'),
                   selected.image.pe.image_base+int(caller['rva'],16))


def geometry(docs,role,read):
    op=docs['dispatch']['operands'];slots=docs['methodInfo']['descriptorSlots']
    delegated={f['id']:f['offset']for f in docs['delegate']['fields']}
    checker=op['checkerOffset']
    hidden=len(ROLES[role][4])+1
    code_start=slots['baseCode'];code_count=slots['primaryCode']+8-code_start
    flag_start=slots['token'];flag_count=slots['flags54']+1-flag_start
    table={
      'machineCurrent':(0,op['currentOffset'],8,4097,4097),
      'machineBlackboard':(0,op['blackboardOffset'],8,4097,4097),
      'machineRunning':(0,op['runningOffset'],1,4097,4097),
      'stateTransitions':(0,op['stateTransitionsOffset'],8,4097,4097),
      'transitionFromTo':(0,op['transitionFromOffset'],op['transitionToOffset']+8-op['transitionFromOffset'],4097,4097),
      'transitionChecker':(0,checker,8,4097,4097),
      'currentSlot':(1,0,8,4097,4097),
      'methodCodePair':(hidden,code_start,code_count,4097,4097),
      'methodFlags':(hidden,flag_start,flag_count,4097,4097),
      'checkerDispatch':(0,delegated['pointer'],delegated['dispatchTarget']+8-delegated['pointer'],checker,4097),
      'checkerMethodCodePair':(0,code_start,code_count,checker,delegated['method']),
      'checkerMethodFlags':(0,flag_start,flag_count,checker,delegated['method']),
    }
    need(read in READS[role] and read in table,'read does not belong to selected role')
    arg,offset,count,c0,c1=table[read]
    need(0<count<=256 and 0<=offset<=4096 and all(x<=4097 for x in(c0,c1)),'derived native span out of bounds')
    return arg,offset,count,c0,c1


def field_descriptor(docs,role,read):
    arg,offset,count,c0,c1=geometry(docs,role,read);typename='native.center-delivery.'+read
    return dict(label=read,type=typename,valueBits=None,arg=arg,kind=6,offset=offset,chain0=c0,chain1=c1,
        byteCount=count,fieldPath=[],argumentName='native',readMode='centerDelivery',role='observation',
        observation='guarded-native-physical-bytes-not-atomic',
        argumentRepresentation=dict(mode='centerDeliveryNative',schema=SCHEMA,role=role,read=read),
        rawProof=dict(type=typename,offset=offset,byteCount=count,fields=[],
                      sourceWitness=dict(schema=SCHEMA,role=role,read=read)))


def compile_field(selected,hook,field):
    role=validate_spec(hook);docs=selected_sources(selected)
    return field_descriptor(docs,role,field['deliveryRead'])


def expected_returns(docs,role):
    c=docs['dispatch']
    if role=='selector':return sorted(r['returnRva']for r in c['callerBindings']if r['role']in('tickFirstSelector','tickSecondSelector'))
    if role=='executor':return [next(r['returnRva']for r in c['callerBindings']if r['role']=='tickTransitionRequest')]
    if role=='condition':
        spans={s['id']:s for s in c['spans']};span=spans['selectorLoop']
        raw=bytes.fromhex(span['hex']);target=c['operands']['conditionRva']
        # Decode only selected authenticated bytes, not byte-pattern address proximity.
        # The selected grammar ends with the sole condition call.
        need(len(raw)>=9 and raw[-9]==0xe8 and raw[-4:-1]==b'\x84\xc0\x74','selector condition E8 suffix differs')
        end=span['rva']+len(raw)-4
        need(end+int.from_bytes(raw[-8:-4],'little',signed=True)==target,'selector condition target differs')
        return [end]
    return []


def check_scope(hook,docs):
    proof=hook.get('centerDeliveryProof')or{};role=proof.get('role')
    if role not in CALLERS:return
    returns=expected_returns(docs,role)
    need(hook.get('captureCallerReturnRvas')==','.join(f'{r:x}'for r in returns)
         and [p.get('returnRva')for p in hook.get('captureCallerProofs',[])]==returns
         and {p.get('callerHook')for p in hook['captureCallerProofs']}==set(CALLERS[role]),
         'exact native selected caller sites required')


def validate_retained_hook(hook,profile):
    """Replay declaration/coordinate checks without treating data as live validation."""
    proof=hook.get('centerDeliveryProof')or{};role=proof.get('role')
    need(role in ROLES and proof.get('schema')==SCHEMA,'retained role proof missing')
    docs,_=declarations();name,owner,method,returns,params,args=ROLES[role]
    need(hook.get('name')==name and hook.get('symbol')==owner+'.'+method
         and signature_matches(role,hook.get('returnType'),hook.get('parameters')),'retained selected signature differs')
    pins=docs['dispatch']['nativeInputs']
    need(proof.get('nativeInputs')==pins and all(profile.get('files',{}).get(k,{}).get('sha256','').upper()==pins[n].upper()
         for k,n in [('gameAssembly','GameAssembly.dll'),('metadata','global-metadata.dat')]),'retained native input pair differs')
    need(all(proof.get(k)is False for k in ('runtimeClosedTypeProved','liveCenterSelectionProved','atomicSnapshotProved')),
         'retained runtime boundary changed')
    row=next((r for r in docs['dispatch']['registrations']if r['id']==role),None)
    mi=docs['methodInfo']['predicate'][0]if role=='predicate'else row['methodIndex']
    rva=docs['methodInfo']['predicate'][3]if role=='predicate'else row['entryRva']
    need(hook.get('methodIndex')==proof.get('methodIndex')==mi and hook.get('rva')==hex(rva),'retained role definition/entry differs')
    if row:
        generic=hook.get('genericEntryProof')or{}
        need(generic.get('methodDefinitionIndices')==[mi]and generic.get('registration',{}).get('tableIndex')==row['tableIndex']
             and generic.get('registration',{}).get('indices',[None])[0]==row['pointerIndex']
             and generic.get('methodSpecIndex')==row['methodSpecIndex']
             and generic.get('registration',{}).get('methodSpecIndex')==row['methodSpecIndex'],'retained exact registration differs')
    declaration=proof.get('returnDeclaration')or{}
    need(declaration.get('name')==hook.get('returnType'),'retained return symbol differs')
    if role=='selector':_generic_reference(declaration,TRANSITION,STATE,False)
    else:
        raw=bytes.fromhex(declaration.get('rawHex',''));need(len(raw)==16 and raw[10]==(2 if role in('condition','predicate')else 1)
             and raw[11]&0x7f==0,'retained ordinary return differs')
    parameters=proof.get('parameterDeclarations')
    need(isinstance(parameters,list)and len(parameters)==len(params),'retained parameter declaration count differs')
    need(all(p.get('name')==declared.get('type')for p,declared in zip(parameters,hook['parameters'])),
         'retained parameter type symbol differs')
    if role=='executor':_generic_reference(parameters[0],STATE,TRANSITION,True)
    if role=='tick':
        raw=bytes.fromhex(parameters[0].get('rawHex',''));need(len(raw)==16 and raw[10]==12 and raw[11]&0x7f==0,'retained Single declaration differs')
    expected=[field_descriptor(docs,role,r)for r in READS[role]]
    actual=[f for f in hook.get('fields',[])if f.get('readMode')=='centerDelivery']
    need(actual==expected,'retained exact physical read descriptor differs')
    need(hook.get('captureScope')==('paired-ancestor'if role in CALLERS else None),'retained scope policy differs')
    expected_abi={'tick':'win64.paired_float_slot1_void_3.v1',
        'selector':'win64.scoped_paired_gp_pointer_2.v1','executor':'win64.scoped_paired_gp_void_3.v1',
        'condition':'win64.scoped_paired_gp_bool_2.v1','predicate':'win64.paired_gp_bool_2.v1'}[role]
    need(hook.get('abiId')==expected_abi,'retained exact ABI role differs')
    need(profile.get('recipeSchema')=='endfield.mission-trace-capture-recipe.v17','retained native reads require v17')
    check_scope(hook,docs)
    return True


def validate_retained_profile(profile):
    """Offline declaration admission only; no fabricated session or observations."""
    hooks=profile.get('missionTraceHooks',[])
    recipe=json.loads((CONTRACTS_DIR/'battle_center_delivery_capture.json').read_text(encoding='utf-8'))
    need(isinstance(recipe,dict) and recipe.get('schema')=='endfield.mission-trace-capture-recipe.v17'
         and recipe.get('status')=='reviewed','reviewed recipe schema/status required')
    declared=recipe.get('hooks')
    need(isinstance(declared,list) and bool(declared)
         and all(isinstance(h,dict) and isinstance(h.get('name'),str) and bool(h['name']) for h in declared)
         and len({h['name']for h in declared})==len(declared),'reviewed recipe requires nonempty unique hook declarations')
    specs={h['name']:h for h in recipe['hooks']}
    expected=set(specs)
    need(isinstance(hooks,list)and all(isinstance(h,dict)for h in hooks)
         and profile.get('centerDeliveryProfile')==SCHEMA and len(hooks)==len(expected)
         and {h.get('name')for h in hooks}==expected,'exact retained delivery profile required')
    need(profile.get('schema')=='endfieldCapture.missionTraceBuild.v2'
         and profile.get('observerProviders')==['mission-trace']and profile.get('providerMask')==128,
         'retained bounded mission-only provider required')
    for hook in hooks:
        spec=specs[hook['name']]
        need(hook.get('symbol')==spec['type']+'.'+spec['method']
             and hook.get('returnType')==spec['returnType'] and hook.get('parameters')==spec['parameters']
             and hook.get('observationMode')==spec['observationMode']
             and hook.get('captureScope')==spec.get('captureScope'),
             'retained reviewed signature/scope differs: '+hook['name'])
        need({p.get('callerHook')for p in hook.get('captureCallerProofs',[])}==set(spec.get('captureCallerHooks',[])),
             'retained reviewed caller selection differs: '+hook['name'])
        fields=hook.get('fields',[])
        need([f.get('label')for f in fields]==[f['label']for f in spec['fields']],
             'retained reviewed field selection differs: '+hook['name'])
        for field,declared in zip(fields,spec['fields']):
            if declared.get('readMode')=='centerDelivery':continue
            need(field.get('type')==declared['type'] and field.get('argumentName')==declared['argument']
                 and field.get('role')==declared.get('role','observation')
                 and field.get('readMode')==declared.get('readMode')
                 and field.get('valueRepresentation')==declared.get('valueRepresentation')
                 and [(p.get('field'),p.get('type'))for p in field.get('fieldPath',[])]
                     ==[(p['field'],p['type'])for p in declared.get('path',[])],
                 'retained reviewed field declaration differs: '+hook['name']+'.'+declared['label'])
            if declared.get('readMode')=='rawBytes':
                need(field.get('byteCount')==declared['byteCount'],'retained raw span differs')
            representation=declared.get('argumentRepresentation')
            if representation:
                need(all((field.get('argumentRepresentation')or{}).get(k)==v for k,v in representation.items()),
                     'retained argument representation differs')
        if hook['name']in {r[0]for r in ROLES.values()}:validate_retained_hook(hook,profile)
        else:need(not hook.get('centerDeliveryProof')and not any(f.get('readMode')=='centerDelivery'for f in hook.get('fields',[])),
                  'native read role attached to an unproved method')
    return True


def validate_retained_field(field,hook):
    proof=hook.get('centerDeliveryProof')or{};role=proof.get('role');read=(field.get('rawProof')or{}).get('sourceWitness',{}).get('read')
    docs,_=declarations()
    need(role in ROLES and field==field_descriptor(docs,role,read),'retained bounded native field differs')


def validate_retained_return(hook,profile):
    validate_retained_hook(hook,profile)
    p=hook.get('returnAbiProof')or{};decl=hook['centerDeliveryProof']['returnDeclaration']
    need(p.get('mode')=='centerDeliveryReference'and p.get('contractSchema')==SCHEMA
         and p.get('returnType')==hook['returnType']and p.get('nativeTypeRecordHex')==decl['rawHex'].lower()
         and p.get('returnObserved')is True and p.get('pointeeRead')is False and p.get('byref')is False,
         'retained selected reference-return proof differs')
    return True
