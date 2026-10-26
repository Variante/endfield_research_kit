"""Independent UInt32 key callback below Char's static dictionary source.

The four-byte machine path is replayed against its own closed uint formatter
registration. It is not an Int32, enum or dictionary-pointer equivalence claim.
String keys use the independently owned pooled String callback.
"""
import json

SCHEMA='endfield.char-static-UInt32-callback.v1'


def need(check,condition):
    if not condition:raise ValueError('charStaticDictionaryCallback.'+check)


def derive_unsigned(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.context import type_parameter_owner
    from scripts.game_data.il2cpp.formatter_composition import _vtable
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack.levelscript_interactive_sources import unmanaged_u32_program
    from scripts.game_data.memorypack.generated_called_advance_sources import derive as derive_advance
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    owner=ctx.index.types['MemoryPack.Formatters.UnmanagedFormatter`1']
    methods=[m for m in md.methods_for(owner)if md.string(m.name_index)=='Deserialize']
    need('one-owned-uint-formatter',len(methods)==1);method,=methods;parameters=list(md.parameters_for(method))
    need('own-instance-void-two',not method.flags&16 and ctx.type_name(method.return_type)=='void'
        and method.parameter_count==len(parameters)==2)
    _vtable(image,owner.index,5,method.index,'charStaticDictionaryUInt')
    reader=image.pe.bytes_at_va(ctx.type_pointer(parameters[0].type_index),16)
    output=image.pe.bytes_at_va(ctx.type_pointer(parameters[1].type_index),16)
    need('own-Reader-byref-and-VAR-output',ctx.type_name(parameters[0].type_index)=='MemoryPack.MemoryPackReader'
        and reader[10:12]==bytes((17,32))and output[10:12]==bytes((19,32)))
    parameter=type_parameter_owner(md.buf,int.from_bytes(output[:8],'little'),
        [t.generic_container_index for t in md.types],source='charStaticDictionaryUInt')
    need('sole-own-class-parameter',(parameter.get('typeIndex'),parameter.get('ordinal'))==(owner.index,0))
    registration=GenericEntries(image).resolve(method.index,['uint'],[]);arg,=registration['classInstantiation']['arguments']
    scalar.ordinary(image,arg['type_pointer_va'],9,'charStaticDictionaryUInt.argument')
    need('actual-UInt32-kind9-carrier',bytes.fromhex(arg['raw_type_record_hex'])[10:12]==bytes((9,128)))
    actual=pointer.owned(image,registration['pointer']);offsets=scalar.reader_offsets(image,'charStaticDictionaryUInt')
    g=BytesPath(actual['regions'],registration['pointer']);b=lambda n:bytes((offsets[n],)).hex()
    g.take('48895c2408','57','4883ec20','837a'+b('bufferLength')+'04','498bf8','488bda');g.branch('0f8c',False)
    g.take('488b42'+b('currentPtr'),'8b00','ba04000000','488bcb','8907','488b5c2430','4883c420','5f')
    advance_target=g.relative('e9')
    program=unmanaged_u32_program(actual['regions'],registration['pointer'],{'advance':advance_target},offsets)
    advance=derive_advance(image,pins,target=advance_target,offsets=offsets)
    result=dict(schema=SCHEMA,status='validated-conditional-callback',nativeInputs=pins,typeName='uint',
        wireBytes=4,outputBytes=4,callbackSlot=5,callbackMethodDefinition=method.index,
        callbackTargetRva=registration['pointer']-base,numericConversion=False,actualRuntimeSelectionObserved=False,
        proof=dict(registration=registration,readerParameterRawHex=reader.hex(),outputParameterRawHex=output.hex(),
            outputParameterOwner=parameter,windows=actual['windows'],regions=[[at-base,raw.hex()]for at,raw in actual['regions']],
            readerOffsets=offsets,program=program,advanceSource=advance),
        conditions=['Exact ready UInt32 provider selects this independently registered slot5 callback and coherent MethodInfo.',
            'Sufficient coherent disjoint buffered input/output, nonwrapping Reader updates and normal Win64 returns.'])
    _publication_gate(image,pins);result=json.loads(json.dumps(result));verify_unsigned(result,pins);return result


def verify_unsigned(callback,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.levelscript_interactive_sources import unmanaged_u32_program
    from scripts.game_data.memorypack.generated_called_advance_sources import advance_program
    need('own-current-UInt32-callback',callback.get('schema')==SCHEMA and callback.get('nativeInputs')==pins
        and callback.get('status')=='validated-conditional-callback'and callback.get('typeName')=='uint'
        and callback.get('wireBytes')==callback.get('outputBytes')==4 and callback.get('callbackSlot')==5
        and callback.get('numericConversion')is False and callback.get('actualRuntimeSelectionObserved')is False
        and len(callback.get('conditions',[]))==2)
    p=callback['proof'];registration=p['registration'];base=registration['pointer']-callback['callbackTargetRva']
    args=registration['classInstantiation']['arguments'];need('independent-closed-uint-registration',
        registration.get('methodDefinitionIndices')==[callback['callbackMethodDefinition']]and len(args)==1
        and bytes.fromhex(args[0]['raw_type_record_hex'])[10:12]==bytes((9,128))
        and bytes.fromhex(p['readerParameterRawHex'])[10:12]==bytes((17,32))
        and bytes.fromhex(p['outputParameterRawHex'])[10:12]==bytes((19,32))
        and p['outputParameterOwner'].get('ordinal')==0)
    raw=regions(p['windows'],p['regions'],base,'char-UInt32-callback')
    advance=p['advanceSource'];need('same-owned-Advance-reader-layout',advance.get('nativeInputs')==pins
        and advance.get('readerOffsets')==p['readerOffsets']and advance.get('completeAdvanceProgramProved')is True
        and advance.get('allFourReaderUpdatesProved')is True and advance.get('entryRspRestored')is True
        and advance.get('allNonvolatilesRestored')is True and advance.get('registeredMethodIdentityClaimed')is False
        and advance.get('childGrammarAdmitted')is False
        and advance.get('family',{}).get('selectedPrimaryRva')==advance.get('targetRva'))
    advance_raw=regions(advance['codeWindows'],[[a-base,h]for a,h in advance['sourceRegions']],base,'char-UInt32-Advance')
    need('full-actual-Advance-byte-replay',json.loads(json.dumps([advance_program(advance_raw,
        base+advance['targetRva'],p['readerOffsets'],zero=zero)for zero in(False,True)]))==advance['programs'])
    need('full-actual-UInt32-byte-replay',json.loads(json.dumps(unmanaged_u32_program(raw,
        base+callback['callbackTargetRva'],{'advance':base+advance['targetRva']},p['readerOffsets'])))==p['program'])
    return base


def unsigned_dispatch(actual,callback,base):
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.levelscript_interactive_sources import u32_dispatch_program
    need('own-unsigned-source-and-callback',actual.get('keyType')==callback.get('typeName')=='uint'
        and actual.get('nativeInputs')==callback.get('nativeInputs'))
    helper=actual['proof']['helpers']['keyDispatch'];need('actual-owned-key-helper',
        helper['entryRva']==actual['proof']['symbolRvas']['keyDispatch'])
    raw=regions(helper['windows'],helper['regions'],base,'char-UInt32-dispatch')
    calls=[control_transfer(row)['target']for row in helper['rows']if bytes.fromhex(row['bytes'])[:1]==b'\xe8']
    need('actual-dispatch-preparation',bool(calls))
    program=u32_dispatch_program(raw,base+helper['entryRva'],dict(prepare=calls[0],
        callback=base+callback['callbackTargetRva'],advance=base+callback['proof']['advanceSource']['targetRva']),
        actual['proof']['readerOffsets'])
    return json.loads(json.dumps(dict(sourceTargetRva=helper['entryRva'],callbackTargetRva=callback['callbackTargetRva'],
        program=program,actualPointerAliasInferred=False,callbackSelectionConditional=True,runtimeSelectionObserved=False)))
