"""Audit retained calibration coverage without inferring missing damage outcomes."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import tempfile
from scripts.game_data.mission_trace_replay import fingerprint
from scripts.game_data.damage_runtime_calibration import LIMIT

WATCHED_NAMES = {'Def', 'CriticalRate', 'CriticalDamageIncrease', 'PhysicalInflictionDamageScalar',
                 'IgniteDamageScalar', 'WeaknessDmgScalar', 'ShelterDmgScalar'}


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


def run(source, output, native_evidence=None):
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
    if native_evidence is not None:
        native_evidence = Path(native_evidence).resolve()
        if not native_evidence.is_relative_to(root) or native_evidence == output:
            raise ValueError('native evidence must be a distinct reports input')
        evidence_pin = fingerprint(native_evidence, LIMIT)
        inspection_pin = data['sources']['before']['inspection']
        inspection_path = Path(inspection_pin['path']).resolve()
        if inspection_path == output or not inspection_path.is_relative_to(root) or fingerprint(inspection_path, LIMIT) != inspection_pin:
            raise ValueError('bound inspection fingerprint differs')
        receipt = json.loads(native_evidence.read_text(encoding='utf-8'))
        inspection = json.loads(inspection_path.read_text(encoding='utf-8'))
        attach_branch_evidence(result, data, receipt, inspection)
        if fingerprint(native_evidence, LIMIT) != evidence_pin or fingerprint(inspection_path, LIMIT) != inspection_pin:
            raise ValueError('native evidence or bound inspection changed')
        extra_sources = {'nativeEvidence':evidence_pin, 'boundInspection':inspection_pin}
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
    args=parser.parse_args()
    print(json.dumps(run(args.calibration,args.output,args.native_evidence)['counts']))


if __name__ == '__main__':
    main()
