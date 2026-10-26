"""Cinemachine's own seven-member impulse envelope wrapper source.

Two curve references, three Singles and two Booleans occupy managed32 with
two padding bytes. Its wire order is proved from the reader, never that size.
The canonical value32 adapter and independent curve grammar remain separate.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

TYPE='Cinemachine.CinemachineImpulseManager+EnvelopeDefinition'
WRAPPER='Beyond.MemoryPack.Cinemachine_CinemachineImpulseManager_EnvelopeDefinitionForMemoryPack'
CURVE='UnityEngine.AnimationCurve'
MEMBERS=(('m_AttackShape',CURVE),('m_AttackTime','float'),('m_DecayShape',CURVE),('m_DecayTime','float'),
         ('m_HoldForever','bool'),('m_ScaleWithImpact','bool'),('m_SustainTime','float'))


def need(key,condition,detail=None):
    if not condition:raise ValueError('impulseEnvelopeSource.'+key+':'+str(detail)[:700])


def layout(image,ctx):
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper
    from scripts.game_data.memorypack.skill_root_value_sources import value_layout
    wrapper=_selected_wrapper(image,WRAPPER);need('own-nominal-value',wrapper.wrapped_type==TYPE)
    fields={name:(typ,18 if typ==CURVE else 12 if typ=='float'else 2,8 if typ==CURVE else 4 if typ=='float'else 1)for name,typ in MEMBERS}
    result=value_layout(image,ctx,TYPE,wrapper,managed_bytes=32,fields=fields)
    expected=dict(m_AttackShape=0,m_DecayShape=8,m_AttackTime=16,m_SustainTime=20,m_DecayTime=24,m_ScaleWithImpact=28,m_HoldForever=29)
    need('exact-current-unboxed-slots',{n:r['unboxedOffset']for n,r in result['fields'].items()}==expected)
    return dict(result,referenceLaneOffsets=[0,8],paddingByteRanges=[[30,32]])


def wrapper_program(regions,entry,offsets,*,new=False,null=False):
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    need('literal-wrapper-modes',type(new)is bool and type(null)is bool and not(new and null))
    cur,rem,adv,used=(bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec20')
    ready=flag(g);g.take('488bfa','488bd9');g.branch('0f84',False)
    g.take('837b'+rem+'01');g.branch('0f8c',False)
    g.take('488b43'+cur,'0fb630','8b6b'+rem,'83ed01');g.branch('0f88',False)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080feff');g.branch('0f84',null)
    calls={};sites={};usages={};guards=[]
    def call(role):
        at=g.at;target=g.relative('e8')
        if role in calls:need('same-actual-helper:'+role,calls[role]==target)
        calls[role]=target;sites.setdefault(role,[]).append(at)
    def typed(role):
        at=g.at;cell=g.relative('488b15');usages[role]=dict(instruction=at,cell=cell)
    def guard(opcode):
        g.take(opcode);guards.append(_nonnull(g))
    if null:
        g.take('488bcf','48c70700000000');call('barrier');g.jump('eb',1)
    else:
        g.take('48833f00');g.branch('0f84',new);allocation=None
        if new:
            at=g.at;cell=g.relative('488b0d');allocation=dict(instruction=at,cell=cell)
            call('allocate');guard('4885c0')
            g.take('0f57c0','488bcf','0f114010','0f114020','488907');call('barrier');g.take('90');g.jump('e9')
        g.take('4080fe07');g.branch('0f85',False)
        typed('attack');g.take('488bcb','488b37');call('curve');guard('4885f6')
        g.take('488d4e10','488901');call('barrier')
        g.take('488b37','488bcb');call('single');guard('4885f6');g.take('f30f114620')
        g.take('488bcb');typed('decay');g.take('488b37');call('curve');guard('4885f6')
        g.take('488d4e18','48894618');call('barrier')
        g.take('488b37','488bcb');call('single');guard('4885f6');g.take('f30f114628')
        for slot in('2d','2c'):
            g.take('488bcb','488b37');call('boolean');guard('4885f6');g.take('8846'+slot)
        g.take('488bcb','488b3f');call('single');guard('4885ff');g.take('f30f114724')
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,wrapperFF=null,
        sourceHeaderBytes=1,headerReaderEffects=dict(currentPtr=1,bufferLength=-1,advancedCount=1,consumed=1),
        memberCount=None if null else 7,actualCalls=calls,callSites=sites,typedUsages=usages,
        allocation=None if null else allocation,wrapperReferenceCleared=null,newWrapperZeroedBytes=32 if new else 0,
        originalDefaultAdmitted=False,allIntegerNonvolatilesRestored=True,entryRspRestored=True,normalReturn=True,
        ownedNullExits=guards,childGrammarAdmitted=False)


def derive_wrapper(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper,_fast_barrier
    from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_primitive_sources import derive as primitive
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrapper=_selected_wrapper(image,WRAPPER);need('exact-current-seven-members',[(m.name,m.declared_type)for m in wrapper.members]==list(MEMBERS))
    nominal=layout(image,ctx);mm=pointer.methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(TYPE,17,False),[],'impulseEnvelope.Getter')
    getter=pointer.leaf(image,image.method_pointer_va(mm['GetValue']),['0F104210','488BC1','0F104A20','0F1101','0F114910','C3'])
    defaults={}
    for role in('.ctor','CreateInstance'):
        scalar.owned_method_abi(image,ctx,mm[role].index,wrapper.type_definition,('void',1,False),[],'impulseEnvelope.'+role)
        defaults[role]=pointer.leaf(image,image.method_pointer_va(mm[role]),['0F57C0','0F114110','0F114120','C3'])
    body=pointer.owned(image,image.method_pointer_va(mm['Deserialize']));offsets=scalar.reader_offsets(image,'impulseEnvelope')
    paths=[wrapper_program(body['regions'],body['pointer'],offsets,**p)for p in({},{'new':True},{'null':True})]
    symbols={}
    for p in paths:
        for role,target in p['actualCalls'].items():
            if role in symbols:need('same-path-helper:'+role,symbols[role]==target)
            symbols[role]=target
    allocation=derive_typed_usage_context(image,paths[1]['allocation']['instruction']-base,label='impulseEnvelope.allocate')
    need('own-wrapper-allocation',(allocation['tag'],allocation['typeName'])==(1,WRAPPER))
    requests={r:derive_typed_usage_context(image,u['instruction']-base,label='impulseEnvelope.'+r)for r,u in paths[0]['typedUsages'].items()}
    readers=reference_reader_abi(image,pins)
    for role,request in requests.items():
        bind_typed_read(image,request,method_name='ReadValue',argument=CURVE,kind=18,reference=True)
        need('same-current-reference-reader',request['methodSpec'][0]==readers['referenceReaderMethodDefinition']and symbols['curve']-base==readers['referenceReaderTargetRva'])
    single=primitive(image,symbols['single'],'float32',offsets);boolean=primitive(image,symbols['boolean'],'bool',offsets)
    barrier,barrier_program,_=_fast_barrier(image,symbols['barrier'])
    pair=derive_pair(image,TYPE,WRAPPER);forwarding=pointer.registered_pair(image,pair,wrapper,label='impulseEnvelope.pair')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.impulse-envelope-wrapper-source.v1',nativeInputs=pins,
        status='proved-envelope-wrapper-source-requires-value-and-curve-joins',typeName=TYPE,wrapperName=WRAPPER,
        layout=nominal,getter=getter,defaults=defaults,programs=paths,sourceWindows=body['windows'],registeredPair=pair,forwarding=forwarding,
        requests=requests,referenceReaders=readers,singleSource=single,booleanSource=boolean,barrierWindows=barrier,barrierProgram=barrier_program,
        symbolRvas={k:v-base for k,v in symbols.items()},originalDefaultValueAdmitted=False,childGrammarAdmitted=False,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        requiredJoins=['actual nominal hidden32 ReadValue/provider/canonical value adapter/slot5/interface transfer',
                       'independent Unity AnimationCurve child grammar and actual parent field/local/store/frame'])))
