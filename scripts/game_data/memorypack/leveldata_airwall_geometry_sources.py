"""Exact old buffered air-wall geometry and Vector2 setter programs.

Nominal layouts, actual source identities and collection framing are separate
joins supplied by the owning derivation. No runtime wall state is inferred.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag


def range_program(regions,entry,s,*,null=False,new=False):
    if type(null)is not bool or type(new)is not bool:raise ValueError('airwallRange.literal-profile')
    g=BytesPath(regions,entry);allocation=None
    def edge():
        prefix=bytes(g.bytes.get(g.at+i,0)for i in range(2))
        g.branch('0f84',False)if prefix==b'\x0f\x84'else g.branch('74',False,1)
    g.take('48895c2418','55','56','57','4883ec20');ready=flag(g)
    g.take('488bfa','488bd9');g.branch('0f84',False)
    g.take('837b3001');g.branch('0f8c',False)
    g.take('488b4350','0fb630','8b6b30','83ed01');g.branch('0f88',False)
    g.take('48ff4350','ff4340','ff4344','896b30','4080feff');g.branch('0f84',null)
    if null:
        g.take('488bcf','48c70700000000','488b5c2450','4883c420','5f','5e','5d')
        if g.relative('e9')!=s['barrier']:raise ValueError('airwallRange.null-barrier')
    else:
        g.take('4c89742448','48833f00');g.branch('0f84',new)
        if new:
            allocation=dict(instruction=g.at,cell=g.relative('488b0d'))
            g.call(s['allocate']);g.take('488be8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');g.call(s['constructor'])
            g.take('488bcf','48892f');g.call(s['barrier']);g.take('90');g.jump('e9')
        g.take('4080fe02');g.branch('0f85',False)
        g.take('837b300c','488b37');g.branch('0f8c',False)
        g.take('488b4350','f20f1000','448b7008','f20f11442440','8b6b30','83c5f4');g.branch('0f88',False)
        g.take('488343500c','8343400c','8343440c','896b30','4885f6');edge()
        g.take('488b4610','4885c0');edge();g.take('f20f114010','44897018')
        g.take('837b300c','488b3f');g.branch('0f8c',False)
        g.take('488b4350','f20f1000','8b6808','f20f11442440','8b7330','83c6f4');g.branch('0f88',False)
        g.take('488343500c','8343400c','8343440c','897330','4885ff');edge()
        g.take('488b4710','4885c0');edge()
        g.take('4c8b742448','f20f11401c','896824','488b5c2450','4883c420','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,initializedFlag=ready,null=null,newWrapper=None if null else new,
        typedAllocation=allocation,headerBytes=1,positiveWireBytes=None if null else 25,
        vectorWireBytes=12,normalReturn=True,entryFrameRestored=True,
        orderedOriginalStores=[]if null else[dict(field='m_center',offset=16,bytes=12),dict(field='m_size',offset=28,bytes=12)],
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)


def range_constructor(regions,entry,s):
    g=BytesPath(regions,entry);g.take('4053','4883ec20');ready=flag(g)
    g.take('488bd9');g.branch('74',False,1)
    allocation=dict(instruction=g.at,cell=g.relative('488b0d'));g.call(s['allocate'])
    g.take('4885c0');g.branch('74',False,1)
    g.take('33c9','48894810','894818','4889481c','894824','488d4b10','48894310','4883c420','5b')
    if g.relative('e9')!=s['barrier']:raise ValueError('airwallRange.constructor-barrier')
    return dict(selectedBytes=g.seen,initializedFlag=ready,typedAllocation=allocation,
        ownedZeroRanges=[[16,28],[28,40]],originalHolderOffset=16,normalTailReturn=True)


def vector2_setter_program(regions,entry,offset):
    if offset not in(32,40):raise ValueError('airwallVector2Setter.closed-field')
    g=BytesPath(regions,entry)
    g.take('4883ec28','488b4110','4889542430','4885c0');g.branch('75',True,1)
    slot=lambda value:bytes((value,)).hex()
    g.take('f30f10442430','f30f104c2434','f30f1140'+slot(offset),
        'f30f1148'+slot(offset+4),'4883c428','c3')
    return dict(selectedBytes=g.seen,ownedHolderOffset=16,managedBytes=8,normalReturn=True,
        source='same incoming RDX low64 saved outside callee shadow homes and loaded as two Singles',
        originalRange=[offset,offset+8],runtimeProviderSelectionObserved=False)


def polyline_program(regions,entry,s,*,null=False,new=False):
    if type(null)is not bool or type(new)is not bool:raise ValueError('airwallPolyline.literal-profile')
    g=BytesPath(regions,entry);allocation=None;reads=[]
    peek=lambda:bytes(g.bytes.get(g.at+i,0)for i in range(2))
    def edge():g.branch('0f84',False)if peek()==b'\x0f\x84'else g.branch('74',False,1)
    def holder(*,final=False,rax=False):
        g.take('4885ff'if final else'4885f6');edge()
        g.take(('488b4710'if final else'488b4610')if rax else('488b4f10'if final else'488b4e10'),
            '4885c0'if rax else'4885c9');edge()
    def source(name,role,*,typed=False):
        context=None
        if typed:context=dict(instruction=g.at,cell=g.relative('488b15'))
        g.take('488bcb','488b37');call=g.at;g.call(s[role])
        reads.append(dict(fieldName=name,kind=role,sourceCall=call,sourceTarget=s[role],typedUsage=context))
    def setter(name,*,final=False):
        g.take('45'+'33c0','488bd0','488bcf'if final else'488bce');g.call(s[name])
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20');ready=flag(g)
    g.take('488bfa','488bd9');g.branch('0f84',False)
    g.take('837b3001');g.branch('0f8c',False)
    g.take('488b4350','0fb630','8b6b30','83ed01');g.branch('0f88',False)
    g.take('48ff4350','ff4340','ff4344','896b30','4080feff');g.branch('0f84',null)
    if null:g.take('488bcf','48c70700000000');g.call(s['barrier']);g.jump('eb',1)
    else:
        g.take('48833f00');g.branch('0f84',new)
        if new:
            allocation=dict(instruction=g.at,cell=g.relative('488b0d'))
            g.call(s['allocate']);g.take('488be8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');g.call(s['constructor'])
            g.take('488bcf','48892f');g.call(s['barrier']);g.take('90');g.jump('e9')
        g.take('4080fe0a');g.branch('0f85',False)
        source('bounds','reference',typed=True);holder();g.take('48894110','4883c110');g.call(s['barrier'])
        g.take('488b37','488bcb');call=g.at;g.call(s['bool']);holder();g.take('884148')
        reads.append(dict(fieldName='disableDefaultEffect',kind='bool',sourceCall=call,sourceTarget=s['bool']))
        g.take('488bcb','488b37');call=g.at;g.call(s['bool']);holder();g.take('884149')
        reads.append(dict(fieldName='enableNavObstacle',kind='bool',sourceCall=call,sourceTarget=s['bool']))
        g.take('488bcb');context=dict(instruction=g.at,cell=g.relative('488b15'));g.take('488b37')
        call=g.at;g.call(s['vector2']);g.take('4885f6');edge();setter('heightSetter')
        reads.append(dict(fieldName='heightRange',kind='vector2',sourceCall=call,sourceTarget=s['vector2'],typedUsage=context))
        g.take('488b37','488bcb');call=g.at;g.call(s['pool']);holder()
        g.take('48894138','4883c138');g.call(s['barrier'])
        reads.append(dict(fieldName='overrideEffectId',kind='pool',sourceCall=call,sourceTarget=s['pool']))
        source('posList','list',typed=True);holder();g.take('48894118','4883c118');g.call(s['barrier'])
        g.take('488b37','488bcb');call=g.at;g.call(s['single']);holder(rax=True)
        g.take('488b37','488bcb','f30f114040')
        reads.append(dict(fieldName='pushDis',kind='single',sourceCall=call,sourceTarget=s['single']))
        call=g.at;g.call(s['single']);holder(rax=True);g.take('488b37','488bcb','f30f114044')
        reads.append(dict(fieldName='pushWarnDis',kind='single',sourceCall=call,sourceTarget=s['single']))
        call=g.at;g.call(s['int32']);holder();g.take('894130')
        reads.append(dict(fieldName='usage',kind='int32',sourceCall=call,sourceTarget=s['int32']))
        g.take('488bcb');context=dict(instruction=g.at,cell=g.relative('488b15'));g.take('488b3f')
        call=g.at;g.call(s['vector2']);g.take('4885ff');edge();setter('visualHeightSetter',final=True)
        reads.append(dict(fieldName='visualHeightRange',kind='vector2',sourceCall=call,sourceTarget=s['vector2'],typedUsage=context))
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,initializedFlag=ready,null=null,newWrapper=None if null else new,
        typedAllocation=allocation,orderedReads=reads,headerBytes=1,recordMemberCount=None if null else 10,
        nullWireBytes=1,normalReturn=True,entryFrameRestored=True,
        childGrammarAdmitted=False,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)


def polyline_constructor(regions,entry,s):
    g=BytesPath(regions,entry);g.take('4053','4883ec20');ready=flag(g)
    g.take('488bd9');g.branch('74',False,1)
    allocation=dict(instruction=g.at,cell=g.relative('488b0d'));g.call(s['allocate'])
    g.take('4c8bc8','4885c0');g.branch('74',False,1)
    default_cell=g.relative('488b05');g.take('498d4938','49894138');g.call(s['barrier'])
    g.take('488d4b10','4c894b10','4883c420','5b')
    if g.relative('e9')!=s['barrier']:raise ValueError('airwallPolyline.constructor-barrier')
    return dict(selectedBytes=g.seen,initializedFlag=ready,typedAllocation=allocation,
        defaultReferenceCell=default_cell,originalHolderOffset=16,normalTailReturn=True,
        condition='The exact selected ordinary non-clobbering barrier preserves the allocated reference in R9; original construction defaults are not serialized child grammar.')


def derive(image,pins,airwalls):
    """Bind geometry programs to their exact current nominal types and callers."""
    import json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.levelscript_family_regenerate import Build
    from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param,pooled_source_helper
    from scripts.game_data.memorypack.pointer_param import owned,methods,leaf
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.vector2_source import validate_vector2_source
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.leveldata_airwall_record_sources import GROUP
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;build=Build(image,pins)
    need=lambda k,e,a:scalar.need('airwallGeometry',k,e,a)
    need('same-current-parent-pins',pins,airwalls['nativeInputs']);records={};plans={
        'Beyond.Gameplay.ThreeDimRange':(('m_center','UnityEngine.Vector3',16),('m_size','UnityEngine.Vector3',28)),
        'Beyond.Gameplay.PolyLineWall':(('bounds','Beyond.Gameplay.ThreeDimRange',16),
            ('disableDefaultEffect','bool',72),('enableNavObstacle','bool',73),('heightRange','UnityEngine.Vector2',32),
            ('overrideEffectId','string',56),('posList','System.Collections.Generic.List`1<UnityEngine.Vector2>',24),
            ('pushDis','float',64),('pushWarnDis','float',68),('usage','int',48),('visualHeightRange','UnityEngine.Vector2',40))}
    vector='UnityEngine.Vector3';definition=ctx.index.types[vector]
    vector_fields=[f for f in md.fields_for(definition)if not ctx.field_attributes(f.type_index)&16]
    need('actual-Vector3-layout',[(axis,'float',16+4*i)for i,axis in enumerate('xyz')],
        [(md.string(f.name_index),*ctx.field(vector+'::'+md.string(f.name_index))[1:])for f in vector_fields])
    need('actual-Vector3-value-type',True,ctx.is_value_type(vector))
    for f in vector_fields:scalar.ordinary(image,ctx.type_pointer(f.type_index),12,'airwallGeometry.Vector3.float')
    sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+definition.index*8)
    need('Vector3-boxed/native-extent',(28,12),(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4)))
    for original,plan in plans.items():
        is_range=original.endswith('.ThreeDimRange');wrapper,=[w for w in build.wrappers.values()if w.wrapped_type==original]
        need('exact-ordered-members',[(n,t)for n,t,_ in plan],[(m.name,m.declared_type)for m in wrapper.members])
        need('exact-original-fields',[(original,t,o)for _,t,o in plan],[ctx.field(original+'::'+n)for n,_,_ in plan])
        need('original-reference',False,ctx.is_value_type(original))
        need('owned-original-holder',(wrapper.name,original,16),ctx.field(wrapper.name+'::__instance'))
        mm=methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
        body=owned(image,image.method_pointer_va(mm['Deserialize']));ctor=owned(image,image.method_pointer_va(mm['.ctor']))
        symbols=dict(constructor=ctor['pointer'],allocate=_body_target(ctor,'test rax, rax',before=True),
            barrier=next(control_transfer(r)['target']for r in ctor['rows']if control_transfer(r)['kind']=='jump'))
        setter_sources={};setters={}
        if not is_range:
            for kind,text in (('reference','mov [rcx+0x10], rax'),('bool','mov [rcx+0x48], al'),
                    ('pool','mov [rcx+0x38], rax'),('list','mov [rcx+0x18], rax'),
                    ('single','movss [rax+0x40], xmm0'),('int32','mov [rcx+0x30], eax')):
                symbols[kind]=_body_target(body,text,before=True)
            symbols['vector2']=_body_target(body,'xor r8d, r8d',before=True)
            for role,name,offset in (('heightSetter','heightRange',32),('visualHeightSetter','visualHeightRange',40)):
                member,=[m for m in wrapper.members if m.name==name];method=md.methods[member.method_index]
                scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),
                    [('UnityEngine.Vector2',17,False)],'airwallGeometry.'+name)
                symbols[role]=image.method_pointer_va(method);setter=owned(image,symbols[role]);setter_sources[name]=setter['windows']
                setters[name]=vector2_setter_program(setter['regions'],setter['pointer'],offset)
        program=range_program if is_range else polyline_program
        programs=[program(body['regions'],body['pointer'],symbols,**kw)for kw in(dict(null=True),dict(new=True),dict(new=False))]
        constructor=(range_constructor if is_range else polyline_constructor)(ctor['regions'],ctor['pointer'],symbols)
        allocations=[]
        for role,allocation,type_name in(('wrapper',programs[1]['typedAllocation'],wrapper.name),
                ('original',constructor['typedAllocation'],original)):
            usage=derive_typed_usage_context(image,allocation['instruction']-base,label='airwallGeometry.'+role)
            need('actual-allocation:'+role,(1,type_name),(usage['tag'],usage['typeName']));allocations.append(usage)
        pair=derive_pair(image,original);adapter=derive_adapter(image,pins,pair,wrapper)
        scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(original,18,True),[],
            'airwallGeometry.getter')
        getter=leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3'])
        children=[];primitives={};o=scalar.reader_offsets(image,'airwallGeometry')
        if not is_range:
            for read in programs[-1]['orderedReads']:
                role=read['kind'];target=read['sourceTarget']
                if read.get('typedUsage')is not None:
                    field,=[f for f in plan if f[0]==read['fieldName']]
                    usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='airwallGeometry.child')
                    if role=='vector2':checked=validate_vector2_source(image,usage,target-base)
                    else:
                        method='ReadValue'if role=='reference'else'ReadPackable'
                        bind_typed_read(image,usage,method_name=method,argument=field[1],kind=18 if role=='reference'else 21,reference=True)
                        build.prove_reader_clone_target(target,'MemoryPack.MemoryPackReader.'+method,result_abi='reference');checked=None
                    children.append(dict(fieldName=field[0],typeName=field[1],source=read,typedRequest=usage,sourceProof=checked))
                elif role=='pool':primitives[role]=pooled_source_helper.validate_on_image(image,target,pins)
                else:
                    source=vector_recorder(image)(target-base)
                    if role=='bool':checked=scalar.boolean_source(image,source,o,'airwallGeometry.bool')
                    elif role=='single':checked=primitive_param.single_source(image,source,o)
                    else:checked=scalar.integer_source(image,source,o,'airwallGeometry.int32',width=4)
                    primitives[role]=dict(source=source,proof=checked)
        barrier,barrier_proof,_=_fast_barrier(image,symbols['barrier'])
        records[original]=dict(wrapperName=wrapper.name,fields=[dict(name=n,typeName=t,offset=o)for n,t,o in plan],
            method=[mm['Deserialize'].index,wrapper.name,'Deserialize',body['pointer']-base],
            sourceWindows=body['windows'],programs=programs,constructor=constructor,constructorWindows=ctor['windows'],
            typedAllocations=allocations,profile=pair,adapter=adapter,getter=getter,setters=setters,
            setterSourceWindows=setter_sources,children=children,primitiveSources=primitives,
            barrier=dict(source=barrier,proof=barrier_proof),symbolRvas={k:v-base for k,v in symbols.items()})
    group=airwalls['records'][GROUP];bounds,=[c for c in group['children']if c['field']['name']=='bounds']
    need('actual-group-bound-type','Beyond.Gameplay.ThreeDimRange',bounds['field']['typeName'])
    return json.loads(json.dumps(dict(nativeInputs=pins,records=records,groupBoundsParent=bounds,
        inlineVector3=dict(typeName=vector,definition=definition.index,managedBytes=12,boxedBytes=28),
        wholeOwnerAdmitted=False,polylineListElementsAdmitted=False,liveFormatterSelectionObserved=False)))
