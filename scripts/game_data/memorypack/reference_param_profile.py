"""Derive selected eager wrapper registration and formatter composition data.

Raw usage-cell references only select candidate windows. The existing exact
registration and composition validators authenticate every returned candidate.
This derives versioned declaration data, not a live formatter selection.
"""
from __future__ import annotations

import hashlib
import struct

from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
from scripts.game_data.il2cpp.formatter_composition import (
    derive_typed_usage_context, validate_registered_formatter_composition,
)
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.native_cell_references import selected_qword_reference_candidates
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.memorypack.wrapper_members import derive_from_image, INSTANCE_FIELD_NAMES

LABEL = 'referenceParamProfile'


def _one(rows, label):
    rows = list(rows)
    if len(rows) != 1:
        raise ValueError(f'{LABEL}.{label}: expected=1 actual={len(rows)}')
    return rows[0]


def _window(image, start, end, **extra):
    if not 0 <= start < end < 1 << 32:
        raise ValueError(LABEL+'.window-domain')
    raw = image.pe.bytes_at_va(image.pe.image_base+start, end-start)
    return dict(startRva=start, endRva=end, sha256=hashlib.sha256(raw).hexdigest().upper(), **extra)


def _method_row(image, method):
    return [method.index, image.type_name(method.declaring_type),
            image.metadata.string(method.name_index), image.method_pointer_va(method)-image.pe.image_base]


def _target(image, row, opcode):
    raw = bytes.fromhex(row['bytes'])
    if len(raw) != 5 or raw[0] != opcode:
        raise ValueError(LABEL+'.relative-transfer')
    return int(row['va'], 16)-image.pe.image_base+5+int.from_bytes(raw[1:], 'little', signed=True)


def _key_cells(image, pointer):
    """Only raw-backed cells containing exact unresolved type usage words."""
    pe, registration = image.pe, image.registration
    table = pe.bytes_at_va(int(registration['types'], 16), registration['typesCount']*8)
    indices = [i for i, (value,) in enumerate(struct.iter_unpack('<Q', table)) if value == pointer]
    if not indices:
        raise ValueError(LABEL+'.original-type-not-registered')
    cells = set()
    for index in indices:
        encoded = struct.pack('<Q', (2 << 29) | (index << 1) | 1)
        for section in pe.sections:
            if section['characteristics'] & 0x20000000:
                continue
            raw = pe.buf[section['rawPointer']:section['rawPointer']+section['rawSize']]
            at = raw.find(encoded)
            while at >= 0:
                if (section['virtualAddress']+at) % 8 == 0:
                    cells.add(section['virtualAddress']+at)
                at = raw.find(encoded, at+1)
    if not 0 < len(cells) <= 256:
        raise ValueError(f'{LABEL}.key-cell-count: actual={len(cells)}')
    return cells


def _derive_registration(image, original_type, wrapper, getter):
    base, pe, metadata = image.pe.image_base, image.pe, image.metadata
    pointer = pe.u64_at_va(int(image.registration['types'], 16)+getter.return_type*8)
    if runtime_type_name(pe, metadata, pointer) != original_type:
        raise ValueError(LABEL+'.getter-original-type')
    candidates = selected_qword_reference_candidates(pe, _key_cells(image, pointer))
    helpers = {}
    for key, owner, name in (
        ('typeFromHandle', 'System.Type', 'GetTypeFromHandle'),
        ('registerWrap', 'MemoryPack.MemoryPackFormatterProvider', 'RegisterWrap'),
    ):
        td = image.named_types[owner]
        method = _one((m for m in metadata.methods_for(td) if metadata.string(m.name_index) == name), key)
        helpers[key] = _method_row(image, method)
    proved = []
    diagnostics = []
    for candidate in candidates:
        if not candidate['rawHex'].startswith('488b05'):
            continue
        key_site = candidate['siteRva']
        # Eight bounded instructions precede the selected original-key load.
        raw_prefix = pe.bytes_at_va(base+max(0, key_site-96), min(key_site, 96))
        offset = raw_prefix.find(b'\x48\x8b\x0d')
        while offset >= 0:
            start = max(0, key_site-96)+offset
            try:
                rows = image.mapper.decode_x64_subset(pe.bytes_at_va(base+start, 192), base+start, stop_offset=192)[:18]
                if len(rows) != 18 or int(rows[8]['va'], 16)-base != key_site:
                    raise ValueError('key-load-not-in-slot-eight')
                end = int(rows[-1]['va'], 16)-base+len(bytes.fromhex(rows[-1]['bytes']))
                usages = [derive_typed_usage_context(image, int(rows[i]['va'], 16)-base, label=LABEL)
                          for i in (0, 5, 8)]
                calls = {key: _target(image, rows[i], 0xe8)
                         for i, key in ((1, 'allocation'), (4, 'objectCheck'), (7, 'constructor'),
                                        (12, 'typeFromHandle'), (17, 'registerWrap'))}
                thunk_start = calls['constructor']
                thunk = image.mapper.decode_x64_subset(pe.bytes_at_va(base+thunk_start, 32),
                                                       base+thunk_start, stop_offset=32)[:2]
                thunk_end = int(thunk[-1]['va'], 16)-base+len(bytes.fromhex(thunk[-1]['bytes']))
                flow = dict(originalType=original_type, wrapperType=wrapper.name,
                            window=_window(image, start, end),
                            allocation=usages[0], constructor=usages[1], key=usages[2],
                            actualCalls=calls, helperMethods=helpers,
                            constructorThunk=dict(window=_window(image, thunk_start, thunk_end),
                                                  context=derive_typed_usage_context(image, thunk_start, label=LABEL),
                                                  sharedTargetRva=_target(image, thunk[1], 0xe9)))
                validate_eager_wrap_registration(image, flow, label=LABEL)
                proved.append(flow)
            except (ValueError, KeyError, IndexError, TypeError) as error:
                diagnostics.append(str(error)[:200])
            offset = raw_prefix.find(b'\x48\x8b\x0d', offset+1)
    unique = {row['window']['startRva']: row for row in proved}
    profile_diagnostics=[]
    if not unique:
        from scripts.game_data.il2cpp import formatter_inline_registration,formatter_direct_registration,formatter_stack_registration,formatter_checked_registration,formatter_checked_value_registration,formatter_guarded_registration,formatter_constructed_guarded_registration,formatter_key_receiver_registration,formatter_late_saved_registration
        for profile in (formatter_inline_registration,formatter_direct_registration,formatter_stack_registration,formatter_checked_registration,formatter_checked_value_registration,formatter_guarded_registration,formatter_constructed_guarded_registration,formatter_key_receiver_registration,formatter_late_saved_registration):
            try:
                row=profile.derive(image,original_type,wrapper.name,candidates,helpers)
                unique[row['window']['startRva']]=row
            except (ValueError,KeyError,IndexError,TypeError) as error:
                profile_diagnostics.append(profile.__name__.rsplit('.',1)[-1]+':'+str(error)[:1600])
    if len(unique) != 1:
        raise ValueError(f'{LABEL}.eager-window-count: original={original_type} wrapper={wrapper.name}'
            f' expected=1 actual={len(unique)} diagnostics={diagnostics[:4]+profile_diagnostics}')
    return next(iter(unique.values()))


def _getter_windows(image, owner, getter, *, owned_family=False, entry_prover=None):
    """Bound a leaf, exact owned getter tail, or explicitly selected family.

    The tail's target has metadata identity and full unwind ownership. This
    proves only registration/composition provenance: callers still prove the
    target's holder/cache program before using its result as a source join.
    """
    if type(owned_family)is not bool:raise ValueError(LABEL+'.getter-family-option')
    if entry_prover is not None and not callable(entry_prover):raise ValueError(LABEL+'.getter-entry-callable-only')
    pe=image.pe;entry=image.method_pointer_va(getter);base=pe.image_base
    if entry_prover is not None:
        if (owned_family or getter.declaring_type!=owner.index or getter.flags&16 or getter.parameter_count
                or image.metadata.string(getter.name_index)!='GetValue'):
            raise ValueError(LABEL+'.getter-entry-owned-instance')
        program=entry_prover(image,owner,getter);selected=program.get('selectedBytes',[]);at=entry
        if not selected:raise ValueError(LABEL+'.getter-entry-empty-program')
        for site,h in selected:
            raw=bytes.fromhex(h)
            if (type(site)is not int or site!=at or not 0<len(raw)<=15 or at+len(raw)>entry+128
                    or pe.bytes_at_va(site,len(raw))!=raw):
                raise ValueError(LABEL+'.getter-entry-exact-contiguous-bytes')
            at+=len(raw)
        if (bytes.fromhex(selected[-1][1])!=b'\xc3' or program.get('normalReturn')is not True
                or program.get('entryRspRestored')is not True or program.get('calleeCalls')!=0):
            raise ValueError(LABEL+'.getter-entry-complete-return-program')
        return [_window(image,entry-base,at-base)],dict(kind='owned-selected-getter-entry',
            entryMethod=_method_row(image,getter),entryProgram=program,physicalFunctionExtentProved=False,
            targetHolderSemanticsProved=False)
    if owned_family:
        if (getter.declaring_type!=owner.index or getter.flags&16 or getter.parameter_count
                or image.metadata.string(getter.name_index)!='GetValue'
                or entry-base not in image.unwind_index.entries):
            raise ValueError(LABEL+'.getter-family-owned-entry-or-abi')
        family=image.unwind_index.family(entry-base)
        windows=[_window(image,*part['runtimeTriple'][:2])for part in family['ranges']]
        if not any(w['startRva']==entry-base for w in windows):
            raise ValueError(LABEL+'.getter-family-missing-primary')
        return windows,dict(kind='owned-getter-family',entryMethod=_method_row(image,getter),
            family=family,targetHolderSemanticsProved=False,
            condition='Exact metadata-owned instance no-argument GetValue with full current unwind family. Caller must independently prove its returned representation, holder/cache/cast effects and complete selected return.')
    prefix=pe.bytes_at_va(entry,7)
    if prefix[:3]==b'\x33\xd2\xe9':
        target=entry+7+int.from_bytes(prefix[3:],'little',signed=True)
        names={'get_'+name for name in INSTANCE_FIELD_NAMES}
        candidates=[m for m in image.metadata.methods_for(owner)
            if image.metadata.string(m.name_index)in names
            and image.method_pointer_va(m)==target]
        named=_one(candidates,'getter-owned-tail-target')
        if (getter.flags&16 or named.flags&16 or getter.parameter_count
                or named.parameter_count or named.return_type!=getter.return_type
                or named.declaring_type!=getter.declaring_type):
            raise ValueError(LABEL+'.getter-owned-tail-abi')
        windows=[_window(image,entry-base,entry-base+7)]
        family=image.unwind_index.family(target-base)
        for part in family['ranges']:
            a,b=part['runtimeTriple'][:2];windows.append(_window(image,a,b))
        if not any(w['startRva']==target-base for w in windows[1:]):
            raise ValueError(LABEL+'.getter-owned-tail-entry')
        return windows,dict(kind='owned-zero-context-getter-tail',
            entryMethod=_method_row(image,getter),instructionHex=prefix.hex().upper(),
            targetMethod=_method_row(image,named),targetFamily=family,
            receiverPreserved=True,explicitContextZero=True,
            targetHolderSemanticsProved=False,physicalThunkExtentProved=False)
    leaf=decode_closed_leaf_entry(image.mapper,pe.bytes_at_va(entry,128),entry)
    end=max(int(r['va'],16)+len(bytes.fromhex(r['bytes']))for r in leaf['rows'])
    return [_window(image,entry-base,end-base)],None


def derive_pair(image, original_type, wrapper_name=None, *, owned_getter_family=False, getter_entry_prover=None):
    """Return independently validated registration/composition for an exact type.

    A non-leaf getter can opt into its actual unwind-owned family. That option
    authenticates physical provenance only; the caller must independently prove
    the getter's representation/holder semantics before composing a grammar.
    """
    metadata, pe = image.metadata, image.pe
    wrapper = _one((w for w in derive_from_image(image).values()
                    if w.wrapped_type == original_type and (wrapper_name is None or w.name == wrapper_name)),
                   'selected-wrapper')
    owner = metadata.types[wrapper.type_definition]
    getter = _one((m for m in metadata.methods_for(owner) if metadata.string(m.name_index) == 'GetValue'), 'getter')
    flow = _derive_registration(image, original_type, wrapper, getter)
    formatter_name = wrapper.name+'+'+wrapper.name.rsplit('.', 1)[-1]+'Formatter'
    formatter = image.named_types[formatter_name]
    deserialize = _one((m for m in metadata.methods_for(formatter)
                        if metadata.string(m.name_index) == 'Deserialize'), 'formatter-deserialize')
    section = metadata.sections['interfaceOffsets']
    start = section.offset+owner.interface_offsets_start*8
    pairs = list(struct.iter_unpack('<ii', metadata.buf[start:start+owner.interface_offsets_count*8]))
    interface = _one(((index, offset) for index, offset in pairs
                      if runtime_type_name(pe, metadata, pe.u64_at_va(int(image.registration['types'], 16)+index*8))
                      == 'Beyond.MemoryPack.IMemoryPackDeSerializeWrapper`1<'+original_type+'>'), 'owned-interface')
    windows,getter_proof=_getter_windows(image,owner,getter,owned_family=owned_getter_family,entry_prover=getter_entry_prover)
    for part in image.unwind_index.family(image.method_pointer_va(deserialize)-pe.image_base)['ranges']:
        a, b = part['runtimeTriple'][:2]
        windows.append(_window(image, a, b))
    spec = flow['constructor']['methodSpec']
    composition = dict(
        registrations=[dict(originalType=original_type, wrapperType=wrapper.name,
                            classInstantiation=spec[1], adapterTypeIndex=flow['allocation']['typeIndex'],
                            keyTypeIndex=flow['key']['typeIndex'],
                            constructorMethodSpecIndex=flow['constructor']['methodSpecIndex'], constructorMethodSpec=spec)],
        interfaces=[dict(originalType=original_type, wrapperType=wrapper.name,
                         wrapperDefinition=owner.index, interfaceTypeIndex=interface[0], interfaceOffset=interface[1],
                         getValueMethodIndex=getter.index, formatterDefinition=formatter.index,
                         formatterDeserializeMethodIndex=deserialize.index)],
        genericContexts=[ContextSymbols(image).context(image.named_types['Beyond.MemoryPack.GenericMemoryPackFormatter`2'].index)],
        methods=[_method_row(image, getter), _method_row(image, deserialize)], codeWindows=windows)
    validate_registered_formatter_composition(image, composition, label=LABEL)
    result=dict(registration=flow, composition=composition)
    if getter_proof is not None:result['getterEntryProof']=getter_proof
    return result


def derive_profile(image, value_type, *, integer_slots=None, initialized_header=False):
    result = derive_pair(image, 'Beyond.Gameplay.Actions.Param`1<'+value_type+'>')
    result['integerSlots'] = integer_slots
    if initialized_header:
        result['initializedHeader'] = True
    return result
