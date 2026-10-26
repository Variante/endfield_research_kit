"""Own nested string/LevelWide dictionary source, without concrete values.

The object/object registration is an independent code witness. Original
string/LevelWide contexts and actual callback equality remain conditions;
no differently closed pointer equality or runtime factory choice follows.
"""
import json

KEY='Beyond.Gameplay.LevelWideConfig+LevelWideConfigType'
VALUE='Beyond.Gameplay.LevelWideConfig'
TYPE='System.Collections.Generic.Dictionary`2<string,'+VALUE+'>'
PARENT='System.Collections.Generic.Dictionary`2<'+KEY+','+TYPE+'>'


def need(check,expected,actual):
    if expected!=actual:raise ValueError('levelwideInner.'+check+':expected='+str(expected)[:350]+':actual='+str(actual)[:350])


def validate_parent_carrier(parent,*,key_definition,value_definition):
    """Pure exact nested carrier shape; supplies no native or callback grant."""
    need('actual-parent',PARENT,parent.get('name'))
    need('parent-definition','System.Collections.Generic.Dictionary`2',parent.get('definition',{}).get('name'))
    need('parent-reference-kind',b'\x15\x00',bytes.fromhex(parent.get('rawHex',''))[10:12])
    arguments=parent.get('classArguments',[]);need('two-parent-arguments',2,len(arguments));key,inner=arguments
    raw=bytes.fromhex(key.get('rawHex',''))
    need('own-outer-enum-carrier',(KEY,b'\x11\x80',key_definition),(key.get('name'),raw[10:12],int.from_bytes(raw[:8],'little')))
    need('actual-nested-value',TYPE,inner.get('name'))
    need('inner-definition','System.Collections.Generic.Dictionary`2',inner.get('definition',{}).get('name'))
    need('inner-generic-reference',b'\x15\x00',bytes.fromhex(inner.get('rawHex',''))[10:12])
    arguments=inner.get('classArguments',[]);need('two-inner-arguments',2,len(arguments));inner_key,inner_value=arguments
    need('actual-pooled-string-key',('string',b'\x0e\x00'),(inner_key.get('name'),bytes.fromhex(inner_key.get('rawHex',''))[10:12]))
    raw=bytes.fromhex(inner_value.get('rawHex',''))
    need('actual-LevelWide-reference',(VALUE,b'\x12\x00',value_definition),(inner_value.get('name'),raw[10:12],int.from_bytes(raw[:8],'little')))
    return inner


def reference_dispatch(regions,entry,*,symbols,callback):
    """Exact already-owned reference adapter inline body, never an alias."""
    from scripts.game_data.memorypack.reference_adapter_sources import dispatch
    need('same-owned-inline-reference-entry',(symbols['dispatch'],symbols['main']),(entry,callback))
    paths=[dispatch(regions,entry,symbols,null=True)]+[
        dispatch(regions,entry,symbols,create=create,wrapper_null=null)
        for create in(False,True)for null in(False,True)]
    need('complete-owned-inline-reference-paths',True,all(
        row.get('normalReturn')is True and row.get('sameIncomingReaderAndOutput')is True
        and row.get('canonicalPointerMatched')is True and row.get('outputBytes')==8 and row.get('slot')==5
        for row in paths))
    return dict(profile='own-canonical-reference-adapter-inline',slot=5,outputBytes=8,
        sameReaderAndOutput=True,canonicalCallbackTarget=callback,programs=paths,
        actualCallbackEqualsOwnCanonicalRequired=True,ordinaryTypedContextsRequired=True,
        runtimeSelectionObserved=False,wholeOwnerAdmitted=False)


def derive(image,pins,*,parent_request,union_source):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.context import type_parameter_owner,method_parameter_owner
    from scripts.game_data.memorypack import npc_collection_programs as programs
    from scripts.game_data.memorypack.leveldata_empty_dictionary_sources import derive_source_witness
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.pooled_string_list_sources import validate_string_components
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);cs=ContextSymbols(image);ge=GenericEntries(image)
    validate_typed_usage_context(image,parent_request,label='levelwideInner.actualOuterParent')
    bind_typed_read(image,parent_request,method_name='ReadPackable',argument=PARENT,kind=21,reference=True)
    argument,=image.instantiations.resolve(parent_request['methodSpec'][2]).arguments
    parent=cs.type(argument.type_pointer_va)
    inner=validate_parent_carrier(parent,key_definition=ctx.index.types[KEY].index,value_definition=ctx.index.types[VALUE].index)
    need('same-current-union-inputs',pins,union_source['nativeInputs']);need('own-union-type',VALUE,union_source['typeName'])
    adapter=union_source['adapter'];need('own-original-adapter-type',VALUE,adapter['typeName'])
    need('explicit-original-callback-condition',True,adapter['callbackBinding']['actualCallbackEqualsCanonicalRequired'])
    image.check_windows(union_source['codeWindows'],label='levelwideInner.retained-own-union')
    witness=derive_source_witness(image,pins)
    slots={r['relativeSlot']:r for r in witness['context']['entries']};md=image.metadata
    add=md.methods[slots[9]['methodSpec'][0]];add_params=list(md.parameters_for(add))
    need('own-Add-ABI',('System.Collections.Generic.Dictionary`2',False,2,'void'),
        (image.type_name(add.declaring_type),bool(add.flags&16),len(add_params),ctx.type_name(add.return_type)))
    containers=[t.generic_container_index for t in md.types];add_formals=[]
    for ordinal,parameter in enumerate(add_params):
        raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
        need('Add-byvalue-VAR:'+str(ordinal),b'\x13\x00',raw[10:12])
        owner=type_parameter_owner(md.buf,int.from_bytes(raw[:8],'little'),containers,source='levelwideInner.Add')
        need('own-Add-VAR:'+str(ordinal),(add.declaring_type,ordinal),(owner['typeIndex'],owner['ordinal']))
        add_formals.append(owner)
    pair_method=md.methods[slots[8]['methodSpec'][0]];pair_params=list(md.parameters_for(pair_method))
    need('own-pair-ABI',('MemoryPack.Formatters.KeyValuePairFormatter','Deserialize',True,5,'void'),
        (image.type_name(pair_method.declaring_type),md.string(pair_method.name_index),bool(pair_method.flags&16),len(pair_params),ctx.type_name(pair_method.return_type)))
    method_containers=[m.generic_container_index for m in md.methods];pair_formals=[]
    for ordinal in(0,1):
        pointer=ctx.type_pointer(pair_params[ordinal].type_index);raw=image.pe.bytes_at_va(pointer,16);formal=cs.type(pointer)
        need('pair-provider-reference:'+str(ordinal),('MemoryPack.MemoryPackFormatter`1',b'\x15\x00'),
            (formal['definition']['name'],raw[10:12]))
        argument,=formal['classArguments'];owner=argument['parameterOwner']
        need('pair-provider-owned-MVAR:'+str(ordinal),(pair_method.index,ordinal),(owner['methodIndex'],owner['ordinal']))
    reader=image.pe.bytes_at_va(ctx.type_pointer(pair_params[2].type_index),16)
    need('pair-same-Reader-byref',(b'\x11\x20',ctx.index.types['MemoryPack.MemoryPackReader'].index),
        (reader[10:12],int.from_bytes(reader[:8],'little')))
    for ordinal in(0,1):
        raw=image.pe.bytes_at_va(ctx.type_pointer(pair_params[ordinal+3].type_index),16)
        need('pair-byref-MVAR:'+str(ordinal),b'\x1e\x20',raw[10:12])
        owner=method_parameter_owner(md.buf,int.from_bytes(raw[:8],'little'),method_containers,source='levelwideInner.pair')
        need('own-pair-output:'+str(ordinal),(pair_method.index,ordinal),(owner['methodIndex'],owner['ordinal']))
        pair_formals.append(owner)
    declaration=ctx.index.types['MemoryPack.Formatters.DictionaryFormatter`2']
    method,=[m for m in image.metadata.methods_for(declaration)if image.metadata.string(m.name_index)=='Deserialize']
    entry=ge.resolve(method.index,['object','object'],[]);body=owned(image,entry['pointer'])
    need('same-complete-open-source-windows',witness['sourceWindows'],body['windows'])
    calls=[control_transfer(row)['target']for row in body['rows']if bytes.fromhex(row['bytes'])[:1]==b'\xe8']
    need('bounded-complete-main-helper-sequence',True,len(calls)>=9)
    symbols=dict(classResolve=calls[0],allocate=calls[1],constructor=calls[2],barrier=calls[3],provider=calls[4],dispatch=calls[6],insert=calls[8])
    need('same-key-value-provider',calls[4],calls[5]);need('same-key-value-dispatcher',calls[6],calls[7])
    from scripts.game_data.memorypack.scalar_param_native import reader_offsets
    offsets=reader_offsets(image,'levelwideInner');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    paths=[programs.dictionary(body['regions'],body['pointer'],symbols,offsets,count=count)for count in(-1,0,1)]
    # The byte owner proves one complete invariant loop, including its sole
    # counter increment, unchanged count slot, exact backedge and normal frame.
    need('own-whole-positive-loop',('all-positive-Int32',True),
        (paths[-1]['countProfile'],paths[-1]['normalReturn']))
    string_fact=_load('levelscript_pooled_string_list_native.json',pins);pooled=validate_string_components(image,string_fact)
    need('own-pooled-string-slot-wire-and-result',(5,4,8),
        (pooled['stringFormatterSlot'],pooled['wireBytes'],pooled['managedReferenceBytes']))
    string_callback=base+next(p['entryRva']for p in string_fact['programs']if p['role']=='string')
    dispatch=owned(image,symbols['dispatch']);prepare=base+adapter['canonicalRoutes']['symbolRvas']['prepare']
    key_dispatch=deserialize_slot(dispatch['regions'],dispatch['pointer'],prepare=prepare,callback=string_callback)
    value_callback=base+adapter['callbackBinding']['canonicalTargetRva']
    own_symbols={name:base+rva for name,rva in adapter['canonicalRoutes']['symbolRvas'].items()}
    value_dispatch=reference_dispatch(dispatch['regions'],dispatch['pointer'],symbols=own_symbols,callback=value_callback)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.story-levelwide-inner-dictionary-source.v1',
        status='validated-conditional-source-only',nativeInputs=pins,typeName=TYPE,keyType='string',valueType=VALUE,
        sourceWitnessClassArguments=['object','object'],sourceWitness=witness,registration=entry,
        sourceWindows=body['windows'],sourceRegions=[[at-base,raw.hex()]for at,raw in body['regions']],
        sourcePrograms=paths,symbolRvas={k:v-base for k,v in symbols.items()},readerOffsets=offsets,
        actualParent=dict(typedRequest=parent_request,closedOuterCarrier=parent,closedInnerCarrier=inner),
        keyCallback=dict(source=pooled,callbackTargetRva=string_callback-base,dispatch=key_dispatch),
        valueCallback=dict(adapter=adapter,callbackTargetRva=value_callback-base,dispatch=value_dispatch),
        helperABI=dict(AddMethodDefinition=add.index,AddParameters=add_formals,
            pairMethodDefinition=pair_method.index,pairOutputParameters=pair_formals),
        positiveCountLoopProved=True,pooledStringKeyGrammarProved=True,concreteValueGrammarAdmitted=False,
        positiveDictionaryAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        closedPointerEquivalenceProved=False,actualCallbackEqualsSourceWitnessRequired=True,
        actualKeyCallbackEqualsPooledStringRequired=True,actualValueCallbackEqualsOwnUnionAdapterRequired=True,
        typedConstructorAndHelperCompatibilityRequired=True,runtimeFormatterSelectionObserved=False,
        evidenceBoundary=dict(exact='Actual nested carrier from an owned outer ReadPackable request; complete registered reference/reference count/new/positive loop, owned TK/TV helper contexts/ABI, independent pooled key callback and exact same-reader/output generic dispatcher transfers to the own LevelWide original adapter.',
            conditional=__doc__+' Initially-null output, coherent typed constructor/provider/helper contexts, normal compatible successful allocation/insertion/barriers and matching actual callbacks remain required.',
            unresolved=['concrete LevelWide records/union child grammar','actual outer enum dictionary and host field composition','runtime generic callback/provider/factory selection']))))
