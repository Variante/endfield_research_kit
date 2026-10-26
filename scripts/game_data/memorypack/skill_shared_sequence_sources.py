"""Fresh same-image source joins for the narrow current Skill sequence reader.

Reviewed source owners declare wire kinds. A wrapper name or metadata type
never supplies a width, collection grammar or element admission here.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.memorypack import (
    scalar_param_native as scalar, primitive_param,
)
from scripts.game_data.memorypack.formatter_native import check_formatter_windows
from scripts.game_data.memorypack.skill_timeline_current_sequence import (
    ATOMIC_KINDS, PROFILE_METHODS, validate_program,
)
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext

LABEL = 'skillSharedSequenceSources'

# Explicit semantic owners, not a scan that promotes every similarly shaped
# contract. Each source retains its own wrapper/member/context review.
UNIFORM_OWNERS = frozenset(
    ['skill_custom_root_motion_native.json', 'skill_snap_to_target_with_range_native.json',
     'skill_timeline_tick_interval_native.json']
    + ['skill_timeline_' + name + '_native.json' for name in (
        'check_target_angle', 'command_to_characters', 'gain_breaking_attack_atb',
        'inherit_buff', 'inherit_ccs', 'jump_to_target', 'knock_down',
        'modify_camera_lock_point', 'move_to_direction', 'move_to_location',
        'move_to_slot', 'push_back', 'remove_ai_marker', 'target_postprocessor',
        'tick_interval_v2')])


def selected_inputs(value):
    if set(value) == {'GameAssembly.dll', 'global-metadata.dat', 'UnityPlayer.dll'}:
        return {k: str(v).upper() for k, v in value.items()}
    raise ValueError(LABEL + '.native:explicit-three-inputs-required')


def contract_path(name):
    if not isinstance(name, str) or Path(name).name != name or not name.endswith('.json'):
        raise ValueError(LABEL + '.dependency:unsafe-path')
    return CONTRACTS_DIR / name


def derive_uniform_source(image, pins, source_owner):
    """Reprove an existing reviewed source on this selected image, unchanged."""
    if source_owner not in UNIFORM_OWNERS:
        raise ValueError(LABEL + '.owner:unreviewed=' + str(source_owner))
    from scripts.game_data import skill_timeline_routes_regenerate as uniform
    from scripts.game_data.buff_frontiers_regenerate import _method_row, _read_switch
    path = contract_path(source_owner); fact = json.loads(path.read_bytes())
    scalar.need(LABEL, 'sameSourceBuild', selected_inputs(pins), selected_inputs(fact['nativeInputs']))
    if source_owner == 'skill_custom_root_motion_native.json':
        from scripts.game_data.skill_custom_root_motion_regenerate import regenerate
        actual = regenerate(fact, opener=lambda: (image, pins))
    else:
        fragments = {}
        for method in fact['methods']:
            current = _method_row(image, method); entry = current[3]
            fragments[image.pe.image_base + entry] = [
                (image.pe.image_base + a, b - a)
                for a, b, _ in (r['runtimeTriple'] for r in image.unwind_index.family(entry)['ranges'])
                if a != entry]
        actual = uniform.regenerate(fact, image, pins, switch=_read_switch(image),
            extents=dict(image.mapper.pdata_function_extents(image.pe)),
            fragments=fragments, wrappers=image.memorypack_wrappers)
    validate_claims(fact, actual, label=LABEL + '.source:' + source_owner)
    validate_claims(actual, fact, label=LABEL + '.declaration:' + source_owner)
    fact=normalize_compile_fact(fact)
    # A source program records its child requirements. Child grammar is a
    # separate capability: an old/unproved child cannot invalidate the fresh
    # parent source identity, and cannot acquire admission from that identity.
    # The current operation composes each usable child on this same image.
    dependencies = {}
    for row in fact['dependencies']:
        name = row['path']; dependency = json.loads(contract_path(name).read_bytes())
        dependencies[name] = dict(role=row.get('role'), childGrammarAdmitted=False,
            buildDeclaration='same-selected-build' if dependency.get('nativeInputs') == pins
                else 'independently-current-proof-required')
    return fact, dict(sourceOwner=source_owner, dispatcher=fact['dispatcher'],
        sourceWindows=fact['codeWindows'], nestedContexts=fact['nestedContexts'],
        dependencyValidation=dependencies)


def normalize_compile_fact(fact):
    """Exact baseTick adapter after its original declaration is re-proved.

    Its old reviewed shape omits two keys. The count comes from its
    authenticated CMP immediate and must equal the reviewed ordered reads;
    metadata names never supply widths, tags or a count.
    """
    from scripts.game_data import skill_timeline_routes_regenerate as uniform
    normalized,keys=uniform.normalized_route(fact)
    if keys:
        scalar.need(LABEL,'baseSequenceAdapterOwner',
            'Beyond.MemoryPack.Beyond_Gameplay_Core_TickIntervalAction_DataForMemoryPack',
            fact['dispatcher']['wrapperName'])
        scalar.need(LABEL,'baseSequenceAdapterShape',{'serializedMemberCount','dependencies'},set(keys))
        instruction=fact['memberCountInstruction'];raw=bytes.fromhex(instruction['hex'])
        scalar.need(LABEL,'baseSequenceAuthenticatedByteCompare',True,
            uniform._is_cmp_r8_imm8(dict(bytes=raw))and 0<raw[-1]<250)
        scalar.need(LABEL,'baseSequenceNativeCount',raw[-1],len(fact['orderedSourceReads']))
        normalized['serializedMemberCount']=raw[-1]
    return normalized


def primitive_sources(image, facts):
    """Exact boolean/Int32/Single source framing, separate from Param parents."""
    record = vector_recorder(image); offsets = scalar.reader_offsets(image, LABEL)
    proofs = {}; targets = {}
    for fact in facts:
        for read in fact['orderedSourceReads']:
            kind = read.get('readKind', read.get('kind'))
            cls = ('bool' if kind in ('bool-byte', 'anonymous-nonzero-byte') else
                   'int32' if kind in ('int32', 'scalar32', 'enum32', 'enum-int32') else
                   'float32' if kind in ('float32-bits', 'raw-float32-bits') else None)
            if cls:
                targets.setdefault(cls, set()).add(read['sourceTargetRva'])
    for cls, pointers in targets.items():
        scalar.need(LABEL, 'onePrimitiveTarget:' + cls, 1, len(pointers))
        target, = pointers; source = record(target)
        if cls == 'bool':
            scalar.boolean_source(image, source, offsets, LABEL + '.bool')
        elif cls == 'int32':
            scalar.integer_source(image, source, offsets, LABEL + '.int32')
        else:
            primitive_param.single_source(image, source, offsets)
        proofs[cls] = source
    return dict(readerOffsets=offsets, sourcePrograms=proofs)


def _operation(source_owner, read):
    kind = read.get('readKind', read.get('kind'))
    if (source_owner=='skill_timeline_tick_interval_v2_native.json'
            and read['memberIndex']==5 and kind=='scalar-payload'):
        return kind,'blackboard-int'
    if kind in ATOMIC_KINDS:
        return kind, None
    if kind in PROFILE_METHODS:
        return kind, {'blackboard-double': 'scalar-payload', 'blackboard-scalar': 'scalar-payload',
            'target-settings': 'target-profile', 'TargetSettings': 'target-profile',
            'string': 'byte-payload'}.get(kind, kind)
    if kind == 'string-list' and source_owner == 'skill_timeline_inherit_buff_native.json':
        return kind, 'inherit-buff-string-list'
    if kind == 'sequence-profile':
        return kind, 'SequenceActionData'
    # This owner reviewed two particular collection element types. Generic
    # metadata names alone do not extend this member-index allowlist.
    if source_owner == 'skill_timeline_target_postprocessor_native.json':
        kinds = {4: ('target-profile', 'target-profile'),
                 5: ('direction-profile', 'direction-profile'),
                 6: ('selector-postprocessor-list', 'target-postprocessor-list'),
                 7: ('target-profile', 'target-profile'),
                 8: ('target-profile', 'target-profile'),
                 10: ('selector-validator-list', 'target-validator-list')}
        if read['memberIndex'] in kinds and kind in ('nested-generic', 'list-generic'):
            return kinds[read['memberIndex']]
    raise ValueError(LABEL + '.compile:unreviewed-owner-kind=' + source_owner + ':' + str(kind))


def compile_uniform_program(source_owner, fact, *, wrapper_null_admitted=False):
    """Compile only source-owned exact operations, without a native claim."""
    if source_owner not in UNIFORM_OWNERS:
        raise ValueError(LABEL + '.compile:unreviewed-owner')
    dispatcher = fact['dispatcher']; methods = fact['methods']
    wrapper = dispatcher['wrapperName']
    if not methods or methods[0][1] != wrapper or methods[0][2] != 'Deserialize':
        raise ValueError(LABEL + '.compile:reader-owner')
    # The wrapped name is derived by the native wrapper identity join by the
    # caller and supplied explicitly; do not reconstruct it from spelling.
    wrapped = fact.get('wrappedType')
    if not isinstance(wrapped, str) or not wrapped:
        raise ValueError(LABEL + '.compile:wrapped-type-required')
    reads = []
    for read in fact['orderedSourceReads']:
        kind, capability = _operation(source_owner, read)
        reads.append(dict(memberIndex=read['memberIndex'], fieldName=read['fieldName'],
                          kind=kind, childCapability=capability))
    if type(wrapper_null_admitted) is not bool:
        raise ValueError(LABEL + '.compile:wrapper-null-proof-required')
    row = dict(family='AbilityActionData', tag=dispatcher['unionTag'], wrapperName=wrapper,
        wrappedType=wrapped, memberCount=fact['serializedMemberCount'], sourceOwner=source_owner,
        reads=reads, wrapperNullAdmitted=wrapper_null_admitted)
    validate_program(row)
    return row


BASE_MEMBERS = (('isEnable', 'bool', 'bool-byte'),
    ('priorityLevel', 'Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority', 'enum32'),
    ('priorityOffset', 'int', 'int32'), ('serverActionIndex', 'int', 'int32'))
SEQUENCE_TYPE = 'Beyond.Gameplay.Core.SequenceActionData'
TARGET_TYPE = 'Beyond.Gameplay.Core.TargetSettings'
# These declarations name reviewed source roles. They do not supply native
# widths: the exact selected primitive/body/context joins below do that.
OWN_FAMILIES = {
    'Beyond.MemoryPack.Beyond_Gameplay_Core_IfElseAction_IfElseActionDataForMemoryPack': (
        ('alwaysNext', 'bool', 'bool-byte'), ('conditionAction', SEQUENCE_TYPE, 'sequence-profile'),
        ('failActions', SEQUENCE_TYPE, 'sequence-profile'), ('succeedActions', SEQUENCE_TYPE, 'sequence-profile')),
    'Beyond.MemoryPack.Beyond_Gameplay_Core_JumpToAction_DataForMemoryPack': (
        ('conditionAction', SEQUENCE_TYPE, 'sequence-profile'), ('destFrame', 'int', 'int32')),
    'Beyond.MemoryPack.Beyond_Gameplay_Core_SetAbilityEntityTarget_DataForMemoryPack': (
        ('targetSettings', TARGET_TYPE, 'target-profile'),),
    'Beyond.MemoryPack.Beyond_Gameplay_Core_PlayPerfectDodgeAnim_DataForMemoryPack': (
        ('forceFightIdle', 'bool', 'bool-byte'), ('forceFightIdleDuration', 'float', 'float32-bits')),
}


def _selected_wrapper(image, name):
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    matches = [w for w in derive_from_image(image).values() if w.name == name]
    scalar.need(LABEL, 'oneNamedWrapper:' + name, 1, len(matches))
    return matches[0]


def _inherited_field(ctx, image, owner, name):
    """Resolve the actual declaring owner; never fabricate a derived field."""
    trail=[]
    while owner not in ('object','System.Object',None) and len(trail)<32:
        scalar.need(LABEL,'fieldHierarchyCycle',False,owner in trail)
        trail.append(owner)
        td=ctx.index.types[owner]
        fields=[f for f in image.metadata.fields_for(td)if image.metadata.string(f.name_index)==name]
        if fields:
            scalar.need(LABEL,'oneDeclaredField',1,len(fields))
            return ctx.field(owner+'::'+name)
        owner=ctx.parent(owner)
    raise ValueError(LABEL+'.field:unresolved='+str(name)+':'+str(trail))


def _wrapper_holder(ctx,image,wrapper):
    from scripts.game_data.memorypack.wrapper_members import INSTANCE_FIELD_NAMES
    found=[]
    for name in INSTANCE_FIELD_NAMES:
        try:found.append(_inherited_field(ctx,image,wrapper.name,name))
        except ValueError as error:
            if '.field:unresolved=' not in str(error):raise
    # Generated concrete wrappers may carry a separate typed cache. The actual
    # selected source dereferences +16, so only that metadata-owned holder is
    # relevant; a cache at another offset is not substituted for it.
    selected=[field for field in found if field[2]==16]
    scalar.need(LABEL,'oneActualWrapperHolderAtSourceOffset16',1,len(selected))
    holder=selected[0];allowed=[];owner=wrapper.wrapped_type
    while owner not in ('object','System.Object',None)and len(allowed)<32:
        scalar.need(LABEL,'originalHierarchyCycle',False,owner in allowed)
        allowed.append(owner);owner=ctx.parent(owner)
    scalar.need(LABEL,'wrapperHolderReferenceAt16',True,
        holder[1]in allowed and holder[2]==16 and not ctx.is_value_type(holder[1]))
    return dict(declaringOwner=holder[0],declaredType=holder[1],offset=holder[2],
        concreteOriginalType=wrapper.wrapped_type,originalAncestry=allowed,
        otherDeclaredInstanceFields=[list(field)for field in found if field!=holder])


def _header_helper(image, rows, header, reader, offsets):
    """Join the actual TryReadObjectHeader call/output to its count compare.

    This proves the normal branch only. Wrapper-null admission is a separate
    capability and remains false for this helper form until its entire return
    path is independently authenticated.
    """
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    candidates = []
    for i, row in enumerate(rows):
        if ec.va(row) >= ec.va(header) or control_transfer(row)['kind'] != 'call':
            continue
        if i + 2 < len(rows) and rows[i + 1]['text'] == 'test al, al':
            branch = control_transfer(rows[i + 2])
            if branch['kind'] == 'conditional' and branch['conditionCode'] == 4:
                candidates.append((i, row))
    i, call = ec.one(candidates, lambda _: True, 'shared.header-helper')
    scalar.need(LABEL, 'headerReaderArgument', f'mov rcx, {reader}', ec.last_write(rows, i, 'rcx')['text'])
    pointer = ec.last_write(rows, i, 'rdx')
    scalar.need(LABEL, 'headerOutputAddress', True, pointer is not None)
    match = re.fullmatch(r'lea rdx, (\[rsp\+0x[0-9a-f]+\])', pointer['text'])
    scalar.need(LABEL, 'headerStackOutput', True, match is not None)
    compare=header['text'].replace('cmp byte ','cmp ')
    direct=f'cmp {match[1]}, {ec.raw(header)[-1]:#x}'
    read_back=None
    if compare!=direct:
        from scripts.game_data.il2cpp.initializer_control import _ALIASES
        operand=compare[4:].split(',')[0]
        register=_ALIASES.get(operand,operand)
        header_index=next(n for n,row in enumerate(rows)if ec.va(row)==ec.va(header))
        read_back=ec.last_write(rows,header_index,register)
        load_match=re.fullmatch(r'movzx (\w+), (?:byte )?'+re.escape(match[1]),read_back['text']if read_back else '')
        if load_match is None or _ALIASES.get(load_match[1],load_match[1])!=register:
            raise ValueError(LABEL+'.headerSameByteReadBack:'+str(dict(expectedAddress=match[1],
                comparedRegister=register,actualText=read_back['text']if read_back else None,
                actualBytes=ec.raw(read_back).hex().upper()if read_back else None)))
        scalar.need(LABEL,'headerByteZeroExtendOpcode',b'\x0f\xb6',ec.raw(read_back)[:2])
    else:scalar.need(LABEL,'headerCompareSameOutput',direct,compare)
    target = control_transfer(call)['target']
    record = vector_recorder(image)(target-image.pe.image_base)
    primitive_param.object_header_source(image, record, offsets)
    return dict(call=ec.site(call, image.pe.image_base), source=record,
        outputAddress=match[1],readBack=ec.site(read_back,image.pe.image_base)if read_back else None,
        normalResult=True, wrapperNullAdmitted=False)


def _inline_base_transfers(image, rows, reads, wrapper, path):
    """IfElse's inherited fields are inline stores, not generated setter calls."""
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    ctx = NativeReferenceContext(image); base = image.pe.image_base
    holder=_wrapper_holder(ctx,image,wrapper)
    by = {ec.va(row): i for i, row in enumerate(path)}
    proof = []
    for index, read in enumerate(reads[:4]):
        declaring, field_type, offset = _inherited_field(ctx,image,wrapper.wrapped_type,read['fieldName'])
        scalar.need(LABEL, 'ifElseBaseType', BASE_MEMBERS[index][1], field_type)
        at = base + read['sourceCallsiteRva']; part = path[by[at] + 1:by[at] + 8]
        expected = ['test rsi, rsi', None, 'mov rcx, [rsi+0x10]', 'test rcx, rcx', None,
            f'mov [rcx+{offset:#x}], {"al" if index == 0 else "eax"}']
        scalar.need(LABEL, 'ifElseInlineTransferLength', 6, len(part[:6]))
        for row, text in zip(part[:6], expected, strict=True):
            if text is None:
                edge = control_transfer(row)
                scalar.need(LABEL, 'ifElseInlineNonNullGuard', ('conditional', 4),
                    (edge['kind'], edge.get('conditionCode')))
                tail = {ec.va(r): r for r in rows}
                terminal = tail.get(edge['target'] + 5)
                scalar.need(LABEL, 'ifElseInlineException', True,
                    edge['target'] in tail and control_transfer(tail[edge['target']])['kind'] == 'call'
                    and terminal is not None and ec.raw(terminal) == b'\xcc')
            else:
                scalar.need(LABEL, 'ifElseInlineStore', text, row['text'])
        scalar.need(LABEL,'ifElseInlineStoreWidthAndOffset',
            bytes((0x88 if index==0 else 0x89,0x41,offset)),ec.raw(part[5]))
        receiver = ec.last_write(path, by[at], 'rsi')
        scalar.need(LABEL, 'ifElseInlineWrapperLoad', 'mov rsi, [rdi]', receiver['text'] if receiver else None)
        proof.append(dict(memberIndex=index, originalFieldOffset=offset,declaringOwner=declaring,holder=holder,
            program=[ec.site(row, base) for row in part[:6]]))
    return proof


def derive_own_families(image, pins):
    """Reprove the four current parent-owned families by exact logical identity."""
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    from scripts.game_data import skill_timeline_routes_regenerate as uniform
    from scripts.game_data.buff_frontiers_regenerate import _read_switch
    from scripts.game_data.memorypack.pointer_param import methods
    base = image.pe.image_base; offsets = scalar.reader_offsets(image, LABEL)
    switch = _read_switch(image); clones = ec.clone_facts(image, pins)
    programs, proofs, facts = [], {}, []
    primitive_targets = {}
    for name, own in OWN_FAMILIES.items():
        wrapper = _selected_wrapper(image, name); declared = BASE_MEMBERS + own
        scalar.need(LABEL, 'ownMembers:' + name, [(n,t) for n,t,_ in declared],
            [(m.name,m.declared_type) for m in wrapper.members])
        route = ec.one(switch['entries'], lambda row: row.get('wrapperName') == name, 'shared.current-route')
        scalar.need(LABEL, 'ownRouteWrapperDefinition', wrapper.type_definition, route['typeDefinition'])
        owned_methods = methods(image, wrapper); method = owned_methods['Deserialize']
        entry = image.method_pointer_va(method) - base
        family, windows, rows = ec.family(image, entry)
        simple_rows = [dict(row, va=ec.va(row)) for row in rows]
        reader = uniform.reader_register(simple_rows)
        candidates = [row for row in rows if uniform._is_cmp_r8_imm8(row)
            and ec.raw(row)[-1] == len(declared)]
        header = ec.one(candidates, lambda _: True, 'shared.member-count')
        path, decisions = ec.fast_path(rows, header, reader, offsets)
        selected = uniform.reader_calls([dict(row,va=ec.va(row)) for row in path], reader)
        scalar.need(LABEL, 'ownReadCount:' + name, len(declared), len(selected))
        reads=[]; contexts=[]
        for index, ((field, typename, kind), call) in enumerate(zip(declared, selected, strict=True)):
            target = int(call['text'].split()[1], 16) - base
            read = dict(memberIndex=index, fieldName=field, readKind=kind,
                sourceCallsiteRva=ec.va(call)-base, sourceCallHex=ec.raw(call).hex().upper(), sourceTargetRva=target)
            reads.append(read)
            cls = 'bool' if kind == 'bool-byte' else 'int32' if kind in ('int32','enum32') else 'float32' if kind == 'float32-bits' else None
            if cls:
                primitive_targets.setdefault(cls,set()).add(target)
            else:
                at = next(i for i,row in enumerate(path) if ec.va(row)==ec.va(call))
                load = ec.last_write(path, at, 'rdx')
                scalar.need(LABEL, 'ownTypedLoad', True, load is not None)
                usage = derive_typed_usage_context(image, ec.va(load)-base, label=LABEL)
                scalar.need(LABEL, 'ownTypedRead', ('MemoryPack.MemoryPackReader','ReadValue',[],[typename]),
                    (usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments']))
                # The contract independently proves the actual optimized
                # caller target and its registered equivalent body. Their
                # addresses are deliberately distinct; the caller must use
                # the reviewed actual target, never an invented alias.
                scalar.need(LABEL, 'ownReferenceReadClone', clones['ReadValue']['targetRva'], target)
                contexts.append(dict(memberIndex=index, usage=usage))
        # Each ordinary generated setter receives the unmodified read result.
        inline = name.endswith('IfElseActionDataForMemoryPack')
        inline_proof = _inline_base_transfers(image, rows, reads, wrapper, path) if inline else []
        start = 4 if inline else 0
        uniform.check_read_setter_transfers(simple_rows, reads[start:],
            [image.method_pointer_va(image.metadata.methods[m.method_index]) for m in wrapper.members[start:]],base=base)
        # No other reader calls, indirect calls or unreviewed inline byte loads
        # may hide an extra member in the selected positive return path.
        expected_calls = {base+r['sourceCallsiteRva'] for r in reads} | {
            image.method_pointer_va(image.metadata.methods[m.method_index]) for m in wrapper.members[start:]}
        for row in path:
            flow=control_transfer(row)
            if flow['kind']=='call':
                scalar.need(LABEL,'ownCompleteCallAccounting',True,
                    ec.va(row) in expected_calls or flow['target'] in expected_calls)
            else:
                scalar.need(LABEL,'ownNoIndirectTransfer',True,
                    flow['kind'] not in ('indirectCall','registerCall','indirectJump','registerJump'))
        header_proof = ec.wrapper_header(image,rows,header,reader,offsets) if inline else _header_helper(image,rows,header,reader,offsets)
        fact=dict(orderedSourceReads=reads);facts.append(fact)
        source_owner='skill_timeline_current_sequence_native.json'
        row=dict(family='AbilityActionData',tag=route['tag'],wrapperName=name,wrappedType=wrapper.wrapped_type,
            memberCount=len(declared),sourceOwner=source_owner,wrapperNullAdmitted=inline,
            reads=[dict(memberIndex=i,fieldName=n,kind=k,
                childCapability=None if k in ATOMIC_KINDS else 'SequenceActionData' if t==SEQUENCE_TYPE else 'target-profile')
                for i,(n,t,k) in enumerate(declared)])
        validate_program(row);programs.append(row)
        proofs[name]=dict(wrapperDefinition=wrapper.type_definition,wrappedType=wrapper.wrapped_type,
            currentRoute=route,readerMethod=[method.index,name,'Deserialize',entry],family=family,
            sourceWindows=windows,header=header_proof,orderedSourceReads=reads,nestedContexts=contexts,
            normalProgram=[ec.site(r,base) for r in path],normalConditions=decisions,
            inlineInheritedTransfers=inline_proof,wrapperNullAdmitted=inline)
    scalar.need(LABEL,'oneOwnPrimitiveTargetPerKind',True,all(len(v)==1 for v in primitive_targets.values()))
    primitives=primitive_sources(image,facts)
    return dict(programs=programs,sourceProofs=proofs,primitives=primitives,
        boundary='exact selected buffered normal source calls and named transfers; runtime registration/provider selection remains conditional')


def derive_selector_lists(image, pins):
    """Independently prove EC's null/empty list parents, without elements."""
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    from scripts.game_data.memorypack.skill_cost_data_list_sources import derive_reference_list_component
    fact=json.loads(ec.CONTRACT_PATH.read_bytes())
    scalar.need(LABEL,'selectorRolesSelectedBuild',pins,fact['nativeInputs'])
    # The owner role gate is mandatory: selecting a context from JSON alone
    # does not authenticate the enclosing field or actual caller instruction.
    role=ec.validate_on_image(image,pins)
    clones=ec.clone_facts(image,pins)
    profile=ec.one(fact['proof']['profiles'],lambda p:p['profile']=='member3','shared.selector-profile')
    events=[e for e in profile['events']if e['kind']=='delegated-list']
    declared=[('target-postprocessor-list','Beyond.Gameplay.Core.Selector+PostProcessor+Data'),
              ('target-validator-list','Beyond.Gameplay.Core.Selector+Validator+Data')]
    scalar.need(LABEL,'selectorListCount',len(declared),len(events))
    result={}
    for event,(capability,element)in zip(events,declared,strict=True):
        usage=derive_typed_usage_context(image,event['context']['instructionRva'],label=LABEL)
        at,raw=event['instruction'];b=bytes.fromhex(raw)
        scalar.need(LABEL,'selectorListDirectCall',True,len(b)==5 and b[0]==0xe8)
        target=image.pe.image_base+at+5+int.from_bytes(b[1:],'little',signed=True)
        result[capability]=derive_reference_list_component(image,pins,typed_request=usage,
            call_target=target,element_type=element,count_limit=0)
    return dict(role=role,components=result,referenceReader=clones['ReadValue'],elementGrammarAdmitted=False)


def derive_containers(image,pins):
    """Current independently proved container components (no whole envelope)."""
    from scripts.game_data.memorypack import skill_sequence_array_sources,skill_current_container_sources
    selectors=derive_selector_lists(image,pins)
    return dict(selectorLists=selectors,actionGroup=derive_action_group(image,pins),
        sequence=skill_sequence_array_sources.derive(image,pins,selectors['components']['target-validator-list']),
        timeline=skill_current_container_sources.derive(image,pins))


def _fast_barrier(image,target):
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    from scripts.game_data.memorypack.buffered_reference_wrappers import validate_fast_reference_barrier
    from scripts.game_data.il2cpp.string_source_instructions import decode_string_source_instructions
    from scripts.game_data.levelscript_two_routes_native import _window
    # This collector leaf has no unwind entry. Prove only the actual selected
    # guard/copy/JE/RET bytes; do not invent a function family or a full extent.
    prefix=image.pe.bytes_at_va(target,12)
    scalar.need(LABEL,'barrierBoundedLeafPrefix',True,
        prefix[:2]==b'\x83\x3d'and prefix[6:10]==b'\x00\x4c\x8b\xc1'and prefix[10]==0x74)
    ret=target+12+int.from_bytes(prefix[11:],'little',signed=True)
    scalar.need(LABEL,'barrierBoundedLeafReturn',b'\xc3',image.pe.bytes_at_va(ret,1))
    rows=decode_string_source_instructions(image.mapper,prefix,target)+decode_string_source_instructions(image.mapper,b'\xc3',ret)
    windows=[_window(image,target,target+12,'selected raw-backed no-unwind collector guard/copy/branch'),
             _window(image,ret,ret+1,'actual selected collector return; no whole extent claim')]
    by={ec.va(r):r for r in rows};first=by[target]
    second=by[target+len(ec.raw(first))];third=by[ec.va(second)+len(ec.raw(second))]
    edge=control_transfer(third)
    scalar.need(LABEL,'barrierDisabledGuard',('conditional',4),(edge['kind'],edge.get('conditionCode')))
    last=by[edge['target']]
    proof=dict(codeWindows=windows,program=[ec.site(r,image.pe.image_base)for r in(first,second,third,last)])
    checked=validate_fast_reference_barrier(image,proof,fail=lambda k,e,a:scalar.need(LABEL,k,e,a))
    return proof,checked,rows


def derive_action_group(image,pins):
    """Exact current MC2 parent and two independently typed list containers."""
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    from scripts.game_data.memorypack.pointer_param import methods
    from scripts.game_data.memorypack.skill_cost_data_list_sources import derive_reference_list_component
    from scripts.game_data import skill_timeline_routes_regenerate as uniform
    name='Beyond.MemoryPack.Beyond_Gameplay_Core_ActionGroupDataForMemoryPack'
    wrapper=_selected_wrapper(image,name);declared=[
        ('passiveEventActions','Beyond.Gameplay.Core.AbilityActionMap'),
        ('timelineActions','Beyond.Gameplay.Core.TimelineAction+TimelineActionData')]
    scalar.need(LABEL,'actionGroupMembers',[(n,'System.Collections.Generic.List`1<'+t+'>')for n,t in declared],
        [(m.name,m.declared_type)for m in wrapper.members])
    method=methods(image,wrapper)['Deserialize'];base=image.pe.image_base
    entry=image.method_pointer_va(method)-base;family,windows,rows=ec.family(image,entry)
    header=ec.one(rows,lambda r:uniform._is_cmp_r8_imm8(r)and ec.raw(r)[-1]==2,'shared.action-group-header')
    reader=uniform.reader_register([dict(r,va=ec.va(r))for r in rows])
    offsets=scalar.reader_offsets(image,LABEL);ctx=NativeReferenceContext(image)
    header_proof=ec.wrapper_header(image,rows,header,reader,offsets)
    barrier,barrier_proof,extra=_fast_barrier(image,base+header_proof['referenceBarrierTargetRva'])
    extended=rows+[r for r in extra if ec.va(r)not in {ec.va(x)for x in rows}]
    path,conditions=ec.fast_path(extended,header,reader,offsets)
    reads=uniform.reader_calls([dict(r,va=ec.va(r))for r in path],reader)
    scalar.need(LABEL,'actionGroupReadCount',2,len(reads))
    holder=_wrapper_holder(ctx,image,wrapper);proofs=[];lists={}
    for index,((field,element),call)in enumerate(zip(declared,reads,strict=True)):
        at=next(i for i,r in enumerate(path)if ec.va(r)==call['va'])
        load=ec.last_write(path,at,'rdx')
        usage=derive_typed_usage_context(image,ec.va(load)-base,label=LABEL)
        component=derive_reference_list_component(image,pins,typed_request=usage,
            call_target=int(call['text'].split()[1],16),element_type=element,count_limit=17)
        declaring,field_type,offset=_inherited_field(ctx,image,wrapper.wrapped_type,field)
        scalar.need(LABEL,'actionGroupListFieldType','System.Collections.Generic.List`1<'+element+'>',field_type)
        part=path[at+1:at+8]
        register='rsi'if index==0 else'rdi'
        expected=[f'test {register}, {register}',None,f'mov rcx, [{register}+0x10]',
            'test rcx, rcx',None,f'mov [rcx+{offset:#x}], rax',f'add rcx, {offset:#x}']
        for row,want in zip(part,expected,strict=True):
            if want is None:
                edge=control_transfer(row)
                scalar.need(LABEL,'actionGroupNonNullTransfer',('conditional',4),(edge['kind'],edge.get('conditionCode')))
            else:scalar.need(LABEL,'actionGroupDirectFieldStore',want,row['text'])
        scalar.need(LABEL,'actionGroupFieldStoreWidthAndOffset',bytes((0x48,0x89,0x41,offset)),ec.raw(part[5]))
        receiver=ec.last_write(path,at,register)
        scalar.need(LABEL,'actionGroupSameWrapper',f'mov {register}, [rdi]',receiver['text']if receiver else None)
        lists[field]=component
        proofs.append(dict(memberIndex=index,memberName=field,declaringOwner=declaring,fieldOffset=offset,
            usage=usage,sourceCall=ec.site(call,base),transferProgram=[ec.site(r,base)for r in part]))
    allowed_reads={base+p['sourceCall'][0]for p in proofs}
    for row in path:
        flow=control_transfer(row)
        if flow['kind']=='call':
            scalar.need(LABEL,'actionGroupCallAccounting',True,
                ec.va(row)in allowed_reads or flow['target']==base+barrier_proof['entryRva'])
        elif flow['kind']in('indirectCall','registerCall','indirectJump','registerJump'):
            raise ValueError(LABEL+'.actionGroup:unreviewed-indirect-transfer')
    return dict(wrapperName=name,wrappedType=wrapper.wrapped_type,memberCount=2,
        readerMethod=[method.index,name,'Deserialize',entry],sourceFamily=family,sourceWindows=windows,
        headerProof=header_proof,holder=holder,orderedTransfers=proofs,lists=lists,
        barrierProgram=barrier,normalProgram=[ec.site(r,base)for r in path],
        selectedConditions=conditions,wrapperNullAdmitted=True,
        childGrammarAdmitted=False,wholeActionGroupAdmitted=False,wholeSkillDataAdmitted=False)
