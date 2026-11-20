"""Bounded HitStop config-load facts; exported asset selection remains unresolved."""
from pathlib import Path
import argparse
import json
import struct

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.repo_paths import REPO_ROOT
from scripts.game_data.il2cpp.context import literal_record,unresolved_usage_index
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols,validate_claims
from scripts.game_data.memorypack.pooled_source_helper import check_unity_input

SCHEMA='endfield.skill-hitstop-config-load-native-contract.v1'
LABEL='skillHitStopConfigLoadNative'
CONTRACT_PATH=CONTRACTS_DIR/'skill_hitstop_config_load_native.json'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def _literal(image,row):
    pe=image.pe;md=image.metadata;base=pe.image_base;at=base+row['instructionRva'];raw=pe.bytes_at_va(at,7)
    need('literal-load-bytes',raw==bytes.fromhex(row['instructionHex'])and raw[:2]in(b'\x48\x8b',b'\x4c\x8b')and raw[2]&0xc7==5)
    cell=at+7+struct.unpack_from('<i',raw,3)[0];need('literal-cell',cell-base==row['cellRva'])
    table,pool=md.sections['stringLiteral'],md.sections['stringLiteralData'];usage=pe.bytes_at_va(cell,8)
    index=unresolved_usage_index(usage,table.size//8,tag=5,source=LABEL,offset=cell)
    need('literal-index',index==row['literalIndex']);offset=table.offset+index*8
    start,size=literal_record(md.buf[offset:offset+8],pool.size,source=LABEL,offset=offset)
    need('literal-value',md.buf[pool.offset+start:pool.offset+start+size].decode('utf-8')==row['value'])


def _validate(image,fact):
    need('identity',fact.get('schema')==SCHEMA and fact.get('status')=='reviewed')
    for method in fact['methods']:image.validate_method_row(method,label=LABEL)
    image.check_windows(fact['codeWindows'],label=LABEL)
    field=fact['field'];actual=NativeReferenceContext(image).field(field['owner']+'::'+field['name'])
    need('typed-config-field',tuple(actual)==(field['owner'],field['typeName'],field['offset']))
    request=derive_typed_usage_context(image,fact['selectedRequest']['instructionRva'],label=LABEL+'.request')
    validate_claims(fact['selectedRequest'],request,label=LABEL+'.request')
    for row in fact['literalLoads']:_literal(image,row)
    span=fact['localStoreSpan'];base=image.pe.image_base;raw=bytes.fromhex(span['rawHex'])
    ranges=image.unwind_index.family(fact['callerMethod'][3])['ranges']
    expected=sorted((row['startRva'],row['endRva'])for row in fact['callerRanges'])
    need('caller-complete-unwind-family',expected==sorted(tuple(row['runtimeTriple'][:2])for row in ranges))
    need('local-span-owned-by-caller',any(start<=span['startRva']and span['startRva']+len(raw)<=end for start,end in expected))
    need('caller-selected-method',fact['callerMethod']in fact['methods'])
    need('router-selected-method',fact['routerMethod']in fact['methods'])
    # No compiled entry exists for this closed MethodSpec in the reviewed
    # table. Keep exact local facts without promoting an unjoined body owner.
    need('local-evidence-scope',fact.get('proofTier')=='direct-caller-and-physical-target-links-only'
        and fact.get('compiledTargetClosedDeclarationProved')is False
        and fact.get('compiledTargetJoinRequired')is False)
    router=image.pe.bytes_at_va(base+fact['routerCallSiteRva'],5)
    need('loader-to-selected-router',router[0]==0xe8 and fact['routerCallSiteRva']+5+struct.unpack_from('<i',router,1)[0]==fact['routerMethod'][3])
    need('router-call-in-loader-window',any(window['startRva']==span['targetRva']
        and window['startRva']<=fact['routerCallSiteRva']and fact['routerCallSiteRva']+5<=window['endRva']for window in fact['codeWindows']))
    need('local-argument-return-store-bytes',image.pe.bytes_at_va(base+span['startRva'],len(raw))==raw)
    call=image.pe.bytes_at_va(base+span['callSiteRva'],5)
    need('selected-loader-call',call[0]==0xe8 and span['callSiteRva']+5+struct.unpack_from('<i',call,1)[0]==span['targetRva'])
    store=image.pe.bytes_at_va(base+span['storeSiteRva'],7)
    need('same-config-field-store',store[:3]==b'\x48\x89\x83'and struct.unpack_from('<i',store,3)[0]==field['offset'])
    claims=fact['contextClaims'];context=ContextSymbols(image).context(claims['definition'],is_method=True,slots=[row['relativeSlot']for row in claims['entries']])
    validate_claims(claims,context,label=LABEL+'.generic-context')
    return dict(status='validated',proofTier=fact['proofTier'],nativeInputs=fact['nativeInputs'],
        compiledTargetClosedDeclarationProved=False,nativeAdmissionGranted=False,
        facts=dict(providedMethodInfo=request,field=field,
        literals=[dict(instructionRva=row['instructionRva'],value=row['value'])for row in fact['literalLoads']],
        loadStoreSite=span['storeSiteRva'],loadCallSite=span['callSiteRva'],physicalCallTargetRva=span['targetRva'],physicalTargetToNamedRouterCall=fact['routerCallSiteRva']),
        assetCandidate=fact['assetCandidate'],unresolvedCalls=fact['unresolvedCalls'],
        selectedLibraryProved=False,runtimeExecutionProved=False,evidenceBoundary=fact['evidenceBoundary'])


def validate_current_native_contract(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
    path=Path(contract_path)
    try:
        raw=path.read_bytes();fact=json.loads(raw);pins=fact['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=Path(gameassembly),metadata=Path(metadata))
        if gate.status!='validated':return dict(status=gate.status,selectedLibraryProved=False,detail=gate.detail)
        if failure:=check_unity_input(gate.gameassembly,pins):return dict(selectedLibraryProved=False,**failure)
        result=_validate(open_native_image(gate.gameassembly,gate.metadata),fact)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':return dict(status=after.status,selectedLibraryProved=False,detail=after.detail)
        if failure:=check_unity_input(gate.gameassembly,pins):return dict(selectedLibraryProved=False,**failure)
        need('declaration-bookend',raw==path.read_bytes())
        return result
    except(ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError)as error:
        return dict(selectedLibraryProved=False,**native_validation_failure(error,label=LABEL,source_path=path))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True)
    parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--contract',type=Path,default=CONTRACT_PATH)
    parser.add_argument('--output',type=Path,default=REPO_ROOT/'reports/game_data/skill_hitstop_config_load_native.json')
    args=parser.parse_args(argv)
    if not args.output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):parser.error('--output must be below reports/')
    result=validate_current_native_contract(gameassembly=args.gameassembly,metadata=args.metadata,contract_path=args.contract)
    if result.get('status')=='validated':
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result.get('status')=='validated'else 2


if __name__=='__main__':raise SystemExit(main())
