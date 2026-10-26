"""Finite initialized-metadata Bitset Param source, including inline raw4.

The selected warm paths are proved from their real entries. Cold metadata
initializers, enabled collectors and refill/error paths are not admitted.
There is no invented ReadUnmanaged MethodInfo for the inline enum read.
"""
import hashlib
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.Actions.Param`1<Beyond.GEnums.BitsetType>'
VALUE='Beyond.GEnums.BitsetType'
LABEL='levelscriptBitsetParam'
SCHEMA='endfield.levelscript-bitset-param-source.v1'


def need(check,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+check+':'+str(detail)[:800])


def reference_carrier_join(holder,returned):
    """Declaration attributes differ; the actual closed carrier must agree."""
    left=bytes.fromhex(holder);right=bytes.fromhex(returned)
    need('same-returned-closed-reference-carrier',len(left)==len(right)==16
         and left[10:12]==right[10:12]==bytes((21,0))
         and left[:8]==right[:8]and left[12:]==right[12:],
         dict(holder=holder,returned=returned))
    return dict(holderTypeRecordHex=holder,returnTypeRecordHex=returned,
        sameClosedGenericClassPointer=True,ordinaryReferenceKind=21,
        holderDeclarationAttributes=int.from_bytes(left[8:10],'little'),
        returnDeclarationAttributes=int.from_bytes(right[8:10],'little'))


def _collector(g,disabled):
    at=g.at;cell=g.relative('833d')+1;g.take('00')
    need('same-independently-disabled-collector',cell==disabled)
    return at


def scalar_setter_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('4883ec28','488b4110','4885c0');g.branch('74',False,1)
    g.take('8950');slot=int.from_bytes(g.read(1),'little',signed=True)
    need('owned-positive-DWORD-slot',16<=slot<=123)
    g.take('4883c428','c3')
    return dict(selectedBytes=g.seen,holderOffset=16,fieldOffset=slot,storedBytes=4,
        incomingEdxStoredUnchanged=True,entryRspRestored=True,allNonvolatilesUnchanged=True,
        normalReturn=True,nonnullHolderRequired=True)


def string_setter_program(regions,entry,*,disabled):
    g=BytesPath(regions,entry)
    g.take('4883ec28','4c8b4110','4d85c0');g.branch('74',False,1)
    _collector(g,disabled);g.take('498950');slot=int.from_bytes(g.read(1),'little',signed=True)
    need('owned-positive-reference-slot',16<=slot<=119)
    g.branch('74',True,1);g.take('4883c428','c3')
    return dict(selectedBytes=g.seen,holderOffset=16,fieldOffset=slot,storedBytes=8,
        incomingWholeRdxStoredUnchanged=True,entryRspRestored=True,allNonvolatilesUnchanged=True,
        normalReturn=True,nonnullHolderAndDisabledCollectorRequired=True)


def factory_program(regions,entry,*,disabled,image_base):
    g=BytesPath(regions,entry)
    g.take('4055','56','4883ec58')
    flag=g.relative('803d')+1;g.take('00')
    need('exact-selected-image-base',g.relative('488d2d')==image_base)
    g.take('488bf1');g.branch('0f85',True)
    at=g.at;allocation=dict(site=at,cell=g.relative('488b0d'))
    allocator=g.relative('e8');g.take('4885c0');g.branch('74',False,1)
    _collector(g,disabled);g.take('c740');slot=int.from_bytes(g.read(1),'little',signed=True)
    g.take('ffffffff','48894610');g.branch('74',True,1)
    g.take('4883c458','5e','5d','c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag,allocation=allocation,
        allocationTarget=allocator,holderOffset=16,idRefOffset=slot,idRefDefaultHex='FFFFFFFF',
        sameAllocatedReferenceStored=True,originalManagedConstructorInvoked=False,
        initializedMetadataAndDisabledCollectorRequired=True,zeroInitializedTypedAllocationRequired=True,
        entryRspRestored=True,nonvolatilesRestored=['rbp','rsi'],allOtherNonvolatilesUnchanged=True,
        normalReturn=True)


def reader_program(regions,entry,offsets,*,existing,ff,disabled,image_base,factory):
    need('literal-four-path-selection',type(existing)is bool and type(ff)is bool)
    g=BytesPath(regions,entry)
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('488bc4','48895820','55','56','57','4156','4157','4883ec60')
    flag=g.relative('803d')+1;g.take('00')
    need('actual-reader-image-base',g.relative('4c8d3d')==image_base)
    g.take('4c8bf2','488bd9');g.branch('0f85',True)
    g.take('837b'+rem+'01');g.branch('7d',True,1)
    g.take('488b43'+cur,'0fb630','8b7b'+rem,'83ef01');g.branch('79',True,1)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'897b'+rem,'4080feff')
    g.branch('0f84',ff)
    allocation=None;slots={};calls={}
    if ff:
        _collector(g,disabled);g.take('49c70600000000');g.branch('74',True,1)
    else:
        g.take('49833e00');g.branch('75',existing,1)
        if not existing:
            at=g.at;allocation=dict(site=at,cell=g.relative('488b0d'))
            allocator=g.relative('e8');allocation['target']=allocator
            g.take('488bf8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');g.call(factory)
            _collector(g,disabled);g.take('49893e');g.branch('74',True,1)
        g.take('4080fe04');g.branch('0f85',False)
        at=g.at
        g.take('837b'+rem+'04','498b3e');g.branch('7d',True,1)
        g.take('488b43'+cur,'8b28','8b73'+rem,'83c6fc');g.branch('79',True,1)
        g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','8973'+rem,
               '4885ff');g.branch('0f84',False)
        g.take('488b4710','4885c0');g.branch('0f84',False)
        g.take('8968');slots['constValue']=int.from_bytes(g.read(1),'little',signed=True)
        inline=dict(startVa=at,wireBytes=4,sourceRegister='ebp',resultStoredUnchanged=True,
            readUnmanagedMethodInfoClaimed=False)
        for name in('idRef','paramSource'):
            g.take('488bcb','498b3e');calls[name]=g.relative('e8')
            g.take('4885ff');g.branch('0f84',False)
            g.take('488b4f10','4885c9');g.branch('0f84',False)
            g.take('8941');slots[name]=int.from_bytes(g.read(1),'little',signed=True)
        need('same-actual-Int32-helper',calls['idRef']==calls['paramSource'])
        g.take('488bcb','498b3e');calls['path']=g.relative('e8')
        g.take('4885ff');g.branch('0f84',False)
        g.take('4c8b4710','4d85c0');g.branch('0f84',False)
        _collector(g,disabled);g.take('498940');slots['path']=int.from_bytes(g.read(1),'little',signed=True)
        g.branch('0f84',True)
        occupied=[p for name,width in(('constValue',4),('idRef',4),('paramSource',4),('path',8))
                  for p in range(slots[name],slots[name]+width)]
        need('whole-disjoint-four-current-field-effects',len(set(occupied))==20 and all(16<=p<128 for p in occupied))
    g.take('488b9c24a8000000','4883c460','415f','415e','5f','5e','5d','c3')
    result=dict(selectedBytes=g.seen,initializedFlag=flag,existing=existing,wrapperNull=ff,
        allocation=allocation,sourceCalls=calls,fieldOffsets=slots,memberCount=4,
        headerBytes=1,nullReferenceBytes=1,outputReferenceBytes=8,
        initializedMetadataAndDisabledCollectorRequired=True,bufferedSourceRequired=True,
        entryOriginalRbxHome=32,currentFrameBytes=136,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rbp','rsi','rdi','r14','r15'],allOtherNonvolatilesUnchanged=True,
        normalReturn=True,childGrammarAdmitted=False,wholeOwnerAdmitted=False)
    if not ff:result['inlineConstantSource']=inline
    return result


def _disabled_collector(image,pins):
    """Reprove the independently reviewed collector leaf, not its flag name."""
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    raw=ec.CONTRACT_PATH.read_bytes();declaration=json.loads(raw)
    need('same-selected-collector-build',declaration['nativeInputs']==pins)
    targets={p['headerProof']['referenceBarrierTargetRva']for p in declaration['proof']['profiles']}
    need('one-independently-reviewed-collector-entry',len(targets)==1)
    proof=_barrier(image,image.pe.image_base+next(iter(targets)))
    return proof,ec.CONTRACT_PATH,raw


def derive(image,pins):
    """Fresh finite warm source; no ordinary adapter or outer field admission."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import levelscript_condition_enum_param_sources as enums
    from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,pooled_source_helper
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    nominal=enums._nominal(image,ctx,TYPE)
    need('exact-nominal-Int32-Bitset',nominal['valueType']==VALUE and nominal['isEnum']is True
         and nominal['constantWireKind']=='i32'and nominal['constantWireBytes']==4)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
    need('four-current-owned-members',[(m.name,m.declared_type)for m in wrapper.members]==
         [('constValue',VALUE),('idRef','int'),('paramSource','int'),('path','string')])
    collector,collector_path,collector_raw=_disabled_collector(image,pins)
    disabled=base+collector['result']['disabledFlagRva']
    pool_raw=pooled_source_helper.CONTRACT_PATH.read_bytes()
    selected={};bodies={}
    names=('.ctor','CreateInstance','GetValue','Deserialize',
           'set___constValue__','set___idRef__','set___paramSource__','set___path__')
    for name in names:
        choices=[m for m in md.methods_for(md.types[wrapper.type_definition])if md.string(m.name_index)==name]
        need('one-owned-method:'+name,len(choices)==1)
        method=choices[0];target=image.method_pointer_va(method)
        if name=='Deserialize':primitive_param.reader_abi(image,ctx,method,wrapper)
        else:
            result=(TYPE,21,True)if name=='GetValue'else('void',1,False)
            member=name[6:-2]if name.startswith('set___')else None
            arguments=[]if member is None else [dict(constValue=(VALUE,17,False),
                idRef=('int',8,False),paramSource=('int',8,False),path=('string',14,True))[member]]
            scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,result,arguments,LABEL+'.'+name)
            if member=='constValue':
                parameter,=md.parameters_for(method)
                raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
                need('own-value-enum-setter-parameter',raw[10:12]==bytes((17,128))
                     and int.from_bytes(raw[:8],'little')==nominal['enumTypeDefinition'])
            if name=='GetValue':
                raw=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
                return_carrier=reference_carrier_join(nominal['carrier']['rawHex'],raw.hex().upper())
        if name=='GetValue':
            leaf=pointer.leaf(image,target,['488B4110','C3']);raw=image.pe.bytes_at_va(target,5)
            selected[name]=dict(methodIndex=method.index,pointerRva=target-base,
                window=dict(startRva=target-base,endRva=target-base+5,sha256=hashlib.sha256(raw).hexdigest().upper()),
                returnedCarrier=return_carrier,**leaf)
            continue
        body=pointer.owned(image,target);bodies[name]=body
        image.check_windows(body['windows'],label=LABEL+'.'+name)
        selected[name]=dict(methodIndex=method.index,pointerRva=target-base,windows=body['windows'],
            sourceRegions=[[a-base,b.hex().upper()]for a,b in body['regions']],
            instructions=[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()]for r in body['rows']])
    setters={}
    for field in('constValue','idRef','paramSource','path'):
        body=bodies['set___'+field+'__']
        setters[field]=(string_setter_program(body['regions'],body['pointer'],disabled=disabled)if field=='path'
            else scalar_setter_program(body['regions'],body['pointer']))
    slots={field:program['fieldOffset']for field,program in setters.items()}
    occupied=[at for field,width in(('constValue',4),('idRef',4),('paramSource',4),('path',8))
              for at in range(slots[field],slots[field]+width)]
    need('disjoint-owned-setter-effects',len(set(occupied))==20)
    factories={};allocation_contexts={}
    for name in('.ctor','CreateInstance'):
        body=bodies[name];program=factory_program(body['regions'],body['pointer'],disabled=disabled,image_base=base)
        usage=derive_typed_usage_context(image,program['allocation']['site']-base,label=LABEL+'.'+name+'.ParamAllocation')
        need('own-closed-Param-allocation:'+name,usage['tag']==1 and usage['typeName']==TYPE)
        need('same-current-allocation-cell:'+name,usage['usageCellRva']==program['allocation']['cell']-base)
        scalar.ordinary(image,ctx.type_pointer(usage['typeIndex']),21,LABEL+'.ParamAllocation',reference=True)
        need('own-idRef-default-slot:'+name,program['idRefOffset']==slots['idRef'])
        factories[name]=program;allocation_contexts[name]=usage
    need('same-typed-Param-factory-allocation',
         factories['.ctor']['allocation']['cell']==factories['CreateInstance']['allocation']['cell']
         and factories['.ctor']['allocationTarget']==factories['CreateInstance']['allocationTarget'])
    offsets=scalar.reader_offsets(image,LABEL);body=bodies['Deserialize'];programs={};wrapper_allocation=None
    for existing in(False,True):
        for ff in(False,True):
            key=('existing'if existing else'new')+('-FF'if ff else'-MC4')
            program=reader_program(body['regions'],body['pointer'],offsets,existing=existing,ff=ff,
                disabled=disabled,image_base=base,factory=base+selected['.ctor']['pointerRva'])
            if not ff:need('same-named-field-stores:'+key,program['fieldOffsets']==slots)
            if not ff and not existing:
                wrapper_allocation=derive_typed_usage_context(image,program['allocation']['site']-base,label=LABEL+'.wrapperAllocation')
                need('actual-wrapper-new-allocation',wrapper_allocation['tag']==1
                     and wrapper_allocation['typeName']==wrapper.name
                     and wrapper_allocation['usageCellRva']==program['allocation']['cell']-base)
                scalar.ordinary(image,ctx.type_pointer(wrapper_allocation['typeIndex']),18,LABEL+'.wrapperAllocation',reference=True)
            programs[key]=program
    positive=programs['existing-MC4'];targets={n:p-base for n,p in positive['sourceCalls'].items()}
    record=vector_recorder(image);integer=record(targets['idRef'])
    scalar.integer_source(image,integer,offsets,LABEL+'.auxiliary-Int32')
    strings=pooled_source_helper.validate_on_image(image,base+targets['path'],pins)
    need('own-selected-path-pool-index',strings['wireEncoding']=='int32-pool-index')
    _publication_gate(image,pins)
    need('collector-declaration-stable',collector_path.read_bytes()==collector_raw)
    need('pooled-source-declaration-stable',pooled_source_helper.CONTRACT_PATH.read_bytes()==pool_raw)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated',nativeInputs=pins,
        sourceProfile='bitset-inline-enum-raw4',typeName=TYPE,valueType=VALUE,nominal=nominal,
        parameter=dict(methods=selected,ownedFieldSlots=slots,allocationContext=allocation_contexts['.ctor'],
            allocationContexts=allocation_contexts,wrapperAllocationContext=wrapper_allocation,
            setterPrograms=setters,factoryPrograms=factories,programs=programs),
        constantSource=dict(mode='inline-buffered-enum-raw4',wireBytes=4,resultRegister='ebp',
            program=positive['inlineConstantSource'],selectedWithinOwnedReader=True,
            readUnmanagedMethodInfoClaimed=False,nominalType=VALUE,enumBacking=nominal['enumDeclaration']),
        int32Source=integer,readerFieldOffsets=offsets,targets=targets,pooledSource=strings,collector=collector,
        canonicalAdapterAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Current closed Param carrier and own Int32 enum backing, declared setter/getter/reader ABI, complete selected warm factory and four reader paths, inline raw4 constant, named disjoint stores, auxiliary Int32 and pooled path sources.',
            conditional='Own metadata-initialized flags true, independently proved collector disabled, matching initialized pool, sufficient buffered input, valid disjoint Reader/output/non-null holder and complete call frames; compatible zero-initialized typed allocator normal returns.',
            unresolved=['cold metadata initialization','refill/errors and enabled collectors','ordinary canonical Param adapter and outer typed field','runtime formatter selection and invocation']))))
