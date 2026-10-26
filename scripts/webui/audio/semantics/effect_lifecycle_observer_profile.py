"""Compile the dedicated bank/subscriber/template lifecycle observation recipe."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.wwise_effect_lifecycle_native import load_validated
from scripts.game_data.wwise_source_native import _collect_opened_source_image
from scripts.game_data.wwise_source_queue_native import validate_native_group_declarations, validate_native_group_windows
from scripts.repo_paths import REPO_ROOT
from scripts.webui.audio.semantics.playback_observer_profile import compile_reads
from scripts.webui.story_recovery.prepare_endfield_source_owner import prepare as prepare_source


def compile_scope(row, symbols):
    """Compare named entry fields against authenticated class/address points."""
    fields={f['name']:i for i,f in enumerate(row['memory'])};tests=[];seen=set();previous=None
    selection=row.get('selection',{});predicates=selection.get('predicates',[])
    if len(predicates)>4:raise ValueError('Effect scope predicate bound exceeded')
    for predicate in predicates:
        index=fields[predicate['field']];value,relative=symbols[predicate['equals']]
        if index in seen and index!=previous:raise ValueError('Effect scope alternatives must be contiguous')
        seen.add(index);previous=index
        if type(value) is not int or not 0<=value<2**32 or relative not in (0,1):raise ValueError('Effect scope value invalid')
        tests.append(f'{index},{value},{relative};')
    parents=selection.get('parentIndices',[])
    if len(set(parents))!=len(parents) or any(type(i) is not int or not 0<=i<34 for i in parents):raise ValueError('Effect scope parent invalid')
    return ''.join(tests),sum(1<<i for i in parents)


def project(base, contract, audit, image):
    observer = contract['observer']; owners = {}; hooks = []
    _, bodies, records = _collect_opened_source_image(image, 'effect lifecycle capture sites')
    for index, row in enumerate(observer['hooks']):
        if row['index'] != index or row['name'] != 'AkSoundEngine.' + row['ownerGroup']:
            raise ValueError('Effect lifecycle hook order/name differs')
        name = row['ownerContract']
        if name not in owners:
            owner = contract if name == 'wwise_effect_lifecycle_native' else json.loads((CONTRACTS_DIR / (name + '.json')).read_bytes())
            if owner['status'] != 'reviewedCurrentBuild' or owner['nativeInputs'] != contract['nativeInputs']:
                raise ValueError('Effect lifecycle hook owner inputs/status differ')
            owners[name] = owner
        if row.get('entryFromProof'):
            # The parameter validator already authenticates its original
            # factory body and address point from the registration owner.
            # Borrow that proof instead of duplicating its native catalog.
            if row['entryFromProof']!='parameterFactoryRva' or name!='wwise_room_parameters_native' or row['ownerGroup']!='roomParameterFactory':raise ValueError('Effect factory observation proof differs')
            entry=audit['parameterProof']['parameterFactoryRva']
        else:
            group = next(g for g in owners[name]['nativeGroups'] if g['key'] == row['ownerGroup'])
            validate_native_group_declarations([group]); validate_native_group_windows([group], image, bodies, records)
            entry=group['entryRva']
        symbols=dict(roomParameterVtable=(int(audit['parameterProof']['parameterVtableRva'],16),1),templateVtable=(int(audit['templateVtableRva'],16),1),subscriberVtable=(int(contract['subscriberAddressPoint']['rva'],16),1),roomParameterClass=(int(observer['parameterClassId'],16),0))
        symbols.update({p['key']:(int(p['rva'],16),1) for p in contract['derivedTemplateAddressPoints']})
        scope_tests,scope_parent_mask=compile_scope(row,symbols)
        hooks.append(dict(name=row['name'], sourceKind=row['ownerGroup'], module='AkSoundEngine.dll',
                          rva=entry, required=True, abiId=row['abiId'],
                          memory=copy.deepcopy(row['memory']), resultMemory=copy.deepcopy(row['resultMemory']),
                          readProgram=compile_reads(row['memory']), resultProgram=compile_reads(row['resultMemory']),scopeTests=scope_tests,scopeParentMask=scope_parent_mask))
    if len(hooks) != 34:
        raise ValueError('Effect lifecycle requires its dedicated 34 paired hooks')
    result = {k: copy.deepcopy(base[k]) for k in ('gameBuild','processName','moduleName','nativeModuleName','files','hooks')}
    external = next(h for h in result['hooks'] if h['name'] == 'AudioAdapter._PostEventWithExternalSource')
    external['abiId'] = 'win64.il2cpp_post_event_external_source.v3'
    result.update(schema=observer['buildSchema'], observerProfile='audioEffectLifecyclePhasesV1', nativeHooks=hooks,
                  phaseNames={'1':'enter','2':'return','3':'unwind'}, automaticWindow=True,
                  nativeSelectionScope='explicitWindowIds', effectLifecycle=copy.deepcopy(observer),
                  evidenceBoundary=copy.deepcopy(contract['evidenceBoundary']), captureBoundary='Unsampled paired calls satisfying declared entry-field predicates and observed-parent scopes in explicit windows. Bank references and carrier/subscription/destruction select reviewed base/shared/custom effect interfaces; actual target registration descendants are retained. Typed parameter writes, clone processing and asynchronous callback comparisons select Room. Bank byte reads require an observed bank-effect parent. Scope exclusions and unreadable predicates have separate counters; unreadable selection withholds claims. Non-Room retained pointers do not acquire inferred allocation generations. Missing startup births remain unresolved.')
    result['effectLifecycle'].pop('hooks')
    result['effectLifecycle'].update(parameterVtableRva=audit['parameterProof']['parameterVtableRva'], templateVtableRva=audit['templateVtableRva'])
    result['effectLifecycle']['subscriberVtableRva']=contract['subscriberAddressPoint']['rva']
    result['effectLifecycle']['templateVtableRvas']=[audit['templateVtableRva']]+[p['rva'] for p in contract['derivedTemplateAddressPoints']]
    parameter_owner=owners['wwise_room_parameters_native']
    result['effectLifecycle']['parameterUpdateRows']=copy.deepcopy(parameter_owner['dispatch']['rows'])
    return result


def prepare(game_root, output):
    root = Path(game_root).resolve(); output = Path(output).resolve()
    if REPO_ROOT / 'reports' not in output.parents:
        raise ValueError('Generated lifecycle manifest must stay under reports/')
    args = dict(gameassembly=root/'GameAssembly.dll', metadata=root/'Endfield_Data/il2cpp_data/Metadata/global-metadata.dat', ak_sound_engine=root/'Endfield_Data/Plugins/x86_64/AkSoundEngine.dll')
    contract, audit = load_validated(**args)
    if contract is None:
        raise ValueError('Effect lifecycle native gate ' + audit['status'] + ': ' + audit['detail'])
    base, source_audit = prepare_source(root, REPO_ROOT/'reports/audio/lifecycle_source_basis.json', REPO_ROOT/'reports/audio/lifecycle_source_basis_gate.json')
    if base is None:
        raise ValueError('Effect lifecycle managed gate ' + source_audit['status'])
    image = load_native_mapper(NATIVE_MAPPER_PATH).PeImage(args['ak_sound_engine'])
    manifest = project(base, contract, audit, image)
    output.parent.mkdir(parents=True, exist_ok=True)
    staged = output.with_suffix('.tmp'); staged.write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8'); staged.replace(output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=REPO_ROOT/'reports/audio/effect_lifecycle_capture_manifest.json')
    args = parser.parse_args(); manifest = prepare(args.game_root, args.output)
    print(f"{len(manifest['nativeHooks'])} paired lifecycle hooks -> {args.output}")


if __name__ == '__main__':
    main()
