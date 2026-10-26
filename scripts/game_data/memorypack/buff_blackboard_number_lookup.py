"""Current complete managed-fallback lookup composed with proved dependencies.

This joins runtime pair/list representations and pure key comparison to the
whole selected loop and returns. It never supplies live receivers, selects
Burst state or promotes the proof to all dispatches, actions or Buff roots.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.memorypack import buff_blackboard_pair_list as pair_owner
from scripts.game_data.memorypack import buff_blackboard_key_comparison as comparison_owner
from scripts.game_data.memorypack import blackboard_number_lookup as control
from scripts.game_data.memorypack.closed_scalar_consumers import signature
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError,_fingerprint,_package_import_closure

LABEL='buffBlackboardNumberLookup'
CONTRACT_PATH=CONTRACTS_DIR/'memorypack_blackboard_number_lookup_native.json'


def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.memorypack-blackboard-number-lookup-native-contract.v1',status='exact-current-build',label=LABEL)
    if c.get('mode')!=control.MODE:raise ValueError(f'{LABEL}.contract:mode')
    return c


def _fail(check,expected,actual):
    c=_contract();error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,record='Beyond.Blackboard._TryGetNumber',nativeInputs=c['nativeInputs'])
    error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error


def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'wholeActionAdmitted':False,'wholeRootAdmitted':False}


def _validate_image(image,c,pair,comparison,pc,cc,*,fail):
    method=c['method']
    if method[1:3]!=['Beyond.Blackboard','_TryGetNumber']:fail('lookup-method-name','actual owned number lookup',method)
    signature(image,method,(2,'bool'),[(14,'string',False),(13,'double',True)],static=False,fail=fail)
    index=BodyIndex(image);entry=image.pe.image_base+method[3]
    if entry not in index.extents:fail('lookup-unwind-entry','actual registered entry extent',method)
    owned={(entry-image.pe.image_base,index.extents[entry]-image.pe.image_base)}
    owned.update((at-image.pe.image_base,at+size-image.pe.image_base) for at,size in index.chained_fragments.get(entry,()))
    windows={(w['startRva'],w['endRva']) for w in c['codeWindows']}
    if len(windows)!=len(c['codeWindows']) or windows!=owned:
        fail('lookup-complete-unwind-ownership','all exact entry/chained extents of this method',sorted(windows))
    string=pc['stringLayout'];fields=[f for f in string['fields'] if f['name']=='_firstChar']
    if (string['name']!='System.String' or len(fields)!=1 or fields[0]['type']['kind']!=3 or fields[0]['type']['name']!='char'
            or int.from_bytes(bytes.fromhex(fields[0]['type']['rawHex'])[8:10],'little')&0x10
            or string['offsets']['_firstChar']!=c['stringFirstCharOffset']):
        fail('lookup-string-first-char','same current owned instance Char field',fields)
    if c['blocks']['callback'][:4]!=cc['lookupCallbackFragment']['instructions']:
        fail('lookup-managed-callback-join','same independently authenticated call and arguments',c['blocks']['callback'][:4])
    if c['blocks']['lengthEqual'][-4:]!=cc['burstSelection']['instructions']:
        fail('lookup-burst-selection-join','same independently authenticated false-getter edge',c['blocks']['lengthEqual'][-4:])
    return control.validate(image,c,pair['transfers'],comparison['comparison'],fail=fail)


def validate_current_native_contract(*,gameassembly: Path,metadata: Path) -> dict[str,Any]:
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return _skip(gate.status,gate.detail,pins)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file():return _skip('missing','UnityPlayer.dll missing beside selected native image',pins)
    if _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:return _skip('mismatched','Selected UnityPlayer.dll hash differs',pins)
    paths=set(_package_import_closure(Path(__file__)))|{CONTRACT_PATH,pair_owner.CONTRACT_PATH,comparison_owner.CONTRACT_PATH,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH}
    inputs={r['path']:r for r in (_fingerprint(p) for p in paths)}
    pc=pair_owner._contract();cc=comparison_owner._contract()
    if pc['nativeInputs']!=pins or cc['nativeInputs']!=pins:
        return _skip('mismatched','Pair or comparison declaration belongs to another build',pins)
    if cc['lookupMethod']!=c['method'] or cc['method']!=c['comparisonMethod'] or cc['burstGetterMethod']!=c['burstGetterMethod']:
        return _skip('mismatched','Lookup or actual direct callee definitions differ from comparison declaration',pins)
    pair=pair_owner.validate_current_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
    if pair['status']!='validated':return _skip(pair['status'],'Pair/list dependency not current: '+pair.get('detail',''),pins)
    comparison=comparison_owner.validate_current_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
    if comparison['status']!='validated':return _skip(comparison['status'],'Managed comparison dependency not current: '+comparison.get('detail',''),pins)
    for role,result in [('pair/list',pair),('comparison',comparison)]:
        if result['nativeInputs']!=pins:return _skip('mismatched',role+' validation belongs to another build',pins)
        for before in result['provenance']['inputs']:
            current=_fingerprint(Path(before['path']))
            if current!=before or inputs.setdefault(before['path'],before)!=before:
                _fail('lookup-dependency-source-drift',before,current)
    if (not all(pair[k] for k in ('boxedToUnboxedCellCorrespondenceProved','closedListFieldFlowProved','numericPredicateSelectedReturnsProved'))
            or not comparison['falseBurstGetterSelectionReachesManagedCallback']):
        _fail('lookup-dependency-scope','proved pair cells/list/numeric and actual false Burst managed selection',[pair,comparison])
    image=open_native_image(gate.gameassembly,gate.metadata)
    flow=_validate_image(image,c,pair,comparison,pc,cc,fail=_fail)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return _skip(after.status,after.detail,pins)
    if not unity.is_file() or _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:
        return _skip('missing' if not unity.is_file() else 'mismatched','Selected UnityPlayer.dll changed during validation',pins)
    for before in inputs.values():
        actual=_fingerprint(Path(before['path']))
        if actual!=before:_fail('source-drift',before,actual)
    return {'status':'validated','nativeInputs':pins,'selectedManagedLookup':flow,
        'completeSelectedManagedLookupCfgProved':True,'lookupFieldFlowProved':True,'callbackInputOriginsProved':True,
        'wholeLookupControlFlowProved':False,'actualLookupFoundValueProved':False,'runtimeExecutionKnown':False,
        'wholeActionAdmitted':False,'wholeRootAdmitted':False,
        'provenance':{'inputs':sorted(inputs.values(),key=lambda r:r['path'])},'evidenceBoundary':c['evidenceBoundary']}
