"""Evaluate named closed Single Param consumer claims on the explicitly selected build."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

if __name__ == '__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.levelscript_float_param_value_native')

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

SCHEMA = 'endfield.levelscript-float-param-value-native-claims.v1'
CONTRACT_PATH = CONTRACTS_DIR / 'levelscript_float_param_value_native_claims.json'


def caller_program(warm, child, ownership, predicate_rva, try_rva, slots):
    forms = ['48895c2410', '4889742418', '57', '4883ec30', '4983793800', '498bd9', '0f29742420', '410fb6f0', '0f28f1', '488bf9', None, 'c744244000000000', '4885ff', None, '488b4338', '488b4808', '4883792000', None, '488b5338', '488bcf', '488b5208', None, '84c0', None, '488b4338', '488d542440', '440fb6c6', '488bcf', '4c8b4810', None, '84c0', None, 'f30f10442440', '488b5c2448', '488b742450', '0f28742420', '4883c430', '5f', 'c3', '488bcb', None, None, 'ff11', None, '0f28c6', None]
    value_bridge.shape(warm, forms, 'floatParamValue.warm')
    value_bridge.shape(child, ['837f'+bytes((slots['idRef'],)).hex()+'ff', None, None], 'floatParamValue.cold')
    need('floatParamValue.caller', 'warmOwnedBounds', True, warm[0][0] == ownership['value']['primary'][0] and warm[-1][0] + len(value_bridge.raw(warm[-1])) == ownership['value']['primary'][1])
    need('floatParamValue.caller', 'coldOwnedBounds', True, child[0][0] == ownership['value']['cold'][0] and child[-1][0] + len(value_bridge.raw(child[-1])) == ownership['value']['cold'][1])
    need('floatParamValue.caller', 'coldParent', ownership['value']['primary'], ownership['value']['coldParent'])
    program = warm + child
    edges = {10: (b'\x74', 39), 13: (b'\x74', 44), 17: (b'\x74', 42), 23: (b'\x0f\x85', 46), 31: (b'\x74', 44), 41: (b'\xeb', 11), 43: (b'\xeb', 18), 45: (b'\xeb', 33), 47: (b'\x0f\x84', 44), 48: (b'\xe9', 24)}
    for at, (opcode, to) in edges.items():
        need('floatParamValue.caller', f'ownedBranchDestination[{at}]', program[to][0], value_bridge.target(program[at], opcode))
    need('floatParamValue.caller', 'actualPredicateCall', predicate_rva, value_bridge.target(warm[21], b'\xe8'))
    need('floatParamValue.caller', 'actualTryCall', try_rva, value_bridge.target(warm[29], b'\xe8'))
    value_bridge.target(warm[40], b'\xe8')
    outcomes = []

    def walk(n, path):
        need('floatParamValue.caller', 'boundedAcyclicCFG', True, n not in path and len(path) < 49)
        path = path + [n]
        if n == 38:
            outcomes.append(path)
            return
        if n in edges:
            opcode, to = edges[n]
            if opcode in (b'\xeb', b'\xe9'):
                walk(to, path)
            else:
                if n not in (10, 17):
                    walk(to, path)
                walk(n + 1, path)
        else:
            walk(n + 1, path)
    walk(0, [])
    need('floatParamValue.caller', 'normalPaths', 6, len(outcomes))
    need('floatParamValue.caller', 'resultPathCounts', True, sum((44 in path for path in outcomes)) == 4 and sum((32 in path for path in outcomes)) == 2)
    for path in outcomes:
        need('floatParamValue.caller', 'retainedFrame', True, all((n in path for n in (0, 1, 2, 3, 6, 8, 9, 11, 33, 34, 35, 36, 37, 38))))
        need('floatParamValue.caller', 'oneResultSource', True, (32 in path) != (44 in path))
    constant_paths=[path for path in outcomes if 32 in path and 46 not in path]
    need('floatParamValue.caller','constantPaths',1,len(constant_paths))
    return {'constantPath':constant_paths[0],'outputBytes':4,'normalPaths': 6, 'fallbackPaths': 4, 'outputPaths': 2, 'frameDelta': 56, 'ownedPrimaryBytes': 167, 'ownedColdBytes': 15, 'returnRegister': 'XMM0 low32', 'return': 'current output DWORD bits or original incoming XMM1 low32 bits', 'floatingArithmeticOrConversionOnSelectedTransfers': False, 'initializerOrReadyCalleeEffectsProved': False}


def constant_program(program, owner, slots, declaration):
    forms = ['48895c2418', '4889542410', '56', '57', '4154', '4156', '4157', '4881ecd0000000', '498bf9', '450fb6f0', '488bf2', '488bd9', '4983793800', None, '33c0', '4889842418010000', '4889842400010000', '0f57c0', '0f118424a0000000', '0f118424b0000000', '48898424c0000000', '4885db', None, '488b4738', '488b4808', '4883792000', None, '837b'+bytes((slots['paramSource'],)).hex()+'00', None, '8b43'+bytes((slots['constValue'],)).hex(), '8906', 'b001', '488b9c2410010000', '4881c4d0000000', '415f', '415e', '415c', '5f', '5e', 'c3']
    value_bridge.shape(program, forms, 'floatParamValue.constant')
    need('floatParamValue.constant','sourceDeclaration',0,declaration)
    for row in program:
        need('floatParamValue.constant','ownedInstruction',True,owner[0]<=row[0]<row[0]+len(value_bridge.raw(row))<=owner[1])
    end = program[-1][0] + 1
    for at, opcode in [(13, b'\x74'), (22, b'\x0f\x84'), (26, b'\x0f\x84'), (28, b'\x0f\x85')]:
        need('floatParamValue.constant', f'unselectedDestination[{at}]', True, not program[0][0] <= value_bridge.target(program[at], opcode) < end)
    need('floatParamValue.constant', 'selectedBytes', 159, end - program[0][0])
    return {'normalPaths':1, 'outputBytes':4, 'selectedBytes': 159, 'frameDelta': 248, 'output': 'original constValue DWORD bits copied unchanged through original explicit byref output', 'return': 'AL=1 after complete DWORD output write', 'opaqueCallsOnSelectedPath': 0, 'otherSourceBehaviorProved': False}


def predicate_program(rows, slots, declarations):
    source = bytes((slots['paramSource'],)).hex()
    value_bridge.shape(rows, ['8379'+source+'ff', None, '8379'+source+'fe', None,
                             '32c0', 'c3', 'b001', 'c3'], 'floatParamValue.predicate')
    for at in (1, 3):
        need('floatParamValue.predicate', 'trueDestination', rows[6][0], value_bridge.target(rows[at], b'\x74'))
    need('floatParamValue.predicate', 'markerDeclarations', [-1, -2], declarations)
    return {'normalPaths':3, 'return':'ordinary Boolean low8', 'storesOrCalls':0}


def evaluate(image, contract):
    context = NativeReferenceContext(image)
    index = BodyIndex(image)
    entries = value_bridge.named_entries(image, contract['methods'], context, primitive_name='Single', primitive_kind=12)
    view = value_bridge.wrapper_view(image, context, contract['methods']['wrapperView'],
        entries['value']['parameterDefinition'], index, primitive_name='Single', primitive_type='float',
        primitive_kind=12, store_prefix=b'\xf3\x0f\x11\x48')
    table_rva, size, table = read_exception_directory(image.pe)
    unwind = UnwindChainIndex(table, lambda rva,n:image.pe.bytes_at_va(image.pe.image_base+rva,n),
                             table_rva=table_rva, image_size=size)
    programs, ownership = {}, {}
    for role in ('value', 'tryValue'):
        pointer = entries[role]['pointerRva']
        family = unwind.family(pointer)
        primary = [part for part in family['ranges'] if part['runtimeTriple'][0] == pointer]
        need('floatParamValue.'+role, 'primaryOwnedRange', 1, len(primary))
        triple = primary[0]['runtimeTriple']
        if not 0 < triple[1]-pointer <= 8192:
            raise ValueError('floatParamValue.'+role+'.ownedRange: unbounded')
        ownership[role] = {'primary':triple}
        programs[role] = value_bridge.decode_rows(index, image.pe.image_base+pointer, triple[1]-pointer)
        if role == 'value':
            cold = [part for part in family['ranges'] if part['runtimeTriple'][0] != pointer]
            need('floatParamValue.caller', 'ownedColdRanges', 1, len(cold))
            cold = cold[0]
            child = cold['runtimeTriple']
            need('floatParamValue.caller', 'directOwnedColdChain', 1, len(cold['parentChain']))
            need('floatParamValue.caller', 'coldChainChild', child, cold['parentChain'][0]['child'])
            if not 0 < child[1]-child[0] <= 8192:
                raise ValueError('floatParamValue.caller.coldRange: unbounded')
            ownership[role].update(cold=child,coldParent=cold['parentChain'][0]['parent'])
            programs['cold'] = value_bridge.decode_rows(index, image.pe.image_base+child[0], child[1]-child[0])
    predicate = value_bridge.decode_rows(index, image.pe.image_base+entries['predicate']['pointerRva'], 18)
    selected = programs['tryValue'][:40]
    names = contract['claims']['predicate']['matchesDeclarations'] + [contract['claims']['constant']['selectorDeclaration']]
    symbols = value_bridge.declarations(image, context, contract['declarations'], names)
    getter = predicate_program(predicate, view['slots'], [symbols[n]['value'] for n in contract['claims']['predicate']['matchesDeclarations']])
    caller = caller_program(programs['value'], programs['cold'], ownership,
        entries['predicate']['pointerRva'], entries['tryValue']['pointerRva'], view['slots'])
    constant = constant_program(selected, ownership['tryValue']['primary'][:2], view['slots'],
        symbols[contract['claims']['constant']['selectorDeclaration']]['value'])

    def member_at(offset):
        matching = [name for name,slot in view['slots'].items() if slot == offset]
        need('floatParamValue.claims', 'memberSlotAliases', 1, len(matching))
        return matching[0]

    proved_claims = {
        'caller': {'normalPaths':caller['normalPaths'], 'fallbackArgument':1, 'outputBytes':caller['outputBytes'],
                   'calls':['predicate','tryValue'], 'return':'ordinary Single low32 bits',
                   'ownedWarmColdJoinRequired':True, 'arithmeticOrConversionOnSelectedTransfers':False},
        'constant': {'selectorMember':member_at(value_bridge.raw(selected[27])[2]),
                     'selectorDeclaration':contract['claims']['constant']['selectorDeclaration'],
                     'sourceMember':member_at(value_bridge.raw(selected[29])[-1]), 'outputArgument':1,
                     'outputBytes':constant['outputBytes'], 'successfulBooleanBits':value_bridge.raw(selected[31])[1],
                     'opaqueCallsOnSelectedPath':constant['opaqueCallsOnSelectedPath']},
        'predicate': {'selectorMember':member_at(value_bridge.raw(predicate[0])[2]),
                      'matchesDeclarations':contract['claims']['predicate']['matchesDeclarations'], 'return':getter['return']},
        'wrapper': {'holderMember':contract['methods']['wrapperView']['holder'], 'sameConcreteParameterDefinition':True,
                    'members':{'constValue':'ordinary Single','idRef':'ordinary Int32','paramSource':'ordinary Int32'}},
    }
    need('floatParamValue.claims', 'evaluatedMeaning', contract['claims'], proved_claims)
    return {'entries':entries, 'wrapperView':view, 'declarations':symbols, 'predicate':getter, 'caller':caller,
            'constant':constant, 'ownedRanges':ownership,
            'selectedWindows':[value_bridge.window(predicate),value_bridge.window(programs['value']),
                               value_bridge.window(programs['cold']),value_bridge.window(selected)],
            'provedClaims':proved_claims, 'evidenceBoundary':contract['evidenceBoundary'],
            'conditions':['compatible unchanged parameter storage where dereferenced',
                          'each selected initialized/ready context branch', 'ordinary closed Single ABI and complete retained frames',
                          'writable caller output and no object aliases corrupting its frame'],
            'runtimeReceiverOrProviderSelectionProved':False, 'storedCursorEvaluatorIntegrationProved':False}


def validate_float_param_value_claims(*,contract_path=CONTRACT_PATH,gameassembly=None,metadata=None):
    contract_path=Path(contract_path)
    try:
        contract_raw=contract_path.read_bytes();contract=json.loads(contract_raw)
        need('floatParamValue','schema',SCHEMA,contract.get('schema'));need('floatParamValue','status','reviewed',contract.get('status'))
        if gameassembly is None or metadata is None:
            return {'status':'missing','rows':[],'detail':'floatParamValue.explicitNativePair: both paths required'}
        pair={'gameassembly':Path(gameassembly),'metadata':Path(metadata)}
        if not all(p.is_file() for p in pair.values()):
            return {'status':'missing','rows':[],'detail':'floatParamValue.explicitNativePair: selected file missing'}
        native={name:_fingerprint(pair[key])['sha256'] for name,key in [('GameAssembly.dll','gameassembly'),('global-metadata.dat','metadata')]}
        paths=[Path(__file__),contract_path,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH,
               *[Path(row['path']) for row in _parser_source_snapshots(Path(__file__))]]
        sources=[_fingerprint(p) for p in sorted({p.resolve() for p in paths},key=str)]
        before=check_installed_native_inputs(native['GameAssembly.dll'],native['global-metadata.dat'],**pair)
        if before.status!='validated':return {'status':before.status,'rows':[],'detail':before.detail}
        row=evaluate(open_native_image(before.gameassembly,before.metadata),contract)
        after=check_installed_native_inputs(native['GameAssembly.dll'],native['global-metadata.dat'],gameassembly=before.gameassembly,metadata=before.metadata)
        if after.status!='validated':return {'status':after.status,'rows':[],'detail':after.detail}
        need('floatParamValue','sourceUnchanged',sources,[_fingerprint(Path(r['path'])) for r in sources])
        need('floatParamValue','declarationUnchanged',contract_raw,contract_path.read_bytes())
        return {'schema':SCHEMA,'status':'validated','rows':[row],'nativeInputs':native,'proofSources':sources,
                'nativeBefore':before.status,'nativeAfter':after.status}
    except (ValueError,KeyError,OSError,IndexError,TypeError,struct.error) as exc:
        return {'status':'pendingReview','rows':[],'detail':str(exc)[:1500],'source':str(contract_path)}


def check_output(output,protected):
    if not output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):raise ValueError('floatParamValue.output: report must be under reports/')
    _guard_output_path(output,protected)
    if output.exists():need('floatParamValue.output','owner',SCHEMA,json.loads(output.read_bytes()).get('schema'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,default=CONTRACT_PATH)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        if args.output is not None:check_output(args.output,[args.contract,args.gameassembly,args.metadata])
        result=validate_float_param_value_claims(contract_path=args.contract,gameassembly=args.gameassembly,metadata=args.metadata)
        if result['status']=='validated' and args.output is not None:
            check_output(args.output,[args.contract,args.gameassembly,args.metadata,*[Path(r['path']) for r in result['proofSources']]])
            need('floatParamValue.publication','sourcesUnchanged',result['proofSources'],[_fingerprint(Path(r['path'])) for r in result['proofSources']])
            atomic_write_text(args.output,json.dumps(result,indent=2)+'\n')
    except (ValueError,KeyError,OSError,TypeError) as exc:
        result={'status':'pendingReview','rows':[],'detail':str(exc)[:1500]}
    print(json.dumps({'status':result['status'],'rows':len(result['rows']),**({'detail':result['detail']} if 'detail' in result else {})},indent=2))
    return 0 if result['status']=='validated' else 2


if __name__=='__main__':raise SystemExit(main())
