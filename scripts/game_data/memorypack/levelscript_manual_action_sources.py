"""Own SendLuaEvent1 outer wrapper and its actual manual Original formatter.

The manual value is not a recursive generated wrapper. Its named native field
stores, inline UTF8 sources and separately owned pooled String Param form one
finite stored grammar. JSON text is retained as serialization, without claiming
the evaluated Param<object>, Lua execution, IFix selection or provider state.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.Actions.SendLuaEvent1'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Actions_SendLuaEvent1ForMemoryPack'
PARAM='Beyond.Gameplay.Actions.Param`1<string>'
SCHEMA='endfield.levelscript-manual-lua-source.v1'


def need(check,condition,detail=''):
    if not condition:raise ValueError('manualLuaSource.'+check+':'+str(detail)[:1400])


def _edge(g,zero):
    first=g.bytes.get(g.at);near=first==15
    opcode=g.bytes.get(g.at+1)if near else first
    need('literal-owned-equality-edge',opcode in((132,133)if near else(116,117)))
    g.branch(('0f'if near else'')+format(opcode,'02x'),zero if opcode&15==4 else not zero,4 if near else 1)


def _call(g,roles,name):
    at=g.at;target=g.relative('e8');row=dict(instructionVa=at,targetVa=target)
    need('one-consistent-call-role',name not in roles or roles[name]['targetVa']==target,name)
    roles.setdefault(name,row);return row


def _usage(g,prefix):
    at=g.at;cell=g.relative(prefix);return dict(instructionVa=at,cellVa=cell)


def _nonnull(g):
    at=g.at;first=g.bytes.get(at);near=first==15;opcode=g.bytes.get(at+1)if near else first
    need('literal-nonnull-edge',opcode in((132,133)if near else(116,117)))
    target=g.relative(('0f'if near else'')+format(opcode,'02x'),4 if near else 1);fall=g.at
    null=target if opcode&15==4 else fall;normal=fall if opcode&15==4 else target
    need('owned-nonreturning-null-throw',g.bytes.get(null)==232 and g.bytes.get(null+5)==204)
    g.at=normal


def object_header_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','83793001','488bfa','488bd9')
    g.branch('0f8c',False)
    g.take('488b4350','0fb608','880f','8b7330','83ee01');g.branch('0f88',False)
    g.take('48ff4350','ff4340','ff4344','897330','803fff','488b5c2430','488b742438',
        '0f95c0','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=1,nullMarker=255,wholeOutputByteStored=True,
        normalReturn=True,entryRspRestored=True,bufferedInputRequired=True)


def inline_string_program(regions,entry,*,header,read_utf8,empty_cell):
    g=BytesPath(regions,entry)
    g.take('4889542410','53','4883ec20');flag=g.relative('803d')+1;g.take('00','488bd9');_edge(g,False)
    g.take('488d542438','c744243800000000','488bcb');g.call(header);g.take('84c0')
    null=g.relative('74',1);g.take('8b542438','85d2');empty=g.relative('74',1)
    g.take('4533c0','488bcb','4883c420','5b');need('same-canonical-UTF8-tail',g.relative('e9')==read_utf8)
    g.at=empty;need('same-authenticated-empty-string-literal',g.relative('488b05')==empty_cell)
    end=g.relative('eb',1);g.at=null;g.take('33c0');need('same-null-empty-return',g.at==end)
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag,wireEncoding='nullable-int32-byte-length-valid-utf8',
        headerTargetVa=header,utf8TargetVa=read_utf8,nullEmptyDistinct=True,fullReferenceReturn=True,
        entryRspRestored=True,metadataInitializedRequired=True)


def byte_program(regions,entry,*,advance):
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20','83793001','488bf9');g.branch('7d',True,1)
    g.take('488b4750','ba01000000','488bcf','0fb618');g.call(advance)
    g.take('0fb6c3','488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=1,rawBooleanBytePreserved=True,entryRspRestored=True)


def callback_program(regions,entry):
    g=BytesPath(regions,entry);roles={}
    g.take('48895c2408','4889742410','57','4883ec20','488b0a','498bd9','498bf8','488bf2')
    _call(g,roles,'prepareFormatterClass')
    g.take('4c8b0e','4c8bc3','488bd7','488bce','498b8190010000','4d8b8998010000',
        '488b5c2430','488b742438','4883c420','5f','48ffe0')
    return dict(selectedBytes=g.seen,roles=roles,slot=5,vtableOffset=320,callbackOffset=400,methodInfoOffset=408,
        sameFormatterReceiverReaderAndByrefField=True,entryRspRestored=True,callbackSelectionObserved=False)


def manual_program(regions,entry,*,existing,ff):
    need('literal-path-selection',type(existing)is bool and type(ff)is bool)
    g=BytesPath(regions,entry);roles={};usages=[];fields=[]
    def call(name):return _call(g,roles,name)
    def usage(role,prefix):
        row=dict(role=role,**_usage(g,prefix));usages.append(row);return row
    def field(kind,prefix,bytes_,width=1):
        g.take(prefix);offset=int.from_bytes(g.read(width),'little',signed=True)
        row=dict(kind=kind,offset=offset,storedBytes=bytes_);fields.append(row);return row
    g.take('48895c2408','48896c2410','4889742418','57','4883ec40')
    flag=g.relative('803d')+1;g.take('00','498bf1','498bf8','488bda','488be9');_edge(g,False)
    patch=_usage(g,'488b05');g.take('488b4830','4885c9');_edge(g,True)
    g.take('488d542430','c644243000','488bcb');call('objectHeader');g.take('84c0');_edge(g,ff)
    if ff:
        g.take('48c70700000000','488bcf');call('barrier')
    else:
        g.take('48833f00');_edge(g,not existing)
        if not existing:
            usage('originalAllocation','488b0d');call('allocate');g.take('488bf0','4885c0');_nonnull(g)
            g.take('33d2','488bc8');call('originalConstructor');g.take('488bcf','488937');call('barrier')
        usage('intContext','488b15');g.take('488bcb','488b37');call('int32')
        g.take('4885f6');_nonnull(g);field('int32','8946',4)
        g.take('488bcb','488b37');call('inlineString');g.take('4885f6');_nonnull(g)
        g.take('488d4e');address=int.from_bytes(g.read(1),'little',signed=True)
        row=field('utf8','488946',8);need('same-string-store-barrier-address',row['offset']==address)
        call('barrier')
        usage('booleanContext','488b15');g.take('488bcb','488b37');call('rawByte')
        g.take('4885f6');_nonnull(g);field('raw-byte','8846',1)
        g.take('488bcb');usage('intContext','488b15');g.take('488b37');call('int32')
        g.take('4885f6');_nonnull(g);field('int32','8946',4)
        g.take('488bcb');usage('booleanContext','488b15');g.take('488b37');call('rawByte')
        g.take('4885f6');_nonnull(g);field('raw-byte','8846',1)
        usage('formatterProviderClass','488b0d');call('classReady')
        usage('stringParamFormatter','488b0d');call('getStringParamFormatter')
        g.take('4c8b0f','4d85c9');_nonnull(g);g.take('4885c0');_nonnull(g)
        field('pooled-string-Param','4981c1',8,4)
        g.take('4c8bc3','488bd0');call('formatterSlot5')
        g.take('488bcb');call('inlineString');usage('jsonClass','488b0d')
        g.take('488bd8','488b3f');call('classReady')
        usage('jsonParamMethod','4c8b05');g.take('33d2','488bcb');call('jsonDeserialize')
        g.take('4885ff');_nonnull(g);row=field('serialized-json-Param','488987',8,4)
        g.take('488d8f');address=int.from_bytes(g.read(4),'little',signed=True)
        need('same-JSON-field-and-barrier-address',address==row['offset']);g.jump('eb',1);call('barrier')
    g.take('488b5c2450','488b6c2458','488b742460','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,roles=roles,usages=usages,fields=fields,existing=existing,ff=ff,
        initializedFlag=flag,patchTable=patch,manualMemberCount=7,headerMemberCountChecked=False,
        noPatchTableSelected=True,fullReferenceOutput=True,entryRspRestored=True,
        runtimeExecutionProved=False,callbackSelectionObserved=False)


def outer_program(regions,entry,*,existing,ff):
    need('literal-outer-path-selection',type(existing)is bool and type(ff)is bool)
    g=BytesPath(regions,entry);roles={};usages=[];reads=[]
    def call(role):return _call(g,roles,role)
    g.take('48895c2410','4889742418','57','4883ec20')
    flag=g.relative('803d')+1;g.take('00','488bda','488bf9');_edge(g,False)
    g.take('488d542430','c644243000','488bcf');call('objectHeader');g.take('84c0');_edge(g,ff)
    if ff:g.take('488bcb','48c70300000000');call('barrier')
    else:
        g.take('48833b00');_edge(g,not existing)
        if not existing:
            usages.append(dict(role='wrapperAllocation',**_usage(g,'488b0d')))
            call('allocate');g.take('488bf0','4885c0');_nonnull(g)
            g.take('33d2','488bc8');call('wrapperConstructor');g.take('488bcb','488933');call('barrier')
        g.take('807c243009');_edge(g,True)
        kinds=('rawByte','int32','rawByte','pooledString','int32','rawByte','rawByte','int32')
        for index,kind in enumerate(kinds):
            if index==4:usages.append(dict(role='scopeEnumContext',**_usage(g,'488b15')))
            if index==4:g.take('488bcf','488b33')
            else:g.take('488b33','488bcf')
            source=call(kind);g.take('4885f6');_nonnull(g);g.take('4533c0')
            g.take('8ad0'if kind=='rawByte'else'488bd0'if kind=='pooledString'else'8bd0')
            g.take('488bce');setter=call('setter'+str(index));reads.append(dict(kind=kind,source=source,setter=setter))
        usages.append(dict(role='manualOriginalRead',**_usage(g,'488b15')))
        g.take('488bcf','488b1b');source=call('manualOriginal');g.take('4885db');_nonnull(g)
        g.take('4533c0','488bd0','488bcb');setter=call('wholeOriginalSetter')
        reads.append(dict(kind='manual-original',source=source,setter=setter));g.jump('eb',1)
    g.take('488b5c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,roles=roles,usages=usages,reads=reads,existing=existing,ff=ff,
        initializedFlag=flag,memberCount=9,wholeOriginalAssignedLast=not ff,
        fullReferenceOutput=True,entryRspRestored=True,runtimeExecutionProved=False)


def factory_program(regions,entry,*,ctor,holder_setter):
    need('literal-own-factory-mode',type(ctor)is bool and type(holder_setter)is int and holder_setter>0)
    g=BytesPath(regions,entry);roles={};usages=[]
    g.take('48895c2408','57','4883ec20');flag=g.relative('803d')+1
    g.take('00','488bf9');_edge(g,False)
    if ctor:
        usages.append(dict(role='readyWrapperAncestor',**_usage(g,'488b0d')))
        _call(g,roles,'classReady');g.take('33d2','488bcf');_call(g,roles,'wrapperBaseConstructor')
    usages.append(dict(role='originalAllocation',**_usage(g,'488b0d')))
    _call(g,roles,'allocate');g.take('488bd8','4885c0');_nonnull(g)
    g.take('33d2','488bcb');_call(g,roles,'originalConstructor')
    g.take('4533c0','488bd3','488bcf','488b5c2430','4883c420','5f')
    need('same-own-whole-holder-setter-tail',g.relative('e9')==holder_setter)
    return dict(selectedBytes=g.seen,roles=roles,usages=usages,initializedFlag=flag,
        constructor=ctor,sameFreshExactNominalInWholeHolderSetter=True,fullIncomingReceiverPreserved=True,
        entryRspRestored=True,originalConstructorEffectsProved=False,runtimeConstructionObserved=False)


def _lifecycle(image,pins,wrapper,wrappers,barrier,getter_cache,outer_paths):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,generated_lifecycle_sources as life
    from scripts.game_data.memorypack import generated_member_sources as members,scalar_param_native as scalar
    from scripts.game_data.memorypack.modelview_factory_sources import dual_setter
    from scripts.game_data.memorypack.modelview_reference_sources import get_value
    from scripts.game_data.memorypack.reference_param_profile import _getter_windows
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);methods=pointer.methods(image,wrapper)
    need('actual-complete-manual-reader-has-no-prehook','OnDeserialized'not in methods
        and len(outer_paths)==4 and all(p['entryRspRestored']for p in outer_paths)
        and{(p['existing'],p['ff'])for p in outer_paths}=={(False,False),(False,True),(True,False),(True,True)})
    reader=methods['Deserialize'];getter=methods['get___instance'];value=methods['GetValue']
    coherent=members._coherent_getter(image,ctx,wrapper,getter,getter_cache,barrier=base+barrier,pins=pins)
    life._typed_abi(image,ctx,value,wrapper,(TYPE,18,True),[],'manualLua.GetValue')
    windows,thunk=_getter_windows(image,md.types[wrapper.type_definition],value)
    need('exact-own-manual-GetValue-tail',thunk['kind']=='owned-zero-context-getter-tail'
        and thunk['targetMethod'][0]==getter.index and base+thunk['targetMethod'][3]==image.method_pointer_va(getter))
    returned=get_value([(base+thunk['entryMethod'][3],bytes.fromhex(thunk['instructionHex']))],
        image.method_pointer_va(value),getter=image.method_pointer_va(getter))
    holder=methods['set___instance'];parameters=list(md.parameters_for(holder))
    need('one-exact-Original-holder-parameter',len(parameters)==1 and ctx.type_name(parameters[0].type_index)==TYPE)
    scalar.owned_method_abi(image,ctx,holder.index,holder.declaring_type,('void',1,False),[(TYPE,18,True)],'manualLua.holder')
    body=members._body(image,image.method_pointer_va(holder),pins=pins)
    stored=dual_setter(body['regions'],body['pointer'],base+barrier,cache=coherent['typedCache'][2],owned_cache=True)
    stored['holderOffsets']=[stored['baseSlot'],stored['cacheSlot']]
    chain=life._class_ancestry(ctx,TYPE);wrapper_chain=life._class_ancestry(ctx,WRAPPER)
    fields=life._holder_fields(image,ctx,WRAPPER,stored['holderOffsets'],chain)
    holder_proof=dict(method=life._method_row(image,holder),codeWindows=body['windows'],program=stored,fields=fields)
    original_type,=image.named_type_definitions[TYPE]
    original,=[m for m in md.methods_for(original_type)if md.string(m.name_index)=='.ctor'and m.parameter_count==0]
    scalar.owned_method_abi(image,ctx,original.index,original.declaring_type,('void',1,False),[],'manualLua.OriginalCtor')
    original_source=life._original_constructor(image,ctx,original,TYPE,pins=pins)
    targets={image.method_pointer_va(original)}
    if 'ownedAncestorTail'in original_source:targets.add(base+original_source['ownedAncestorTail']['targetRva'])
    if 'typedAncestorTail'in original_source:targets.add(base+original_source['typedAncestorTail']['targetMethod'][3])
    factories=[]
    for name in('.ctor','CreateInstance'):
        method=methods[name];life._typed_abi(image,ctx,method,wrapper,('void',1,False),[],'manualLua.factory')
        body=members._body(image,image.method_pointer_va(method),pins=pins)
        program=factory_program(body['regions'],body['pointer'],ctor=name=='.ctor',holder_setter=image.method_pointer_va(holder))
        need('own-exact-Original-constructor-or-proved-ancestor-tail',program['roles']['originalConstructor']['targetVa']in targets)
        typed=[]
        for use in program['usages']:
            actual=derive_typed_usage_context(image,use['instructionVa']-base,label='manualLua.factory.'+use['role'])
            need('owned-factory-class',actual.get('tag')==1 and actual.get('typeName')in
                ([TYPE]if use['role']=='originalAllocation'else wrapper_chain[1:]))
            typed.append(dict(role=use['role'],usage=actual))
        if name=='.ctor':
            target=program['roles']['wrapperBaseConstructor']['targetVa'];found=[]
            for owner in wrapper_chain[1:]:
                found.extend(m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)=='.ctor'
                    and m.parameter_count==0 and image.method_pointer_va(m)==target)
            need('one-actual-owned-wrapper-base-constructor',len(found)==1)
            base_ctor=found[0]
            scalar.owned_method_abi(image,ctx,base_ctor.index,base_ctor.declaring_type,('void',1,False),[],'manualLua.baseCtor')
            program['baseConstructorSource']=life._original_constructor(image,ctx,base_ctor,image.type_name(base_ctor.declaring_type),pins=pins)
        program['typedCacheOffset']=coherent['typedCache'][2]
        factories.append(dict(method=life._method_row(image,method),codeWindows=body['windows'],program=program,
            holderSetter=holder_proof,typedRequests=typed,originalConstructor=original_source))
    callback=life._concrete_formatter(image,ctx,wrapper,reader,pins=pins)
    return dict(wrapperName=WRAPPER,wrappedType=TYPE,baseHolder=coherent['baseHolder'],typedCache=coherent['typedCache'],
        coherentGetter=coherent,GetValue=dict(method=life._method_row(image,value),entryWindows=windows,entryProof=thunk,program=returned),
        concreteFormatter=callback,factories=factories,holderSetter=holder_proof,barrier=_barrier(image,base+barrier),
        prehookAbsentFromExactReader=True,allFourReaderPathsProved=True,wholeOwnerAdmitted=False,
        runtimeProviderSelectionObserved=False)


def derive(image,pins,*,wrapper,wrappers,barrier,getter_cache,reference_readers):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,_vtable
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,primitive_param
    from scripts.game_data.memorypack import generated_lifecycle_sources as lifecycle
    from scripts.game_data.memorypack import generated_member_sources as members
    from scripts.game_data.memorypack import generated_primitive_sources as primitives
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    from scripts.game_data.memorypack import utf8_source_helper as utf8
    from scripts.game_data.memorypack import pooled_source_helper as pooled
    from scripts.game_data.memorypack import interactive_param_sources as parameters
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    need('one-own-manual-wrapper',wrapper.name==WRAPPER and wrapper.wrapped_type==TYPE
        and len(wrapper.members)==9 and wrapper.members[8].name=='manualValue'
        and wrapper.members[8].declared_type==TYPE)
    methods=pointer.methods(image,wrapper);reader=methods['Deserialize']
    primitive_param.reader_abi(image,ctx,reader,wrapper)
    outer=pointer.owned(image,image.method_pointer_va(reader))
    formatter_name=TYPE+'+SendLuaEvent1Formatter';formatter,=image.named_type_definitions[formatter_name]
    method,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize']
    need('own-instance-slot-five',not method.flags&16 and method.slot==5 and method.parameter_count==2
        and ctx.type_name(method.return_type)=='void')
    _vtable(image,formatter.index,5,method.index,'manualLuaSource.actualManualFormatter')
    for parameter,name,kind in zip(md.parameters_for(method),('MemoryPack.MemoryPackReader',TYPE),(17,18),strict=True):
        raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
        need('exact-manual-byref-ABI',ctx.type_name(parameter.type_index)==name and raw[10:12]==bytes((kind,32)))
    manual=pointer.owned(image,image.method_pointer_va(method))
    outer_paths=[outer_program(outer['regions'],outer['pointer'],existing=e,ff=f)for e in(False,True)for f in(False,True)]
    manual_paths=[manual_program(manual['regions'],manual['pointer'],existing=e,ff=f)for e in(False,True)for f in(False,True)]
    positive=next(p for p in outer_paths if p['existing']and not p['ff'])
    inner=next(p for p in manual_paths if p['existing']and not p['ff'])
    need('same-independently-proved-object-header',positive['roles']['objectHeader']['targetVa']==inner['roles']['objectHeader']['targetVa'])
    header=pointer.owned(image,positive['roles']['objectHeader']['targetVa']);header_proof=object_header_program(header['regions'],header['pointer'])
    # The complete maintained UTF8 owner authenticates its signed header,
    # span/advance, encoding cache and decoder joins. This separately compiled
    # ReadString alias must join those exact helpers and empty literal itself.
    utf8_contract=utf8._contract();need('same-selected-UTF8-build',utf8_contract['nativeInputs']==pins)
    utf8_proof=utf8._validate_native(image,utf8_contract)
    string=pointer.owned(image,inner['roles']['inlineString']['targetVa'])
    string_proof=inline_string_program(string['regions'],string['pointer'],
        header=base+utf8_contract['bodies']['header']['entryRva'],
        read_utf8=base+utf8_contract['bodies']['readUtf8']['entryRva'],
        empty_cell=base+utf8_contract['emptyLiteral']['usageCellRva'])
    byte=pointer.owned(image,inner['roles']['rawByte']['targetVa'])
    byte_proof=byte_program(byte['regions'],byte['pointer'],advance=base+utf8_contract['bodies']['advance']['entryRva'])
    offsets=ec.source_offsets(image)
    integer=primitives.derive(image,inner['roles']['int32']['targetVa'],'int32',offsets)
    need('same-outer-Int32-reader',positive['roles']['int32']['targetVa']==inner['roles']['int32']['targetVa'])
    boolean=primitives.derive(image,positive['roles']['rawByte']['targetVa'],'bool',offsets)
    pool=pooled.validate_on_image(image,positive['roles']['pooledString']['targetVa'],pins)
    setters=[members._derive_setter(image,m,wrappers,barrier,getter_cache,pins=pins)for m in wrapper.members[:8]]
    for index,setter in enumerate(setters):
        need('own-whole-ordinary-field-setter',setter.get('incomingValueStoredUnchanged')is True
            and positive['reads'][index]['setter']['targetVa']==base+setter['method'][3])
    life=_lifecycle(image,pins,wrapper,wrappers,barrier,getter_cache,outer_paths)
    from scripts.game_data.memorypack.generated_reader_sources import constructed_getter_join
    construction=constructed_getter_join(life,setters)
    getter=life['GetValue'];callback=life['concreteFormatter']
    need('own-complete-wrapper-callback-and-Original-getter',getter['program'].get('fullReferenceOutput')is True
        and(callback['program'].get('completeOriginalForwarderChecked')is True
            or callback['program'].get('completeSelectedFormatterAdmitted')is True))
    ctors=[f for f in life['factories']if f['method'][2]=='.ctor'];need('one-own-wrapper-constructor',len(ctors)==1)
    need('same-actual-wrapper-constructor',outer_paths[0]['roles']['wrapperConstructor']['targetVa']==base+ctors[0]['method'][3])
    holder=ctors[0]['holderSetter']
    need('actual-whole-Original-assignment',positive['roles']['wholeOriginalSetter']['targetVa']==base+holder['method'][3])
    fresh=next(p for p in manual_paths if not p['existing']and not p['ff'])
    own_factory=ctors[0]['program']['roles']
    need('same-exact-normal-nominal-allocation-and-constructor',fresh['roles']['allocate']['targetVa']==own_factory['allocate']['targetVa']
        ==outer_paths[0]['roles']['allocate']['targetVa']==base+utf8_contract['opaqueCalls']['allocate']
        and fresh['roles']['originalConstructor']['targetVa']==own_factory['originalConstructor']['targetVa'])
    mapped=[]
    def field_at(offset):
        found=[];name=TYPE;seen=set()
        while name and name not in seen:
            if name=='object':name='System.Object'
            seen.add(name);td=ctx.index.types[name]
            for f in md.fields_for(td):
                qualified=name+'::'+md.string(f.name_index)
                if ctx.field_attributes(f.type_index)&16:continue
                owner,typ,at=ctx.field(qualified)
                if at==offset:found.append(dict(fieldName=md.string(f.name_index),declaredType=typ,declaringType=owner,fieldOffset=at))
            name=ctx.parent(name)
        need('one-actual-named-native-field',len(found)==1,(offset,found));return found[0]
    for field in inner['fields']:
        named=field_at(field['offset']);kind=field['kind'];typ=named['declaredType']
        expected={'int32':'int','raw-byte':'bool','utf8':'string','pooled-string-Param':PARAM,
            'serialized-json-Param':'Beyond.Gameplay.Actions.Param`1<object>'}[kind]
        need('own-field-exact-nominal',typ==expected,(named,kind))
        mapped.append(dict(named,wireKind=kind,managedBytes=field['storedBytes']))
    child=parameters.derive(image,pins,parameter_types=[PARAM]);param=child['capabilities'][PARAM]
    typed=[]
    for path in [*outer_paths,*manual_paths]:
        for site in path['usages']:
            usage=derive_typed_usage_context(image,site['instructionVa']-base,label='manualLuaSource.'+site['role'])
            role=site['role']
            if role in('originalAllocation','wrapperAllocation'):
                need('own-exact-allocation',(usage['tag'],usage['typeName'])==(1,TYPE if role=='originalAllocation'else WRAPPER))
            elif role in('intContext','booleanContext','scopeEnumContext'):
                declared=wrapper.members[4].declared_type if role=='scopeEnumContext'else'int'if role=='intContext'else'bool'
                need('own-primitive-context',usage.get('tag')==6 and usage.get('typeName')=='MemoryPack.MemoryPackReader'
                    and usage.get('methodName')=='ReadUnmanaged'and usage.get('classArguments')==[]
                    and usage.get('methodArguments')==[declared],dict(role=role,declaredType=declared,usage=usage))
            elif role=='manualOriginalRead':
                bind_typed_read(image,usage,method_name='ReadValue',argument=TYPE,kind=18,reference=True)
                need('same-independent-reference-read-ABI',usage['methodSpec'][0]==reference_readers['referenceReaderMethodDefinition']
                    and positive['roles']['manualOriginal']['targetVa']==base+reference_readers['referenceReaderTargetRva'])
            elif role=='stringParamFormatter':
                need('own-typed-String-Param-formatter-provider',usage.get('tag')==6
                    and usage.get('typeName')=='MemoryPack.MemoryPackFormatterProvider'
                    and usage.get('methodName')in('GetFormatter','GetFormatterWithVerify')
                    and usage.get('classArguments')==[] and usage.get('methodArguments')==[PARAM])
            elif role=='jsonParamMethod':
                need('own-typed-serialized-Param-JSON-method',usage.get('tag')==6
                    and usage.get('typeName')=='Beyond.JsonHelper'and usage.get('methodName')=='DeserializeObject'
                    and usage.get('classArguments')==[]and usage.get('methodArguments')==[mapped[-1]['declaredType']],usage)
            elif role=='formatterProviderClass':need('own-formatter-provider-class',(usage['tag'],usage['typeName'])==(1,'MemoryPack.MemoryPackFormatterProvider'))
            elif role=='jsonClass':need('own-JSON-class',(usage['tag'],usage['typeName'])==(1,'Beyond.JsonHelper'),usage)
            typed.append(dict(role=role,usage=usage))
    dispatch=pointer.owned(image,inner['roles']['formatterSlot5']['targetVa'])
    dispatch_proof=callback_program(dispatch['regions'],dispatch['pointer'])
    need('same-independent-class-preparation',dispatch_proof['roles']['prepareFormatterClass']['targetVa']==base+utf8_contract['opaqueCalls']['prepareClass'])
    barrier_targets={p['roles']['barrier']['targetVa']for p in[*outer_paths,*manual_paths]if 'barrier'in p['roles']}
    need('same-independent-reference-barrier',barrier_targets=={base+barrier})
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,status='validated-conditional-manual-Lua-action',
        wrapperName=WRAPPER,typeName=TYPE,memberCount=9,manualMemberCount=7,manualFields=mapped,
        outerFields=[dict(fieldName=m.name,declaredType=m.declared_type)for m in wrapper.members],
        paramSource=child,paramCapability=param,
        proof=dict(outerWindows=outer['windows'],outerPrograms=outer_paths,manualWindows=manual['windows'],
            manualMethod=[method.index,formatter_name,'Deserialize',manual['pointer']-base],manualPrograms=manual_paths,
            objectHeaderWindows=header['windows'],objectHeader=header_proof,
            utf8=utf8_proof,utf8AliasWindows=string['windows'],utf8Alias=string_proof,rawByteWindows=byte['windows'],rawByte=byte_proof,
            integer=integer,boolean=boolean,pooledString=pool,setters=setters,lifecycle=life,construction=construction,typedRequests=typed,
            slotFiveWindows=dispatch['windows'],slotFive=dispatch_proof,referenceReaders=reference_readers),
        wholeStoredGrammarAdmitted=True,rootConcreteCallbackAndOriginalGetterProved=True,
        manualOriginalFormatterProved=True,providerSelectionObserved=False,IFixSelectionObserved=False,
        evaluatedJsonParamObjectProved=False,runtimeLuaExecutionProved=False)))
