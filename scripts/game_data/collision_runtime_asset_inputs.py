"""Join observed collision input identities to current AssetBundle containers.

Only local PPtrs with the exact CAB and unsigned PathID identify an input.
Container aliases are retained; they do not select a hit shape's geometry.

Evidence and admission boundary
-------------------------------
Exact CAB and unsigned local PathID equality joins observed physical inputs to
current exported container paths only after export freshness and selected stored
hash checks. External-file PPtrs do not join by PathID alone. Aliases survive;
a container relation neither proves Unity class nor decodes raw/cooked geometry.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

from scripts.game_data.extraction.verify_export_freshness import build_report, Requirements, DEFAULT_SUMMARY
from scripts.game_data.unity_store import UnityObjectStore, store_path


def container_candidates(document, path_id):
    result=[]
    if type(path_id) is not int or not 0 <= path_id < 1 << 64:
        raise ValueError('collision input unsigned PathID bound')
    for item in document.get('m_Container', []):
        pointer=item['Value']['asset']
        pid=pointer.get('m_PathID')
        if type(pointer.get('m_FileID')) is not int or pointer['m_FileID'] != 0 or pointer.get('IsNull') is True or type(pid) is not int:
            continue
        if not -(1 << 63) <= pid < 1 << 64:
            raise ValueError('AssetBundle PPtr PathID bound')
        if pid & ((1 << 64)-1) == path_id:
            result.append(dict(path=item['Key'],preloadIndex=item['Value'].get('preloadIndex'),
                               preloadSize=item['Value'].get('preloadSize')))
    return result


def link_inputs(definitions, *, export_root: Path, game_root: Path, summary_path=DEFAULT_SUMMARY):
    gate=build_report(game_root=game_root,output_root=export_root,summary_path=summary_path,
                      sources=None,requirements=Requirements(unity=('AssetBundle',)))
    result=dict(status='failed',freshness=gate,inputs=[],diagnostics=[])
    if not gate['fresh']:
        result['diagnostics']=[dict(check='assetbundle_freshness',detail='required AssetBundle export is absent, partial or stale')]
        return result
    wanted={}
    for definition in definitions:
        for binding in definition.get('meshBindings',[]):
            if binding['status']!='matched_resource_and_serialized_input':
                continue
            origin=binding['origin'];key=(origin['cab'],int(origin['pathId']))
            wanted.setdefault(key,[]).append(dict(decoderCall=definition['call'],meshSlot=binding['meshSlot'],
                                                resourceHex=binding['resourceHex'],instanceId=binding['instanceId']))
    database=store_path(export_root);before=database.stat();census=Counter();rows=[]
    with UnityObjectStore.for_export(export_root) as store:
        bundles={};wanted_cabs={cab for cab,_ in wanted}
        for row in store.iter_rows('AssetBundle'):
            cab=Path(row.source_file or '').name.lower()
            if cab in wanted_cabs:bundles.setdefault(cab,[]).append(row)
        documents={}
        for cab,items in bundles.items():
            for row in items:
                raw=store.read_bytes(row.type,row.name)
                if hashlib.sha256(raw).hexdigest().lower()!=row.sha256.lower():
                    raise ValueError('AssetBundle document hash differs:'+row.ref)
                document=json.loads(raw)
                if Path(document['$animestudio']['sourceFile']).name.lower()!=cab:
                    raise ValueError('AssetBundle header CAB differs:'+row.ref)
                documents[row.name]=(document,dict(reference=row.ref,sha256=row.sha256,sourceFile=row.source_file))
        for (cab,pid),observations in sorted(wanted.items()):
            candidates=[]
            for row in bundles.get(cab,[]):
                document,evidence=documents[row.name]
                for candidate in container_candidates(document,pid):
                    candidates.append(dict(**candidate,bundleDocument=evidence))
            paths={c['path'] for c in candidates}
            status='unique_container_path' if len(paths)==1 else 'multiple_container_paths' if paths else (
                   'not_container_asset' if cab in bundles else 'bundle_document_not_exported')
            census[status]+=1
            rows.append(dict(cab=cab,pathId=str(pid),status=status,observations=observations,candidates=candidates))
    after=database.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
        raise ValueError('Unity store changed during collision input join')
    result.update(status='validated_input_container_joins',inputs=rows,census=dict(census),
                  evidenceBoundary='Direct observed CAB/PathID equals a local PPtr in a current authenticated exported AssetBundle document. All container aliases are retained. No name match, manifest suffix, preload range or equal parameters selects hit-shape geometry; a container PPtr alone does not establish the target Unity class or decode its bytes.')
    return result
