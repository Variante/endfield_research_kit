"""Re-prove LevelScript contracts by shape against one selected native image.

The shared formatter path admits only complete, unchained readers with the
reviewed declaration order, primitive wire operations, named setter targets,
and typed Param contexts. Specialized ranges, composite routes and auxiliary
claims refuse with a JSON path; metadata agreement alone never repins them.
Source receipts remain historical and are checked separately by consumers.
This is stored-layout evidence, not current corpus admission or execution.
"""
from __future__ import annotations

if __name__ == '__main__' and not __package__:
    raise SystemExit('Use python -m scripts.game_data.levelscript_family_regenerate')

import argparse
import copy
import importlib
import json
import struct
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.levelscript_two_routes_native import RouteRefused, _sha256_upper, _window
from scripts.game_data.buff_frontiers_regenerate import _method_row
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.skill_custom_root_motion_regenerate import prove_primitive


def open_selected_build() -> tuple[Any, dict[str, str]]:
    """Check the selected inputs before any metadata or body derivation."""
    gate = check_installed_native_inputs()
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise RouteRefused(f'native-inputs:{gate.status}:{gate.detail}')
    unity = gate.gameassembly.parent / 'UnityPlayer.dll'
    if not unity.is_file():
        raise RouteRefused('native-inputs:UnityPlayer.dll:missing')
    inputs = {name: _sha256_upper(path.read_bytes()) for name, path in (
        ('GameAssembly.dll', gate.gameassembly), ('global-metadata.dat', gate.metadata),
        ('UnityPlayer.dll', unity))}
    return open_native_image(gate.gameassembly, gate.metadata), inputs


def walk(value: Any, path: str = '$'):
    if isinstance(value, dict):
        yield path, value
        for key, item in value.items():
            yield from walk(item, f'{path}.{key}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, f'{path}[{index}]')


def shape(contract: dict[str, Any]) -> str:
    if contract.get('catalogContract'):
        return 'catalog-coupled'
    if 'orderedReads' in contract and 'methods' in contract:
        return 'shared-formatter-window'
    if 'routes' in contract or 'route' in contract:
        return 'getter-route'
    return 'specialized-sub-ranges'


def check_fields(route: dict[str, Any], wrapper: Any) -> None:
    actual = [[m.name, m.declared_type] for m in wrapper.members]
    expected = route.get('nativeDeclaredTypes')
    if expected is None:
        expected = [row[0] for row in route['fields']]
        actual = [row[0] for row in actual]
        if actual != expected:
            actual = [name.lstrip('_') for name in actual]
    elif actual != expected:
        actual = [[name.lstrip('_'), kind] for name, kind in actual]
    if actual != expected:
        first = next(i for i in range(max(len(actual), len(expected)))
                     if i >= len(actual) or i >= len(expected) or actual[i] != expected[i])
        raise RouteRefused(f"reviewed-field-drift:{route['wrapperName']}:member={first}"
                           f':expected={expected[first:first+1]}:actual={actual[first:first+1]}'
                           f':counts={len(expected)}/{len(actual)}')
    if len(wrapper.members) != route['serializedMemberCount']:
        raise RouteRefused(f"member-count:{route['wrapperName']}:expected={route['serializedMemberCount']}:actual={len(wrapper.members)}")
    if wrapper.wrapped_type != route['typeName']:
        raise RouteRefused(f"wrapped-type:{route['wrapperName']}:actual={wrapper.wrapped_type}")


def select_calls(rows: list[dict[str, Any]], count: int, setters: list[int]):
    """Require alternating reader and named setter calls after one count check.

    This recognizes the reviewed RDI reader convention. An unfamiliar register,
    inlined read, extra call, missing setter or undecodable byte refuses.
    """
    headers = [i for i, r in enumerate(rows) if r['text'].startswith('cmp ')
               and r['text'].endswith(f', {count:#x}')
               and bytes.fromhex(r['bytes'])[-1] == count
               and len(bytes.fromhex(r['bytes'])) in (4, 5)]
    if len(headers) != 1:
        raise RouteRefused(f'member-count-instruction:expected=1:actual={len(headers)}')
    reads, writes, setups, pending = [], [], [], []
    reader = False
    for r in rows[headers[0]+1:]:
        text = r['text']
        if text.startswith('db '):
            raise RouteRefused(f"normal-path-undecodable:{r['va']}")
        pending.append(r)
        if text.startswith('mov rcx,'):
            reader = text == 'mov rcx, rdi'
        if text.startswith('call '):
            target = int(text.split()[1], 16)
            member = len(writes)
            if len(reads) == member and reader:
                reads.append(r)
                setups.append(pending)
            elif len(reads) == member + 1 and target == setters[member]:
                writes.append(r)
            else:
                raise RouteRefused(f'called-target-or-read-order:member={member}:actual={target:#x}')
            pending, reader = [], False
            if len(writes) == count:
                return rows[headers[0]], reads, writes, setups
    raise RouteRefused(f'read-setter-count:expected={count}:actual={len(reads)}/{len(writes)}')


def check_read_plan(contract: dict[str, Any]) -> None:
    """Do not silently replace an independently reviewed read or setter plan."""
    fields = contract['route']['fields']
    reads, setters = contract['orderedReads'], contract['setters']
    expected = [(i, row[0], row[1]) for i, row in enumerate(fields)]
    actual = [(r.get('memberIndex'), r.get('fieldName'), r.get('readKind')) for r in reads]
    if actual != expected:
        raise RouteRefused(f'reviewed-read-plan:expected={expected}:actual={actual}')
    if [r.get('memberIndex') for r in setters] != list(range(len(fields))):
        raise RouteRefused('reviewed-setter-plan:member-order-or-count')


class Build:
    def __init__(self, image: Any, inputs: dict[str, str]):
        self.image, self.inputs = image, inputs
        self.wrappers = {w.name: w for w in derive_from_image(image).values()}
        self.switches: dict[str, Any] = {}
        self.body = BodyIndex(image)

    def switch(self, family: str):
        family = {'GetterBase': 'PureGetter'}.get(family, family)
        if family not in self.switches:
            self.switches[family] = read_union_switch(
                self.image, f'Beyond_Gameplay_Actions_{family}ForMemoryPack',
                wrappers={w.type_definition: w for w in self.wrappers.values()})
        return self.switches[family]

    def prove_named_target(self, target: int, owner: str, name: str):
        claim = f'{owner}.{name}'
        if claim in self.body.names_of(target):
            return
        if claim == 'MemoryPack.MemoryPackReader.ReadString':
            self.prove_pooled_string_target(target)
            return
        raise RouteRefused(f'called-target:{claim}:not-resolved-at={target:#x}')

    def prove_pooled_string_target(self, target: int):
        """Admit only the reviewed optimized string reader on its exact build.

        The anonymous clone inlines the Int32 read performed by the named
        extension. Both sentinel returns and their shared pool/index tail join
        are reviewed in the contract. This is value equivalence, not wire
        equivalence with inline ReadString. Never accept a name alone here.
        """
        fact = json.loads((CONTRACTS_DIR / 'memorypack_pooled_string_reader_native.json').read_bytes())
        if (fact.get('schema') != 'endfield.memorypack-pooled-string-reader-native.v1'
                or fact.get('status') != 'exact-current-build'
                or fact.get('claim') != 'MemoryPack.MemoryPackReader.ReadString'):
            raise RouteRefused('pooled-string:unsupported-reviewed-fact')
        if {k:v.upper() for k,v in fact['nativeInputs'].items()} != {k:v.upper() for k,v in self.inputs.items()}:
            raise RouteRefused('pooled-string:native-inputs:mismatched')
        if target != self.image.pe.image_base + fact['targetRva']:
            raise RouteRefused(f'pooled-string:unproven-target={target:#x}')
        try:
            self.image.validate_method_row(fact['equivalentMethod'])
            self.image.check_windows(fact['codeWindows'])
            self.image.check_instruction_windows(fact['instructions'])
        except ValueError as exc:
            raise RouteRefused(f'pooled-string:proof-failed:{exc}') from exc


def regenerate_formatter(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    """Shared complete-reader shape; all other claims require a shape adapter."""
    allowed = {'schema', 'status', 'evidenceBoundary', 'evidenceNote', 'nativeInputs',
               'route', 'dispatcher', 'methods', 'codeWindows', 'memberCountInstruction',
               'readerHelpers', 'orderedReads', 'setters', 'nestedContexts', 'sourceReceipts'}
    extra = sorted(set(contract) - allowed)
    if extra:
        raise RouteRefused(f'auxiliary-reviewed-claims:{extra}:shape-adapter-required')
    check_read_plan(contract)
    image, base = build.image, build.image.pe.image_base
    out = copy.deepcopy(contract)
    route = out['route']
    wrapper = build.wrappers[route['wrapperName']]
    if 'nativeDeclaredTypes' not in route:
        raise RouteRefused('route.nativeDeclaredTypes:missing-reviewed-types')
    check_fields(route, wrapper)
    if len(out['setters']) != len(wrapper.members):
        raise RouteRefused('setters:complete-inherited-chain-required')
    for key in ('inheritedMemberCount', 'ownMemberCount'):
        actual = len(wrapper.inherited_members if key.startswith('inherited') else wrapper.own_members)
        if key in route and route[key] != actual:
            raise RouteRefused(f'{key}:expected={route.get(key)}:actual={actual}')
    switch = build.switch(route['family'])
    entries = [e for e in switch['entries'] if e.get('wrapperName') == wrapper.name]
    if len(entries) != 1:
        raise RouteRefused(f'dispatch-entry:matches={len(entries)}')
    e = entries[0]
    route.update(tag=e['tag'], typeDefinition=e['typeDefinition'], registeredTypeIndex=e['registeredTypeIndex'])
    dispatch = out['dispatcher']
    if 'branchWindow' not in dispatch:
        raise RouteRefused('$.dispatcher.branchWindow:absent:dispatcher-shape-adapter-required')
    target, body, cell = (int(e[k], 16) for k in ('targetVa', 'bodyVa', 'usageCellVa'))
    table = int(switch['tableVa'], 16)
    branch_rows = image.mapper.decode_x64_subset(image.pe.bytes_at_va(body, 128), body, stop_offset=128)
    loads = []
    for r in branch_rows:
        raw = bytes.fromhex(r['bytes']); va = int(r['va'],16)
        if raw[:3] == b'\x48\x8b\x15' and len(raw) == 7 and va+7+struct.unpack_from('<i',raw,3)[0] == cell:
            loads.append(r)
    if len(loads) != 1:
        raise RouteRefused(f'dispatch-type-load:matches={len(loads)}')
    load = loads[0]
    # This prefix boundary is explicitly limited to the observed type load.
    dispatch.update(switchTableRva=table-base, switchEntryCount=switch['entryCount'],
        switchTableSha256=_sha256_upper(image.pe.bytes_at_va(table,switch['entryCount']*4)),
        switchTargetRva=target-base, switchEntryHex=image.pe.bytes_at_va(target,5).hex().upper(),
        bodyRva=body-base, usageCellRva=cell-base, usageRawHex=image.pe.bytes_at_va(cell,8).hex().upper(),
        typeLoadRva=int(load['va'],16)-base, typeLoadHex=bytes.fromhex(load['bytes']).hex().upper(),
        branchWindow=_window(image,body,int(load['va'],16)+7,dispatch['branchWindow']['boundary']))
    out['methods'] = [_method_row(image,m) for m in out['methods']]
    windows=[]
    for old, old_method, method in zip(contract['codeWindows'],contract['methods'],out['methods'],strict=True):
        if old.get('startRva') != old_method[3] or not old['boundary'].startswith('complete '):
            raise RouteRefused(f'reviewed-sub-range:{old["boundary"]}:boundary-proof-required')
        start=base+method[3]
        if build.body.chained_fragments.get(start):
            raise RouteRefused(f'chained-reader:{method[1]}:complete-fragment-adapter-required')
        windows.append(_window(image,start,build.body.extents[start],old['boundary']))
    out['codeWindows']=windows
    w=windows[0]; start=base+w['startRva']
    rows=image.mapper.decode_x64_subset(image.pe.bytes_at_va(start,w['endRva']-w['startRva']),start,
                                        stop_offset=w['endRva']-w['startRva'])
    setter_targets=[image.method_pointer_va(image.metadata.methods[m.method_index]) for m in wrapper.members]
    header, reads, writes, setups=select_calls(rows,len(wrapper.members),setter_targets)
    out['memberCountInstruction']={'rva':int(header['va'],16)-base,'hex':bytes.fromhex(header['bytes']).hex().upper()}
    helpers={}
    contexts=[]
    for index,(read,write,member,setup) in enumerate(zip(reads,writes,wrapper.members,setups,strict=True)):
        kind=route['fields'][index][1]; callee=int(read['text'].split()[1],16)
        if kind in ('bool', 'string') and member.kind != kind:
            raise RouteRefused(f'declared-wire-kind:member={index}:reviewed={kind}:installed={member.kind}')
        if kind == 'int32' and member.kind not in ('scalar32', 'enum'):
            raise RouteRefused(f'declared-wire-kind:member={index}:reviewed=int32:installed={member.kind}')
        if kind in ('bool','int32'):
            if member.kind == 'enum' and (member.underlying_kind != 'scalar32' or member.width != 4):
                raise RouteRefused(f'enum-wire-width:member={index}')
            prove_primitive(image,callee,'bool-byte' if kind=='bool' else 'int32')
        elif kind == 'string':
            build.prove_named_target(callee,'MemoryPack.MemoryPackReader','ReadString')
        else:
            # Context interpretation is delegated to the owning validator;
            # re-derive its bytes through the shared Param carrier reader.
            from scripts.game_data.levelscript_two_routes_native import _derive_context
            old=next((c for c in contract['nestedContexts'] if c['memberIndex']==index),None)
            if old is None or old.get('baseTypeName') != 'Beyond.Gameplay.Actions.Param`1':
                raise RouteRefused(f'nested-context:member={index}:Param-adapter-required')
            if not old.get('readerMethodName'):
                raise RouteRefused(f'nested-context:member={index}:readerMethodName:missing-reviewed-identity')
            if old['elementTypeKind'] not in (2,8,12,17):
                raise RouteRefused(f'nested-element:member={index}:kind={old["elementTypeKind"]}:adapter-required')
            loads=[r for r in setup if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x15']
            if len(loads)!=1:
                raise RouteRefused(f'nested-load:member={index}:matches={len(loads)}')
            load=dict(loads[0],vaInt=int(loads[0]['va'],16),raw=bytes.fromhex(loads[0]['bytes']))
            context=_derive_context(image,index,load,old['elementTypeName'])
            context.update(baseTypeName=old['baseTypeName'],readerMethodName=old['readerMethodName'])
            contexts.append(context)
            build.prove_named_target(callee,'MemoryPack.MemoryPackReader','ReadValue')
        if kind in helpers and helpers[kind]!=callee-base:
            raise RouteRefused(f'wire-helper-drift:{kind}:multiple-targets')
        helpers[kind]=callee-base
        out['orderedReads'][index].update(sourceCallsiteRva=int(read['va'],16)-base,
            sourceCallHex=bytes.fromhex(read['bytes']).hex().upper(),sourceTargetRva=callee-base)
        setter=out['setters'][index]
        name=image.metadata.string(image.metadata.methods[member.method_index].name_index)
        if setter['setterName']!=name or setter['declaringWrapper']!=member.declaring_wrapper:
            raise RouteRefused(f'setter-identity-drift:member={index}')
        setter.update(callsiteRva=int(write['va'],16)-base,callHex=bytes.fromhex(write['bytes']).hex().upper(),
            targetRva=setter_targets[index]-base,methodIndex=member.method_index)
    out['readerHelpers'],out['nestedContexts']=helpers,contexts
    out['nativeInputs']=build.inputs
    out['evidenceNote']='Selected native stored layout re-proved. sourceReceipts are historical, separately hash-gated cursor evidence; no current corpus or runtime claim.'
    return out


def regenerate_getter_route(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    """Adapt nested read/setter-pair routes to the shared body proof.

    Only the declared keys below are handled. Auxiliary enum, pointer and
    inheritance claims still refuse rather than surviving as stale evidence.
    Each route is atomic; the caller publishes only after the owning validator
    accepts every route. No old instruction offset or window length is reused.
    """
    allowed = {'schema', 'status', 'evidenceBoundary', 'evidenceNote', 'nativeInputs',
               'dispatcher', 'route', 'routes'}
    extra = sorted(set(contract) - allowed)
    if extra:
        raise RouteRefused(f'getter-auxiliary-claims:{extra}:proof-required')
    if ('route' in contract) == ('routes' in contract):
        raise RouteRefused('getter-route:expected-one-route-container')
    routes = contract.get('routes', [contract.get('route')])
    out = copy.deepcopy(contract)
    derived = []
    dispatchers = []
    for index, route in enumerate(routes):
        allowed_route = {'family', 'nativeFamily', 'tag', 'typeName', 'wrapperName',
            'typeDefinition', 'registeredTypeIndex', 'switchTargetRva', 'bodyRva',
            'usageCellRva', 'usageRawHex', 'serializedMemberCount', 'memberCount',
            'inheritedMemberCount', 'ownMemberCount', 'fields', 'nativeDeclaredTypes',
            'methods', 'codeWindows', 'formatterTailJump', 'memberCountInstruction',
            'orderedReads', 'readOrder', 'paramContexts', 'sourceReceipts'}
        extra = sorted(set(route) - allowed_route)
        if extra:
            raise RouteRefused(f'route[{index}]:auxiliary-claims={extra}:proof-required')
        reads = route.get('orderedReads', route.get('readOrder'))
        if reads is None or not route.get('methods'):
            raise RouteRefused(f'route[{index}]:paired-read-plan-or-methods:missing')
        if route.get('paramContexts'):
            # These context shapes include ParamOutput and reference children;
            # the shared Param adapter does not prove their full carrier join.
            first = route['paramContexts'][0]
            raise RouteRefused(f'route[{index}]:param-context-carrier-proof-required:member={first.get("memberIndex")}')
        canonical_route = {k: copy.deepcopy(route[k]) for k in (
            'family','tag','typeName','wrapperName','typeDefinition','registeredTypeIndex',
            'inheritedMemberCount','ownMemberCount') if k in route}
        canonical_route['serializedMemberCount'] = route.get('serializedMemberCount', route.get('memberCount'))
        canonical_route['fields'] = [r[:2] for r in route['fields']]
        canonical_route['nativeDeclaredTypes'] = route.get('nativeDeclaredTypes')
        if canonical_route['nativeDeclaredTypes'] is None and all(len(r) == 3 for r in route['fields']):
            canonical_route['nativeDeclaredTypes'] = [[r[0],r[2]] for r in route['fields']]
        if canonical_route['nativeDeclaredTypes'] is None:
            raise RouteRefused(f'route[{index}]:nativeDeclaredTypes:missing-reviewed-types')
        canonical_reads, canonical_setters = [], []
        for member, row in enumerate(reads):
            if row.get('memberIndex') != member:
                raise RouteRefused(f'route[{index}]:reviewed-read-order:member={member}')
            canonical_reads.append({'memberIndex': member, 'fieldName': row['fieldName'],
                                    'readKind': row['readKind']})
            # Authenticate the old setter's identity by name, not its old index.
            field = route['fields'][member][0]
            canonical_setters.append({'memberIndex':member,
                'setterName': f'set___{field}__', 'declaringWrapper':row['declaringWrapper']})
        canonical = {'route':canonical_route, 'dispatcher':copy.deepcopy(contract['dispatcher']),
            'methods':route['methods'], 'codeWindows':route['codeWindows'],
            'memberCountInstruction':route['memberCountInstruction'], 'readerHelpers':{},
            'orderedReads':canonical_reads,'setters':canonical_setters,'nestedContexts':[],
            'sourceReceipts':route.get('sourceReceipts',[])}
        # Table-only dispatchers keep branch evidence on the route. Derive a
        # fresh branch prefix, retaining no old window offsets or hashes.
        canonical['dispatcher'].setdefault('branchWindow', {'boundary':'selected wrapper type-load prefix'})
        proved = regenerate_formatter(canonical,build)
        new = copy.deepcopy(route)
        new.update(tag=proved['route']['tag'],typeDefinition=proved['route']['typeDefinition'],
                   registeredTypeIndex=proved['route']['registeredTypeIndex'],
                   methods=proved['methods'],codeWindows=proved['codeWindows'],
                   memberCountInstruction=proved['memberCountInstruction'])
        branch = proved['dispatcher']
        for key in ('switchTargetRva','bodyRva','usageCellRva','usageRawHex'):
            if key in new: new[key] = branch[key]
        key = 'orderedReads' if 'orderedReads' in route else 'readOrder'
        for old, read, setter in zip(new[key], proved['orderedReads'],proved['setters'],strict=True):
            old.update(readCallRva=read['sourceCallsiteRva'],readCallHex=read['sourceCallHex'],
                readTargetRva=read['sourceTargetRva'],setterCallRva=setter['callsiteRva'],
                setterCallHex=setter['callHex'],setterTargetRva=setter['targetRva'],
                setterMethodIndex=setter['methodIndex'])
        if 'formatterTailJump' in new:
            image,base = build.image,build.image.pe.image_base
            window = proved['codeWindows'][1]
            end = base + window['endRva']
            raw = image.pe.bytes_at_va(end-5,5)
            target = end + struct.unpack_from('<i',raw,1)[0]
            if raw[0] != 0xE9 or target != base + proved['methods'][0][3]:
                raise RouteRefused(f'route[{index}]:formatter-tail-jump:not-direct-source-forward')
            new['formatterTailJump'] = {'instructionRva':end-5-base,
                'instructionHex':raw.hex().upper(),'targetRva':target-base}
        derived.append(new)
        dispatchers.append(branch)
    if not derived:
        raise RouteRefused('getter-route:empty-routes')
    dispatcher = out['dispatcher']
    if set(dispatcher) == {'tableRva','entryCount','tableSha256'}:
        values = {(d['switchTableRva'],d['switchEntryCount'],d['switchTableSha256']) for d in dispatchers}
        if len(values) != 1:
            raise RouteRefused('getter-route:mixed-dispatch-tables')
        table,count,digest = values.pop()
        out['dispatcher'] = {'tableRva':table,'entryCount':count,'tableSha256':digest}
    elif len(derived) == 1:
        out['dispatcher'] = dispatchers[0]
    else:
        raise RouteRefused('getter-route:multi-route-dispatcher-shape')
    if 'routes' in out: out['routes'] = derived
    else: out['route'] = derived[0]
    out['nativeInputs'] = build.inputs
    out['evidenceNote'] = 'Selected stored native route re-proved; source receipts remain historical and separately hash-gated. Runtime effects are unobserved.'
    return out


def regenerate_condition_identity(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    """Re-derive declaration/union identity, never claim a reader-body proof.

    This schema's reviewed branch ends at the next unique switch target.
    Require the original inheritance, complete setter order and member types.
    Param arguments are resolved full names from metadata, not tag proximity.
    No historical offsets, branch lengths, tokens or type indexes are reused.
    """
    allowed = {'schema', 'status', 'nativeInputs', 'evidenceBoundary', 'dispatcher', 'codeWindows', 'rows'}
    if set(contract) - allowed:
        raise RouteRefused(f'condition-auxiliary-claims:{sorted(set(contract)-allowed)}')
    dispatcher_keys = {'typeDefinition','methodToken','methodRva','switchTableRva','maxTag'}
    if set(contract['dispatcher'])-dispatcher_keys:
        raise RouteRefused('condition-dispatcher:auxiliary-claims')
    for window in contract['codeWindows']:
        if (set(window)-{'name','rva','length','sha256','boundary'}
                or window['boundary'] != 'Exact switch target through the next unique switch target.'):
            raise RouteRefused('condition-window:unsupported-reviewed-boundary')
    image, base = build.image, build.image.pe.image_base
    switch = read_union_switch(image, 'Beyond_Gameplay_GameConditionForMemoryPack',
        wrappers={w.type_definition:w for w in build.wrappers.values()})
    if not switch['tableVa']:
        raise RouteRefused('condition-dispatch:table-required')
    out = copy.deepcopy(contract)
    pointer = int(switch['dispatcherVa'],16)
    named = [i for i,m in enumerate(image.metadata.methods)
             if image.method_pointer_va(m) == pointer
             and image.metadata.string(m.name_index) == 'Deserialize'
             and image.type_name(m.declaring_type).startswith('Beyond.MemoryPack.Beyond_Gameplay_GameConditionForMemoryPack+')]
    if len(named) != 1:
        raise RouteRefused(f'condition-dispatch-method:matches={len(named)}')
    method = image.metadata.methods[named[0]]
    out['dispatcher'] = {'typeDefinition':method.declaring_type,
        'methodToken':f'0x{method.token:08x}', 'methodRva':hex(pointer-base),
        'switchTableRva':hex(int(switch['tableVa'],16)-base), 'maxTag':hex(switch['entryCount']-1)}
    windows = []
    for row in out['rows']:
        allowed_row = {'tag','memberCount','wrapperName','generatedDeclaration',
            'generatedSetterOrder','fields','nativeIdentity','conditionType'}
        if set(row)-allowed_row:
            raise RouteRefused(f'condition-row-auxiliary-claims:{sorted(set(row)-allowed_row)}')
        if set(row.get('nativeIdentity',{}))-{'switchTargetRva','usageCellRva','usageRawHex',
                'registeredTypeIndex','typePointerRva','typeDefinition'}:
            raise RouteRefused('condition-identity:auxiliary-claims')
        wrapper = build.wrappers[row['wrapperName']]
        # The reviewed declaration describes this exact server-condition base.
        expected_declaration = ('public class '+wrapper.name.rsplit('.',1)[-1]+' : '
            + (wrapper.parent_name or '').rsplit('.',1)[-1]
            + ', IMemoryPackDeSerializeWrapper, IMemoryPackDeSerializeWrapper<'
            + (wrapper.wrapped_type or '').rsplit('.',1)[-1]+'>, IMemoryPackDeSerializeType')
        if row['generatedDeclaration'] != expected_declaration:
            raise RouteRefused(f'condition-declaration-drift:{wrapper.name}:{expected_declaration}')
        aliases = {'int':'int32', 'Beyond.GEnums.ScopeName':'int32'}
        fields = []
        for member in wrapper.members:
            kind = aliases.get(member.declared_type, member.declared_type)
            prefix = 'Beyond.Gameplay.Actions.Param`1<'
            if kind and kind.startswith(prefix) and kind.endswith('>'):
                child = kind[len(prefix):-1]
                # EntityPtr is the one reviewed nonprimitive argument here.
                if child == 'Beyond.Gameplay.Core.EntityPtr': child = 'EntityPtr'
                if child not in ('bool','string','EntityPtr'):
                    raise RouteRefused(f'condition-param-type:{child}')
                kind = f'Param<{child}>'
            if kind == 'int32' and (member.width != 4 or member.kind not in ('enum','scalar32')):
                raise RouteRefused(f'condition-int32-width:{member.name}:{member.width}')
            fields.append([member.name.lstrip('_'),kind])
        if fields != row['fields'] or len(fields) != row['memberCount']:
            raise RouteRefused(f'condition-field-drift:{wrapper.name}:expected={row["fields"]}:actual={fields}')
        owner = image.metadata.types[wrapper.type_definition]
        setters = [image.metadata.string(image.metadata.methods[i].name_index)[4:]
                   for i in range(owner.method_start,owner.method_start+owner.method_count)
                   if image.metadata.string(image.metadata.methods[i].name_index).startswith('set_')]
        if setters != row['generatedSetterOrder']:
            raise RouteRefused(f'condition-setter-order:{wrapper.name}:expected={row["generatedSetterOrder"]}:actual={setters}')
        if wrapper.wrapped_type.rsplit('.',1)[-1] != row['conditionType']:
            raise RouteRefused(f'condition-type:{wrapper.wrapped_type}')
        entries = [e for e in switch['entries'] if e['wrapperName']==wrapper.name]
        if len(entries)!=1: raise RouteRefused(f'condition-entry:matches={len(entries)}')
        entry = entries[0]
        target,cell = int(entry['targetVa'],16),int(entry['usageCellVa'],16)
        following = sorted(int(e['targetVa'],16) for e in switch['entries'] if int(e['targetVa'],16)>target)
        if not following or following[0]-target>4096:
            raise RouteRefused('condition-branch-boundary:next-unique-target-unproven')
        end=following[0]
        if not target <= int(entry['bodyVa'],16) < end:
            raise RouteRefused('condition-branch-boundary:thunk-outside-window')
        row['tag']=hex(entry['tag'])
        types=int(image.registration['types'],16)
        type_pointer=image.pe.u64_at_va(types+entry['registeredTypeIndex']*8)
        row['nativeIdentity']={'switchTargetRva':hex(target-base),'usageCellRva':hex(cell-base),
            'usageRawHex':image.pe.bytes_at_va(cell,8).hex().upper(),
            'registeredTypeIndex':entry['registeredTypeIndex'],'typePointerRva':hex(type_pointer-base),
            'typeDefinition':entry['typeDefinition']}
        windows.append({'name':f'GameCondition.tag_{row["tag"]}.branch','rva':hex(target-base),
            'length':end-target,'sha256':_sha256_upper(image.pe.bytes_at_va(target,end-target)).lower(),
            'boundary':'Exact switch target through the next unique switch target.'})
    if not windows: raise RouteRefused('condition-rows:empty')
    out['codeWindows']=windows
    out['nativeInputs']={k:v.lower() for k,v in build.inputs.items()}
    out['evidenceBoundary'] = {
        'exact':'Selected GameCondition switch entry, type usage, registered type pointer, wrapper parent, member declarations and setter order.',
        'direct':'The selected dispatcher branch loads the registered wrapper type for the recorded union tag.',
        'conditional':'The stored row applies only after the selected native inputs and branch windows validate and the serialized member count matches.',
        'unresolved':'Complete reader wire operations, condition evaluation, server authority, entity resolution and gameplay outcome are not established by this declaration and dispatch proof.'}
    return out


def regenerate(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    if contract.get('schema') == 'endfield.levelscript-task-condition-native.v1':
        return regenerate_condition_identity(contract, build)
    for path,row in walk(contract):
        if row.get('wrapperName') and row.get('fields') and row.get('serializedMemberCount') is not None:
            wrapper=build.wrappers.get(row['wrapperName'])
            if wrapper is None:
                raise RouteRefused(f'{path}:wrapper-missing:{row["wrapperName"]}')
            check_fields(row,wrapper)
    if shape(contract)=='shared-formatter-window':
        return regenerate_formatter(contract,build)
    if shape(contract)=='getter-route':
        return regenerate_getter_route(contract,build)
    ranges=[f'{p}:{r.get("boundary", "unnamed")}' for p,r in walk(contract)
            if 'startRva' in r and 'endRva' in r]
    raise RouteRefused(f'{shape(contract)}:shape-adapter-required:reviewed-ranges={ranges[:4]}')


def validate_candidate(filename: str, contract: dict[str, Any], build: Build) -> None:
    """Run the owning shape and native validator before publishing any bytes."""
    if contract.get('schema') == 'endfield.levelscript-task-condition-native.v1':
        from scripts.game_data.levelscript_task_condition_native import load_levelscript_task_condition_rows
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / filename
            path.write_text(json.dumps(contract), encoding='utf-8')
            _, audit = load_levelscript_task_condition_rows(
                game_root=build.image.metadata_path.parent.parent.parent, contract_path=path)
            if audit['status'] != 'validated':
                raise RouteRefused(f'consumer-validation:{audit}')
        return
    module=importlib.import_module('scripts.game_data.'+Path(filename).stem)
    shape_reader=getattr(module,'_contract',None)
    validator=getattr(module,'_validate_native',None)
    if shape_reader is None or validator is None:
        raise RouteRefused('consumer-validation:shared _contract/_validate_native adapter unavailable')
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/filename
        path.write_text(json.dumps(contract),encoding='utf-8')
        checked=shape_reader(path)
        validator(build.image,checked)


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--regenerate',action='store_true',required=True)
    parser.add_argument('--write',action='store_true')
    parser.add_argument('--only',action='append',help='Contract basename (repeatable); default all LevelScript contracts')
    parser.add_argument('--report',type=Path,default=Path('reports/game_data/levelscript_regeneration.json'))
    args=parser.parse_args(argv)
    try:
        image,inputs=open_selected_build()
    except RouteRefused as exc:
        parser.exit(1, f'{exc}\n')
    build=Build(image,inputs)
    results=[]
    for path in sorted(CONTRACTS_DIR.glob('levelscript_*.json')):
        if args.only and path.stem not in args.only: continue
        c=json.loads(path.read_bytes())
        # Claims-style and already-current contracts are outside this migration.
        native=c.get('nativeInputs',{})
        old=native.get('GameAssembly.dll',native.get('gameAssemblySha256',''))
        if not native or (not args.only and old and old.upper()==inputs['GameAssembly.dll']): continue
        row={'contract':path.name,'shape':shape(c),'written':False}
        try:
            candidate=regenerate(c,build)
            validate_candidate(path.name,candidate,build)
            row['status']='proved'
            if args.write:
                path.write_bytes((json.dumps(candidate,indent=2,ensure_ascii=False).replace('\n','\r\n')+'\r\n').encode('utf-8'))
                row['written']=True
        except (ValueError,KeyError,IndexError,TypeError,ModuleNotFoundError) as exc:
            row.update(status='refused',reason=f'{type(exc).__name__}:{exc}')
        results.append(row)
    report={'nativeInputs':inputs,'counts':dict(Counter(r['status'] for r in results)),'results':results}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'counts':report['counts'],'written':sum(r['written'] for r in results),'report':str(args.report)}))
    return 1 if any(r['status']=='refused' for r in results) else 0


if __name__=='__main__':
    raise SystemExit(main())
