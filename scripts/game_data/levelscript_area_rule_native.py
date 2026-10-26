"""Authenticate the reviewed conditional original active-area equivalence."""
from __future__ import annotations
import hashlib,itertools,json,re
from pathlib import Path
from scripts.common import check_installed_native_inputs,sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import native_validation_failure,NativeIdentityMismatch
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory

SCHEMA='endfield.levelscript-area-rule-native.v1'
SCOPE='original-initialized-finite-area'
KIND='conditional-original-rule-equivalence'
CONTRACT=CONTRACTS_DIR/'levelscript_area_rule_native.json'
LABEL='levelscriptAreaRule'
PREMISES=('initializedMetadataAndClasses','noActiveNamedOverride','finiteEulerComponents','originalQuaternionIcallCaches','stableDisjointStorage','ordinaryNontrappingArithmetic')
FLAGS=dict.fromkeys(('completeOwnedBytePartition','typedCallerArgumentsProved','namedOriginalOuterBranchesProved','optimizedOuterBranchesProved','pairedGeometryControlProved','pairedGeometryValuesProved','nativeForeignBufferEffectsProved','protectedOuterSlotsProved','ordinaryAbiRestorationProved'),True)
FLAGS.update(dict.fromkeys(('exceptionalOrResumptionPathsProved','nonfiniteEulerPathsProved','replacementPathsProved','runtimeExecutionObserved'),False))


def projection_valid(identity,actual_callee):
    if not isinstance(identity,dict) or identity.get('status')!='validated':return False
    if any(not re.fullmatch(r'0x[0-9a-f]+',str(identity.get(k) or '')) for k in ('actualCalleeVa','namedRuleVa')) or identity['actualCalleeVa']!=actual_callee:return False
    if identity.get('kind')=='direct-current-named-target':return identity['actualCalleeVa']==identity['namedRuleVa']
    return (identity.get('kind')==KIND and identity.get('scope')==SCOPE and identity.get('evidenceBoundary')=='conditional'
        and identity.get('conditionalPremises')==list(PREMISES) and isinstance(identity.get('proofFlags'),dict)
        and set(identity['proofFlags'])==set(FLAGS) and all(identity['proofFlags'][k] is v for k,v in FLAGS.items()))


def _shape(fact):
    if fact.get('schema')!=SCHEMA or fact.get('status')!='exact-current-build' or fact.get('scope')!=SCOPE:raise ValueError(LABEL+'.contract:schema-status-scope')
    identity=dict(status='validated',kind=KIND,scope=fact['scope'],evidenceBoundary='conditional',actualCalleeVa='0x1',namedRuleVa='0x2',proofFlags=fact.get('proofFlags'),conditionalPremises=fact.get('conditionalPremises'))
    if not projection_valid(identity,'0x1'):raise ValueError(LABEL+'.contract:proof-scope')
    if set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}:raise ValueError(LABEL+'.contract:native-inputs')
    keys=('sensitive','previous','enterNull','exitNull','exitEmpty','enterPredicate','exitPredicate');expected={bits for bits in itertools.product((False,True),repeat=len(keys)) if not bits[3] or bits[4]};actual=[]
    for row in fact['proof']['outerTruthTable']:
        values=row['inputs']
        if set(values)!=set(keys) or any(type(v) is not bool for v in values.values()) or type(row['result']) is not bool:raise ValueError(LABEL+'.contract:outer-case-shape')
        s,p,en,xn,xe,ep,xp=(values[k] for k in keys);result=not s or not en and ep or p and not xe and xp
        if row['result']!=bool(result):raise ValueError(LABEL+'.contract:outer-case-result')
        actual.append(tuple(values[k] for k in keys))
    if len(actual)!=len(expected) or set(actual)!=expected:raise ValueError(LABEL+'.contract:complete-outer-case-matrix')
    control=fact['proof']['geometryControl']
    if control['failures'] or control['uncovered']!=[[],[]] or not control['matchedInstructions']:raise ValueError(LABEL+'.contract:complete-geometry-control')
    if not fact['proof']['foreignBufferEffects'] or any(row.get('allOutputViewsDisjoint') is not True for row in fact['proof']['protectedSlots']):raise ValueError(LABEL+'.contract:foreign-or-protected-slot-proof')


def _windows(pe,unwind,bodies,windows):
    declared={(r['startRva'],r['endRva']) for r in windows};covered=set()
    if not bodies or not windows or len(declared)!=len(windows):raise ValueError(LABEL+'.native:empty-or-duplicate-windows')
    for body in bodies:
        ranges=[tuple(r) for r in body['ranges']];entry=body['entryRva']
        if body['kind']=='unwind':
            actual=[tuple(r['runtimeTriple'][:2]) for r in unwind.family(entry)['ranges']]
            if set(actual)!=set(ranges):raise ValueError(LABEL+'.native:complete-owned-ranges:'+hex(entry))
        elif body['kind']=='closed-leaf':
            if entry in unwind.entries or len(ranges)!=1 or ranges[0][0]!=entry or pe.bytes_at_va(pe.image_base+ranges[0][1]-1,1)!=b'\xc3':raise ValueError(LABEL+'.native:closed-leaf:'+hex(entry))
        else:raise ValueError(LABEL+'.native:unknown-body-kind')
        covered.update(ranges)
    if covered!=declared:raise ValueError(LABEL+'.native:unowned-or-missing-window')
    for r in windows:
        a,b=r['startRva'],r['endRva']
        if type(a) is not int or type(b) is not int or not 0<=a<b:raise ValueError(LABEL+'.native:window-range:'+str((a,b)))
        actual=hashlib.sha256(pe.bytes_at_va(pe.image_base+a,b-a)).hexdigest().upper()
        if actual!=r['sha256'].upper():raise NativeIdentityMismatch(LABEL+'.native:window-bytes',expected=r['sha256'].upper(),recorded=(a,b),actual=actual)


def validate_on_image(image,*,actual_callee,named_rule,empty_exit_proof,contract_path=CONTRACT):
    try:
        path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);_shape(fact);pins=fact['nativeInputs'];base=image.pe.image_base
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=image.gameassembly,metadata=image.metadata_path)
        if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
        unity_path=image.gameassembly.parent/'UnityPlayer.dll'
        if not unity_path.is_file():return dict(status='missing',detail='Selected UnityPlayer.dll missing')
        if sha256_file_upper(unity_path)!=pins['UnityPlayer.dll']:return dict(status='mismatched',detail='Selected UnityPlayer.dll hash differs')
        if actual_callee!=base+fact['actualCalleeRva'] or named_rule!=base+fact['namedMethod'][3]:raise NativeIdentityMismatch(LABEL+'.native:caller-or-named-target',expected=(base+fact['actualCalleeRva'],base+fact['namedMethod'][3]),recorded='actual/named',actual=(actual_callee,named_rule))
        image.validate_method_row(fact['namedMethod'],label=LABEL)
        empty_flags=('incomingCollectionAndMethodInfoBitsProved','invokerSlotZeroAndArgumentBitsProved','low32ZeroTestEquivalent','selectedExitArgumentBitsProved','trueResultReturnsFalse')
        if not isinstance(empty_exit_proof,dict) or empty_exit_proof.get('status')!='validated' or any(empty_exit_proof.get(k) is not True for k in empty_flags):raise ValueError(LABEL+'.native:typed-empty-exit-proof')
        call=int(empty_exit_proof['callSiteVa'],16);instruction=image.pe.bytes_at_va(call,5)
        if instruction[0]!=0xe8 or call+5+int.from_bytes(instruction[1:],'little',signed=True)!=base+fact['emptyHelperRva']:raise ValueError(LABEL+'.native:typed-empty-target')
        _windows(image.pe,image.unwind_index,fact['gameAssemblyBodies'],fact['gameAssemblyCodeWindows'])
        unity=image.mapper.PeImage(unity_path);table,size,data=read_exception_directory(unity);unwind=UnwindChainIndex(data,lambda r,n:unity.bytes_at_va(unity.image_base+r,n),table_rva=table,image_size=size)
        _windows(unity,unwind,fact['unityBodies'],fact['unityCodeWindows'])
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=image.gameassembly,metadata=image.metadata_path)
        if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
        if sha256_file_upper(unity_path)!=pins['UnityPlayer.dll']:return dict(status='mismatched',detail='UnityPlayer.dll changed during validation')
        if raw!=path.read_bytes():raise ValueError(LABEL+'.contract:declaration-changed-during-validation')
        return dict(status='validated',kind=KIND,scope=SCOPE,namedRuleVa=hex(named_rule),actualCalleeVa=hex(actual_callee),evidenceBoundary='conditional',proofFlags=fact['proofFlags'],conditionalPremises=fact['conditionalPremises'],boundary=fact['evidenceBoundary'])
    except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError) as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)
