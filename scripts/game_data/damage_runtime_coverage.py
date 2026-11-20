"""Audit retained calibration coverage without inferring missing damage outcomes."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
import math
import struct
from pathlib import Path
import tempfile
from scripts.game_data.mission_trace_replay import fingerprint
from scripts.game_data.damage_runtime_calibration import LIMIT

WATCHED_NAMES = {'Def', 'CriticalRate', 'CriticalDamageIncrease', 'PhysicalInflictionDamageScalar',
                 'IgniteDamageScalar', 'WeaknessDmgScalar', 'ShelterDmgScalar',
                 'MaxPoise', 'PoiseRecTime', 'PoiseRecTimeScalar', 'PoiseDamageTakenScalar',
                 'PoiseDamageOutputScalar', 'BreakingAttackDamageTakenScalar', 'DamageToBrokenUnitIncrease'}
POISE_NAMES = {'MaxPoise', 'PoiseRecTime', 'PoiseRecTimeScalar', 'PoiseDamageTakenScalar',
               'PoiseDamageOutputScalar', 'BreakingAttackDamageTakenScalar', 'DamageToBrokenUnitIncrease'}


def analyze(calibration, attribute_rows):
    if calibration.get('schema') != 'endfield.damage-runtime-calibration.v1' or calibration.get('status') != 'observed-candidates':
        raise ValueError('requires maintained calibration candidates')
    by_dump = defaultdict(lambda: defaultdict(dict))
    count = 0
    for row in attribute_rows:
        count += 1
        names = set(row.get('attributeNames') or []) & WATCHED_NAMES
        if len(names) > 1:
            raise ValueError('ambiguous retained attribute names')
        if names:
            name = next(iter(names))
            key = (row['getterCallerRva'], row['attributesPointer'], row['attributesInstanceUid'])
            prior = by_dump[row['dumpId']][key].get(name)
            item = {k: row.get(k) for k in ('sequence', 'invocationId', 'attributeType', 'attributeNames', 'value', 'raw64')}
            if prior is not None:
                raise ValueError('duplicate attribute in one explicit typed dump source')
            by_dump[row['dumpId']][key][name] = item
    mods = {m['id']: m for m in calibration['outerModifiers']}
    dumps = {d['id']: d for d in calibration['dumps']}
    samples = []
    flag_counts, environments, units = Counter(), Counter(), Counter()
    for modifier in mods.values():
        before = modifier['before']
        def exact(label):
            f = before.get(label) or {}
            return f.get('value') if f.get('stateName') == 'exact' else None
        flag_counts[str(exact('sharedFlagMask'))] += 1
        environments[str(exact('environmentId'))] += 1
        units[str(exact('damageUnitIndex'))] += 1
    for sample in calibration['samples']:
        candidates = [mods[i] for i in sample['modifierCandidateIds']]
        indexed = [m for m in candidates if (m['before'].get('damageUnitIndex') or {}).get('stateName') == 'exact'
                   and m['before']['damageUnitIndex'].get('value') == 0]
        sources = []
        identity_candidates = set()
        for did in sample['dumpIds']:
            dump = dumps[did]
            if dump['parentHook'] == 'damage.Pack.GetFinalAttackValue' and dump['entry']['parentInvocationId'] != sample['pack']['entry']['invocationId']:
                continue
            for key, attrs in by_dump[did].items():
                matched = [m['id'] for m in indexed if m.get('target') is not None and key[1] not in (None, 0)
                           and key[2] is not None and m['target'][3] == key[1] and m['target'][4] == key[2]]
                if dump['parentHook'] == 'damage.Pack.GetFinalAttackValue':
                    identity_candidates.update(matched)
                sources.append({'dumpId': did, 'dumpParentHook': dump['parentHook'],
                    'packAssociation': 'explicit-parent-invocation' if dump['parentHook'] == 'damage.Pack.GetFinalAttackValue' else 'same-action-pointer-candidate',
                    'getterCallerRva': key[0], 'attributesPointer': key[1], 'attributesInstanceUid': key[2],
                    'identityMatchedUnitZeroModifierCandidateIds': matched,
                    'watchedAttributes': {str(k): v for k,v in attrs.items()},
                    'criticalRateExactlyZero': attrs.get('CriticalRate', {}).get('value') == 0,
                    'criticalDamageIncreaseExactlyZero': attrs.get('CriticalDamageIncrease', {}).get('value') == 0})
        matched_modifier = mods[next(iter(identity_candidates))] if len(identity_candidates) == 1 else None
        matched_fields = matched_modifier['before'] if matched_modifier else {}
        samples.append({'sampleId': sample['id'], 'packInvocation': sample['pack']['entry'],
            'unitZeroModifierCandidateIds': [m['id'] for m in indexed],
            'nestedDumpIdentityMatchedModifierCandidateIds': sorted(identity_candidates),
            'nestedDumpIdentityAssociation': 'unique-typed-dump-identity-candidate' if len(identity_candidates) == 1 else 'ambiguous-or-absent',
            'identityMatchedModifier': None if matched_modifier is None else {
                'id': matched_modifier['id'], 'entry': matched_modifier['entry'], 'target': matched_modifier['target'],
                'environmentId': matched_fields.get('environmentId'),
                'damageUnitIndex': matched_fields.get('damageUnitIndex'),
                'serverActionIndex': matched_fields.get('serverActionIndex'),
                'sharedFlagMask': matched_fields.get('sharedFlagMask')},
            'unitZeroAssociation': 'sole-same-action-index-zero-candidate' if len(indexed) == 1 else 'ambiguous-or-absent',
            'unitZeroEnvironmentCandidates': [(m['before'].get('environmentId') or {}).get('value') for m in indexed],
            'typedAttributeSources': sources, 'observedCritical': None, 'observedBlocked': None,
            'fullDamagePrediction': None,
            'remainingUnobserved': ['formula callback selection/effect', 'conditional Actor Single scale',
                'critical RNG/output', 'block output', 'pack-to-modifier causal binding']})
    zeros = Counter()
    for sample in samples:
        for source in sample['typedAttributeSources']:
            if source['dumpParentHook'] == 'damage.Pack.GetFinalAttackValue':
                for attr, flag in (('CriticalRate', 'criticalRateExactlyZero'), ('CriticalDamageIncrease', 'criticalDamageIncreaseExactlyZero')):
                    if source[flag]:
                        zeros[f"caller={source['getterCallerRva']};attribute={attr}"] += 1
    return {'schema':'endfield.damage-runtime-coverage.v1', 'status':'observed-candidates',
        'boundary':'No fit or missing-effect default. Numeric zero is an observed typed source value; critical branch equivalence requires authenticated native source-role and formula proof. Modifier sharedFlagMask remains a later field observation, not a captured formula critical/block result.',
        'counts': {'samples':len(samples), 'attributeRows':count,
            'uniqueNestedDumpIdentityCandidates':sum(len(s['nestedDumpIdentityMatchedModifierCandidateIds']) == 1 for s in samples),
            'soleIndexZeroCandidates':sum(s['unitZeroAssociation'] == 'sole-same-action-index-zero-candidate' for s in samples),
            'zeroNamedValuesAtPackNestedDump':dict(zeros)},
        'modifierFieldCoverage':{'sharedFlagMask':dict(flag_counts), 'damageUnitIndex':dict(units), 'environmentId':dict(environments)},
        'samples': samples}


def attach_branch_evidence(result, calibration, receipt, inspection):
    """Interpret later flags conditionally; never promote the target candidate."""
    from scripts.game_data.damage_process_formula_native import CONTRACT, SCHEMA
    if receipt.get('schema') != SCHEMA or receipt.get('status') != 'validated' or receipt.get('failures') != []:
        raise ValueError('requires validated native branch evidence')
    if str(receipt.get('contractSha256', '')).lower() != fingerprint(CONTRACT, LIMIT)['sha256'].lower():
        raise ValueError('native evidence contract digest differs from current reviewed contract')
    evidence = receipt.get('branchEvidence') or {}
    flags = evidence.get('modifierSharedFlags') or {}
    if evidence.get('evidenceBoundary') != 'conditional' or not flags.get('conditions') or not flags.get('boundary'):
        raise ValueError('native modifier flag conditions absent')
    bits = (flags.get('criticalBit'), flags.get('blockedBit'))
    if any(type(bit) is not int or not 0 <= bit < 32 for bit in bits) or bits[0] == bits[1]:
        raise ValueError('invalid native flag bit declaration')
    captured = inspection['sourceContext']['nativeInputs']
    expected = {'gameAssemblySha256': captured['gameAssembly']['sha256'], 'metadataSha256': captured['metadata']['sha256']}
    actual_pins = receipt.get('nativeInputs') or {}
    if set(actual_pins) != set(expected) or any(str(actual_pins[k]).lower() != expected[k].lower() for k in expected):
        raise ValueError('native evidence differs from captured native inputs')
    entries = {r['sequence']: r for a in inspection['actions'] for r in a['observations']
               if r['hook'] == 'buff.AbilitySystem.ApplyModifier' and r['phase'] == 'enter'}
    counts = Counter()
    dice_counts = Counter()
    dice = evidence.get('diceAtOrBelowEpsilon') or {}
    threshold = dice.get('thresholdDouble')
    if dice.get('result') is not False or not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or threshold <= 0:
        raise ValueError('native deterministic Dice declaration absent')
    for sample in result['samples']:
        modifier = sample['identityMatchedModifier']
        critical = blocked = None
        if modifier is not None:
            row = entries.get(modifier['entry']['sequence'], {})
            field = next((f for f in row.get('fields', []) if f['label'] == 'sharedFlagMask'), {})
            path = field.get('fieldPath') or []
            if field.get('stateName') != 'exact' or len(path) != 1 or path[0].get('field') != flags['metadataField'] or path[0].get('offset') != flags['rawOffset']:
                raise ValueError('captured modifier flag field layout differs from native evidence')
            compact = modifier['sharedFlagMask'] or {}
            if compact.get('stateName') != 'exact' or compact.get('value') != field.get('value') or compact.get('raw64') != field.get('raw64'):
                raise ValueError('calibration modifier flag differs from bound inspection')
            mask = field['value']
            critical, blocked = bool(mask & (1 << flags['criticalBit'])), bool(mask & (1 << flags['blockedBit']))
            counts[f'critical={critical};blocked={blocked}'] += 1
        sample['conditionalLaterModifierFlags'] = {'critical': critical, 'blocked': blocked,
            'evidenceBoundary': 'conditional', 'conditions': flags['conditions'], 'boundary': flags['boundary'],
            'ownership': 'unique typed source/target identity candidate; pack-to-modifier causal binding remains conditional'}
        predictions = []
        for source in sample['typedAttributeSources']:
            rate = source['watchedAttributes'].get('CriticalRate') or {}
            probability = rate.get('value')
            if source['packAssociation'] != 'explicit-parent-invocation' or not isinstance(probability, (int, float)) or not math.isfinite(probability) or probability > threshold:
                continue
            item = {'dumpId':source['dumpId'], 'getterCallerRva':source['getterCallerRva'],
                'criticalRate':rate, 'critical':False, 'evidenceBoundary':'conditional',
                'conditions':['This typed source must be the actual compatible A array consumed by this formula invocation; that source/frame join remains unresolved.', dice['selection']],
                'boundary':dice['boundary'], 'independentLaterFlagAgreement': None if critical is None else critical is False}
            predictions.append(item)
            dice_counts[str(source['getterCallerRva'])] += 1
        sample['conditionalNoCritSourcePredictions'] = predictions
    result['conditionalFlagEvidence'] = {'declaration': flags, 'nativeInputs': expected,
        'nativeEvidenceSchema':receipt['schema'], 'reviewedContractDigest':receipt['contractSha256'],
        'counts': dict(counts)}
    result['conditionalDiceEvidence'] = {'declaration':dice, 'sourceCandidateCountsByGetterCaller':dict(dice_counts),
        'boundary':'Separate typed-source conditional predictions. Later flag values never select a formula branch.'}
    result['defenderPoiseFactorConditionalRule'] = evidence.get('callbackSelection')


def attach_poise_inventory(result, inspection):
    """Separate retained poise quantities from an unobserved selector result."""
    rows = {r['sequence']:r for a in inspection['actions'] for r in a['observations']}
    rows.update({r['sequence']:r for r in inspection.get('unownedObservations',[])})
    hooks = inspection['sourceContext']['hooks']
    declaration = result.get('defenderPoiseFactorConditionalRule') or {}
    getter = declaration.get('logicalGetter')
    factor_hooks = {h['name'] for h in hooks if getter is not None and h.get('symbol')==getter}
    factor_returns = [r for r in rows.values() if r['hook'] in factor_hooks and r['phase']=='return']
    candidate_hooks = {h['name'] for h in hooks if h.get('captureIndirectCaller')=='damage.defenderPoiseFactor'
                       and h.get('returnType')=='double'}
    hook_counts = Counter(r['hook'] for r in rows.values())
    entries = {(r['threadId'],r['invocationId']):r for r in rows.values() if r['phase']=='enter'}
    poise = []
    selectors, callback_returns = [], []
    def observation_ref(row):
        return {k:row.get(k) for k in ('hook','sequence','threadId','invocationId','parentInvocationId',
                                       'phase','callerGameAssemblyRva','returnAddress')}
    def exact_fields(row):
        return {f['label']:f for f in row.get('fields',[]) if f.get('stateName')=='exact'}
    def compact(field):
        return None if field is None else {k:field[k] for k in ('value','raw64','stateName','enumNames') if k in field}
    for row in sorted(rows.values(),key=lambda r:r['sequence']):
        if row['hook']=='damage.Action.ProcessDamage' and row['phase'] in ('enter','return'):
            for snapshot in row.get('fields',[]):
                if snapshot.get('readMode')!='moduleCallbackSelector':
                    continue
                selectors.append({'observation':observation_ref(row),
                    'returnedNormally':None if row['phase']=='enter' else row.get('invocationReceipt',{}).get('returnedNormally') is True,
                    'snapshot':{k:snapshot[k] for k in ('label','type','state','stateName','predicateReason',
                        'before','after','rawHex','byteCount','snapshotStable','readMode') if k in snapshot},
                    'actualSelectorPath':None,'actualFactor':None,
                    'boundary':'Process entry/normal-return boundary snapshot only. Two equal tuples do not establish intermediate selector stability, absence of ABA, arithmetic branch selection or a per-Pack factor.'})
        if row['hook'] in candidate_hooks and row['phase']=='return' and row.get('invocationReceipt',{}).get('returnedNormally') is True:
            raw=row.get('returnValue')
            number=struct.unpack('<d',raw.to_bytes(8,'little'))[0] if type(raw) is int and 0<=raw<2**64 else None
            finite=math.isfinite(number) if number is not None else None
            entered=entries.get((row['threadId'],row['invocationId']))
            callback_returns.append({'entry':None if entered is None else observation_ref(entered),
                'return':observation_ref(row),'returnedNormally':True,
                'raw64':raw,'floatBits':f'0x{raw:016x}' if type(raw) is int and 0<=raw<2**64 else None,
                'value':number if finite else None,'finite':finite,'actualPerPackFactor':None,
                'boundary':'Observed original normal Double return at this scoped physical callback entry/caller site. It is not automatically assigned to any Pack or multiplied across samples.'})
        fs=exact_fields(row)
        if row['hook']!='buff.AbilitySystem.ApplyModifier' or row['phase']!='return' or 'Poise' not in fs.get('targetType',{}).get('enumNames',[]):
            continue
        entered=entries.get((row['threadId'],row['invocationId']))
        before=exact_fields(entered or {})
        poise.append({'threadId':row['threadId'],'invocationId':row['invocationId'],
            'entrySequence':None if entered is None else entered['sequence'],'returnSequence':row['sequence'],
            'before':{k:compact(before.get(k)) for k in ('attributesIdentity','attributesInstanceUid','modifierValue','deltaType','targetType')},
            'after':{k:compact(fs.get(k)) for k in ('realDelta','deltaType','cancelReason','targetType')},
            'returnedNormally':row.get('invocationReceipt',{}).get('returnedNormally') is True,
            'currentPoiseBefore':None,'currentPoiseAfter':None})
    summaries = {}
    for sample in result['samples']:
        for source in sample['typedAttributeSources']:
            if source['packAssociation']!='explicit-parent-invocation':
                continue
            for name, item in source['watchedAttributes'].items():
                if name not in POISE_NAMES:
                    continue
                key=json.dumps([source.get('nativeArrayRole'),source['getterCallerRva'],name])
                summary=summaries.setdefault(key,{'role':source.get('nativeArrayRole'),'getterCallerRva':source['getterCallerRva'],
                    'attributeName':name,'returns':0,'values':Counter()})
                summary['returns']+=1
                summary['values'][str(item.get('value'))]+=1
    for summary in summaries.values():
        summary['values']=dict(summary['values'])
    result['defenderPoiseFactorRetainedCoverage'] = {
        'actualFactor':None,'actualSelectorPath':None,'factorGetterConfigured':any(h.get('symbol')==getter for h in hooks) if getter else None,
        'configuredHooks':[{'hook':h['name'],'symbol':h.get('symbol'),'fields':[f['label'] for f in h.get('fields',[])],
            'inlineRows':hook_counts[h['name']]} for h in hooks],
        'projectionCounts':inspection.get('projectionCounts'),
        'getterDoubleReturnRetained':bool(factor_returns),
        'getterReturnReferences':[{'sequence':r['sequence'],'invocationId':r['invocationId'],
            'value':r.get('decodedReturnValue'),'raw64':r.get('returnValue')} for r in factor_returns],
        'replacementTableFunctionReceiverSnapshotRetained':bool(selectors),
        'processSelectorSnapshots':selectors,
        'processSelectorSnapshotCounts':{'rows':len(selectors),
            'entries':sum(s['observation']['phase']=='enter' for s in selectors),
            'returns':sum(s['observation']['phase']=='return' for s in selectors),
            'invocations':len({(s['observation']['threadId'],s['observation']['invocationId']) for s in selectors}),
            'states':dict(Counter(s['snapshot'].get('stateName') for s in selectors))},
        'candidateNormalDoubleReturns':callback_returns,
        'candidateNormalDoubleReturnCounts':{'entries':sum(r['hook'] in candidate_hooks and r['phase']=='enter' for r in rows.values()),
            'normalReturns':len(callback_returns),
            'finite':sum(r['finite'] is True for r in callback_returns),
            'nonFinite':sum(r['finite'] is False for r in callback_returns),
            'unknownFinite':sum(r['finite'] is None for r in callback_returns),
            'byHook':dict(Counter(r['return']['hook'] for r in callback_returns)),
            'byCallerGameAssemblyRva':dict(Counter(str(r['return']['callerGameAssemblyRva']) for r in callback_returns))},
        'fullPackBytesRetained':False,'currentPoiseBeforeAfterRetained':False,
        'poiseModifierReturns':poise,'poiseAttributeSummaries':list(summaries.values()),
        'sourceContextInventory':[{'path':p['path'],'bytes':p['bytes'],'sha256':p['sha256']}
            for p in inspection['sourceContext']['inventory']['snapshotInputs']],
        'decodedSourceReread':False,
        'boundary':'Only GetValue rows are compacted; other configured observations are deduplicated by original sequence. Retained Process selector boundaries and scoped normal callback Double returns remain separate observations; no actual arithmetic path or per-Pack factor is assigned. Named poise attributes and Poise-target modifier deltas are not a factor or current-poise state. HP fields remain HP even on Poise modifiers. Raw GP pointers are not full Pack bytes. Getter/candidate absence cannot select the native default branch; no factor is inferred from HP or modifier residuals.'}


def attach_source_roles(result, calibration, evidence, inspection):
    from scripts.game_data.damage_runtime_source_roles_native import SCHEMA as ROLE_SCHEMA, CONTRACT_PATH, CLAIM_SCHEMA
    if evidence.get('schema') != ROLE_SCHEMA or evidence.get('status') != 'validated' or evidence.get('failures') != []:
        raise ValueError('requires validated native source role evidence')
    if evidence.get('claimContractSchema') != CLAIM_SCHEMA or str(evidence.get('claimContractSha256','')).lower() != fingerprint(CONTRACT_PATH,LIMIT)['sha256'].lower():
        raise ValueError('source role contract digest differs')
    capture = inspection['sourceContext']['nativeInputs']
    expected = {'gameAssemblySha256':capture['gameAssembly']['sha256'],'metadataSha256':capture['metadata']['sha256']}
    pins = evidence.get('nativeInputs') or {}
    if set(pins) != set(expected) or any(str(pins[k]).lower() != expected[k].lower() for k in expected):
        raise ValueError('source role native pair differs from capture')
    proof_sources = evidence.get('proofSources') or []
    if not proof_sources:
        raise ValueError('source role proof source fingerprints absent')
    for pin in proof_sources:
        if fingerprint(Path(pin['path']),LIMIT) != pin:
            raise ValueError('source role proof source changed')
    roles = evidence.get('roles') or []
    if {r.get('role') for r in roles} != {'attacker','defender'} or len(roles) != 2 or len({r.get('getterCallerRva') for r in roles}) != 2:
        raise ValueError('source role declarations incomplete or ambiguous')
    if any(r.get('evidenceBoundary') != 'conditional' or not r.get('conditions') for r in roles):
        raise ValueError('source role conditions absent')
    by_caller = {r['getterCallerRva']:r for r in roles}
    counts, dice_counts = Counter(), Counter()
    for sample in result['samples']:
        selected = {}
        for source in sample['typedAttributeSources']:
            role = by_caller.get(source['getterCallerRva'])
            source['nativeArrayRole'] = None if role is None else role['role']
            source['nativeArrayRoleEvidence'] = role
            if source['packAssociation'] == 'explicit-parent-invocation':
                selected[(source['dumpId'],source['getterCallerRva'])] = source['nativeArrayRole']
                counts[str(source['nativeArrayRole'])] += 1
        if 'conditionalNoCritSourcePredictions' in sample:
            predictions = [p for p in sample['conditionalNoCritSourcePredictions']
                if selected.get((p['dumpId'],p['getterCallerRva'])) == 'attacker']
            for prediction in predictions:
                prediction['nativeArrayRole'] = 'attacker'
                prediction['conditions'].extend(by_caller[prediction['getterCallerRva']]['conditions'])
                dice_counts[str(prediction['getterCallerRva'])] += 1
            sample['conditionalNoCritSourcePredictions'] = predictions
    result['nativeSourceRoleEvidence'] = {'declarations':roles,'explicitNestedSourceCounts':dict(counts),
        'boundary':'Native caller-to-named array destination role. Generic Lock typed return, actual actor ownership and formula array/frame continuity remain conditional.'}
    if 'conditionalDiceEvidence' in result:
        result['conditionalDiceEvidence']['sourceCandidateCountsByGetterCaller'] = dict(dice_counts)
        result['conditionalDiceEvidence']['sourceRoleSelection'] = 'only authenticated attacker-array destination callers in explicit own Pack final invocation dump'


def run(source, output, native_evidence=None, source_role_evidence=None):
    from scripts.repo_paths import REPO_ROOT
    source, output = Path(source).resolve(), Path(output).resolve()
    root = (REPO_ROOT/'reports').resolve()
    if not source.is_relative_to(root) or not output.is_relative_to(root) or source == output:
        raise ValueError('distinct reports input/output required')
    before = fingerprint(source, LIMIT)
    data = json.loads(source.read_text(encoding='utf-8'))
    side = data['attributeValues']
    sidepath = Path(side['path']).resolve()
    if not sidepath.is_relative_to(root) or sidepath == output:
        raise ValueError('distinct reports attribute input required')
    side_before = fingerprint(sidepath, LIMIT)
    if any(side_before[k] != side[k] for k in ('bytes','sha256')):
        raise ValueError('calibration attribute fingerprint differs')
    with sidepath.open(encoding='utf-8') as handle:
        result = analyze(data, (json.loads(line) for line in handle))
    extra_sources = {}
    if native_evidence is not None or source_role_evidence is not None:
        inspection_pin = data['sources']['before']['inspection']
        inspection_path = Path(inspection_pin['path']).resolve()
        if inspection_path == output or not inspection_path.is_relative_to(root) or fingerprint(inspection_path, LIMIT) != inspection_pin:
            raise ValueError('bound inspection fingerprint differs')
        inspection = json.loads(inspection_path.read_text(encoding='utf-8'))
        extra_sources = {'boundInspection':inspection_pin}
        for name, path, attach in (('nativeEvidence',native_evidence,attach_branch_evidence),('sourceRoleEvidence',source_role_evidence,attach_source_roles)):
            if path is None:
                continue
            path = Path(path).resolve()
            if not path.is_relative_to(root) or path == output:
                raise ValueError('native evidence must be a distinct reports input')
            evidence_pin = fingerprint(path,LIMIT)
            attach(result,data,json.loads(path.read_text(encoding='utf-8')),inspection)
            if fingerprint(path,LIMIT) != evidence_pin:
                raise ValueError('native evidence changed')
            extra_sources[name] = evidence_pin
        if fingerprint(inspection_path,LIMIT) != inspection_pin:
            raise ValueError('bound inspection changed')
    if native_evidence is not None and source_role_evidence is None:
        for sample in result['samples']:
            sample['conditionalNoCritSourcePredictions'] = []
        result['conditionalDiceEvidence']['sourceCandidateCountsByGetterCaller'] = {}
        result['conditionalDiceEvidence']['sourceRoleSelection'] = 'withheld: authenticated attacker-array caller evidence was not supplied'
    if native_evidence is not None or source_role_evidence is not None:
        attach_poise_inventory(result,inspection)
    if result['counts']['attributeRows'] != data['counts']['attributeRows']:
        raise ValueError('calibration attribute row count differs')
    after, side_after = fingerprint(source, LIMIT), fingerprint(sidepath, LIMIT)
    if before != after or side_before != side_after:
        raise ValueError('inputs changed during coverage')
    result['sources'] = {'before':{'calibration':before,'attributes':side_before}, 'after':{'calibration':after,'attributes':side_after}}
    result['sources']['conditionalFlagInputsVerifiedBeforeAndAfter'] = extra_sources
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=output.name+'.', suffix='.tmp', delete=False, mode='w', encoding='utf-8') as handle:
            temporary = Path(handle.name)
            json.dump(result,handle,indent=2,allow_nan=False)
            handle.write('\n')
        temporary.replace(output)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calibration',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--native-evidence',type=Path)
    parser.add_argument('--source-role-evidence',type=Path)
    args=parser.parse_args()
    print(json.dumps(run(args.calibration,args.output,args.native_evidence,args.source_role_evidence)['counts']))


if __name__ == '__main__':
    main()
