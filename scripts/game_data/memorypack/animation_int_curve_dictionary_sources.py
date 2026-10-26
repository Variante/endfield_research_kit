"""Own Int32/UnityCurve Dictionary source below AnimationConfig member ten.

The actual closed ReadPackable request is separate from the int/object source
witness. Runtime typed formatter/MethodInfo compatibility, successful cache
and provider selection, normal typed constructor/insertion effects and the
independently proved Unity curve callback remain explicit conditions.
"""
import copy
import json

from scripts.game_data.memorypack import animation_int_curve_dictionary_programs as paths

SCHEMA='endfield.animation-int-curve-dictionary-sources.v1'
OWNER='MemoryPack.Formatters.DictionaryFormatter`2'
DICTIONARY='System.Collections.Generic.Dictionary`2'
VALUE='UnityEngine.AnimationCurve'
TYPE=DICTIONARY+'<int,'+VALUE+'>'
PARENT='Beyond.Gameplay.View.Animation.AnimationConfigJson'
FIELD='syncGroupAnimationCurves'
CAPABILITY='animation-int-unity-curve-dictionary'


def need(check,condition):
    if not condition:raise ValueError('animationIntCurveDictionarySource.'+check)


def require_carrier(carrier,value_index):
    need('exact-closed-Dictionary',isinstance(carrier,dict) and type(value_index)is int and value_index>=0
        and carrier.get('name')==TYPE and carrier.get('definition',{}).get('name')==DICTIONARY
        and len(carrier.get('classArguments',[]))==2)
    key,value=carrier['classArguments'];kr=bytes.fromhex(key['rawHex']);vr=bytes.fromhex(value['rawHex'])
    need('actual-Int32-and-owned-UnityCurve-carriers',key.get('name')=='int' and len(kr)==16 and kr[10:12]==bytes((8,128))
        and value.get('name')==VALUE and len(vr)==16 and vr[10:12]==bytes((18,0))
        and int.from_bytes(vr[:8],'little')==value_index)
    return dict(typeName=TYPE,keyType='int',keyValueType=True,valueType=VALUE,valueValueType=False)


def parent_call(image,usage,target):
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer
    ctx=NativeReferenceContext(image);base=image.pe.image_base
    wrappers=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==PARENT]
    need('one-current-parent-wrapper',len(wrappers)==1);wrapper,=wrappers
    need('own-member-ten-declaration',len(wrapper.members)==15
        and(wrapper.members[10].name,wrapper.members[10].declared_type)==(FIELD,TYPE))
    method=pointer.methods(image,wrapper)['Deserialize'];parent=pointer.owned(image,image.method_pointer_va(method))
    setter=image.metadata.methods[wrapper.members[10].method_index]
    g=BytesPath(parent['regions'],base+usage['instructionRva']);g.take(usage['instructionHex'])
    g.take('488bcf','488b33');at=g.at;g.call(target)
    g.take('4885f6');g.branch('0f84',False);g.take('4533c0','488bd0','488bce');g.call(image.method_pointer_va(setter))
    return dict(typeName=PARENT,wrapperName=wrapper.name,memberIndex=10,fieldName=FIELD,
        originalField=list(ctx.field(PARENT+'::'+FIELD)),readerMethod=[method.index,wrapper.name,'Deserialize',parent['pointer']-base],
        setterMethod=[setter.index,wrapper.name,image.metadata.string(setter.name_index),image.method_pointer_va(setter)-base],
        sourceInstructionRva=at-base,sourceTargetRva=target-base,selectedBytes=g.seen,
        windows=parent['windows'],regions=[[a-base,h.hex()]for a,h in parent['regions']],
        sameReturnedReferencePassedToNamedSetter=True,completeSetterSemanticsProved=False,
        parentFieldAdmitted=False,enclosingFrameAdmitted=False)


def helper_context(image,definition):
    """Only the three used Dictionary slots; unrelated kind5 stays unopened."""
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    actual=ContextSymbols(image).context(definition,slots=[1,2,24]);slots={r['relativeSlot']:r for r in actual['entries']}
    for index,name in((1,'Initialize'),(24,'TryInsert')):
        row=slots[index];need('own-Dictionary-helper:'+name,(row['typeName'],row['methodName'])==(DICTIONARY,name)
            and[(a['parameterOwner'].get('typeIndex'),a['parameterOwner'].get('ordinal'))for a in row['classArguments']]
                ==[(definition,0),(definition,1)])
    row=slots[2]
    need('own-key-default-comparer',(row['typeName'],row['methodName'])==('System.Collections.Generic.EqualityComparer`1','get_Default')
        and len(row['classArguments'])==1
        and(row['classArguments'][0]['parameterOwner'].get('typeIndex'),row['classArguments'][0]['parameterOwner'].get('ordinal'))==(definition,0))
    return actual


def constructor_observation(rows,definition,selected_spec):
    """Exact requested row; physical folding never becomes a method alias."""
    need('one-owned-formatter-constructor-observation',isinstance(rows,list) and len(rows)==1
        and isinstance(rows[0],dict) and type(rows[0].get('pointer'))is int and rows[0]['pointer']>0)
    row,=rows
    need('exact-requested-formatter-constructor-spec',isinstance(selected_spec,(list,tuple)) and len(selected_spec)==3
        and type(definition)is int and selected_spec[0]==definition and selected_spec[1]>=0 and selected_spec[2]==-1
        and definition in row.get('methodDefinitionIndices',[]))
    return row


def derive(image,pins,*,typed_request,call_target,count_limit=4096):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,_vtable
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack import modelview_packable_sources,npc_collection_programs
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_context
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import derive_integer
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);cs=ContextSymbols(image);ge=GenericEntries(image)
    validate_typed_usage_context(image,typed_request,label='animationIntCurveDictionarySource.parent')
    bind_typed_read(image,typed_request,method_name='ReadPackable',argument=TYPE,kind=21,reference=True)
    arg,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments;carrier=cs.type(arg.type_pointer_va)
    identity=require_carrier(carrier,ctx.index.types[VALUE].index)
    need('actual-UnityCurve-reference',ctx.is_value_type(VALUE)is False)
    dep_paths=[CONTRACTS_DIR/n for n in('npc_runtime_native.json','leveldata_npc_patrol_native.json')]
    dep_bytes={p:p.read_bytes()for p in dep_paths};core,generic=[json.loads(dep_bytes[p])for p in dep_paths]
    need('same-reviewed-reference-inputs',core.get('nativeInputs')==generic.get('nativeInputs')==pins)
    routes=copy.deepcopy(generic['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
    need('actual-owned-ReadPackable-target',type(call_target)is int and call_target==base+core['readPackable']['entryRva'])
    reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
    parent=parent_call(image,typed_request,call_target)
    td=ctx.index.types[OWNER];methods=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
    need('one-current-DictionaryFormatter-Deserialize',len(methods)==1);method,=methods
    need('own-slot5-instance-void-ABI',not method.flags&16 and method.slot==5 and method.parameter_count==2 and ctx.type_name(method.return_type)=='void')
    _vtable(image,td.index,5,method.index,'animationIntCurveDictionarySource')
    context=cs.context(td.index);context_proof=dictionary_context(image,context);slots={r['relativeSlot']:r for r in context['entries']}
    reader,output=md.parameters_for(method);rr=image.pe.bytes_at_va(ctx.type_pointer(reader.type_index),16);out=image.pe.bytes_at_va(ctx.type_pointer(output.type_index),16)
    allocated=image.pe.bytes_at_va(ctx.type_pointer(slots[3]['index']),16)
    need('Reader-and-own-open-Dictionary-byref-ABI',ctx.type_name(reader.type_index)=='MemoryPack.MemoryPackReader'
        and rr[10:12]==bytes((17,32)) and out[10:12]==bytes((21,32)) and out[:8]==allocated[:8])
    witness=ge.resolve(method.index,['int','object'],[]);actual=pointer.owned(image,witness['pointer'])
    closed=ge.observe(method.index,['int',VALUE],[])
    need('no-contradictory-closed-registration',all(r.get('pointer')==witness['pointer']for r in closed))
    key=derive_integer(image,pins);symbols=paths.symbols(actual['regions']);offsets=scalar.reader_offsets(image,'animationIntCurveDictionarySource')
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    programs=[paths.program(actual['regions'],actual['pointer'],offsets,symbols,count=n,key_callback=base+key['callbackTargetRva'],same_comparer=same)
        for same in(False,True)for n in(-1,0,1,2,3)]
    counted=paths.induction(programs,count_limit=count_limit)
    selected_helpers=helper_context(image,ctx.index.types[DICTIONARY].index)
    constructors=[];overloads=[m for m in md.methods_for(td)if md.string(m.name_index)=='.ctor']
    for arity in(0,1):
        declared,=[m for m in overloads if m.parameter_count==arity]
        observed=ge.observe(declared.index,['int','object'],[])
        need('one-current-formatter-constructor-row',len(observed)==1)
        registered=constructor_observation(observed,declared.index,ge.specs[observed[0]['methodSpecIndex']])
        body=pointer.owned(image,registered['pointer']);constructors.append(dict(methodDefinition=declared.index,registration=registered,
            windows=body['windows'],regions=[[a-base,h.hex()]for a,h in body['regions']],
            foldedMethodDefinitionsExplicit=True,uniquePhysicalMethodIdentityClaimed=False))
    def raw(row):return[(base+a,bytes.fromhex(h))for a,h in row['regions']]
    ctor_programs=[npc_collection_programs.dictionary_formatter_default(raw(constructors[0]),constructors[0]['registration']['pointer'],constructors[1]['registration']['pointer']),
        npc_collection_programs.dictionary_formatter_comparer(raw(constructors[1]),constructors[1]['registration']['pointer'],symbols['barrier'])]
    need('actual-formatter-comparer-holder',ctor_programs[1].get('storedUnchangedComparerOffset')==16)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    need('sole-owned-comparer-field',len(fields)==1 and md.string(fields[0].name_index)=='equalityComparer')
    comparer=cs.type(ctx.type_pointer(fields[0].type_index));item,=comparer['classArguments']
    need('formatter-owned-key-comparer',comparer['definition']['name']=='System.Collections.Generic.IEqualityComparer`1'
        and(item['parameterOwner']['typeIndex'],item['parameterOwner']['ordinal'])==(td.index,0))
    helpers={}
    for name in('initialize','keyProvider','valueProvider','valueDispatch','insert'):
        body=pointer.owned(image,symbols[name]);helpers[name]=dict(entryRva=symbols[name]-base,windows=body['windows'],regions=[[a-base,h.hex()]for a,h in body['regions']],rows=body['rows'])
    for p,before in dep_bytes.items():need('reference-declaration-bookend',p.read_bytes()==before)
    result=dict(schema=SCHEMA,status='validated-conditional-int-reference-dictionary-source',nativeInputs=dict(pins),typeName=TYPE,
        packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base,
        sourceTargetRva=actual['pointer']-base,sourceMethodDefinition=method.index,sourceWitnessClassArguments=['int','object'],
        callbackEqualsCanonicalRequired=True,closedPointerEquivalenceProved=bool(closed),
        proof=dict(typedRequest=typed_request,closedCarrier=carrier,nominalIdentity=identity,actualParent=parent,referenceParent=reference,
            registration=witness,closedRegistrations=closed,context=context,contextProof=context_proof,selectedDictionaryHelperContext=selected_helpers,
            readerParameterRawHex=rr.hex().upper(),outputParameterRawHex=out.hex().upper(),actualWindows=actual['windows'],
            actualSourceRegions=[[a-base,h.hex()]for a,h in actual['regions']],readerOffsets=offsets,
            symbolRvas={k:v-base for k,v in symbols.items()},programs=programs,induction=counted,
            formatterConstructors=constructors,formatterConstructorPrograms=ctor_programs,comparerFieldType=comparer,
            integerCallback=key,helpers=helpers,barrier=_barrier(image,symbols['barrier'])),
        keyGrammarAdmitted=True,valueGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own closed Int32/UnityCurve nominal parent, actual ReadPackable/zero-local reference ABI, own int/object formatter and Int32 callback, full inline capacity/comparer/default/new/null program, scoped metadata slots and saved-counter induction.',
            conditional=__doc__,structuralOnly='Stored signed keys and ordered value entries; final mutable dictionary contents are not reconstructed.',
            unresolved=['actual UnityCurve callback child and dispatcher join','live provider/closed MethodInfo/formatter selection',
                'normal Initialize/TryInsert/comparer effects','parent setter/getter/full frame','reused dictionary','whole AnimationConfig/physical EOF']))
    _publication_gate(image,pins);return json.loads(json.dumps(result))
