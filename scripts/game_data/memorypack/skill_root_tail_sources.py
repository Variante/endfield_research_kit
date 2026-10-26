"""Current root49's named caller continuation and complete selected return.

The caller proof is separate from every reached child grammar. It begins at the
independently proved member4 barrier return, accounts for each named field5..48
source/transfer, and restores the actual root frame through RET. Selected native
metadata and source bytes supply field offsets, enum backing and call identities;
names and a matching stored width never supply a child codec.

Vector3 is an inlined twelve-byte buffered transfer with its actual Advance(12).
GameplayTagQuery instead has an inlined typed provider and sixteen-byte hidden
output transfer: sixteen is its managed ABI, not its wire width. Its distinct
callback/source/child joins remain mandatory. Normal initialized existing
nonnull root/original, coherent closed MethodInfos, stable disjoint buffered
storage, normal Win64 helper effects and matching runtime callbacks are explicit
conditions. New/null root paths, runtime provider choice and any child without
its independent proof stay closed. Whole serialized root/EOF admission requires
all child joins plus the selected parser's exact final cursor, never a historical
root48 terminal or an inferred tail.
"""
from __future__ import annotations

import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import scalar_param_native as scalar, primitive_param, pooled_source_helper
from scripts.game_data.memorypack.pointer_param import methods, owned
from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper, selected_inputs, _fast_barrier
from scripts.game_data.memorypack import skill_root_prefix_sources as prefix_source
from scripts.game_data.memorypack.vector_layout import vector_recorder

LABEL='skillRootTailSources'
SCHEMA='endfield.skill-root-tail-source.v1'
ROOT=prefix_source.ROOT
WRAPPER=prefix_source.WRAPPER

# Finite format declarations, not native addresses or a metadata-name decoder.
DECLARATIONS=(
    (5,'buffs','System.Collections.Generic.List`1<Beyond.Gameplay.Core.BuffInput>','list'),
    (6,'canCastInAir','bool','boolean'),(7,'canCastInWater','bool','boolean'),
    (8,'canDummyCast','bool','boolean'),(9,'canMove','bool','boolean'),
    (10,'cardAttributeModifier','Beyond.Gameplay.AttributeModifierData','reference'),
    (11,'castData','Beyond.Gameplay.Core.CastData','reference'),
    (12,'castType','Beyond.Gameplay.CastType','enum32'),
    (13,'characterReturnToIdle','bool','boolean'),
    (14,'comboSkillUIBigSpriteName','string','string'),(15,'comboSkillUISpriteName','string','string'),
    (16,'dontInterruptCombo','bool','boolean'),(17,'dummyPositionOffset','UnityEngine.Vector3','vector3-inline'),
    (18,'durationFrame','int','int32'),(19,'exclusiveFrame','int','int32'),
    (20,'hittableAttackRange','float','single'),(21,'iconBgType','Beyond.GEnums.DamageType','enum32'),
    (22,'iconId','string','string'),(23,'level','int','int32'),
    (24,'needEnemyOutOfScreenWarning','bool','boolean'),
    (25,'needEnemyOutOfScreenWarningOverrideValue','bool','boolean'),
    (26,'normalSkillSubType','Beyond.Gameplay.NormalSkillSubType','enum32'),
    (27,'offsetRecordFrame','int','int32'),(28,'overrideHittableObjAttackRange','bool','boolean'),
    (29,'overrideNeedEnemyOutOfScreenWarning','bool','boolean'),
    (30,'passiveSkillType','Beyond.Gameplay.PassiveSkillType','enum32'),
    (31,'rootMotionCliffCheck','bool','boolean'),(32,'selectStrategy','Beyond.Gameplay.SelectStrategy','enum32'),
    (33,'showNotRecommendState','bool','boolean'),
    (34,'skillHighlightCondition','Beyond.Gameplay.Core.SequenceActionData','reference'),
    (35,'skillId','string','string'),(36,'skillName','string','string'),
    (37,'skillSpecification','Beyond.Gameplay.SkillSpecification','enum32'),
    (38,'skillTags','Beyond.Gameplay.Core.GameplayTagList','reference'),
    (39,'smartTargetBuffFindSettings','Beyond.Gameplay.Core.BuffFindSettings','reference'),
    (40,'smartTargetBuffIds','System.Collections.Generic.List`1<Beyond.Gameplay.Core.BuffId>','list'),
    (41,'smartTargetSelectStrategy','Beyond.Gameplay.SmartTargetSelectStrategy','enum32'),
    (42,'smartTargetTagQuery','Beyond.Gameplay.Core.GameplayTagQuery','hidden16-inline'),
    (43,'switchToBuffConfig','Beyond.Gameplay.Core.SwitchToBuffConfig','reference'),
    (44,'switchToCenterBeforeCast','bool','boolean'),
    (45,'tagDuringAttach','Beyond.Gameplay.Core.GameplayTagList','reference'),
    (46,'toggleBuffs','System.Collections.Generic.List`1<Beyond.Gameplay.Core.ToggleBuffData>','list'),
    (47,'uiRangeHints','System.Collections.Generic.List`1<Beyond.Gameplay.Core.UIRangeHintData>','list'),
    (48,'useAIExclusiveFrame','bool','boolean'),
)
BOUNDARY=dict(
    exact='Finite current root49 caller events5..48, exact source setup and unchanged named field stores, raw Vector3/Advance12, distinct GameplayTagQuery managed16 output and complete selected root frame restoration/return.',
    conditional='Initialized existing nonnull root/original and coherent supplied selected contexts; stable disjoint buffered Reader/output/frame and normal compatible Win64 helper, metadata, provider, predicate, callback and disabled-barrier effects. Every reached child source/ABI/grammar must compose independently.',
    structuralOnly='Stored field ownership and exact source control do not establish runtime skill execution or event delivery.',
    unresolved=['unjoined positive children and callbacks','new/null root and cold/refill/error paths',
        'live provider/cache/default/override selection','whole SkillData/EOF until all child joins and exact parser cursor'])


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def tail_program(regions,entry,slots,offsets):
    """Caller bytes only; delegated cursor effects acquire no admission here."""
    need('field-slot-inventory',{name for _,name,_,_ in DECLARATIONS},set(slots))
    widths={name:1 if kind=='boolean'else 12 if kind=='vector3-inline'else 16 if kind=='hidden16-inline'
        else 8 if kind in('list','reference','string')else 4 for _,name,_,kind in DECLARATIONS}
    occupied=[p for name,slot in slots.items()for p in range(slot,slot+widths[name])]
    need('disjoint-owned-fields',len(occupied),len(set(occupied)))
    need('bounded-owned-fields',True,all(type(v)is int and 16<=v<4096 for v in slots.values()))
    g=BytesPath(regions,entry);events=[];failures=[];barriers=[];preloaded=set()
    cur,rem=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength'))
    def peek(n):
        try:return bytes(g.bytes[g.at+i]for i in range(n)).hex()
        except KeyError as error:raise ValueError(LABEL+'.unowned-source-byte')from error
    def context(register='rdx'):
        at=g.at;cell=g.relative('488b15'if register=='rdx'else'488b1d')
        return dict(instruction=at,cell=cell,register=register)
    def source_setup(kind):
        setup=set(preloaded);preloaded.clear();usage=None;start=len(g.seen)
        for _ in range(3):
            opcode=peek(3)
            if opcode=='498b1e':
                need('duplicate-root-holder-load',False,'holder'in setup);setup.add('holder');g.take(opcode)
            elif opcode=='488bcf':
                need('duplicate-reader-argument',False,'reader'in setup);setup.add('reader');g.take(opcode)
            elif opcode=='488b15':
                need('duplicate-method-context',None,usage);usage=context()
            else:break
        need('reader-and-holder-setup',{'reader','holder'},setup)
        need('typed-context-presence',kind in('enum32','reference','list'),usage is not None)
        return usage,g.seen[start:]
    def source_call():
        at=g.at;target=g.relative('e8');return dict(instruction=at,target=target)
    def guards(original='rcx'):
        g.take('4885db');failures.append(g.relative('0f84'))
        g.take('488b4b10'if original=='rcx'else'488b4310',
            '4885c9'if original=='rcx'else'4885c0');failures.append(g.relative('0f84'))
        for target in failures[-2:]:need('owned-null-failure',True,target in g.bytes)
    def displacement(slot):return bytes((slot,)).hex()if slot<128 else slot.to_bytes(4,'little').hex()
    def store(kind,slot):
        if kind=='boolean':g.take(('8841'if slot<128 else'8881')+displacement(slot))
        elif kind in('enum32','int32'):g.take(('8941'if slot<128 else'8981')+displacement(slot))
        elif kind in('reference','list','string'):
            g.take(('488941'if slot<128 else'488981')+displacement(slot),
                ('4883c1'if slot<128 else'4881c1')+displacement(slot))
            barrier=source_call();barriers.append(barrier['target']);return barrier
        else:raise ValueError(LABEL+'.unreviewed-store-kind:'+kind)
        return None
    for index,name,typename,kind in DECLARATIONS:
        before=len(g.seen);slot=slots[name];event=dict(memberIndex=index,fieldName=name,typeName=typename,kind=kind)
        try:
            if kind=='vector3-inline':
                g.take('837f'+rem+'0c','498b1e');g.branch('7d',True,1)
                g.take('488b47'+cur,'ba0c000000','488bcf','f20f1030','8b7008')
                event['sourceCall']=source_call();guards('rax')
                g.take('f20f11b0'+slot.to_bytes(4,'little').hex(),'488bcf',
                    '89b0'+(slot+8).to_bytes(4,'little').hex())
                preloaded.add('reader');event.update(wireBytes=12,advanceArgument=12,managedBytes=12)
            elif kind=='hidden16-inline':
                usage=context('rbx');g.take('4d8b3e','48837b3800');g.branch('75',True,1)
                provider_site=g.at;provider=g.relative('488b0d')
                g.take('0f57c0','0f1145e0','83b9e000000000');g.branch('75',True,1)
                g.take('488b4338','488b30','48837e3800');g.branch('75',True,1)
                type_site=g.at;type_class=g.relative('488b0d')
                g.take('488b5e38','83b9e000000000','488b1b');g.branch('75',True,1)
                g.take('33d2','488bcb');type_from=source_call()
                need('same-hidden16-provider-class',provider,g.relative('488b0d'))
                g.take('488bd8','83b9e000000000');g.branch('75',True,1)
                g.take('488bcb');backend=source_call()
                g.take('488b4e38','ba01000000','488bd8');resolve=source_call()
                g.take('4885db');invalid=g.relative('0f84');need('owned-hidden16-null-failure',True,invalid in g.bytes)
                g.take('488b0b','488bd0');predicate=source_call();g.take('84c0')
                need('same-hidden16-type-failure',invalid,g.relative('0f84'))
                g.take('4c8d4de0','4c8bc7','488bd3');callback=source_call()
                g.take('4d85ff');failures.append(g.relative('0f84'))
                g.take('498b4f10','4885c9');failures.append(g.relative('0f84'))
                g.take('0f1045e0',('0f1141'if slot<128 else'0f1181')+displacement(slot))
                # The second half is the actual contained reference address.
                need('hidden16-contained-reference-small-offset',True,slot+8==128)
                g.take('4883e980');barrier=source_call();barriers.append(barrier['target'])
                event.update(typedContext=usage,managedBytes=16,wireBytes=None,
                    providerClassCell=provider,providerUsageSite=provider_site,typeUsageSite=type_site,
                    typeClassCell=type_class,typeFromHandle=type_from,backend=backend,
                    resolveClass=resolve,predicate=predicate,sourceCall=callback,
                    callbackAbi=dict(reader='r8',output='r9',formatter='rdx',rcx='callee must independently prove unused'),
                    referenceBarrier=barrier,childSourceAbiAdmitted=False)
            else:
                usage,setup=source_setup(kind);event.update(typedContext=usage,setupProgram=setup)
                event['sourceCall']=source_call()
                guards('rax'if kind=='single'else'rcx')
                if kind=='single':
                    # The next enum's Reader/holder setup is scheduled before
                    # this unchanged XMM0 store. No call clobbers that result.
                    g.take('498b1e','488bcf','f30f1180'+slot.to_bytes(4,'little').hex())
                    preloaded.update(('reader','holder'));event['resultRegister']='xmm0'
                else:
                    if index==48:g.take('0f28742470')
                    event['referenceBarrier']=store(kind,slot)
                event['managedBytes']=widths[name]
            event['fieldOffset']=slot;event['selectedBytes']=g.seen[before:];events.append(event)
        except ValueError as error:
            at,actual=g.seen[-1]if g.seen else(g.at,'unowned')
            raise ValueError(f'{LABEL}.member{index}:{name}:at={at:#x}:actual={actual}:{error}')from error
    need('no-unconsumed-argument-preloads',set(),preloaded)
    need('one-shared-null-failure',1,len(set(failures)))
    need('one-shared-reference-barrier',1,len(set(barriers)))
    epilogue_start=len(g.seen)
    g.take('4c8d9c2480000000','498b5b38','498b7340','498b7b48','498be3',
        '415f','415e','415d','415c','5d','c3')
    return dict(entry=entry,end=g.at,selectedBytes=g.seen,orderedFields=events,
        epilogue=g.seen[epilogue_start:],completeSelectedReturnProved=True,
        restoredNonvolatileRegisters=['rbx','rbp','rsi','rdi','r12','r13','r14','r15','xmm6'],
        entryRspRestored=True,referenceBarrierTarget=barriers[0],nullFailureTarget=failures[0],
        childGrammarsAdmitted=False,wholeSkillDataAdmitted=False)


def derive(image,pins,prefix=None):
    """Fresh named caller proof; returned child requirements are mandatory holds."""
    selected_inputs(pins)
    if prefix is None:prefix=prefix_source.derive(image,pins)
    need('prefix-selected-inputs',selected_inputs(pins),selected_inputs(prefix['nativeInputs']))
    need('prefix-complete-member',4,prefix['lastCompleteMember'])
    base=image.pe.image_base;ctx=NativeReferenceContext(image);wrapper=_selected_wrapper(image,WRAPPER)
    need('root-identity',ROOT,wrapper.wrapped_type);need('root49-count',49,len(wrapper.members))
    need('exact-tail-member-inventory',[(name,kind)for _,name,kind,_ in DECLARATIONS],
        [(m.name,m.declared_type)for m in wrapper.members[5:]])
    method=methods(image,wrapper)['Deserialize'];primitive_param.reader_abi(image,ctx,method,wrapper)
    source=owned(image,image.method_pointer_va(method));slots={name:ctx.field(ROOT+'::'+name)[2]for _,name,_,_ in DECLARATIONS}
    need('same-root-source',prefix['proof']['rootPrefix']['readerMethod'][3],source['pointer']-base)
    offsets=scalar.reader_offsets(image,LABEL)
    program=tail_program(source['regions'],prefix['proof']['program']['end'],slots,offsets)
    need('same-root-prefix-barrier',prefix['proof']['rootPrefix']['program']['barrierTarget'],program['referenceBarrierTarget'])
    contexts={};requirements=[];field_abi=[]
    root_td=ctx.index.types[ROOT]
    for index,name,typename,kind in DECLARATIONS:
        original_field=ctx.field(ROOT+'::'+name)
        need('owned-declared-field:'+name,(ROOT,typename),original_field[:2])
        declared,=[f for f in image.metadata.fields_for(root_td)if image.metadata.string(f.name_index)==name]
        type_kind={'boolean':2,'int32':8,'single':12,'string':14,'enum32':17,
            'vector3-inline':17,'hidden16-inline':17,'reference':18,'list':21}[kind]
        pointer=ctx.type_pointer(declared.type_index)
        scalar.ordinary(image,pointer,type_kind,LABEL+'.field.'+name,reference=kind in('reference','list','string'))
        field_abi.append(dict(memberIndex=index,fieldName=name,typeName=typename,kind=type_kind,
            typeRawHex=image.pe.bytes_at_va(pointer,16).hex().upper(),fieldOffset=original_field[2]))
    from scripts.game_data.levelscript_family_regenerate import Build
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    clones=ec.clone_facts(image,pins);record=vector_recorder(image);primitives={};enum_proofs={}
    build=Build(image,pins)
    for event in program['orderedFields']:
        kind=event['kind'];name=event['fieldName'];typename=event['typeName'];target=event['sourceCall']['target']
        if event.get('typedContext'):
            usage=derive_typed_usage_context(image,event['typedContext']['instruction']-base,label=LABEL+'.'+name)
            method_name='ReadUnmanaged'if kind=='enum32'else'ReadPackable'if kind=='list'else'ReadValue'
            type_kind=17 if kind in('enum32','hidden16-inline')else 21 if kind=='list'else 18
            prefix_source.bind_typed_read(image,usage,method_name=method_name,argument=typename,
                kind=type_kind,reference=kind in('list','reference'))
            contexts[name]=usage
        if kind in('boolean','int32','enum32','single'):
            primitive_kind='int32'if kind=='enum32'else kind
            if primitive_kind in primitives:need('same-'+primitive_kind+'-source',primitives[primitive_kind]['targetRva'],target-base)
            else:
                actual=record(target-base)
                if primitive_kind=='boolean':scalar.boolean_source(image,actual,offsets,LABEL+'.boolean')
                elif primitive_kind=='single':primitive_param.single_source(image,actual,offsets)
                else:scalar.integer_source(image,actual,offsets,LABEL+'.integer')
                primitives[primitive_kind]=dict(targetRva=target-base,source=actual)
            if kind=='enum32':enum_proofs[name]=build.derive_enum(dict(typeName=typename,backingType='System.Int32',width=4))
        elif kind=='string':
            actual=pooled_source_helper.validate_on_image(image,target,pins)
            primitives.setdefault('string',actual)
        elif kind=='vector3-inline':
            advance=record(target-base,fragments=True);scalar.advance_source(image,advance,offsets,LABEL+'.Advance12')
            primitives['vector3Advance']=advance
            from scripts.game_data.memorypack.wrapper_members import unmanaged_value_sizes_from_image
            need('vector3-unmanaged-width',12,unmanaged_value_sizes_from_image(image).get(typename))
            need('vector3-value-type',True,ctx.is_value_type(typename))
            vector_fields=[f for f in image.metadata.fields_for(ctx.index.types[typename])if not ctx.field_attributes(f.type_index)&16]
            need('vector3-exact-instance-fields',['x','y','z'],[image.metadata.string(f.name_index)for f in vector_fields])
            vector_layout=[]
            for n,f in enumerate(vector_fields):
                field=image.metadata.string(f.name_index);layout=ctx.field(typename+'::'+field)
                need('vector3-owned-float-field',(typename,'float',16+4*n),layout)
                scalar.ordinary(image,ctx.type_pointer(f.type_index),12,LABEL+'.vector3.'+field)
                vector_layout.append(dict(field=field,unboxedOffset=4*n,bytes=4))
            primitives['vector3Layout']=dict(typeName=typename,managedBytes=12,wireBytes=12,fields=vector_layout)
        elif kind in('reference','list'):
            method_name='ReadPackable'if kind=='list'else'ReadValue'
            need('actual-'+method_name+'-target',base+clones[method_name]['targetRva'],target)
            requirements.append(dict(memberIndex=event['memberIndex'],typeName=typename,kind=kind,
                required='exact nominal child grammar/callback/source composition'))
        elif kind=='hidden16-inline':
            requirements.append(dict(memberIndex=event['memberIndex'],typeName=typename,kind=kind,
                required='own inline provider contexts, actual hidden16 callback ABI/source and nominal child wire grammar'))
        else:raise ValueError(LABEL+'.unreviewed-event:'+kind)
    barrier,barrier_proof,_=_fast_barrier(image,program['referenceBarrierTarget'])
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-caller-program-requires-child-joins',nativeInputs=pins,
        prefixLastCompleteMember=4,parentLastSourceMember=48,program=program,sourceWindows=source['windows'],
        fields=[dict(memberIndex=i,fieldName=n,typeName=t,kind=k,fieldOffset=slots[n])for i,n,t,k in DECLARATIONS],
        contexts=contexts,fieldAbi=field_abi,primitiveSources=primitives,enumBacking=enum_proofs,barrier=barrier,barrierProof=barrier_proof,
        requiredChildJoins=requirements,completeSelectedReturnProved=True,childGrammarsAdmitted=False,
        wholeSkillDataAdmitted=False,evidenceBoundary=BOUNDARY)))
