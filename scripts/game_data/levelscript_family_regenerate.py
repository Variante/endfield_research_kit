"""Re-prove LevelScript contracts by shape against one selected native image.

The shared formatter path requires complete owned reader windows and the
reviewed declaration order, primitive wire operations, named setter targets,
and typed Param contexts. The ordered read/setter sequence must be in the
primary body and its immediately contiguous owned fragments. Specialized
ranges and unhandled auxiliary claims refuse;
metadata agreement alone never repins them.
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
import re
import struct
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.audit_build_impact import native_pins
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp import protocol
from scripts.game_data.il2cpp.integer_tag_dispatch import decode_memory_immediate_compare
from scripts.game_data.il2cpp.reference_field_programs import preserved_argument,instance_getter,inlined_getter_setter
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.levelscript_two_routes_native import RouteRefused, _sha256_upper, _window
from scripts.game_data.buff_frontiers_regenerate import _method_row, _type_definition
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.skill_custom_root_motion_regenerate import prove_primitive

_PRIMITIVE_SCHEMAS={f'endfield.levelscript-{kind}-param-native.v1':kind for kind in ('bool','int','string','float','uint','ulong','vector2','vector3')}


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
    else:
        expected = [[name, protocol.canonical_type_name(kind)] for name, kind in expected]
        actual = [[name, protocol.canonical_type_name(kind)] for name, kind in actual]
        if actual != expected:
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


def select_calls(rows: list[dict[str, Any]], count: int, setters: list[int], inline_members=(), *, reader_register=None,getter_targets=None,prefix_count=None):
    """Require ordered reads and reviewed setter transfers after one count check.

    The saved entry argument carries the reader. Scalar inlining needs a separate
    typed ownership/program proof; other extra calls or missing transfers refuse.
    """
    limit = count if prefix_count is None else prefix_count
    if type(limit) is not int or not 1 <= limit <= count or len(setters) < limit:
        raise RouteRefused('read-setter-prefix:invalid-bound')
    def byte_count(row):
        raw = bytes.fromhex(row['bytes'])
        try:
            decoded = decode_memory_immediate_compare(raw, 0, int(row['va'], 16)) if raw else None
        except (ValueError, IndexError):
            return False
        if decoded:
            fact, end = decoded
            return (end == len(raw) and fact['memoryImmediateComparisonOperation']['bits'] == 8
                    and fact['memoryImmediateComparisonOperation']['immediateValue'] == count
                    and fact['text'].replace('cmp byte ', 'cmp ') == row['text'].replace('cmp byte ', 'cmp '))
        if raw and 0x40 <= raw[0] <= 0x4f:
            raw = raw[1:]
        return (len(raw) == 3 and raw[0] == 0x80 and raw[1] & 0xf8 == 0xf8 and raw[2] == count
                and re.fullmatch(r'cmp [a-z0-9]+, '+f'{count:#x}', row['text']) is not None)
    headers = [i for i, row in enumerate(rows) if byte_count(row)]
    if len(headers) != 1:
        raise RouteRefused(f'member-count-instruction:expected=1:actual={len(headers)}')
    prove_argument=reader_register is None
    if prove_argument:reader_register=preserved_argument(rows[:headers[0]+1],'rcx')
    reads, writes, setups, pending = [], [], [], []
    getter_targets=getter_targets or {};getter_calls=set()
    def finish():
        if prove_argument and preserved_argument(rows[:rows.index(reads[-1])],'rcx')!=reader_register:
            raise RouteRefused('reader-argument:normal-path-clobber')
        return rows[headers[0]],reads,writes,setups
    reader = False
    for r in rows[headers[0]+1:]:
        text = r['text']
        if text.startswith('db '):
            raise RouteRefused(f"normal-path-undecodable:{r['va']}")
        pending.append(r)
        member=len(writes)
        direct=member in inline_members and re.fullmatch(r'mov \[(?:rcx|r8)\+0x[0-9a-f]+\], (?:al|eax|rax)',text)
        backed=member in getter_calls and re.fullmatch(r'mov \[rax\+0x[0-9a-f]+\], (?:[er](?:bx|bp|si|di)|bl|bpl|sil|dil|r1[2-5][db]?)',text)
        if len(reads)==member+1 and (direct or backed):
            writes.append(r);pending=[];reader=False
            if len(writes)==limit:return finish()
            continue
        if text.startswith('mov rcx,'):
            reader = text == 'mov rcx, '+reader_register
        if text.startswith('call '):
            target = int(text.split()[1], 16)
            member = len(writes)
            if len(reads) == member and reader:
                reads.append(r)
                setups.append(pending)
            elif len(reads) == member + 1 and target == setters[member]:
                writes.append(r)
            elif len(reads)==member+1 and target==getter_targets.get(member) and member not in getter_calls:
                getter_calls.add(member)
            else:
                raise RouteRefused(f'called-target-or-read-order:member={member}:actual={target:#x}')
            pending, reader = [], False
            if len(writes) == limit:
                return finish()
    raise RouteRefused(f'read-setter-count:expected={limit}:actual={len(reads)}/{len(writes)}')


def check_read_plan(contract: dict[str, Any]) -> None:
    """Do not silently replace an independently reviewed read or setter plan."""
    fields = contract['route']['fields']
    reads = contract['orderedReads']
    expected = [(i, row[0], row[1]) for i, row in enumerate(fields)]
    actual = [(r.get('memberIndex'), r.get('fieldName'), r.get('readKind')) for r in reads]
    if actual != expected:
        first=next(i for i in range(max(len(actual),len(expected))) if actual[i:i+1]!=expected[i:i+1])
        raise RouteRefused(f'reviewed-read-plan:member={first}:expected={expected[first:first+1]}:actual={actual[first:first+1]}:counts={len(expected)}/{len(actual)}')
    setters = contract.get('setters')
    if setters is not None and [r.get('memberIndex') for r in setters] != list(range(len(fields))):
        raise RouteRefused('reviewed-setter-plan:member-order-or-count')


def contiguous_reader_end(windows: list[dict[str, Any]]) -> int:
    """Extend only through immediately adjacent owned source fragments.

    The final window is the separately authenticated formatter. Remote cold
    fragments stay hashed ownership evidence and are never spliced into order.
    """
    end=windows[0]['endRva']
    for window in windows[1:-1]:
        if window['startRva'] != end:
            break
        end=window['endRva']
    return end


def generic_child_context(image: Any, context: dict[str, Any], base_name: str):
    """Authenticate a one-argument nested generic carrier from selected bytes."""
    from scripts.game_data.il2cpp.context import generic_type_carrier
    if context['elementTypeKind'] != 21:
        raise RouteRefused('nested-list:unsupported-carrier')
    raw = bytes.fromhex(context['elementRawHex'])
    carrier_raw = image.pe.bytes_at_va(struct.unpack_from('<Q',raw)[0],32)
    base_raw = image.pe.bytes_at_va(struct.unpack_from('<Q',carrier_raw)[0],16)
    argument = context['classInstantiation']['arguments'][0]
    carrier = generic_type_carrier(raw,carrier_raw,base_raw,type_pointer=argument['type_pointer_va'],
                                  type_count=len(image.metadata.types),source='levelscript-regenerate')
    if image.type_name(carrier['baseDefinitionIndex']) != base_name:
        raise RouteRefused('nested-list:base-drift')
    child = image.instantiations.resolve_pointer(carrier['classInstantiationPointerVa'])
    if len(child.arguments) != 1:
        raise RouteRefused('nested-list:element-arity')
    element = bytes.fromhex(child.arguments[0].raw_type_record_hex)
    return carrier,child,element


def derive_list_context(image: Any, context: dict[str, Any], reviewed: dict[str, Any]) -> dict[str, Any]:
    """Prove the reviewed List<T> carrier and its single value-type child."""
    if reviewed['listBaseTypeName'] != 'System.Collections.Generic.List`1':
        raise RouteRefused('nested-list:unsupported-carrier')
    carrier,child,element=generic_child_context(image,context,reviewed['listBaseTypeName'])
    expected_kind=reviewed.get('listElementTypeKind',17)
    if expected_kind not in (*range(2,15),17):
        raise RouteRefused('nested-list:unsupported-element-kind')
    actual_name=(image.type_name(struct.unpack_from('<Q',element)[0]) if element[10]==17
                 else protocol.RUNTIME_PRIMITIVE_TYPE_NAMES.get(element[10],''))
    if element[10] != expected_kind or protocol.canonical_type_name(actual_name) != protocol.canonical_type_name(reviewed['listElementTypeName']):
        raise RouteRefused('nested-list:element-drift')
    row = child.as_dict(); row['arguments'] = list(row['arguments'])
    context.update(listCarrier=carrier,listInstantiation=row,listBaseTypeName=reviewed['listBaseTypeName'],
                   listElementTypeName=reviewed['listElementTypeName'])
    for key,value in (('listElementRawHex',element.hex().upper()),
                      ('listElementTypeDefinition',struct.unpack_from('<Q',element)[0] if element[10]==17 else None)):
        if key in reviewed:context[key]=value
    return {'classCarrier':carrier,'classInstantiation':row,'elementRawHex':element.hex().upper(),
            'elementTypeKind':element[10],'elementTypeDefinition':struct.unpack_from('<Q',element)[0] if element[10]==17 else None,
            'elementTypeName':reviewed['listElementTypeName']}


def derive_string_list_context(image: Any, context: dict[str, Any], reviewed: dict[str, Any]) -> None:
    nested=reviewed['nestedGeneric']
    if (set(nested)!={'carrier','classInstantiation','innerTypeName'} or nested['innerTypeName']!='System.String'
            or reviewed['elementTypeName']!='System.Collections.Generic.List`1'):
        raise RouteRefused('nested-string-list:unsupported-reviewed-shape')
    carrier,child,element=generic_child_context(image,context,reviewed['elementTypeName'])
    if element[10]!=14:
        raise RouteRefused('nested-string-list:element-kind-drift')
    row=child.as_dict();row['arguments']=list(row['arguments'])
    context['elementPointerVa']=struct.unpack_from('<Q',bytes.fromhex(context['elementRawHex']))[0]
    context['nestedGeneric']={'carrier':carrier,'classInstantiation':row,'innerTypeName':'System.String'}


def derive_class_read_context(image, member, setup, expected):
    """Prove a ReadValue<T> usage whose single argument is the named class."""
    from scripts.game_data.il2cpp.context import method_spec_usage_index,method_spec_record
    loads=[r for r in setup if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x15']
    if len(loads)!=1:raise RouteRefused('class-read:one-context-load-required')
    load=loads[0];raw=bytes.fromhex(load['bytes']);base=image.pe.image_base;va=int(load['va'],16)
    cell=va+7+struct.unpack_from('<i',raw,3)[0];usage=image.pe.bytes_at_va(cell,8)
    index=method_spec_usage_index(usage,image.registration['methodSpecsCount'],source='class-read',offset=cell)
    address=int(image.registration['methodSpecs'],16)+index*12
    spec=method_spec_record(image.pe.bytes_at_va(address,12),len(image.metadata.methods),image.registration['genericInstsCount'],source='class-read',offset=address)
    method=image.metadata.methods[spec[0]];instance=image.instantiations.resolve(spec[2])
    if (image.type_name(method.declaring_type)!='MemoryPack.MemoryPackReader'
        or image.metadata.string(method.name_index)!='ReadValue' or len(instance.arguments)!=1):
        raise RouteRefused('class-read:reader-or-arity')
    argument=instance.arguments[0];raw_type=bytes.fromhex(argument.raw_type_record_hex);definition=struct.unpack_from('<Q',raw_type)[0]
    if raw_type[10]!=18 or image.type_name(definition)!=expected:
        raise RouteRefused('class-read:typed-argument')
    return dict(memberIndex=member,instructionRva=va-base,instructionHex=raw.hex().upper(),cellRva=cell-base,
        usageRawHex=usage.hex().upper(),methodSpecIndex=index,methodSpec=list(spec),argumentRawHex=raw_type.hex().upper(),
        typeKind=18,typeDefinition=definition,typeName=expected)


class Build:
    def __init__(self, image: Any, inputs: dict[str, str]):
        self.image, self.inputs = image, inputs
        self.wrappers = {w.name: w for w in derive_from_image(image).values()}
        self.switches: dict[str, Any] = {}
        self.body = image.body_index

    def derive_enum(self, reviewed: dict[str, Any]) -> dict[str, Any]:
        """Re-read enum backing and literal IDs; refuse a changed named domain."""
        allowed={'memberIndex','typeName','typeDefinition','backingType','underlyingType','wireName','width','members'}
        if set(reviewed)-allowed:
            raise RouteRefused(f'enum:unsupported-claims:{sorted(set(reviewed)-allowed)}')
        name=reviewed['typeName']
        matches=[t for t in self.image.metadata.types if self.image.metadata.type_full_name(t)==name]
        if len(matches)!=1:
            raise RouteRefused(f'enum:{name}:definition-matches={len(matches)}')
        owner=matches[0]
        fields=[f for f in self.image.metadata.fields_for(owner) if self.image.metadata.string(f.name_index)=='value__']
        if len(fields)!=1:
            raise RouteRefused(f'enum:{name}:value-field-matches={len(fields)}')
        ptr=self.image.pe.u64_at_va(int(self.image.registration['types'],16)+fields[0].type_index*8)
        backing=protocol.runtime_type_name(self.image.pe,self.image.metadata,ptr)
        for key in ('backingType','underlyingType'):
            if key in reviewed and protocol.canonical_type_name(reviewed[key])!=protocol.canonical_type_name(backing):
                raise RouteRefused(f'enum:{name}:{key}:expected={reviewed[key]}:actual={backing}')
        members=None
        if 'members' in reviewed:
            members=protocol.native_enum_members(self.image.metadata,self.body.enum_defaults,self.image.pe,self.image.registration,name)
            expected=[(m['id'],m['name']) for m in reviewed['members']]
            actual=[(m['id'],m['name']) for m in members]
            if actual!=expected:
                raise RouteRefused(f'enum:{name}:members:expected={expected[:32]}:actual={actual[:32]}')
        width={'System.Boolean':1,'System.Byte':1,'System.SByte':1,'System.Int16':2,'System.UInt16':2,
               'System.Int32':4,'System.UInt32':4,'System.Int64':8,'System.UInt64':8}.get(protocol.canonical_type_name(backing))
        if 'width' in reviewed and reviewed['width']!=width:
            raise RouteRefused(f'enum:{name}:width:expected={reviewed["width"]}:actual={width}')
        out=copy.deepcopy(reviewed)
        if 'typeDefinition' in out:out['typeDefinition']=owner.index
        if members is not None:out['members']=[{k:fresh[k] for k in old} for old,fresh in zip(reviewed['members'],members,strict=True)]
        return out

    def switch(self, family: str):
        family = {'GetterBase': 'PureGetter'}.get(family, family)
        if family not in self.switches:
            namespace='Beyond_Gameplay_' if family=='GameCondition' else 'Beyond_Gameplay_Actions_'
            self.switches[family] = read_union_switch(
                self.image, f'{namespace}{family}ForMemoryPack',
                wrappers={w.type_definition: w for w in self.wrappers.values()})
        return self.switches[family]

    def prove_named_target(self, target: int, owner: str, name: str, *, result_abi="reference"):
        claim = f'{owner}.{name}'
        if claim in self.body.names_of(target):
            return
        if claim == 'MemoryPack.MemoryPackReader.ReadString':
            self.prove_pooled_string_target(target)
            return
        if owner == 'MemoryPack.MemoryPackReader' and name in ('ReadValue', 'ReadArray', 'ReadPackable'):
            self.prove_reader_clone_target(target, claim, result_abi=result_abi)
            return
        raise RouteRefused(f'called-target:{claim}:not-resolved-at={target:#x}')

    def prove_reader_clone_target(self, target: int, claim: str, *, result_abi="reference"):
        """Authenticate one reviewed optimized reader, never a similar body.

        The explicit result ABI prevents reference-return and hidden-output facts
        from crossing. The caller still proves its typed context and result use.
        The fact records the registered generic equivalent and the complete
        code/dataflow proof (including inlined helper and dispatch joins).
        Its exact build, claim, target, registration identity, complete pdata
        coverage and instruction bytes must all agree before admission.
        """
        path = CONTRACTS_DIR / 'memorypack_reader_clones_native.json'
        if not path.is_file():
            raise RouteRefused('reader-clone:reviewed-fact:missing')
        fact = json.loads(path.read_bytes())
        if (fact.get('schema') != 'endfield.memorypack-reader-clones-native.v3'
                or fact.get('status') != 'exact-current-build'):
            raise RouteRefused('reader-clone:unsupported-reviewed-fact')
        if {k:v.upper() for k,v in fact['nativeInputs'].items()} != {k:v.upper() for k,v in self.inputs.items()}:
            raise RouteRefused('reader-clone:native-inputs:mismatched')
        base = self.image.pe.image_base
        if result_abi not in ('reference','hidden-output-16','hidden-output-40'):
            raise RouteRefused('reader-clone:unsupported-result-ABI')
        matches = [c for c in fact['clones'] if c['claim'] == claim and base+c['targetRva'] == target
                   and c.get('resultAbi') == result_abi]
        if len(matches) != 1:
            raise RouteRefused(f'reader-clone:unproven-target:{claim}:target={target:#x}')
        c = matches[0]
        try:
            method = c['equivalentMethod']
            if '.'.join(method[1:3]) != claim:
                raise ValueError('equivalent-method-claim')
            self.image.validate_method_row(method)
            equivalent = c['equivalentBody']
            entries = self.body.names_by_pointer.get(base+equivalent['rva'], [])
            if not any(row.get('methodIndex') == method[0]
                       and row.get('type') == method[1] and row.get('method') == method[2]
                       and all(row.get(key) == equivalent[key] for key in
                               ('methodSpecIndex', 'genericMethodPointerSlot')) for row in entries):
                raise ValueError('equivalent-generic-registration')
            roots = c['bodyRoots']
            if c['targetRva'] not in roots or equivalent['rva'] not in roots:
                raise ValueError('missing-proof-root')
            expected = set()
            for root in roots:
                start = base+root
                expected.add((root, self.body.extents[start]-base))
                expected.update((va-base, va+size-base) for va,size in self.body.chained_fragments.get(start, ()))
            if expected != {(w['startRva'], w['endRva']) for w in c['codeWindows']} or not c['instructions']:
                raise ValueError('incomplete-proof-windows')
            self.image.check_windows(c['codeWindows'])
            self.image.check_instruction_windows(c['instructions'])
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise RouteRefused(f'reader-clone:proof-failed:{exc}') from exc

    def prove_pooled_string_target(self, target: int):
        """Admit only the reviewed optimized string reader on its exact build.

        The anonymous clone inlines the Int32 read performed by the named
        extension. Both sentinel returns and their shared pool/index tail join
        are reviewed in the contract. This is value equivalence, not wire
        equivalence with inline ReadString. Never accept a name alone here.
        """
        from scripts.game_data.memorypack.pooled_source_helper import validate_on_image
        try:
            validate_on_image(self.image,target,self.inputs)
        except ValueError as exc:
            raise RouteRefused(f'pooled-string:proof-failed:{exc}') from exc


def regenerate_formatter(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    """Shared complete-reader shape; all other claims require a shape adapter."""
    allowed = {'schema', 'status', 'evidenceBoundary', 'evidenceNote', 'nativeInputs',
               'route', 'dispatcher', 'methods', 'codeWindows', 'memberCountInstruction',
               'readerHelpers', 'orderedReads', 'setters', 'nestedContexts', 'sourceReceipts'}
    allowed.update(('enumTypes','enumUnderlying','enumAlias','enumAliases','enumWidths','ownSetters','sourceLedger','inlineSetterMembers','getterSetterMembers','instanceAssignment'))
    extra = sorted(set(contract) - allowed)
    if extra:
        raise RouteRefused(f'auxiliary-reviewed-claims:{extra}:shape-adapter-required')
    check_read_plan(contract)
    image, base = build.image, build.image.pe.image_base
    out = copy.deepcopy(contract)
    route = out['route']
    wrapper = build.wrappers[route['wrapperName']]
    # Older reviewed shapes state wire types plus exact typed Param contexts
    # instead of a nativeDeclaredTypes column. check_fields still proves the
    # names/count/wrapped type, each read below proves its wire operation and
    # carrier, and publication requires the owner's independent native type map.
    check_fields(route, wrapper)
    own_only = 'setters' not in out
    if own_only:
        if 'ownSetters' not in out:
            raise RouteRefused('setters:missing-reviewed-plan')
        # Names come from the reviewed ordered fields, authenticated against
        # the generated wrapper and every actual setter call below.
        out['setters'] = [{'memberIndex':i,'declaringWrapper':m.declaring_wrapper,
                           'setterName':f'set___{m.name}__'} for i,m in enumerate(wrapper.members)]
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
    dispatch.update(switchTableRva=table-base, switchEntryCount=switch['entryCount'],
        switchTableSha256=_sha256_upper(image.pe.bytes_at_va(table,switch['entryCount']*4)),
        switchTargetRva=target-base, bodyRva=body-base, usageCellRva=cell-base,
        usageRawHex=image.pe.bytes_at_va(cell,8).hex().upper())
    if 'branchWindow' in dispatch:
        # This prefix boundary is limited to the observed type load.
        dispatch.update(switchEntryHex=image.pe.bytes_at_va(target,5).hex().upper(),
            typeLoadRva=int(load['va'],16)-base,typeLoadHex=bytes.fromhex(load['bytes']).hex().upper(),
            branchWindow=_window(image,body,int(load['va'],16)+7,dispatch['branchWindow']['boundary']))
    elif target != body or set(dispatch)-{'switchTableRva','switchEntryCount','switchTableSha256',
                                         'switchTargetRva','bodyRva','usageCellRva','usageRawHex'}:
        raise RouteRefused('dispatcher:direct-entry-shape-or-target-drift')
    out['methods'] = [_method_row(image,m) for m in out['methods']]
    windows=[]
    if len(out['methods']) != 2 or len(contract['codeWindows']) < 2:
        raise RouteRefused('method-windows:expected-reader-and-formatter')
    for position, (old, old_method, method) in enumerate(zip(
            (contract['codeWindows'][0],contract['codeWindows'][-1]),contract['methods'],out['methods'],strict=True)):
        boundary=old.get('boundary')
        reviewed_complete={'complete-pdata-function','generated source reader entry','generated source reader main fragment','hot-pdata-function','reader-entry','forwarding-formatter'}
        if old.get('startRva') != old_method[3] or (boundary is not None and not (boundary.startswith('complete ') or boundary in reviewed_complete)):
            raise RouteRefused(f'reviewed-sub-range:{boundary}:boundary-proof-required')
        start=base+method[3]
        window=_window(image,start,build.body.extents[start],boundary or 'complete method body')
        if boundary is None:
            del window['boundary']
        windows.append(window)
        fragments=build.body.chained_fragments.get(start,())
        if position == 1 and fragments:
            raise RouteRefused('chained-formatter:adapter-required')
        if position == 0:
            for pointer,length in fragments:
                windows.append(_window(image,pointer,pointer+length,'complete owned source reader fragment'))
    out['codeWindows']=windows
    w=windows[0]; start=base+w['startRva']; size=contiguous_reader_end(windows)-w['startRva']
    rows=decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(start,size),start)
    setter_targets=[image.method_pointer_va(image.metadata.methods[m.method_index]) for m in wrapper.members]
    assignment=out.get('instanceAssignment');assignment_method=None
    if assignment is not None:
        if (set(assignment)!={'memberIndex','declaredSetterMethodIndex','declaredSetterName','assignmentMethodIndex','assignmentName',
            'declaringWrapper','callsiteRva','callHex','targetRva'} or assignment['memberIndex']!=len(wrapper.members)-1
            or assignment['declaringWrapper']!=wrapper.name or assignment['assignmentName']!='set___instance'
            or assignment['declaredSetterName']!=f'set___{wrapper.members[-1].name}__'):
            raise RouteRefused('instance-assignment:reviewed-identity')
        assignment_method=_method_row(image,[0,wrapper.name,assignment['assignmentName'],0])
        method=image.metadata.methods[assignment_method[0]];parameters=image.metadata.parameters_for(method)
        if len(parameters)!=1 or protocol.runtime_type_name(image.pe,image.metadata,image.pe.u64_at_va(
            int(image.registration['types'],16)+parameters[0].type_index*8))!=route['typeName']:
            raise RouteRefused('instance-assignment:parameter-type')
        setter_targets[-1]=base+assignment_method[3]
    inline=contract.get('inlineSetterMembers',[])
    if inline!=sorted(set(inline)) or any(type(i) is not int or not 0<=i<len(wrapper.members) for i in inline):
        raise RouteRefused('inline-setters:reviewed-member-order')
    backed=contract.get('getterSetterMembers',[])
    if backed!=sorted(set(backed)) or set(backed)&set(inline) or any(type(i) is not int or not 0<=i<len(wrapper.members) for i in backed):
        raise RouteRefused('getter-setters:reviewed-member-order')
    if assignment is not None and (own_only or assignment['memberIndex'] in (*inline,*backed)):
        raise RouteRefused('instance-assignment:incompatible-setter-profile')
    getter_targets={i:instance_getter(image,build.wrappers,wrapper.members[i])[1] for i in backed}
    header, reads, writes, setups=select_calls(rows,len(wrapper.members),setter_targets,inline,getter_targets=getter_targets)
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
        elif assignment is not None and index==assignment['memberIndex']:
            if kind!=route['typeName'].rsplit('.',1)[-1] or member.declared_type!=route['typeName']:
                raise RouteRefused('instance-assignment:read-type')
            context=derive_class_read_context(image,index,setup,route['typeName'])
            old=contract['nestedContexts']
            if (len(old)!=1 or set(old[0])!=set(context) or old[0]['memberIndex']!=index
                or old[0]['typeName']!=route['typeName'] or old[0]['typeKind']!=18):
                raise RouteRefused('class-read:unhandled-context-claims')
            contexts.append(context);build.prove_named_target(callee,'MemoryPack.MemoryPackReader','ReadValue')
        else:
            # Context interpretation is delegated to the owning validator;
            # re-derive its bytes through the shared Param carrier reader.
            from scripts.game_data.levelscript_two_routes_native import _derive_context
            old=next((c for c in contract['nestedContexts'] if c['memberIndex']==index),None)
            expected_base=('Beyond.Gameplay.Actions.ParamOutput`1' if kind.startswith('ParamOutput<')
                           else 'Beyond.Gameplay.Actions.Param`1' if kind.startswith('Param<') else None)
            if old is None or expected_base is None or old.get('baseTypeName',expected_base)!=expected_base:
                raise RouteRefused(f'nested-context:member={index}:Param-adapter-required')
            reader_name='ReadArray' if kind.endswith('[]') else 'ReadValue'
            if old.get('readerMethodName',reader_name)!=reader_name:
                raise RouteRefused(f'nested-context:member={index}:reviewed-reader-wire-kind-drift')
            if old.get('elementTypeKind') is not None and old['elementTypeKind'] not in (*range(2,15),17,18,21,28):
                raise RouteRefused(f'nested-element:member={index}:kind={old["elementTypeKind"]}:adapter-required')
            loads=[r for r in setup if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x15']
            if len(loads)!=1:
                raise RouteRefused(f'nested-load:member={index}:matches={len(loads)}')
            load=dict(loads[0],vaInt=int(loads[0]['va'],16),raw=bytes.fromhex(loads[0]['bytes']))
            expected_element=old['elementTypeName']
            if 'nestedGeneric' in old:
                if kind!='Param<List<string>>' or expected_element!='System.Collections.Generic.List`1':
                    raise RouteRefused(f'nested-string-list:member={index}:wire-type-drift')
                expected_element+='<' + old['nestedGeneric']['innerTypeName'] + '>'
            context=_derive_context(image,index,load,protocol.canonical_type_name(expected_element),expected_base=expected_base)
            # Keep the reviewed consumer spelling after proving the canonical
            # metadata type, and retain all independent kind/carrier checks.
            if old.get('elementTypeKind',context['elementTypeKind']) != context['elementTypeKind']:
                raise RouteRefused(f'nested-element:member={index}:kind-drift')
            context['elementTypeName']=old['elementTypeName']
            if 'baseTypeName' in old:context['baseTypeName']=old['baseTypeName']
            if 'readerMethodName' in old:context['readerMethodName']=reader_name
            if 'nestedGeneric' in old:derive_string_list_context(image,context,old)
            list_keys={'listCarrier','listInstantiation','listBaseTypeName','listElementTypeName'}
            if set(old)&list_keys:
                if not list_keys <= set(old):
                    raise RouteRefused(f'nested-list:member={index}:incomplete-reviewed-claims')
                derive_list_context(image,context,old)
            if 'nestedList' in old:
                nested=old['nestedList']
                if nested is None:
                    if context['elementTypeKind']==21:
                        raise RouteRefused(f'nested-list:member={index}:unexpected-generic-element')
                    context['nestedList']=None
                else:
                    temporary=copy.deepcopy(context)
                    derived=derive_list_context(image,temporary,{'listBaseTypeName':'System.Collections.Generic.List`1',
                        'listElementTypeName':nested['elementTypeName'],'listElementTypeKind':nested['elementTypeKind']})
                    if 'carrier' in nested:derived['carrier']=derived.pop('classCarrier')
                    if 'instantiation' in nested:derived['instantiation']=derived.pop('classInstantiation')
                    if set(nested)!=set(derived):
                        raise RouteRefused(f'nested-list:member={index}:unsupported-reviewed-shape')
                    context['nestedList']=derived
            if set(old)-set(context):
                raise RouteRefused(f'nested-context:member={index}:unhandled-claims={sorted(set(old)-set(context))}')
            contexts.append(context)
            method=image.metadata.methods[context['methodSpec'][0]]
            if (image.type_name(method.declaring_type) != 'MemoryPack.MemoryPackReader'
                    or image.metadata.string(method.name_index) != reader_name):
                raise RouteRefused(f'nested-context:member={index}:reader-method-drift')
            build.prove_named_target(callee,'MemoryPack.MemoryPackReader',reader_name)
        if kind in helpers and helpers[kind]!=callee-base:
            raise RouteRefused(f'wire-helper-drift:{kind}:multiple-targets')
        helpers[kind]=callee-base
        out['orderedReads'][index].update(sourceCallsiteRva=int(read['va'],16)-base,
            sourceCallHex=bytes.fromhex(read['bytes']).hex().upper(),sourceTargetRva=callee-base)
        setter=out['setters'][index]
        name=image.metadata.string(image.metadata.methods[member.method_index].name_index)
        if setter['setterName']!=name or setter['declaringWrapper']!=member.declaring_wrapper:
            raise RouteRefused(f'setter-identity-drift:member={index}')
        if index in backed:
            setter=inlined_getter_setter(image,build.body,build.wrappers,member,rows,read,write)
            setter['memberIndex']=index;out['setters'][index]=setter
        elif index in inline:
            from scripts.game_data.il2cpp.reference_field_programs import inlined_base_setter
            setter=inlined_base_setter(image,build.body,build.wrappers,member,rows,read,write)
            setter['memberIndex']=index;out['setters'][index]=setter
        else:
            setter.update(callsiteRva=int(write['va'],16)-base,callHex=bytes.fromhex(write['bytes']).hex().upper(),
                targetRva=setter_targets[index]-base,methodIndex=member.method_index)
            if assignment is not None and index==assignment['memberIndex']:
                assignment.update(declaredSetterMethodIndex=member.method_index,assignmentMethodIndex=assignment_method[0],
                    **{k:setter[k] for k in ('callsiteRva','callHex','targetRva')})
                setter.update(methodIndex=assignment_method[0],setterName=assignment['assignmentName'])
    out['readerHelpers'],out['nestedContexts']=helpers,contexts
    for key in ('enumTypes','enumUnderlying','enumAlias','enumAliases'):
        if key in contract:
            value=contract[key]
            out[key]=[build.derive_enum(e) for e in value] if isinstance(value,list) else build.derive_enum(value)
    if 'enumWidths' in contract:
        for name,width in contract['enumWidths'].items():
            build.derive_enum({'typeName':name,'width':width})
    if 'ownSetters' in contract:
        expected=contract['ownSetters']
        derived=[s for s in out['setters'] if s['memberIndex']>=len(wrapper.inherited_members)]
        if [(s['memberIndex'],s['setterName'],s['declaringWrapper']) for s in expected]!=[(s['memberIndex'],s['setterName'],s['declaringWrapper']) for s in derived]:
            raise RouteRefused('own-setters:reviewed-identity-or-order-drift')
        out['ownSetters']=copy.deepcopy(derived)
    if own_only:
        del out['setters']
    if 'sourceLedger' in contract:
        ledger=contract['sourceLedger']
        if (set(ledger)-{'summary','ledger','family','inputSetSha256','ledgerSha256'} or not {'summary','ledger'}<=set(ledger)
                or ledger.get('family','LevelScriptData')!='LevelScriptData'
                or any(key in ledger and not re.fullmatch(r'[0-9A-Fa-f]{64}',ledger[key]) for key in ('inputSetSha256','ledgerSha256'))):
            raise RouteRefused('source-ledger:unsupported-reviewed-shape')
    out['nativeInputs']=build.inputs
    out['evidenceNote']='Selected native stored layout re-proved. sourceReceipts are historical, separately hash-gated cursor evidence; no current corpus or runtime claim.'
    return out


def param_template(old: dict[str, Any], field: list[str]) -> dict[str, Any]:
    out=copy.deepcopy(old)
    if 'buffPtrRawHex' in out:
        out.update(listBaseTypeName='System.Collections.Generic.List`1',listElementTypeName=out.pop('buffPtrTypeName'),
            listElementTypeDefinition=out.pop('buffPtrTypeDefinition'),listElementRawHex=out.pop('buffPtrRawHex'))
    reader='MemoryPack.MemoryPackReader.'+('ReadArray' if field[1].endswith('[]') else 'ReadValue')
    if out.pop('fieldName',field[0])!=field[0] or out.pop('methodName',reader)!=reader:
        raise RouteRefused('param-context:reviewed-field-or-reader-drift')
    if out.pop('readerMethod',reader.rsplit('.',1))!=reader.rsplit('.',1):
        raise RouteRefused('param-context:reviewed-reader-method-drift')
    child=out.pop('child',None)
    if child is not None:
        out.update(elementRawHex=child['rawHex'],elementTypeKind=child['kind'],
            elementTypeName=child['typeName'],elementTypeDefinition=child.get('typeDefinition'))
        if child['kind']==21:
            inner=child.get('elementTypeName',protocol.canonical_type_name(protocol.RUNTIME_PRIMITIVE_TYPE_NAMES.get(child['elementKind'],'')))
            nominal='System.Collections.Generic.List`1'
            if child['typeName'].startswith(nominal+'<') and child['typeName'].endswith('>'):
                declared=child['typeName'][len(nominal)+1:-1]
                if inner and protocol.canonical_type_name(inner)!=protocol.canonical_type_name(declared):
                    raise RouteRefused('param-context:nested-list-element-name-drift')
                inner=declared
            elif child['typeName']!=nominal:
                raise RouteRefused('param-context:nested-list-type-required')
            if not inner:raise RouteRefused('param-context:nested-list-element-required')
            out['elementTypeName']=nominal+f'<{inner}>'
            out['nestedList']={'classCarrier':child['carrier'],'classInstantiation':child['classInstantiation'],
                'elementRawHex':child['elementRawHex'],'elementTypeKind':child['elementKind'],
                'elementTypeName':inner,'elementTypeDefinition':child.get('elementTypeDefinition')}
        allowed={'rawHex','kind','typeName','typeDefinition','carrier','classInstantiation','elementRawHex','elementKind','elementTypeName','elementTypeDefinition'}
        if set(child)-allowed:raise RouteRefused(f'param-context:unhandled-child-claims={sorted(set(child)-allowed)}')
    elif out.get('elementTypeKind')==21 and '<' not in out['elementTypeName'] and out.get('nestedList'):
        out['elementTypeName']+='<'+out['nestedList']['elementTypeName']+'>'
    if out.get('nestedList') and 'elementTypeKind' not in out['nestedList']:
        nested=out['nestedList']
        nested['elementTypeKind']=bytes.fromhex(nested['elementRawHex'])[10]
    return out


def param_projection(old: dict[str, Any], fresh: dict[str, Any]) -> dict[str, Any]:
    out=copy.deepcopy(fresh)
    if 'buffPtrRawHex' in old:
        out.update(buffPtrRawHex=out['listElementRawHex'],buffPtrTypeDefinition=out['listElementTypeDefinition'],
                   buffPtrTypeName=out['listElementTypeName'])
    if 'child' in old:
        child={'rawHex':out['elementRawHex'],'kind':out['elementTypeKind'],'typeName':old['child']['typeName']}
        if 'typeDefinition' in old['child']:child['typeDefinition']=struct.unpack_from('<Q',bytes.fromhex(out['elementRawHex']))[0]
        if child['kind']==21:
            nested=out['nestedList']
            child.update(carrier=nested['classCarrier'],classInstantiation=nested['classInstantiation'],
                elementRawHex=nested['elementRawHex'],elementKind=nested['elementTypeKind'],
                elementTypeName=nested['elementTypeName'],elementTypeDefinition=nested['elementTypeDefinition'])
        out['child']={k:child[k] for k in old['child']}
    if out['elementTypeKind']==18 and old.get('elementTypeDefinition') is not None:
        out['elementTypeDefinition']=struct.unpack_from('<Q',bytes.fromhex(out['elementRawHex']))[0]
    if 'elementTypeName' in old:out['elementTypeName']=old['elementTypeName']
    if out['elementTypeKind']==21 and old.get('elementTypeDefinition') is not None:
        nested=out['nestedList'];out['elementTypeDefinition']=nested.get('classCarrier',nested.get('carrier'))['baseDefinitionIndex']
    if old.get('nestedList'):
        out['nestedList']={k:out['nestedList'][k] for k in old['nestedList']}
    for key in ('fieldName','methodName','readerMethod'):
        if key in old:out[key]=old[key]
    if set(old)-set(out):raise RouteRefused(f'param-context:unhandled-claims={sorted(set(old)-set(out))}')
    return {key:out[key] for key in old}


def forwarding_jump(image: Any, window: dict[str, Any], target: int) -> dict[str, Any]:
    start=image.pe.image_base+window['startRva'];size=window['endRva']-window['startRva']
    rows=image.mapper.decode_x64_subset(image.pe.bytes_at_va(start,size),start,stop_offset=size)
    matches=[]
    for row in rows:
        raw=bytes.fromhex(row['bytes']);rva=int(row['va'],16)-image.pe.image_base
        if len(raw)==5 and raw[0]==0xE9 and rva+5+struct.unpack_from('<i',raw,1)[0]==target:
            matches.append({'instructionRva':rva,'instructionHex':raw.hex().upper(),'targetRva':target})
    if len(matches)!=1:raise RouteRefused(f'formatter-forwarding-jump:matches={len(matches)}')
    return matches[0]


def project_dispatcher(old: dict[str, Any], fresh: dict[str, Any]) -> dict[str, Any]:
    aliases={'tableRva':'switchTableRva','entryCount':'switchEntryCount','tableSha256':'switchTableSha256'}
    if set(old)-set(fresh)-set(aliases):raise RouteRefused('dispatcher:unhandled-reviewed-claims')
    return {k:({key:fresh[k][key] for key in value} if k=='branchWindow' else fresh[aliases.get(k,k)]) for k,value in old.items()}


def regenerate_single_param_routes(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    """Re-prove grouped routes with one own setter and one typed Param context."""
    allowed={'schema','status','evidenceBoundary','evidenceNote','nativeInputs','switch','readerHelpers','sourceLedger','routes'}
    if set(contract)-allowed:raise RouteRefused('single-param-routes:unhandled-root-claims')
    out=copy.deepcopy(contract);helpers={};switch=None
    for route in out['routes']:
        nested={'dispatcher','methods','codeWindows','memberCountInstruction','orderedReads','ownSetter','nestedContext','sourceReceipts'}
        identity={'family','tag','typeName','wrapperName','typeDefinition','registeredTypeIndex',
                  'serializedMemberCount','inheritedMemberCount','fields','nativeDeclaredTypes'}
        if set(route)!=nested|identity:raise RouteRefused('single-param-routes:unhandled-route-claims')
        if set(route['ownSetter'])!={'memberIndex','callsiteRva','callHex','targetRva','declaringWrapper','methodIndex','setterName'}:
            raise RouteRefused('single-param-routes:unhandled-setter-claims')
        if any(set(row)!={'memberIndex','fieldName','readKind','sourceCallsiteRva','sourceCallHex','sourceTargetRva'} for row in route['orderedReads']):
            raise RouteRefused('single-param-routes:unhandled-read-claims')
        if route['ownSetter'].get('memberIndex')!=len(route['fields'])-1 or route['nestedContext'].get('memberIndex')!=len(route['fields'])-1:
            raise RouteRefused('single-param-routes:reviewed-own-member')
        canonical={key:copy.deepcopy(contract[key]) for key in ('schema','status','evidenceBoundary','nativeInputs','sourceLedger')}
        canonical.update(route={k:route[k] for k in identity},
            dispatcher=dict(contract['switch'],**route['dispatcher']),methods=route['methods'],codeWindows=route['codeWindows'],
            memberCountInstruction=route['memberCountInstruction'],orderedReads=route['orderedReads'],readerHelpers={},
            ownSetters=[route['ownSetter']],nestedContexts=[param_template(route['nestedContext'],route['fields'][-1])],
            sourceReceipts=route['sourceReceipts'])
        proved=regenerate_formatter(canonical,build)
        route.update({k:proved['route'][k] for k in identity})
        route['dispatcher']=project_dispatcher(route['dispatcher'],proved['dispatcher'])
        for key in ('methods','codeWindows','memberCountInstruction','orderedReads'):route[key]=proved[key]
        route['ownSetter']=proved['ownSetters'][0]
        route['nestedContext']=param_projection(route['nestedContext'],proved['nestedContexts'][0])
        current=project_dispatcher(contract['switch'],proved['dispatcher'])
        if switch is not None and current!=switch:raise RouteRefused('single-param-routes:mixed-dispatch-tables')
        switch=current
        for kind,target in proved['readerHelpers'].items():
            if kind in helpers and helpers[kind]!=target:raise RouteRefused(f'single-param-routes:mixed-helper={kind}')
            helpers[kind]=target
    if not switch or set(helpers)!=set(contract['readerHelpers']):raise RouteRefused('single-param-routes:helper-or-route-set')
    out.update(switch=switch,readerHelpers=helpers,nativeInputs=build.inputs,
        evidenceNote='Selected native stored routes re-proved; historical source receipts remain separately hash-gated. No runtime claim.')
    return out


def prove_inherited_param_route(contract,route,build,reads,contexts,windows,reviewed):
    wrapper=build.wrappers[route['wrapperName']]
    if wrapper.own_members:raise RouteRefused('inherited-route:reviewed-inheritance')
    setters=[{'memberIndex':i,'setterName':f'set___{m.name}__','declaringWrapper':m.declaring_wrapper}
             for i,m in enumerate(wrapper.members)]
    if (set(reviewed)!={'memberIndex','callsiteRva','callHex','targetRva','declaringWrapper','methodIndex','setterName'}
        or any(reviewed[k]!=setters[-1][k] for k in ('memberIndex','setterName','declaringWrapper'))):
        raise RouteRefused('inherited-route:reviewed-inherited-setter')
    canonical={k:contract[k] for k in ('schema','status','evidenceBoundary','nativeInputs')}
    branch=copy.deepcopy(route['dispatcher']);branch['branchWindow'].setdefault('boundary','selected wrapper type-load prefix')
    canonical.update(route={**{k:route[k] for k in ('tag','typeName','wrapperName','serializedMemberCount','fields')},'family':route['nativeFamily']},
        dispatcher=branch,methods=route['methods'],codeWindows=windows,
        memberCountInstruction=route['memberCountInstruction'],orderedReads=reads,
        setters=setters,nestedContexts=contexts,readerHelpers=route['readerHelpers'],sourceReceipts=[])
    return regenerate_formatter(canonical,build)


def regenerate_header_routes(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    """Re-prove inherited event headers, including their final Param setter."""
    if set(contract)!={'schema','status','evidenceBoundary','interpretation','nativeInputs','routes'}:
        raise RouteRefused('header-routes:unhandled-root-claims')
    out=copy.deepcopy(contract)
    for route in out['routes']:
        keys={'nativeFamily','codecFamily','tag','typeName','wrapperName','serializedMemberCount','fields',
              'dispatcher','methods','codeWindows','memberCountInstruction','orderedSourceReads',
              'inheritedValidateSetter','nestedContexts','readerHelpers'}
        if set(route)!=keys:raise RouteRefused('header-routes:unhandled-route-claims')
        if set(route['dispatcher'])!={'switchTableRva','switchEntryCount','switchTableSha256','switchTargetRva','branchRva',
            'dispatchKind','branchWindow','typeLoadRva','typeLoadHex','usageCellRva','usageRawHex','registeredTypeIndex','wrapperTypeDefinition','typePointerVa'}:
            raise RouteRefused('header-routes:unhandled-dispatch-claims')
        if any(set(row)!={'memberIndex','fieldName','readKind','sourceCallsiteRva','sourceCallHex','sourceTargetRva'} for row in route['orderedSourceReads']):
            raise RouteRefused('header-routes:unhandled-read-claims')
        if route['nativeFamily']!='ActionHeader' or route['codecFamily']!='ActionHeader':
            raise RouteRefused('header-routes:reviewed-inheritance')
        fresh=prove_inherited_param_route(contract,route,build,route['orderedSourceReads'],route['nestedContexts'],
            route['codeWindows'],route['inheritedValidateSetter']);branch=fresh['dispatcher'];selected=fresh['route']
        if branch['switchTargetRva']!=branch['bodyRva'] or route['dispatcher']['dispatchKind']!='direct-branch':
            raise RouteRefused('header-routes:direct-dispatch-required')
        branch.update(branchRva=branch['bodyRva'],dispatchKind='direct-branch',
            registeredTypeIndex=selected['registeredTypeIndex'],wrapperTypeDefinition=selected['typeDefinition'],
            typePointerVa=hex(build.image.pe.u64_at_va(int(build.image.registration['types'],16)+selected['registeredTypeIndex']*8)))
        route['tag']=selected['tag'];route['dispatcher']=project_dispatcher(route['dispatcher'],branch)
        for key in ('methods','codeWindows','memberCountInstruction','readerHelpers','nestedContexts'):route[key]=fresh[key]
        route['orderedSourceReads']=fresh['orderedReads'];route['inheritedValidateSetter']=fresh['setters'][-1]
    out['nativeInputs']=build.inputs
    return out


def regenerate_getter_int(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    if set(contract)!={'schema','status','evidenceBoundary','nativeInputs','route','sourceReceipt','evidenceNote'}:
        raise RouteRefused('getter-int:unhandled-root-claims')
    out=copy.deepcopy(contract);route=out['route'];wrapper=build.wrappers[route['wrapperName']]
    if set(route)!={'nativeFamily','codecFamily','tag','typeName','wrapperName','parentWrapperName','serializedMemberCount','fields',
        'dispatcher','methods','sourceWindows','formatterWindow','memberCountInstruction','readerHelpers','orderedSourceReads',
        'inheritedValueSetter','nestedContext','generatedWrapper','formatterTailJump'}:
        raise RouteRefused('getter-int:unhandled-route-claims')
    if route['nativeFamily']!='PureGetter' or route['codecFamily']!='GetterBase' or wrapper.parent_name!=route['parentWrapperName']:
        raise RouteRefused('getter-int:reviewed-inheritance')
    if set(route['dispatcher'])!={'switchTableRva','switchEntryCount','switchTableSha256','switchTargetRva','bodyRva','branchWindow',
        'typeLoadRva','typeLoadHex','usageCellRva','usageRawHex','registeredTypeIndex','wrapperTypeDefinition'}:
        raise RouteRefused('getter-int:unhandled-dispatch-claims')
    if any(set(row)!={'memberIndex','fieldName','readKind','callsiteRva','callHex','targetRva'} for row in route['orderedSourceReads']):
        raise RouteRefused('getter-int:unhandled-read-claims')
    if set(route['formatterTailJump'])!={'instructionRva','instructionHex','targetRva'}:
        raise RouteRefused('getter-int:unhandled-forwarding-claims')
    if any(set(w)!={'startRva','endRva','sha256'} for w in route['sourceWindows']):
        raise RouteRefused('getter-int:unhandled-source-window-claims')
    aliases={'callsiteRva':'sourceCallsiteRva','callHex':'sourceCallHex','targetRva':'sourceTargetRva'}
    reads=[{aliases.get(k,k):v for k,v in row.items()} for row in route['orderedSourceReads']]
    fresh=prove_inherited_param_route(contract,route,build,reads,[param_template(route['nestedContext'],route['fields'][-1])],
        [*route['sourceWindows'],route['formatterWindow']],route['inheritedValueSetter'])
    fresh['dispatcher'].update(registeredTypeIndex=fresh['route']['registeredTypeIndex'],wrapperTypeDefinition=fresh['route']['typeDefinition'])
    route['dispatcher']=project_dispatcher(route['dispatcher'],fresh['dispatcher']);route['tag']=fresh['route']['tag']
    route['sourceWindows']=[{k:w[k] for k in ('startRva','endRva','sha256')} for w in fresh['codeWindows'][:-1]]
    route['formatterWindow']=fresh['codeWindows'][-1]
    for key in ('methods','memberCountInstruction','readerHelpers'):route[key]=fresh[key]
    route['orderedSourceReads']=[{next((old for old,new in aliases.items() if new==k),k):v for k,v in row.items()} for row in fresh['orderedReads']]
    route['nestedContext']=param_projection(route['nestedContext'],fresh['nestedContexts'][0]);route['inheritedValueSetter']=fresh['setters'][-1]
    generated=wrapper.row()
    old=route['generatedWrapper']
    if set(generated)!=set(old) or len(generated['members'])!=len(old['members']) or any(
        set(a)!=set(b) for a,b in zip(generated['members'],old['members'])):
        raise RouteRefused('getter-int:generated-wrapper-shape')
    route['generatedWrapper']=generated
    route['formatterTailJump']=forwarding_jump(build.image,route['formatterWindow'],fresh['methods'][0][3])
    out.update(nativeInputs=build.inputs,evidenceNote='Selected native stored route re-proved; source receipt remains historical and separately hash-gated.')
    return out


def typed_route_template(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    """Upgrade reviewed V1 read plans, without admitting their historical spans.

    Old addresses are template keys only. The V2 derivation replaces every
    native anchor, proves generic contexts and full owned reader coverage.
    """
    from scripts.game_data.levelscript_route_deserialize_native import LAYOUT_PATH
    allowed = {'schema','status','nativeInputs','routes','evidenceBoundary','interpretation','enumUnderlying'}
    if set(contract)-allowed or contract['status'] != 'reviewed':
        raise RouteRefused('v1-routes:unsupported-claims')
    interpretations = (
        'Selected union branches resolve the generated wrappers. Each generated Deserialize body checks its member count and calls read helpers and setters in the listed order. Source-authenticated cursors consume these records exactly; stored fields do not establish runtime effects.',
        'For each selected union route, its generated Deserialize checks the recorded member count and calls the recorded read helper then generated setter in the listed order. The byte hash pins the contiguous reader body from entry through its first normal return, including the observed ordered path. This proves serialized read order and does not establish runtime execution or event causality.',
    )
    if contract.get('interpretation') not in interpretations:
        raise RouteRefused('v1-routes:unreviewed-interpretation')
    layouts = json.loads(LAYOUT_PATH.read_bytes())
    if layouts.get('schema') != 'endfield.action-map-layouts.v5':raise RouteRefused('v1-routes:layout-schema')
    selected = {(r['family'],r['wrapperName']):r for r in layouts['layouts']}
    out = copy.deepcopy(contract)
    out.pop('interpretation'); out.update(schema='endfield.levelscript-route-deserialize-native.v2',status='exact-current-build',typedReaderWindows=[])
    targets = set()
    for row in out['routes']:
        allowed_row = {'family','tag','wrapperName','memberCount','fields','nativeIdentity','sourceEvidence',
                       'deserializeMethodIndex','deserializeRva','normalBodyLength','normalBodySha256','readOrder'}
        if set(row)-allowed_row:raise RouteRefused('v1-routes:route-claims')
        layout = selected[row['family'],row['wrapperName']]
        if ('fields' in row and row['fields'] != layout['fields']) or row['memberCount'] != layout['memberCount']:
            raise RouteRefused('v1-routes:reviewed-layout-drift')
        row['fields'] = copy.deepcopy(layout['fields'])
        old_source = row.pop('sourceEvidence',None)
        if old_source is not None and set(old_source) != {'source','sha256','unionOffset','endOffset','wholeFileStatus'}:
            raise RouteRefused('v1-routes:source-evidence-claims')
        # V1 has no authenticated span digest. Do not invent a current receipt.
        row['sourceReceipts'] = []
        wrapper = build.wrappers[row['wrapperName']]
        if len(row['readOrder']) != len(wrapper.members):raise RouteRefused('v1-routes:read-count-drift')
        row.update(typeName=wrapper.wrapped_type,typeDefinition=wrapper.type_definition,
                   inheritedMemberCount=len(wrapper.inherited_members),deserializeFragmentWindows=[],memberCountInstruction={'rva':0,'hex':''})
        row.setdefault('nativeIdentity',dict.fromkeys(('dispatcherVa','switchTableVa','switchTargetVa','branchBodyVa',
            'branchCodeHex','usageCellVa','usageRawHex','registeredTypeIndex','typeDefinition'),0))
        for item,member,field in zip(row['readOrder'],wrapper.members,row['fields'],strict=True):
            if set(item) != {'name','declaredType','setterMethodIndex','readCallRva','readTargetRva',
                             'setterCallRva','setterTargetRva','setterName'}:
                raise RouteRefused('v1-routes:read-claims')
            item['declaringWrapper'] = member.declaring_wrapper
            if field[1].startswith(('Param<','ParamOutput<')):
                item['typedReadContext'] = dict(instructionRva=0,instructionHex='',cellVa=0,usageRawHex='',
                    methodSpecIndex=0,methodSpec=[],argumentRawHex='',argumentType=item['declaredType'],
                    readerType='MemoryPack.MemoryPackReader',readerMethod='ReadValue')
                targets.add(item['readTargetRva'])
    out['typedReaderWindows'] = [dict(startRva=t,endRva=0,sha256='',fragmentWindows=[],
        boundary='complete selected generic reader and owned fragments; child grammar and provider selection are separate') for t in sorted(targets)]
    return out


def regenerate_typed_routes(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    """Re-derive the bounded V2 read/setter shape; receipts stay historical."""
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    collection_schema='endfield.levelscript-route-deserialize-native.v6'
    if set(contract)-{'enumUnderlying'}-({'collectionReaders'} if contract['schema']==collection_schema else set()) != {'schema','status','nativeInputs','routes','evidenceBoundary','typedReaderWindows'}:
        raise RouteRefused('typed-routes:auxiliary-claims:adapter-required')
    if contract['schema']==collection_schema and contract.get('collectionReaders')!=[{'codecKind':'List<int>','declaredType':'System.Collections.Generic.List`1<int>','sourceContract':'levelscript_int_list_native.json'}]:
        raise RouteRefused('typed-routes:int-list-source-shape')
    if contract['schema']==collection_schema and (len(contract['routes'])!=1 or contract['routes'][0]['wrapperName']!='Beyond.MemoryPack.Beyond_Gameplay_Actions_SwitchIntLargerForMemoryPack' or contract['routes'][0]['family']!='ActionBase' or [(i,f[0]) for i,f in enumerate(contract['routes'][0]['fields']) if f[1]=='List<int>']!=[(8,'caseIDList'),(9,'caseValueList')]):
        raise RouteRefused('typed-routes:int-list-SwitchIntLarger-scope')
    out = copy.deepcopy(contract); image = build.image; base = image.pe.image_base
    window_boundaries = {}
    for window in contract['typedReaderWindows']:
        if set(window) != {'startRva','endRva','sha256','fragmentWindows','boundary'}:
            raise RouteRefused('typed-routes:reader-window-claims')
        if any(set(fragment)!={'startRva','endRva','sha256'} for fragment in window['fragmentWindows']):
            raise RouteRefused('typed-routes:reader-fragment-claims')
        window_boundaries[window['startRva']] = window['boundary']
    old_targets = [item['readTargetRva'] for row in contract['routes'] for item in row['readOrder'] if 'typedReadContext' in item]
    if set(old_targets) != set(window_boundaries) or len(window_boundaries) != len(contract['typedReaderWindows']):
        raise RouteRefused('typed-routes:reviewed-reader-coverage')
    targets = {}
    for row in out['routes']:
        if set(row) != {'family','tag','wrapperName','typeName','typeDefinition','memberCount','inheritedMemberCount',
                'fields','nativeIdentity','deserializeMethodIndex','deserializeRva','normalBodyLength','normalBodySha256',
                'deserializeFragmentWindows','memberCountInstruction','readOrder','sourceReceipts'}:
            raise RouteRefused('typed-routes:route-claims:adapter-required')
        if (set(row['memberCountInstruction'])!={'rva','hex'} or any(
                set(fragment)!={'startRva','endRva','sha256'} for fragment in row['deserializeFragmentWindows'])):
            raise RouteRefused('typed-routes:reader-claims')
        if (set(row['nativeIdentity']) != {'dispatcherVa','switchTableVa','switchTargetVa','branchBodyVa',
                'branchCodeHex','usageCellVa','usageRawHex','registeredTypeIndex','typeDefinition'}
                or [f[0] for f in row['fields']] != [r['name'] for r in row['readOrder']]):
            raise RouteRefused('typed-routes:identity-or-field-plan')
        wrapper = build.wrappers[row['wrapperName']]
        check_fields(dict(row, serializedMemberCount=row['memberCount'],
            nativeDeclaredTypes=[[r['name'],r['declaredType']] for r in row['readOrder']]), wrapper)
        if row['inheritedMemberCount'] != len(wrapper.inherited_members):
            raise RouteRefused('typed-routes:inherited-member-count')
        body = build.body.body(wrapper.name, 'Deserialize')
        inline = [i for i,item in enumerate(row['readOrder']) if 'setterInlineProof' in item]
        if inline and (out['schema'] != 'endfield.levelscript-route-deserialize-native.v5'
                or any(row['readOrder'][i]['setterInlineProof'].get('transfer') != 'inlinedBaseStore'
                       or row['fields'][i][1] not in ('bool','int32') for i in inline)):
            raise RouteRefused('typed-routes:inline-base-store-claims')
        header, reads, setters, setups = select_calls(body.rows, len(wrapper.members),
            [image.method_pointer_va(image.metadata.methods[m.method_index]) for m in wrapper.members],inline_members=inline)
        for index, (item, member, read, setter, setup) in enumerate(zip(row['readOrder'],wrapper.members,reads,setters,setups,strict=True)):
            expected_keys = {'name','declaredType','setterMethodIndex','setterName','declaringWrapper',
                             'readCallRva','readTargetRva','setterCallRva','setterTargetRva'}
            kind = row['fields'][index][1]
            literal_list=kind=='List<int>' and out['schema']==collection_schema and member.declared_type=='System.Collections.Generic.List`1<int>'
            generic = kind.startswith(('Param<','ParamOutput<')) or literal_list
            if set(item) != expected_keys | ({'typedReadContext'} if generic else set()) | ({'setterInlineProof'} if index in inline else set()):
                raise RouteRefused(f'typed-routes:read-claims:member={index}')
            if item['setterName'] != image.metadata.string(image.metadata.methods[member.method_index].name_index) or item['declaringWrapper'] != member.declaring_wrapper:
                raise RouteRefused(f'typed-routes:setter-identity:member={index}')
            target = int(read['text'].split()[1],16)
            if kind in ('bool','int32'):
                if (kind == 'bool' and member.kind != 'bool' or kind == 'int32'
                        and member.kind != 'scalar32' and (member.kind,member.underlying_kind,member.width) != ('enum','scalar32',4)):
                    raise RouteRefused(f'typed-routes:primitive-type:member={index}')
                prove_primitive(image,target,'bool-byte' if kind=='bool' else 'int32')
            elif kind == 'string':
                if member.kind != 'string':raise RouteRefused('typed-routes:string-type')
                build.prove_pooled_string_target(target)
            elif generic:
                loads = [r for r in setup if bytes.fromhex(r['bytes'])[:3] == b'\x48\x8b\x15']
                if len(loads) != 1:raise RouteRefused('typed-routes:context-load-count')
                context = derive_typed_usage_context(image,int(loads[0]['va'],16)-base,label='typed-routes')
                reader_method='ReadPackable' if literal_list else 'ReadValue'
                if (context['tag'] != 6 or context['typeName'] != 'MemoryPack.MemoryPackReader'
                        or context['methodName'] != reader_method or context['classArguments']
                        or context['methodArguments'] != [member.declared_type]):
                    raise RouteRefused('typed-routes:reader-context-type')
                arguments = image.instantiations.resolve(context['methodSpec'][2]).arguments
                fresh = {k:context[k] for k in ('instructionRva','instructionHex','usageRawHex','methodSpecIndex','methodSpec')}
                fresh.update(cellVa=base+context['usageCellRva'], argumentRawHex=arguments[0].raw_type_record_hex.upper(),
                    argumentType=member.declared_type,readerType=context['typeName'],readerMethod=context['methodName'])
                reviewed = item['typedReadContext']
                if (set(reviewed) != set(fresh) or reviewed['readerType'] != fresh['readerType']
                        or reviewed['readerMethod'] != fresh['readerMethod']
                        or protocol.canonical_type_name(reviewed['argumentType']) != protocol.canonical_type_name(member.declared_type)):
                    raise RouteRefused('typed-routes:context-claims')
                item['typedReadContext'] = fresh
                old_target = item['readTargetRva']
                if old_target not in window_boundaries:raise RouteRefused('typed-routes:missing-reviewed-reader-window')
                boundary = window_boundaries[old_target]
                if target in targets and targets[target] != boundary:raise RouteRefused('typed-routes:reader-boundary-drift')
                targets[target] = boundary
                if literal_list:build.prove_reader_clone_target(target,'MemoryPack.MemoryPackReader.ReadPackable',result_abi='reference')
                else:build.prove_named_target(target,'MemoryPack.MemoryPackReader','ReadValue')
            else:raise RouteRefused(f'typed-routes:wire-kind-adapter-required={kind}')
            if index in inline:
                from scripts.game_data.il2cpp.reference_field_programs import inlined_base_setter
                item['setterInlineProof']=inlined_base_setter(image,build.body,build.wrappers,member,body.rows,read,setter)
                item['setterInlineProof']['memberIndex']=index
            item.update(declaredType=member.declared_type,setterMethodIndex=member.method_index,
                readCallRva=int(read['va'],16)-base,readTargetRva=target-base,
                setterCallRva=None if index in inline else int(setter['va'],16)-base,
                setterTargetRva=image.method_pointer_va(image.metadata.methods[member.method_index])-base)
        switch = build.switch(row['family'])
        entries = [e for e in switch['entries'] if e.get('wrapperName') == wrapper.name]
        if len(entries) != 1:raise RouteRefused('typed-routes:union-entry-count')
        entry = entries[0]; branch = int(entry['bodyVa'],16); cell = int(entry['usageCellVa'],16)
        branch_rows = image.mapper.decode_x64_subset(image.pe.bytes_at_va(branch,128),branch,stop_offset=128)
        loads = [r for r in branch_rows if bytes.fromhex(r['bytes'])[:3] == b'\x48\x8b\x15'
            and int(r['va'],16)+7+struct.unpack_from('<i',bytes.fromhex(r['bytes']),3)[0] == cell]
        if len(loads) != 1:raise RouteRefused('typed-routes:union-type-load-count')
        row.update(tag=entry['tag'],typeDefinition=wrapper.type_definition,deserializeRva=body.pointer-base,
            deserializeMethodIndex=_method_row(image,[0,wrapper.name,'Deserialize',0])[0],normalBodyLength=body.size,
            normalBodySha256=_sha256_upper(image.pe.bytes_at_va(body.pointer,body.size)),
            deserializeFragmentWindows=[{k:v for k,v in _window(image,va,va+size,'').items() if k!='boundary'}
                for va,size in build.body.chained_fragments.get(body.pointer,())],
            memberCountInstruction={'rva':int(header['va'],16)-base,'hex':bytes.fromhex(header['bytes']).hex().upper()},
            nativeIdentity=dict(dispatcherVa=switch['dispatcherVa'],switchTableVa=switch['tableVa'],
                switchTargetVa=entry['targetVa'],branchBodyVa=entry['bodyVa'],usageCellVa=entry['usageCellVa'],
                registeredTypeIndex=entry['registeredTypeIndex'],typeDefinition=entry['typeDefinition'],
                branchCodeHex=image.pe.bytes_at_va(branch,int(loads[0]['va'],16)+7-branch).hex().upper(),
                usageRawHex=image.pe.bytes_at_va(cell,8).hex().upper()))
    if not out['routes']:raise RouteRefused('typed-routes:empty-routes')
    out['typedReaderWindows'] = []
    for target,boundary in sorted(targets.items()):
        window = _window(image,target,build.body.extents[target],boundary)
        window['fragmentWindows'] = [{k:v for k,v in _window(image,va,va+size,'').items() if k!='boundary'}
            for va,size in build.body.chained_fragments.get(target,())]
        out['typedReaderWindows'].append(window)
    out['nativeInputs'] = {'gameAssembly':{'sha256':build.inputs['GameAssembly.dll']},
                           'metadata':{'sha256':build.inputs['global-metadata.dat']}}
    from scripts.game_data.levelscript_route_deserialize_native import HEADER_ENUM_UNDERLYING, PARAM_ENUM_UNDERLYING, STORED_ENUM_UNDERLYING
    enums = {row['typeName']:row for row in contract.get('enumUnderlying',[])}
    if len(enums)!=len(contract.get('enumUnderlying',[])):raise RouteRefused('typed-routes:duplicate-enum-claim')
    for row in out['routes']:
        for item in row['readOrder']:
            required = {**HEADER_ENUM_UNDERLYING,**PARAM_ENUM_UNDERLYING,**STORED_ENUM_UNDERLYING}.get(item['declaredType'])
            if required:enums.setdefault(required[0],{'typeName':required[0],'underlyingType':required[1]})
    if enums:
        out['enumUnderlying'] = [build.derive_enum(dict(row,typeDefinition=0))
                                for name,row in sorted(enums.items())]
    out['evidenceBoundary'] = 'exact selected union identity, complete generated reader, member count, typed read contexts and ordered setters; source receipts are historical and separately hash-gated; default provider selection, current owner EOF and runtime effects remain unresolved'
    return out


def regenerate_getter_route(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    """Adapt nested read/setter-pair routes to the shared body proof.

    Only declared context, enum and metadata-only pointer shapes are handled.
    Unhandled claims refuse rather than surviving as stale evidence.
    Each route is atomic; the caller publishes only after the owning validator
    accepts every route. No old instruction offset or window length is reused.
    """
    lifted={'methods','codeWindows','memberCountInstruction','readOrder','paramContexts','paramContext','readerHelpers','sourceReceipts','formatterTailJump'} & set(contract)
    if lifted:
        if 'route' not in contract:raise RouteRefused('getter-route:top-reader-plan-needs-single-route')
        normalized=copy.deepcopy(contract)
        for key in lifted:
            if key in normalized['route']:raise RouteRefused(f'getter-route:duplicate-claim={key}')
            value=normalized.pop(key)
            normalized['route']['paramContexts' if key=='paramContext' else key]=[value] if key=='paramContext' else value
        out=regenerate_getter_route(normalized,build)
        for key in lifted:
            value=out['route'].pop('paramContexts' if key=='paramContext' else key)
            if key=='paramContext' and len(value)!=1:raise RouteRefused('getter-route:single-context-count')
            out[key]=value[0] if key=='paramContext' else value
        return out
    allowed = {'schema', 'status', 'evidenceBoundary', 'evidenceNote', 'nativeInputs',
               'dispatcher', 'route', 'routes','enumTypes','enumUnderlying','enumAlias','enumWidths','enum','pointers','spawnerPtr','entityPtr','pointerTypes'}
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
            'orderedReads', 'readOrder', 'paramContexts', 'sourceReceipts','dispatcher','readerHelpers','inlineSetterMembers','getterSetterMembers'}
        extra = sorted(set(route) - allowed_route)
        if extra:
            raise RouteRefused(f'route[{index}]:auxiliary-claims={extra}:proof-required')
        reads = route.get('orderedReads', route.get('readOrder'))
        if reads is None or not route.get('methods'):
            raise RouteRefused(f'route[{index}]:paired-read-plan-or-methods:missing')
        canonical_route = {k: copy.deepcopy(route[k]) for k in (
            'family','tag','typeName','wrapperName','typeDefinition','registeredTypeIndex',
            'inheritedMemberCount','ownMemberCount') if k in route}
        if 'family' not in canonical_route:
            if contract['schema'] not in ('endfield.levelscript-taskmap-condition-native.v1','endfield.levelscript-taskmap-followon-native.v1'):
                raise RouteRefused(f'route[{index}]:reviewed-family:missing')
            canonical_route['family']='GameCondition'
        canonical_route['serializedMemberCount'] = route.get('serializedMemberCount', route.get('memberCount'))
        canonical_route['fields'] = [[r[0],'int32' if r[1]=='enum32' else r[1]] for r in route['fields']]
        canonical_route['nativeDeclaredTypes'] = route.get('nativeDeclaredTypes')
        if canonical_route['nativeDeclaredTypes'] is None and all(len(r) == 3 for r in route['fields']):
            canonical_route['nativeDeclaredTypes'] = [[r[0],r[2]] for r in route['fields']]
        if canonical_route['nativeDeclaredTypes'] is None:
            raise RouteRefused(f'route[{index}]:nativeDeclaredTypes:missing-reviewed-types')
        canonical_reads, canonical_setters = [], []
        for member, row in enumerate(reads):
            if row.get('memberIndex') != member:
                raise RouteRefused(f'route[{index}]:reviewed-read-order:member={member}')
            wire=canonical_route['fields'][member][1]
            if row.get('readKind',route['fields'][member][1]) not in (route['fields'][member][1],'generic' if wire.startswith(('Param<','ParamOutput<')) else wire):
                raise RouteRefused(f'route[{index}]:reviewed-read-kind:member={member}')
            canonical_reads.append({'memberIndex': member, 'fieldName': row.get('fieldName',route['fields'][member][0]),
                                    'readKind': wire})
            # Authenticate the old setter's identity by name, not its old index.
            declaration = build.wrappers[route['wrapperName']].members[member]
            field=declaration.name
            if row.get('setterName',f'set___{field}__')!=f'set___{field}__':
                raise RouteRefused(f'route[{index}]:reviewed-setter-name:member={member}')
            canonical_setters.append({'memberIndex':member,
                'setterName': f'set___{field}__', 'declaringWrapper':row.get('declaringWrapper',declaration.declaring_wrapper)})
        dispatcher=copy.deepcopy(contract['dispatcher']);dispatcher.update(route.get('dispatcher',{}))
        contexts=[param_template(c,route['fields'][c['memberIndex']]) for c in route.get('paramContexts',[])]
        if 'paramContexts' not in route:
            for member,((_,wire),(_,declared)) in enumerate(zip(canonical_route['fields'],canonical_route['nativeDeclaredTypes'],strict=True)):
                base='Beyond.Gameplay.Actions.'+('ParamOutput`1' if wire.startswith('ParamOutput<') else 'Param`1')
                if wire.startswith(('Param<','ParamOutput<')):
                    if not declared.startswith(base+'<') or not declared.endswith('>'):
                        raise RouteRefused(f'param-context:reviewed-declaration={declared}')
                    contexts.append({'memberIndex':member,'elementTypeName':declared[len(base)+1:-1]})
        canonical = {'route':canonical_route, 'dispatcher':dispatcher,
            'methods':route['methods'], 'codeWindows':route['codeWindows'],
            'memberCountInstruction':route.get('memberCountInstruction',{}), 'readerHelpers':{},
            'orderedReads':canonical_reads,'setters':canonical_setters,
            'nestedContexts':contexts,
            'sourceReceipts':route.get('sourceReceipts',[])}
        if 'inlineSetterMembers' in route:canonical['inlineSetterMembers']=route['inlineSetterMembers']
        if 'getterSetterMembers' in route:canonical['getterSetterMembers']=route['getterSetterMembers']
        # Table-only dispatchers keep branch evidence on the route. Derive a
        # fresh branch prefix, retaining no old window offsets or hashes.
        canonical['dispatcher'].setdefault('branchWindow', {'boundary':'selected wrapper type-load prefix'})
        canonical['dispatcher']['branchWindow'].setdefault('boundary','selected wrapper type-load prefix')
        try:proved = regenerate_formatter(canonical,build)
        except (ValueError,RuntimeError) as exc:raise RouteRefused(f'route[{index}]:{route["wrapperName"]}:{exc}') from exc
        new = copy.deepcopy(route)
        new.update(tag=proved['route']['tag'],typeDefinition=proved['route']['typeDefinition'],
                   registeredTypeIndex=proved['route']['registeredTypeIndex'],
                   methods=proved['methods'],codeWindows=proved['codeWindows'])
        if 'memberCountInstruction' in new:new['memberCountInstruction']=proved['memberCountInstruction']
        branch = proved['dispatcher']
        if 'dispatcher' in new:new['dispatcher']=project_dispatcher(route['dispatcher'],branch)
        if 'paramContexts' in route:
            by_member={c['memberIndex']:c for c in proved['nestedContexts']}
            new['paramContexts']=[param_projection(c,by_member[c['memberIndex']]) for c in route['paramContexts']]
        for key in ('switchTargetRva','bodyRva','usageCellRva','usageRawHex'):
            if key in new: new[key] = branch[key]
        key = 'orderedReads' if 'orderedReads' in route else 'readOrder'
        for old, read, setter in zip(new[key], proved['orderedReads'],proved['setters'],strict=True):
            values=dict(readCallRva=read['sourceCallsiteRva'],readCallHex=read['sourceCallHex'],
                readTargetRva=read['sourceTargetRva'],callsiteRva=read['sourceCallsiteRva'],callHex=read['sourceCallHex'],targetRva=read['sourceTargetRva'])
            if 'storeRva' in setter:
                for field in ('setterCallRva','setterCallHex','setterTargetRva','setterMethodIndex'):old.pop(field,None)
                old['setterInlineProof']=setter
            else:
                values.update(setterCallRva=setter['callsiteRva'],setterCallHex=setter['callHex'],setterTargetRva=setter['targetRva'],setterMethodIndex=setter['methodIndex'])
            old.update({k:v for k,v in values.items() if k in old})
            for target,source in (('contextLoadRva','instructionRva'),('contextLoadHex','instructionHex'),('contextCellRva','cellRva')):
                if target in old:old[target]=by_member[old['memberIndex']][source]
        if 'formatterTailJump' in new:
            new['formatterTailJump']=forwarding_jump(build.image,proved['codeWindows'][-1],proved['methods'][0][3])
        if 'readerHelpers' in new:
            helpers={}
            for row in new[key]:
                kind=row['readKind'];target=row['readTargetRva']
                if kind in helpers and helpers[kind]!=target:raise RouteRefused(f'reader-helpers:multiple-targets={kind}')
                helpers[kind]=target
            if set(helpers)!=set(new['readerHelpers']):raise RouteRefused('reader-helpers:reviewed-kinds-drift')
            new['readerHelpers']=helpers
        derived.append(new)
        dispatchers.append(branch)
    if not derived:
        raise RouteRefused('getter-route:empty-routes')
    out['dispatcher']=project_dispatcher(contract['dispatcher'],dispatchers[0])
    if any(project_dispatcher(contract['dispatcher'],d)!=out['dispatcher'] for d in dispatchers[1:]):
        raise RouteRefused('getter-route:mixed-dispatch-tables')
    if 'routes' in out: out['routes'] = derived
    else: out['route'] = derived[0]
    for key in ('enumTypes','enumUnderlying','enumAlias','enum'):
        if key in contract:
            value=contract[key]
            out[key]=[build.derive_enum(e) for e in value] if isinstance(value,list) else build.derive_enum(value)
    for name,width in contract.get('enumWidths',{}).items():build.derive_enum({'typeName':name,'width':width})
    pointers=dict(contract.get('pointers',{}),**contract.get('pointerTypes',{}))
    pointers.update({key:contract[key] for key in ('spawnerPtr','entityPtr') if key in contract})
    for name,pointer in pointers.items():
        if set(pointer)!={'typeDefinition','wrapperName','wrappedType','fields'}:
            raise RouteRefused(f'pointers.{name}:unhandled-claims')
        w=build.wrappers[pointer['wrapperName']]
        check_fields({'wrapperName':w.name,'typeName':pointer['wrappedType'],'serializedMemberCount':len(pointer['fields']),
                      'nativeDeclaredTypes':pointer['fields']},w)
        target=out.get('pointers',{}).get(name,out.get('pointerTypes',{}).get(name,out.get(name)))
        target['typeDefinition']=w.type_definition
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


def regenerate_instance_route(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    """Re-prove a final whole-instance read; preserve inner receipts as historical."""
    if set(contract)!={'schema','status','evidenceBoundary','evidenceNote','nativeInputs','route','dispatcher','methods','codeWindows',
        'memberCountInstruction','readerHelpers','orderedReads','setters','nestedAssignment','nestedContexts','nestedValue','enumTypes','sourceReceipts'}:
        raise RouteRefused('instance-route:unhandled-root-claims')
    route=contract['route'];wrapper=build.wrappers[route['wrapperName']]
    if (set(route)!={'family','tag','typeName','wrapperName','typeDefinition','registeredTypeIndex','serializedMemberCount','inheritedMemberCount','fields','nativeDeclaredTypes'}
        or route['family']!='ActionBase' or route['typeName']!='Beyond.Gameplay.Actions.SendLuaEvent1'
        or len(wrapper.own_members)!=1 or len(wrapper.inherited_members)!=8
        or contract['enumTypes']!=[] or contract['nestedValue']!={'memberCount':7,'jsonParamCount':1,
            'fieldKinds':['int32','string','bool','int32','bool','Param<string>','string']}):
        raise RouteRefused('instance-route:reviewed-type-or-historical-shape')
    assignment=contract['nestedAssignment']
    if (set(contract['dispatcher'])!={'switchTableRva','switchEntryCount','switchTableSha256','switchTargetRva','switchEntryHex',
        'bodyRva','usageCellRva','usageRawHex','branchWindow','typeLoadRva','typeLoadHex'}
        or any(set(w)!={'startRva','endRva','sha256','boundary'} for w in contract['codeWindows'])
        or any(set(read)!={'memberIndex','fieldName','readKind','sourceCallsiteRva','sourceCallHex','sourceTargetRva'} for read in contract['orderedReads'])
        or any(set(setter)!={'memberIndex','callsiteRva','callHex','targetRva','declaringWrapper','methodIndex','setterName'} for setter in contract['setters'])):
        raise RouteRefused('instance-route:unhandled-program-claims')
    canonical={k:copy.deepcopy(v) for k,v in contract.items() if k not in ('nestedAssignment','nestedValue','enumTypes')}
    canonical['instanceAssignment']=copy.deepcopy(assignment)
    canonical['setters'].append(dict(memberIndex=assignment['memberIndex'],declaringWrapper=assignment['declaringWrapper'],setterName=assignment['declaredSetterName']))
    out=regenerate_formatter(canonical,build)
    if set(out['readerHelpers'])!=set(contract['readerHelpers']):raise RouteRefused('instance-route:reviewed-helper-kinds')
    out['setters'].pop();out['nestedAssignment']=out.pop('instanceAssignment')
    out.update(nestedValue=copy.deepcopy(contract['nestedValue']),enumTypes=[],
        evidenceNote='Selected outer native route, typed ReadValue and whole-instance assignment re-proved. The inner seven-member grammar rests on historical, separately hash-gated source receipts; current inner corpus admission and runtime effects remain unresolved.')
    return out


def regenerate_catalog_route(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    """Adapt catalog-owned action cursors without carrying native identities forward."""
    if set(contract)!={'schema','status','nativeInputs','catalogContract','evidenceBoundary','route'} or contract['catalogContract']!='levelscript_union_tags.json':
        raise RouteRefused('catalog-route:unhandled-root-claims')
    out=copy.deepcopy(contract);route=out['route'];image=build.image
    keys={'family','tag','name','typeName','wrapperName','serializedMemberCount','fields','dispatcher',
          'wrapperInheritance','managedInheritance','ownWrapperSetters','ownManagedFields','inheritedSetterOwners',
          'methods','codeWindows','memberCountInstruction','orderedMembers'}
    if set(route)-{'nestedContexts'}!=keys or route['family']!='ActionBase' or route['typeName']!='Beyond.Gameplay.Actions.'+route['name']:
        raise RouteRefused('catalog-route:unhandled-route-claims')
    if set(route['dispatcher'])!={'switchTableRva','switchEntryCount','switchTableSha256','switchTargetRva','switchEntryHex',
        'branchRva','branchWindow','typeLoadRva','typeLoadHex','usageCellRva','usageRawHex','registeredTypeIndex','wrapperTypeDefinition'}:
        raise RouteRefused('catalog-route:unhandled-dispatch-claims')
    wrapper=build.wrappers[route['wrapperName']];reads=[];setters=[]
    for member,reviewed in zip(wrapper.members,route['orderedMembers'],strict=True):
        if (set(reviewed)!={'memberIndex','fieldName','wireKind','sourceRead','setterCall','setterMethod'}
            or any(set(reviewed[k])!={'rva','hex','targetRva'} for k in ('sourceRead','setterCall'))
            or len(reviewed['setterMethod'])!=4):
            raise RouteRefused('catalog-route:unhandled-member-claims')
        old=reviewed['setterMethod'];name=f'set___{member.name}__'
        if old[1:3]!=[member.declaring_wrapper,name]:raise RouteRefused('catalog-route:reviewed-setter-identity')
        kind=reviewed['wireKind'];prefix='Beyond.Gameplay.Actions.Param`1<'
        if kind.startswith('Param<') and (kind not in ('Param<string>','Param<bool>')
            or not member.declared_type.startswith(prefix) or not member.declared_type.endswith('>')
            or protocol.canonical_type_name(member.declared_type[len(prefix):-1])!=protocol.canonical_type_name(kind[6:-1])):
            raise RouteRefused('catalog-route:declared-param-type')
        reads.append(dict(memberIndex=reviewed['memberIndex'],fieldName=reviewed['fieldName'],readKind=reviewed['wireKind']))
        setters.append(dict(memberIndex=reviewed['memberIndex'],declaringWrapper=old[1],setterName=old[2]))
    windows=copy.deepcopy(route['codeWindows'])
    if (any(set(w)!={'startRva','endRva','sha256','boundary'} for w in windows)
        or windows[0]['startRva']!=route['methods'][0][3] or windows[-1]['startRva']!=route['methods'][1][3]
        or windows[0].get('boundary') not in ('source reader primary .pdata entry','complete source reader .pdata body')
        or windows[-1].get('boundary') not in ('generated formatter forwarding body','complete forwarding formatter body')):
        raise RouteRefused('catalog-route:reviewed-complete-window-boundary')
    windows[0]['boundary']='complete source reader .pdata body';windows[-1]['boundary']='complete forwarding formatter body'
    canonical={k:contract[k] for k in ('schema','status','evidenceBoundary','nativeInputs')}
    canonical.update(route={k:route[k] for k in ('family','tag','typeName','wrapperName','serializedMemberCount','fields')},
        dispatcher=route['dispatcher'],methods=route['methods'],codeWindows=windows,
        memberCountInstruction=route['memberCountInstruction'],readerHelpers={},orderedReads=reads,
        setters=setters,nestedContexts=route.get('nestedContexts',[]),sourceReceipts=[])
    fresh=regenerate_formatter(canonical,build);branch=fresh['dispatcher'];selected=fresh['route']
    branch.update(branchRva=branch['bodyRva'],registeredTypeIndex=selected['registeredTypeIndex'],wrapperTypeDefinition=selected['typeDefinition'])
    route['dispatcher']=project_dispatcher(route['dispatcher'],branch);route['tag']=selected['tag']
    for key in ('methods','codeWindows','memberCountInstruction'):route[key]=fresh[key]
    if 'nestedContexts' in route:
        route['nestedContexts']=[param_projection(old,new) for old,new in zip(route['nestedContexts'],fresh['nestedContexts'],strict=True)]
    for old,read,setter in zip(route['orderedMembers'],fresh['orderedReads'],fresh['setters'],strict=True):
        old['sourceRead']={k:read[v] for k,v in zip(('rva','hex','targetRva'),('sourceCallsiteRva','sourceCallHex','sourceTargetRva'))}
        old['setterCall']={k:setter[v] for k,v in zip(('rva','hex','targetRva'),('callsiteRva','callHex','targetRva'))}
        method=image.metadata.methods[setter['methodIndex']];parameter=image.metadata.parameters_for(method)
        if len(parameter)!=1:raise RouteRefused('catalog-route:setter-arity')
        old['setterMethod']=[method.index,setter['declaringWrapper'],setter['setterName'],image.metadata.metadata_type_name(parameter[0].type_index)]
    types={image.metadata.type_full_name(t):t for t in image.metadata.types}
    for row in route['wrapperInheritance']+route['managedInheritance']:
        if set(row)!={'typeDefinition','typeName','parentTypeDefinition','parentTypeName'}:
            raise RouteRefused('catalog-route:unhandled-inheritance-claims')
        row.update(typeDefinition=types[row['typeName']].index,parentTypeDefinition=types[row['parentTypeName']].index)
        image.check_wrapper_inheritance(row)
    own=route['ownWrapperSetters'];actual=image.setter_methods(types[route['wrapperName']],parameter='typeName')
    if [r[1] for r in own]!=[r[1] for r in actual]:raise RouteRefused('catalog-route:own-setter-drift')
    route['ownWrapperSetters']=actual
    managed=types[route['typeName']];fields=image.metadata.fields_for(managed)
    if [r[0] for r in route['ownManagedFields']]!=[image.metadata.string(f.name_index) for f in fields]:
        raise RouteRefused('catalog-route:managed-field-drift')
    by_name={m.name:m for m in wrapper.own_members}
    for field in fields:
        name=image.metadata.string(field.name_index);pointer=image.pe.u64_at_va(int(image.registration['types'],16)+field.type_index*8)
        actual=protocol.runtime_type_name(image.pe,image.metadata,pointer)
        if name not in by_name or protocol.canonical_type_name(actual)!=protocol.canonical_type_name(by_name[name].declared_type):
            raise RouteRefused(f'catalog-route:managed-field-type:{name}:{actual}')
    route['ownManagedFields']=[[image.metadata.string(f.name_index),image.metadata.metadata_type_name(f.type_index)] for f in fields]
    for owner in route['inheritedSetterOwners']:
        if set(owner)!={'typeDefinition','typeName','setters'}:raise RouteRefused('catalog-route:unhandled-setter-owner-claims')
        actual=image.setter_methods(types[owner['typeName']],parameter='typeName')
        if [r[1:] for r in owner['setters']]!=[r[1:] for r in actual]:raise RouteRefused('catalog-route:inherited-setter-drift')
        owner.update(typeDefinition=types[owner['typeName']].index,setters=actual)
    out['nativeInputs']=build.inputs
    out['evidenceBoundary'].update(
        exact='Selected ActionBase switch route, registered wrapper, complete reader and formatter bodies, inherited setter chain and recorded typed read contexts on the pinned build.',
        direct='Observed native source reads, typed parameter contexts and setter transfers in the recorded member order.',
        unresolved='Pooled string value equivalence does not prove inline string wire equivalence. Current installed corpus admission, runtime scheduling and gameplay effects remain unproved.')
    return out


def regenerate_scalar_param(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    """Derive flat scalar Param profiles; each owner proves its actual program."""
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.string_source_instructions import decode_string_source_instructions as decode
    leaf=contract.get('leaf');width=leaf['rawSize'] if leaf else 8
    if set(contract) != {'schema','status','codecKind','nativeInputs','dependencies','evidenceBoundary','parameter','constantSource','int32Source'} | ({'leaf'} if leaf else set()):
        raise RouteRefused('long-param:unsupported-claims')
    out=copy.deepcopy(contract);p=out['parameter'];image=build.image;base=image.pe.image_base
    if set(p) != {'typeDefinition','wrapperName','wrappedType','members','methods','orderedReads','allocationContext','ownedFieldSlots','memberCountInstruction'}:
        raise RouteRefused('long-param:unsupported-parameter-claims')
    wrapper=build.wrappers[p['wrapperName']]
    if set(p['ownedFieldSlots'])!={m.name for m in wrapper.members}:raise RouteRefused('scalar-param:owned-field-claims')
    if wrapper.wrapped_type!=p['wrappedType']:raise RouteRefused('scalar-param:wrapped-type')
    if [[m.name,protocol.canonical_type_name(m.declared_type)] for m in wrapper.members] != [[m['name'],protocol.canonical_type_name(m['declaredType'])] for m in p['members']]:
        raise RouteRefused('long-param:reviewed-field-drift')
    p['typeDefinition']=wrapper.type_definition
    p['members']=[{'name':m.name,'declaredType':m.declared_type,'methodIndex':m.method_index} for m in wrapper.members]
    required={'.ctor','GetValue','CreateInstance','Deserialize',*('set___'+m.name+'__' for m in wrapper.members)}
    if set(p['methods']) != required: raise RouteRefused('long-param:method-claims')
    def record(start,end):
        rows=decode(image.mapper,image.pe.bytes_at_va(start,end-start),start)
        return {'window':{k:v for k,v in _window(image,start,end,'').items() if k!='boundary'},
                'instructions':[[int(row['va'],16)-base,bytes.fromhex(row['bytes']).hex().upper()] for row in rows]},rows
    def leaf_end(start):
        rows=image.mapper.decode_x64_subset(image.pe.bytes_at_va(start,128),start,stop_offset=128)
        terminal=next((r for r in rows if r['text']=='ret' or r['text'].startswith('jmp ')),None)
        if terminal is None:raise RouteRefused('scalar-param:unterminated-leaf')
        return int(terminal['va'],16)+len(bytes.fromhex(terminal['bytes']))
    programs={}
    for name,method in p['methods'].items():
        if set(method) != {'methodIndex','pointerRva','window','instructions'}: raise RouteRefused('long-param:method-extra-claims')
        fresh=_method_row(image,[method['methodIndex'],p['wrapperName'],name,method['pointerRva']]);start=base+fresh[3]
        end=build.body.extents.get(start)
        if name=='Deserialize':end=start+build.body.body(p['wrapperName'],name).size
        if end is None:end=leaf_end(start)
        value,rows=record(start,end);method.update(methodIndex=fresh[0],pointerRva=fresh[3],**value);programs[name]=rows
    des=programs['Deserialize'];targets=[base+p['methods']['set___'+m.name+'__']['pointerRva'] for m in wrapper.members]
    count,reads,writes,_=select_calls(des,4,targets)
    declaration=lambda rows:[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in rows]
    call=lambda row:[*declaration([row])[0],int(row['text'].split()[1],16)-base]
    p['memberCountInstruction']=declaration([count])[0];previous=des.index(count)
    if len(p['orderedReads'])!=4: raise RouteRefused('long-param:read-claims')
    for read,write,m,claim in zip(reads,writes,wrapper.members,p['orderedReads']):
        if set(claim)!={'name','declaredType','setterMethodIndex','readCall','setterCall','readerSetup','returnToSetter'}:
            raise RouteRefused('long-param:read-extra-claims')
        a=des.index(read);b=des.index(write)
        reader_arg=b'\x48\x8b\xce' if bytes.fromhex(count['bytes'])==b'\x80\x7c\x24\x30\x04' else b'\x48\x8b\xcf'
        setup=[r for r in des[previous+1:a] if bytes.fromhex(r['bytes']) in (b'\x48\x8b\x33',b'\x48\x8b\x3b',b'\x48\x8b\x1b',reader_arg)]
        claim.update(setterMethodIndex=m.method_index,readCall=call(read),setterCall=call(write),readerSetup=declaration(setup),returnToSetter=declaration(des[a+1:b]));previous=b
        prefix=b'\x48\x89\x51' if m.name=='path' else b'\x48\x89\x50' if m.name=='constValue' and width==8 else b'\x89\x50'
        stores=[bytes.fromhex(r['bytes']) for r in programs['set___'+m.name+'__'] if bytes.fromhex(r['bytes']).startswith(prefix)]
        if len(stores)!=1 or len(stores[0])!=len(prefix)+1: raise RouteRefused('long-param:owned-field-store')
        p['ownedFieldSlots'][m.name]=stores[0][-1]
    for key,read in (('constantSource',reads[0]),('int32Source',reads[1])):
        allowed={'window','instructions'} | ({'typedContext','registeredMethod','registeredEntry','actualEqualsRegistered','advance'} if leaf and key=='constantSource' else set())
        if set(out[key])-allowed: raise RouteRefused('long-param:source-extra-claims')
        start=int(read['text'].split()[1],16);value,rows=record(start,build.body.extents[start]);out[key].update(value)
        if key=='constantSource' and 'advance' in out[key]:
            from scripts.game_data.il2cpp.unwind_chains import read_exception_directory,UnwindChainIndex
            calls=[int(r['text'].split()[1],16)-base for r in rows if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
            if len(calls)!=(2 if width==4 else 1):raise RouteRefused('scalar-param:advance-call-count')
            calls=calls[-1:]
            rva,size,raw=read_exception_directory(image.pe)
            unwind=UnwindChainIndex(raw,lambda r,n:image.pe.bytes_at_va(base+r,n),table_rva=rva,image_size=size)
            ranges=sorted(tuple(r['runtimeTriple'][:2]) for r in unwind.family(calls[0])['ranges'])
            end=unwind.entries[calls[0]][1]
            for a,b in ranges:
                if a==end:end=b
            out[key]['advance']={'pointerRva':calls[0],'window':record(base+calls[0],base+end)[0]['window'],
                'fragmentWindows':[record(base+a,base+b)[0]['window'] for a,b in ranges if a!=calls[0]]}
    loads=[r for r in programs['.ctor'] if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d']
    if len(loads)!=1: raise RouteRefused('long-param:allocation-context-load')
    p['allocationContext']=derive_typed_usage_context(image,int(loads[0]['va'],16)-base,label='longParam')
    out['nativeInputs']={k:build.inputs[k] for k in contract['nativeInputs']}
    out['schema']=contract['schema'].rsplit('.',1)[0]+('.v3' if contract['schema'].startswith('endfield.levelscript-spline-ptr-native.') else '.v2')
    out['dependencies']=[{'role':'pooledStringSource','path':'memorypack_pooled_string_reader_native.json'}]
    if leaf:
        from scripts.game_data.il2cpp.generic_entries import GenericEntries
        l=out['leaf']
        if set(l)!={'typeDefinition','typeName','fieldName','fieldType','fieldKind','rawSize','wrapperTypeDefinition','wrapperName','methods'}:
            raise RouteRefused('scalar-param:leaf-extra-claims')
        if set(l['methods'])!={'GetValue','set___'+l['fieldName']+'__'}:raise RouteRefused('scalar-param:leaf-method-claims')
        l['typeDefinition']=_type_definition(image,l['typeName'])
        lw=build.wrappers[l['wrapperName']];l['wrapperTypeDefinition']=lw.type_definition
        for name,method in l['methods'].items():
            fresh=_method_row(image,[method['methodIndex'],l['wrapperName'],name,method['pointerRva']]);start=base+fresh[3]
            end=build.body.extents.get(start)
            if end is None:end=leaf_end(start)
            value,_=record(start,end);method.update(methodIndex=fresh[0],pointerRva=fresh[3],**value)
        loads=[r for r in des[des.index(count)+1:des.index(reads[0])] if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x15']
        if len(loads)!=1:raise RouteRefused('scalar-param:constant-context-load')
        source=out['constantSource'];source['typedContext']=derive_typed_usage_context(image,int(loads[0]['va'],16)-base,label='scalarParam')
        source['registeredMethod']=source['typedContext']['methodSpec'][0]
        entry=GenericEntries(image).resolve(source['registeredMethod'],[],[l['typeName']])
        source['registeredEntry']=json.loads(json.dumps(entry));source['actualEqualsRegistered']=entry['pointer']==base+source['window']['startRva']
    out['evidenceBoundary']['exact']='Ordinary typed scalar constant source/cursor and four-field owned Param composition; the path consumes a signed StringPool index through the independently authenticated BeyondReadString clone.'
    out['evidenceBoundary']['conditional']='Selected default generated wrapper, normal allocator/metadata initialization/barrier, compatible disjoint reader/storage and buffered scalar path. String paths select the initialized pool-present branch; non-sentinel paths require the independently supplied matching exported StringPool. Native pool instance/file identity and live selection are not observed.'
    return out


def regenerate_param_value(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    """Re-derive selected Int32 evaluator entries and the typed wrapper view."""
    from scripts.game_data import levelscript_param_value_bridge as bridge
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    if set(contract)!={'schema','status','nativeInputs','evidenceBoundary','entries','wrapper'}:
        raise RouteRefused('param-value:unsupported-claims')
    if set(contract['entries'])!={'value','getterPredicate','tryConstant'}:raise RouteRefused('param-value:entry-roles')
    image=build.image;out=copy.deepcopy(contract);base=image.pe.image_base;index=image.body_index;specs={}
    for role,record in out['entries'].items():
        if set(record)!={'definition','methodSpecIndex','methodSpec','window','instructions'}:raise RouteRefused('param-value:entry-claims')
        _,type_name,method_name=record['definition'];definition=_type_definition(image,type_name)
        image_name=image.metadata.string(image.metadata.images[image.owners[definition]].name_index)
        key={'getterPredicate':'predicate','tryConstant':'tryValue'}.get(role,role)
        specs[key]={'type':type_name,'image':image_name,'method':method_name,'classArguments':['Int32'] if key=='predicate' else [],
            'methodArguments':[] if key=='predicate' else ['Int32'],'callAbi':'instance' if key=='predicate' else 'static',**bridge.prototype_tokens(key)}
    selected=bridge.named_entries(image,specs,NativeReferenceContext(image),primitive_name='Int32',primitive_kind=8)
    def record_rows(rows):return {'window':{k:v for k,v in bridge.window(rows).items() if k!='instructionCount'},'instructions':rows}
    generics=GenericEntries(image)
    for role,record in out['entries'].items():
        key={'getterPredicate':'predicate','tryConstant':'tryValue'}.get(role,role);entry=selected[key];start=base+entry['pointerRva']
        rows=bridge.decode_rows(index,start,64 if key=='predicate' else index._extent(start))
        if key=='predicate':rows=rows[:8]
        elif key=='tryValue':rows=rows[:next(n for n,r in enumerate(rows) if bytes.fromhex(r[1])==b'\xc3')+1]
        record.update(definition=[entry['methodIndex'],*record['definition'][1:]],methodSpecIndex=entry['methodSpecIndex'],
            methodSpec=list(generics.specs[entry['methodSpecIndex']]),**record_rows(rows))
    wrapper=out['wrapper']
    if set(wrapper)!={'type','holder','holderOffset','wrappedType','slots','methods'} or set(wrapper['methods'])!={'GetValue','set___constValue__','set___idRef__','set___paramSource__'}:
        raise RouteRefused('param-value:wrapper-claims')
    definition=_type_definition(image,wrapper['type']);owner=image.metadata.types[definition]
    wrapper['holderOffset']=protocol.runtime_type_field_offsets(image.metadata,image.pe,image.registration,definition)[wrapper['holder']]
    for name,record in wrapper['methods'].items():
        if set(record)!={'definition','window','instructions'}:raise RouteRefused('param-value:wrapper-method-claims')
        methods=[m for m in image.metadata.methods_for(owner) if image.metadata.string(m.name_index)==name]
        if len(methods)!=1:raise RouteRefused('param-value:wrapper-method-count')
        method=methods[0];start=image.method_pointer_va(method)
        rows=bridge.decode_rows(index,start,5 if name=='GetValue' else index._extent(start))
        record.update(definition=[method.index,wrapper['type'],name],**record_rows(rows))
    wrapper['slots']={name:bytes.fromhex(wrapper['methods']['set___'+name+'__']['instructions'][6][1])[-1] for name in ('constValue','idRef','paramSource')}
    out['nativeInputs']={k:build.inputs[k] for k in contract['nativeInputs']}
    return out


def regenerate_primitive_param(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    from scripts.game_data.memorypack.primitive_param import derive_parameter
    primitive=_PRIMITIVE_SCHEMAS[contract['schema']]
    wire='Vector'+primitive[-1] if primitive in ('vector2','vector3') else primitive
    owner=importlib.import_module(f'scripts.game_data.levelscript_{primitive}_param_native')
    if (set(contract) != {'schema','status','codecKind','nativeInputs','evidenceBoundary','proof'}
            or (contract['schema'],contract['status'],contract['codecKind']) != (owner.SCHEMA,'exact-current-build','Param<'+wire+'>')):
        raise RouteRefused('primitive-param:identity-or-unsupported-claims')
    proof=derive_parameter(build.image,build.inputs,primitive)
    if proof.pop('status')!='validated':raise RouteRefused('primitive-param:unvalidated-source')
    fresh={'schema':owner.SCHEMA,'status':'exact-current-build','codecKind':'Param<'+wire+'>','nativeInputs':dict(build.inputs),
           'evidenceBoundary':proof.pop('evidenceBoundary'),'proof':proof}
    def shape(old,new,path='$'):
        if type(old) is not type(new):raise RouteRefused(f'primitive-param:claim-shape:{path}')
        if isinstance(old,dict):
            if old.keys()!=new.keys():raise RouteRefused(f'primitive-param:unsupported-claims:{path}')
            for key in old:shape(old[key],new[key],path+'.'+key)
        elif isinstance(old,list):
            if len(old)!=len(new):raise RouteRefused(f'primitive-param:claim-count:{path}')
            for n,(left,right) in enumerate(zip(old,new)):shape(left,right,f'{path}[{n}]')
    shape(contract,fresh)
    return fresh


def regenerate_environment_enable(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    """Keep historical spans separate from the parent and typed child proofs."""
    core=copy.deepcopy(contract);child=core.pop('pointedStruct')
    if (set(child)!={'typeDefinition','wrapperName','wrappedType','fields','methods','codeWindows'}
            or child['wrapperName']!='Beyond.MemoryPack.Beyond_Gameplay_Core_EnvironmentVolumePtrForMemoryPack'
            or child['wrappedType']!='Beyond.Gameplay.Core.EnvironmentVolumePtr' or child['fields']!=[['id','ulong']]
            or len(child['methods'])!=2 or len(child['codeWindows'])!=2):
        raise RouteRefused('environment-enable:pointed-claims')
    out=regenerate_formatter(core,build);wrapper=build.wrappers[child['wrapperName']]
    if (wrapper.wrapped_type!=child['wrappedType'] or wrapper.inherited_members
            or [[m.name,m.declared_type] for m in wrapper.members]!=child['fields']):
        raise RouteRefused('environment-enable:pointed-declarations')
    methods=[_method_row(build.image,row) for row in child['methods']];windows=[];base=build.image.pe.image_base
    expected=[child['wrapperName'],child['wrapperName']+'+'+child['wrapperName'].rsplit('.',1)[-1]+'Formatter']
    for name,method,old in zip(expected,methods,child['codeWindows'],strict=True):
        pointer=base+method[3]
        if method[1:3]!=[name,'Deserialize'] or not old['boundary'].startswith('complete ') or build.body.chained_fragments.get(pointer):
            raise RouteRefused('environment-enable:pointed-method-boundary')
        windows.append(_window(build.image,pointer,build.body.extents[pointer],old['boundary']))
    out['pointedStruct']={**child,'typeDefinition':wrapper.type_definition,'methods':methods,'codeWindows':windows}
    return out


def regenerate(contract: dict[str, Any], build: Build) -> dict[str, Any]:
    if contract.get('schema')=='endfield.levelscript-null-param-native.v1':
        from scripts.game_data.levelscript_null_param_native import _check_contract
        from scripts.game_data.memorypack.null_param import derive
        try:_check_contract(contract)
        except (KeyError,TypeError,ValueError) as error:raise RouteRefused('null-param:component-shape:'+str(error)) from error
        out=copy.deepcopy(contract);out['nativeInputs']=build.inputs
        for row in out['components']:row['proof']=derive(build.image,build.inputs,row['valueType'])
        return out
    if contract.get('schema')=='endfield.levelscript-camera-target-param-native.v1':
        from scripts.game_data.levelscript_camera_target_param_native import SCHEMA,KIND,VALUE_TYPE
        from scripts.game_data.memorypack.inlined_integer_param import derive
        if (set(contract)!={'schema','status','nativeInputs','codecKind','valueType','proof'}
                or (contract['schema'],contract['status'],contract['codecKind'],contract['valueType'])!=(SCHEMA,'exact-current-build',KIND,VALUE_TYPE)):
            raise RouteRefused('camera-target-param:component-shape')
        return {**copy.deepcopy(contract),'nativeInputs':build.inputs,'proof':derive(build.image,build.inputs,VALUE_TYPE)}
    if contract.get('schema')=='endfield.levelscript-environment-enable-native-contract.v1':
        return regenerate_environment_enable(contract,build)
    if contract.get('schema') in ('endfield.levelscript-enum-param-native.v1','endfield.levelscript-byte-enum-param-native.v1'):
        from scripts.game_data.memorypack.primitive_param import derive_parameter
        if set(contract)!={'schema','status','nativeInputs','components','evidenceBoundary'}:raise RouteRefused('enum-param:auxiliary-claims')
        out=copy.deepcopy(contract);out['nativeInputs']=build.inputs
        for row in out['components']:
            if set(row)!={'codecKind','wrappedType','proof'} or not row['wrappedType'].startswith('Beyond.Gameplay.Actions.Param`1<') or not row['wrappedType'].endswith('>'):
                raise RouteRefused('enum-param:component-claims')
            row['proof']=derive_parameter(build.image,build.inputs,'int',value_type=row['wrappedType'][len('Beyond.Gameplay.Actions.Param`1<'):-1],**({'enum_byte':True} if contract['schema']=='endfield.levelscript-byte-enum-param-native.v1' else {}))
        return out
    if contract.get('schema') == 'endfield.levelscript-route-deserialize-native.v1':
        return regenerate_typed_routes(typed_route_template(contract,build),build)
    if contract.get('schema') == 'endfield.levelscript-param-output-native.v1':
        from scripts.game_data.memorypack.output_param import derive_output
        if set(contract)!={'schema','status','nativeInputs','components','evidenceBoundary'}:
            raise RouteRefused('param-output:auxiliary-claims')
        out=copy.deepcopy(contract);out['nativeInputs']=build.inputs
        for row in out['components']:
            if set(row)!={'codecKind','wrappedType','proof'}:raise RouteRefused('param-output:component-claims')
            row['proof']=derive_output(build.image,build.inputs,row['wrappedType'])
        return out
    if contract.get('schema') in ('endfield.levelscript-route-deserialize-native.v2','endfield.levelscript-route-deserialize-native.v5','endfield.levelscript-route-deserialize-native.v6'):return regenerate_typed_routes(contract,build)
    if contract.get('schema') in _PRIMITIVE_SCHEMAS:return regenerate_primitive_param(contract,build)
    if contract.get('schema')=='endfield.levelscript-param-value-native.v1':return regenerate_param_value(contract,build)
    if contract.get('schema','').rsplit('.',1)[0] in ('endfield.levelscript-long-param-native','endfield.levelscript-gameplay-tag-param-native','endfield.levelscript-water-volume-ptr-param-native','endfield.levelscript-environment-volume-ptr-param-native','endfield.levelscript-spline-ptr-native'):
        return regenerate_scalar_param(contract, build)
    if contract.get('schema') == 'endfield.levelscript-task-condition-native.v1':
        return regenerate_condition_identity(contract, build)
    if contract.get('schema') == 'endfield.levelscript-settlement-followon-native-contract.v1':
        return regenerate_single_param_routes(contract, build)
    if contract.get('schema') == 'endfield.levelscript-header-native-contract.v1':
        return regenerate_header_routes(contract, build)
    if contract.get('schema') == 'endfield.levelscript-getter-int-native-contract.v1':
        return regenerate_getter_int(contract, build)
    if contract.get('schema') == 'endfield.levelscript-send-lua-event1-native-contract.v1':
        return regenerate_instance_route(contract, build)
    if contract.get('schema') in ('endfield.levelscript-reset-summon-team-ai-native-contract.v1',
                                 'endfield.levelscript-npc-atmospheric-cluster-native-contract.v1'):
        return regenerate_catalog_route(contract, build)
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
    if contract.get('schema')=='endfield.levelscript-environment-enable-native-contract.v1':
        from scripts.game_data.levelscript_environment_enable_native import validate_environment_enable_native_contract
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/filename;path.write_text(json.dumps(contract),encoding='utf8')
            audit=validate_environment_enable_native_contract(contract_path=path,game_root=build.image.metadata_path.parent.parent.parent)
        if audit.get('status')!='validated':raise RouteRefused(f'environment-enable:consumer-validation:{audit}')
        return
    if contract.get('schema') in ('endfield.levelscript-enum-param-native.v1','endfield.levelscript-byte-enum-param-native.v1'):
        from scripts.game_data.levelscript_enum_param_native import validate_enum_param_native_contract
        if contract['schema']=='endfield.levelscript-byte-enum-param-native.v1':
            from scripts.game_data.levelscript_byte_enum_param_native import validate_byte_enum_param_native_contract as validate_enum_param_native_contract
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/filename;path.write_text(json.dumps(contract),encoding='utf8')
            audit=validate_enum_param_native_contract(contract_path=path,gameassembly=build.image.gameassembly,metadata=build.image.metadata_path)
        if audit.get('status')!='validated':raise RouteRefused(f'enum-param:consumer-validation:{audit}')
        return
    if contract.get('schema') == 'endfield.levelscript-param-output-native.v1':
        from scripts.game_data.levelscript_param_output_native import validate_param_output_native_contract
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/filename;path.write_text(json.dumps(contract),encoding='utf8')
            audit=validate_param_output_native_contract(contract_path=path,gameassembly=build.image.gameassembly,metadata=build.image.metadata_path)
        if audit.get('status')!='validated':raise RouteRefused(f'param-output:consumer-validation:{audit}')
        return
    if contract.get('schema') in ('endfield.levelscript-route-deserialize-native.v2','endfield.levelscript-route-deserialize-native.v5','endfield.levelscript-route-deserialize-native.v6'):
        from scripts.game_data.levelscript_route_deserialize_native import validate
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/filename; path.write_text(json.dumps(contract),encoding='utf8')
            audit = validate(contract_path=path,gameassembly=build.image.gameassembly,metadata=build.image.metadata_path)
        if audit.get('status') != 'validated':raise RouteRefused(f'typed-routes:consumer-validation:{audit}')
        return
    if contract.get('schema') in _PRIMITIVE_SCHEMAS:
        primitive=_PRIMITIVE_SCHEMAS[contract['schema']]
        validator=getattr(importlib.import_module(f'scripts.game_data.levelscript_{primitive}_param_native'),f'validate_{primitive}_param_native_contract')
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/filename;path.write_text(json.dumps(contract),encoding='utf-8')
            audit=validator(contract_path=path,gameassembly=build.image.gameassembly,metadata=build.image.metadata_path)
        if audit['status']!='validated':raise RouteRefused(f'primitive-param:consumer-validation:{audit}')
        return
    if contract.get('schema')=='endfield.levelscript-param-value-native.v1':
        from scripts.game_data.levelscript_param_value_native import validate
        validate(build.image,contract)
        gate=check_installed_native_inputs(build.inputs['GameAssembly.dll'],build.inputs['global-metadata.dat'],gameassembly=build.image.gameassembly,metadata=build.image.metadata_path)
        if gate.status!='validated':raise RouteRefused(f'param-value:after-inputs:{gate.status}:{gate.detail}')
        if _sha256_upper((build.image.gameassembly.parent/'UnityPlayer.dll').read_bytes())!=build.inputs['UnityPlayer.dll']:raise RouteRefused('param-value:after-inputs:UnityPlayer.dll:mismatched')
        return
    if contract.get('schema') == 'endfield.levelscript-long-param-native.v2':
        from scripts.game_data import levelscript_long_param_native as owner
        from scripts.game_data.memorypack.pooled_source_helper import validate_on_image
        strings=validate_on_image(build.image,build.image.pe.image_base+contract['parameter']['orderedReads'][-1]['readCall'][2],build.inputs)
        owner._composition(build.image, contract, strings)
        gate = check_installed_native_inputs(build.inputs['GameAssembly.dll'], build.inputs['global-metadata.dat'],
            gameassembly=build.image.gameassembly, metadata=build.image.metadata_path)
        if gate.status != 'validated': raise RouteRefused(f'long-param:after-inputs:{gate.status}:{gate.detail}')
        if _sha256_upper((build.image.gameassembly.parent/'UnityPlayer.dll').read_bytes()) != build.inputs['UnityPlayer.dll']:
            raise RouteRefused('long-param:after-inputs:UnityPlayer.dll:mismatched')
        return
    scalar_owners={'endfield.levelscript-spline-ptr-native.v3':('levelscript_spline_ptr_native','Beyond.Gameplay.Core.SplinePtr'),
                   'endfield.levelscript-gameplay-tag-param-native.v2':('levelscript_gameplay_tag_param_native','Beyond.Gameplay.Core.GameplayTag'),
                   'endfield.levelscript-water-volume-ptr-param-native.v2':('levelscript_water_volume_ptr_param_native','Beyond.Gameplay.Core.WaterVolumePtr'),
                   'endfield.levelscript-environment-volume-ptr-param-native.v2':('levelscript_environment_volume_ptr_param_native','Beyond.Gameplay.Core.EnvironmentVolumePtr')}
    if contract.get('schema') in scalar_owners:
        from scripts.game_data.memorypack import pooled_source_helper,scalar_param_native
        module,type_name=scalar_owners[contract['schema']];owner=importlib.import_module('scripts.game_data.'+module)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/filename;path.write_text(json.dumps(contract))
            scalar_param_native.read_scalar_contract(path,schema=owner.SCHEMA,type_name=type_name,codec_kind='Param<'+type_name.rsplit('.',1)[-1]+'>')
        strings=pooled_source_helper.validate_on_image(build.image,build.image.pe.image_base+contract['parameter']['orderedReads'][-1]['readCall'][2],build.inputs)
        scalar_param_native._composition(build.image,contract,strings,owner.SOURCE_PROOF,module)
        gate=check_installed_native_inputs(build.inputs['GameAssembly.dll'],build.inputs['global-metadata.dat'],gameassembly=build.image.gameassembly,metadata=build.image.metadata_path)
        if gate.status!='validated':raise RouteRefused(f'scalar-param:after-inputs:{gate.status}:{gate.detail}')
        if _sha256_upper((build.image.gameassembly.parent/'UnityPlayer.dll').read_bytes())!=build.inputs['UnityPlayer.dll']:raise RouteRefused('scalar-param:after-inputs:UnityPlayer.dll:mismatched')
        return
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
    owners={'levelscript_reset_summon_team_ai_native':'codecs.levelscript.reset_summon_team_ai',
            'levelscript_npc_atmospheric_cluster_native':'codecs.levelscript.npc_atmospheric_cluster'}
    module=importlib.import_module('scripts.game_data.'+owners.get(Path(filename).stem,Path(filename).stem))
    shape_reader=getattr(module,'_contract',None)
    validator=getattr(module,'_validate_native',None)
    if shape_reader is None or validator is None:
        raise RouteRefused('consumer-validation:shared _contract/_validate_native adapter unavailable')
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/filename
        path.write_text(json.dumps(contract),encoding='utf-8')
        checked=shape_reader(path)
        validator(build.image,checked)


def needs_regeneration(contract: dict[str, Any], inputs: dict[str, str], *, explicit=False) -> bool:
    """Include every pinned block; a current outer pin cannot hide old children."""
    pins=native_pins(contract)
    return bool(pins) and (explicit or any(inputs.get(p['file'],'').upper()!=p['sha256'] for p in pins))


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
        if not needs_regeneration(c,inputs,explicit=bool(args.only)):continue
        row={'contract':path.name,'shape':shape(c),'written':False}
        try:
            candidate=regenerate(c,build)
            validate_candidate(path.name,candidate,build)
            row['status']='proved'
            if args.write:
                path.write_bytes((json.dumps(candidate,indent=2,ensure_ascii=False).replace('\n','\r\n')+'\r\n').encode('utf-8'))
                row['written']=True
        except (ValueError,KeyError,IndexError,TypeError,ModuleNotFoundError,RuntimeError) as exc:
            row.update(status='refused',reason=f'{type(exc).__name__}:{exc}')
        results.append(row)
        print(f'{path.name}: {row["status"]} {row.get("reason", "")[:700]}',flush=True)
    report={'nativeInputs':inputs,'counts':dict(Counter(r['status'] for r in results)),'results':results}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'counts':report['counts'],'written':sum(r['written'] for r in results),'report':str(args.report)}))
    return 1 if any(r['status']=='refused' for r in results) else 0


if __name__=='__main__':
    raise SystemExit(main())
