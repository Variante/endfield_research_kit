"""Publish complete current DynamicStreaming roots and independent authored joins."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts.common import resolve_installed_native_inputs
from scripts.game_data.dynamic_scalar_components_native import (
    _resolve_string_index, validate_native_layout,
)
from scripts.game_data.dynamic_stream_area_corpus import (
    MAIN_NAME_RE,
)
from scripts.game_data.dynamic_root_comp_native import (
    decode_authenticated_root_components, load_current_template_asset,
    validate_native_layout as validate_root_layout,
)
from scripts.webui.data_inspector.contract import source_descriptor
from scripts.common import sha256_file_upper
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs


def main_raw_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.bytes") if MAIN_NAME_RE.search(path.as_posix()))


def _attach_authored_owners(components: list[dict[str, Any]], references: list[dict[str, Any]],
                           fields: dict[str, int]) -> int:
    """Join only the same grid, proved vector field and stored element index."""
    indexed: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    for reference in references:
        key = (reference["gridOrdinal"], reference["fieldIndex"], reference["componentOrdinal"])
        indexed.setdefault(key, []).append(reference)
    owned = 0
    for component in components:
        matches = indexed.get((component["gridOrdinal"], fields[component["name"]], component["ordinal"]), [])
        if any(reference["component"] != component["name"]
               or reference["gridUniqueId"] != component["uniqueId"] for reference in matches):
            raise ValueError("authored root association differs from the selected component field/grid")
        component["authoredOwners"] = [{**reference["authoredOwner"],
                                       "directoryOrdinal": reference["directoryOrdinal"]} for reference in matches]
        owned += bool(matches)
    return owned


def dynamic_main_records(export_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Publish complete current roots only after every independent exit proof."""
    from scripts.game_data.dynamic_components_corpus import current_main_files
    export_root = Path(export_root).resolve()
    reader_inputs = snapshot_complete_reader_inputs()
    gameassembly, metadata = resolve_installed_native_inputs()
    complete_rows, operation = current_main_files(export_root, gameassembly=gameassembly, metadata=metadata)
    # These consumers add authored strings and associations. They have their
    # own native claims; full stored syntax never substitutes for those claims.
    scalar, main, scalar_digests, scalar_inputs = validate_native_layout(gameassembly, metadata)
    root_layout, index_layout, root_main, enums, entities, root_digests, root_inputs = validate_root_layout(gameassembly, metadata)
    if scalar_inputs != operation['nativeInputs'] or root_inputs != operation['nativeInputs']:
        raise ValueError('dynamic components: independent native selections differ')
    game_root = Path(metadata).resolve().parents[2]
    templates, template_receipt = load_current_template_asset(root_layout['templateLookup'],
        game_root=game_root, export_root=export_root, entity_enum=entities, data_enum=enums)
    fields = {row['name']: row['fieldIndex'] for row in main['vectors']}
    records = []
    for selected in complete_rows:
        source = selected['source']; path = selected['rawPath']; frame = selected['decoded']
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest().upper() != frame['sourceSha256']:
            raise ValueError('dynamic components: late input drift: ' + str(path))
        components = frame['components']
        strings = [row['text'] for row in frame['fields'][4]['value']]
        for component in components:
            for join in scalar.get('stringIndexConsumers', []):
                if join['record'] != component['name']:
                    continue
                component['stringReferences'][join['field']] = _resolve_string_index(strings, component['values'][join['field']])
        references = decode_authenticated_root_components(data, layout=root_layout, index_layout=index_layout,
            main_layout=root_main, enum_by_id=enums, entity_enum=entities, templates=templates, source=source)
        owned = _attach_authored_owners(components, references, fields)
        keys = {reference['text'] for component in components
                for reference in component['stringReferences'].values() if reference.get('status') == 'resolved'}
        relative = path.relative_to(export_root).as_posix()
        records.append(dict(id=relative, title=path.stem,
            source=source_descriptor(path, export_root=export_root, media_type='application/octet-stream'),
            status='named_exact', tags=['world', 'dynamic-streaming', 'named_exact'],
            summary=f"{len(components)} stored components; complete root; authored mission keys={len(keys)}",
            searchTerms=sorted({*frame['byType'], *keys, *(r['authoredOwner']['entityTypeName'] for r in references)}),
            facts=dict(componentCount=len(components), byType=frame['byType'], authoredMissionKeyCount=len(keys),
                authoredOwnedComponentCount=owned, authoredRootReferenceCount=len(references),
                wholeSchemaExact=True, physicalEOF=True, bytesConsumed=frame['bytesConsumed'],
                rootFieldCount=5, gridFieldCount=61),
            payloadKind='reader', payload={**frame, 'authoredRootReferences':references,
                'authoredRootAssociationGate':dict(status='validated', nativeInputs=root_inputs,
                    **root_digests, template=template_receipt),
                'evidenceBoundary':{**frame['evidenceBoundary'], 'missionConditionString':'direct',
                    'authoredRootOwnership':'direct', 'runtimeEntityOwnership':'unresolved', 'conditionEvaluation':'unresolved'}}))
    # Association work runs after the complete corpus operation. Check its
    # inputs again before returning any records to the page publisher.
    for row in operation['authenticatedInputs']:
        path = Path(row['path'])
        if not path.is_file() or sha256_file_upper(path) != row['sha256']:
            raise ValueError('dynamic components: late input drift: ' + str(path))
    corpus = operation['currentCorpus']
    for row in corpus['sourceFingerprints'] + corpus['gameBuildFingerprints']:
        path = Path(row['path'])
        if not path.is_file() or sha256_file_upper(path) != row['sha256']:
            raise ValueError('dynamic components: late VFS/native input drift: ' + str(path))
    native_paths = [(Path(gameassembly), 'gameAssemblySha256'), (Path(metadata), 'metadataSha256'),
                    (Path(gameassembly).parent / 'UnityPlayer.dll', 'unityPlayerSha256')]
    for path, key in native_paths:
        if not path.is_file() or sha256_file_upper(path) != operation['nativeInputs'][key]:
            raise ValueError('dynamic components: late native input drift: ' + str(path))
    after_templates, after_receipt = load_current_template_asset(root_layout['templateLookup'],
        game_root=game_root, export_root=export_root, entity_enum=entities, data_enum=enums)
    if (after_templates, after_receipt) != (templates, template_receipt):
        raise ValueError('dynamic components: late template input drift')
    if reader_inputs != snapshot_complete_reader_inputs():
        raise ValueError('dynamic components: late reader/contract drift')
    return records, dict(nativeStatus='validated', nativeInputs=operation['nativeInputs'],
        completeDynamicComponentsOperation=operation, authenticatedFiles=operation['authenticatedFiles'],
        authoredRootAssociations=dict(status='validated', nativeInputs=root_inputs, **root_digests, template=template_receipt),
        authoredStringConsumers=dict(nativeInputs=scalar_inputs, **scalar_digests))
