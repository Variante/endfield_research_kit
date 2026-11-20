"""Authenticate reviewed native getter callers to named damage array roles."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.damage_snapshot_abi import require_ordinary_type, require_ordinary_pointer, require_ordinary_value_type, require_ordinary_int32_enum
from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.memorypack.corpus_gate import _parser_source_snapshots, _fingerprint

LIMIT = 4 * 1024**3
SCHEMA = 'endfield.damage-runtime-source-roles-native.v1'
CLAIM_SCHEMA = 'endfield.damage-runtime-source-roles-contract.v1'
CONTRACT_PATH = CONTRACTS_DIR/'damage_runtime_source_roles_native.json'


def fingerprint(path, limit):
    path=Path(path).resolve()
    before=path.stat()
    if before.st_size>limit:
        raise ValueError('native role proof source budget exceeded')
    pin=_fingerprint(path)
    after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
        raise ValueError('native role proof source changed while hashing')
    return {'path':str(path),'bytes':pin['length'],'sha256':pin['sha256'].lower()}


def load_roles(*, gameassembly, metadata):
    contract, digest = read_reviewed_contract(CONTRACT_PATH,schema=CLAIM_SCHEMA,status='reviewed',label='damageRuntimeSourceRoles')
    pins=contract['nativeInputs']
    gate=check_installed_native_inputs(pins['gameAssemblySha256'],pins['metadataSha256'],gameassembly=gameassembly,metadata=metadata)
    source_paths={Path(p['path']).resolve() for p in _parser_source_snapshots(Path(__file__))}
    source_paths.update((NATIVE_MAPPER_PATH.resolve(),METADATA_HELPER_PATH.resolve()))
    sources=[fingerprint(path,LIMIT) for path in sorted(source_paths)]
    result={'schema':SCHEMA,'status':gate.status,'detail':gate.detail,'roles':[],
        'claimContract':str(CONTRACT_PATH),'claimContractSha256':digest,'claimContractSchema':CLAIM_SCHEMA,
        'nativeInputs':{'gameAssemblySha256':gate.gameassembly_sha256,'metadataSha256':gate.metadata_sha256},
        'failures':[],'proofSources':sources,'evidenceBoundary':contract['evidenceBoundary']}
    if not gate.validated:
        return result
    try:
        image=open_native_image(gate.gameassembly,gate.metadata)
        index=BodyIndex(image)
        selected=NativeReferenceContext(image,index=index)
        spec=contract['method']
        body=index.body(spec['type'],spec['method'])
        if body.pointer-image.pe.image_base != int(spec['rva'],16) or body.size != spec['bytes']:
            raise ValueError('named dump entry/extent differs from reviewed contract')
        raw=index.pe.bytes_at_va(body.pointer,body.size)
        if hashlib.sha256(raw).hexdigest().lower() != spec['sha256'].lower():
            raise ValueError('reviewed dump body bytes differ')
        require_ordinary_value_type(selected,index.types[spec['type']].byval_type_index,spec['type'],'sourceRole.receiver')
        _check_named_provider(index,body.pointer,body.symbol,[],'void',is_static=False)
        getter=contract['getter']
        provider=index.body(getter['type'],getter['method'])
        getter_owner=index.types[getter['type']]
        require_ordinary_type(selected,getter_owner.byval_type_index,getter['type'],'sourceRole.Attributes',reference_kind=0x12)
        definitions=[index.metadata.methods[n['methodIndex']] for n in index.names_by_pointer.get(provider.pointer,())
                     if f"{n.get('type')}.{n.get('method')}"==provider.symbol]
        if not definitions:
            raise ValueError('typed getter definition absent')
        for definition in definitions:
            parameters=list(index.metadata.parameters_for(definition))
            if definition.declaring_type!=getter_owner.index or definition.flags&0x10 or len(parameters)!=1:
                raise ValueError('typed getter receiver or arity differs')
            require_ordinary_int32_enum(selected,parameters[0].type_index,getter['parameter'],'sourceRole.attributeIndex')
            require_ordinary_type(selected,definition.return_type,getter['returnType'],'sourceRole.DoubleReturn')
            if index.parameter_location(provider.pointer,provider.symbol,index.metadata.string(parameters[0].name_index))!=('register','rdx'):
                raise ValueError('typed getter enum parameter is not in RDX')
        actor=contract['actorAttributesField']
        fo,ft,offset=selected.field(actor['field'])
        if fo != actor['field'].split('::')[0] or ft != actor['type'] or offset != actor['metadataOffset']:
            raise ValueError('actor current Attributes declaration differs')
        owner=index.types[spec['type']]
        for declaration in contract['roles']:
            field=declaration['destinationArrayField']
            fo,ft,offset=selected.field(field)
            if fo != spec['type'] or ft != 'double[]' or offset != declaration['metadataOffset']:
                raise ValueError('named role destination Double array declaration differs')
            fields=[f for f in index.metadata.fields_for(owner) if index.metadata.string(f.name_index)==field.split('::')[1]]
            if len(fields)!=1:
                raise ValueError('array role field declaration not unique')
            abi=require_ordinary_type(selected,fields[0].type_index,'double[]','sourceRole.array',reference_kind=0x1d)
            record=index.pe.bytes_at_va(selected.type_pointer(fields[0].type_index),16)
            element=int.from_bytes(record[:8],'little')
            element_abi=require_ordinary_pointer(selected,element,runtime_type_name(index.pe,index.metadata,element),'double','sourceRole.element')
            fo,ft,lock_offset=selected.field(declaration['lockStorageField'])
            if fo != spec['type'] or ft != declaration['lockStorageType'] or lock_offset != declaration['lockMetadataOffset']:
                raise ValueError('named role ObjectPtr storage declaration differs')
            call_offset=declaration['getterCallOffset']
            call=raw[call_offset:call_offset+5]
            if len(call)!=5 or call[0]!=0xe8 or body.pointer+call_offset+5+int.from_bytes(call[1:],'little',signed=True)!=provider.pointer:
                raise ValueError('role caller does not target typed named Double getter')
            window=declaration['transferWindow']
            block=raw[window['offset']:window['offset']+window['bytes']]
            if len(block)!=window['bytes'] or hashlib.sha256(block).hexdigest().lower()!=window['sha256'].lower():
                raise ValueError('role getter-to-array transfer window differs')
            result['roles'].append({**declaration,'getterCallerRva':body.pointer-image.pe.image_base+call_offset+5,
                'rawOffset':offset-contract['valueHeaderBytes'],'valueHeaderBytes':contract['valueHeaderBytes'],
                'arrayABI':abi,'elementABI':element_abi,'evidenceBoundary':'conditional','conditions':contract['conditions']})
        result['reviewedProgram']=contract['reviewedProgram']
    except (OSError,ValueError,RuntimeError,KeyError,IndexError) as exc:
        result.update(status='pendingReview',detail=str(exc)[:1600],roles=[],failures=[{'check':'current-native-array-role-proof','detail':str(exc)[:1600]}])
    after=check_installed_native_inputs(pins['gameAssemblySha256'],pins['metadataSha256'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if not after.validated:
        result.update(status=after.status,detail=after.detail,roles=[])
        result['failures'].append({'check':'native-inputs-after','source':str(gate.gameassembly),
            'expected':pins,'actual':{'status':after.status,'detail':after.detail,
                'gameAssemblySha256':after.gameassembly_sha256,'metadataSha256':after.metadata_sha256}})
        return result
    drift=[]
    for expected in sources:
        try:
            actual=fingerprint(Path(expected['path']),LIMIT)
        except (OSError,ValueError) as exc:
            actual={'error':type(exc).__name__,'detail':str(exc)[:1200]}
        if actual!=expected:
            drift.append({'check':'proof-source-after','source':expected['path'],
                'expected':expected,'actual':actual})
    try:
        contract_after=fingerprint(CONTRACT_PATH,LIMIT)
    except (OSError,ValueError) as exc:
        contract_after={'error':type(exc).__name__,'detail':str(exc)[:1200]}
    if str(contract_after.get('sha256','')).lower()!=digest.lower():
        drift.append({'check':'claim-contract-after','source':str(CONTRACT_PATH),
            'expected':{'sha256':digest},'actual':contract_after})
    if drift:
        result.update(status='pendingReview',detail=f'proof source changed: {drift[0]["source"]}',roles=[])
        result['failures'].extend(drift)
    elif not result['failures']:
        result.update(status='validated',detail='')
    return result


def main(argv=None):
    from scripts.repo_paths import REPO_ROOT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True)
    parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    output=args.output.resolve()
    if not output.is_relative_to((REPO_ROOT/'reports').resolve()):
        parser.error('output must be under reports/')
    result=load_roles(gameassembly=args.gameassembly,metadata=args.metadata)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','detail','roles','failures')}))
    return 0 if result['status']=='validated' else 1


if __name__=='__main__':
    raise SystemExit(main())
