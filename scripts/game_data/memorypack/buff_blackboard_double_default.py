"""Selected current TryGetDouble/default chain with explicit native gates."""
from __future__ import annotations
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.memorypack import buff_blackboard_double_lookup as lookup_owner
from scripts.game_data.memorypack import blackboard_double_default as control
from scripts.game_data.memorypack.closed_scalar_consumers import signature
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _package_import_closure

LABEL='buffBlackboardDoubleDefault'
CONTRACT_PATH=CONTRACTS_DIR/'memorypack_blackboard_double_default_native.json'


def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.memorypack-blackboard-double-default-native-contract.v1',status='exact-current-build',label=LABEL)
    if c.get('mode')!=control.MODE: raise ValueError(LABEL+'.contract:mode')
    return c


def _fail(check,expected,actual):
    error=CensusGateError(LABEL+'.'+check,source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,record='Beyond.Blackboard.GetDoubleOrDefault')
    error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error


def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'wholeActionAdmitted':False,'wholeRootAdmitted':False}


def _validate_image(image,c,dependency,*,fail):
    methods=c['methods']; scalar='Beyond.Blackboard+BlackboardDouble'; board='Beyond.Blackboard'
    for role,owner,name,result,params in [
        ('tryDouble',board,'TryGetDouble',(2,'bool'),[(18,scalar,False),(13,'double',True)]),
        ('getDoubleOrDefault',board,'GetDoubleOrDefault',(13,'double'),[(18,scalar,False),(13,'double',False),(2,'bool',False)]),
        ('getValueOrDefaultInternal',scalar,'GetValueOrDefaultInternal',(13,'double'),[(18,board,False),(13,'double',False)])]:
        if methods[role][1:3]!=[owner,name]:fail('default-method-name',[owner,name],methods[role])
        signature(image,methods[role],result,params,static=False,fail=fail)
    signature(image,methods['patchCheck'],(2,'bool'),[(8,'int',False)],static=True,fail=fail)
    signature(image,methods['numberLookup'],(2,'bool'),[(14,'string',False),(13,'double',True)],static=False,fail=fail)
    index=BodyIndex(image);base=image.pe.image_base
    for role in ('tryDouble','getDoubleOrDefault','getValueOrDefaultInternal'):
        entry=base+methods[role][3]
        if entry not in index.extents:fail('default-owned-entry',methods[role],'missing unwind extent')
        owned={(entry-base,index.extents[entry]-base)}|{(at-base,at+size-base) for at,size in index.chained_fragments.get(entry,())}
        declared=c['ownedCodeWindows'][role]
        if {(w['startRva'],w['endRva']) for w in declared}!=owned or len(declared)!=len(owned):
            fail('default-all-unwind-ranges',sorted(owned),declared)
        image.check_windows(declared,label=LABEL)
        for program in c['programs'].values():
            if program['methodRole']==role and program['codeWindows']!=declared:
                fail('default-program-ownership',declared,program['codeWindows'])
    consumer=dependency['dependencyProofs']['consumer']['consumerTransfer']
    return control.validate(image,c,consumer,dependency['selectedKeyedLookupRelation'],fail=fail)


def validate_current_native_contract(*,gameassembly:Path,metadata:Path)->dict:
    paths=set(_package_import_closure(Path(__file__)))|{CONTRACT_PATH,lookup_owner.consumer_owner.CONTRACT_PATH,
        lookup_owner.lookup_owner.CONTRACT_PATH,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH}
    inputs={r['path']:r for r in (_fingerprint(p) for p in paths)}
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return _skip(gate.status,gate.detail,pins)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file():return _skip('missing','UnityPlayer.dll missing beside selected native image',pins)
    if _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:return _skip('mismatched','Selected UnityPlayer.dll differs',pins)
    declaration=lookup_owner.consumer_owner._contract()
    if (declaration['nativeInputs']!=pins or c['methods']['patchCheck']!=declaration['patchCheckMethod']
            or c['methods']['numberLookup']!=declaration['numberLookupMethod']):
        return _skip('mismatched','Dependency build or actual callees differ',pins)
    dependency=lookup_owner.validate_current_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
    if dependency['status']!='validated':return _skip(dependency['status'],'Keyed relation not current: '+dependency.get('detail',''),pins)
    if dependency['nativeInputs']!=pins:return _skip('mismatched','Dependency belongs to another native build',pins)
    for before in dependency['provenance']['inputs']:
        current=_fingerprint(Path(before['path']))
        if current!=before or inputs.setdefault(before['path'],before)!=before:_fail('dependency-source-drift',before,current)
    image=open_native_image(gate.gameassembly,gate.metadata);flow=_validate_image(image,c,dependency,fail=_fail)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return _skip(after.status,after.detail,pins)
    if not unity.is_file() or _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:
        return _skip('missing' if not unity.is_file() else 'mismatched','Selected UnityPlayer.dll changed',pins)
    for before in inputs.values():
        actual=_fingerprint(Path(before['path']))
        if actual!=before:_fail('source-drift',before,actual)
    return {'status':'validated','nativeInputs':pins,'selectedDefaultChain':flow,
        'selectedDefaultChainComposed':True,'provenance':{'inputs':sorted(inputs.values(),key=lambda r:r['path'])},
        'evidenceBoundary':'conditional','actualDefaultOrLookupValueKnown':False,'publicGetValueEndToEndProved':False,
        'runtimeExecutionKnown':False,'providerSelectionProved':False,'allDispatchAndFailureEffectsProved':False,
        'wholeActionAdmitted':False,'wholeRootAdmitted':False}
