"""Current LevelData UInt64 and Interactive list parents, with separate children."""
ULONG='System.Collections.Generic.List`1<ulong>'
INTERACTIVES='System.Collections.Generic.List`1<Beyond.Gameplay.LevelInteractiveData>'


def bind_ulong_parent(field,read,usage,carrier,component):
    if (field['name'],field['typeName'],read['fieldName'])!=('autoSpawnedInteractives',ULONG,'autoSpawnedInteractives'):
        raise ValueError('leveldataScriptParents.closed-UInt64-parent')
    if (usage['methodName'],usage['methodArguments'])!=('ReadPackable',[ULONG]):
        raise ValueError('leveldataScriptParents.UInt64-typed-request')
    if (carrier['name'],carrier['definition']['name'])!=(ULONG,'System.Collections.Generic.List`1'):
        raise ValueError('leveldataScriptParents.closed-UInt64-carrier')
    argument,=carrier['classArguments'];raw=bytes.fromhex(argument['rawHex'])
    if len(raw)!=16 or raw[10:12]!=b'\x0b\x80':raise ValueError('leveldataScriptParents.UInt64-raw-kind')
    if (component['typeName'],component['headerBytes'],component['elementWireBytes'],component['elementRawKind'])!=(ULONG,4,8,11):
        raise ValueError('leveldataScriptParents.exact-UInt64-source')
    actual_entry=component['referenceSource']['source']['selectedBytes'][0][0]
    if read['sourceTarget']!=actual_entry:raise ValueError('leveldataScriptParents.actual-UInt64-parent-source')
    return dict(field=field,source=read,typedRequest=usage,closedCarrier=carrier,
        capability=dict(closedListType=ULONG,headerBytes=4,countLimit=16384,elementWireBytes=8,
            elementRawKind=11,wholeGrammarAdmitted=True,wholeOwnerAdmitted=False))


def derive(image,pins,owners,leveldata):
    import json
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.skill_cost_data_list_sources import derive_reference_list_component
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.levelscript_collection_sources import derive_ulong_list,reference_list_induction
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack import scalar_param_native as scalar
    if pins!=owners['nativeInputs']or pins!=leveldata['nativeInputs']:
        raise ValueError('leveldataScriptParents.selected-inputs')
    base=image.pe.image_base;ctx=NativeReferenceContext(image);ulongs=derive_ulong_list(image,pins,owners)
    parents=[];interactive=None
    for field,read in zip(leveldata['fields'],leveldata['program']['orderedReads'],strict=True):
        if field['name']not in('autoSpawnedInteractives','interactives'):continue
        usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='leveldataScriptParents')
        bind_typed_read(image,usage,method_name='ReadPackable',argument=field['typeName'],kind=21,reference=True)
        if field['name']=='autoSpawnedInteractives':
            argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
            carrier=ContextSymbols(image).type(argument.type_pointer_va)
            parents.append(bind_ulong_parent(field,read,usage,carrier,ulongs))
        else:
            if field['typeName']!=INTERACTIVES:raise ValueError('leveldataScriptParents.closed-Interactive-list')
            collection=derive_reference_list_component(image,pins,typed_request=usage,
                call_target=read['sourceTarget'],element_type='Beyond.Gameplay.LevelInteractiveData',count_limit=2)
            body=owned(image,collection['entry']['pointer']);offsets=scalar.reader_offsets(image,'leveldataScriptParents')
            offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
            induction=reference_list_induction(body['regions'],body['pointer'],offsets,
                {k:base+v for k,v in collection['symbols'].items()})
            interactive=dict(parent=dict(field=field,source=read,typedRequest=usage),
                collection=collection,positiveCountInduction=induction,
                capability=dict(closedListType=INTERACTIVES,headerBytes=4,countLimit=16384,
                    recordType='Beyond.Gameplay.LevelInteractiveData',elementGrammarAdmitted=False,
                    wholeGrammarAdmitted=False,wholeOwnerAdmitted=False))
    if len(parents)!=1 or interactive is None:raise ValueError('leveldataScriptParents.exact-two-parent-set')
    return json.loads(json.dumps(dict(nativeInputs=pins,ulongParent=parents[0],ulongComponent=ulongs,
        interactiveList=interactive,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
