"""Bounded original combo registration, mapping and interrupt predicates.

This authenticates explicit selected native inputs and reviewed control paths.
Typed collection requests retain normal-return/storage conditions; their names
do not turn the resulting interrupt predicate into complete input acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.skill_timing_runtime_native import _require, _validate_fields

SCHEMA='endfield.skill-combo-acceptance-native-contract.v3'
AUDIT_SCHEMA='endfield.skill-combo-acceptance-native-audit.v3'
CONTRACT_PATH=CONTRACTS_DIR/'skill_combo_acceptance_native.json'
LABEL='skillComboAcceptance'
ORDER=('noCurrentSkill','allowedPackContains','plungingStartEquals','plungingEndEquals',
       'newPrioritySignedGreater','currentCanInterrupt')


def _rule_scope(contract):
    rules=contract['rules']
    _require(contract['orderedPredicates']==list(ORDER) and rules['interruptPredicateOrder']==list(ORDER),
             'combo-predicate-order',list(ORDER),contract.get('orderedPredicates'))
    _require(rules['originalPathOnly'] is True and rules['completePlayerInputAcceptanceProved'] is False
             and rules['priorityComparison']=='signedInt32StrictGreaterThan'
             and rules['equalPriorityFallsThroughToCurrentGetter'] is True
             and rules['objectPtrSuffixWholeLayoutProved'] is True
             and rules['allowNextActionClosedDataSlotProved'] is True
             and rules['objectPtrAllInstantiationsLayoutProved'] is False,
             'combo-rule-boundary','original conditional predicate with selected witness only',rules)
    facts={row['id']:row for row in contract['facts']}
    required_facts={'orderedInterruptPredicate','allowedPackInitialization','allowedPackRegistrationRemoval',
        'effectiveMappingRefresh','mappingRemovalRefresh','normalAttackOuterPredicate','allowNextStoredArgumentBridge',
        'mappingHandleCleanup','allowNextHandleCleanup','allowNextClosedDataSlot','mappingPayload24'}
    _require(len(facts)==len(contract['facts']) and set(facts)==required_facts,
             'combo-fact-coverage',sorted(required_facts),sorted(facts))
    _require(facts['orderedInterruptPredicate']['orderedPredicates']==list(ORDER),
             'combo-fact-order','distinct facts and ordered conditional predicate',list(facts))
    for fact,rule in [('allowedPackInitialization','allowedPackInit'),('effectiveMappingRefresh','mappingRefresh'),
                      ('mappingRemovalRefresh','mappingRemove'),('mappingHandleCleanup','mappingHandleCleanup'),
                      ('allowNextHandleCleanup','allowNextHandleCleanup')]:
        _require(facts[fact]['rule']==rules[rule],'combo-rule-fact-binding',rules[rule],facts[fact].get('rule'))
    _require(all(row['evidence']=='conditional' and row['boundary'] for row in facts.values()),
             'combo-fact-boundaries','conditional bounded facts',list(facts))
    return rules


def _branch(raw,rva):
    conditions={0x74:'equal',0x75:'notEqual',0x79:'nonNegative',0x7c:'signedLess',0x7f:'signedGreater'}
    if len(raw)==2 and raw[0] in conditions:
        return conditions[raw[0]],rva+2+int.from_bytes(raw[1:],'little',signed=True)
    if len(raw)==6 and raw[0]==0x0f and raw[1]-0x10 in conditions:
        return conditions[raw[1]-0x10],rva+6+struct.unpack_from('<i',raw,2)[0]
    raise ValueError(LABEL+'.conditional-branch-encoding')


def _written_register(raw):
    """Finite straight-line MOV/LEA/XOR/SIMD setup instructions only."""
    registers=('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15')
    at=0;rex=0;simd=False;immediate=0
    if raw and raw[0]in(0xf2,0xf3):at+=1;simd=True
    if at<len(raw)and 0x40<=raw[at]<=0x4f:rex=raw[at];at+=1
    _require(at<len(raw),'combo-setup-opcode','bounded instruction',raw.hex())
    opcode=raw[at];at+=1
    if opcode==0x0f:
        _require(at<len(raw)and raw[at]in(0x10,0x11,0x28,0x29,0xc6),
                 'combo-setup-simd','MOV/SHUF setup only',raw.hex())
        immediate=int(raw[at]==0xc6);at+=1;simd=True
    else:_require(not simd and opcode in(0x8b,0x89,0x8d,0x33),'combo-setup-opcode','MOV/LEA/XOR',raw.hex())
    _require(at<len(raw),'combo-setup-modrm','complete ModRM',raw.hex())
    modrm=raw[at];at+=1;mod=modrm>>6;rm=modrm&7
    if mod!=3 and rm==4:
        _require(at<len(raw),'combo-setup-sib','complete SIB',raw.hex())
        sib=raw[at];at+=1
        if mod==0 and sib&7==5:at+=4
    if mod==0 and rm==5:at+=4
    elif mod==1:at+=1
    elif mod==2:at+=4
    _require(at+immediate==len(raw),'combo-setup-instruction-length',at+immediate,len(raw))
    if simd:return None
    if opcode==0x89:return registers[rm+(8 if rex&1 else 0)]if mod==3 else None
    return registers[((modrm>>3)&7)+(8 if rex&4 else 0)]


def _context_bindings():
    result={}
    def group(owner,nominal,args,rows,*,method_args=()):
        for role,method in rows:
            result[role]=(owner,nominal,method,tuple(args),tuple(method_args))
    pack='Beyond.Gameplay.Core.AbilitySystem+ComboController+AllowedNextSkillPack'
    modifier='Beyond.Gameplay.Core.AbilitySystem+ComboController+MappingModifier'
    command='Beyond.Gameplay.Core.AbilitySystem+ComboController+BattleCommandType'
    queue='Beyond.PriorityQueue`1<'+modifier+'>'
    combo='AbilitySystem+ComboController'
    group('AbilitySystem.CheckCanInterruptCurSkill','Beyond.ListSet`1',[pack],[('allowedItem','get_Item')])
    group('AbilitySystem.CheckCanInterruptCurSkill','System.Collections.Generic.List`1',['string'],[('allowedContains','Contains')])
    group(combo+'.AddAllowedNextSkillPack','Beyond.ListSet`1',[pack],[('allowedAdd','Add')])
    group(combo+'.AddAllowedNextSkillPack','Beyond.ObjectPtr`1',[pack],[('allowedObjectPtr','op_Implicit')])
    group(combo+'.RemoveAllowedNextSkillPack','Beyond.ListSet`1',[pack],[('allowedRemove','Remove')])
    group('AbilitySystem.CanCastSkill','System.Collections.Generic.Dictionary`2',['string','Beyond.Gameplay.Core.Skill'],[('castContainsSkill','ContainsKey'),('castGetSkill','get_Item')])
    group(combo+'+AllowedNextSkillPack.Init','System.Collections.Generic.List`1',['string'],[('packInitAddRange','AddRange'),('packInitContains','Contains'),('packInitAdd','Add')])
    group(combo+'._UpdateRealEffectedMapping','System.Collections.Generic.Dictionary`2',[command,queue],[('refreshRuntimeTry','TryGetValue')])
    group(combo+'._UpdateRealEffectedMapping','System.Collections.Generic.Dictionary`2',[command,modifier],[('refreshBaseTry','TryGetValue'),('refreshClear','Clear'),('refreshSet','set_Item')])
    group(combo+'._UpdateRealEffectedMapping','Beyond.PriorityQueue`1',[modifier],[('refreshQueueEmpty','get_isEmpty'),('refreshQueueZero','get_Item')])
    group(combo+'._UpdateRealEffectedMapping','System.Collections.Generic.CollectionExtensions',[],[('refreshBaseDefault','GetValueOrDefault')],method_args=[command,modifier])
    group(combo+'.RemoveMappingModifier','System.Collections.Generic.Dictionary`2',[command,queue],[('removeQueueTry','TryGetValue')])
    group(combo+'.RemoveMappingModifier','Beyond.PriorityQueue`1',[modifier],[('removeQueueCount','get_count'),('removeQueueItem','get_Item'),('removeQueueRemove','Remove')])
    group(combo+'.AddMappingModifier','System.Collections.Generic.Dictionary`2',[command,queue],[('addQueueTry','TryGetValue')])
    group(combo+'.AddMappingModifier','Beyond.PriorityQueue`1',[modifier],[('addQueueAdd','Add')])
    group(combo+'.AddAllowedNextSkillPack','Beyond.PoolCore.GenericStaticPool`1',[pack],[('allocateAllowedPack','Allocate')])
    group('AbilitySystem.CanCastNormalAttackAttack','Beyond.CollectionExtensions',[],[('normalSafeCount','SafeCount')],method_args=['Beyond.Gameplay.Core.Skill'])
    group('AbilitySystem.CanCastNormalAttackAttack','System.Collections.Generic.List`1',['Beyond.Gameplay.Core.Skill'],[('normalListItem','get_Item')])
    group(combo+'+MappingModifier+Handle.RemoveModifier','Beyond.ObjectPtr`1',['Beyond.Gameplay.Core.AbilitySystem'],[('handleOwnerForRemove','Lock'),('handleOwnerForClear','Lock')])
    group('Handle.offsetCleanup','Beyond.ObjectPtr`1',['Beyond.Gameplay.Core.AbilitySystem'],[('handleOwnerForOffset','Lock')])
    group('AllowNextSkillAction.OnEnd','Beyond.ObjectPtr`1',[pack],[('allowedHandleValid','get_isValid'),('allowedHandleLock','Lock')])
    return result


def _suffix_geometry(base_size,witness_size,query_offset,pack_offset):
    _require(all(type(value)is int and 16<=value<=4096 and value%8==0
                 for value in(base_size,witness_size,query_offset,pack_offset)),
             'combo-suffix-alignment','bounded aligned reference instance extents',
             (base_size,witness_size,query_offset,pack_offset))
    _require(query_offset==base_size+8 and pack_offset==query_offset+8 and witness_size==pack_offset+16,
             'combo-suffix-complete','sole reference, query pointer, selected ObjectPtr16 with no gap/tail',
             (base_size,witness_size,query_offset,pack_offset))
    return base_size


def _validate_allow_layout(image,context,contract,checked):
    """One concrete witness plus an independently checked constructed value ABI.

    Open generic sizes/offsets are never interpreted as closed layout, and the
    shared reference-only helper is neither called permissively nor changed.
    """
    spec=contract['allowNextLayout'];types=context.index.types;metadata=image.metadata
    witness='Beyond.Gameplay.Core.AllowNextSkillAction';base='Beyond.Gameplay.Core.AbilityAction'
    data=witness+'+Data';generic=base+'`1';closed=generic+'<'+data+'>'
    pack='Beyond.Gameplay.Core.AbilitySystem+ComboController+AllowedNextSkillPack'
    value='Beyond.ObjectPtr`1<'+pack+'>'
    _require((spec['witness'],spec['base'],spec['dataArgument'],spec['closedParent'],spec['selectedObjectPtrValue'])
             ==(witness,base,data,closed,value),'combo-layout-nominal','one selected closed witness',spec)
    _require(spec['selectedNativeAbiOnly'] is True and spec['allObjectPtrInstantiationsProved'] is False
             and spec['referenceBytes']==8 and spec['inheritedField']=='m_data'
             and spec['suffix']==[{'field':'m_query','bytes':8},{'field':'m_allowedNextSkillPack','bytes':16}],
             'combo-layout-boundary','one reference plus independently checked 8/16 suffix',spec)
    _require(context.parent(witness)==closed and context.parent(generic)==base
             and context.parent(base)in('object','System.Object') and not context.is_value_type(data)
             and not context.is_value_type(pack) and context.is_value_type(value),
             'combo-layout-parent','actual closed parent and reference/value classification',spec)
    sizes={}
    for row in spec['typeSizes']:
        td=types[row['type']]
        _require(td.flags==row['flags'] and td.bitfield==row['bitfield'] and td.bitfield&0x800
                 and td.flags&0x18!=0x10,'combo-layout-default-size','selected non-explicit default-sized declaration',row)
        _require(td.generic_container_index==row['genericContainerIndex'],
                 'combo-layout-generic-container',row['genericContainerIndex'],td.generic_container_index)
        table=int(image.registration['typeDefinitionsSizes'],16)
        _require(0<=td.index<image.registration['typeDefinitionsSizesCount'],'combo-layout-size-index','selected table',td.index)
        pointer=image.pe.u64_at_va(table+td.index*8);raw=image.pe.bytes_at_va(pointer,16)
        _require(raw.hex()==row['typeSizeRowHex'] and int.from_bytes(raw[:4],'little')==row['instanceBytes'],
                 'combo-layout-size-row',row,raw.hex())
        sizes[row['type']]=row['instanceBytes']
    _require(set(sizes)=={base,generic,witness,'Beyond.ObjectPtr`1'},
             'combo-layout-size-coverage','base, generic definition, witness and value definition',list(sizes))
    def parameter(owner):
        td=types[owner];section=metadata.sections['genericContainers'];at=section.offset+td.generic_container_index*16
        _require(td.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16,
                 'combo-layout-generic-bounds','current generic container',at)
        actual,count,is_method,index=struct.unpack_from('<iiii',metadata.buf,at)
        _require((actual,count,is_method)==(td.index,1,0),'combo-layout-generic-owner','one class parameter',(actual,count,is_method))
        return index
    def instances(owner):
        return [field for field in metadata.fields_for(types[owner])if not context.field_attributes(field.type_index)&0x10]
    own=instances(generic);argument=parameter(generic)
    _require(len(own)==1 and metadata.string(own[0].name_index)=='m_data'
             and context.type_name(own[0].type_index)=='VAR['+str(argument)+']',
             'combo-layout-sole-reference-prefix','one current reference type parameter',len(own))
    context.require_ordinary_kind(own[0].type_index,0x13)
    ptr_fields={metadata.string(field.name_index):field for field in instances('Beyond.ObjectPtr`1')}
    ptr_argument=parameter('Beyond.ObjectPtr`1')
    _require(set(ptr_fields)=={'obj','cachedUid'}
             and context.type_name(ptr_fields['obj'].type_index)=='VAR['+str(ptr_argument)+']'
             and context.type_name(ptr_fields['cachedUid'].type_index)=='uint',
             'combo-objectptr-declaration','current generic reference argument plus UInt32 UID',list(ptr_fields))
    # Generic definition field offsets/sizes are placeholders, not used here.
    context.require_ordinary_kind(ptr_fields['obj'].type_index,0x13)
    context.require_ordinary_kind(ptr_fields['cachedUid'].type_index,0x09)
    base_extents=[]
    for field in instances(base):
        name=metadata.string(field.name_index);_,nominal,offset=context.field(base+'::'+name)
        width={'bool':1,'int':4}.get(nominal)
        if context.is_enum(nominal):
            _require(context.field(nominal+'::value__')[1]=='int','combo-base-enum','Int32 enum',nominal);width=4
        if nominal in types and not context.is_value_type(nominal):width=8
        _require(width is not None and 16<=offset<offset+width<=sizes[base],
                 'combo-base-field-extent','bounded actual primitive/reference extent',(name,nominal,offset,width))
        base_extents.append((offset,offset+width))
    _require(base_extents and max(end for start,end in base_extents)==sizes[base]
             and all(a[1]<=b[0]for a,b in zip(sorted(base_extents),sorted(base_extents)[1:])),
             'combo-base-tail-and-overlap','no trailing base padding or overlapping fields',base_extents)
    declared={metadata.string(field.name_index)for field in instances(witness)}
    _require(declared=={'m_query','m_allowedNextSkillPack'},'combo-suffix-fields','complete concrete suffix',declared)
    _,query,query_offset=context.field(witness+'::m_query')
    _,pack_type,pack_offset=context.field(witness+'::m_allowedNextSkillPack')
    _require(query=='Beyond.Gameplay.Core.Skill+AllowNextSkillQuery' and not context.is_value_type(query)
             and pack_type==value,'combo-suffix-field-types','query reference and exact constructed value',(query,pack_type))
    data_offset=_suffix_geometry(sizes[base],sizes[witness],query_offset,pack_offset)
    spans={row['role']:row for row in spec['spans']}
    expected={'implicitZero16':'0f57c0488bd90f1101','implicitReferenceStore':'48893b',
              'implicitUidStore':'894308','implicitValueReturn':'488bc3','implicitNullFields':'33c0488903894308',
              'controllerResultRead16':'0f10442430','controllerResultWrite16':'0f1107',
              'actionResultRead16':'0f1000'}
    _require(set(spans)==set(expected)|{'actionClosedDataLoad','actionResultWrite16','mappingBaseCopy24','mappingQueueCopy24'},
             'combo-layout-operation-coverage','complete selected ABI transfers',list(spans))
    for role,encoding in expected.items():
        _require(checked(spans[role]).hex()==encoding,'combo-layout-operation',encoding,spans[role]['hex'])
    _require(checked(spans['actionClosedDataLoad'])==bytes.fromhex('488b4b')+bytes([data_offset])
             and checked(spans['actionResultWrite16'])==bytes.fromhex('0f1143')+bytes([pack_offset]),
             'combo-layout-selected-prefix-consumer','actual inherited ref and full concrete value store',spec)
    context_request=next(row for row in contract['typedContexts']if row['role']=='allowedObjectPtr')
    factory=next(row for row in contract['codeWindows']if row['owner']=='ObjectPtr.allowedImplicit')
    _require(context_request['callTargetRva']==factory['startRva'],
             'combo-objectptr-selected-factory','same actual closed-context call target',context_request['callTargetRva'])
    payload=next(row for row in contract['facts']if row['id']=='mappingPayload24')
    modifier='Beyond.Gameplay.Core.AbilitySystem+ComboController+MappingModifier'
    _require(context.is_value_type(modifier) and payload['payloadBytes']==24
             and payload['valueType']==modifier and payload['valueTypeHeaderAdjustment']==16,
             'combo-mapping-value-view','conditional current value type and explicit header16',payload)
    payload_fields={'skillId':(0,8,'string'),'instId':(8,8,'ulong'),'priority':(16,4,None),'cacheTime':(20,4,'float')}
    _require(payload['fields']==[dict(name=name,offset=offset,bytes=width)for name,(offset,width,_)in payload_fields.items()],
             'combo-mapping-field-shape','exact 24-byte carrier declaration',payload['fields'])
    for name,(offset,width,nominal)in payload_fields.items():
        _,actual,declared_offset=context.field(modifier+'::'+name)
        _require(declared_offset-16==offset and(actual==nominal if nominal else
                 context.is_enum(actual)and context.field(actual+'::value__')[1]=='int'),
                 'combo-mapping-field-view',(offset,nominal),(declared_offset-16,actual))
    _require(checked(spans['mappingBaseCopy24']).hex()=='0f1045a0f20f104db00f2945c04c8d45c0f20f114dd0'
             and checked(spans['mappingQueueCopy24']).hex()=='0f1045c04c8d45e0488bcef20f104dd00f2945e0f20f114df0',
             'combo-mapping-complete-copy','current 16+8-bit-preserving selected setter carrier',spec['spans'])
    return dict(closedType=closed,dataFieldOffset=data_offset,dataReferenceBytes=8,
                selectedObjectPtrBytes=16,witnessBytes=sizes[witness],runtimeProviderObserved=False,
                allGenericInstantiationsProved=False)



def _type_zero_enum_members(image):
    from scripts.game_data.il2cpp.protocol import native_enum_members,field_defaults
    return native_enum_members(image.metadata,field_defaults(image.metadata),image.pe,image.registration,'Beyond.Gameplay.SkillType')


def _validate_type_zero_priority(contract,read,field,enum_members):
    """Only the ordinary zero-type path; nonzero jump-table cases stay opaque."""
    d=contract['normalTypeZeroPriority']
    method=next(row for row in contract['methods']if row['id']==d['owner'])
    window=next(row for row in contract['codeWindows']if row['owner']==d['owner'])
    _require(d['owner']=='Skill.get_skillInterruptPriority'and d['skillTypeFieldId']=='Skill::<skillType>k__BackingField'
        and window['startRva']==method['identity'][3],'combo-type-zero-owner','selected getter and field',d)
    actual=field('Beyond.Gameplay.Core.Skill::<skillType>k__BackingField')
    _require(actual[:2]==('Beyond.Gameplay.Core.Skill','Beyond.Gameplay.SkillType'),
        'combo-type-zero-field','typed SkillType receiver field',actual)
    members=[m for m in enum_members if m['name']==d['enumMember']['name']]
    _require(d['enumMember']['type']=='Beyond.Gameplay.SkillType'and d['enumMember']['name']=='Attack'
        and d['enumMember']['id']==0 and len(members)==1
        and (members[0]['id'],members[0]['token'])==(0,d['enumMember']['token']),
        'combo-type-zero-enum','fresh Attack zero metadata',members)
    start=window['startRva'];raw=read(start,window['endRva']-start)
    # Entry guard is framed independently of the subset disassembler. Its
    # taken iFix edge leaves this owned window; only ordinary fallthrough is used.
    _require(len(raw)>=46 and raw[:7]==bytes.fromhex('4883ec28488b05')
        and raw[11:20]==bytes.fromhex('4c8b48484d85c90f85')
        and not start<=start+24+struct.unpack_from('<i',raw,20)[0]<window['endRva'],
        'combo-type-zero-entry-guard','framed ordinary fallback after iFix guard',raw[:24].hex())
    offset=actual[2].to_bytes(4,'little')
    expected=bytes.fromhex('486381')+offset+bytes.fromhex('85c0750b8b81')+offset+bytes.fromhex('4883c428c3')
    _require((d['ordinaryStartOffset'],d['zeroReturnEndOffset'],d['nonzeroTargetOffset'])==(24,46,46)
        and raw[24:46]==expected and start+35+struct.unpack_from('<b',raw,34)[0]==start+46,
        'combo-type-zero-return','test zero then same-field EAX return without helpers',raw[24:46].hex())
    return dict(normalTypeZeroPriorityZeroProved=True,normalTypeZeroSemantic='Attack',
        nonzeroTypePriorityAlgorithmProved=False,sameTypeAcrossTwoReadsRequired=True,
        currentAndCandidateSkillTypeObserved=False,evidenceBoundary=d['evidenceBoundary'])

def _validate(image,contract):
    rules=_rule_scope(contract);context=NativeReferenceContext(image);methods={}
    for row in contract['methods']:
        index=image.validate_method_row(row['identity'],label=LABEL)
        method=image.metadata.methods[index]
        actual=dict(returnType=context.type_name(method.return_type),parameters=[
            dict(name=image.metadata.string(p.name_index),type=context.type_name(p.type_index))
            for p in image.metadata.parameters_for(method)])
        _require(actual=={key:row[key] for key in actual} and not method.flags&0x10,
                 'combo-method-signature',row,actual)
        nominal=row['identity'][1].removeprefix('Beyond.Gameplay.Core.')+'.'+row['identity'][2]
        _require(row['id']==nominal and nominal not in methods,'combo-method-identity',nominal,row['id'])
        methods[nominal]=row
    windows=contract['codeWindows']
    _require(len({row['owner']for row in windows})==len(windows),'combo-window-owner','unique owner',windows)
    for window in windows:
        if window['owner'] in methods:
            _require(window['startRva']==methods[window['owner']]['identity'][3],
                     'combo-window-entry',methods[window['owner']]['identity'][3],window['startRva'])
    image.check_windows(windows,label=LABEL)
    fields=_validate_fields(image,contract['fields'])
    type_members=_type_zero_enum_members(image)
    _validate_type_zero_priority(contract,lambda r,n:image.pe.bytes_at_va(image.pe.image_base+r,n),context.field,type_members)
    def checked(row):
        owners=[window for window in windows if window['owner']==row['owner']]
        _require(len(owners)==1,'combo-operand-owner',row['owner'],len(owners))
        window=owners[0];raw=bytes.fromhex(row['hex']);rva=row['rva']
        _require(0<len(raw)<=65536 and window['startRva']<=rva<rva+len(raw)<=window['endRva'],
                 'combo-operand-bounds',window,row)
        actual=image.pe.bytes_at_va(image.pe.image_base+rva,len(raw))
        _require(actual==raw,'combo-operand-bytes',raw.hex(),actual.hex())
        return raw
    roles={}
    for row in contract['fieldOperands']:
        raw=checked(row);field=fields[row['field']]
        context.field(field['type']+'::'+field['name'])
        at,width=row['displacementOffset'],row['displacementSize']
        _require(width in(1,4) and 0<=at<=len(raw)-width,'combo-displacement-shape','bounded disp8/32',row)
        actual=int.from_bytes(raw[at:at+width],'little',signed=True)
        adjustment=row.get('valueTypeHeaderAdjustment',0)
        if adjustment:
            _require(adjustment==16 and row['role'] in('handleInstId','handleCommand','handleClearRequest','handleClearOffset')
                     and context.is_value_type(field['type']),'combo-conditional-value-view',
                     'explicit Handle value-type view with header16',row)
        _require(actual==field['offset']-adjustment,'combo-field-operand',field['offset']-adjustment,actual)
        _require(row['role']not in roles,'combo-field-role','distinct roles',row['role']);roles[row['role']]=row
    required_fields={'currentSkillNull','comboExists','newSkillId','allowedPacks','packSkillList',
                     'plungeStart','plungeEnd','initExistingList','initAlwaysSkills','actionAllowedList',
                     'actionPackStore','realMapping','runtimeMapping','baseMapping','normalCandidateType',
                     'handleInstId','handleCommand','handleClearRequest','handleClearOffset','currentPriorityReceiver',
                     'castActiveMap','normalSkillList'}
    _require(set(roles)==required_fields,'combo-field-coverage',sorted(required_fields),sorted(roles))
    branches={}
    for row in contract['branches']:
        result=_branch(checked(row),row['rva'])
        _require(result==(row['condition'],row['targetRva']),'combo-branch-target',
                 (row['condition'],row['targetRva']),result)
        _require(row['role']not in branches,'combo-branch-role','distinct roles',row['role']);branches[row['role']]=row
    expected_conditions={'noCurrentSkill':'equal','missingComboSkipsAllowed':'equal',
        'allowedLoopIndexLessCount':'signedLess','allowedContainsTrue':'notEqual',
        'plungeStartPointerEqual':'equal','plungeStartContentEqual':'notEqual',
        'plungeEndPointerEqual':'equal','plungeEndContentEqual':'notEqual',
        'higherPriority':'signedGreater','currentCanInterrupt':'notEqual',
        'initContainsSkipsAdd':'notEqual','removeNoQueue':'equal','removeInstIdMismatch':'notEqual',
        'removeReverseContinue':'nonNegative','mappingRuntimeFound':'notEqual','mappingQueueNonEmpty':'equal',
        'handleSkipClearRequest':'equal','handleDoClearOffset':'notEqual','allowHandleInvalidReturns':'equal'}
    _require({role:row['condition']for role,row in branches.items()}==expected_conditions,
             'combo-branch-semantics',expected_conditions,{r:v['condition']for r,v in branches.items()})
    true_roles=['noCurrentSkill','allowedContainsTrue','plungeStartPointerEqual','plungeStartContentEqual',
                'plungeEndPointerEqual','plungeEndContentEqual','higherPriority','currentCanInterrupt']
    true_target=branches['noCurrentSkill']['targetRva']
    _require(all(branches[role]['targetRva']==true_target for role in true_roles),
             'combo-true-return-join',true_target,{r:branches[r]['targetRva']for r in true_roles})
    spans={row['role']:row for row in contract['flowSpans']}
    expected_spans={'trueReturn':'b001','allowedIndexZero':'33ed','allowedIndexIncrement':'ffc5','signedPriorityCompare':'3bf8'}
    _require(set(spans)==set(expected_spans)|{'priorityNormalReturnTransfer'},'combo-flow-span-coverage',expected_spans,list(spans))
    for role,encoding in expected_spans.items():
        _require(checked(spans[role]).hex()==encoding,'combo-flow-operation',encoding,spans[role]['hex'])
    _require(spans['trueReturn']['rva']==true_target,'combo-true-return-operation',true_target,spans['trueReturn']['rva'])
    _require(branches['missingComboSkipsAllowed']['targetRva']==roles['plungeStart']['rva'],
             'combo-missing-owner-skip',roles['plungeStart']['rva'],branches['missingComboSkipsAllowed']['targetRva'])
    _require(roles['plungeStart']['rva']<roles['plungeEnd']['rva']<spans['signedPriorityCompare']['rva'],
             'combo-plunge-order','start then end then signed priority',roles)
    calls={}
    expected_calls={
        'newPriority':('AbilitySystem.CheckCanInterruptCurSkill','Beyond.Gameplay.Core.Skill','get_skillInterruptPriority'),
        'currentPriority':('AbilitySystem.CheckCanInterruptCurSkill','Beyond.Gameplay.Core.Skill','get_skillInterruptPriority'),
        'currentCanInterrupt':('AbilitySystem.CheckCanInterruptCurSkill','Beyond.Gameplay.Core.Skill','get_canInterrupt'),
        'interruptCheck':('AbilitySystem.CanCastSkill','Beyond.Gameplay.Core.AbilitySystem','CheckCanInterruptCurSkill'),
        'normalCandidateCast':('AbilitySystem.CanCastNormalAttackAttack','Beyond.Gameplay.Core.AbilitySystem','CanCastSkill'),
        'targetCheck':('AbilitySystem.CanCastSkill','Beyond.Gameplay.Core.Skill','CanCastToTarget'),
        'packInitialize':('AbilitySystem+ComboController.AddAllowedNextSkillPack','Beyond.Gameplay.Core.AbilitySystem+ComboController+AllowedNextSkillPack','Init'),
        'actionAddPack':('AllowNextSkillAction.ExecuteInternal','Beyond.Gameplay.Core.AbilitySystem+ComboController','AddAllowedNextSkillPack'),
        'removeBridge':('AllowNext.removeBridge','Beyond.Gameplay.Core.AbilitySystem+ComboController','RemoveAllowedNextSkillPack'),
        'mappingAddedRefresh':('AbilitySystem+ComboController.AddMappingModifier','Beyond.Gameplay.Core.AbilitySystem+ComboController','_UpdateRealEffectedMapping'),
        'mappingRemovedRefresh':('AbilitySystem+ComboController.RemoveMappingModifier','Beyond.Gameplay.Core.AbilitySystem+ComboController','_UpdateRealEffectedMapping'),
        'handleRemove':('Handle.removeBridge','Beyond.Gameplay.Core.AbilitySystem+ComboController','RemoveMappingModifier'),
        'handleClearRequest':('Handle.clearBridge','Beyond.Gameplay.Core.AbilitySystem+ComboController','ClearSkillRequestByModifierInstId'),
        'handleClearOffset':('Handle.offsetCleanup','Beyond.Gameplay.Core.AbilitySystem','ClearOffsetModifier')}
    for row in contract['directCalls']:
        expected=expected_calls.get(row['role'])
        _require(expected==(row['owner'],row['target'][1],row['target'][2]),
                 'combo-call-nominal-join',expected,(row['owner'],row['target'][1],row['target'][2]))
        raw=checked(row)
        _require(len(raw)==5 and raw[0] in(0xe8,0xe9),'combo-direct-call','E8/E9 rel32',raw.hex())
        index=image.validate_method_row(row['target'],label=LABEL)
        target=row['rva']+5+struct.unpack_from('<i',raw,1)[0]
        _require(target==row['target'][3],'combo-direct-call-target',row['target'][3],target)
        _require(row['role']not in calls,'combo-call-role','distinct',row['role']);calls[row['role']]=row
    _require(set(calls)==set(expected_calls),'combo-call-coverage',list(expected_calls),list(calls))
    transfer=spans['priorityNormalReturnTransfer'];raw=checked(transfer)
    expected=(bytes.fromhex('33d2498bce')+checked(calls['newPriority'])+checked(roles['currentPriorityReceiver'])
              +bytes.fromhex('8bf84885c9')+raw[22:28]+bytes.fromhex('33d2')
              +checked(calls['currentPriority'])+bytes.fromhex('3bf8')+checked(branches['higherPriority']))
    _require(len(raw)==39 and raw==expected and _branch(raw[22:28],transfer['rva']+22)[0]=='equal'
             and calls['newPriority']['rva']==transfer['rva']+5
             and roles['currentPriorityReceiver']['rva']==transfer['rva']+10
             and calls['currentPriority']['rva']==transfer['rva']+30
             and branches['higherPriority']['rva']==transfer['rva']+37,
             'combo-priority-normal-return-transfer','EAX new -> preserved EDI, current EAX, CMP EDI,EAX then JG',raw.hex())
    contexts=[]
    expected_contexts=_context_bindings();seen_contexts=set()
    for row in contract['typedContexts']:
        actual=derive_typed_usage_context(image,row['rva'],label=LABEL)
        _require(actual==row['result'],'combo-typed-request',row['result'],actual)
        _require(any(w['owner']==row['owner'] and w['startRva']<=row['rva']<w['endRva']for w in windows),
                 'combo-context-window',row['owner'],row['rva'])
        role=row['role']
        _require(role not in seen_contexts,'combo-context-role','distinct',role);seen_contexts.add(role)
        if row['binding']=='inline-metadata-guard-only':
            _require(role=='allowedInlineCountGuard' and row['owner']=='AbilitySystem.CheckCanInterruptCurSkill'
                     and row['closedCollectionAbiProved'] is False and actual['typeName']=='Beyond.ListSet`1'
                     and actual['methodName']=='get_count','combo-inline-count-boundary','selected metadata guard only',row)
        else:
            identity=(row['owner'],actual['typeName'],actual['methodName'],tuple(actual['classArguments']),tuple(actual['methodArguments']))
            _require(row['binding']=='selected-callsite' and expected_contexts.get(role)==identity,
                     'combo-context-nominal-site',expected_contexts.get(role),identity)
            instructions=[bytes.fromhex(value)for value in row['setupInstructions']]
            _require(len(instructions)>=2 and instructions[0].hex().upper()==actual['instructionHex'].upper(),
                     'combo-context-setup-start',actual['instructionHex'],row['setupInstructions'])
            block=dict(owner=row['owner'],rva=row['rva'],hex=b''.join(instructions).hex());checked(block)
            first=_written_register(instructions[0])
            _require(first==row['contextRegister'] and all(_written_register(value)!=first for value in instructions[1:-1]),
                     'combo-context-carrier','same MethodInfo argument register through reviewed setup',row)
            call=instructions[-1];callsite=row['rva']+sum(len(value)for value in instructions[:-1])
            _require(len(call)==5 and call[0]==0xe8 and callsite==row['callRva']
                     and callsite+5+struct.unpack_from('<i',call,1)[0]==row['callTargetRva'],
                     'combo-context-consumer-call','actual final E8 consumes unchanged carrier',row)
        contexts.append(actual)
    _require(seen_contexts==set(expected_contexts)|{'allowedInlineCountGuard'},
             'combo-context-site-coverage',sorted(expected_contexts),sorted(seen_contexts))
    identities={(row['typeName'],row.get('methodName'),tuple(row.get('classArguments',[])))for row in contexts}
    required={('Beyond.ListSet`1','get_Item',('Beyond.Gameplay.Core.AbilitySystem+ComboController+AllowedNextSkillPack',)),
              ('Beyond.ListSet`1','Add',('Beyond.Gameplay.Core.AbilitySystem+ComboController+AllowedNextSkillPack',)),
              ('Beyond.ListSet`1','Remove',('Beyond.Gameplay.Core.AbilitySystem+ComboController+AllowedNextSkillPack',)),
              ('System.Collections.Generic.List`1','Contains',('string',)),
              ('System.Collections.Generic.List`1','AddRange',('string',)),
              ('System.Collections.Generic.List`1','Add',('string',)),
              ('Beyond.PriorityQueue`1','get_Item',('Beyond.Gameplay.Core.AbilitySystem+ComboController+MappingModifier',)),
              ('Beyond.PriorityQueue`1','Remove',('Beyond.Gameplay.Core.AbilitySystem+ComboController+MappingModifier',)),
              ('Beyond.PriorityQueue`1','Add',('Beyond.Gameplay.Core.AbilitySystem+ComboController+MappingModifier',))}
    _require(required<=identities,'combo-required-typed-requests',sorted(required),sorted(identities))
    _validate_allow_layout(image,context,contract,checked)
    return dict(rules)


def load_skill_combo_acceptance(contract_path=CONTRACT_PATH,*,gameassembly=None,metadata=None):
    path=Path(contract_path)
    audit=dict(schema=AUDIT_SCHEMA,normalTypeZeroPriorityZeroProved=False,status='validation_failed',nativeInputs={},rows=[],rules={},orderedPredicates=[],failures=[],contract=str(path))
    try:
        contract,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label=LABEL)
        audit.update(contractSha256=digest,evidenceBoundary=contract['evidenceBoundary'])
        pins=contract['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        image=open_native_image(gate.gameassembly,gate.metadata)
        source_paths={Path(m.__file__).resolve()for name,m in tuple(sys.modules.items())
            if (name=='scripts' or name.startswith('scripts.') or name.startswith('endfield_'))
            and getattr(m,'__file__',None)and str(m.__file__).endswith('.py')}
        source_paths.update((Path(__file__).resolve(),Path(image.mapper.__file__).resolve()))
        before={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(source_paths)}
        rules=_validate(image,contract)
        source_after={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(source_paths)}
        _require(before==source_after,'combo-source-bookends','unchanged selected validator sources','changed')
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated','combo-native-inputs-after','validated',after.detail)
        _require(hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'combo-contract-after','unchanged','changed')
        audit.update(status='validated',detail='',nativeInputs={name:pins[name]for name in('GameAssembly.dll','global-metadata.dat')},
                     rows=contract['facts'],rules=rules,orderedPredicates=contract['orderedPredicates'],normalTypeZeroPriorityZeroProved=True,
                     normalTypeZeroPriorityBoundary=contract['normalTypeZeroPriority']['evidenceBoundary'],
                     sourceDependencies=before,sourceBookends=dict(before=before,after=source_after,matched=True))
    except(OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError,struct.error)as error:
        audit.update(status='validation_failed',detail=str(error)[:1200],nativeInputs={},rows=[],rules={},orderedPredicates=[])
        audit['failures'].append(dict(validator=LABEL,check=str(error).split(':',1)[0],source=str(path),detail=str(error)[:1200]))
    return audit


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract',type=Path,default=CONTRACT_PATH)
    parser.add_argument('--gameassembly',type=Path);parser.add_argument('--metadata',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    audit=load_skill_combo_acceptance(args.contract,gameassembly=args.gameassembly,metadata=args.metadata)
    if args.output:
        from scripts.repo_paths import REPO_ROOT
        if not any(args.output.resolve().is_relative_to(REPO_ROOT/root)for root in('reports','scratch','tmp')):
            parser.error('--output must be under reports/, scratch/ or tmp/')
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({key:audit[key]for key in('status','detail','orderedPredicates','failures')},indent=2))
    return 0 if audit['status']=='validated'else 1


if __name__=='__main__':raise SystemExit(main())
