"""Own UInt64/reference Module dictionary source and bounded count induction.

This is Dictionary<ulong,Module>, not Rune's ulong/int pair storage. The source
owns key8 and reference-output8 independently; the Module union grammar and
whole containing root/frame remain separate obligations. Actual matching
canonical callbacks and compatible typed helper returns remain conditions.
"""
import json
from scripts.game_data.memorypack import levelscript_ulong_dictionary_sources as paths

ROOT='Beyond.Gameplay.LevelScriptData'
VALUE='Beyond.Gameplay.LevelScriptModuleData'
TYPE='System.Collections.Generic.Dictionary`2<ulong,'+VALUE+'>'
SCHEMA='endfield.story-module-ulong-dictionary-source.v1'
LIMIT=4096


def need(check,condition):
    if not condition:raise ValueError('moduleUlongDictionary.'+check)


def norm(value):return json.loads(json.dumps(value))


def request_shape(usage):
    need('own-actual-reference-ReadPackable-request',
        tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[TYPE])
        and isinstance(usage.get('methodSpec'),(list,tuple))and len(usage['methodSpec'])==3
        and all(type(n)is int for n in usage['methodSpec'])and usage['methodSpec'][1]==-1
        and len(bytes.fromhex(usage.get('instructionHex','')))==7
        and bytes.fromhex(usage['instructionHex'])[:3]==bytes.fromhex('488b15'))


def require_carrier(carrier,value_definition):
    need('exact-closed-dictionary-carrier',carrier.get('name')==TYPE
        and carrier.get('definition',{}).get('name')=='System.Collections.Generic.Dictionary`2'
        and len(carrier.get('classArguments',[]))==2
        and bytes.fromhex(carrier.get('rawHex',''))[10:12]==bytes((21,0)))
    key,value=carrier['classArguments'];kr=bytes.fromhex(key.get('rawHex',''));vr=bytes.fromhex(value.get('rawHex',''))
    need('separate-UInt64-and-own-Module-CLASS',key.get('name')=='ulong'and len(kr)==16 and kr[10:12]==bytes((11,128))
        and value.get('name')==VALUE and len(vr)==16 and vr[10:12]==bytes((18,0))
        and type(value_definition)is int and int.from_bytes(vr[:8],'little')==value_definition)


def parent_program(regions,instruction,*,call_target,field_offset):
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    from scripts.game_data.memorypack.pooled_string_list_sources import flag
    need('own-declared-root-modules-field',type(field_offset)is int and field_offset>=128)
    g=BytesPath(regions,instruction-3);g.take('498bcd');usage=g.at;cell=g.relative('488b15');g.take('498b1f')
    call=g.at;g.call(call_target);g.take('4885db');g.branch('0f84',False)
    g.take('4c8b4310','4d85c0');g.branch('0f84',False)
    disabled=flag(g,'833d');g.take('498980'+field_offset.to_bytes(4,'little').hex());g.branch('74',True,1)
    return dict(selectedBytes=g.seen,contextInstructionVa=usage,contextCellVa=cell,callInstructionVa=call,
        fieldOffset=field_offset,sameReturnedRaxReferenceStored=True,readerRegister='r13',wrapperOutputRegister='r15',
        originalHolderOffset=16,collectorDisabledFlagVa=disabled,wholeParentFrameAdmitted=False)


def induction(programs,*,count_limit=LIMIT):
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    need('literal-finite-positive-domain',type(count_limit)is int and 3<=count_limit<=LIMIT)
    proofs=[]
    for same in(False,True):
        selected=[dict(p,elementCallbacks=max(p['countWitness'],0))for p in programs
            if p['countWitness']>=0 and p['comparerMatchesDefault']is same]
        need('four-exact-comparer-witnesses',sorted(p['countWitness']for p in selected)==[0,1,2,3])
        certificate=prove_induction(selected,initial='4533e4',increment='41ffc4',comparison='453be5',
            counter='r12d',saved_count='Immutable signed R13D; R12 counter preserved at RSP+56 independently of key8 RSP+168 and reference8 RSP+48',
            max_count=count_limit,mode_key='newDictionary',backedge_sites=[next(p['loopBackEdge']for p in selected if p['countWitness']==1)])
        proofs.append(dict(comparerMatchesDefault=same,proof=certificate))
    return dict(schema='endfield.module-ulong-dictionary-loop-induction.v1',maxCount=count_limit,
        positiveCountRange=[0,count_limit],comparerPaths=proofs,counterHomeRsp=[56,64],keyHomeRsp=[168,176],
        valueHomeRsp=[48,56],callShadowRsp=[0,32],fifthArgumentHomeRsp=[32,40],
        keyWireBytes=8,valueOutputBytes=8,elementGrammarAdmitted=False,parentFieldAdmitted=False)


def programs(regions,entry,offsets,symbols,*,count_limit=LIMIT):
    rows=[paths.dictionary_program(regions,entry,offsets,symbols,count=n,same_comparer=same,induction_witness=True)
        for n in(-1,0,1,2,3)for same in(False,True)]
    return rows,induction(rows,count_limit=count_limit)


def verify_source(actual,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.levelscript_collection_sources import ulong_formatter_program
    need('own-narrow-source-proof',actual.get('schema')==SCHEMA and actual.get('nativeInputs')==pins
        and actual.get('status')=='validated-conditional-module-ulong-dictionary-source'
        and actual.get('typeName')==TYPE and actual.get('keyWireBytes')==8 and actual.get('valueOutputBytes')==8
        and actual.get('headerBytes')==4 and isinstance(actual.get('countRange'),list)and len(actual['countRange'])==2
        and all(type(n)is int for n in actual['countRange'])and actual['countRange'][0]==-1 and 3<=actual['countRange'][1]<=LIMIT
        and actual.get('initiallyNullOutputRequired')is True
        and all(actual.get(k)is False for k in('valueGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted','closedPointerEquivalenceProved')))
    p=actual['proof'];base=p['imageBase'];need('explicit-selected-image-base',type(base)is int and base>=1<<32)
    request_shape(p['typedRequest']);require_carrier(p['closedCarrier'],p['valueTypeDefinition'])
    raw=regions(p['windows'],p['regions'],base,'module-ulong-dictionary');s={k:base+v for k,v in p['symbolRvas'].items()}
    selected,certificate=programs(raw,base+p['dictionaryTargetRva'],p['readerOffsets'],s,count_limit=actual['countRange'][1])
    need('full-owned-five-count-programs-and-both-comparers',norm(selected)==p['programs']and norm(certificate)==p['induction'])
    key=p['key'];raw=regions(key['windows'],key['regions'],base,'module-UInt64-key')
    need('own-UInt64-callback-and-full-raw8-source',key['registration']['pointer']==s['keyCallback']
        and key['registration']['methodDefinitionIndices']==[key['methodDefinition']]
        and len(key['registration']['classInstantiation']['arguments'])==1
        and bytes.fromhex(key['registration']['classInstantiation']['arguments'][0]['raw_type_record_hex'])[10:12]==bytes((11,128))
        and norm(ulong_formatter_program(raw,s['keyCallback'],p['readerOffsets']))==key['program'])
    abi=key['abi'];need('own-UInt64-callback-formal-byrefs',abi.get('instance')is True and abi.get('slot')==5
        and abi.get('returnType')=='void'and bytes.fromhex(abi['readerRawHex'])[10:12]==bytes((17,32))
        and bytes.fromhex(abi['output']['rawHex'])[10:12]==bytes((19,32))
        and abi['output']['parameterOwner'].get('typeIndex')==abi['declaringType']
        and abi['output']['parameterOwner'].get('ordinal')==0)
    parent=p['parent'];raw=regions(parent['windows'],parent['regions'],base,'Module-root-parent')
    need('same-actual-root-Module-call-and-reference-store',parent['typeName']==ROOT
        and parent['fieldName']=='modules'and parent['fieldType']==TYPE
        and norm(parent_program(raw,base+p['typedRequest']['instructionRva'],call_target=base+p['callTargetRva'],
            field_offset=parent['fieldOffset']))==parent['program'])
    return base


def bind_callback(actual,pins,adapter):
    """Own actual selected dispatcher paths; admit no Module child grammar."""
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.reference_adapter_sources import dispatch
    base=verify_source(actual,pins);binding=adapter.get('callbackBinding',{});routes=adapter.get('canonicalRoutes',{})
    need('independent-own-Module-canonical-adapter',adapter.get('schema')=='endfield.reference-object-adapter-source.v1'
        and adapter.get('nativeInputs')==pins and adapter.get('typeName')==VALUE
        and binding.get('actualCallbackEqualsCanonicalRequired')is True and binding.get('runtimeSelectionObserved')is False
        and routes.get('symbolRvas',{}).get('main')==binding.get('canonicalTargetRva'))
    helper=actual['proof']['helpers']['valueDispatch'];raw=regions(helper['windows'],helper['regions'],base,'Module-value-dispatch')
    symbols={k:base+v for k,v in routes['symbolRvas'].items()}
    parsed=[dispatch(raw,base+helper['targetRva'],symbols,**kw)for kw in(
        {},dict(create=False),dict(wrapper_null=True),dict(create=False,wrapper_null=True),dict(null=True))]
    return norm(dict(typeName=VALUE,canonicalAdapterTargetRva=binding['canonicalTargetRva'],
        actualDispatchTargetRva=helper['targetRva'],programs=parsed,actualCallbackEqualsProvedChildRequired=True,
        actualPointerAliasInferred=False,elementGrammarAdmitted=False))


def derive(image,pins,*,typed_request,call_target,count_limit=LIMIT):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_typed_usage_context,_vtable
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
    from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_context
    from scripts.game_data.memorypack.levelscript_collection_sources import ulong_formatter_program
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,modelview_packable_sources
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
    request_shape(typed_request);validate_typed_usage_context(image,typed_request,label='moduleUlongDictionary.actual')
    bind_typed_read(image,typed_request,method_name='ReadPackable',argument=TYPE,kind=21,reference=True)
    argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments;cs=ContextSymbols(image)
    carrier=cs.type(argument.type_pointer_va);require_carrier(carrier,ctx.index.types[VALUE].index)
    need('own-Module-reference-nominal',ctx.is_value_type(VALUE)is False)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==ROOT]
    member,=[m for m in wrapper.members if m.name=='modules'];need('actual-named-Module-root-field',member.declared_type==TYPE)
    declared=ctx.field(ROOT+'::modules');need('own-declared-reference-field',declared[:2]==(ROOT,TYPE))
    parent=pointer.owned(image,image.method_pointer_va(pointer.methods(image,wrapper)['Deserialize']))
    parent_path=parent_program(parent['regions'],base+typed_request['instructionRva'],call_target=call_target,field_offset=declared[2])
    need('same-actual-RDX-MethodInfo-cell',parent_path['contextCellVa']==base+typed_request['usageCellRva'])
    core=_load('npc_runtime_native.json',pins)['readPackable'];generic=_load('leveldata_npc_patrol_native.json',pins)['declarations']
    need('same-owned-reference-ReadPackable-entry',call_target==base+core['entryRva'])
    import copy
    routes=copy.deepcopy(generic['adapters']['referenceRoutes']);routes['wrappers']=[]
    frontend=modelview_packable_sources.validate_components(image,pins,core,routes)
    owner=ctx.index.types['MemoryPack.Formatters.DictionaryFormatter`2']
    method,=[m for m in md.methods_for(owner)if md.string(m.name_index)=='Deserialize'];_vtable(image,owner.index,5,method.index,'moduleUlongDictionary')
    need('own-instance-slot5-two-out-ABI',not method.flags&16 and method.slot==5 and method.parameter_count==2 and ctx.type_name(method.return_type)=='void')
    context=cs.context(owner.index);context_proof=dictionary_context(image,context);slots={r['relativeSlot']:r for r in context['entries']}
    reader,out=md.parameters_for(method);rr=image.pe.bytes_at_va(ctx.type_pointer(reader.type_index),16);output=image.pe.bytes_at_va(ctx.type_pointer(out.type_index),16)
    declared_out=image.pe.bytes_at_va(ctx.type_pointer(slots[3]['index']),16)
    need('own-exact-Reader-and-Dictionary-byrefs',rr[10:12]==bytes((17,32))and int.from_bytes(rr[:8],'little')==ctx.index.types['MemoryPack.MemoryPackReader'].index
        and output[10:12]==bytes((21,32))and output[:8]==declared_out[:8])
    registration=ge.resolve(method.index,['ulong','object'],[]);body=pointer.owned(image,registration['pointer'])
    key_owner=ctx.index.types['MemoryPack.Formatters.UnmanagedFormatter`1']
    key_method,=[m for m in md.methods_for(key_owner)if md.string(m.name_index)=='Deserialize'];_vtable(image,key_owner.index,5,key_method.index,'moduleUlongDictionary.key')
    key_reader,key_out=md.parameters_for(key_method);kr=image.pe.bytes_at_va(ctx.type_pointer(key_reader.type_index),16)
    key_output=cs.type(ctx.type_pointer(key_out.type_index))
    need('own-Unmanaged-UInt64-instance-callback-ABI',not key_method.flags&16 and key_method.slot==5 and key_method.parameter_count==2
        and ctx.type_name(key_method.return_type)=='void'and kr[10:12]==bytes((17,32))
        and int.from_bytes(kr[:8],'little')==ctx.index.types['MemoryPack.MemoryPackReader'].index
        and bytes.fromhex(key_output['rawHex'])[10:12]==bytes((19,32))
        and key_output['parameterOwner'].get('typeIndex')==key_owner.index and key_output['parameterOwner'].get('ordinal')==0)
    key_registration=ge.resolve(key_method.index,['ulong'],[]);key=pointer.owned(image,key_registration['pointer'])
    symbols={k:_body_target(body,text)for k,text in(('context','mov rcx, [rcx+0xc0]'),('allocate','mov rcx, rax'),
        ('initialize','mov r8, [r8+0x8]'),('comparer','mov rcx, [rcx+0x10]'),('barrier','mov [r15], rdi'),
        ('keyProvider','mov rcx, [rcx+0x30]'),('valueProvider','mov rcx, [rcx+0x38]'),('prepare','mov rcx, [r14]'),
        ('valueDispatch','mov rdx, rbp'),('tryInsert','mov r9b, 0x2'))};symbols['keyCallback']=key['pointer']
    offsets=scalar.reader_offsets(image,'moduleUlongDictionary');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    selected,certificate=programs(body['regions'],body['pointer'],offsets,symbols,count_limit=count_limit)
    key_program=ulong_formatter_program(key['regions'],key['pointer'],offsets)
    observations=ge.observe(method.index,['ulong',VALUE],[])
    need('no-contradictory-closed-Module-formatter-entry',all(r.get('pointer')==body['pointer']for r in observations))
    helpers={name:pointer.owned(image,symbols[name])for name in('valueDispatch','initialize','comparer','tryInsert','keyProvider','valueProvider')}
    result=norm(dict(schema=SCHEMA,status='validated-conditional-module-ulong-dictionary-source',nativeInputs=pins,
        typeName=TYPE,keyType='ulong',valueType=VALUE,headerBytes=4,keyWireBytes=8,valueOutputBytes=8,countRange=[-1,count_limit],
        initiallyNullOutputRequired=True,valueGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        closedPointerEquivalenceProved=False,actualCallbackSelectionObserved=False,
        proof=dict(imageBase=base,typedRequest=typed_request,callTargetRva=call_target-base,closedCarrier=carrier,valueTypeDefinition=ctx.index.types[VALUE].index,
            registration=registration,closedRegistrationObservations=observations,dictionaryTargetRva=body['pointer']-base,
            windows=body['windows'],regions=[[a-base,h.hex().upper()]for a,h in body['regions']],programs=selected,induction=certificate,
            context=context,contextProof=context_proof,readerOffsets=offsets,symbolRvas={k:v-base for k,v in symbols.items()},referenceFrontend=frontend,
            readerParameterRawHex=rr.hex().upper(),outputParameterRawHex=output.hex().upper(),
            key=dict(registration=key_registration,methodDefinition=key_method.index,windows=key['windows'],
                regions=[[a-base,h.hex().upper()]for a,h in key['regions']],program=key_program,
                abi=dict(instance=True,slot=5,returnType='void',declaringType=key_owner.index,readerRawHex=kr.hex().upper(),output=key_output)),
            parent=dict(typeName=ROOT,wrapperName=wrapper.name,methodDefinition=pointer.methods(image,wrapper)['Deserialize'].index,
                fieldName='modules',fieldType=TYPE,fieldOffset=declared[2],windows=parent['windows'],
                regions=[[a-base,h.hex().upper()]for a,h in parent['regions']],program=parent_path),
            helpers={name:dict(targetRva=v['pointer']-base,windows=v['windows'],regions=[[a-base,h.hex().upper()]for a,h in v['regions']])for name,v in helpers.items()}),
        evidenceBoundary=dict(exact='Actual root Module dictionary declaration/ReadPackable fragment, closed UInt64/Module carrier, own formatter contexts and raw key8/reference8/insert/frame byte programs with both comparer paths and bounded induction.',
            conditional='Fresh null frontend output, initialized coherent exact K/V contexts, selected canonical callbacks, normal typed allocation/Initialize/comparer/provider/TryInsert/preparation and disabled collector effects. Serialized duplicate entries survive; final mutation, Module child grammar and containing root/frame remain separate.')))
    verify_source(result,pins);_publication_gate(image,pins);return result
