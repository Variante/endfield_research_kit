"""Evaluate named closed Boolean Param consumer claims on the explicitly selected build.

Evidence and admission boundary:

Conditional initialized/ready Boolean evaluation copies one source byte through
explicit output and returns separate low-byte success; caller zero-extends
output or fallback without proving value normalization. Exact concrete Param,
registered caller targets, reciprocal class/method ownership/arity and byref
output declarations join the compatible one-byte wrapper slot. Unlike stored
Boolean source normalization, this evaluator's byte transfer proves no 0/1
normalization. Unchanged compatible storage is required; predicate server
markers add no serialized alternatives. Runtime receiver/context/provider,
nonconstant paths and stored-cursor integration remain unresolved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

if __name__ == '__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.levelscript_bool_param_value_native')

from scripts.common import check_installed_native_inputs
from scripts.game_data import levelscript_param_value_bridge as value_bridge
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import METADATA_HELPER_PATH, NATIVE_MAPPER_PATH, open_native_image
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _guard_output_path, _parser_source_snapshots
from scripts.game_data.memorypack.scalar_param_native import need
from scripts.repo_paths import REPO_ROOT

SCHEMA = 'endfield.levelscript-bool-param-value-native-claims.v1'
CONTRACT_PATH = CONTRACTS_DIR / 'levelscript_bool_param_value_native_claims.json'


def caller_program(program, getter, attempt, slots):
    forms = ['48895c2410', '48896c2418', '4889742420', '57', '4883ec20', '4983793800', '498bd9', '410fb6f0', '0fb6ea', '488bf9', None, 'c644243000', '4885ff', None, '488b4338', '488b5008', '48837a2000', None, '488b5338', '488bcf', '488b5208', None, '84c0', None, '488b4338', '488d542430', '440fb6c6', '488bcf', '4c8b4810', None, '84c0', None, '0fb6442430', '488b5c2438', '488b6c2440', '488b742448', '4883c420', '5f', 'c3', '837f'+bytes((slots['idRef'],)).hex()+'ff', None, '400fb6c5', None, '488bcb', None, None, 'ff12', None]
    value_bridge.shape(program, forms, 'boolParamValue.caller')
    edges = {10: (b'\x74', 43), 13: (b'\x74', 41), 17: (b'\x74', 46), 23: (b'\x75', 39), 31: (b'\x74', 41), 40: (b'\x75', 24), 42: (b'\xeb', 33), 45: (b'\xeb', 11), 47: (b'\xeb', 18)}
    for at, (opcode, to) in edges.items():
        need('boolParamValue.caller', f'destination[{at}]', program[to][0], value_bridge.target(program[at], opcode))
    need('boolParamValue.caller', 'actualPredicateCall', getter, value_bridge.target(program[21], b'\xe8'))
    need('boolParamValue.caller', 'actualTryCall', attempt, value_bridge.target(program[29], b'\xe8'))
    value_bridge.target(program[44], b'\xe8')
    need('boolParamValue.caller','selectedBytes',166,program[-1][0]+len(value_bridge.raw(program[-1]))-program[0][0])
    outcomes = []

    def walk(n, path):
        need('boolParamValue.caller', 'boundedAcyclicCFG', True, n not in path and len(path) < 48)
        path = path + [n]
        if n == 38:
            outcomes.append(path)
            return
        if n in edges:
            op, to = edges[n]
            if op == b'\xeb':
                walk(to, path)
            else:
                if n not in (10, 17):
                    walk(to, path)
                walk(n + 1, path)
        else:
            walk(n + 1, path)
    walk(0, [])
    need('boolParamValue.caller', 'normalPaths', 6, len(outcomes))
    for path in outcomes:
        need('boolParamValue.caller', 'retainedFrame', True, all((n in path for n in (0, 1, 2, 3, 4, 8, 9, 11, 33, 34, 35, 36, 37, 38))))
        need('boolParamValue.caller', 'oneResultSource', True, (32 in path) != (41 in path))
    constant_paths = [path for path in outcomes if 32 in path and 39 not in path]
    need('boolParamValue.caller','constantPaths',1,len(constant_paths))
    need('boolParamValue.caller','fallbackPaths',4,sum(41 in path for path in outcomes))
    need('boolParamValue.caller','outputPaths',2,sum(32 in path for path in outcomes))
    return {'normalPaths': 6, 'fallbackPaths': 4, 'outputPaths': 2, 'constantPath':constant_paths[0], 'outputBytes':1, 'frameDelta': 40, 'return': 'zero-extended original DL byte or current local output byte in EAX/RAX', 'lowByteNormalizationToZeroOrOneProved': False}


def constant_program(program, owner, slots, declaration):
    forms = ['48895c2418', '4889542410', '56', '57', '4154', '4156', '4157', '4881ecd0000000', '498bf9', '450fb6e0', '488bf2', '488bd9', '4983793800', None, '33c0', '4889842418010000', '4889842400010000', '0f57c0', '0f118424a0000000', '0f118424b0000000', '48898424c0000000', '4885db', None, '488b4738', '488b4808', '4883792000', None, '837b'+bytes((slots['paramSource'],)).hex()+'00', None, '0fb643'+bytes((slots['constValue'],)).hex(), '8806', 'b001', '488b9c2410010000', '4881c4d0000000', '415f', '415e', '415c', '5f', '5e', 'c3']
    value_bridge.shape(program, forms, 'boolParamValue.constant')
    need('boolParamValue.constant','sourceDeclaration',0,declaration)
    for row in program:
        need('boolParamValue.constant','ownedInstruction',True,owner[0]<=row[0]<row[0]+len(value_bridge.raw(row))<=owner[1])
    end = program[-1][0] + 1
    for at, opcode in [(13, b'\x0f\x84'), (22, b'\x0f\x84'), (26, b'\x0f\x84'), (28, b'\x75')]:
        need('boolParamValue.constant', f'unselectedDestination[{at}]', True, not program[0][0] <= value_bridge.target(program[at], opcode) < end)
    need('boolParamValue.constant', 'selectedBytes', 160, end - program[0][0])
    return {'normalPaths':1, 'outputBytes':1, 'selectedBytes': 160, 'frameDelta': 248, 'output': 'original constValue byte copied unchanged through original explicit byref output', 'return': 'AL=1 after byte output write', 'opaqueCallsOnSelectedPath': 0, 'outputByteNormalizationProved': False, 'otherSourceBehaviorProved': False}


def predicate_program(rows, slots, declarations):
    source = bytes((slots['paramSource'],)).hex()
    value_bridge.shape(rows, ['8379'+source+'ff', None, '8379'+source+'fe', None,
                             '32c0', 'c3', 'b001', 'c3'], 'boolParamValue.predicate')
    for at in (1, 3):
        need('boolParamValue.predicate', 'trueDestination', rows[6][0], value_bridge.target(rows[at], b'\x74'))
    need('boolParamValue.predicate', 'markerDeclarations', [-1, -2], declarations)
    return {'normalPaths':3, 'return':'ordinary Boolean low8', 'storesOrCalls':0}


def evaluate(image, contract):
    context = NativeReferenceContext(image)
    index = BodyIndex(image)
    entries = value_bridge.named_entries(image, contract['methods'], context, primitive_name='Boolean', primitive_kind=2)
    bridge = value_bridge.wrapper_view(image, context, contract['methods']['wrapperView'],
        entries['value']['parameterDefinition'], index, primitive_name='Boolean', primitive_type='bool',
        primitive_kind=2, store_prefix=b'\x88\x50')
    table_rva, size, table = read_exception_directory(image.pe)
    unwind = UnwindChainIndex(table, lambda rva,n:image.pe.bytes_at_va(image.pe.image_base+rva,n),
                             table_rva=table_rva, image_size=size)
    programs, ownership = {}, {}
    for role in ('value', 'tryValue'):
        pointer = entries[role]['pointerRva']
        family = unwind.family(pointer)
        primary = [part for part in family['ranges'] if part['runtimeTriple'][0] == pointer]
        need('boolParamValue.'+role, 'primaryOwnedRange', 1, len(primary))
        triple = primary[0]['runtimeTriple']
        if not 0 < triple[1]-pointer <= 8192:
            raise ValueError('boolParamValue.'+role+'.ownedRange: unbounded')
        ownership[role] = triple
        programs[role] = value_bridge.decode_rows(index, image.pe.image_base+pointer, triple[1]-pointer)
    predicate = value_bridge.decode_rows(index, image.pe.image_base+entries['predicate']['pointerRva'], 18)
    selected = programs['tryValue'][:40]
    names = contract['claims']['predicate']['matchesDeclarations'] + [contract['claims']['constant']['selectorDeclaration']]
    symbols = value_bridge.declarations(image, context, contract['declarations'], names)
    getter = predicate_program(predicate, bridge['slots'], [symbols[n]['value'] for n in contract['claims']['predicate']['matchesDeclarations']])
    caller = caller_program(programs['value'], entries['predicate']['pointerRva'], entries['tryValue']['pointerRva'], bridge['slots'])
    constant = constant_program(selected, ownership['tryValue'][:2], bridge['slots'],
        symbols[contract['claims']['constant']['selectorDeclaration']]['value'])

    def member_at(offset):
        matching = [name for name,slot in bridge['slots'].items() if slot == offset]
        need('boolParamValue.claims', 'memberSlotAliases', 1, len(matching))
        return matching[0]

    proved_claims = {
        'caller': {'normalPaths':caller['normalPaths'], 'fallbackArgument':1, 'outputBytes':caller['outputBytes'],
                   'calls':['predicate','tryValue'], 'return':'zero-extended original Boolean storage byte',
                   'returnedByteNormalizationProved':False},
        'constant': {'selectorMember':member_at(value_bridge.raw(selected[27])[2]),
                     'selectorDeclaration':contract['claims']['constant']['selectorDeclaration'],
                     'sourceMember':member_at(value_bridge.raw(selected[29])[-1]), 'outputArgument':1,
                     'outputBytes':constant['outputBytes'], 'successfulBooleanBits':value_bridge.raw(selected[31])[1],
                     'opaqueCallsOnSelectedPath':constant['opaqueCallsOnSelectedPath'], 'outputByteNormalizationProved':False},
        'predicate': {'selectorMember':member_at(value_bridge.raw(predicate[0])[2]),
                      'matchesDeclarations':contract['claims']['predicate']['matchesDeclarations'], 'return':getter['return']},
        'wrapper': {'holderMember':contract['methods']['wrapperView']['holder'], 'sameConcreteParameterDefinition':True,
                    'members':{'constValue':'ordinary Boolean','idRef':'ordinary Int32','paramSource':'ordinary Int32'}},
    }
    need('boolParamValue.claims', 'evaluatedMeaning', contract['claims'], proved_claims)
    return {'entries':entries, 'wrapperView':bridge, 'declarations':symbols, 'predicate':getter, 'caller':caller,
            'constant':constant, 'ownedRanges':ownership,
            'selectedWindows':[value_bridge.window(predicate),value_bridge.window(programs['value']),value_bridge.window(selected)],
            'provedClaims':proved_claims, 'evidenceBoundary':contract['evidenceBoundary'],
            'conditions':['compatible unchanged parameter storage where dereferenced',
                          'each selected initialized/ready context branch', 'ordinary closed ABI and complete retained frames',
                          'writable caller output and no object aliases corrupting its frame'],
            'runtimeReceiverOrProviderSelectionProved':False, 'storedCursorEvaluatorIntegrationProved':False,
            'byteNormalizationToZeroOrOneProved':False}


def validate_bool_param_value_claims(*,contract_path=CONTRACT_PATH,gameassembly=None,metadata=None):
    contract_path=Path(contract_path)
    try:
        contract_raw=contract_path.read_bytes();contract=json.loads(contract_raw)
        need('boolParamValue','schema',SCHEMA,contract.get('schema'));need('boolParamValue','status','reviewed',contract.get('status'))
        if gameassembly is None or metadata is None:
            return {'status':'missing','rows':[],'detail':'boolParamValue.explicitNativePair: both paths required'}
        pair={'gameassembly':Path(gameassembly),'metadata':Path(metadata)}
        if not all(p.is_file() for p in pair.values()):
            return {'status':'missing','rows':[],'detail':'boolParamValue.explicitNativePair: selected file missing'}
        native={name:_fingerprint(pair[key])['sha256'] for name,key in [('GameAssembly.dll','gameassembly'),('global-metadata.dat','metadata')]}
        paths=[Path(__file__),contract_path,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH,
               *[Path(row['path']) for row in _parser_source_snapshots(Path(__file__))]]
        sources=[_fingerprint(p) for p in sorted({p.resolve() for p in paths},key=str)]
        before=check_installed_native_inputs(native['GameAssembly.dll'],native['global-metadata.dat'],**pair)
        if before.status!='validated':return {'status':before.status,'rows':[],'detail':before.detail}
        row=evaluate(open_native_image(before.gameassembly,before.metadata),contract)
        after=check_installed_native_inputs(native['GameAssembly.dll'],native['global-metadata.dat'],gameassembly=before.gameassembly,metadata=before.metadata)
        if after.status!='validated':return {'status':after.status,'rows':[],'detail':after.detail}
        need('boolParamValue','sourceUnchanged',sources,[_fingerprint(Path(r['path'])) for r in sources])
        need('boolParamValue','declarationUnchanged',contract_raw,contract_path.read_bytes())
        return {'schema':SCHEMA,'status':'validated','rows':[row],'nativeInputs':native,'proofSources':sources,
                'nativeBefore':before.status,'nativeAfter':after.status}
    except (ValueError,KeyError,OSError,IndexError,TypeError,struct.error) as exc:
        return {'status':'pendingReview','rows':[],'detail':str(exc)[:1500],'source':str(contract_path)}


def check_output(output,protected):
    if not output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):raise ValueError('boolParamValue.output: report must be under reports/')
    _guard_output_path(output,protected)
    if output.exists():need('boolParamValue.output','owner',SCHEMA,json.loads(output.read_bytes()).get('schema'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,default=CONTRACT_PATH)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        if args.output is not None:check_output(args.output,[args.contract,args.gameassembly,args.metadata])
        result=validate_bool_param_value_claims(contract_path=args.contract,gameassembly=args.gameassembly,metadata=args.metadata)
        if result['status']=='validated' and args.output is not None:
            check_output(args.output,[args.contract,args.gameassembly,args.metadata,*[Path(r['path']) for r in result['proofSources']]])
            need('boolParamValue.publication','sourcesUnchanged',result['proofSources'],[_fingerprint(Path(r['path'])) for r in result['proofSources']])
            atomic_write_text(args.output,json.dumps(result,indent=2)+'\n')
    except (ValueError,KeyError,OSError,TypeError) as exc:
        result={'status':'pendingReview','rows':[],'detail':str(exc)[:1500]}
    print(json.dumps({'status':result['status'],'rows':len(result['rows']),**({'detail':result['detail']} if 'detail' in result else {})},indent=2))
    return 0 if result['status']=='validated' else 2


if __name__=='__main__':raise SystemExit(main())
