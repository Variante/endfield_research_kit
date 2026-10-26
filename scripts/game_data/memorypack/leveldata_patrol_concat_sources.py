"""The actual all-string Patrol concat caller and its independent helpers.

Current MethodInfo/type/cache selections and valid string/builder storage are
conditions. File bytes never establish live class or thread-static identity.
"""
import json
from itertools import product

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as packets

CALLER_SCHEMA='endfield.story-patrol-concat-caller-sources.v2'
SCHEMA='endfield.story-patrol-concat-sources.v2'


def need(check,condition,detail=None):
    if not condition:raise ValueError('patrolConcat.'+check+(':'+str(detail)[:800]if detail is not None else''))


def caller_program(regions,entry,*,create,type_from_handle,append,string_ctor,dispose,present=(True,True,True),empty=False):
    need('literal-all-string-source-selection',isinstance(present,tuple)and len(present)==3
        and all(type(v)is bool for v in present)and type(empty)is bool)
    g=BytesPath(regions,entry);sites={};class_cells=[];string_cells=[];type_cells=[]
    def cell(role):
        at=g.at;value=g.relative('488b0d');sites.setdefault(role,[]).append(dict(instructionVa=at,cellVa=value));return value
    def initialized(role):
        value=cell(role);g.take('83b9e000000000');g.branch('75',True,1);return value
    g.take('48895c2408','4889742410','57','4156','4157','4883ec50','498bf9','4d8bf8','4c8bf2','488bf1',
        '4983793800');g.branch('75',True,1)
    g.take('0f57c0','0f11442428','33db','48899c2488000000')
    class_cells.append(cell('builderClass'));g.take('3999e0000000');g.branch('75',True,1)
    g.take('b201','488d4c2428');g.call(create)
    g.take('48895c2438','488d442428','4889442440')
    for ordinal,(is_present,load,test,arg)in enumerate(zip(present,
        ('488b1b','488b5b18','488b5b30'),('4885f6','4d85f6','4d85ff'),('488bd6','498bd6','498bd7'),strict=True)):
        g.take('488b5f38',load);type_cells.append(initialized('runtimeTypeClass'))
        g.take('33d2','488bcb');g.call(type_from_handle);g.take('488bd8','33d2')
        string_cells.append(cell('stringType'));g.call(type_from_handle);g.take('483bd8');g.branch('0f84',True)
        g.take(test);g.branch('74',not is_present,1)
        if is_present:
            class_cells.append(initialized('builderClass'));g.take(arg,'488d4c2428');g.call(append)
    class_cells.append(initialized('builderClass'));g.take('448b442430','4585c0');g.branch('74',empty,1)
    empty_site=None;empty_cell=None
    if empty:
        empty_site=g.at;empty_cell=g.relative('488b05');g.take('488b88b8000000','488b19')
    else:
        g.take('4533c9','33d2','488b4c2428');g.call(string_ctor);g.take('488bd8');g.jump('eb',1)
    g.take('48899c2488000000');class_cells.append(initialized('builderClass'))
    g.take('488d4c2428');g.call(dispose);g.jump('eb',1)
    g.take('488bc3','488b5c2470','488b742478','4883c450','415f','415e','5f','c3')
    need('one-own-builder-class-cell',len(set(class_cells))==1)
    need('same-string-and-runtimeType-cells',len(set(string_cells))==len(set(type_cells))==1)
    return dict(selectedBytes=g.seen,typedClassUsageSites=sites,emptyStringClassUsageSiteVa=empty_site,
        emptyStringClassUsageCellVa=empty_cell,present=list(present),emptyResult=empty,
        actualStringTypeEqualityRequired=[0,1,2],methodContextTypeSlots=[0,3,6],
        appendOrder=[i for i,v in enumerate(present)if v],appendArguments=[dict(rcx='same builder local',rdx='same incoming string'+str(i))for i,v in enumerate(present)if v],
        builderLocalOffset=40,builderLocalBytes=16,builderLengthOffset=8,createNotNestedBool=True,
        stringConstructionArguments=None if empty else dict(rcx='same builder char[]',edx=0,r8d='same final builder length',r9=0),
        returnedReference='same String.Empty static reference'if empty else'same String.Ctor returned reference',
        sameReturnedReferenceSurvivesDispose=True,resultHeldInCalleePreservedRbx=True,entryRspRestored=True,frameBytes=104,callShadow=[0,32],
        restoredNonvolatiles=['rbx','rsi','rdi','r14','r15'],helperEffectsProved=False,
        condition='Own ready closed three-string MethodInfo and ready canonical classes/type handles; Type.GetTypeFromHandle returns stable corresponding canonical references so all three actual String tests match; compatible disjoint strings/builder/frame and normally returning Win64 helper ABI. This caller alone proves argument/return transfer, not builder/string helper effects.')


def _contexts(image,lookup):
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    request=lookup['proof']['leadSource']['proof']['actualTypedUsages']['concat-MethodInfo']
    need('own-closed-three-string-request',tuple(request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
        (6,'Beyond.StringUtils','ZConcat',[],['string','string','string']))
    wrapper=ContextSymbols(image).context(request['methodSpec'][0],is_method=True)
    need('single-actual-concat-method-context',len(wrapper['entries'])==1)
    row=wrapper['entries'][0]
    need('own-ZString-Concat-declaration',(row['relativeSlot'],row['kind'],row.get('typeName'),row.get('methodName'))==
        (0,3,'Cysharp.Text.ZString','Concat')and row.get('classArguments')==[]and len(row.get('methodArguments',[]))==3)
    for ordinal,arg in enumerate(row['methodArguments']):
        raw=bytes.fromhex(arg['rawHex']);owner=arg.get('parameterOwner',{})
        need('own-wrapper-generic-substitution-'+str(ordinal),raw[10:12]==bytes((30,0))and owner.get('methodIndex')==request['methodSpec'][0]and owner.get('ordinal')==ordinal)
    child=ContextSymbols(image).context(row['methodSpec'][0],is_method=True,slots=[0,3,6])
    for ordinal,arg in enumerate(child['entries']):
        raw=bytes.fromhex(arg['type']['rawHex']);owner=arg['type'].get('parameterOwner',{})
        need('own-child-generic-type-slot-'+str(ordinal),(arg['relativeSlot'],arg['kind'])==(ordinal*3,1)
            and raw[10:12]==bytes((30,0))and owner.get('methodIndex')==row['methodSpec'][0]and owner.get('ordinal')==ordinal)
    return dict(request=request,wrapper=wrapper,child=child)


def _validate_contexts(contexts):
    request=contexts['request'];wrapper=contexts['wrapper'];child=contexts['child']
    need('replay-own-three-string-context-request',tuple(request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
        (6,'Beyond.StringUtils','ZConcat',[],['string','string','string']))
    need('replay-own-wrapper-context',wrapper['definition']==request['methodSpec'][0]and wrapper['isMethod']is True and len(wrapper['entries'])==1)
    row=wrapper['entries'][0]
    need('replay-child-concat-method',(row['relativeSlot'],row['kind'],row.get('typeName'),row.get('methodName'))==
        (0,3,'Cysharp.Text.ZString','Concat')and row.get('classArguments')==[]and len(row.get('methodArguments',[]))==3)
    for ordinal,arg in enumerate(row['methodArguments']):
        raw=bytes.fromhex(arg['rawHex']);owner=arg.get('parameterOwner',{})
        need('replay-wrapper-MVAR-'+str(ordinal),raw[10:12]==bytes((30,0))and owner.get('methodIndex')==request['methodSpec'][0]and owner.get('ordinal')==ordinal)
    need('replay-own-child-context',child['definition']==row['methodSpec'][0]and child['isMethod']is True and len(child['entries'])==3)
    for ordinal,arg in enumerate(child['entries']):
        raw=bytes.fromhex(arg['type']['rawHex']);owner=arg['type'].get('parameterOwner',{})
        need('replay-child-MVAR-'+str(ordinal),(arg['relativeSlot'],arg['kind'])==(ordinal*3,1)and
            raw[10:12]==bytes((30,0))and owner.get('methodIndex')==row['methodSpec'][0]and owner.get('ordinal')==ordinal)


def _derive_caller(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import leveldata_patrol_lookup_sources as lookup_owner
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
    _publication_gate(image,pins);lookup=lookup_owner.derive(image,pins);base=image.pe.image_base
    child=lookup['proof']['tailChildren']['concat-path'];entry=base+child['entryRva'];body=owned(image,entry)
    targets=dict(packets._calls([r for r in body['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8']))
    symbols=dict(create=targets[91],type_from_handle=targets[144],append=targets[341],string_ctor=targets[863],dispose=targets[924])
    need('same-string-appends-and-type-helper',targets[579]==targets[817]==symbols['append']and all(targets[at]==symbols['type_from_handle']for at in(161,380,397,618,635)))
    programs=[caller_program(body['regions'],entry,**symbols,present=p,empty=e)for p in product((False,True),repeat=3)for e in(False,True)]
    usages={}
    for role,sites in programs[-1]['typedClassUsageSites'].items():
        usages[role]=[derive_typed_usage_context(image,s['instructionVa']-base,label='patrolConcat.'+role)for s in sites]
    expected=dict(builderClass=(1,'Cysharp.Text.Utf16ValueStringBuilder'),runtimeTypeClass=(1,'System.Type'),stringType=(2,'string'))
    for role,rows in usages.items():need('own-class-usage-'+role,all((r.get('tag'),r.get('typeName'))==expected[role]for r in rows),
        dict(expected=expected[role],actual=[(r.get('tag'),r.get('typeName'))for r in rows]))
    ctx=NativeReferenceContext(image);md=image.metadata;builder_fields=[]
    for field in md.fields_for(ctx.index.types['Cysharp.Text.Utf16ValueStringBuilder']):
        if ctx.field_attributes(field.type_index)&16:continue
        name=md.string(field.name_index);builder_fields.append(dict(name=name,field=ctx.field('Cysharp.Text.Utf16ValueStringBuilder::'+name)))
    empty_usage=derive_typed_usage_context(image,programs[-1]['emptyStringClassUsageSiteVa']-base,label='patrolConcat.emptyStringClass')
    need('actual-empty-String-class-usage',(empty_usage.get('tag'),empty_usage.get('typeName'))==(1,'string'),
        dict(tag=empty_usage.get('tag'),typeName=empty_usage.get('typeName')))
    string_type=ctx.index.types['System.String']
    empty_field,=[f for f in md.fields_for(string_type)if md.string(f.name_index)=='Empty']
    empty_field_info=dict(name='Empty',typeName=ctx.type_name(empty_field.type_index),
        static=bool(ctx.field_attributes(empty_field.type_index)&16),
        offset=runtime_type_field_offsets(md,image.pe,image.registration,string_type.index)['Empty'])
    need('actual-Empty-static-string-field',empty_field_info==dict(name='Empty',typeName='string',static=True,offset=0),empty_field_info)
    source_helpers={name:packets.packet(image,target)for name,target in symbols.items()}
    result=dict(schema=CALLER_SCHEMA,status='validated-conditional-three-string-concat-caller-source',nativeInputs=pins,
        proof=dict(imageBase=base,lookupSource=lookup,source=packets.packet(image,entry),contexts=_contexts(image,lookup),
            symbolRvas={k:v-base for k,v in symbols.items()},programs=programs,classUsages=usages,helpers=source_helpers,builderFields=builder_fields,
            emptyStringUsage=empty_usage,emptyStringField=empty_field_info),
        allStringCallerTransfersAndFrameProved=True,concatStringEffectsProved=False,
        wholeConversionProved=False,runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Own closed all-string request, reciprocal generic MethodInfo/type slots, all null-presence and empty/nonempty caller branches, ordered same-builder string requests and unchanged normal return/frame.',
            conditional=__doc__,unresolved=['Create/Append/String.Ctor/Dispose helper effects','canonical runtime Type.GetTypeFromHandle/cache/MethodInfo selection','other generic argument kinds, growth/allocation/cold/exceptional paths','actual asset and controller invocation']))
    result=json.loads(json.dumps(result));_validate_caller(result,pins);_publication_gate(image,pins);return result


def _validate_caller(value,pins):
    need('schema-and-inputs',value.get('schema')==CALLER_SCHEMA and value.get('nativeInputs')==pins)
    p=value['proof'];base=p['imageBase'];source=p['source'];packets.verify_packet(source)
    lookup=p['lookupSource'];need('same-own-actual-tail',lookup['nativeInputs']==pins
        and source['entryRva']==lookup['proof']['tailChildren']['concat-path']['entryRva']
        and base+source['entryRva']==lookup['proof']['programs']['concat-path']['tailTargetVa'])
    need('complete-source-helper-domain',set(p['helpers'])==set(p['symbolRvas'])=={'create','type_from_handle','append','string_ctor','dispose'})
    for role,child in p['helpers'].items():
        packets.verify_packet(child);need('same-own-helper-entry-'+role,child['entryRva']==p['symbolRvas'][role])
    symbols={k:base+v for k,v in p['symbolRvas'].items()}
    actual=[caller_program(packets.regions(source,base),base+source['entryRva'],**symbols,present=mode,empty=e)
        for mode in product((False,True),repeat=3)for e in(False,True)]
    need('complete-selected-caller-replay',json.loads(json.dumps(actual))==p['programs'])
    _validate_contexts(p['contexts'])
    need('same-actual-typed-concat-request',p['contexts']['request']==lookup['proof']['leadSource']['proof']['actualTypedUsages']['concat-MethodInfo'])
    expected=dict(builderClass=(1,'Cysharp.Text.Utf16ValueStringBuilder'),runtimeTypeClass=(1,'System.Type'),stringType=(2,'string'))
    need('complete-typed-class-role-domain',set(p['classUsages'])==set(expected))
    for role,rows in p['classUsages'].items():
        sites=actual[-1]['typedClassUsageSites'][role]
        need('same-own-typed-sites-'+role,len(rows)==len(sites)and all((r.get('tag'),r.get('typeName'))==expected[role]and
            r['instructionRva']==s['instructionVa']-base and r['usageCellRva']==s['cellVa']-base for r,s in zip(rows,sites)))
    empty=p['emptyStringUsage'];selected=actual[-1]
    need('same-actual-Empty-class-and-field',(empty.get('tag'),empty.get('typeName'))==(1,'string')and
        empty['instructionRva']==selected['emptyStringClassUsageSiteVa']-base and empty['usageCellRva']==selected['emptyStringClassUsageCellVa']-base and
        p['emptyStringField']==dict(name='Empty',typeName='string',static=True,offset=0))
    need('source-only-flags',value.get('allStringCallerTransfersAndFrameProved')is True and all(value.get(k)is False for k in
        ('concatStringEffectsProved','wholeConversionProved','runtimeInvocationObserved','playbackProved')))
    return value


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import leveldata_patrol_concat_string_sources as string_owner
    _publication_gate(image,pins)
    caller=_derive_caller(image,pins);strings=string_owner.derive(image,pins,caller)
    result=dict(schema=SCHEMA,status='validated-conditional-three-string-concat-source',nativeInputs=pins,
        proof=dict(callerSource=caller,stringSource=strings),
        allStringCallerTransfersAndFrameProved=True,concatStringEffectsProved=True,
        wholeConversionProved=False,runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Actual closed three-string request and reciprocal method/type contexts, complete caller paths, independently replayed current string helpers, bounded copy and prefix composition.',
            conditional=strings['evidenceBoundary']['conditional'],unresolved=strings['evidenceBoundary']['unresolved']))
    validate(result,pins);_publication_gate(image,pins);return result


def validate(value,pins):
    from scripts.game_data.memorypack import leveldata_patrol_concat_string_sources as string_owner
    need('complete-schema-and-inputs',value.get('schema')==SCHEMA and value.get('nativeInputs')==pins)
    p=value['proof'];caller=_validate_caller(p['callerSource'],pins)
    string_owner.validate(p['stringSource'],pins,caller)
    need('complete-source-flags',value.get('allStringCallerTransfersAndFrameProved')is True and value.get('concatStringEffectsProved')is True and
        all(value.get(k)is False for k in('wholeConversionProved','runtimeInvocationObserved','playbackProved')))
    return value
