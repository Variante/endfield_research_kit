"""Exact provider open List-to-ListFormatter insertion argument slice.

The current provider initializer loads the actual open List and ListFormatter
type usages, calls the same selected System.Type.GetTypeFromHandle entry,
preserves the first returned Type as the key, and supplies the second return
as the value to the actual closed Dictionary<Type,Type>.Add request. The map
receiver is the unchanged incoming RDI for this bounded slice. Its prior
allocation, dictionary effects, final static publication and later lookup are
not supplied by the two type names or by this source interval.

All actual owned initializer bytes are independently partitioned and decoded,
including the real final tail jump. Enclosing tail/return semantics remain
explicitly unadmitted. This source-only mapping claim neither constructs an
actual closed enum formatter nor establishes a receiver/MethodInfo callback,
element width, list grammar, current parent admission or whole owner.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-provider-open-list-mapping.v1'
LABEL='enumProviderOpenListMapping'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def program(regions,entry):
    g=BytesPath(regions,entry);key_cell=g.relative('488b0d');g.take('33d2');key_type=g.relative('e8')
    value_site=g.at;value_cell=g.relative('488b0d');g.take('33d2','488bd8')
    value_type=g.relative('e8');need('same-actual-get-type-from-handle',key_type==value_type)
    add_site=g.at;method_cell=g.relative('4c8b0d')
    g.take('4c8bc0','488bd3','488bcf');call=g.at;add=g.relative('e8')
    return dict(selectedBytes=g.seen,entry=entry,end=g.at,keyTypeUsageCell=key_cell,
        valueTypeUsageInstruction=value_site,valueTypeUsageCell=value_cell,typeFromHandleTarget=key_type,
        addMethodUsageInstruction=add_site,addMethodUsageCell=method_cell,addCall=call,addTarget=add,
        actualArguments=dict(rcx='unchanged incoming RDI dictionary receiver',rdx='first actual Type result',
            r8='second actual Type result',r9='actual closed Dictionary.Add MethodInfo'),
        nullTypeFromHandleMethodInfo=True,normalAbiPreservingTypeCallsRequired=True,
        coherentTypedDictionaryReceiverRequired=True,enclosingFrameAndReturnProved=False,
        dictionaryInsertionOrClosedFormatterSelectionProved=False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.enum_initialization_instructions import decode_enum_initialization_instructions
    from scripts.game_data.il2cpp.owned_partition import checked_rows,check_byte_partition
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base
    owners=[m for m in md.methods_for(ctx.index.types['MemoryPack.MemoryPackFormatterProvider'])if md.string(m.name_index)=='.cctor']
    need('one-current-provider-initializer',len(owners)==1);method,=owners
    body=owned(image,image.method_pointer_va(method));rows=[];candidates=[]
    for at,raw in body['regions']:
        decoded=checked_rows(decode_enum_initialization_instructions(image.mapper,raw,at),raw,LABEL);rows+=decoded
        for row in decoded:
            data=bytes.fromhex(row['bytes'])
            if len(data)!=7 or data[:3]!=bytes.fromhex('488b0d'):continue
            try:usage=derive_typed_usage_context(image,int(row['va'],16)-base,label=LABEL)
            except ValueError:continue
            if usage.get('tag')==2 and usage.get('typeName')=='System.Collections.Generic.List`1':candidates.append(usage)
    rows.sort(key=lambda row:int(row['va'],16));need('one-actual-open-list-key-usage',len(candidates)==1);key,=candidates
    check_byte_partition([(a,a+len(raw))for a,raw in body['regions']],
        [(int(r['va'],16),int(r['va'],16)+len(bytes.fromhex(r['bytes'])),'instruction')for r in rows],LABEL)
    source=program(body['regions'],base+key['instructionRva'])
    value=derive_typed_usage_context(image,source['valueTypeUsageInstruction']-base,label=LABEL)
    add=derive_typed_usage_context(image,source['addMethodUsageInstruction']-base,label=LABEL)
    need('actual-open-list-and-list-formatter-types',value.get('tag')==2 and value.get('typeName')=='MemoryPack.Formatters.ListFormatter`1')
    need('actual-closed-type-map-add-request',add.get('tag')==6 and add.get('typeName')=='System.Collections.Generic.Dictionary`2'
        and add.get('methodName')=='Add'and add.get('classArguments')==['System.Type','System.Type']and add.get('methodArguments')==[])
    type_methods=[m for m in md.methods_for(ctx.index.types['System.Type'])if md.string(m.name_index)=='GetTypeFromHandle'
        and[ctx.type_name(p.type_index)for p in md.parameters_for(m)]==['System.RuntimeTypeHandle']]
    need('one-actual-named-type-from-handle',len(type_methods)==1);type_method,=type_methods
    need('same-actual-named-type-from-handle-entry',image.method_pointer_va(type_method)==source['typeFromHandleTarget'])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-bounded-source-only',nativeInputs=pins,
        proof=dict(initializerMethod=[method.index,'MemoryPack.MemoryPackFormatterProvider','.cctor'],
            initializerWindows=body['windows'],ownedDecodedInstructionCount=len(rows),completeOwnedInstructionPartitionChecked=True,
            selectedMappingSlice=source,keyTypeUsage=key,valueTypeUsage=value,addMethodUsage=add,
            typeFromHandleMethod=[type_method.index,'System.Type','GetTypeFromHandle']),
        exactOpenListFormatterMapArgumentSliceProved=True,initializerCompleteReturnProved=False,
        initializedProviderMapOrActualClosedFormatterProved=False,concreteEnumCallbackSelected=False,
        wireGrammarAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Actual open List/ListFormatter usages, named TypeFromHandle target, unchanged key/value/receiver and closed Dictionary<Type,Type>.Add MethodInfo argument slice; full owned byte partition only.',
            conditional=__doc__,structuralOnly='Open generic type-to-formatter map insertion arguments.',
            unresolved=['prior map receiver allocation and Add semantics','initializer final tail/return and map publication/history',
                'reflection constructed closed receiver and actual MethodInfo/callback','wire/parent/EOF']))))
