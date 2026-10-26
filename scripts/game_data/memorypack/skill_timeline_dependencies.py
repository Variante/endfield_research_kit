"""Compose exact timeline child components on the caller's selected image.

Named components must pass their own maintained on-image source proof and the
selected native bookends. Each parent then binds its actual E8 source call,
unclobbered typed RDX request and unchanged EAX/reference setter transfer to the
returned capability. Formatter projections retain their mandatory semantic
owner; frontier8 retains its complete on-image validator. No old catalog or
unknown declaration shape stands in for a named component. Selector lists are
strictly null/empty; positive elements remain unproved.
"""
from __future__ import annotations

import json
import struct

from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.memorypack.formatter_native import check_formatter_windows, is_role_projection

ATOMIC = {
    'memorypack_layer_mask_source_native.json': ('UnityEngine.LayerMask','layer-mask-raw4'),
    'memorypack_gameplay_tag_source_native.json': ('Beyond.Gameplay.Core.GameplayTag','gameplay-tag32'),
}
REFERENCES = {
    'buff_blackboard_int_native.json': 'Beyond.Blackboard+BlackboardInt',
    'buff_blackboard_vector3_native.json': 'Beyond.Blackboard+BlackboardVector3',
}
SELECTORS = 'skill_selector_list_sources_native.json'
FORMATTERS = {'buff_ec_native.json','buff_98_native.json','buff_23_native.json'}
BASE_SEQUENCE = 'skill_timeline_tick_interval_native.json'
FRONTIER = 'buff_frontier8.json'


def _need(label, check, expected, actual):
    if expected != actual:
        raise ValueError(f'{label}.dependency:{check}:expected={str(expected)[:400]}:actual={str(actual)[:400]}')


def _component_owner(name):
    if name == 'memorypack_layer_mask_source_native.json':
        from scripts.game_data.memorypack import buff_layer_mask_native
        return buff_layer_mask_native
    if name == 'memorypack_gameplay_tag_source_native.json':
        from scripts.game_data.memorypack import buff_gameplay_tag_native
        return buff_gameplay_tag_native
    if name == 'buff_blackboard_int_native.json':
        from scripts.game_data.memorypack import buff_blackboard_int_native
        return buff_blackboard_int_native
    if name == 'buff_blackboard_vector3_native.json':
        from scripts.game_data.memorypack import buff_blackboard_vector3_native
        return buff_blackboard_vector3_native
    if name == SELECTORS:
        from scripts.game_data import skill_selector_list_sources_native
        return skill_selector_list_sources_native
    raise ValueError('skillTimelineDependencies.dependency:unsupported-component='+str(name)[:200])


def _contexts(parent):
    if 'nestedContexts' in parent and 'genericContexts' in parent:
        raise ValueError('skillTimelineDependencies.dependency:ambiguous-parent-context-shape')
    rows = parent.get('nestedContexts',parent.get('genericContexts'))
    if not isinstance(rows,list):
        raise ValueError('skillTimelineDependencies.dependency:missing-parent-contexts')
    return rows


def _read(parent, member, label):
    rows = [r for r in parent['orderedSourceReads'] if r['memberIndex']==member]
    _need(label,'unique-parent-read',1,len(rows))
    return rows[0]


def _selected_wrapper(wrappers,name,*,label):
    selected=[w for w in wrappers.values()if w.name==name]
    _need(label,'unique-named-parent-wrapper',1,len(selected))
    return selected[0]


def _selector_reader_route(cap,usage,*,label):
    """Select the separately proved source for the actual typed reader method."""
    _need(label,'selector-reader-owner',(6,'MemoryPack.MemoryPackReader',[]),
          tuple(usage[k]for k in('tag','typeName','classArguments')))
    method=usage['methodName']
    if method=='ReadValue':prefix='referenceReader'
    elif method=='ReadPackable':prefix='packableReader'
    else:raise ValueError(label+'.dependency:unsupported-selector-reader-method='+str(method))
    definition=cap[prefix+'MethodDefinition'];target=cap[prefix+'TargetRva']
    _need(label,'selector-reader-capability',True,
          type(definition)is int and definition>=0 and type(target)is int and 0<target<1<<32)
    _need(label,'selector-reader-method-definition',definition,usage['methodSpec'][0])
    return method,definition,target


def _context_binding(image, parent, context, *, expected_type, method_name,
                     method_definition, target, type_kind, type_definition=None, label):
    """Authenticate the actual typed load-to-call interval, not a type-name match."""
    from scripts.game_data.il2cpp.body_claims import _writes_register
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
    base = image.pe.image_base
    read = _read(parent,context['memberIndex'],label)
    _need(label,'actual-source-target',target,read['sourceTargetRva'])
    raw = image.pe.bytes_at_va(base+read['sourceCallsiteRva'],5)
    _need(label,'source-call-opcode',b'\xe8',raw[:1])
    _need(label,'source-call-bytes',read['sourceCallHex'].replace(' ','').upper(),raw.hex().upper())
    _need(label,'source-call-target',target,read['sourceCallsiteRva']+5+struct.unpack_from('<i',raw,1)[0])
    usage = derive_typed_usage_context(image,context['instructionRva'],label=label+'.componentCaller')
    _need(label,'typed-request',(6,'MemoryPack.MemoryPackReader',method_name,[],[expected_type]),
          tuple(usage[k] for k in ('tag','typeName','methodName','classArguments','methodArguments')))
    _need(label,'same-parent-method-spec',context['methodSpec'],usage['methodSpec'])
    _need(label,'same-parent-context-index',context['methodSpecIndex'],usage['methodSpecIndex'])
    _need(label,'same-parent-context-bytes',context['instructionHex'].replace(' ','').upper(),usage['instructionHex'].upper())
    _need(label,'selected-reader-definition',method_definition,usage['methodSpec'][0])
    spec = usage['methodSpec']
    _need(label,'method-only-instantiation',True,spec[1]==-1 and spec[2]>=0)
    arguments = image.instantiations.resolve(spec[2]).arguments
    _need(label,'closed-reader-arity',1,len(arguments))
    argument = image.pe.bytes_at_va(arguments[0].type_pointer_va,16)
    _need(label,'same-parent-type-record',context['argumentRawHex'].upper(),argument.hex().upper())
    _need(label,'closed-argument-flags',bytes((type_kind,128 if type_kind==17 else 0)),argument[10:12])
    if type_definition is not None:
        _need(label,'closed-argument-definition',type_definition,int.from_bytes(argument[:8],'little'))
    declaration = image.metadata.methods[spec[0]]
    _need(label,'reader-instance-arity',(False,0),(bool(declaration.flags&16),declaration.parameter_count))
    start = context['instructionRva']+len(bytes.fromhex(usage['instructionHex']))
    end = read['sourceCallsiteRva']
    _need(label,'bounded-context-to-call',True,0<=end-start<=96)
    data = image.pe.bytes_at_va(base+start,end-start)
    rows = decode_type_data_initialization_instructions(image.mapper,data,base+start) if data else []
    at = base+start
    for row in rows:
        actual_at = int(row['va'],16)
        _need(label,'context-setup-partition',at,actual_at)
        _need(label,'context-setup-decoded',False,row['text'].startswith('db '))
        _need(label,'context-unclobbered',False,_writes_register(row,'rdx'))
        _need(label,'context-setup-linear','next',control_transfer(row)['kind'])
        at += len(bytes.fromhex(row['bytes']))
    _need(label,'context-setup-end',base+end,at)
    return dict(memberIndex=context['memberIndex'],sourceTargetRva=target,usage=usage)


def _prove_transfer(image,parent,read,*,expected_type,label):
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.skill_timeline_routes_regenerate import check_read_setter_transfers, reader_register
    base = image.pe.image_base
    name = parent['dispatcher']['wrapperName']
    wrapper = _selected_wrapper(derive_from_image(image),name,label=label)
    member, = [m for m in wrapper.members if m.name==read['fieldName']]
    _need(label,'selected-parent-field-type',expected_type,member.declared_type)
    method = image.metadata.methods[member.method_index]
    target = image.method_pointer_va(method)
    row, = [r for r in parent['methods'] if r[1:3]==[name,'Deserialize']]
    _family,_windows,rows = ec.family(image,row[3])
    entry = next(i for i,r in enumerate(rows) if ec.va(r)==base+row[3])
    reader = reader_register(rows[entry:])
    call = next(i for i,r in enumerate(rows) if ec.va(r)==base+read['sourceCallsiteRva'])
    setup = ec.last_write(rows,call,'rcx')
    _need(label,'same-entry-reader',f'mov rcx, {reader}',setup['text'] if setup else None)
    for instruction in rows:
        if ec.va(setup)<ec.va(instruction)<base+read['sourceCallsiteRva']:
            _need(label,'reader-setup-linear','next',control_transfer(instruction)['kind'])
    check_read_setter_transfers([dict(r,va=ec.va(r)) for r in rows],[read],[target],base=base)
    return dict(memberIndex=read['memberIndex'],setterMethodIndex=method.index)


def bind_component(image,parent,name,proof,*,label):
    """Bind only the exact capabilities this dependency is declared to provide."""
    _need(label,'component-status','validated',proof.get('status'))
    _need(label,'component-native-inputs',parent['nativeInputs'],proof.get('nativeInputs'))
    contexts = _contexts(parent)
    joins = []
    if name in ATOMIC or name in REFERENCES:
        atomic = name in ATOMIC
        expected = ATOMIC[name][0] if atomic else REFERENCES[name]
        _need(label,'component-type-name',expected,proof.get('typeName'))
        kind = 17 if atomic else 18
        _need(label,'component-context-kind',kind,proof.get('contextTypeKind'))
        selected = [c for c in contexts if c.get('typeName')==expected]
        _need(label,'component-parent-context-present',True,bool(selected))
        _need(label,'unique-component-parent-members',len(selected),len({c['memberIndex'] for c in selected}))
        if atomic:
            _need(label,'atomic-wire-and-result',(4,'eax'),(proof.get('wireBytes'),proof.get('resultRegister')))
        for context in selected:
            read = _read(parent,context['memberIndex'],label)
            if atomic:_need(label,'atomic-read-kind',ATOMIC[name][1],read.get('readKind',read.get('kind')))
            join = _context_binding(image,parent,context,expected_type=expected,
                method_name='ReadUnmanaged' if atomic else 'ReadValue',
                method_definition=proof['readerMethodDefinition' if atomic else 'referenceReaderMethodDefinition'],
                target=proof['targetRva' if atomic else 'referenceReaderTargetRva'],
                type_kind=kind,type_definition=proof['typeDefinition'],label=label)
            join['transfer'] = _prove_transfer(image,parent,read,expected_type=expected,label=label)
            joins.append(join)
    elif name == SELECTORS:
        capabilities = proof.get('capabilities',{})
        expected = {'target-postprocessor-list':'Beyond.Gameplay.Core.Selector+PostProcessor+Data',
                    'target-validator-list':'Beyond.Gameplay.Core.Selector+Validator+Data'}
        _need(label,'exact-selector-capabilities',set(expected),set(capabilities))
        for key,element in expected.items():
            cap = capabilities[key]
            closed = 'System.Collections.Generic.List`1<'+element+'>'
            _need(label,'closed-selector-list',(element,closed),(cap.get('elementType'),cap.get('closedListType')))
            _need(label,'selector-count-boundary',([-1,0],True,False,None,False),
                (cap.get('collectionCounts'),cap.get('nullable'),cap.get('positiveCountsAdmitted'),
                 cap.get('elementCapability'),cap.get('elementGrammarAdmitted')))
            selected = [c for c in contexts if c.get('elementTypeName')==element]
            _need(label,'unique-selector-context',1,len(selected))
            context = selected[0]
            read = _read(parent,context['memberIndex'],label)
            _need(label,'selector-parent-read-kind','list-generic',read.get('readKind',read.get('kind')))
            usage=derive_typed_usage_context(image,context['instructionRva'],label=label+'.selectorReader')
            method,definition,target=_selector_reader_route(cap,usage,label=label)
            join = _context_binding(image,parent,context,expected_type=closed,method_name=method,
                method_definition=definition,target=target,
                type_kind=21,label=label)
            join['transfer'] = _prove_transfer(image,parent,read,expected_type=closed,label=label)
            joins.append(join)
    else:raise ValueError(label+'.dependency:unsupported-component='+name)
    return dict(status='validated',component=name,joins=joins,capability=proof)


def validate_dependency(image,parent,dependency,*,label):
    """Validate one allowlisted declaration and its exact current parent join."""
    name = dependency.get('path')
    inputs = parent['nativeInputs']
    if name in ATOMIC or name in REFERENCES or name == SELECTORS:
        owner = _component_owner(name)
        _need(label,'component-owner-path',name,owner.CONTRACT_PATH.name)
        fact,_ = read_reviewed_contract(owner.CONTRACT_PATH,schema=owner.SCHEMA,status='exact-current-build',label=label+'.'+name)
        _need(label,'selected-component-inputs',inputs,fact['nativeInputs'])
        _publication_gate(image,inputs)
        proof = owner.validate_on_image(image,inputs)
        result = bind_component(image,parent,name,proof,label=label)
        _publication_gate(image,inputs)
        return result
    if name not in FORMATTERS | {FRONTIER,BASE_SEQUENCE}:
        raise ValueError(label+'.dependency:unsupported-contract='+str(name)[:200])
    fact = json.loads((CONTRACTS_DIR/name).read_bytes())
    if 'nativeInputs' in fact:_need(label,'selected-dependency-inputs',inputs,fact['nativeInputs'])
    _publication_gate(image,inputs)
    if name == FRONTIER:
        from scripts.game_data.buff_frontiers_native import validate_on_image
        _need(label,'frontier-schema-status',('endfield.buff-frontier8-native-contract.v1','exact-current-build'),(fact.get('schema'),fact.get('status')))
        validate_on_image(image,fact)
    else:
        if name == BASE_SEQUENCE:
            _need(label,'sequence-schema-status',('endfield.skill-timeline-tick-interval-native-contract.v1','exact-current-build'),(fact.get('schema'),fact.get('status')))
        else:
            _need(label,'mandatory-role-projection',True,is_role_projection(fact))
        _need(label,'owned-code-windows-present',True,bool(fact.get('codeWindows')))
        check_formatter_windows(image,fact,label=label+'.'+name)
        image.check_windows(fact.get('dataWindows',[]),gate='data-window',label=label+'.'+name)
    _publication_gate(image,inputs)
    return dict(status='validated',component=name)


def validate_dependencies(image,parent,*,label):
    rows = parent.get('dependencies',[])
    names = [r.get('path') for r in rows]
    _need(label,'unique-dependency-names',len(names),len(set(names)))
    return {row['path']:validate_dependency(image,parent,row,label=label) for row in rows}


def read_null_empty_selector_list(reader):
    """Consume only the two collection headers admitted by the component."""
    from scripts.game_data.memorypack.buff_actions import Unsupported
    at = reader.pos
    count, = struct.unpack('<i',reader.take(4,'count-i32'))
    if count not in (-1,0):
        raise Unsupported(reader.source,at,[-1,0],count,'selector-list-count-unproved')
    return count
