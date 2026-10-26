"""Finite Nullable<Single> source, independent of enclosing Enemy admission.

The selected ReadValue path requires a compatible nonnull provider result whose
slot-five callback equals the freshly registered NullableFormatter<Single>
entry and whose initialized MethodInfo matches that exact closed context. The
callback and actual inline path forward the same Reader/output to the owned
DangerousReadUnmanaged source. All eight wire bytes, including the hasValue
byte, padding and Single bits, are copied unchanged. No FF header is involved.
Normal provider/preparation effects, disjoint buffered input/output/frame and
initialized contexts remain conditions. Runtime selection is unobserved.
"""
import hashlib
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import scalar_param_native as scalar

TYPE='System.Nullable`1<float>'
FORMATTER='MemoryPack.Formatters.NullableFormatter`1'
CAP='story-nullable-single'
LABEL='storyNullableSingle'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def owned_parameter(symbol,*,owner_kind,owner):
    """Exact unmodified owned generic parameter, never a byref/name alias."""
    need('literal-owned-parameter-kind',True,owner_kind in('type','method'))
    kind=19 if owner_kind=='type'else 30;key='typeIndex'if owner_kind=='type'else'methodIndex'
    raw=bytes.fromhex(symbol['rawHex'])
    need('ordinary-owned-parameter',bytes((kind,0)),raw[10:12])
    identity=symbol['parameterOwner'];need('reciprocal-owned-parameter',(owner,0),(identity[key],identity['ordinal']))
    return identity


def raw8_program(regions,entry,offsets):
    """Exact normal buffered raw8 copy and complete Reader/frame return."""
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20','8379'+rem+'08','488bfa','488bd9');g.branch('0f8c',False)
    g.take('488b41'+cur,'488b00','488907','8b7b'+rem,'83c7f8');g.branch('0f88',False)
    g.take('488343'+cur+'08','8343'+adv+'08','8343'+used+'08','897b'+rem,
        '488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=8,outputBytes=8,outputRegister='incoming rdx',
        incomingReader='rcx',rawOutputBitsUnchanged=True,headerBytes=0,normalReturn=True,
        savedRbxRestored=True,savedRdiRestored=True,entryFrameRestored=True,
        selectedFrameBytes=40,originalOutputMustNotAliasInputOrFrame=True)


def callback_program(regions,entry,target):
    """Complete call-free selected Nullable formatter leaf ending at owned tail."""
    g=BytesPath(regions,entry)
    g.take('498b4120','4d8bd0','488bca','498bd2','4c8b80c0000000','4d8b00')
    need('callback-tail-target',target,g.relative('e9'))
    return dict(selectedBytes=g.seen,tailTarget=target,readerRegister='incoming rdx',
        outputRegister='incoming r8',classContextRegister='incoming r9',classContextSlot=0,
        physicalFunctionExtentProved=False,completeNormalTailProgram=True,
        sameReaderAndOutput=True,stackAndNonvolatilesUntouched=True)


def read_value_program(regions,entry,s):
    """Complete selected provider/callback-equality/raw8/full-RAX path."""
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20','48837a3800','488bda','488bf9');g.branch('0f84',False)
    provider_site=g.at;provider_cell=g.relative('488b0d')
    g.take('48c744243800000000','83b9e000000000');g.branch('0f84',False)
    g.take('488b4b38','488b09');g.call(s['provider'])
    g.take('488bd8','4885c0');g.branch('74',False,1)
    g.take('488b08');g.call(s['prepare'])
    g.take('488b0b','488b8190010000','4c8b8998010000')
    need('selected-callback-exact-registered-entry',s['callback'],g.relative('488d0d'))
    g.take('483bc1');g.branch('0f85',False)
    g.take('498b4120','488d542438','488bcf','4c8b80c0000000','4d8b00');g.call(s['raw8'])
    g.take('488b442438','488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,providerClassCell=provider_cell,providerClassInstruction=provider_site,readerRegister='incoming rcx',
        inputMethodInfoRegister='incoming rdx',providerContextSlot=0,formatterContextSlot=0,
        managedBytes=8,resultAbi='rax-managed-value',zeroedOutputBytes=8,outputHomeEntryOffset=16,
        savedRbxHomeEntryOffset=8,savedRdiHomeEntryOffset=-8,shadowHomeRelativeRsp=[0,32],
        temporaryAndSavedHomesDisjoint=True,selectedFrameBytes=40,
        callbackEqualsRegisteredEntryRequired=True,normalReturn=True,
        savedRbxRestored=True,savedRdiRestored=True,entryFrameRestored=True,
        copiedCompleteOutputToRax=True,wireBytesAdmittedHere=False)


def _direct_entry(image,entries,method):
    """Bound only a normal unboxed direct slot; the adjustor is opaque/unused.

    No adjustor pointer is read, no thunk-table extent is asserted, and no
    runtime invocation is inferred from a direct registration witness.
    """
    found=[]
    for index,spec_index in entries._rows_by_method.get(method.index,()):
        need('direct-table-index-bounded',True,type(index)is int and 0<=index<entries.meta['genericMethodTableCount'])
        raw=image.pe.bytes_at_va(entries.table_base+index*16,16)
        need('direct-immutable-row',entries.table[index*16:(index+1)*16],raw)
        selected,slot,invoker,adjustor=struct.unpack('<iiii',raw)
        need('direct-selected-spec-key',spec_index,selected)
        need('direct-spec-bound',True,0<=selected<len(entries.specs))
        definition,ci,mi=entries.specs[selected]
        if entries.arguments(ci)[0]!=['float']or mi!=-1:continue
        need('direct-fresh-selected-MethodSpec',struct.pack('<iii',definition,ci,mi),
            image.pe.bytes_at_va(int(entries.meta['methodSpecs'],16)+selected*12,12))
        need('direct-owned-method-definition',method.index,definition)
        need('direct-pointer-slot-bounded',True,0<=slot<entries.code['genericMethodPointersCount'])
        need('direct-invoker-slot-bounded',True,0<=invoker<entries.code['invokerPointersCount'])
        pointer=image.pe.u64_at_va(int(entries.code['genericMethodPointers'],16)+8*slot)
        need('direct-nonnull-entry',True,pointer>image.pe.image_base)
        found.append(dict(methodDefinition=definition,methodSpec=list(entries.specs[selected]),
            tableIndex=index,tableCount=entries.meta['genericMethodTableCount'],rawRegistrationHex=raw.hex().upper(),
            methodPointerSlot=slot,methodPointerCount=entries.code['genericMethodPointersCount'],
            pointer=pointer,invokerSlot=invoker,invokerCount=entries.code['invokerPointersCount'],
            closedClassInstantiation=entries.arguments(ci)[1],adjustorIndexOpaque=adjustor,
            adjustorTableExtentProved=False,adjustorDereferenced=False,adjustorAdmitted=False,
            runtimeInvocationObserved=False,physicalPointerUniquenessClaimed=False))
    need('one-exact-direct-Single-witness',1,len(found))
    return found[0]


def derive_layout(image,*,type_pointer):
    """Fresh nominal layout only; the enclosing selected operation owns gates.

    This does not select a formatter, call a constructor, or admit wire bytes.
    The supplied pointer must itself be the exact ordinary constructed value
    carrier. Its direct unboxed method witnesses leave adjustors opaque.
    """
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.memorypack.pointer_param import leaf
    need('literal-selected-type-pointer',True,type(type_pointer)is int and type_pointer>image.pe.image_base)
    ctx=NativeReferenceContext(image);md=image.metadata;sy=ContextSymbols(image)
    argument=sy.type(type_pointer);definition=ctx.index.types['System.Nullable`1']
    need('ordinary-selected-value-carrier',bytes.fromhex('1580'),bytes.fromhex(argument['rawHex'])[10:12])
    need('exact-selected-value-definition',('System.Nullable`1',definition.index,bytes.fromhex('1180')),
        (argument['definition']['name'],int.from_bytes(bytes.fromhex(argument['definition']['rawHex'])[:8],'little'),bytes.fromhex(argument['definition']['rawHex'])[10:12]))
    need('one-selected-Single-argument',1,len(argument['classArguments']))
    single=argument['classArguments'][0];need('selected-ordinary-Single',('float',bytes.fromhex('0c80')),(single['name'],bytes.fromhex(single['rawHex'])[10:12]))
    need('Nullable-value-ancestry',('System.ValueType',True,False),(ctx.parent('System.Nullable`1'),ctx.is_value_type('System.Nullable`1'),ctx.is_enum('System.Nullable`1')))
    fields=[f for f in md.fields_for(definition)if not ctx.field_attributes(f.type_index)&16]
    need('complete-owned-Nullable-fields',[('hasValue','bool'),('value','VAR')],
        [(md.string(f.name_index),'VAR'if image.pe.bytes_at_va(ctx.type_pointer(f.type_index),16)[10]==19 else ctx.type_name(f.type_index))for f in fields])
    scalar.ordinary(image,ctx.type_pointer(fields[0].type_index),2,LABEL+'.hasValue')
    parameter=owned_parameter(sy.type(ctx.type_pointer(fields[1].type_index)),owner_kind='type',owner=definition.index)
    entries=GenericEntries(image);direct={}
    for name,expected in (('.ctor',['F30F114904','C60101','C3']),('get_HasValue',['0FB601','C3']),('GetValueOrDefault',['F30F104104','C3'])):
        method,=[m for m in md.methods_for(definition)if md.string(m.name_index)==name and m.parameter_count==(1 if name=='.ctor'else 0)]
        need('direct-instance-method',0,method.flags&16)
        if name=='.ctor':
            scalar.ordinary(image,ctx.type_pointer(method.return_type),1,LABEL+'.ctor-return')
            formal,=md.parameters_for(method);owned=sy.type(ctx.type_pointer(formal.type_index))
            owned_parameter(owned,owner_kind='type',owner=definition.index)
        elif name=='get_HasValue':scalar.ordinary(image,ctx.type_pointer(method.return_type),2,LABEL+'.hasValue-return')
        else:
            owned=sy.type(ctx.type_pointer(method.return_type));owned_parameter(owned,owner_kind='type',owner=definition.index)
        direct[name]=_direct_entry(image,entries,method);direct[name]['normalUnboxedLeaf']=leaf(image,direct[name]['pointer'],expected)
    return json.loads(json.dumps(dict(typeName=TYPE,managedBytes=8,concreteTypeKind=21,valueCarrier=True,
        referenceLaneOffsets=[],paddingByteRanges=[[1,3]],hasValueByteOffset=0,singleBitsByteOffset=4,
        wireGrammarAdmitted=False,providerSelectionAdmitted=False,constructorInvocationObserved=False,
        selectedCarrier=argument,
        layout=dict(hasValue=0,single=4,managedBytes=8,fieldParameter=parameter,directWitnesses=direct))))


def derive_read_value(image,pins,*,typed_request,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import _vtable,validate_typed_usage_context,validate_generic_contexts,derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack.pointer_param import owned as own_body
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    _publication_gate(image,pins);ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base
    need('literal-actual-source-target',True,type(source_target)is int and source_target>base)
    validate_typed_usage_context(image,typed_request,label=LABEL+'.actualCaller')
    binding=bind_typed_read(image,typed_request,method_name='ReadValue',argument=TYPE,kind=21)
    layout=derive_layout(image,type_pointer=binding['argumentPointer'])
    argument=layout['selectedCarrier'];single=argument['classArguments'][0]
    sy=ContextSymbols(image);entries=GenericEntries(image)
    formatter=ctx.index.types[FORMATTER]
    deserialize,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize'and m.slot==5]
    need('canonical-formatter-instance-ABI',(0,'void',2),(deserialize.flags&16,ctx.type_name(deserialize.return_type),deserialize.parameter_count))
    _vtable(image,formatter.index,5,deserialize.index,LABEL)
    registered=entries.resolve(deserialize.index,['float'],[]);callback=registered['pointer']
    need('same-selected-Single-pointer',single['typePointerVa'],registered['classInstantiation']['arguments'][0]['type_pointer_va'])
    fc=sy.context(formatter.index);validate_generic_contexts(image,[fc],label=LABEL+'.formatter')
    slot,=[r for r in fc['entries']if r['relativeSlot']==0];nested,=slot['methodArguments'];var,=nested['classArguments']
    need('formatter-owned-raw-source',(3,'MemoryPack.MemoryPackReader','DangerousReadUnmanaged',[], -1),
        (slot['kind'],slot['typeName'],slot['methodName'],slot['classArguments'],slot['methodSpec'][1]))
    need('formatter-Nullable-VAR-argument',('System.Nullable`1',formatter.index,0),
        (nested['definition']['name'],var['parameterOwner']['typeIndex'],var['parameterOwner']['ordinal']))
    dangerous=md.methods[slot['methodSpec'][0]];formal,=md.parameters_for(dangerous)
    need('raw-source-void-instance-one-formal',(0,'void',1),(dangerous.flags&16,ctx.type_name(dangerous.return_type),dangerous.parameter_count))
    raw_formal=image.pe.bytes_at_va(ctx.type_pointer(formal.type_index),16);need('raw-source-byref-owned-MVAR',bytes.fromhex('1e20'),raw_formal[10:12])
    owned=sy.type(ctx.type_pointer(formal.type_index))['parameterOwner'];need('raw-source-MVAR-owner',(dangerous.index,0),(owned['methodIndex'],owned['ordinal']))
    # The exact registered callback is a call-free tail forwarder. Its tail
    # destination is independently owned in full by the selected unwind data.
    callback_prefix=image.pe.bytes_at_va(callback,28)
    g=BytesPath([(callback,callback_prefix)],callback)
    g.take('498b4120','4d8bd0','488bca','498bd2','4c8b80c0000000','4d8b00');raw_target=g.relative('e9')
    canonical=callback_program([(callback,callback_prefix)],callback,raw_target)
    inner=own_body(image,raw_target);actual=own_body(image,source_target)
    offsets=scalar.reader_offsets(image,LABEL);raw_program=raw8_program(inner['regions'],inner['pointer'],offsets)
    calls=[control_transfer(r)['target']for r in actual['rows']if control_transfer(r)['kind']=='call'and bytes.fromhex(r['bytes'])[:1]==b'\xe8']
    need('actual-main-helper-calls',True,len(calls)>=3)
    source_program=read_value_program(actual['regions'],actual['pointer'],dict(provider=calls[0],prepare=calls[1],callback=callback,raw8=raw_target))
    rc=sy.context(typed_request['methodSpec'][0],is_method=True);validate_generic_contexts(image,[rc],label=LABEL+'.reader')
    return_symbol=sy.type(ctx.type_pointer(md.methods[typed_request['methodSpec'][0]].return_type))
    owned_parameter(return_symbol,owner_kind='method',owner=typed_request['methodSpec'][0])
    rslot,=[r for r in rc['entries']if r['relativeSlot']==0];provider=md.methods[rslot['methodSpec'][0]]
    need('provider-static-noargs',(16,0),(provider.flags&16,provider.parameter_count))
    need('exact-ReadValue-provider-context',(3,'MemoryPack.MemoryPackFormatterProvider','GetFormatter',typed_request['methodSpec'][0],0),
        (rslot['kind'],rslot['typeName'],rslot['methodName'],rslot['methodArguments'][0]['parameterOwner']['methodIndex'],rslot['methodArguments'][0]['parameterOwner']['ordinal']))
    provider_class=derive_typed_usage_context(image,source_program['providerClassInstruction']-base,label=LABEL+'.providerClass')
    need('actual-provider-class-cell',(1,'MemoryPack.MemoryPackFormatterProvider'),(provider_class['tag'],provider_class['typeName']))
    parameters=list(md.parameters_for(deserialize));need('callback-byref-formals',2,len(parameters))
    first=sy.type(ctx.type_pointer(parameters[0].type_index));second=sy.type(ctx.type_pointer(parameters[1].type_index))
    need('callback-reader-byref',('MemoryPack.MemoryPackReader',bytes.fromhex('1120')),(first['name'],bytes.fromhex(first['rawHex'])[10:12]))
    need('callback-Nullable-byref',('System.Nullable`1',bytes.fromhex('1520'),formatter.index,0),
        (second['definition']['name'],bytes.fromhex(second['rawHex'])[10:12],second['classArguments'][0]['parameterOwner']['typeIndex'],second['classArguments'][0]['parameterOwner']['ordinal']))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.story-nullable-single-source.v1',status='validated-conditional-source',nativeInputs=pins,
        typeName=TYPE,capability=dict(typeName=TYPE,capability=CAP,managedBytes=8,wireBytes=8,headerBytes=0,
            resultAbi='rax-managed-value',readerMethodDefinition=typed_request['methodSpec'][0],sourceTargetRva=source_target-base,
            concreteTypeKind=21,valueCarrier=True,actualSourceProved=True,wireGrammarAdmitted=True,
            hasValueByteOffset=0,paddingByteRanges=[[1,3]],singleBitsByteOffset=4,
            rawBitsPreserved=True,hasValueByteNormalized=False,nullHeaderAdmitted=False,
            actualCallbackEqualsProvedChildRequired=True,runtimeProviderSelectionObserved=False,
            parentFieldAdmitted=False,wholeOwnerAdmitted=False),
        proof=dict(typedRequest=typed_request,typedBinding=binding,selectedCarrier=argument,
            layout=layout['layout'],
            formatterRegistration=registered,formatterContext=fc,readerContext=rc,providerClass=provider_class,
            canonicalCallback=canonical,raw8=raw_program,actualReadValue=source_program,
            readerOffsets=offsets,sourceSymbolsRva=dict(provider=calls[0]-base,prepare=calls[1]-base,
                callback=callback-base,raw8=raw_target-base),
            sourceRegions=dict(actual=[[at-base,raw.hex().upper()]for at,raw in actual['regions']],
                raw8=[[at-base,raw.hex().upper()]for at,raw in inner['regions']],
                callbackPrefix=[[callback-base,callback_prefix.hex().upper()]]),
            sourceWindows=dict(actual=actual['windows'],raw8=inner['windows'],callbackPrefix=dict(startRva=callback-base,
                endRva=callback-base+28,sha256=hashlib.sha256(callback_prefix).hexdigest().upper(),physicalExtentProved=False))),
        evidenceBoundary=dict(exact='Fresh closed Nullable<Single> value21 carrier, exact bounded direct normal unboxed layout witnesses, registered NullableFormatter<Single> callback/context, full selected actual ReadValue and raw8 Reader/output/frame programs.',
            conditional=__doc__,unresolved=['actual enclosing local/setter/frame','runtime provider/default/override selection','cold/refill paths',
                'opaque unused adjustor indices and thunk-table extent','constructor invocation','whole owner/physical EOF']))))
