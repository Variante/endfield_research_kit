"""Prepare the targeted damage operand observer offline from selected native inputs."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data import damage_operand_capture_native as native
from scripts.game_data import mission_trace_capture_prepare as mission
from scripts.repo_paths import REPO_ROOT

RECIPE = CONTRACTS_DIR / 'damage_operand_capture.json'
SCHEMA = 'endfield.damage-operand-capture-recipe.v1'
CONTEXT_ABI = 'win64.entry_context.v1'
PREFIX = 'damage.Operand.'
NO_CHAIN = 4097


def require(condition, detail):
    if not condition:
        raise mission.PreparationError('damage_operand: ' + detail)


def field(label, kind, *, offset=0, chain0=NO_CHAIN, width=64, **extra):
    return dict(label=label, type='ulong' if width == 64 else 'int', valueBits=width,
                arg=0, kind=kind, offset=offset, chain0=chain0, chain1=NO_CHAIN, **extra)


def compile_operand_hooks(proof, recipe, base_hooks, contract):
    """Compile only the native validator's bounded entry observations."""
    require(proof.get('status') == 'validated', 'native observation proof did not validate')
    require(proof.get('runtimeValues') is None, 'preparation cannot contain live values')
    names = [hook['name'] for hook in base_hooks]
    require(len(names) == len(set(names)), 'duplicate base hook names')
    require(names.count(recipe['processHook']) == 1, 'unique Process hook required')
    require(names.count(recipe['packHook']) == 1, 'unique Pack hook required')
    process_index = names.index(recipe['processHook'])
    require(base_hooks[process_index].get('observationMode') == 'paired', 'Process must be paired')
    fields = {row['field']: row for row in contract['fields']}
    data = fields['Beyond.Gameplay.Core.AbilitySystem::<data>k__BackingField']['offset']
    health = fields['Beyond.Gameplay.Core.AbilitySystemData::healthType']['offset']
    hooks = []
    sites = proof.get('sites', [])
    require(len(sites) == 5, 'expected the complete five-entry observation set')
    for site in sites:
        key = site['key']
        name = PREFIX + key
        require(name not in names and name not in [h['name'] for h in hooks], 'duplicate observation key')
        expected = bytes.fromhex(site['expectedBytes'])
        require(16 <= len(expected) <= 256, 'bounded native entry bytes required')
        returns = sorted(int(v, 16) if isinstance(v, str) else v for v in site['callerReturnRvas'])
        require(returns and len(returns) == len(set(returns)), 'unique explicit caller returns required')
        require(all(type(v) is int and 0 < v <= 0xffffffff for v in returns), 'caller return RVA outside module domain')
        common = dict(name=name, module='GameAssembly.dll', rva=site['rva'],
                      expectedBytes=expected.hex(), fields=[],
                      captureCallerReturnRvas=','.join(f'{v:x}' for v in returns),
                      captureScope='paired-ancestor', captureCallerHooks=[recipe['processHook']],
                      operandEntryKey=key, operandEntryProof=copy.deepcopy(site),
                      evidenceBoundary=recipe['evidenceBoundary'])
        if site['type'] == 'entryContext':
            spans = [dict(label=label, type='byte[]', valueBits=0, arg=0, kind=6,
                          offset=0, chain0=NO_CHAIN, chain1=NO_CHAIN, byteCount=count)
                     for label, count in [('contextRegisters', 160), ('contextVectors', 256)]]
            program = f'ctx1:{process_index};' + ''.join(
                ','.join(str(n) for n in mission.read_words(row)) + ';' for row in spans)
            common.update(abiId=CONTEXT_ABI, observationMode='entry-context', returnType='void',
                          fields=spans, readProgram=program,
                          contextProcessHookIndex=process_index)
        elif key == 'healthPredicateEntry' and site['type'] == 'physicalPaired':
            snapshots = [field('defenderIdentity', 4, role='identity'),
                         field('defenderDataIdentity', 1, offset=data, role='identity',
                               valueRepresentation='referenceIdentity'),
                         field('defenderHealthTypeSnapshot', 2, offset=health, chain0=data,
                               width=32, role='entry-snapshot')]
            common.update(abiId='win64.scoped_paired_gp_bool_1.v1', observationMode='paired',
                          returnType='bool', fields=snapshots,
                          readProgram='v2:' + ''.join(','.join(str(n) for n in mission.read_words(row)) + ';' for row in snapshots),
                          snapshotBoundary='at-predicate-entry; not the later native load',
                          physicalAbi=True)
        elif key == 'usesRawEntry' and site['type'] == 'managedPaired':
            snapshots = [field('damageType', 4, width=32, role='incoming-value')]
            common.update(abiId='win64.scoped_paired_gp_bool_2.v1', observationMode='paired',
                          returnType='bool', fields=snapshots,
                          readProgram='v2:' + ''.join(','.join(str(n) for n in mission.read_words(row)) + ';' for row in snapshots))
        else:
            raise mission.PreparationError('damage_operand: unsupported observation entry: ' + key)
        hooks.append(common)
    require(sum(h['abiId'] == CONTEXT_ABI for h in hooks) == 3, 'three first-call entry observers required')
    require(len(base_hooks) + len(hooks) <= mission.MAX_HOOKS, 'observer capacity exceeded')
    return hooks


def prepare(game_dir):
    recipe = json.loads(RECIPE.read_text(encoding='utf-8'))
    require(recipe.get('schema') == SCHEMA and recipe.get('status') == 'reviewed', 'unreviewed recipe')
    require(recipe['nativeContract'] == native.CONTRACT.name, 'native contract owner differs')
    base_path = (CONTRACTS_DIR / recipe['baseRecipe']).resolve()
    require(base_path.parent == CONTRACTS_DIR.resolve(), 'base recipe must be a sibling contract')
    base = mission.prepare(Path(game_dir), recipe=mission.read_recipe(base_path))
    root = Path(game_dir).resolve()
    if root.name.casefold() == 'endfield_data':
        root = root.parent
    ga = root / base['files']['gameAssembly']['relativePath']
    md = root / base['files']['metadata']['relativePath']
    proof = native.load_damage_operand_capture(gameassembly=ga, metadata=md)
    require(proof.get('status') == 'validated', 'native proof failed: ' + str(proof.get('failures')))
    pins = proof['nativeInputs']
    for name, key in [('gameAssembly', 'gameAssemblySha256'), ('metadata', 'metadataSha256')]:
        require(base['files'][name]['sha256'].lower() == pins[key].lower(), 'base and observation native epochs differ')
    contract_bytes = native.CONTRACT.read_bytes()
    require(hashlib.sha256(contract_bytes).hexdigest().lower() == proof['contractSha256'].lower(),
            'native contract changed after validation')
    contract = json.loads(contract_bytes)
    hooks = compile_operand_hooks(proof, recipe, base['missionTraceHooks'], contract)
    gate = check_installed_native_inputs(pins['gameAssemblySha256'], pins['metadataSha256'],
                                         gameassembly=ga, metadata=md)
    require(gate.validated, 'selected inputs changed: ' + gate.detail)
    require(native.CONTRACT.read_bytes() == contract_bytes, 'native contract changed during preparation')
    base.update(recipeSchema=SCHEMA, baseRecipeSchema=base['recipeSchema'],
                recordingScope='damage-operands-with-explicit-process-scope',
                operandNativeProof=proof, operandRecipe=recipe,
                evidenceBoundary=recipe['evidenceBoundary'],
                coverageGaps=base.get('coverageGaps', []) + recipe['coverageGaps'])
    base['missionTraceHooks'].extend(hooks)
    return base


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=REPO_ROOT / 'reports/runtime_capture/damage-operands-build.json')
    parser.add_argument('--report', type=Path, default=REPO_ROOT / 'reports/runtime_capture/damage-operands-preparation.json')
    args = parser.parse_args(argv)
    output, report = mission.checked_output(args.output), mission.checked_output(args.report)
    require(output != report, 'build and report paths must differ')
    try:
        manifest = prepare(args.game_dir)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        diagnostic = dict(schema='endfield.damage-operand-preparation.v1', status='failed',
                          detail=str(exc)[:2000], liveAttached=False)
        atomic_write_text(report, json.dumps(diagnostic, indent=2) + '\n')
        print(json.dumps(diagnostic)); return 1
    atomic_write_text(output, json.dumps(manifest, indent=2) + '\n')
    result = dict(schema='endfield.damage-operand-preparation.v1', status='validated',
                  manifest=str(output), hookCount=len(manifest['missionTraceHooks']),
                  contextHooks=3, liveAttached=False, runtimeValues=None)
    atomic_write_text(report, json.dumps(result, indent=2) + '\n')
    print(json.dumps(result)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
