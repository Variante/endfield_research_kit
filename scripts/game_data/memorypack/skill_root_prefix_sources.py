"""Selected current SkillData continuation through named members one to four.

This extends the independently proved root49/ActionGroup field0 prefix on the
same initialized existing nonnull wrapper/original path. Exact source bytes
preserve the incoming Reader and root holder, join each actual typed request,
and store unchanged Int32/enum32/reference results in the named original fields.
The enum's actual Int32 backing is proved without restricting authored values.

DataPair is a value type. Its reference List container admits only signed
counts -1/0 through its independently proved closed value-element list source.
Its positive value callback/storage has no admission. BuffInputBase admits only the canonical
reference adapter's buffered FF path, with an exact closed ReadValue identity.
Neither a nominal list request nor a matching reference width admits elements
or positive BuffInputBase values. Live formatter/cache/provider selection,
normal helper/collector effects and coherent initialized generic contexts remain
conditions. Cold refill, new/null root wrappers, members5..48, the root's full
return and whole SkillData/EOF remain unproved. No historical root48 framing or
terminal receipt supplies bytes to this continuation.
"""
from __future__ import annotations

import json
import copy

from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import primitive_param, scalar_param_native as scalar
from scripts.game_data.memorypack.pointer_param import methods, owned
from scripts.game_data.memorypack.skill_shared_sequence_sources import (
    _selected_wrapper, selected_inputs, _fast_barrier,
)
from scripts.game_data.memorypack.vector_layout import vector_recorder

LABEL = 'skillRootPrefixSources'
SCHEMA = 'endfield.skill-root-prefix-source.v1'
ROOT = 'Beyond.Gameplay.Core.SkillData'
WRAPPER = 'Beyond.MemoryPack.Beyond_Gameplay_Core_SkillDataForMemoryPack'
ENUM = 'Beyond.Gameplay.AttackRangeType'
PAIR = 'Beyond.Blackboard+DataPair'
PAIR_LIST = 'System.Collections.Generic.List`1<' + PAIR + '>'
BUFF_INPUT = 'Beyond.Gameplay.Core.BuffInputBase'
LIST_CAPABILITY = 'skill-root-data-pair-list'
NULL_CAPABILITY = 'skill-root-buff-input-base'
DECLARATIONS = (
    ('actionGroupData', 'Beyond.Gameplay.Core.ActionGroupData'),
    ('aiExclusiveFrame', 'int'), ('attackRangeType', ENUM),
    ('blackboard', PAIR_LIST), ('buffInputBase', BUFF_INPUT),
)
BOUNDARY = dict(
    exact='Selected initialized existing nonnull root49/field0 normal continuation, exact ordered named source calls, closed MethodSpec/raw type identities and unchanged Int32/enum32/reference field stores through the admitted last member. DataPair is a value type; its separate closed List formatter proves only four-byte signed -1/0 headers, own null/new-zero/existing-zero paths and complete selected returns. BuffInputBase supplies only its selected canonical reference FF path. No element width is inferred.',
    conditional='The selected native owner authenticates this opened image and inputs at operation entry/exit. Coherent initialized closed contexts, stable disjoint buffered Reader/source/output/frame, existing nonnull root/original, normal Win64 metadata/allocation/context/preparation/provider/cache/collector effects, selected matching formatter callbacks and disabled reference barriers are required. New Lists are typed zeroed allocations with initialized owned empty arrays; existing Lists initially have size zero. Live selection and invocation are unobserved.',
    structuralOnly='Exact stored prefix framing and named field ownership do not establish authored actions running, runtime event delivery or whole root ownership.',
    unresolved=['positive DataPair counts/elements and their wire grammar','positive BuffInputBase values',
        'members after the admitted continuation','cold/refill/malformed/new/null root paths',
        'whole SkillData return/tail/EOF','live formatter/provider/cache/default/override/inflation selection'])


def need(check, expected, actual):
    scalar.need(LABEL, check, expected, actual)


def continuation_program(regions, entry, slots, *, through_member=4):
    """Exact contiguous selected caller bytes after field0's normal barrier.

    Entry must independently join that root prefix. This program has no root
    header or standalone entry-point claim, and stops after the last field's
    store/barrier, before the next source instruction.
    """
    need('supported-last-member', True, type(through_member) is int and through_member in (2, 4))
    names = [row[0] for row in DECLARATIONS[1:through_member+1]]
    need('exact-field-slots', set(names), set(slots))
    occupied = []
    for index, name in enumerate(names, 1):
        slot = slots[name]; width = 4 if index < 3 else 8
        need('bounded-field-slot:'+name, True, type(slot) is int and 16 <= slot < 4096)
        if index < 3:need('scalar-disp8:'+name, True, slot < 128)
        occupied.extend(range(slot, slot+width))
    need('disjoint-field-slots', len(occupied), len(set(occupied)))
    g = BytesPath(regions, entry); events = []; failures = []

    def usage():
        at = g.at; cell = g.relative('488b15')
        return dict(instruction=at, cell=cell)

    def transfer(index, context):
        name = DECLARATIONS[index][0]; before = len(g.seen)
        call = g.at; target = g.relative('e8')
        g.take('4885db'); failures.append(g.relative('0f84'))
        need('owned-null-wrapper-target', True, failures[-1] in g.bytes)
        g.take('488b4b10','4885c9'); failures.append(g.relative('0f84'))
        need('owned-null-original-target', True, failures[-1] in g.bytes)
        slot = slots[name]
        if index < 3:
            g.take('8941'+bytes((slot,)).hex()); barrier = None
        else:
            displacement = slot.to_bytes(4,'little').hex()
            g.take('488981'+displacement,'4881c1'+displacement)
            barrier = g.relative('e8')
        events.append(dict(memberIndex=index, fieldName=name,
            sourceCall=call, sourceTarget=target, typedContext=context,
            fieldOffset=slot, storedBytes=4 if index<3 else 8,
            resultRegister='eax' if index<3 else 'rax',
            referenceBarrierTarget=barrier, selectedBytes=g.seen[before:]))

    for index in range(1,through_member+1):
        try:
            context = None
            if index == 1:g.take('498b1e','488bcf')
            elif index in (2,3):g.take('488bcf');context=usage();g.take('498b1e')
            else:context=usage();g.take('488bcf','498b1e')
            transfer(index,context)
        except ValueError as error:
            at,actual = g.seen[-1] if g.seen else (g.at,'unowned')
            raise ValueError(f'{LABEL}.member{index}:{DECLARATIONS[index][0]}:'
                f'at={at:#x}:actual={actual}:{error}') from error
    if through_member == 4:
        need('same-reference-barrier', events[2]['referenceBarrierTarget'], events[3]['referenceBarrierTarget'])
    need('same-owned-null-failure', 1, len(set(failures)))
    return dict(selectedBytes=g.seen, entry=entry, end=g.at,
        orderedFields=events, lastCompleteMember=through_member,
        nullFailureTarget=failures[0], incomingReader='rdi', incomingRootByref='r14',
        unchangedNamedStores=True, directReaderWrites=0,
        completeReturnProved=False, wholeSkillDataAdmitted=False)


def bind_typed_read(image, usage, *, method_name, argument, kind, reference=False):
    """Own the selected generic method and exact undecorated concrete argument."""
    need('closed-typed-request', (6,'MemoryPack.MemoryPackReader',method_name,[],[argument]),
        tuple(usage.get(k) for k in ('tag','typeName','methodName','classArguments','methodArguments')))
    definition, class_inst, method_inst = usage['methodSpec']
    need('no-reader-class-instantiation', -1, class_inst)
    method = image.metadata.methods[definition]
    need('reader-instance-no-formals', (0,0), (method.flags & 16, method.parameter_count))
    need('reader-generic-method', True, method.generic_container_index >= 0 and method_inst >= 0)
    args = image.instantiations.resolve(method_inst).arguments
    need('closed-reader-arity', 1, len(args))
    scalar.ordinary(image,args[0].type_pointer_va,kind,LABEL+'.argument',reference=reference)
    return dict(methodDefinition=definition, concreteTypeKind=kind,
        argumentType=argument, argumentPointer=args[0].type_pointer_va)


def bind_null_component(pins, event, usage, component, *, base):
    """The canonical FF proof must join this actual nominal parent source."""
    need('null-component-native-inputs', selected_inputs(pins), selected_inputs(component['nativeInputs']))
    need('null-component-type', BUFF_INPUT, component['typeName'])
    need('canonical-null-boundary', (255,1,8,False,False),
        tuple(component.get(k) for k in ('nullMarker','consumedBytes','outputBytes',
            'positiveAdmitted','reservedMarkersAdmitted')))
    need('null-component-source-definition', usage['methodSpec'][0], component['referenceReaderMethodDefinition'])
    need('null-component-actual-source-target', event['sourceTarget']-base, component['referenceReaderTargetRva'])
    return dict(typeName=BUFF_INPUT, nullAdmitted=True, positiveGrammarAdmitted=False,
        marker=255, wireBytes=1, referenceReaderMethodDefinition=component['referenceReaderMethodDefinition'],
        referenceReaderTargetRva=component['referenceReaderTargetRva'])


def bind_list_component(pins, event, usage, component, *, base):
    """Only the closed value-element DataPair list's -1/0 branches supply bytes."""
    need('list-component-native-inputs', selected_inputs(pins), selected_inputs(component['nativeInputs']))
    need('list-element-type', PAIR, component['elementType'])
    need('list-element-value-type', True, component['elementValueType'])
    need('list-actual-request', usage, component['typedRequest'])
    need('list-actual-target', event['sourceTarget']-base, component['callTargetRva'])
    need('list-only-null-empty', 0, component['countLimit'])
    need('list-count-witnesses', [-1,0], sorted({p['countWitness'] for p in component['programs']}))
    need('list-no-element-callbacks', True, all(not p['elementCallbackSites'] for p in component['programs']))
    need('list-no-element-grammar', False, component['elementGrammarAdmitted'])
    return dict(elementType=PAIR,closedListType=PAIR_LIST,collectionCounts=[-1,0],
        elementValueType=True,nullable=True,positiveCountsAdmitted=False,elementCapability=None,elementGrammarAdmitted=False,
        packableReaderMethodDefinition=usage['methodSpec'][0],
        packableReaderTargetRva=event['sourceTarget']-base)


def data_pair_list_program(regions, entry, offsets, symbols, *, count=-1, new=True):
    """Closed DataPair formatter's own complete null/empty selected return.

    Its 32-byte positive callback is deliberately outside this program. No
    element size, source or codec is inferred from this parent proof.
    """
    need('data-pair-count-scope', True, type(count) is int and count in (-1,0) and type(new) is bool)
    g=BytesPath(regions,entry)
    cur,rem,adv,used,total=(bytes((offsets[n],)).hex()for n in
        ('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g.take('4053','55','56','4154','4156','4883ec70','837a'+rem+'04',
        '0f57c0','0f11442450','4d8bf1','4d8be0','0f11442460','488bf2')
    g.branch('0f8c',False)
    g.take('488b46'+cur,'8b28','8b5e'+rem,'83c3fc');g.branch('0f88',False)
    g.take('488346'+cur+'04','8346'+adv+'04','8346'+used+'04','895e'+rem,
        '486346'+used,'488b4e'+total,'482bc8','4863c5','483bc8');g.branch('0f8c',False)
    g.take('4889bc24a0000000','83fdff');g.branch('0f84',count==-1)
    provider_site=None;provider_cell=None
    if count==-1:
        g.take('33ff','498bcc','49893c24');g.call(symbols['barrier']);g.jump('e9')
    else:
        g.take('4c89ac24a8000000','4c89bc24b0000000','49833c2400');g.branch('0f85',not new)
        if new:
            g.take('498b4e20','33d2','488b89c0000000');g.call(symbols['context'])
            g.take('488bc8');g.call(symbols['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False)
            g.take('498b4e20','488b91c0000000','488b4a08','4883792000');g.branch('0f84',False)
            g.take('85ed');g.branch('0f88',False)
            g.take('498b4620','488b88c0000000','488b7908','488b4720','488b88c0000000');g.branch('0f85',False)
            g.take('33d2');g.call(symbols['context']);g.take('83b8e000000000');g.branch('0f84',False)
            g.take('488b4f20','33d2','488b89c0000000');g.call(symbols['context'])
            g.take('488b88b8000000','488b01','488d4b10','48894310');g.call(symbols['barrier'])
            g.take('498bcc','49891c24');g.call(symbols['barrier'])
        else:
            g.take('498b4620','498b1c24','488b88c0000000','488b4110','4883782000');g.branch('75',True,1)
            g.take('498b4620','488bcb','488b90c0000000','488b5210');g.call(symbols['clear'])
            g.take('90');g.jump('e9')
        provider_site=g.at;provider_cell=g.relative('488b0d')
        g.take('83b9e000000000');g.branch('0f84',False)
        g.take('498b4620','488b88c0000000','488b4918');g.call(symbols['provider'])
        g.take('33ff','4c8bf8','85ed');g.branch('7f',False,1)
        g.take('4c8bac24a8000000','4c8bbc24b0000000')
    g.take('488bbc24a0000000','4883c470','415e','415c','5e','5d','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newList=new,
        elementCallbackSites=[],elementGrammarAdmitted=False,elementValueType=True,
        headerBytes=4,outputBytes=8,reader='rsi',output='r12',context='r14',normalReturn=True,
        providerSite=provider_site,providerCell=provider_cell,providerResultUsed=False,
        condition='Matching initialized closed ListFormatter<DataPair> contexts and normal compatible helper/barrier effects; sufficient buffered disjoint input/output/frame. New List allocation is typed and zeroed, with its owned empty array initialized. Existing List initially has size zero; only its actual zero-size Clear path is admitted. Provider returns normally without changing those inputs; its returned formatter is unused. No positive count, element width/codec, callback or runtime provider selection is admitted.')


def data_pair_clear_zero(regions,entry):
    """Actual named closed List<DataPair>.Clear, only when initial size is zero."""
    g=BytesPath(regions,entry)
    # The selected target is independently resolved against the closed named
    # Clear registration below. A differing optimized target requires its own
    # proof and is refused here, rather than treated as an address alias.
    g.take('448b4118','ff411c','c7411800000000','4585c0');g.branch('7e',True,1)
    g.take('c3')
    return dict(selectedBytes=g.seen,initialSize=0,returnedSize=0,sizeOffset=24,
        versionOffset=28,elementArrayTouched=False,normalReturn=True,
        fullPhysicalExtentProved=False)


def derive_data_pair_list(image,pins,typed_request,call_target):
    """A distinct value-element parent component, never the reference-element one."""
    from scripts.game_data.il2cpp.formatter_composition import _vtable
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import modelview_packable_sources
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
    from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;entries=GenericEntries(image)
    bind_typed_read(image,typed_request,method_name='ReadPackable',argument=PAIR_LIST,kind=21,reference=True)
    pointer=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments[0].type_pointer_va
    carrier=ContextSymbols(image).type(pointer);need('data-pair-list-carrier',PAIR_LIST,carrier['name'])
    element,=carrier['classArguments'];raw=bytes.fromhex(element['rawHex'])
    need('data-pair-value-record',(b'\x11\x80',ctx.index.types[PAIR].index),(raw[10:12],int.from_bytes(raw[:8],'little')))
    need('data-pair-value-parent','System.ValueType',ctx.parent(PAIR))
    core=_load('npc_runtime_native.json',pins)['readPackable']
    generic=_load('leveldata_npc_patrol_native.json',pins)['declarations']
    routes=copy.deepcopy(generic['adapters']['referenceRoutes']);routes['wrappers']=[]
    need('data-pair-reference-list-caller-target',base+core['entryRva'],call_target)
    reference=modelview_packable_sources.validate_components(image,pins,core,routes)
    td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1']
    method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
    registration=entries.resolve(method.index,[PAIR],[])
    need('closed-data-pair-list-registration',[raw.hex().upper()],
        [a['raw_type_record_hex'].upper()for a in registration['classInstantiation']['arguments']])
    source=owned(image,registration['pointer']);context=ContextSymbols(image).context(td.index)
    typed=validate_list_formatter_base_context(image,context,entries,fail=need)
    list_td=ctx.index.types['System.Collections.Generic.List`1'];list_context=ContextSymbols(image).context(list_td.index)
    capacity=validate_capacity_constructor_context(image,context,list_context,entries,fail=need)
    _vtable(image,td.index,5,method.index,LABEL)
    need('data-pair-list-formatter-ABI',(False,5,2,'void'),
        (bool(method.flags&16),method.slot,method.parameter_count,ctx.type_name(method.return_type)))
    params=list(md.parameters_for(method))
    reader=image.pe.bytes_at_va(ctx.type_pointer(params[0].type_index),16)
    output=image.pe.bytes_at_va(ctx.type_pointer(params[1].type_index),16)
    need('data-pair-list-reader-byref',(b'\x11\x20',ctx.index.types['MemoryPack.MemoryPackReader'].index),
        (reader[10:12],int.from_bytes(reader[:8],'little')))
    slots={r['relativeSlot']:r for r in context['entries']}
    list_raw=image.pe.bytes_at_va(ctx.type_pointer(slots[0]['index']),16)
    need('data-pair-list-output-byref',(b'\x15\x20',list_raw[:8]),(output[10:12],output[:8]))
    by_offset={int(r['va'],16)-source['pointer']:r for r in source['rows']}
    def call(offset):
        row=by_offset[offset];need('data-pair-direct-helper',b'\xe8',bytes.fromhex(row['bytes'])[:1])
        return control_transfer(row)['target']
    symbols=dict(context=call(158),allocate=call(166),barrier=call(305),provider=call(357))
    # The cold existing-list block is reached by the actual selected branch.
    existing=control_transfer(by_offset[139])['target']
    by_va={int(r['va'],16):r for r in source['rows']}
    clear_row=by_va[existing+61];need('data-pair-existing-clear-call',b'\xe8',bytes.fromhex(clear_row['bytes'])[:1])
    symbols['clear']=control_transfer(clear_row)['target']
    clear_method=slots[2]['methodSpec'][0];clear_registration=entries.resolve(clear_method,[PAIR],[])
    need('data-pair-exact-closed-clear-target',clear_registration['pointer'],symbols['clear'])
    clear_method_row=md.methods[clear_method]
    need('data-pair-clear-ABI',(False,'void',0),
        (bool(clear_method_row.flags&16),ctx.type_name(clear_method_row.return_type),clear_method_row.parameter_count))
    # This actual registered closed Clear has no unwind owner. Hash only its
    # selected raw prefix/branch target, never padding, a guessed full extent,
    # or bytes fabricated across the unselected array-clear tail.
    from scripts.game_data.levelscript_two_routes_native import _window
    clear_entry=symbols['clear'];clear_prefix=image.pe.bytes_at_va(clear_entry,19)
    need('data-pair-clear-selected-JLE',b'\x7e',clear_prefix[17:18])
    clear_return=clear_entry+19+int.from_bytes(clear_prefix[18:19],'little',signed=True)
    clear_regions=[(clear_entry,clear_prefix),(clear_return,image.pe.bytes_at_va(clear_return,1))]
    clear=data_pair_clear_zero(clear_regions,clear_entry)
    clear_windows=[_window(image,clear_entry,clear_entry+19,'actual selected closed Clear raw prefix; no unwind/full extent claim'),
        _window(image,clear_return,clear_return+1,'actual selected zero-size Clear return; unselected tail excluded')]
    offsets=scalar.reader_offsets(image,LABEL);offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    programs=[data_pair_list_program(source['regions'],source['pointer'],offsets,symbols,count=n,new=new)
        for n in(-1,0)for new in(True,False)]
    barrier,barrier_proof,_=_fast_barrier(image,symbols['barrier'])
    provider_program=next(p for p in programs if p['providerSite']is not None)
    provider_usage=derive_typed_usage_context(image,provider_program['providerSite']-base,label=LABEL+'.listProvider')
    need('data-pair-provider-owner',(1,'MemoryPack.MemoryPackFormatterProvider'),(provider_usage['tag'],provider_usage['typeName']))
    # Zero initialization plus the sole stored static SZARRAY reference proves
    # the inline zero-capacity items transfer without a borrowed EntityPtr size.
    static=[f for f in md.fields_for(list_td)if ctx.field_attributes(f.type_index)&16 and not ctx.field_attributes(f.type_index)&64]
    need('data-pair-list-sole-static-array',1,len(static));empty=static[0]
    empty_raw=image.pe.bytes_at_va(ctx.type_pointer(empty.type_index),16)
    need('data-pair-empty-array-kind',b'\x1d\x00',empty_raw[10:12])
    own_list,=next(r for r in list_context['entries']if r['relativeSlot']==0)['type']['classArguments']
    need('data-pair-empty-array-owned-element',own_list['typePointerVa'],int.from_bytes(empty_raw[:8],'little'))
    return dict(nativeInputs=pins,elementType=PAIR,elementValueType=True,typedRequest=typed_request,
        callTargetRva=call_target-base,countLimit=0,programs=programs,elementGrammarAdmitted=False,
        referenceSource=reference,closedCarrier=carrier,registration=registration,context=context,
        typedContext=typed,capacityContext=capacity,listContext=list_context,sourceWindows=source['windows'],
        clearRegistration=clear_registration,clearWindows=clear_windows,clearProgram=clear,
        barrier=barrier,barrierProof=barrier_proof,providerUsage=provider_usage,
        helperRvas={k:v-base for k,v in symbols.items()},emptyArrayTypeHex=empty_raw.hex().upper(),
        positiveCountsAdmitted=False,wholeOwnerAdmitted=False)


def derive(image, pins, *, through_member=4):
    """Fresh same-image proof. The public owner authenticates native bookends.

    Explicit through_member=2 is a separate narrower source proof; a failed
    member3/4 proof is never silently caught or downgraded into that capability.
    """
    from scripts.game_data.memorypack.skill_current_container_sources import derive_skill_prefix
    selected_inputs(pins)
    need('supported-last-member', True, type(through_member) is int and through_member in (2,4))
    prefix = derive_skill_prefix(image,pins)
    base = image.pe.image_base; ctx = NativeReferenceContext(image)
    wrapper = _selected_wrapper(image,WRAPPER)
    need('root-type', ROOT, wrapper.wrapped_type)
    need('root-member-count', 49, len(wrapper.members))
    need('named-root-prefix', list(DECLARATIONS[:through_member+1]),
        [(m.name,m.declared_type) for m in wrapper.members[:through_member+1]])
    method = methods(image,wrapper)['Deserialize']
    primitive_param.reader_abi(image,ctx,method,wrapper)
    source = owned(image,image.method_pointer_va(method))
    need('same-selected-root', prefix['readerMethod'][3], source['pointer']-base)
    end_at, last = prefix['program']['selectedBytes'][-1]
    start = end_at+len(bytes.fromhex(last))
    slots = {}; metadata_fields = []
    root_td = ctx.index.types[ROOT]
    for index,(name,typename) in enumerate(DECLARATIONS[1:through_member+1],1):
        field = ctx.field(ROOT+'::'+name)
        need('owned-field-type:'+name, (ROOT,typename), field[:2]);slots[name]=field[2]
        declared, = [f for f in image.metadata.fields_for(root_td) if image.metadata.string(f.name_index)==name]
        kind = {1:8,2:17,3:21,4:18}[index]
        scalar.ordinary(image,ctx.type_pointer(declared.type_index),kind,LABEL+'.field.'+name,reference=index>=3)
        metadata_fields.append(dict(memberIndex=index,fieldName=name,typeName=typename,
            fieldOffset=field[2],runtimeBytes=4 if index<3 else 8))
    program = continuation_program(source['regions'],start,slots,through_member=through_member)
    need('prefix-member0-disjoint', True, all(
        not set(range(field['fieldOffset'],field['fieldOffset']+field['runtimeBytes']))
        & set(range(prefix['field0'][2],prefix['field0'][2]+8)) for field in metadata_fields))
    record = vector_recorder(image); integer = record(program['orderedFields'][0]['sourceTarget']-base)
    offsets = scalar.reader_offsets(image,LABEL)
    scalar.integer_source(image,integer,offsets,LABEL+'.integer')
    contexts = {}
    for event in program['orderedFields'][1:]:
        at = event['typedContext']['instruction']
        contexts[event['memberIndex']] = derive_typed_usage_context(image,at-base,label=LABEL+'.context')
    enum_usage = contexts[2]
    enum_request = bind_typed_read(image,enum_usage,method_name='ReadUnmanaged',argument=ENUM,kind=17)
    need('actual-enum-Int32-helper', program['orderedFields'][0]['sourceTarget'], program['orderedFields'][1]['sourceTarget'])
    need('actual-enum-type', True, ctx.is_enum(ENUM))
    from scripts.game_data.levelscript_family_regenerate import Build
    enum = Build(image,pins).derive_enum(dict(typeName=ENUM,backingType='System.Int32',width=4))
    proof = dict(rootPrefix=prefix,sourceWindows=source['windows'],program=program,fields=metadata_fields,
        contexts=contexts,integerSource=integer,enumRequest=enum_request,enumBacking=enum)
    reads = [dict(memberIndex=1,fieldName='aiExclusiveFrame',kind='int32',childCapability=None),
             dict(memberIndex=2,fieldName='attackRangeType',kind='enum32',childCapability=None)]
    caps = {}
    if through_member == 4:
        from scripts.game_data.memorypack.skill_action_null_source import derive_reference_null
        pair_event, value_event = program['orderedFields'][2:]
        collection = derive_data_pair_list(image,pins,contexts[3],pair_event['sourceTarget'])
        caps[LIST_CAPABILITY] = bind_list_component(pins,pair_event,contexts[3],collection,base=base)
        null_request = bind_typed_read(image,contexts[4],method_name='ReadValue',argument=BUFF_INPUT,kind=18,reference=True)
        null = derive_reference_null(image,pins,BUFF_INPUT)
        caps[NULL_CAPABILITY] = bind_null_component(pins,value_event,contexts[4],null,base=base)
        barrier, barrier_result, _ = _fast_barrier(image,pair_event['referenceBarrierTarget'])
        need('same-root-reference-barrier', prefix['program']['barrierTarget'], pair_event['referenceBarrierTarget'])
        proof.update(dataPairList=collection,buffInputNull=null,buffInputRequest=null_request,
            referenceBarrier=barrier,referenceBarrierResult=barrier_result)
        reads += [dict(memberIndex=3,fieldName='blackboard',kind='null-empty-value-list',childCapability=LIST_CAPABILITY),
                  dict(memberIndex=4,fieldName='buffInputBase',kind='null-reference',childCapability=NULL_CAPABILITY)]
    caps['SkillDataContinuation'] = dict(memberCount=49,startMemberIndex=1,lastMemberIndex=through_member,
        orderedReads=reads,wholeSkillDataAdmitted=False)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-components',nativeInputs=pins,
        capabilities=caps,proof=proof,lastCompleteMember=through_member,nextMemberIndex=through_member+1,
        completeReturnProved=False,wholeSkillDataAdmitted=False,evidenceBoundary=BOUNDARY)))
