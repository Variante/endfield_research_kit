"""Shared producer and replay gates for explicitly scoped Unity supplements.

Each domain owns its types, schema and raw inspection. This module authenticates
only the extraction and current inputs; it never infers a component layout.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess
import tempfile

from scripts.common import sha256_file, write_json
from scripts.game_data.cooked_collision_corpus import _decoder_closure, _selection_input
from scripts.game_data import unity_scene_corpus as scenes
from scripts.game_data.unity_scene import read_scene_object, scene_identity
from scripts.game_data.unity_asset_bundle import read_container_prefix


def selection(scene):
    sources = {(r['identity']['sourceOriginalPath'], r['identity']['sourceOffset'])
               for r in scene['rawSources'] if r['type'] == 'AssetBundle'}
    if not sources:
        raise ValueError('Unity supplement needs admitted physical AssetBundle sources')
    return [dict(Source=source, Offset=offset, PathID=0, Type='AssetBundle', Name='')
            for source, offset in sorted(sources)]


def command(scene, run, types):
    return [scene['extraction']['command'][0], str(_selection_input(selection(scene))), str(run/'json'),
            '--game', 'ArknightsEndfield', '--types', *types, '--export_type', 'JSON',
            '--filter_data', str(run/'selection.json'), '--secondary_export_type', 'Raw',
            '--secondary_export_path', str(run/'raw'), '--secondary_types', *types,
            '--logger_flags', 'Warning', 'Error']


def inspect_sources(run, scene, types):
    """Authenticate supplemental census and reuse admitted stored scene bodies."""
    admitted = {scene_identity(r['identity']): r for r in scene['rawSources']}
    bundles = {k:r for k,r in admitted.items() if r['type']=='AssetBundle'}
    cabs = {key[:3] for key in bundles}
    bodies, prefab_roots = {}, {}
    for key, row in admitted.items():
        if row['type'] not in ('GameObject','Transform'):
            continue
        raw = Path(row['rawPath']).read_bytes()
        if len(raw)!=row['byteSize'] or hashlib.sha256(raw).hexdigest()!=row['rawSha256']:
            raise ValueError(f"supplement scene body changed: {row['rawPath']}")
        bodies[key] = dict(read_scene_object(row['type'],raw),kind=row['type'])
    sources, documents, seen = {}, {}, set()
    for path in sorted((run/'json').glob('*/*.json')):
        document=json.loads(path.read_text('utf-8-sig')); meta=document['$animestudio']
        kind=meta['type'];key=scene_identity(meta)
        if kind not in types or path.parent.name!=kind or key[:3] not in cabs or key in seen:
            raise ValueError(f'Unity supplement identity/type/selection differs: {path}')
        seen.add(key)
        raw_path=run/'raw'/kind/(path.stem+'.dat');raw=raw_path.read_bytes()
        digest=hashlib.sha256(raw).hexdigest()
        if len(raw)!=meta['byteSize'] or len(raw)!=meta['rawDataLength'] or digest!=meta['rawDataSha256']:
            raise ValueError(f'Unity supplement raw length/hash differs: {raw_path}')
        source=dict(identity={f:meta[f] for f in ('sourceOriginalPath','sourceOffset','sourceFile','pathId')},
                    type=kind,jsonPath=str(path),rawPath=str(raw_path),rawSha256=digest,
                    jsonSha256=sha256_file(path),byteSize=len(raw))
        sources[key]=source;documents[key]=(document,raw)
        if kind!='AssetBundle':
            if key in admitted:
                raise ValueError('supplement component conflicts with admitted scene identity')
            continue
        if key not in bundles or bundles[key]['rawSha256']!=digest:
            raise ValueError('supplement AssetBundle differs from admitted physical object')
        prefix=read_container_prefix(raw);scenes._check_typed(prefix,document,kind)
        for entry in prefix['containers']:
            if entry['asset'][0]==0 and entry['asset'][1] and entry['path'].endswith('.prefab'):
                target=(*key[:3],entry['asset'][1]&((1<<64)-1))
                if bodies.get(target,{}).get('kind')=='GameObject':
                    prefab_roots.setdefault(target,set()).add(entry['path'])
    if ({Path(r['rawPath']).resolve() for r in sources.values()}
            != {p.resolve() for p in (run/'raw').glob('*/*.dat')}):
        raise ValueError('Unity supplement raw/typed object census differs')
    if {key for key in seen if key in bundles}!=set(bundles):
        raise ValueError('Unity supplement physical AssetBundle coverage differs')
    return sources, documents, bodies, prefab_roots


def collect(scene_receipt, *, work_root, prefix, types, inspect):
    scene_receipt = scene_receipt.resolve(); scene = scenes.validate_receipt(scene_receipt)
    work_root.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=prefix, dir=work_root.resolve()))
    selection_path = run/'selection.json'; write_json(selection_path, selection(scene))
    args = command(scene, run, types); log_path = run/'export.log'
    with log_path.open('wb') as log:
        completed = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=False)
    if completed.returncode or log_path.stat().st_size:
        raise ValueError(f'Unity supplement export failed/diagnosed: exit={completed.returncode}; log={log_path}; '
                         + log_path.read_text('utf-8', errors='replace')[:1000])
    scenes.check_receipt_snapshot(scene)
    report = inspect(run, scene)
    report.update(inputSetSha256=scene['inputSetSha256'], sceneReceipt=str(scene_receipt),
                  sceneReceiptSha256=sha256_file(scene_receipt),
                  extraction=dict(command=args, log=str(log_path), logSha256=sha256_file(log_path),
                                  selectionSha256=sha256_file(selection_path),
                                  decoderOutputClosure=scene['extraction']['decoderOutputClosure']))
    scenes.check_receipt_snapshot(scene)
    return report


def validate_receipt(path, scene, *, schema, types, inspect):
    original = path.read_bytes(); saved = json.loads(original)
    if saved.get('schema') != schema or saved.get('status') != 'complete' or saved.get('failures'):
        raise ValueError(f'Unity supplement receipt is not complete: {schema}')
    if (saved['inputSetSha256'] != scene['inputSetSha256']
            or saved['sceneReceipt'] not in scene['currentInputSnapshots']
            or sha256_file(Path(saved['sceneReceipt'])) != saved['sceneReceiptSha256']):
        raise ValueError('Unity supplement receipt and admitted scene inputs differ')
    run = Path(saved['extraction']['command'][2]).parent
    selection_path = run/'selection.json'; log_path = run/'export.log'
    if (json.loads(selection_path.read_bytes()) != selection(scene)
            or sha256_file(selection_path) != saved['extraction']['selectionSha256']
            or command(scene, run, types) != saved['extraction']['command']
            or str(log_path) != saved['extraction']['log'] or log_path.stat().st_size
            or sha256_file(log_path) != saved['extraction']['logSha256']
            or _decoder_closure(Path(scene['extraction']['command'][0])) != saved['extraction']['decoderOutputClosure']
            or saved['extraction']['decoderOutputClosure'] != scene['extraction']['decoderOutputClosure']):
        raise ValueError('Unity supplement extraction selection/command/log/exporter gate differs')
    paths = {path.resolve(), selection_path, log_path}
    paths.update(Path(r[f]) for r in saved['rawSources'] for f in ('jsonPath', 'rawPath'))
    snapshots = {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in paths}
    current = inspect(run, scene)
    if current['rawSources'] != saved['rawSources'] or path.read_bytes() != original:
        raise ValueError('Unity supplement receipt object hashes or receipt changed')
    scenes.check_receipt_snapshot(scene)
    current['currentInputSnapshots'] = snapshots
    scenes.check_receipt_snapshot(current)
    return current
