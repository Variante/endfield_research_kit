"""Authenticate the original global-variable callback's conditional request flow."""
from __future__ import annotations
import argparse
import json
import os
import struct
import tempfile
from pathlib import Path

if __name__ == '__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.levelscript_global_var_callback_native')

from scripts.common import check_installed_native_inputs
from scripts.game_data import levelscript_param_types as types
from scripts.game_data import levelscript_param_value_bridge as bridge
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import generic_method_candidates, method_spec_record, method_spec_usage_index, type_parameter_owner
from scripts.game_data.il2cpp.native_image import METADATA_HELPER_PATH, NATIVE_MAPPER_PATH, open_native_image
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.runtime_data_instructions import decode_runtime_data
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory
from scripts.game_data.levelscript_global_var_callback_flow import check_callback
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _guard_output_path, _parser_source_snapshots
from scripts.game_data.memorypack.scalar_param_native import need
from scripts.repo_paths import REPO_ROOT

SCHEMA = 'endfield.levelscript-global-var-callback-native-claims.v2'
CONTRACT_PATH = CONTRACTS_DIR / 'levelscript_global_var_callback_native_claims.json'
PARAM_CONTRACT_PATH = CONTRACTS_DIR / 'levelscript_long_param_value_native_claims.json'


def enum_abi(image, context, raw, definition=None):
    types.ordinary(raw, 17, 'globalVarCallback.enum')
    need('globalVarCallback.enum', 'valueMarker', 128, raw[11] & 128)
    actual = int.from_bytes(raw[:8], 'little')
    if definition is not None: need('globalVarCallback.enum', 'concreteDefinition', definition, actual)
    owner = image.metadata.types[actual]
    need('globalVarCallback.enum', 'declaredEnumParent', 'System.Enum', context.type_name(owner.parent_index))
    parent = types.type_record(image, context, owner.parent_index)
    types.ordinary(parent, 18, 'globalVarCallback.enumParent')
    need('globalVarCallback.enumParent', 'referenceMarker', 0, parent[11] & 128)
    fields = [f for f in image.metadata.fields_for(owner)
              if not int.from_bytes(types.type_record(image, context, f.type_index)[8:10], 'little') & 16]
    need('globalVarCallback.enum', 'backingCount', 1, len(fields))
    need('globalVarCallback.enum', 'backingName', 'value__', image.metadata.string(fields[0].name_index))
    record = types.type_record(image, context, fields[0].type_index)
    types.ordinary(record, 8, 'globalVarCallback.enumBacking')
    need('globalVarCallback.enum', 'instanceBacking', 0, int.from_bytes(record[8:10], 'little') & 16)
    return actual


def event_parameter(image, context, raw, expected):
    types.ordinary(raw, 21, 'globalVarCallback.eventByref', byref=True)
    base, inst = struct.unpack('<QQ', image.pe.bytes_at_va(int.from_bytes(raw[:8], 'little'), 16))
    definition = image.pe.bytes_at_va(base, 16)
    types.ordinary(definition, 17, 'globalVarCallback.eventDefinition')
    need('globalVarCallback.event', 'valueMarker', 128, definition[11] & 128)
    need('globalVarCallback.event', 'concreteDefinition', expected, int.from_bytes(definition[:8], 'little'))
    arguments = image.instantiations.resolve_pointer(inst).arguments
    need('globalVarCallback.event', 'arity', 2, len(arguments))
    for argument in arguments:
        types.ordinary(image.pe.bytes_at_va(argument.type_pointer_va, 16), 10, 'globalVarCallback.eventArgument')
    fields = image.metadata.fields_for(image.metadata.types[expected])
    need('globalVarCallback.event', 'fieldCount', 2, len(fields))
    for ordinal, field in enumerate(fields):
        record = types.type_record(image, context, field.type_index)
        types.ordinary(record, 19, 'globalVarCallback.eventVariable')
        owner = type_parameter_owner(image.metadata.buf, int.from_bytes(record[:8], 'little'),
            [td.generic_container_index for td in image.metadata.types], source='globalVarCallback.eventVariable')
        need('globalVarCallback.event', 'variableOwner', expected, owner['typeIndex'])
        need('globalVarCallback.event', 'variableOrdinal', ordinal, owner['ordinal'])
        need('globalVarCallback.event', 'declaredArity', 2, struct.unpack_from('<i', bytes.fromhex(owner['containerRawHex']), 4)[0])
    return {'definition': expected, 'explicitByref': True, 'ordinaryInt64Arguments': 2,
            'concreteFieldPlacementProved': False}


def method(image, context, spec, definitions):
    owner = bridge.qualified_owner(image, spec)
    need('globalVarCallback.method', 'nongenericOwner', -1, owner.generic_container_index)
    matches = []; refusals = []
    def token(raw, name):
        if name in ('Void', 'Boolean', 'Int32', 'Single'):
            types.ordinary(raw, {'Void': 1, 'Boolean': 2, 'Int32': 8, 'Single': 12}[name], 'globalVarCallback.methodType')
        elif name == 'explicit byref EventData<Int64,Int64>':
            event_parameter(image, context, raw, definitions['eventData'])
        else: enum_abi(image, context, raw, definitions[name])
    for candidate in image.metadata.methods_for(owner):
        if image.metadata.string(candidate.name_index) != spec['method']: continue
        try:
            need('globalVarCallback.method', 'static', spec['static'], bool(candidate.flags & 16))
            need('globalVarCallback.method', 'nongenericMethod', -1, candidate.generic_container_index)
            parameters = image.metadata.parameters_for(candidate)
            need('globalVarCallback.method', 'parameterCount', len(spec['parameters']), len(parameters))
            token(types.type_record(image, context, candidate.return_type), spec['return'])
            for param, expected in zip(parameters, spec['parameters']): token(types.type_record(image, context, param.type_index), expected)
        except (ValueError, KeyError, IndexError, struct.error) as exc:
            if len(refusals) < 3: refusals.append(str(exc)[:300])
            continue
        matches.append(candidate)
    if len(matches) != 1:
        raise ValueError('globalVarCallback.ordinaryMethod: ' + json.dumps({'type': spec['type'], 'method': spec['method'], 'expected': 1, 'actual': len(matches), 'firstRefusals': refusals}))
    pointer = image.method_pointer_va(matches[0])
    need('globalVarCallback.method', 'nonzeroPointer', True, bool(pointer))
    return matches[0], pointer


def loaded_context(image, row, formal, kind, definition=None):
    raw = bytes.fromhex(row['bytes']); address = int(row['va'], 16)
    need('globalVarCallback.context', 'loadEncoding', b'\x4c\x8b\x0d', raw[:3])
    need('globalVarCallback.context', 'loadSize', 7, len(raw))
    cell = address + 7 + struct.unpack_from('<i', raw, 3)[0]
    usage = image.pe.bytes_at_va(cell, 8)
    index = method_spec_usage_index(usage, image.registration['methodSpecsCount'], source='globalVarCallback.context', offset=cell)
    spec_address = int(image.registration['methodSpecs'], 16) + index * 12
    spec = method_spec_record(image.pe.bytes_at_va(spec_address, 12), len(image.metadata.methods),
        image.registration['genericInstsCount'], source='globalVarCallback.context', offset=spec_address)
    need('globalVarCallback.context', 'formalMethod', formal.index, spec[0])
    need('globalVarCallback.context', 'classInstantiation', -1, spec[1])
    arguments = image.instantiations.resolve(spec[2]).arguments
    need('globalVarCallback.context', 'argumentCount', 1, len(arguments))
    record = image.pe.bytes_at_va(arguments[0].type_pointer_va, 16)
    types.ordinary(record, kind, 'globalVarCallback.contextArgument')
    if definition is not None: enum_abi(image, NativeReferenceContext(image), record, definition)
    return {'methodSpecIndex': index, 'methodSpec': list(spec), 'cellVa': cell, 'usageRawHex': usage.hex().upper()}


def registered_pointer(image, spec_index):
    reg = image.registration; code = image.mapper.code_registration_summary(image.pe, image.code_registration)
    address = int(reg['genericMethodTable'], 16)
    rows = generic_method_candidates(image.pe.bytes_at_va(address, reg['genericMethodTableCount'] * 16),
        reg['genericMethodTableCount'], reg['methodSpecsCount'], {spec_index}, code['genericMethodPointersCount'],
        code['invokerPointersCount'], source='globalVarCallback.registration', offset=address)
    need('globalVarCallback.registration', 'entryCount', 1, len(rows))
    return image.pe.u64_at_va(int(code['genericMethodPointers'], 16) + rows[0]['indices'][0] * 8)


def physical_enum_argument(image, context, spec_index, formal, expected_name):
    reg = image.registration
    address = int(reg['methodSpecs'], 16) + spec_index * 12
    spec = method_spec_record(image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
        reg['genericInstsCount'], source='globalVarCallback.enumPhysicalContext', offset=address)
    need('globalVarCallback.enumPhysicalContext', 'formalMethod', formal.index, spec[0])
    need('globalVarCallback.enumPhysicalContext', 'classInstantiation', -1, spec[1])
    arguments = image.instantiations.resolve(spec[2]).arguments
    need('globalVarCallback.enumPhysicalContext', 'arity', 1, len(arguments))
    raw = image.pe.bytes_at_va(arguments[0].type_pointer_va, 16)
    definition = enum_abi(image, context, raw)
    need('globalVarCallback.enumPhysicalContext', 'name', expected_name, image.type_name(definition))
    return {'definition': definition, 'rawTypeHex': raw.hex().upper(), 'methodSpec': list(spec),
            'ordinaryEnumBackingBits': 32, 'actualLoadedContextCompatibilityProved': False}


def receiver_base(image, context, owner, target):
    seen = set(); ancestors = []
    while owner.parent_index >= 0:
        raw = types.type_record(image, context, owner.parent_index)
        types.ordinary(raw, 18, 'globalVarCallback.receiverParent')
        need('globalVarCallback.receiverParent', 'referenceMarker', 0, raw[11] & 128)
        parent = int.from_bytes(raw[:8], 'little')
        need('globalVarCallback.receiver', 'acyclicParent', True, parent not in seen and len(seen) < 32)
        seen.add(parent); ancestors.append(parent)
        if parent == target: return ancestors
        owner = image.metadata.types[parent]
    raise ValueError('globalVarCallback.receiver.setterBase: selected base definition not reached')


def evaluate(image, declaration, param_declaration):
    context = NativeReferenceContext(image); index = BodyIndex(image); md = image.metadata
    definitions = {name: bridge.qualified_owner(image, spec).index for name, spec in declaration['types'].items()}
    methods = {role: method(image, context, spec, definitions) for role, spec in declaration['methods'].items()}
    callback, pointer = methods['callback']; base = image.pe.image_base
    table_rva, size, table = read_exception_directory(image.pe)
    unwind = UnwindChainIndex(table, lambda rva, n: image.pe.bytes_at_va(base+rva, n), table_rva=table_rva, image_size=size)
    family = unwind.family(pointer-base)
    need('globalVarCallback.owned', 'rangeCount', 1, len(family['ranges']))
    begin, end, _ = family['ranges'][0]['runtimeTriple']
    need('globalVarCallback.owned', 'entry', pointer-base, begin)
    need('globalVarCallback.owned', 'boundedPrimary', True, 0 < end-begin <= 4096)
    rows = decode_runtime_data(image.mapper, image.pe.bytes_at_va(pointer, end-begin), pointer)
    need('globalVarCallback.owned', 'unknownInstructions', [], [r['text'] for r in rows if r['text'].startswith(('db', 'unknown', 'ff/'))][:3])
    ancestors = receiver_base(image, context, md.types[callback.declaring_type], methods['resultSetter'][0].declaring_type)
    formal_spec = param_declaration['methods']['value']; formal_owner = bridge.qualified_owner(image, formal_spec)
    candidates = []
    for candidate in md.methods_for(formal_owner):
        if md.string(candidate.name_index) != formal_spec['method']: continue
        try: definition = bridge.formal_method(image, context, candidate, 'value')
        except (ValueError, KeyError, IndexError, struct.error): continue
        candidates.append((candidate, definition))
    need('globalVarCallback.param', 'formalCount', 1, len(candidates)); formal, param_definition = candidates[0]
    offsets = runtime_type_field_offsets(md, image.pe, image.registration, callback.declaring_type)
    fields = {}; field_rows = {}
    for role, name in declaration['fields'].items():
        found = [f for f in md.fields_for(md.types[callback.declaring_type]) if md.string(f.name_index) == name]
        need('globalVarCallback.field', 'unique.'+name, 1, len(found)); field = found[0]
        raw = types.type_record(image, context, field.type_index)
        need('globalVarCallback.field', 'instance', 0, int.from_bytes(raw[8:10], 'little') & 16)
        need('globalVarCallback.field', 'parameterDefinition', param_definition, types.param_reference(image, raw, 17 if role=='enumValue' else 10))
        if role == 'enumValue':
            _, inst = struct.unpack('<QQ', image.pe.bytes_at_va(int.from_bytes(raw[:8], 'little'), 16))
            argument = image.instantiations.resolve_pointer(inst).arguments[0]
            enum_abi(image, context, image.pe.bytes_at_va(argument.type_pointer_va, 16), definitions['CompareOperator'])
        fields[name] = offsets[name]; field_rows[name] = {'index': field.index, 'offset': offsets[name], 'rawType': raw.hex().upper()}
    contexts = {'enumValue': loaded_context(image, rows[19], formal, 17, definitions['CompareOperator']),
                'longValue': loaded_context(image, rows[25], formal, 10)}
    long_pointer = registered_pointer(image, contexts['longValue']['methodSpecIndex'])
    enum_target = bridge.target([int(rows[24]['va'],16), rows[24]['bytes']], b'\xe8')
    aliases = [a for a in index.names_by_pointer.get(enum_target, []) if a.get('methodIndex') == formal.index
        and a.get('genericInstantiation') and [x.get('typeName') for x in a.get('methodInstantiation',{}).get('arguments',[])] == [declaration['enumPhysicalEntryArgument']]]
    need('globalVarCallback.enumEntry', 'registeredPhysicalAliases', 1, len(aliases))
    physical = physical_enum_argument(image, context, aliases[0]['methodSpecIndex'], formal, declaration['enumPhysicalEntryArgument'])
    need('globalVarCallback.enumEntry', 'actualRegisteredPointer', enum_target, registered_pointer(image, aliases[0]['methodSpecIndex']))
    targets = {role: p for role, (m, p) in methods.items() if role != 'callback'}
    targets.update(enumValue=enum_target, longValue=long_pointer)
    program = check_callback(rows, fields, targets)
    proved = {'selectedNormalPaths': program['selectedNormalPaths'], 'eventLaneNamedPlacementProved': False,
              'comparisonInputs': ['signed Int64 anonymous byref lane to Single', 'signed Int64 current parameter return to Single'],
              'resultSetterInput': 'zero-extended current comparison AL as ordinary ConditionResult',
              'enumSharedImplementationCompatibilityProved': False, 'concreteNumericResultOrSetterEffectProved': False}
    need('globalVarCallback', 'evaluatedClaims', proved, declaration['claims'])
    return {'program': program, 'provedClaims': proved, 'fields': field_rows, 'contexts': contexts, 'receiverAncestorDefinitions': ancestors,
            'enumPhysicalEntry': aliases[0], 'enumPhysicalArgument': physical, 'ownedRange': [begin,end],
            'methods': {role: {'methodIndex': m.index, 'pointerRva': p-base} for role,(m,p) in methods.items()},
            'evidenceBoundary': declaration['evidenceBoundary'], 'runtimeExecutionObserved': False}


def proof_sources(contract_path):
    paths = [contract_path, PARAM_CONTRACT_PATH, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH,
             *[Path(r['path']) for r in _parser_source_snapshots(Path(__file__))]]
    return [_fingerprint(p) for p in sorted({p.resolve() for p in paths}, key=str)]


def validate_callback_claims(*, contract_path=CONTRACT_PATH, gameassembly=None, metadata=None):
    contract_path = Path(contract_path)
    try:
        raw = contract_path.read_bytes(); declaration = json.loads(raw)
        need('globalVarCallback','schema',SCHEMA,declaration.get('schema'))
        need('globalVarCallback','status','reviewed',declaration.get('status'))
        need('globalVarCallback','dependencies',[{'role':'paramValue','path':PARAM_CONTRACT_PATH.name}],declaration['dependencies'])
        if gameassembly is None or metadata is None:
            return {'status':'missing','rows':[],'detail':'globalVarCallback.explicitNativePair: both paths required'}
        pair = {'gameassembly':Path(gameassembly),'metadata':Path(metadata)}
        if not all(p.is_file() for p in pair.values()):
            return {'status':'missing','rows':[],'detail':'globalVarCallback.explicitNativePair: selected file missing'}
        native = [_fingerprint(p) for p in pair.values()]; sources = proof_sources(contract_path)
        need('globalVarCallback','parsedDeclarationUnchanged',raw,contract_path.read_bytes())
        before = check_installed_native_inputs(native[0]['sha256'],native[1]['sha256'],**pair)
        if before.status!='validated':return {'status':before.status,'rows':[],'detail':before.detail}
        row = evaluate(open_native_image(before.gameassembly,before.metadata),declaration,json.loads(PARAM_CONTRACT_PATH.read_bytes()))
        after = check_installed_native_inputs(native[0]['sha256'],native[1]['sha256'],**pair)
        if after.status!='validated':return {'status':after.status,'rows':[],'detail':after.detail}
        need('globalVarCallback','nativeUnchanged',native,[_fingerprint(p) for p in pair.values()])
        need('globalVarCallback','sourcesUnchanged',sources,proof_sources(contract_path))
        return {'schema':SCHEMA,'status':'validated','rows':[row],'nativeInputs':native,'proofSources':sources,
                'nativeBefore':before.status,'nativeAfter':after.status}
    except (ValueError,KeyError,OSError,TypeError,IndexError,StopIteration,struct.error) as exc:
        return {'status':'pendingReview','rows':[],'source':str(contract_path),'detail':str(exc)[:1500]}


def check_output(output, protected):
    root=(REPO_ROOT/'reports').resolve(); target=output.resolve()
    if not root.is_relative_to(REPO_ROOT.resolve()) or target==root or not target.is_relative_to(root):
        raise ValueError('globalVarCallback.output: report must be under reports/')
    _guard_output_path(output,protected)
    if output.exists():need('globalVarCallback.output','owner',SCHEMA,json.loads(output.read_bytes()).get('schema'))


def publish(output,result,contract_path,protected):
    inputs=protected+[Path(r['path']) for r in result['proofSources']];check_output(output,inputs)
    output.parent.mkdir(parents=True,exist_ok=True)
    descriptor,name=tempfile.mkstemp(prefix='.global-var-callback-',suffix='.tmp',dir=output.parent);staged=Path(name)
    try:
        with os.fdopen(descriptor,'w',encoding='utf-8',newline='\n') as handle:json.dump(result,handle,indent=2);handle.write('\n')
        sources=proof_sources(contract_path)
        need('globalVarCallback.publication','sourcesUnchanged',result['proofSources'],sources)
        need('globalVarCallback.publication','nativeUnchanged',result['nativeInputs'],[_fingerprint(Path(r['path'])) for r in result['nativeInputs']])
        inputs += [Path(r['path']) for r in sources]
        check_output(staged,inputs);check_output(output,inputs);os.replace(staged,output)
    finally:
        if staged.exists():staged.unlink()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,default=CONTRACT_PATH)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        protected=[args.contract,PARAM_CONTRACT_PATH,args.gameassembly,args.metadata]
        if args.output is not None:check_output(args.output,protected)
        result=validate_callback_claims(contract_path=args.contract,gameassembly=args.gameassembly,metadata=args.metadata)
        if result['status']=='validated' and args.output is not None:publish(args.output,result,args.contract,protected)
    except (ValueError,KeyError,OSError,TypeError) as exc:result={'status':'pendingReview','rows':[],'detail':str(exc)[:1500]}
    print(json.dumps({'status':result['status'],'rows':len(result['rows']),**({'detail':result['detail']} if 'detail' in result else {})}))
    return 0 if result['status']=='validated' else 2


if __name__=='__main__':raise SystemExit(main())
