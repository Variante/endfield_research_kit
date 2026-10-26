"""Exact PullAttenuation value source, separate from list and wire children.

The selected value is managed16 with one reference at lane0, a Single at lane8
and four padding bytes. Its wrapper reads MC2 as captured Single4 followed by
the independently typed BlackboardSuperArmorValue reference. The source's FF
clears the wrapper reference; original default16 requires its separate value
adapter. Own hidden GetValue copies all16 unchanged, including padding, while
the wrapper constructor/CreateInstance independently zero all16. Neither fact
assigns a wire width to the value. Ready coherent contexts/callbacks, normal
typed zeroed allocation/helpers, disabled collector and buffered disjoint
storage remain conditions. Runtime attenuation/armor behavior, provider choice,
positive collection and enclosing action/root/physical EOF stay unresolved.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_child_bindings import need

SCHEMA='endfield.skill-pull-attenuation-source.v1'
TYPE='Beyond.Gameplay.Core.PullComponent+PullAttenuationValueConfig'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_PullComponent_PullAttenuationValueConfigForMemoryPack'
REFERENCE='Beyond.Gameplay.Core.BlackboardSuperArmorValue'
CAPABILITY='skill-pull-attenuation-value'
LIST='skill-action-pull-attenuation-list'
CHILD='skill-blackboard-super-armor-value'
ORDER=[dict(fieldName='attenuationFactor',kind='single-bits',childCapability=None),
    dict(fieldName='superArmorValue',kind='record',childCapability=CHILD)]


def wrapper_program(regions,entry,s,*,new=False,null=False):
    """Complete selected wrapper paths; no original-value default admission."""
    need('pull-literal-wrapper-path',True,type(new)is bool and type(null)is bool and not(new and null))
    g=BytesPath(regions,entry);g.take('48895c2418','57','4883ec20');ready=flag(g)
    g.take('488bda','488bf9');g.branch('0f84',False)
    g.take('488d542430','c644243000','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null)
    allocation=None;usage=None
    if null:
        g.take('488bcb','48c70300000000');g.call(s['barrier']);g.take('90');g.jump('e9')
    else:
        g.take('4889742438','48833b00');g.branch('0f84',new)
        if new:
            at=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False)
            g.take('0f57c0','488bcb','0f114010','488903');g.call(s['barrier']);g.take('90');g.jump('e9')
            allocation=dict(instruction=at,cell=cell,wrapperValueOffset=16,zeroedManagedBytes=16)
        g.take('0fb6742430','4080fe02');g.branch('0f85',False)
        g.take('488b33','488bcf');single=g.at;g.call(s['single']);g.take('4885f6');g.branch('74',False,1)
        g.take('488b1b','488bcf','f30f114618');at=g.at;cell=g.relative('488b15');usage=dict(instruction=at,cell=cell)
        reference=g.at;g.call(s['reference']);g.take('4885db');g.branch('74',False,1)
        g.take('488d4b10','488901');g.call(s['barrier']);g.take('488b742438')
    g.take('488b5c2440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,ff=null,allocation=allocation,
        referenceUsage=usage,memberCount=None if null else 2,wireHeaderBytes=1,
        fieldWireBytes=[]if null else[4,None],originalDefaultValueAdmitted=False,
        wrapperReferenceCleared=null,hiddenValueBytes=16,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rdi']+([]if null else['rsi']),normalReturn=True)


def require_reference(component,pins):
    need('pull-same-reference-native-inputs',pins,component.get('nativeInputs'))
    cap=component['capabilities'][CHILD]
    need('pull-own-exact-ordinary-child',True,cap.get('typeName')==REFERENCE
        and all(cap.get(k)is True for k in('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    return cap


def _derive_wrapper(image,pins,reference):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param
    from scripts.game_data.memorypack.pointer_param import methods,owned,leaf,registered_pair
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_root_value_sources import value_layout
    from scripts.game_data.memorypack.skill_root_child_bindings import bind_read_value
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper,_fast_barrier
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    require_reference(reference,pins);wrapper=_selected_wrapper(image,WRAPPER)
    need('pull-selected-exact-nominal',TYPE,wrapper.wrapped_type)
    need('pull-plain-nongeneric-value-parent',('System.ValueType',-1),(ctx.parent(TYPE),ctx.index.types[TYPE].generic_container_index))
    scalar.ordinary(image,ctx.type_pointer(ctx.index.types[TYPE].byval_type_index),17,'pullAttenuation.value')
    need('pull-complete-literal-members',[('attenuationFactor','float'),('superArmorValue',REFERENCE)],
        [(m.name,m.declared_type)for m in wrapper.members])
    layout=value_layout(image,ctx,TYPE,wrapper,managed_bytes=16,
        fields={'superArmorValue':(REFERENCE,18,8),'attenuationFactor':('float',12,4)})
    need('pull-exact-reordered-layout',dict(superArmorValue=(0,16,8),attenuationFactor=(8,24,4)),
        {n:(f['unboxedOffset'],f['wrapperOffset'],f['bytes'])for n,f in layout['fields'].items()})
    layout.update(referenceLaneOffsets=[0],paddingByteRanges=[[12,16]])
    mm=methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    pair=derive_pair(image,TYPE,WRAPPER);registration=registered_pair(image,pair,wrapper,label='pullAttenuation.pair')
    scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(TYPE,17,False),[],'pullAttenuation.getter')
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['0F104210','488BC1','0F1101','C3'])
    defaults={}
    for role in('.ctor','CreateInstance'):
        scalar.owned_method_abi(image,ctx,mm[role].index,wrapper.type_definition,('void',1,False),[],'pullAttenuation.'+role)
        defaults[role]=leaf(image,image.method_pointer_va(mm[role]),['0F57C0','0F114110','C3'])
    body=owned(image,image.method_pointer_va(mm['Deserialize']));by={int(r['va'],16):r for r in body['rows']};entry=body['pointer']
    def call(at):
        row=by[at];raw=bytes.fromhex(row['bytes']);need('pull-actual-owned-E8',(5,232),(len(raw),raw[0]));return control_transfer(row)['target']
    new=control_transfer(by[entry+64])['target']
    s=dict(header=call(entry+42),single=call(entry+91),reference=call(entry+119),barrier=call(entry+136),allocate=call(new+7))
    programs=[wrapper_program(body['regions'],entry,s,**path)for path in({},{'new':True},{'null':True})]
    allocation=derive_typed_usage_context(image,programs[1]['allocation']['instruction']-base,label='pullAttenuation.allocation')
    need('pull-own-wrapper-allocation',(1,WRAPPER),(allocation['tag'],allocation['typeName']))
    scalar.ordinary(image,ctx.type_pointer(allocation['typeIndex']),18,'pullAttenuation.allocation',reference=True)
    request=derive_typed_usage_context(image,programs[0]['referenceUsage']['instruction']-base,label='pullAttenuation.child')
    typed_reference=bind_typed_read(image,request,method_name='ReadValue',argument=REFERENCE,kind=18,reference=True)
    binding=bind_read_value(pins,dict(fieldName='superArmorValue',typeName=REFERENCE,typedRequest=request,
        sourceTargetRva=s['reference']-base),reference,CHILD)
    offsets=scalar.reader_offsets(image,'pullAttenuation');record=vector_recorder(image)
    header=record(s['header']-base);primitive_param.object_header_source(image,header,offsets)
    single=record(s['single']-base);primitive_param.single_source(image,single,offsets)
    barrier,barrier_program,_=_fast_barrier(image,s['barrier'])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-pull-wrapper-source-requires-value-adapter',nativeInputs=pins,
        typeName=TYPE,wrapperName=WRAPPER,layout=layout,registeredPair=pair,registration=registration,getter=getter,defaults=defaults,
        sourceWindows=body['windows'],programs=programs,allocationUsage=allocation,referenceRequest=request,referenceBinding=binding,typedReference=typed_reference,
        headerSource=header,singleSource=single,barrierWindows=barrier,barrierProgram=barrier_program,
        symbolRvas={n:v-base for n,v in s.items()},referenceChild=reference,wireOrder=ORDER,
        positiveCollectionAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own reordered/padded nominal managed16, zero16 defaults/hidden getter, fresh registered wrapper forwarding, complete MC2/new/FF caller and exact Single/ordinary SuperArmor source-to-field join.',
            conditional=__doc__,structuralOnly='Stored pull attenuation and armor configuration.',
            unresolved=['canonical value adapter/default16 transfer','positive list callback/Add/induction','actual enclosing action/root/EOF','live provider/behavior']))))
