"""Recover sampled shader selection and missing pair-policy operands offline.

Never manufacture a pair from separately timed query-hit shapes. The original
compiled rules and their required inputs are reported separately from execution.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from scripts.common import sha256_file
from scripts.game_data.collision_body_state_native import CONTRACT as BODY_CONTRACT, SCHEMA as BODY_SCHEMA
from scripts.game_data.collision_capture_body_state import decode_body_states
from scripts.game_data.collision_capture_memory import AddressCoverage
from scripts.game_data.collision_pair_filter_native import load as load_filter
from scripts.game_data.collision_runtime_mesh import load_admission, read_calls, _le_pointer, _output_path
from scripts.game_data.collision_runtime_mesh_native import load_layout
from scripts.game_data.corpus_common import atomic_write_text


def summarize(bodies, memory, receipt, contract):
    selected = [s for s in bodies['samples'] if s['stable'] and
        s['after']['actorClass'] in (1, 2) and
        s['after']['readMask'] == (2031 if s['after']['actorClass'] == 1 else 2047)]
    shader = next(w['rva'] for w in contract['codeWindows'] if w['role'] == 'shader')
    player = _le_pointer(receipt['playerBase'])
    matched = [s for s in selected if s['after']['filterSlot0'] == player+shader]
    shapes = Counter((s['actor'], s['shape'], s['after']['actorClass'],
                      tuple(s['after']['simulationFilterWords']), tuple(s['after']['queryFilterWords'])) for s in matched)
    rules = contract['rules']
    coverage = AddressCoverage(memory['windows'])
    requests = []
    # Each requested range retains the original sample call. Even an any-call
    # address union cannot repair a missing same-call typed operand.
    for scene, slot1, notification in sorted({(s['after']['storedScbScene'], s['after']['filterSlot1'],
                                              s['after']['notificationCallback']) for s in matched}):
        call = next(s['call'] for s in matched if (s['after']['storedScbScene'], s['after']['filterSlot1'],
                    s['after']['notificationCallback']) == (scene, slot1, notification))
        spans = dict(managerPointer=coverage.span(player+contract['layout']['manager']['cell'], 8, call),
            kinematicKinematicMode=coverage.span(scene+contract['layout']['scene']['kinematicKinematicMode'], 4, call),
            kinematicStaticMode=coverage.span(scene+contract['layout']['scene']['kinematicStaticMode'], 4, call))
        if notification:
            spans['notificationObjectVtable'] = coverage.span(notification, 8, call)
        requests.append(dict(internalScene=f'{scene:016x}', publicScene=f"{scene+contract['layout']['scene']['publicDelta']:016x}", call=call,
            pairCallback=f'{slot1:016x}', notificationCallback=f'{notification:016x}', ranges=spans))
    ignore_ranges = []
    keyed = {}
    for sample in matched:
        words = sample['after']['simulationFilterWords']
        key = words[rules['keyLowWord']] | words[rules['keyHighWord']] << 32
        if key and not key & rules['tagMask']:
            keyed.setdefault(key, sample['call'])
    for key, call in sorted(keyed.items()):
        ignore_ranges.append(dict(key=f'{key:016x}', call=call,
            ranges={name:coverage.span(key+offset, 8, call)
                    for name, offset in contract['layout']['ignoreList'].items()},
            boundary='Raw untagged key and list-header address coverage only; no object lifetime, other pair key or executed lookup.'))
    return dict(coverage=dict(bodySamples=len(bodies['samples']), completeStableSamples=len(selected),
        selectedShaderSamples=len(matched), otherShaderSamples=len(selected)-len(matched),
        shapeConfigurations=len(shapes)),
        shapeConfigurations=[dict(actor=actor, shape=shape, actorClass=kind,
            simulationFilterWords=list(sim), queryFilterWords=list(query), samples=count,
            layer=sim[rules['layerWord']] & ((1 << rules['layerLowBits'])-1),
            taggedKey=bool(sim[rules['keyLowWord']] & rules['tagMask']),
            singleShapeExclusionFlag=bool(sim[rules['policyWord']] & rules['forcedExclusionMask']),
            dualShapeExclusionFlag=bool(sim[rules['policyWord']] & rules['bothExclusionMask']))
            for (actor, shape, kind, sim, query), count in sorted(shapes.items())],
        operandCoverage=requests,
        ignoreListCoverage=ignore_ranges,
        compiledRules=dict(abi=contract['abi'], shader=rules, upstream=contract['upstream']),
        remainingGaps=[
            'Query-hit shape observations supply no original simulation pair, coexistence or overlap.',
            'Scene-mode operands and committed body-core flags select upstream exclusion before the shader.',
            'The layer matrix requires its observed manager pointer and selected row; tagged keys bypass only the object-list lookup.',
            'Untagged nonzero keys require the same original call\'s list and target key for an object exclusion decision.',
            'A notification callback pointer alone supplies neither its typed virtual target nor delivered contacts.',
            'Shader flags can be changed downstream; they do not establish solving or report delivery.'],
        boundary='Direct sampled scene shader address and complete original compiled rules. Operand coverage is an address-range check; no executed filter decision or inferred pair.')


def summarize_execution(observed, contract):
    """Keep executed decisions, passive policies and missing step joins distinct."""
    rules=contract['rules'];permit=rules['resultDefault'];exclude=rules['resultExcluded']
    trigger_mask=rules['triggerAttributeMask']
    shaders=observed['shaders'];dispatches={d['call']:d for d in observed['dispatches']}
    by_shader={s['call']:s for s in shaders}
    paired=[]
    for pair in observed['prefilters']:
        children=[dispatches[c] for c in pair['dispatcherCalls']]
        linked=[by_shader[c] for child in children for c in child['shaderCalls']]
        paired.append(dict(call=pair['call'],dispatcherCalls=pair['dispatcherCalls'],shaderCalls=[s['call'] for s in linked],
            originalResult=pair['originalResult'],stepStatus=pair['step']['status'],
            permittedTrigger=bool(pair['originalResult'] and pair['originalResult']['filterFlags']==permit and
                linked and all(s['originalFilterResult']==permit and (s['arguments'][1]|s['arguments'][3])&trigger_mask for s in linked))))
    policies=[p for p in observed['policies'] if p['stable'] and p['after']['readMask']&31==31]
    policy_groups=Counter((p['after']['publicScene'],p['after']['kinematicKinematicMode'],p['after']['kinematicStaticMode'],
        p['after']['shader'],p['after']['notificationTarget'],tuple(p['after']['matrixRows'])) for p in policies)
    compared=[s for s in shaders if s['conditionalModel'] is not None]
    flags_compared=[s for s in compared if s['conditionalModel']['pairFlags'] is not None]
    excluded_compared=[s for s in compared if s['conditionalModel']['result']==exclude]
    unbound=[s for s in shaders if s.get('dispatcherCall') not in dispatches]
    proved_steps={'observed_original_ancestry', 'observed_original_worker_generation'}
    return dict(coverage=dict(originalPrefilters=len(paired),prefiltersWithDispatcher=sum(bool(p['dispatcherCalls']) for p in paired),
        prefiltersWithObservedStep=sum(p['stepStatus'] in proved_steps for p in paired),
        prefiltersWithoutObservedStep=sum(p['stepStatus'] not in proved_steps for p in paired),
        permittedTriggerPrefilters=sum(p['permittedTrigger'] for p in paired),
        originalShaders=len(shaders),excludedShaders=sum(s['originalFilterResult']==exclude for s in shaders),
        permittedShaders=sum(s['originalFilterResult']==permit for s in shaders),
        layerExclusions=sum(d['originalExcluded'] for d in observed['layerDecisions']),
        objectExclusions=sum(d['originalExcluded'] for d in observed['objectDecisions']),
        conditionalResultComparisons=len(compared),conditionalResultMatches=sum(s['conditionalModel']['matchesOriginalResult'] for s in compared),
        conditionalFlagComparisons=len(flags_compared),conditionalFlagMatches=sum(s['conditionalModel']['pairFlags']==s['pairFlagsAfter'] for s in flags_compared),
        excludedFlagPreservationComparisons=len(excluded_compared),excludedFlagPreservationMatches=sum(s['pairFlagsBefore']==s['pairFlagsAfter'] for s in excluded_compared),
        shadersWithoutCapturedPair=len(unbound),permittedNonTriggerShadersWithoutCapturedPair=sum(s['originalFilterResult']==permit and not (s['arguments'][1]|s['arguments'][3])&trigger_mask for s in unbound),
        completeStablePolicySamples=len(policies),stableTypedOwnerSamples=sum(o['stable'] for o in observed['owners']),
        versionedEcsOwnerSamples=sum(o['versionedEcsOwner'] is not None for o in observed['owners'])),
        prefilters=paired,
        scenePolicies=[dict(publicScene=scene,kinematicKinematicMode=kk,kinematicStaticMode=ks,shader=shader,
            notificationTarget=target,matrixRows=list(matrix),samples=count) for (scene,kk,ks,shader,target,matrix),count in sorted(policy_groups.items())],
        layerDecisions=[dict(layer0=a,layer1=b,originalExcluded=excluded,samples=count)
            for (a,b,excluded),count in sorted(Counter((d['layer0'],d['layer1'],d['originalExcluded']) for d in observed['layerDecisions']).items())],
        conditionalExclusionInputs=[dict(predicates=list(predicates),samples=count)
            for predicates,count in sorted(Counter(tuple(sorted(name for name,value in s['conditionalModel']['exclusions'].items() if value is True))
                for s in compared if s['originalFilterResult']==exclude).items())],
        boundary='Original sampled returns establish decisions; repeated policies and conditional flag comparisons remain separately timed. Permitted triggers and unbound shaders do not establish solver work. Missing original step ancestry remains missing.')


def verify_pair_replay(cached, recomputed, source):
    if cached==recomputed:
        return
    cached=cached if isinstance(cached,dict) else {}
    key=next(k for k in sorted(set(cached)|set(recomputed)) if cached.get(k)!=recomputed.get(k))
    expected,actual=recomputed.get(key),cached.get(key);field=key;call=None
    if isinstance(expected,list) and isinstance(actual,list):
        for index,(left,right) in enumerate(zip(expected,actual)):
            if left==right:continue
            field+=f'[{index}]'
            if isinstance(left,dict) and isinstance(right,dict):
                call=left.get('call');name=next(k for k in sorted(set(left)|set(right)) if left.get(k)!=right.get(k))
                field+='.'+name;expected,actual=left.get(name),right.get(name)
            else:expected,actual=left,right
            break
        else:expected,actual=len(expected),len(actual);field+='.length'
    raise ValueError(f'cached pair/filter observations differ: source={source},field={field},call={call},'
        f'expected={repr(expected)[:160]},actual={repr(actual)[:160]}')


def audit(root: Path, *, game_root: Path):
    root = root.resolve()
    result = dict(schema='endfield.collision-runtime-filter.v3', status='failed', session=str(root), diagnostics=[])
    try:
        admitted, profile, receipt, _ = load_admission(root, game_root=game_root)
        if profile['schema'] not in ('endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
            raise ValueError('capture has no typed body/shape filter records')
        directory = game_root.parent if game_root.name == 'Endfield_Data' else game_root
        paths = {name: directory/row['relativePath'] for name, row in profile['files'].items()}
        body, body_gate = load_layout(gameassembly=paths['gameAssembly'], metadata=paths['metadata'],
            unityplayer=paths['unityPlayer'], contract_path=BODY_CONTRACT, schema=BODY_SCHEMA,
            validator='collision_runtime_filter_body')
        result['bodyNativeGate'] = body_gate
        if body is None:
            raise ValueError('body filter native gate:'+body_gate['status'])
        if body != profile['bodyCapture']['contract']:
            raise ValueError('current/frozen body filter contract differs')
        contract, gate = load_filter(gameassembly=paths['gameAssembly'], metadata=paths['metadata'],
                                    unityplayer=paths['unityPlayer'])
        result['filterNativeGate'] = gate
        if contract is None:
            raise ValueError('pair-filter native gate:'+gate['status'])
        if contract['nativeInputs'] != body['nativeInputs']:
            raise ValueError('pair-filter/body selected native inputs differ')
        calls = read_calls(root, profile)
        bodies = decode_body_states(calls, profile, receipt)
        if bodies != admitted['bodyStates']:
            raise ValueError('cached body/filter observations differ')
        summary = summarize(bodies, admitted['nativeMemory'], receipt, contract)
        if profile['schema'] in ('endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
            from scripts.game_data.collision_capture_pair_filter import decode_pair_filter
            lifecycle=None
            if profile['schema'] in ('endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
                from scripts.game_data.collision_capture_geometry_state import decode_geometry_state
                from scripts.game_data.collision_capture_lifecycle import decode_lifecycle
                geometry=decode_geometry_state(calls,profile,receipt,admitted['nativeMemory'])
                lifecycle=decode_lifecycle(calls,profile,receipt,geometry)
                if lifecycle!=admitted['lifecycle']:raise ValueError('cached lifecycle/body replay differs')
            pairs=decode_pair_filter(calls,profile,receipt,task_routes=lifecycle['taskRoutes'] if lifecycle else None)
            verify_pair_replay(admitted['pairFiltering'],pairs,root/'events.jsonl')
            summary['executed']=pairs
            summary['executionSummary']=summarize_execution(pairs,contract)
            summary['operandCoverageScope']='Body-record archive windows only; inline policy matrices and original helper decisions are reported separately in executed and executionSummary.'
            summary['remainingGaps']=[
                'Pair calls without original step ancestry remain unbound; scene addresses and nearby updates cannot supply a generation.',
                'Shaders without a captured pair retain their own original result but no pair-bound actor/shape ownership.',
                'Passive matrix/list and owner reads remain separately timed; bounded ignore-list tails and continuous lifetime are not supplied.',
                'Permitted processing and observed notification targets do not establish contact preparation, solving or delivered reports.',
                'Versioned ECS owners do not alone identify a serialized Mesh; native-only owners retain no CAB/PathID join.']
            summary['boundary']='Direct original sampled pair/filter/helper returns and typed owner/policy observations; compiled model comparisons remain conditional. No missing step, continuous lifetime or positive solver-contact inference.'
        if (sha256_file(root/'events.jsonl') != admitted['journalSha256'] or
                sha256_file(root/'native-memory.bin') != receipt['nativeMemory']['sha256']):
            raise ValueError('capture changed during pair-filter audit')
        execution=summary.get('executionSummary',{}).get('coverage',{})
        result.update(status='validated_compiled_rules_and_sampled_execution' if execution.get('originalShaders') or execution.get('originalPrefilters') else 'validated_compiled_rules_and_sampled_selection',
            journalSha256=admitted['journalSha256'], archiveSha256=receipt['nativeMemory']['sha256'], **summary)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, struct.error) as error:
        result.update(status='failed', diagnostics=[dict(check='runtime_pair_filter', detail=str(error)[:1800])])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    result = audit(args.session, game_root=args.game_root)
    output = _output_path(args.output or args.session/'collected/runtime-filter.json')
    atomic_write_text(output, json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key:result[key] for key in ('status', 'coverage', 'diagnostics') if key in result} | (
        {'executionCoverage':result['executionSummary']['coverage']} if 'executionSummary' in result else {})))
    return int(result['status'] == 'failed')


if __name__ == '__main__':
    raise SystemExit(main())
