"""Own CameraControlStateInitialParam wrapper source and managed24 layout.

Four Boolean and three Single wire fields are reordered within managed24 and
contain padding. The marshaled native size is a separate ABI measurement.
Own hidden GetValue copies every managed byte, while ctor/CreateInstance and
the selected new-wrapper path zero24. FF clears only the wrapper reference;
default Original24 requires its separate actual value adapter. Ready coherent
contexts, normal typed allocation/helpers, disabled collector and stable
disjoint buffered storage remain conditions. This owns no enclosing field,
wire value capability, runtime camera behavior or physical EOF.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPE='Beyond.Gameplay.View.CameraControlStateInitialParam'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_View_CameraControlStateInitialParamForMemoryPack'
CAPABILITY='skill-camera-initial-param'
MEMBERS=(('applyHorizontalAngle','bool'),('applyVerticalValue','bool'),('applyZoomScale','bool'),
    ('horizontalAngle','float'),('horizontalAngleRelativeToCharacter','bool'),('verticalValue','float'),('zoomScale','float'))
ORDER=[dict(fieldName=n,kind='bool-byte'if t=='bool'else'float32-bits',childCapability=None)for n,t in MEMBERS]


def getter_program(regions,entry):
    g=BytesPath(regions,entry);g.take('0f104210','488bc1','f20f104a20','0f1101','f20f114910','c3')
    return dict(selectedBytes=g.seen,managedBytes=24,wrapperRegister='rdx',wrapperOffset=16,
        hiddenOutputRegister='rcx',sameHiddenOutputReturnedInRax=True,
        slices=[dict(sourceOffset=0,outputOffset=0,bytes=16),dict(sourceOffset=16,outputOffset=16,bytes=8)],
        references=[],normalReturn=True,entryRspRestored=True)


def default_program(regions,entry):
    g=BytesPath(regions,entry);g.take('0f57c0','33c0','0f114110','48894120','c3')
    return dict(selectedBytes=g.seen,managedBytes=24,wrapperOffset=16,zeroByteRanges=[[0,16],[16,24]],
        references=[],normalReturn=True,entryRspRestored=True)


def wrapper_program(regions,entry,slots,*,new=False,null=False):
    need('camera-initial-literal-path',True,type(new)is bool and type(null)is bool and not(new and null))
    need('camera-initial-all-named-fields',set(n for n,t in MEMBERS),set(slots))
    need('camera-initial-disp8-owned-fields',True,all(type(n)is int and 16<=n<=39 for n in slots.values()))
    g=BytesPath(regions,entry);g.take('48895c2410','4889742418','57','4883ec20');ready=flag(g)
    g.take('488bda','488bf9');g.branch('75',True,1)
    calls={};sites={}
    def call(role):
        site=g.at;target=g.relative('e8')
        if role in calls:need('camera-initial-same-actual-helper:'+role,calls[role],target)
        calls[role]=target;sites.setdefault(role,[]).append(site)
    g.take('488d542430','c644243000','488bcf');call('header');g.take('84c0');g.branch('0f84',null)
    allocation=None
    if null:
        g.take('488bcb','48c70300000000');call('barrier')
    else:
        g.take('48833b00');g.branch('75',not new,1)
        if new:
            at=g.at;cell=g.relative('488b0d');call('allocate');g.take('4885c0');g.branch('0f84',False)
            g.take('33c9','0f57c0','0f114010','48894820','488bcb','488903');call('barrier')
            allocation=dict(instruction=at,cell=cell,zeroedManagedBytes=24,wrapperValueOffset=16)
        g.take('807c243007');g.branch('0f85',False)
        for index,(name,typ)in enumerate(MEMBERS):
            if index==0:g.take('488b33','488bcf')
            elif index==6:pass  # Last call arguments precede the prior Single store.
            else:g.take('488bcf','488b33')
            call('boolean'if typ=='bool'else'single')
            g.take('4885db'if index==6 else'4885f6');g.branch('74',False,1)
            if index==5:g.take('488b1b','488bcf')
            slot=bytes((slots[name],)).hex()
            g.take(('8846'if typ=='bool'else'f30f1143'if index==6 else'f30f1146')+slot)
        g.jump('eb',1)
    g.take('488b5c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,wrapperFF=null,
        allocation=allocation,actualCalls=calls,callSites=sites,memberCount=None if null else 7,
        orderedReads=[]if null else ORDER,wireBytes=1 if null else 17,managedBytes=24,
        wrapperReferenceCleared=null,originalDefaultValueAdmitted=False,
        entryRspRestored=True,allIntegerNonvolatilesRestored=True,normalReturn=True)


def derive_wrapper(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param
    from scripts.game_data.memorypack.pointer_param import methods,owned,leaf,registered_pair
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_root_value_sources import value_layout
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper,_fast_barrier
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrapper=_selected_wrapper(image,WRAPPER);need('camera-initial-selected-original',TYPE,wrapper.wrapped_type)
    need('camera-initial-own-members',list(MEMBERS),[(m.name,m.declared_type)for m in wrapper.members])
    need('camera-initial-plain-value-base',('System.ValueType',-1),(ctx.parent(TYPE),ctx.index.types[TYPE].generic_container_index))
    fields={n:(t,2 if t=='bool'else 12,1 if t=='bool'else 4)for n,t in MEMBERS}
    layout=value_layout(image,ctx,TYPE,wrapper,managed_bytes=24,fields=fields)
    occupied={i for f in layout['fields'].values()for i in range(f['unboxedOffset'],f['unboxedOffset']+f['bytes'])}
    need('camera-initial-owned-field-bytes',16,len(occupied));padding=[]
    for at in sorted(set(range(24))-occupied):
        if padding and padding[-1][1]==at:padding[-1][1]+=1
        else:padding.append([at,at+1])
    layout.update(referenceLaneOffsets=[],paddingByteRanges=padding)
    mm=methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    pair=derive_pair(image,TYPE,WRAPPER);forwarding=registered_pair(image,pair,wrapper,label='cameraInitial.pair')
    scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(TYPE,17,False),[],'cameraInitial.GetValue')
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['0F104210','488BC1','F20F104A20','0F1101','F20F114910','C3'])
    getter_semantics=getter_program([(base+at,bytes.fromhex(h))for at,h in getter['instructions']],image.method_pointer_va(mm['GetValue']))
    defaults={}
    for name in('.ctor','CreateInstance'):
        scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,('void',1,False),[],'cameraInitial.'+name)
        defaults[name]=leaf(image,image.method_pointer_va(mm[name]),['0F57C0','33C0','0F114110','48894120','C3'])
    body=owned(image,image.method_pointer_va(mm['Deserialize']));slots={n:f['wrapperOffset']for n,f in layout['fields'].items()}
    paths=[wrapper_program(body['regions'],body['pointer'],slots,**choice)for choice in({},{'new':True},{'null':True})]
    symbols={}
    for path in paths:
        for name,target in path['actualCalls'].items():
            if name in symbols:need('camera-initial-identical-path-helper:'+name,symbols[name],target)
            symbols[name]=target
    allocation=derive_typed_usage_context(image,paths[1]['allocation']['instruction']-base,label='cameraInitial.allocation')
    need('camera-initial-actual-wrapper-allocation',(1,WRAPPER),(allocation['tag'],allocation['typeName']))
    offsets=scalar.reader_offsets(image,'cameraInitial');record=vector_recorder(image)
    header=record(symbols['header']-base);primitive_param.object_header_source(image,header,offsets)
    boolean=record(symbols['boolean']-base);scalar.boolean_source(image,boolean,offsets,'cameraInitial.Boolean')
    single=record(symbols['single']-base);primitive_param.single_source(image,single,offsets)
    barrier,barrier_program,_=_fast_barrier(image,symbols['barrier']);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-camera-initial-wrapper-source.v1',
        status='proved-camera-initial-wrapper-requires-value-adapter',nativeInputs=pins,typeName=TYPE,wrapperName=WRAPPER,
        layout=layout,registeredPair=pair,forwarding=forwarding,getter=getter,getterProgram=getter_semantics,defaults=defaults,
        sourceWindows=body['windows'],programs=paths,allocationUsage=allocation,headerSource=header,booleanSource=boolean,
        singleSource=single,barrierWindows=barrier,barrierProgram=barrier_program,symbolRvas={n:v-base for n,v in symbols.items()},
        wireOrder=ORDER,originalDefaultValueAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own managed24/padding, complete MC7 primitive-to-named-field/new/FF source and return frames, hidden getter copy24, own zero24 defaults and fresh registered wrapper forwarding.',
            conditional=__doc__,structuralOnly='Stored camera initial parameters.',
            unresolved=['actual value24 canonical adapter/default/Reader/dispatcher/conversion','actual parent whole-field transfer','enclosing action/root/physical EOF','runtime camera/provider choice']))))
