"""Finite named current Skill child record source programs.

The direct-record shape owns the buffered MC/FF path, exact named source order,
unchanged Boolean/Int32/Single/reference stores, constructor join and complete
return or barrier tail. Each actual typed source call must still join its own
nominal child capability. In particular an array/list request or eight-byte
reference store never admits its elements. Matching initialized contexts,
nonnull original holders, typed zeroed normal allocations and compatible
noninterfering helpers/barriers are explicit conditions. Runtime formatter
selection, unselected refill/error paths and enclosing root/EOF are unobserved.
"""
from __future__ import annotations

import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import scalar_param_native as scalar
from scripts.game_data.memorypack.pooled_string_list_sources import flag

LABEL='skillRootRecordSources'
DECLARATIONS={
 'Beyond.Gameplay.AttributeModifierData':(
    ('attributeModifiers','Beyond.Gameplay.AttributeModifierData+AttributeModifier[]','array'),
    ('isConvertedAttribute','bool','bool')),
 'Beyond.Gameplay.Core.CastData':(
    ('castAngle','float','single'),('castDistance','Beyond.Blackboard+BlackboardDouble','reference'),
    ('checkCastDistanceType','Beyond.Gameplay.CheckCastDistanceType','enum'),
    ('checkHeightDiff','bool','bool'),('cooldownTime','float','single'),
    ('costData','Beyond.Gameplay.Core.CastData+CostData','reference'),
    ('heightDiffLimit','Beyond.Blackboard+BlackboardDouble','reference'),('maxChargeTime','int','int32'),
    ('rotateType','Beyond.Gameplay.CastRotateType','enum'),('startCdFrame','int','int32'),
    ('useCustomCastDistance','bool','bool')),
 'Beyond.Gameplay.Core.GameplayTagList':(
    ('predefinedTag','System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>','list'),),
}


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def peek(g,size=4):return bytes(g.bytes.get(g.at+i,0)for i in range(size))


def branch(g,near,short,taken):
    if peek(g,len(bytes.fromhex(near)))==bytes.fromhex(near):target=g.relative(near)
    else:
        need('exact-short-branch',bytes.fromhex(short),peek(g,len(bytes.fromhex(short))))
        target=g.relative(short,1)
    need('owned-branch-destination',True,target in g.bytes)
    if taken:g.at=target
    return target


def _store(kind,slot):
    """One exact field store; a managed displacement is never a wire width."""
    prefix={'bool':'88','int32':'89','enum':'89','int64':'4889',
            'reference':'4889','list':'4889','array':'4889','pool':'4889','single':'f30f11'}[kind]
    modrm=('40'if kind=='single'else'41')if slot<128 else('80'if kind=='single'else'81')
    return prefix+modrm+(bytes((slot,)).hex()if slot<128 else struct.pack('<i',slot).hex())


def _field_address(slot):
    return '4883c1'+bytes((slot,)).hex()if slot<128 else'4881c1'+struct.pack('<i',slot).hex()


def direct_record_program(regions,entry,offsets,fields,*,holder='rdi',new=False,null=False):
    """Detected complete direct-original shape; all actual bytes are consumed."""
    need('supported-holder',True,holder in('rdi','rsi'))
    need('literal-path-selection',True,type(new)is bool and type(null)is bool and not(new and null))
    need('finite-field-inventory',True,1<=len(fields)<=64)
    names=[f['fieldName']for f in fields];need('unique-field-names',len(names),len(set(names)))
    occupied=[]
    for f in fields:
        need('known-field-kind',True,f['kind']in('bool','int32','enum','single','int64','reference','list','array','pool'))
        slot=f['fieldOffset'];width=1 if f['kind']=='bool'else 4 if f['kind']in('int32','enum','single')else 8
        need('bounded-named-field-slot',True,type(slot)is int and 16<=slot<4096)
        occupied.extend(range(slot,slot+width))
    need('disjoint-named-fields',len(occupied),len(set(occupied)))
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry);header_reg='sil'if holder=='rdi'else'dil'
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20');ready=flag(g)
    g.take('488bfa'if holder=='rdi'else'488bf2','488bd9');g.branch('0f84',False)
    g.take('837b'+rem+'01');g.branch('0f8c',False)
    g.take('488b43'+cur,'0fb630'if holder=='rdi'else'0fb638','8b6b'+rem,'83ed01');g.branch('0f88',False)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,
        '4080feff'if holder=='rdi'else'4080ffff');branch(g,'0f84','74',null)
    allocation=None;events=[];failures=[];barriers=[];pending=None
    if null:
        if holder=='rdi':
            if peek(g,3)==bytes.fromhex('488bcf'):g.take('488bcf','48c70700000000')
            else:g.take('48c70700000000','488bcf')
        else:g.take('48c70600000000','488bce')
        if peek(g,1)==b'\xe8':barriers.append(g.relative('e8'))
        g.jump('eb',1)
    else:
        g.take('48833f00'if holder=='rdi'else'48833e00');g.branch('0f84',new)
        if new:
            site=g.at;cell=g.relative('488b0d');allocate=g.relative('e8')
            g.take('488be8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');constructor=g.relative('e8')
            g.take('488bcf'if holder=='rdi'else'488bce','48892f'if holder=='rdi'else'48892e')
            barriers.append(g.relative('e8'));g.take('90');g.jump('e9')
            allocation=dict(usageSite=site,usageCell=cell,allocate=allocate,constructor=constructor)
        g.take(('4080fe'if holder=='rdi'else'4080ff')+bytes((len(fields),)).hex());g.branch('0f85',False)
        for index,f in enumerate(fields):
            before=len(g.seen);reader=False;wrapper=None;context=None;delayed=None
            for _ in range(6):
                raw=peek(g,4)
                if raw[:1]==b'\xe8':break
                if raw[:3]==bytes.fromhex('488bcb'):
                    need('one-reader-setup',False,reader);g.take('488bcb');reader=True
                elif raw[:3]in(bytes.fromhex('488b37'),bytes.fromhex('488b3f'),bytes.fromhex('488b3e')):
                    need('one-wrapper-setup',None,wrapper)
                    pattern=raw[:3].hex();allowed=('488b37','488b3f')if holder=='rdi'else('488b3e',)
                    need('actual-byref-holder-load',True,pattern in allowed)
                    if pattern=='488b3f':need('byref-holder-overwrite-only-final',len(fields)-1,index)
                    g.take(pattern);wrapper='rsi'if pattern=='488b37'else'rdi'
                elif raw[:3]==bytes.fromhex('488b15'):
                    need('one-typed-context',None,context);site=g.at;cell=g.relative('488b15')
                    context=dict(instruction=site,cell=cell)
                elif pending and raw in(bytes.fromhex('f30f1140'),bytes.fromhex('f30f1180')):
                    g.take(_store('single',pending['fieldOffset']))
                    pending['storeSite']=g.seen[-1][0];delayed=pending;pending=None
                else:raise ValueError(f'{LABEL}.unproved-source-setup:{f["fieldName"]}:{g.at:#x}:{raw.hex()}')
            need('reader-and-wrapper-setups',True,reader and wrapper is not None)
            need('previous-single-stored-before-next-call',None,pending)
            typed=f['kind']in('enum','reference','list','array')
            need('typed-context-presence',typed,context is not None)
            call=g.at;target=g.relative('e8')
            g.take('4885f6'if wrapper=='rsi'else'4885ff')
            failures.append(branch(g,'0f84','74',False))
            original='rax'if f['kind']=='single'else'rcx'
            g.take(('488b4610'if wrapper=='rsi'else'488b4710')if original=='rax'else
                ('488b4e10'if wrapper=='rsi'else'488b4f10'))
            g.take('4885c0'if original=='rax'else'4885c9');failures.append(branch(g,'0f84','74',False))
            slot=f['fieldOffset'];store=None;barrier=None
            if f['kind']=='single':pending=dict(fieldName=f['fieldName'],fieldOffset=f['fieldOffset'])
            elif f['kind']in('bool','int32','enum','int64'):store=g.at;g.take(_store(f['kind'],slot))
            else:
                store=g.at;g.take(_store(f['kind'],slot),_field_address(slot))
                if peek(g,1)==b'\xe8':barrier=g.relative('e8');barriers.append(barrier)
                else:need('only-final-reference-tail',len(fields)-1,index)
            events.append(dict(memberIndex=index,fieldName=f['fieldName'],kind=f['kind'],fieldOffset=f['fieldOffset'],
                sourceCall=call,sourceTarget=target,typedContext=context,sourceSetup=g.seen[before:],
                resultRegister='xmm0'if f['kind']=='single'else'al'if f['kind']=='bool'else'eax'if f['kind']in('int32','enum')else'rax',
                storeSite=store,delayedPreviousStore=delayed,referenceBarrier=barrier))
        if pending:
            g.take(_store('single',pending['fieldOffset']));pending['storeSite']=g.seen[-1][0]
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f')
    tail=None
    if peek(g,1)==b'\xe9':tail=g.relative('e9');barriers.append(tail)
    else:g.take('c3')
    if barriers:need('one-reference-barrier',1,len(set(barriers)))
    if failures:need('same-owned-null-failure',1,len(set(failures)))
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,nullWrapper=null,
        memberCount=None if null else len(fields),orderedFields=events,allocation=allocation,
        barrierTarget=barriers[0]if barriers else None,normalReturn=True,tailBarrier=tail,
        sameOwnedNullFailure=failures[0]if failures else None,childGrammarsAdmitted=False)


def simple_class_constructor_program(regions,entry,fields,*,holder='rbx'):
    """Typed original allocation, optional own defaults/constructor, holder16."""
    need('constructor-holder-profile',True,holder in('rbx','rdi'))
    g=BytesPath(regions,entry)
    if holder=='rbx':g.take('4053','4883ec20')
    else:g.take('48895c2408','57','4883ec20')
    ready=flag(g);g.take('488bd9'if holder=='rbx'else'488bf9');g.branch('74',False,1)
    usage=g.at;cell=g.relative('488b0d');allocate=g.relative('e8')
    constructor=None;defaults=[]
    if holder=='rdi':
        g.take('488bd8','4885c0');g.branch('74',False,1)
        g.take('33d2','488bc8');constructor=g.relative('e8')
        g.take('488d4f10','48895f10','488b5c2430','4883c420','5f')
    else:
        g.take('4885c0');g.branch('74',False,1);address=False
        for _ in range(32):
            raw=peek(g,3)
            if raw==bytes.fromhex('488943'):break
            if raw==bytes.fromhex('488d4b'):
                need('single-holder-address',False,address);g.take('488d4b10');address=True
            elif raw[:2]==bytes.fromhex('c740'):
                g.take('c740');slot=g.read(1)[0];bits=g.read(4).hex()
                candidates=[f for f in fields if f['fieldOffset']==slot and f['kind']in('int32','enum','single')]
                need('owned-four-byte-constructor-default',1,len(candidates))
                need('one-default-per-field',False,any(x['fieldOffset']==slot for x in defaults))
                defaults.append(dict(fieldName=candidates[0]['fieldName'],fieldOffset=slot,bitsHex=bits))
            else:raise ValueError(f'{LABEL}.constructor-unproved-operation:{g.at:#x}:{raw.hex()}')
        need('complete-holder-address',True,address)
        g.take('48894310','4883c420','5b')
    barrier=g.relative('e9')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,usageSite=usage,usageCell=cell,
        allocate=allocate,originalConstructor=constructor,defaults=defaults,
        wrapperHolderOffset=16,originalReferenceUnchanged=True,barrier=barrier,
        normalReturnViaBarrier=True,wireBytes=0)


def _derive_records(image,pins,definitions,*,holders=None,constructor_holders=None):
    """Fresh nominal source proof shared by finite named record owners."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.pointer_param import owned,methods,registered_pair,leaf
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs,_selected_wrapper,_fast_barrier
    from scripts.game_data.memorypack import primitive_param,pooled_source_helper,buff_ec_profiles_native as ec
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.levelscript_family_regenerate import Build
    selected_inputs(pins);_publication_gate(image,pins)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    need('finite-named-source-owners',True,isinstance(definitions,dict)and 1<=len(definitions)<=32)
    holders={}if holders is None else holders;constructor_holders={}if constructor_holders is None else constructor_holders
    clones=ec.clone_facts(image,pins);record=vector_recorder(image);offsets=scalar.reader_offsets(image,LABEL);result={}
    for type_name,declarations in definitions.items():
        need('finite-named-field-declaration',True,isinstance(type_name,str)and isinstance(declarations,(list,tuple))and 1<=len(declarations)<=64)
        matches=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==type_name]
        need('unique-owned-wrapper:'+type_name,1,len(matches));wrapper=matches[0]
        need('exact-record-order:'+type_name,[(n,t)for n,t,_ in declarations],
            [(m.name,m.declared_type)for m in wrapper.members])
        need('original-reference-type',False,ctx.is_value_type(type_name))
        need('wrapper-holder',(wrapper.name,type_name,16),ctx.field(wrapper.name+'::__instance'))
        mm=methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
        fields=[]
        for n,t,kind in declarations:
            field=ctx.field(type_name+'::'+n);need('owned-original-field',(type_name,t),field[:2])
            fd,=[f for f in md.fields_for(ctx.index.types[type_name])if md.string(f.name_index)==n]
            raw_kind={'bool':2,'int32':8,'int64':10,'single':12,'enum':17,'reference':18,'list':21,'array':29,'pool':14}[kind]
            scalar.ordinary(image,ctx.type_pointer(fd.type_index),raw_kind,LABEL+'.field.'+n,
                reference=kind in('reference','list','array','pool'))
            fields.append(dict(fieldName=n,typeName=t,kind=kind,fieldOffset=field[2]))
        source=owned(image,image.method_pointer_va(mm['Deserialize']));holder=holders.get(type_name,'rsi'if type_name.endswith('.GameplayTagList')else'rdi')
        programs=[direct_record_program(source['regions'],source['pointer'],offsets,fields,holder=holder,**path)
            for path in({},{'new':True},{'null':True})]
        pair=derive_pair(image,type_name,wrapper.name);forward=registered_pair(image,pair,wrapper,label=LABEL+'.pair')
        scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(type_name,18,False),[],LABEL+'.getter')
        getter=leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3'])
        ctor=owned(image,image.method_pointer_va(mm['.ctor']))
        constructor=simple_class_constructor_program(ctor['regions'],ctor['pointer'],fields,
            holder=constructor_holders.get(type_name,'rdi'if type_name.endswith('.GameplayTagList')else'rbx'))
        alloc=programs[1]['allocation'];need('selected-wrapper-constructor',ctor['pointer'],alloc['constructor'])
        usage=derive_typed_usage_context(image,alloc['usageSite']-base,label=LABEL+'.wrapperAllocation')
        need('wrapper-allocation-type',(1,wrapper.name),(usage['tag'],usage['typeName']))
        original=derive_typed_usage_context(image,constructor['usageSite']-base,label=LABEL+'.originalAllocation')
        need('original-allocation-type',(1,type_name),(original['tag'],original['typeName']))
        scalar.ordinary(image,ctx.type_pointer(original['typeIndex']),18,LABEL+'.originalAllocation',reference=True)
        need('same-typed-allocator',alloc['allocate'],constructor['allocate'])
        if constructor['originalConstructor']is not None:
            om,=[m for m in md.methods_for(ctx.index.types[type_name])if md.string(m.name_index)=='.ctor'and m.parameter_count==0]
            need('named-original-constructor',image.method_pointer_va(om),constructor['originalConstructor'])
            scalar.owned_method_abi(image,ctx,om.index,om.declaring_type,('void',1,False),[],LABEL+'.originalConstructor')
        barrier,barrier_proof,_=_fast_barrier(image,constructor['barrier'])
        for program in programs:need('same-source-barrier',constructor['barrier'],program['barrierTarget'])
        children=[];primitive={};contexts={}
        for event,field in zip(programs[0]['orderedFields'],fields,strict=True):
            kind=field['kind'];target=event['sourceTarget'];name=field['fieldName']
            if kind in('bool','int32','single','enum'):
                helper=record(target-base)
                if kind=='bool':scalar.boolean_source(image,helper,offsets,LABEL+'.'+name)
                elif kind=='single':primitive_param.single_source(image,helper,offsets)
                else:scalar.integer_source(image,helper,offsets,LABEL+'.'+name)
                primitive[name]=helper
            elif kind=='int64':
                helper=record(target-base)
                scalar.integer_source(image,helper,offsets,LABEL+'.'+name,width=8)
                primitive[name]=dict(sourceWindows=owned(image,target)['windows'],source=helper,
                    bufferedWireBytes=8,rawBitsUnchanged=True,resultRegister='rax')
            elif kind=='pool':
                primitive[name]=pooled_source_helper.validate_on_image(image,target,pins)
            if event['typedContext']is not None:
                typed=derive_typed_usage_context(image,event['typedContext']['instruction']-base,label=LABEL+'.'+name)
                method='ReadArray'if kind=='array'else'ReadPackable'if kind=='list'else'ReadUnmanaged'if kind=='enum'else'ReadValue'
                argument=field['typeName'][:-2]if kind=='array'else field['typeName']
                bind_typed_read(image,typed,method_name=method,argument=argument,
                    kind={'enum':17,'reference':18,'list':21,'array':18}[kind],reference=kind!='enum')
                contexts[name]=typed
                if kind in('reference','list'):
                    need('exact-reference-child-source-target',clones[method]['targetRva'],target-base)
                if kind=='enum':primitive[name+'Backing']=Build(image,pins).derive_enum(dict(typeName=argument,backingType='System.Int32',width=4))
                else:children.append(dict(fieldName=name,kind=kind,typeName=field['typeName'],typedRequest=typed,
                    sourceTargetRva=target-base,childGrammarAdmitted=False))
        result[type_name]=dict(typeName=type_name,wrapperName=wrapper.name,memberCount=len(fields),fields=fields,
            sourceWindows=source['windows'],programs=programs,registeredPair=pair,forwarding=forward,getter=getter,
            constructorWindows=ctor['windows'],constructor=constructor,wrapperAllocation=usage,originalAllocation=original,
            barrier=barrier,barrierProof=barrier_proof,primitiveSources=primitive,typedRequests=contexts,
            requiredChildJoins=children,wholeRecordAdmitted=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-record-source.v1',nativeInputs=pins,
        status='proved-record-callers-requires-child-joins',records=result,
        evidenceBoundary=dict(exact='Finite named current child record MC/FF/new paths, original allocation/holder, unchanged typed stores, scalar sources and complete selected returns.',
            conditional=__doc__,unresolved=['listed positive child grammars','runtime formatter/provider/MethodInfo selection','whole root/physical EOF']))))


def derive_direct_record(image,pins,type_name,declarations,*,holder='rdi',constructor_holder='rbx'):
    """Prove one explicitly named caller, never its delegated child grammars.

    The caller owns its finite nominal declaration. Metadata must match every
    field, actual ABI, managed slot and source transfer; no caller-supplied
    cached component or field width is accepted as native evidence.
    """
    return _derive_records(image,pins,{type_name:declarations},holders={type_name:holder},
        constructor_holders={type_name:constructor_holder})['records'][type_name]


def derive(image,pins,*,types=None):
    """Fresh complete root-child callers, with their explicit finite owners."""
    types=list(DECLARATIONS)if types is None else list(types)
    need('finite-source-owner-allowlist',True,bool(types)and len(types)==len(set(types))and set(types)<=set(DECLARATIONS))
    return _derive_records(image,pins,{name:DECLARATIONS[name]for name in types})
