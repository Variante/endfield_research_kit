"""Current zero-member Finder source programs and canonical two-byte children.

CharacterTeamFinder keeps its separate owner. Complete selected concrete
reader/forwarder/header programs and both generic caller alternatives are
checked here, including both anonymous physical helpers, the byref terminal
jump, owned MVAR/provider contexts and concrete formatter slot five. The
actual helper entries differ from canonical Object registrations; named body
identities and runtime context inflation remain unresolved. Provider/lifecycle
and global effects retain explicit conditions. Target selection and complete
enclosing action/list/root composition are not observed or admitted.
"""
from __future__ import annotations
import hashlib
import json
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import method_parameter_owner, method_spec_usage_index
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts, _vtable
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.zero_wrapper_programs import (
    prove_buffered_header, prove_zero_wrapper_reader, prove_zero_wrapper_forwarder,
    prove_finder_short_union_prefix, prove_finder_case,
)
from scripts.game_data.il2cpp.reference_reader_programs import (
    prove_packable_byref_bridge, prove_read_value_byref_bridge, prove_terminal_entry_jump,
)
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack.packable_reference_sources import validate_packable_context, validate_packable_transfer
from scripts.game_data.memorypack.packable_byref_sources import validate_byref_contexts
from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
from scripts.game_data.memorypack.formatter_provider_sources import validate_provider_transfer
from scripts.game_data.memorypack.reference_conversion_sources import validate_formatter_dispatch

LABEL = 'buffSelectorZeroFinders'
SCHEMA = 'endfield.buff-selector-zero-finders-native-contract.v2'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_selector_zero_finders_native.json'


def _fail(check, expected, actual):
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract():
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    records = c.get('records', [])
    if (c.get('catalogContract') != 'levelscript_union_tags.json' or not records
            or set(c.get('dependencies', {})) != {'rootList', 'readValue', 'provider'}
            or not c.get('sharedReaders')
            or c.get('separateOwnerType') != 'Beyond.Gameplay.Core.Selector+CharacterTeamFinder+Data'
            or len({r['tag'] for r in records}) != len(records)
            or any(type(r['tag']) is not int or not 0 <= r['tag'] < 250
                or r['wrapper'].get('serializedMemberCount') != 0
                or r['wrapper'].get('inheritedMemberCount') != 0 for r in records)):
        _fail('contract-shape', 'distinct short tags and complete zero-member wrappers', records)
    return c


def _owned_rows(image, index, body):
    entry = image.pe.image_base + body['entryRva']
    if 'method' in body:
        image.validate_method_row(body['method'], label=LABEL)
        if body['entryRva'] != body['method'][3]: _fail('body-method-entry', body['method'][3], body['entryRva'])
    end = index.extents.get(entry)
    if end is None: _fail('owned-body', 'current unwind ownership', body['entryRva'])
    spans = sorted(set([(entry, end)] + [(at, at + size) for at, size in index.chained_fragments.get(entry, ())]))
    actual = [{'startRva': a-image.pe.image_base, 'endRva': b-image.pe.image_base} for a, b in spans]
    if actual != body['ownedPdataFragments']: _fail('complete-owned-fragments', body['ownedPdataFragments'], actual)
    merged = []
    for a, b in spans:
        if merged and merged[-1][1] == a: merged[-1][1] = b
        else: merged.append([a, b])
    windows = body['codeWindows']
    if [[w['startRva']+image.pe.image_base, w['endRva']+image.pe.image_base] for w in windows] != merged:
        _fail('complete-owned-window-coverage', merged, windows)
    image.check_windows(windows, label=LABEL)
    return [index._decode(a, b-a) for a, b in merged]


def _program(image, body, proof):
    image.check_windows(proof['codeWindows'], label=LABEL)
    image.check_instruction_windows(proof['program'], label=LABEL)
    rows = []
    for at, raw_hex in proof['program']:
        raw = bytes.fromhex(raw_hex)
        if not any(w['startRva'] <= at < at+len(raw) <= w['endRva'] for w in body['codeWindows']):
            _fail('selected-program-owner', body['entryRva'], [at, raw_hex])
        decoded = image.mapper.decode_x64_subset(raw, image.pe.image_base+at, stop_offset=len(raw))
        # The mapper deliberately lacks this ADD; its complete fixed encoding
        # is independently checked by the prefix grammar, not decoded as data.
        if raw == b'\x48\x03\xca':
            decoded = [{'va': hex(image.pe.image_base+at), 'bytes': raw.hex(), 'text': 'add rcx, rdx'}]
        if len(decoded) != 1 or 'db ' in decoded[0]['text']:
            _fail('selected-program-instruction', 'one understood complete instruction', [at, raw_hex, decoded])
        rows.append(decoded[0])
    if not proof['program'] or proof['codeWindows'] != [{
        **proof['codeWindows'][0], 'startRva': proof['program'][0][0],
        'endRva': proof['program'][-1][0]+len(bytes.fromhex(proof['program'][-1][1]))}]:
        _fail('selected-program-exact-window', 'one complete contiguous instruction window', proof)
    return rows


def _closed_context(image, entries, context, wrapper, identity, *, byref):
    cell, raw = image.nested_usage_cell(context, label=LABEL,
        load_prefixes=(b'\x4c\x8b\x05',) if byref else (b'\x48\x8b\x15',))
    spec_index = method_spec_usage_index(raw, image.registration['methodSpecsCount'], source=str(image.gameassembly), offset=cell)
    if spec_index != context['methodSpecIndex'] or list(entries.specs[spec_index]) != context['methodSpec']:
        _fail('selected-method-spec', context, spec_index)
    definition, class_inst, method_inst = entries.specs[spec_index]
    method = image.metadata.methods[definition]
    if (class_inst != -1 or image.type_name(method.declaring_type) != 'MemoryPack.MemoryPackReader'
            or image.metadata.string(method.name_index) != 'ReadPackable' or method.flags & 0x10
            or method.generic_container_index < 0):
        _fail('selected-read-packable-owner', 'instance generic Reader.ReadPackable', context)
    args = image.instantiations.resolve(method_inst).arguments
    if len(args) != 1 or len(context['arguments']) != 1: _fail('selected-wrapper-arity', 1, len(args))
    arg = bytes.fromhex(args[0].raw_type_record_hex)
    expected = context['arguments'][0]
    if (arg[10:12] != b'\x12\x00' or int.from_bytes(arg[:8], 'little') != wrapper['typeDefinition']
            or args[0].raw_type_record_hex.upper() != expected['rawTypeRecordHex'].upper()
            or expected['typeDefinition'] != wrapper['typeDefinition'] or expected['typeName'] != wrapper['wrapperName']):
        _fail('selected-closed-wrapper', wrapper['wrapperName'], expected)
    meta = image.metadata; section = meta.sections['genericContainers']; at = section.offset+method.generic_container_index*16
    if not section.offset <= at <= section.offset+section.size-16: _fail('generic-container-range', section, at)
    owner, count, is_method, start = struct.unpack_from('<iiii', meta.buf, at)
    reciprocal = method_parameter_owner(meta.buf, start, [m.generic_container_index for m in meta.methods], source=LABEL)
    if ((owner, count, is_method) != (definition, 1, 1)
            or reciprocal['methodIndex'] != definition or reciprocal['ordinal'] != 0):
        _fail('owned-method-parameter', [definition, 1, 1, 0], reciprocal)
    types = NativeReferenceContext(image); result = image.pe.bytes_at_va(types.type_pointer(method.return_type), 16)
    params = meta.parameters_for(method)
    if byref:
        if len(params) != 1 or result[10] != 1 or result[11] & 0x20 or types.type_name(method.return_type) != 'void':
            _fail('byref-overload-abi', 'instance void with one byref MVAR', {'context':context, 'returnTypeRecordHex':result.hex().upper(), 'parameterCount':len(params)})
        parameter = image.pe.bytes_at_va(types.type_pointer(params[0].type_index), 16)
        if parameter[10:12] != b'\x1e\x20' or int.from_bytes(parameter[:8], 'little') != start:
            _fail('byref-overload-owned-parameter', start, parameter.hex())
    elif params or result[10:12] != b'\x1e\x00' or int.from_bytes(result[:8], 'little') != start:
        _fail('value-return-overload-abi', 'instance owned MVAR return with no explicit parameters', context)
    registration_rows = [row for row in struct.iter_unpack('<iiii', entries.table) if row[0] == spec_index]
    if registration_rows: _fail('selected-closed-registration-gap', 'no compiled closed usage entry in this selected build', registration_rows)
    if (identity['methodDefinition'] != definition or identity['actualSourceTransferProved'] is not True
            or identity['matchedIndependentObjectEntry'] is not False):
        _fail('actual-physical-transfer-context-join', 'same declared overload and independently checked anonymous transfer', identity)
    return {'methodDefinition': definition, 'methodSpecIndex': spec_index, 'wrapperDefinition': wrapper['typeDefinition'],
        'overload': 'byref-void' if byref else 'value-return', 'actualPhysicalEntryRva': identity['calledEntryRva'],
        'actualPhysicalEntryMatchesIndependentObject': False, 'namedPhysicalBodyIdentity': 'unresolved',
        'actualSourceTransferProved': True, 'directClosedRegistrationPresent': False,
        'originalClosedRuntimeEntryInvocationProved': False, 'runtimeInflatedContextObserved': False}


def _shared_sources(image, index, entries, c):
    schemas = {'rootList': 'endfield.buff-timeline-root-list-native-contract.v1',
        'readValue': 'endfield.buff-timeline-read-value-native-contract.v3',
        'provider': 'endfield.buff-formatter-provider-native-contract.v1'}
    deps = {k: read_reviewed_contract(CONTRACTS_DIR/c['dependencies'][k], schema=s,
        status='exact-current-build', label=LABEL)[0] for k,s in schemas.items()}
    if any(d['nativeInputs'] != c['nativeInputs'] for d in deps.values()):
        _fail('shared-dependency-build', c['nativeInputs'], [d['nativeInputs'] for d in deps.values()])
    root, value, provider = (deps[k] for k in ('rootList','readValue','provider')); shared = c['sharedReaders']
    contexts = [root['packableContext'], value['readValueContext'], provider['providerContext'],
        shared['byrefPackableContext'], shared['byrefReadValueContext']]
    validate_generic_contexts(image, contexts, label=LABEL)
    owned_return = validate_read_value_context(image, value['readValueContext'], provider['providerContext'], entries, fail=_fail)
    return_context = validate_packable_context(image, root['packableContext'], owned_return['readerMethodDefinition'], entries, fail=_fail)
    byref_context = validate_byref_contexts(image, shared['byrefPackableContext'], shared['byrefReadValueContext'], entries, owned_return, fail=_fail)
    if any(root['packableCalls'][k] != value['calls'][k] for k in root['packableCalls']):
        _fail('shared-value-callees', root['packableCalls'], value['calls'])
    _owned_rows(image, index, shared['valuePackable'])
    owned_windows = [{k:w[k] for k in ('startRva','endRva','sha256')} for w in shared['valuePackable']['codeWindows']]
    if root['packableProgram']['codeWindows'] != owned_windows or shared['valuePackable']['entryRva'] != c['symbols']['readPackable']:
        _fail('same-actual-value-helper-owner', owned_windows, root['packableProgram']['codeWindows'])
    return_transfer = validate_packable_transfer(image, root['packableProgram'], root['packableCalls'], fail=_fail)
    rows = _owned_rows(image, index, shared['byrefPackable'])
    value_rows = _owned_rows(image, index, shared['byrefReadValue'])
    if len(rows) != 1 or len(value_rows) != 1 or shared['byrefPackable']['entryRva'] != c['symbols']['readPackableByref']:
        _fail('complete-byref-physical-owners', 'same single-fragment shim and target', shared['byrefPackable'])
    symbols = shared['symbols']
    if (any(symbols[k] != c['symbols'][k] for k in ('metadataInit','classInit'))
            or symbols['provider'] != provider['calledEntryRva'] or symbols['provider'] != value['calls']['wrapperGetFormatter']
            or symbols['formatterDispatch'] != root['packableCalls']['formatterDispatch']):
        _fail('byref-proved-provider-dispatch-join', 'same current checked physical helper dependencies', symbols)
    provider_transfer = validate_provider_transfer(image, provider['proof'], provider['calls'], fail=_fail)
    physical_symbols = {k: image.pe.image_base+v for k,v in symbols.items()}
    shim_transfer = prove_packable_byref_bridge(rows[0], context_init=physical_symbols['contextInit'],
        read_value_entry=image.pe.image_base+shared['byrefReadValueCalledEntryRva'], label=LABEL+'.byrefPackable')
    byref_transfer = prove_read_value_byref_bridge(value_rows[0], physical_symbols, label=LABEL+'.byrefReadValue')
    jumps = []; current = shared['byrefReadValueCalledEntryRva']; seen = set()
    if not 1 <= len(shared['entryTransfers']) <= 8: _fail('byref-entry-transfer-count', 'one to eight reviewed direct terminal jumps', shared['entryTransfers'])
    for t in shared['entryTransfers']:
        if t['entryRva'] != current or current in seen or t['window']['startRva'] != current or t['window']['endRva'] != current+5:
            _fail('byref-entry-transfer-chain', current, t)
        seen.add(current); image.check_windows([t['window']], label=LABEL)
        image.check_instruction_windows([[current, t['instructionHex']]], label=LABEL)
        decoded = image.mapper.decode_x64_subset(bytes.fromhex(t['instructionHex']), image.pe.image_base+current, stop_offset=5)
        if len(decoded) != 1: _fail('byref-entry-transfer-instruction', 'one complete jump', decoded)
        jumps.append(prove_terminal_entry_jump(decoded[0], image.pe.image_base+t['targetRva'], label=LABEL+'.entryJump'))
        current = t['targetRva']
    if current != shared['byrefReadValue']['entryRva']: _fail('byref-entry-terminal-owner', shared['byrefReadValue']['entryRva'], current)
    identities = {}
    for r in shared['independentPackableObjectEntries']:
        actual = entries.resolve(r['definition'], [], ['object'])
        if json.loads(json.dumps(actual)) != r['objectRegistration']:
            _fail('independent-packable-object-registration', r['objectRegistration'], actual)
        identities[r['definition']] = actual
    if set(identities) != {return_context['packableDefinition'], byref_context['packableDefinition']}:
        _fail('independent-overload-coverage', 'both checked overload definitions', identities)
    registration_slots = list(struct.iter_unpack('<iiii', entries.table))
    actual_entries = shared['actualCalledEntryRegistrations']
    if {r['rva'] for r in actual_entries} != {c['symbols']['readPackable'],c['symbols']['readPackableByref']} or any(r['registrations'] for r in actual_entries):
        _fail('physical-registration-gap-contract', 'both actual entries with zero generic registration rows', actual_entries)
    for r in actual_entries:
        found = [row for row in registration_slots if struct.unpack_from('<Q', entries.pointers, row[1]*8)[0] == image.pe.image_base+r['rva']]
        if found: _fail('current-physical-registration-gap', [], found[:16])
    physical_identities = {}
    for role, ctx in (('new',return_context),('existing',byref_context)):
        called = c['symbols']['readPackable' if role == 'new' else 'readPackableByref']
        if identities[ctx['packableDefinition']]['pointer'] == image.pe.image_base+called:
            _fail('actual-entry-differs-from-independent-object', 'distinct physical entries; named body identity unresolved', called)
        physical_identities[role] = {'methodDefinition':ctx['packableDefinition'], 'calledEntryRva':called,
            'matchedIndependentObjectEntry':False, 'actualSourceTransferProved':True}
    actual = entries.resolve(byref_context['readerDefinition'], [], ['object'])
    if (json.loads(json.dumps(actual)) != shared['independentReadValueObjectEntry']
            or actual['pointer'] == image.pe.image_base+shared['byrefReadValueCalledEntryRva']
            or shared['actualReadValueMatchedIndependentObject'] is not False):
        _fail('independent-byref-read-value-entry-gap', shared['independentReadValueObjectEntry'], actual)
    reference = read_reviewed_contract(CONTRACTS_DIR/value['dependencies']['reference'],
        schema='endfield.buff-timeline-reference-native-contract.v2', status='exact-current-build', label=LABEL)[0]
    if reference['nativeInputs'] != c['nativeInputs']: _fail('dispatch-dependency-build', c['nativeInputs'], reference['nativeInputs'])
    dispatch = validate_formatter_dispatch(image, reference['conversionPrograms']['formatterDispatch'],
        [r['formatter']['entryRva'] for r in c['records']], fail=_fail)
    if reference['conversionPrograms']['formatterDispatch']['program'][0][0] != symbols['formatterDispatch']:
        _fail('same-ordinary-formatter-dispatch-entry', symbols['formatterDispatch'], dispatch)
    return {'returnContext':return_context, 'byrefContext':byref_context, 'returnTransfer':return_transfer,
        'byrefPackableTransfer':shim_transfer, 'entryTransfers':jumps, 'byrefReadValueTransfer':byref_transfer,
        'providerTransfer':provider_transfer, 'ordinaryFormatterDispatch':dispatch,
        'identities':physical_identities, 'conditionalBothPhysicalReaderOutputPathsProved':True,
        'namedPhysicalBodyIdentities':'unresolved', 'runtimeInflatedContextsObserved':False}


def _validate_image(image, c, selector_native):
    catalog = read_reviewed_contract(CONTRACTS_DIR/c['catalogContract'], schema='endfield.levelscript-union-tags.v1', label=LABEL)[0]
    pins = c['nativeInputs']
    if (catalog['nativeInputs']['gameAssemblySha256'] != pins['GameAssembly.dll']
            or catalog['nativeInputs']['metadataSha256'] != pins['global-metadata.dat']):
        _fail('catalog-build', pins, catalog['nativeInputs'])
    declared = {r['tag']: r for r in catalog['families']['SelectorFinder']
        if r['memberCount'] == 0 and r['wrappedType'] != c['separateOwnerType']}
    if set(declared) != {r['tag'] for r in c['records']}: _fail('all-remaining-zero-finders', set(declared), c['records'])
    index = BodyIndex(image); wrappers = derive_from_image(image); entries = GenericEntries(image)
    shared = _shared_sources(image, index, entries, c)
    symbols = {k: image.pe.image_base+v for k, v in c['symbols'].items()}
    header_rows = _owned_rows(image, index, c['header'])
    if len(header_rows) != 2: _fail('header-fragments', 2, len(header_rows))
    header = prove_buffered_header(*header_rows, symbols, label=LABEL+'.header')
    _owned_rows(image, index, c['parent'])
    prefix = prove_finder_short_union_prefix(_program(image, c['parent'], c['prefix']),
        image_base=image.pe.image_base, table_rva=c['records'][0]['dispatcher']['switchTableRva'],
        count=c['records'][0]['dispatcher']['switchEntryCount'], label=LABEL+'.prefix')
    registry = selector_native['_registry']; plan = registry.plans[selector_native['selectorDefinition']]
    members = [m for m in plan if m.name == 'finderData' and m.kind == 'union']
    if len(members) != 1: _fail('selector-finder-field', 'one typed finderData union', members)
    summaries = []
    for r in c['records']:
        tag = r['tag']; wrapper = r['wrapper']; decl = declared[tag]; actual = wrappers.get(wrapper['typeDefinition'])
        if (actual is None or actual.row() != wrapper or decl['wrapperName'] != wrapper['wrapperName']
                or decl['wrappedType'] != wrapper['wrappedType'] or actual.members or actual.inherited_members
                or registry.union_tag_maps.get(members[0].ref, {}).get(tag) != wrapper['typeDefinition']
                or registry.plans.get(wrapper['typeDefinition']) != ()
                or registry.wrapped_names.get(wrapper['typeDefinition']) != wrapper['wrappedType']):
            _fail('current-wrapper-and-selector-parent', wrapper, decl)
        dispatch = image.validate_dispatcher(r['dispatcher'], label=LABEL)
        if (dispatch['definition'] != wrapper['typeDefinition']
                or int(catalog['switches']['SelectorFinder']['tableVa'], 16) != image.pe.image_base+r['dispatcher']['switchTableRva']
                or int(catalog['switches']['SelectorFinder']['dispatcherVa'], 16) != image.pe.image_base+c['parent']['entryRva']):
            _fail('current-indexed-parent', wrapper['typeDefinition'], dispatch)
        rows = _owned_rows(image, index, r['reader']); forward = _owned_rows(image, index, r['formatter'])
        lifecycle = {}
        for body in r['lifecycle']:
            _owned_rows(image, index, body); lifecycle[body['method'][2]] = image.pe.image_base+body['entryRva']
        if set(lifecycle) != {'.ctor', 'OnDeserialized'}: _fail('lifecycle-entry-inventory', ['.ctor', 'OnDeserialized'], lifecycle)
        own_symbols = {**symbols, 'constructor': lifecycle['.ctor'], 'onDeserialized': lifecycle['OnDeserialized']}
        if len(rows) not in (1, 2) or len(forward) != 1: _fail('wrapper-body-fragments', 'one primary and optional cold reader; one formatter', [len(rows), len(forward)])
        reader = prove_zero_wrapper_reader(rows[0], rows[1] if len(rows) == 2 else [], own_symbols, label=f'{LABEL}.reader:{tag}')
        formatter = prove_zero_wrapper_forwarder(forward[0], own_symbols, image.pe.image_base+r['reader']['entryRva'], label=f'{LABEL}.formatter:{tag}')
        method = image.metadata.methods[r['formatter']['method'][0]]
        if (method.slot != 5 or image.metadata.nested_parent_by_type_index.get(method.declaring_type) != wrapper['typeDefinition']):
            _fail('concrete-formatter-slot-owner', 'same wrapper nested formatter slot five', r['formatter']['method'])
        _vtable(image, method.declaring_type, 5, method.index, LABEL)
        formatter['currentConcreteMetadataSlotFiveJoined'] = True
        programs = {k: _program(image, c['parent'], v) for k, v in r['casePrograms'].items()}
        case = prove_finder_case(**programs, symbols=symbols, label=f'{LABEL}.case:{tag}')
        type_load = case['typeLoad']; raw = bytes.fromhex(type_load['bytes'])
        if int(type_load['va'], 16)+7+int.from_bytes(raw[3:], 'little', signed=True) != dispatch['usageCell']:
            _fail('actual-case-type-load', dispatch['usageCell'], type_load)
        if (r['newContext']['instructionRva'] != r['casePrograms']['new']['program'][0][0]
                or r['existingContext']['instructionRva'] != r['casePrograms']['existing']['program'][0][0]):
            _fail('actual-case-context-loads', 'same checked blocks', tag)
        new_context = _closed_context(image, entries, r['newContext'], wrapper, shared['identities']['new'], byref=False)
        existing_context = _closed_context(image, entries, r['existingContext'], wrapper, shared['identities']['existing'], byref=True)
        summaries.append({'tag': tag, 'runtimeTypeName': wrapper['wrappedType'], 'wrapperDefinition': wrapper['typeDefinition'],
            'reader': reader, 'formatter': formatter, 'case': case, 'newContext': new_context, 'existingContext': existing_context})
    return {'header': header, 'prefix': prefix, 'records': summaries, 'sharedReaders': shared,
        'canonicalShortChildSourceAndTypedParentJoinsProved': True,
        'parentGenericHelperEffectsProved': False, 'liveDefaultFormatterSelectionObserved': False,
        'fullParentUnionAndExtendedEncodingParityProved': False}


def validate_current_native_contract(*, selector_native, gameassembly: Path|None=None, metadata: Path|None=None):
    c = _contract(); pins = c['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated': return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins}
    if selector_native.get('status') != 'validated' or selector_native.get('nativeInputs') != pins:
        _fail('selected-selector-native', pins, selector_native.get('status'))
    unity = Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def matches():
        if not unity.is_file(): return False
        with unity.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest().upper() == pins['UnityPlayer.dll']
    if not matches(): return {'status': 'mismatched' if unity.is_file() else 'missing', 'detail': 'UnityPlayer.dll missing or mismatched', 'nativeInputs': pins}
    try: summary = _validate_image(open_native_image(gate.gameassembly, gate.metadata), c, selector_native)
    except ValueError as error:
        if isinstance(error, CensusGateError): raise
        _fail('complete-source-programs', 'current native ownership, bytes, contexts and local joins', str(error))
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not matches():
        return {'status': after.status if after.status != 'validated' else 'mismatched', 'detail': 'native inputs changed during source proof', 'nativeInputs': pins}
    return {'status': 'validated', 'nativeInputs': pins, 'summary': summary,
        'wholeActionAdmitted': False, 'positiveListAdmitted': False, 'wholeRootAdmitted': False,
        'runtimeMeaningExact': False, 'evidenceBoundary': c['evidenceBoundary']}


def finder_tags():
    return frozenset(r['tag'] for r in _contract()['records'])


def decode_finder(data: bytes, *, source: str, digest: str, start: int, end: int, native_validation: dict[str, Any]):
    c = _contract(); native = native_validation
    if (native.get('status') != 'validated' or native.get('nativeInputs') != c['nativeInputs']
            or native.get('summary', {}).get('canonicalShortChildSourceAndTypedParentJoinsProved') is not True
            or native.get('summary', {}).get('sharedReaders', {}).get('conditionalBothPhysicalReaderOutputPathsProved') is not True
            or not isinstance(data, bytes) or not isinstance(digest, str) or not source
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    if end-start != 2: raise ValueError(f'{LABEL}.decode:canonical-two-byte-span')
    records = {r['tag']: r for r in c['records']}; r = records.get(data[start])
    if r is None: raise ValueError(f'{LABEL}.decode:unsupported-canonical-tag')
    proved = [p for p in native['summary'].get('records', []) if p.get('tag') == r['tag']]
    if (len(proved) != 1 or proved[0].get('runtimeTypeName') != r['wrapper']['wrappedType']
            or proved[0].get('wrapperDefinition') != r['wrapper']['typeDefinition']
            or proved[0].get('reader', {}).get('conditionalZeroHeaderNormalReturnProved') is not True
            or proved[0].get('reader', {}).get('conditionalFFClearsFullOutputReferenceProved') is not True
            or proved[0].get('formatter', {}).get('conditionalReaderAndOutputForwardingProved') is not True
            or proved[0].get('formatter', {}).get('currentConcreteMetadataSlotFiveJoined') is not True
            or proved[0].get('case', {}).get('conditionalReaderAndOutputThroughBothGenericCallerReturnsProved') is not True):
        raise ValueError(f'{LABEL}.decode:selected-record-proof')
    header = data[start+1]
    if header not in (0, 255): raise ValueError(f'{LABEL}.decode:zero-or-FF-wrapper-header')
    return {'schema': 'endfield.buff-selector-zero-finder-child-receipt.v1', 'source': source,
        'logicalSha256': digest.upper(), 'start': start, 'end': end, 'tag': r['tag'],
        'typeName': r['wrapper']['wrappedType'], 'namedFields': [],
        'status': 'exact-null-wrapper' if header == 255 else 'conditional-named-zero-member-finder-exact-span',
        'wholeStoredSpanExact': True, 'recursiveNamedSchemaExact': True, 'recursiveStoredSchemaExact': True,
        'nativeSourceSelectionConditional': True, 'runtimeTargetSelectionKnown': False,
        'wholeActionAdmitted': False, 'positiveListAdmitted': False, 'wholeRootAdmitted': False,
        'evidenceBoundary': c['evidenceBoundary']}
