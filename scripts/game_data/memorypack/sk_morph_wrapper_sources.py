"""Exact SkMorph MC5 wire source, independent from its managed40 value."""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import sk_morph_value_sources as value


def need(check,condition):
    if not condition:raise ValueError('skMorphWrapper.'+check)


def program(regions,entry,*,new=False,null=False):
    need('literal-selected-path',type(new)is bool and type(null)is bool and not(new and null))
    g=BytesPath(regions,entry);symbols={};requests=[]
    def call(role):
        at=g.at;target=g.relative('e8');need('same-helper:'+role,role not in symbols or symbols[role]==target)
        symbols[role]=target;return at
    g.take('48895c2418','57','4883ec20');ready=g.relative('803d');g.take('00','488bda','488bf9');g.branch('0f84',False)
    g.take('488d542430','c644243000','488bcf');call('header');g.take('84c0');g.branch('0f84',null)
    allocation=None
    if null:g.take('488bcb','48c70300000000');call('barrier');g.take('90');g.jump('e9')
    else:
        g.take('4889742438','48833b00');g.branch('0f84',new)
        if new:
            at=g.at;cell=g.relative('488b0d');call('allocate');g.take('4885c0');g.branch('0f84',False)
            g.take('33c9','0f57c0','0f114010','0f114020','48894830','488bcb','488903');call('barrier');g.take('90');g.jump('e9')
            allocation=dict(instructionVa=at,cellVa=cell,zeroedSlices=value.SLICES)
        g.take('0fb6742430','4080fe05');g.branch('0f85',False)
        for index,role,store in((0,'hash','48894620'),(1,'tag','894618'),(2,'enum','894614'),(3,'transition','48894630')):
            if index:g.take('488bcf')
            at=g.at;cell=g.relative('488b15')
            if index==0:g.take('488bcf')
            g.take('488b33');callsite=call(role);g.take('4885f6');g.branch('74',False,1);g.take(store)
            requests.append(dict(memberIndex=index,role=role,instructionVa=at,cellVa=cell,sourceCallInstructionVa=callsite,sourceTargetVa=symbols[role]))
        g.take('488bcf','488b1b');boolsite=call('boolean');g.take('4885db');g.branch('74',False,1)
        g.take('488b742438','884310')
    g.take('488b5c2440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,newWrapper=new,wrapperNull=null,metadataReadyFlagVa=ready,allocation=allocation,
        actualTypedRequests=requests,symbols=symbols,booleanSourceInstructionVa=None if null else boolsite,
        memberCount=None if null else 5,serializedFieldOrder=[]if null else[
            'motionAssetPathHash','motionTag','motionType','transitionInfo','useAssetDirectly'],
        wireBytes=1 if null else 26,managedBytes=40,existingRuntimeObjectPreserved=not null and not new,
        freshRuntimeObjectZeroed=new,normalReturn=True,entryRspRestored=True,allIntegerNonvolatilesRestored=True,
        actualRuntimeSelectionObserved=False,wholeOwnerAdmitted=False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,scalar_param_native as scalar,generated_primitive_sources as primitive
    from scripts.game_data.memorypack import animation_mask_sources as hash_source,nominal_int32_value_sources as tag_source
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.buff_ec_profiles_native import contexts
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.animation_transition_value_sources import derive_raw
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    nominal=value.layout(image,ctx);wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==value.WRAPPER]
    need('own-five-generated-members',[(m.name,m.declared_type)for m in wrapper.members]==[
        ('motionAssetPathHash','Beyond.Resource.StringPathHash'),('motionTag','Beyond.Gameplay.Core.GameplayTag'),
        ('motionType','Beyond.Montage.SkMorphMotionType'),('transitionInfo',value.TRANSITION),('useAssetDirectly','bool')])
    method=pointer.methods(image,wrapper)['Deserialize'];primitive_param.reader_abi(image,ctx,method,wrapper)
    at=image.method_pointer_va(method);body=pointer.owned(image,at);programs=[program(body['regions'],at,**p)for p in({},dict(new=True),dict(null=True))]
    first=programs[0];symbols=first['symbols'];need('same-positive-helper-requests',programs[1]['actualTypedRequests']==first['actualTypedRequests'])
    offsets=scalar.reader_offsets(image,'skMorphWrapper');header=primitive_param.object_header_source(image,vector_recorder(image)(symbols['header']-base,fragments=True),offsets)
    actual_contexts={r['instructionRva']:r for r in contexts(image,body['rows'],allow_value_generic_arguments=True)}
    expected=[('Beyond.Resource.StringPathHash','ReadUnmanaged'),('Beyond.Gameplay.Core.GameplayTag','ReadUnmanaged'),
        ('Beyond.Montage.SkMorphMotionType','ReadUnmanaged'),(value.TRANSITION,'ReadUnmanaged')]
    requests=[];children={}
    for event,(name,read_method)in zip(first['actualTypedRequests'],expected,strict=True):
        usage=derive_typed_usage_context(image,event['instructionVa']-base,label='skMorphWrapper.'+event['role'])
        need('own-actual-nominal-request',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
            ==(6,'MemoryPack.MemoryPackReader',read_method,[],[name]))
        binding=bind_typed_read(image,usage,method_name=read_method,argument=name,kind=17)
        target=event['sourceTargetVa'];role=event['role']
        if role=='hash':
            own=pointer.owned(image,target);children[role]=dict(program=hash_source.hash_program(own['regions'],target,offsets),
                windows=own['windows'],regions=[[a-base,h.hex()]for a,h in own['regions']])
        elif role=='tag':children[role]=tag_source.derive(image,pins,context=actual_contexts[event['instructionVa']-base],source_target=target)
        elif role=='enum':children[role]=primitive.derive(image,target,'int32',offsets)
        else:children[role]=derive_raw(image,pins,typed_request=usage,source_target=target)
        requests.append(dict(typedRequest=usage,typedBinding=binding,**event))
    children['boolean']=primitive.derive(image,symbols['boolean'],'bool',offsets)
    allocations=[]
    for p in programs:
        if p['allocation']:
            use=derive_typed_usage_context(image,p['allocation']['instructionVa']-base,label='skMorphWrapper.allocation')
            need('own-wrapper-allocation',use.get('tag')==1 and use.get('typeName')==value.WRAPPER);allocations.append(use)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.sk-morph-wrapper-source.v1',status='validated-conditional-sk-morph-MC5-source',
        nativeInputs=pins,typeName=value.TYPE,wrapperName=value.WRAPPER,memberCount=5,wireBytes=26,nullWireBytes=1,
        originalDefaultValueAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(layout=nominal,method=[method.index,value.WRAPPER,'Deserialize',at-base],windows=body['windows'],regions=[[a-base,h.hex()]for a,h in body['regions']],
            programs=programs,requests=requests,allocations=allocations,children=children,objectHeader=header,readerOffsets=offsets,
            symbolRvas={k:v-base for k,v in symbols.items()}),evidenceBoundary=__doc__)))
