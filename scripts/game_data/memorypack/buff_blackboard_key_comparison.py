"""Current Blackboard lookup's owned managed callback and pure key comparison.

The complete comparison CFG is proved separately from callback dispatch, input
origins and the enclosing lookup. Explicit native/source gates fail closed.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp import utf16_ascii_comparison as program
from scripts.game_data.memorypack import buff_blackboard_double_consumers as caller
from scripts.game_data.memorypack.closed_scalar_consumers import signature
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _package_import_closure

LABEL='buffBlackboardKeyComparison'
CONTRACT_PATH=CONTRACTS_DIR/'memorypack_blackboard_key_comparison_native.json'

def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.memorypack-blackboard-key-comparison-native-contract.v1',
        status='exact-current-build',label=LABEL)
    if c.get('mode') != program.MODE:raise ValueError(f'{LABEL}.contract:mode')
    return c

def _fail(check,expected,actual):
    c=_contract();error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,record=c['method'][1]+'.'+c['method'][2],nativeInputs=c['nativeInputs'])
    error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error

def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'wholeActionAdmitted':False,'wholeRootAdmitted':False}

def validate_current_native_contract(*,gameassembly: Path,metadata: Path) -> dict[str,Any]:
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return _skip(gate.status,gate.detail,pins)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file():return _skip('missing','UnityPlayer.dll missing beside selected native image',pins)
    if _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:return _skip('mismatched','Selected UnityPlayer.dll hash differs',pins)
    paths=set(_package_import_closure(Path(__file__)))|{CONTRACT_PATH,caller.CONTRACT_PATH,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH}
    inputs={r['path']:r for r in (_fingerprint(p) for p in paths)}
    declaration=caller._contract()
    if declaration['nativeInputs']!=pins or declaration['numberLookupMethod']!=c['lookupMethod']:
        return _skip('mismatched','Concrete caller lookup definition differs from selected comparison declaration',pins)
    image=open_native_image(gate.gameassembly,gate.metadata)
    if c['method'][1:3]!=['Beyond.StringUtils','_EqualsIgnoreCase$BurstManaged']:
        _fail('comparison-method-name','actual named managed key-comparison definition',c['method'])
    signature(image,c['method'],(2,'bool'),[(15,'short*',False),(15,'short*',False),(8,'int',False)],static=True,fail=_fail)
    signature(image,c['lookupMethod'],(2,'bool'),[(14,'string',False),(13,'double',True)],static=False,fail=_fail)
    if c['leaf']['codeWindow']['startRva']!=c['method'][3]:_fail('leaf-entry',c['method'][3],c['leaf']['codeWindow'])
    comparison=program.validate(image,c['leaf'],fail=_fail)
    index=BodyIndex(image);entry=image.pe.image_base+c['lookupMethod'][3]
    owned=[(entry,index.extents[entry]-entry)]+list(index.chained_fragments.get(entry,()))
    fragment=c['lookupCallbackFragment'];window=fragment['codeWindow'];rows=fragment['instructions']
    if not any(begin-image.pe.image_base==window['startRva'] and begin+size-image.pe.image_base==window['endRva'] for begin,size in owned):
        _fail('callback-unwind-owner','exact lookup-owned entry or unwind range',window)
    image.check_windows([window],label=LABEL);image.check_instruction_windows(rows,label=LABEL)
    selection=c['burstSelection'];swindow=selection['codeWindow'];srows=selection['instructions']
    signature(image,c['burstGetterMethod'],(2,'bool'),[],static=True,fail=_fail)
    if c['burstGetterMethod'][1:3]!=['Unity.Burst.BurstCompiler','get_IsEnabled']:
        _fail('burst-getter-name','actual BurstCompiler.get_IsEnabled definition',c['burstGetterMethod'])
    if not any(begin-image.pe.image_base==swindow['startRva'] and begin+size-image.pe.image_base==swindow['endRva'] for begin,size in owned):
        _fail('burst-selection-unwind-owner','exact lookup-owned range',swindow)
    image.check_windows([swindow],label=LABEL);image.check_instruction_windows(srows,label=LABEL)
    if len(srows)!=4 or srows[0][1]!='33C9' or srows[2][1]!='84C0':
        _fail('burst-selection-program','zero companion, actual Boolean getter, TEST AL and JE',srows)
    for i,row in enumerate(srows):
        if not swindow['startRva']<=row[0]<row[0]+len(bytes.fromhex(row[1]))<=swindow['endRva']:
            _fail('burst-selection-contained','within owned range',row)
        if i and srows[i-1][0]+len(bytes.fromhex(srows[i-1][1]))!=row[0]:
            _fail('burst-selection-contiguity','complete selected argument/check/branch fragment',srows)
    call=bytes.fromhex(srows[1][1]);branch=bytes.fromhex(srows[3][1])
    if len(call)!=5 or call[0]!=0xe8 or srows[1][0]+5+int.from_bytes(call[1:],'little',signed=True)!=c['burstGetterMethod'][3]:
        _fail('burst-getter-callee',c['burstGetterMethod'],srows[1])
    if len(branch)!=6 or branch[:2]!=b'\x0f\x84' or srows[3][0]+6+int.from_bytes(branch[2:],'little',signed=True)!=rows[0][0]:
        _fail('managed-fallback-entry','actual false Boolean JE reaches first callback instruction',srows[3])
    expected=['448BC5','488D5614','498BCE',None]
    if len(rows)!=4:_fail('callback-program-size',4,rows)
    for i,(row,wanted) in enumerate(zip(rows,expected,strict=True)):
        if wanted is not None and row[1]!=wanted:_fail('callback-arguments',[i,wanted],row)
        if not window['startRva']<=row[0]<row[0]+len(bytes.fromhex(row[1]))<=window['endRva']:
            _fail('callback-contained','within exact unwind-owned range',row)
        if i and rows[i-1][0]+len(bytes.fromhex(rows[i-1][1]))!=row[0]:_fail('callback-contiguity','complete fragment',rows)
    raw=bytes.fromhex(rows[-1][1])
    if len(raw)!=5 or raw[0]!=0xe8 or rows[-1][0]+5+int.from_bytes(raw[1:],'little',signed=True)!=c['method'][3]:
        _fail('callback-callee-identity',c['method'],rows[-1])
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return _skip(after.status,after.detail,pins)
    if not unity.is_file() or _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:
        return _skip('missing' if not unity.is_file() else 'mismatched','Selected UnityPlayer.dll changed during validation',pins)
    for before in inputs.values():
        actual=_fingerprint(Path(before['path']))
        if actual!=before:_fail('source-drift',before,actual)
    return {'status':'validated','nativeInputs':pins,'comparison':comparison,
        'lookupUnwindOwnedDirectCallFragmentProved':True,
        'falseBurstGetterSelectionReachesManagedCallback':True,'burstGetterRuntimeResultKnown':False,
        'callbackArgumentAliases':{'rcx':'r14','rdx':'rsi+20','r8d':'ebp'},
        'callbackInputOriginsProved':False,'wholeLookupControlFlowProved':False,'callbackRuntimeDispatchObserved':False,
        'runtimeExecutionKnown':False,'actualLookupFoundValueProved':False,
        'wholeActionAdmitted':False,'wholeRootAdmitted':False,
        'provenance':{'inputs':sorted(inputs.values(),key=lambda r:r['path'])},'evidenceBoundary':c['evidenceBoundary']}
