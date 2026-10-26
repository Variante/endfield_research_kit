"""Authenticate the current stored camera read/store component; owner admission is separate.

Evidence and admission boundary:

Direct selected parent read/store proof includes inserted custom name,
target-type argument positions and move-state CustomPrefab enum. The move-
state and camera-target Params keep independent signed-Int32/pooled-source
gates. Historical removed cursor spans cannot establish current owner
closure, default selection or camera effects.
"""
from __future__ import annotations
import json
if __name__=="__main__" and not __package__:
    raise SystemExit("Run python -m scripts.game_data.levelscript_track_camera_native")
from pathlib import Path
from scripts.common import check_installed_native_inputs,sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.levelscript_family_regenerate import Build,regenerate_formatter
from scripts.game_data.memorypack.pooled_source_helper import check_unity_input

SCHEMA='endfield.levelscript-track-camera-native-contract.v2'
LABEL='levelscriptTrackCameraNative'
CONTRACT_PATH=CONTRACTS_DIR/'levelscript_track_camera_native.json'
LAYOUT_PATH=CONTRACTS_DIR.parent/'codecs/levelscript/action_map_layouts.json'
KEYS={'schema','status','evidenceBoundary','evidenceNote','nativeInputs','route','dispatcher','methods','codeWindows','memberCountInstruction','readerHelpers','orderedReads','setters','nestedContexts','sourceReceipts','inlineSetterMembers','enumTypes'}

def _contract(path):
    fact=json.loads(Path(path).read_bytes());route=fact['route'];enums=fact['enumTypes']
    if (set(fact)!=KEYS or fact['schema']!=SCHEMA or fact['status']!='exact-current-build'
            or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}
            or route['family']!='ActionBase' or route['typeName']!='Beyond.Gameplay.Actions.EnterDollyTrackCamera'
            or fact['sourceReceipts'] or len(enums)!=1
            or enums[0]['typeName']!='Beyond.Gameplay.Actions.EnterDollyTrackCamera+TrackCameraMoveState'
            or enums[0]['underlyingType']!='int'):
        raise ValueError(LABEL+'.contract:shape')
    layouts=json.loads(LAYOUT_PATH.read_bytes());rows=[r for r in layouts['layouts'] if (r['family'],r['wrapperName'])==(route['family'],route['wrapperName'])]
    if (layouts['schema']!='endfield.action-map-layouts.v5' or len(rows)!=1
            or rows[0].get('nativeGate')!='levelscript_track_camera_native'
            or (rows[0]['memberCount'],rows[0]['fields'])!=(route['serializedMemberCount'],route['fields'])):
        layout=rows[0] if len(rows)==1 else {};expected=route['fields'];actual=layout.get('fields',[])
        first=next((i for i in range(max(len(expected),len(actual))) if expected[i:i+1]!=actual[i:i+1]),None)
        failure=dict(gate='contract:reviewed-layout-join',wrapper=route['wrapperName'],memberIndex=first,
            expected=dict(memberCount=route['serializedMemberCount'],field=expected[first:first+1] if first is not None else []),
            actual=dict(memberCount=layout.get('memberCount'),field=actual[first:first+1] if first is not None else []),
            sources=[dict(path=str(p),sha256=sha256_file(p)) for p in (path,LAYOUT_PATH)])
        error=ValueError(LABEL+'.contract:reviewed-layout-join:'+str(failure));error.diagnostic=failure;raise error
    return fact

def _validate_native(image,fact):
    actual=regenerate_formatter(fact,Build(image,fact['nativeInputs']))
    validate_claims(fact,actual,label=LABEL+'.proof');validate_claims(actual,fact,label=LABEL+'.declaration')

def validate_track_camera_native_contract(*,contract_path=CONTRACT_PATH,game_root=None,gameassembly=None,metadata=None,export_root=None,ledger_path=None):
    try:
        path=Path(contract_path);raw=path.read_bytes();layout=LAYOUT_PATH.read_bytes();fact=_contract(path);pins=fact['nativeInputs']
        if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both paths required')
        root=Path(game_root) if game_root is not None else None
        args=dict(gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],**args)
        if gate.status!='validated':return dict(status=gate.status,failedCheck='installed-native-inputs',detail=gate.detail)
        failed=check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        _validate_native(open_native_image(gate.gameassembly,gate.metadata),fact)
        # This component carries no current source receipts; never reuse the old build's spans.
        if export_root is not None or ledger_path is not None:raise ValueError(LABEL+'.source:current-owner-receipts-unproved')
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':return dict(status=after.status,failedCheck='native-inputs-changed',detail=after.detail)
        failed=check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        if raw!=path.read_bytes() or layout!=LAYOUT_PATH.read_bytes():raise ValueError(LABEL+'.contract:declaration changed during validation')
        route=fact['route']
        return dict(status='validated',evidenceBoundary=fact['evidenceBoundary'],route={k:route[k] for k in ('family','tag','wrapperName','fields')},enumMembers=[[r['name'],r['id']] for r in fact['enumTypes'][0]['members']],sourceReceiptsChecked=0)
    except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError) as error:
        audit=native_validation_failure(error,label=LABEL,source_path=contract_path)
        if hasattr(error,'diagnostic'):audit['failedCheck']=error.diagnostic['gate']
        return audit

def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('contract','game-root','gameassembly','metadata','export-root','ledger'):parser.add_argument('--'+name,type=Path,default=CONTRACT_PATH if name=='contract' else None)
    args=parser.parse_args();audit=validate_track_camera_native_contract(contract_path=args.contract,game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata,export_root=args.export_root,ledger_path=args.ledger)
    print(json.dumps(audit,indent=2));return 0 if audit['status']=='validated' else 2

if __name__=='__main__':raise SystemExit(main())
