"""Evaluate named closed Int64 Param consumer claims on the explicitly selected build."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

if __name__ == '__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.levelscript_long_param_value_native')

from scripts.common import check_installed_native_inputs
from scripts.game_data import levelscript_param_value_bridge as value_bridge
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.il2cpp.native_image import METADATA_HELPER_PATH, NATIVE_MAPPER_PATH, open_native_image
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _guard_output_path, _parser_source_snapshots
from scripts.game_data.memorypack.scalar_param_native import need
from scripts.repo_paths import REPO_ROOT

SCHEMA = 'endfield.levelscript-long-param-value-native-claims.v1'
CONTRACT_PATH = CONTRACTS_DIR / 'levelscript_long_param_value_native_claims.json'


def predicate_program(rows, slots, declarations):
    source = bytes((slots['paramSource'],)).hex()
    value_bridge.shape(rows, ['8379'+source+'ff', None, 'b001', 'c3', '8379'+source+'fe', '0f94c0', 'c3'], 'longParamValue.predicate')
    need('longParamValue.predicate', 'otherMarkerDestination', rows[4][0], value_bridge.target(rows[1], b'\x75'))
    need('longParamValue.predicate', 'markerDeclarations', [-1, -2], declarations)
    return {'normalPaths': 2, 'return': 'ordinary Boolean low8', 'returnRegister':'AL', 'storesOrCalls': 0}


def caller_program(rows, predicate_rva, try_rva, slots):
    ref = bytes((slots['idRef'],)).hex()
    forms = ['48895c2410','48896c2418','4889742420','57','4883ec20','4983793800',
             '498bd9','418ae8','488bf2','488bf9',None,'488bcb',None,'48c744243000000000',
             '4885ff',None,'488b4338','488b4808','4883792000',None,'ff11','488b5338',
             '488bcf','488b5208',None,'84c0',None,'837f'+ref+'ff',None,'4c8b4b38','488d542430',
             '448ac5','488bcf','4d8b4910',None,'84c0','488b442430',None,'488bc6',
             '488b5c2438','488b6c2440','488b742448','4883c420','5f','c3']
    value_bridge.shape(rows, forms, 'longParamValue.caller')
    edges = {10:(b'\x75',13),15:(b'\x74',38),19:(b'\x75',21),26:(b'\x74',29),
             28:(b'\x74',38),37:(b'\x75',39)}
    for n,(opcode,to) in edges.items():
        need('longParamValue.caller', f'destination[{n}]', rows[to][0], value_bridge.target(rows[n], opcode))
    need('longParamValue.caller', 'actualPredicateCall', predicate_rva, value_bridge.target(rows[24], b'\xe8'))
    need('longParamValue.caller', 'actualTryCall', try_rva, value_bridge.target(rows[34], b'\xe8'))
    value_bridge.target(rows[12], b'\xe8')
    paths=[]

    def walk(n,path):
        if n in path or len(path)>=45:
            raise ValueError('longParamValue.caller.CFG: cycle or oversized path')
        path=path+[n]
        if n==44: paths.append(path); return
        if n in edges:
            if n in (10,19): walk(edges[n][1],path)
            else: walk(edges[n][1],path);walk(n+1,path)
        else: walk(n+1,path)

    walk(0,[])
    need('longParamValue.caller', 'normalPaths', 6, len(paths))
    for path in paths:
        need('longParamValue.caller', 'retainedFrame', True,
             all(n in path for n in (0,1,2,3,4,8,9,13,39,40,41,42,43,44)))
    need('longParamValue.caller', 'outputPaths', 2, sum(38 not in path for path in paths))
    return {'normalPaths':6, 'fallbackPaths':4, 'outputPaths':2, 'frameDelta':40,
            'outputLocalOffset':48, 'return':'RAX full64 current output or original incoming RDX fallback bits',
            'initializerOrReadyCalleeEffectsProved':False}


def constant_program(parts, owner, slots, declaration):
    source=bytes((slots['paramSource'],)).hex();value=bytes((slots['constValue'],)).hex()
    forms=[
        ['4889542410','53','56','57','4154','4155','4156','4157','4881ece0000000',
         '498bf9','458ae8','4c8bf2','488bf1','33db','49395938',None],
        ['48895c2430','48899c2438010000','0f57c0','33c0','0f118424b0000000',
         '0f118424c0000000','48898424d0000000','4885f6',None,'488b4738','488b4808','48395920',None],
        ['395e'+source,None], ['488b46'+value,'498906','b801000000',None],
        ['4881c4e0000000','415f','415e','415d','415c','5f','5e','5b','c3'],
    ]
    need('longParamValue.constant', 'parts', 5, len(parts))
    seen=set()
    for n,(rows,pattern) in enumerate(zip(parts,forms)):
        value_bridge.shape(rows,pattern,'longParamValue.constant.part'+str(n))
        for row in rows:
            if row[0] in seen or not owner[0]<=row[0]<row[0]+len(value_bridge.raw(row))<=owner[1]:
                raise ValueError(f'longParamValue.constant.ownedInstruction: rva={row[0]:#x}')
            seen.add(row[0])
    for part,opcode,next_part in [(0,b'\x0f\x85',1),(1,b'\x75',2),(2,b'\x0f\x84',3),(3,b'\xe9',4)]:
        need('longParamValue.constant', 'actualFragmentEdge', parts[next_part][0][0], value_bridge.target(parts[part][-1],opcode))
    refused=value_bridge.target(parts[1][8],b'\x0f\x84')
    if refused in seen: raise ValueError('longParamValue.constant.nullGuard: destination inside selected path')
    need('longParamValue.constant', 'sourceDeclaration', 0, declaration)
    return {'normalPaths':1, 'selectedInstructions':len(seen), 'frameDelta':280,
            'outputBytes':8, 'output':'original parameter-compatible source QWORD to original explicit byref output',
            'return':'EAX=1 after complete output write', 'opaqueCallsOnSelectedPath':0,
            'nonconstantOrInitializerBehaviorProved':False}


def evaluate(image,contract):
    context=NativeReferenceContext(image);index=image.body_index
    entries=value_bridge.named_entries(image,contract['methods'],context,primitive_name='Int64',primitive_kind=10)
    bridge=value_bridge.wrapper_view(image,context,contract['methods']['wrapperView'],entries['value']['parameterDefinition'],index,primitive_name='Int64',primitive_type='long',primitive_kind=10,store_prefix=b'\x48\x89\x50')
    table_rva,size,table=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(table,lambda rva,n:image.pe.bytes_at_va(image.pe.image_base+rva,n),table_rva=table_rva,image_size=size)
    parts={};ownership={}
    for role in ('value','tryValue'):
        pointer=entries[role]['pointerRva'];family=unwind.family(pointer)
        primary=[part for part in family['ranges'] if part['runtimeTriple'][0]==pointer]
        need('longParamValue.'+role,'primaryOwnedRange',1,len(primary));triple=primary[0]['runtimeTriple']
        ownership[role]=triple
        if not 0<triple[1]-triple[0]<=8192: raise ValueError('longParamValue.'+role+'.ownedRange: unbounded')
        parts[role]=value_bridge.decode_rows(index,image.pe.image_base+pointer,triple[1]-pointer)
    predicate=value_bridge.decode_rows(index,image.pe.image_base+entries['predicate']['pointerRva'],17)
    attempt={row[0]:row for row in parts['tryValue']};start=entries['tryValue']['pointerRva']
    def take(at,count):
        selected=[]
        for _ in range(count):
            if at not in attempt: raise ValueError(f'longParamValue.tryValue.instructionStart: {at:#x}')
            row=attempt[at];selected.append(row);at+=len(value_bridge.raw(row))
        return selected
    selected=[take(start,16)]
    selected.append(take(value_bridge.target(selected[0][-1],b'\x0f\x85'),13))
    selected.append(take(value_bridge.target(selected[1][-1],b'\x75'),2))
    selected.append(take(value_bridge.target(selected[2][-1],b'\x0f\x84'),4))
    selected.append(take(value_bridge.target(selected[3][-1],b'\xe9'),9))
    names=contract['claims']['predicate']['matchesDeclarations']+[contract['claims']['constant']['selectorDeclaration']]
    symbols=value_bridge.declarations(image,context,contract['declarations'],names)
    getter=predicate_program(predicate,bridge['slots'],[symbols[n]['value'] for n in contract['claims']['predicate']['matchesDeclarations']])
    caller=caller_program(parts['value'],entries['predicate']['pointerRva'],entries['tryValue']['pointerRva'],bridge['slots'])
    constant=constant_program(selected,ownership['tryValue'][:2],bridge['slots'],symbols[contract['claims']['constant']['selectorDeclaration']]['value'])
    def member_at(offset):
        matching=[name for name,slot in bridge['slots'].items() if slot==offset]
        need('longParamValue.claims','memberSlotAliases',1,len(matching));return matching[0]
    proved_claims={
        'caller':{'normalPaths':caller['normalPaths'],'fallbackArgument':['rcx','rdx','r8','r9'].index('rdx'),
                  'outputBytes':8 if value_bridge.raw(parts['value'][36])[0]&8 else 4,
                  'calls':['predicate','tryValue'],'return':'ordinary Int64'},
        'constant':{'selectorMember':member_at(value_bridge.raw(selected[2][0])[-1]),
                    'selectorDeclaration':contract['claims']['constant']['selectorDeclaration'],
                    'sourceMember':member_at(value_bridge.raw(selected[3][0])[-1]),
                    'outputArgument':['rcx','rdx','r8','r9'].index('rdx'),
                    'outputBytes':8 if value_bridge.raw(selected[3][1])[0]&8 else 4,
                    'successfulBooleanBits':int.from_bytes(value_bridge.raw(selected[3][2])[1:],'little'),
                    'opaqueCallsOnSelectedPath':constant['opaqueCallsOnSelectedPath']},
        'predicate':{'selectorMember':member_at(value_bridge.raw(predicate[0])[2]),
                     'matchesDeclarations':contract['claims']['predicate']['matchesDeclarations'],
                     'return':getter['return']},
        'wrapper':{'holderMember':contract['methods']['wrapperView']['holder'],
                   'sameConcreteParameterDefinition':True,
                   'members':{'constValue':'ordinary Int64','idRef':'ordinary Int32','paramSource':'ordinary Int32'}},
    }
    need('longParamValue.claims','evaluatedMeaning',contract['claims'],proved_claims)
    return {'entries':entries,'wrapperView':bridge,'declarations':symbols,'predicate':getter,'caller':caller,'constant':constant,
            'ownedRanges':ownership,'selectedWindows':[value_bridge.window(predicate),value_bridge.window(parts['value']),*[value_bridge.window(rows) for rows in selected]],
            'provedClaims':proved_claims,'evidenceBoundary':contract['evidenceBoundary'],'conditions':['compatible unchanged parameter storage where dereferenced',
            'each selected initialized/ready context branch','ordinary closed ABI and complete retained frames',
            'writable caller output and no object aliases corrupting its frame'],
            'runtimeReceiverOrProviderSelectionProved':False,'storedCursorEvaluatorIntegrationProved':False}


def validate_long_param_value_claims(*,contract_path=CONTRACT_PATH,gameassembly=None,metadata=None):
    contract_path=Path(contract_path)
    try:
        contract_raw=contract_path.read_bytes();contract=json.loads(contract_raw)
        need('longParamValue','schema',SCHEMA,contract.get('schema'));need('longParamValue','status','reviewed',contract.get('status'))
        if gameassembly is None or metadata is None:
            return {'status':'missing','rows':[],'detail':'longParamValue.explicitNativePair: both paths required'}
        pair={'gameassembly':Path(gameassembly),'metadata':Path(metadata)}
        if not all(p.is_file() for p in pair.values()):
            return {'status':'missing','rows':[],'detail':'longParamValue.explicitNativePair: selected file missing'}
        native={name:_fingerprint(pair[key])['sha256'] for name,key in [('GameAssembly.dll','gameassembly'),('global-metadata.dat','metadata')]}
        paths=[Path(__file__),contract_path,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH,
               *[Path(row['path']) for row in _parser_source_snapshots(Path(__file__))]]
        sources=[_fingerprint(p) for p in sorted({p.resolve() for p in paths},key=str)]
        before=check_installed_native_inputs(native['GameAssembly.dll'],native['global-metadata.dat'],**pair)
        if before.status!='validated':return {'status':before.status,'rows':[],'detail':before.detail}
        row=evaluate(open_native_image(before.gameassembly,before.metadata),contract)
        after=check_installed_native_inputs(native['GameAssembly.dll'],native['global-metadata.dat'],gameassembly=before.gameassembly,metadata=before.metadata)
        if after.status!='validated':return {'status':after.status,'rows':[],'detail':after.detail}
        need('longParamValue','sourceUnchanged',sources,[_fingerprint(Path(r['path'])) for r in sources])
        need('longParamValue','declarationUnchanged',contract_raw,contract_path.read_bytes())
        return {'schema':SCHEMA,'status':'validated','rows':[row],'nativeInputs':native,'proofSources':sources,
                'nativeBefore':before.status,'nativeAfter':after.status}
    except (ValueError,KeyError,OSError,IndexError,TypeError,struct.error) as exc:
        return {'status':'pendingReview','rows':[],'detail':str(exc)[:1500],'source':str(contract_path)}


def check_output(output,protected):
    if not output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):raise ValueError('longParamValue.output: report must be under reports/')
    _guard_output_path(output,protected)
    if output.exists():need('longParamValue.output','owner',SCHEMA,json.loads(output.read_bytes()).get('schema'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,default=CONTRACT_PATH)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        if args.output is not None:check_output(args.output,[args.contract,args.gameassembly,args.metadata])
        result=validate_long_param_value_claims(contract_path=args.contract,gameassembly=args.gameassembly,metadata=args.metadata)
        if result['status']=='validated' and args.output is not None:
            check_output(args.output,[args.contract,args.gameassembly,args.metadata,*[Path(r['path']) for r in result['proofSources']]])
            need('longParamValue.publication','sourcesUnchanged',result['proofSources'],[_fingerprint(Path(r['path'])) for r in result['proofSources']])
            atomic_write_text(args.output,json.dumps(result,indent=2)+'\n')
    except (ValueError,KeyError,OSError,TypeError) as exc:
        result={'status':'pendingReview','rows':[],'detail':str(exc)[:1500]}
    print(json.dumps({'status':result['status'],'rows':len(result['rows']),**({'detail':result['detail']} if 'detail' in result else {})},indent=2))
    return 0 if result['status']=='validated' else 2


if __name__=='__main__':raise SystemExit(main())
