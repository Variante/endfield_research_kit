"""Extract and admit stored BoxColliders within an admitted scene selection.

This supplemental scope does not widen the scene/Mesh receipt. Only selected
physical CABs participate; raw bodies and serialized type trees prove the box
layout. Names, preloads and export absence do not establish ownership/absence.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from scripts.common import write_json
from scripts.game_data import unity_scene_supplement as supplement
from scripts.game_data.unity_scene import BOX_TYPE_TREE_FIELDS, read_scene_object, trace_collider
from scripts.game_data import unity_scene_corpus as scenes
from scripts.repo_paths import REPO_ROOT

SCHEMA = "endfield.selected-unity-box-corpus.v1"
TYPES = ('BoxCollider', 'AssetBundle')


def inspect_exports(run: Path, scene: dict) -> dict:
    """Inspect supplemental output after the caller admits its source/producer."""
    sources, documents, bodies, prefab_roots = supplement.inspect_sources(run, scene, TYPES)
    box_bodies = {}
    for key, source in sources.items():
        if source['type'] != 'BoxCollider':
            continue
        document, raw = documents[key]; meta = document['$animestudio']
        if (meta.get('classId') != 65 or meta.get('typeTreeSource') != 'serializedType'
                or tuple(meta.get('typeTreeFieldPaths', [])) != BOX_TYPE_TREE_FIELDS):
            raise ValueError(f"BoxCollider serialized type-tree layout differs: {source['jsonPath']}")
        try:
            body = read_scene_object('BoxCollider', raw); scenes._check_typed(body, document, 'BoxCollider')
        except (ValueError, KeyError, TypeError, OverflowError) as error:
            raise ValueError(f"BoxCollider body gate: source={source['jsonPath']}; {error}") from error
        bodies[key] = dict(body, kind='BoxCollider'); box_bodies[key] = source
    rows = []
    for key, source in sorted(box_bodies.items()):
        try:
            trace = trace_collider(key, bodies)
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError(f"BoxCollider hierarchy gate: source={source['jsonPath']}; collider={key}; {error}") from error
        paths = sorted(prefab_roots.get(tuple(trace['chain'][-1]['gameObject']), []))
        rows.append(dict(collider=source, trace=trace, prefabPaths=paths,
                         status='exact_stored_box_link', settings={k: bodies[key][k] for k in
                             ('colliderOptions', 'tagConfig', 'surfaceType', 'isTrigger', 'enabled', 'enableDither')}))
    return dict(schema=SCHEMA, status='complete', failures=[], boxes=rows, rawSources=list(sources.values()),
                counts=dict(boxes=len(rows), prefabLinkedBoxes=sum(bool(r['prefabPaths']) for r in rows),
                            physicalBundles=sum(r['type']=='AssetBundle' for r in sources.values())),
                evidenceBoundary='Exact selected raw/typed BoxCollider fields, serialized layout, reciprocal scene hierarchy and declared prefab roots. Box size is full dimensions and center is collider-local. Mathematical stored TRS projection is not effective runtime PhysX geometry, activation or world placement. Other classes and export absence remain outside this claim.')


def collect(scene_receipt: Path, *, work_root: Path) -> dict:
    return supplement.collect(scene_receipt, work_root=work_root, prefix='boxes-',
                              types=TYPES, inspect=inspect_exports)


def validate_receipt(path: Path, scene: dict) -> dict:
    return supplement.validate_receipt(path, scene, schema=SCHEMA, types=TYPES, inspect=inspect_exports)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene-receipt', type=Path, required=True)
    parser.add_argument('--work-root', type=Path, default=REPO_ROOT/'tmp/animestudio/collision_primitives')
    parser.add_argument('--output-json', type=Path, default=REPO_ROOT/'reports/assets/collision_boxes_current.json')
    args = parser.parse_args(argv)
    if not args.output_json.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):
        parser.error('generated receipts belong under reports/')
    try:
        report = collect(args.scene_receipt, work_root=args.work_root)
        write_json(args.output_json, report)
        print('Stored BoxCollider corpus:', report['status'], report['counts'])
        return 0
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as error:
        print('Stored BoxCollider corpus failed:', str(error)[:1600])
        return 1


if __name__ == '__main__':
    if not __package__:
        raise SystemExit('Run as python -m scripts.game_data.unity_box_corpus')
    raise SystemExit(main())
