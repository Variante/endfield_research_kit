"""Join typed DataGroup children to template-checked authored RootComp owners.

Run with ``python -m scripts.game_data.dynamic_group_owner_join``. This consumes
current bytes, not report samples. An authored parent chain does not establish
that the corresponding entity was registered, loaded or activated in play.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __name__ == '__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_group_owner_join')

from scripts.game_data import dynamic_group_components_native as groups
from scripts.game_data.dynamic_root_comp_native import decode_authenticated_root_components, load_current_template_asset, DEFAULT_SUMMARY
from scripts.game_data.unity_store import store_path
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots
from scripts.game_data.corpus_common import atomic_write_text
from scripts.repo_paths import REPO_ROOT


def join_authored_owners(group_rows: list[dict[str, Any]], root_rows: list[dict[str, Any]],
                         *, templates: dict[int, tuple[int, ...]], enum: dict[int, str], source: str) -> dict[str, Any]:
    """Join only exact file-local grid/component ordinals from admitted decoders.

    ``group_rows`` and ``root_rows`` must be decoded from the same authenticated
    source bytes with one selected native context. All candidates are retained.
    No source, vector-order, field-name or numeric-ID proximity is a join key.
    """
    roots = defaultdict(list)
    for root in root_rows:
        key = (root['gridOrdinal'], root['gridUniqueId'], root['component'], root['componentOrdinal'])
        owner = root['authoredOwner']
        entity_type = owner['entityType']
        signature = templates.get(entity_type)
        if signature is None:
            raise groups.DynamicGroupComponentsError(f'{source}:missing checked template entityType={entity_type}')
        roots[key].append({'directoryOrdinal': root['directoryOrdinal'], 'fieldIndex': root['fieldIndex'],
            'authoredOwner': owner, 'templateSignature': list(signature),
            'templateComponentNames': [enum[value] for value in signature]})
    children, parents, seen = {}, [], set()
    for parent in group_rows:
        key = (parent['gridOrdinal'], parent['gridUniqueId'], parent['component'], parent['componentOrdinal'])
        if key in seen:
            raise groups.DynamicGroupComponentsError(f'{source}:duplicate containing component key={key}')
        seen.add(key)
        owner_rows = roots.get(key, [])
        for field, link in parent['groups'].items():
            parent_row = {'source': source, 'gridOrdinal': parent['gridOrdinal'], 'gridUniqueId': parent['gridUniqueId'],
                'component': parent['component'], 'componentOrdinal': parent['componentOrdinal'], 'groupField': field,
                'sourceByteSpan': parent['sourceByteSpan'], 'groupStatus': link['status'],
                'authoredRootCandidates': owner_rows, 'target': link.get('target'), 'targetSpan': link.get('span'),
                'ownershipStatus': 'authored_candidates' if owner_rows else 'no_direct_root_reference'}
            parents.append(parent_row)
            if link['status'] != 'resolved':
                continue
            first, end = link['span']
            start_byte, end_byte = link['sourceByteSpan']
            if end <= first or start_byte < 0 or end_byte <= start_byte or (end_byte-start_byte) % (end-first):
                raise groups.DynamicGroupComponentsError(f'{source}:invalid admitted child span={link}')
            width = (end_byte-start_byte)//(end-first)
            for ordinal in range(first, end):
                child_key = (parent['gridOrdinal'], parent['gridUniqueId'], link['target'], ordinal)
                byte_span = [start_byte+(ordinal-first)*width, start_byte+(ordinal-first+1)*width]
                child = children.setdefault(child_key, {'source': source, 'gridOrdinal': parent['gridOrdinal'],
                    'gridUniqueId': parent['gridUniqueId'], 'component': link['target'], 'componentOrdinal': ordinal,
                    'sourceByteSpan': byte_span, 'authoredParentChains': []})
                if child['sourceByteSpan'] != byte_span:
                    raise groups.DynamicGroupComponentsError(f'{source}:conflicting admitted child byte spans key={child_key}')
                child['authoredParentChains'].append(parent_row)
    for child in children.values():
        identities = {(p['gridOrdinal'], row['authoredOwner']['rootCompOrdinal'])
            for p in child['authoredParentChains'] for row in p['authoredRootCandidates']}
        child['authoredRootCandidateCount'] = len(identities)
        child['ownershipStatus'] = ('no_direct_root_reference' if not identities else
            'unique_authored_root' if len(identities)==1 else 'multiple_authored_roots')
        child['evidenceBoundary'] = 'structuralOnly'
    return {'parents': parents, 'children': list(children.values())}


def _proof_sources():
    snapshots = groups._proof_sources() + _parser_source_snapshots(Path(__file__))
    return sorted({row['path']: row for row in snapshots}.values(), key=lambda row:row['path'])


def _require_raw_inputs_unchanged(snapshots: list[dict[str, Any]]) -> None:
    """Re-resolve the original dump paths as well as authenticating their bytes."""
    for before in snapshots:
        actual = _fingerprint(Path(before['path']))
        expected = {'path': before['resolvedPath'], 'length': before['length'], 'sha256': before['sha256']}
        if actual != expected:
            raise groups.DynamicGroupComponentsError(
                f"raw-source-drift:source={before['path']} expectedPath={expected['path']} actualPath={actual['path']} "
                f"expectedLength={expected['length']} actualLength={actual['length']} "
                f"expectedSha256={expected['sha256']} actualSha256={actual['sha256']}")


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('gameassembly','metadata','game-root','export-root','input-root'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--expected-input-set-sha256',required=True)
    parser.add_argument('--outer-report',type=Path,default=groups.DEFAULT_OUTER)
    parser.add_argument('--ledger',type=Path,default=groups.DEFAULT_LEDGER)
    parser.add_argument('--cli',type=Path,default=groups.DEFAULT_CLI)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_group_owner_join_latest.json')
    args=parser.parse_args(argv)
    try:
        template_inputs = [DEFAULT_SUMMARY, args.export_root/'meta/extraction/provenance.json',
            args.export_root/'meta/StreamingAssets/asset_map/endfield_streamingassets_assets.json',
            args.export_root/'meta/StreamingAssets/export_manifest/StreamingAssets_animestudio_json_by_type_MonoBehaviour.jsonl']
        protected = [args.gameassembly,args.metadata,args.gameassembly.parent/'UnityPlayer.dll',args.game_root,args.export_root,
            args.input_root,args.outer_report,args.ledger,args.cli,groups.CONTRACTS_DIR,store_path(args.export_root),*template_inputs]
        groups._guard_publication(args.output_json,protected)
        proof_sources = _proof_sources()
        proof_inputs = [_fingerprint(path) for path in [args.gameassembly,args.metadata,args.gameassembly.parent/'UnityPlayer.dll',
            args.outer_report,args.ledger,args.cli,*template_inputs]]
        protected.extend(Path(row['path']) for row in proof_sources)
        groups._guard_publication(args.output_json,protected)
        records,inline,layout,enum,receipt,context = groups.validate_native_layout(args.gameassembly,args.metadata)
        for key,snapshot in zip(('gameAssemblySha256','metadataSha256','unityPlayerSha256'),proof_inputs[:3]):
            if receipt[key].upper()!=snapshot['sha256'].upper():
                raise groups.DynamicGroupComponentsError(f'native-input-drift:{snapshot["path"]}')
        template_args = dict(game_root=args.game_root,export_root=args.export_root,entity_enum=context['entityEnum'],data_enum=enum)
        templates,template_receipt = load_current_template_asset(context['root']['templateLookup'],**template_args)
        outer,files,provenance = groups.load_current_inputs(args.outer_report,args.ledger,args.cli,args.expected_input_set_sha256,
            file_name_re=groups.MAIN_NAME_RE,selection_label='fb_main_*.bytes')
        protected.extend(groups._checked_dump_path(args.input_root,row['path']) for row in files)
        groups._guard_publication(args.output_json,protected)
        parents,children,sources,raw_proofs = [],[],[],[]
        for source in files:
            dump_path=groups._checked_dump_path(args.input_root,source['path'])
            resolved_before=dump_path.resolve().as_posix()
            data=dump_path.read_bytes()
            raw_proofs.append({'path':dump_path.absolute().as_posix(),'resolvedPath':resolved_before,
                'length':len(data),'sha256':hashlib.sha256(data).hexdigest().upper()})
            group_rows=groups.decode_authenticated_main(data,records=records,inline=inline,main=layout,enum=enum,source=source)
            root_rows=decode_authenticated_root_components(data,layout=context['root'],index_layout=context['index'],
                main_layout=layout,enum_by_id=enum,entity_enum=context['entityEnum'],templates=templates,source=source)
            joined=join_authored_owners(group_rows,root_rows,templates=templates,enum=enum,source=source['path'])
            parents.extend(joined['parents']);children.extend(joined['children'])
            sources.append({'path':source['path'],'length':len(data),'fileDataMd5':source['fileDataMd5'],
                'sha256':hashlib.sha256(data).hexdigest().upper(),'groupParents':len(group_rows),
                'directRootReferences':len(root_rows),'indirectChildren':len(joined['children'])})
        templates_after,template_after = load_current_template_asset(context['root']['templateLookup'],**template_args)
        if templates_after!=templates or template_after!=template_receipt:
            raise groups.DynamicGroupComponentsError('template-source-drift:selected object/provenance changed')
        counts=Counter((row['component'],row['ownershipStatus']) for row in children)
        report={'format':'endfield.dynamic-group-owner-join.v2','status':'validated','nativeInputs':receipt,
            'inputSetSha256':outer['inputSetSha256'],'outer':provenance,'template':template_receipt,
            'proofSources':proof_sources,'proofInputs':proof_inputs,'rawProofInputs':raw_proofs,
            'files':sources,'parents':parents,'children':children,
            'childOwnershipCounts':[{'component':component,'status':status,'count':count} for (component,status),count in sorted(counts.items())],
            'evidenceBoundary':'StructuralOnly exact same-source RootComp directory -> template-matched containing component -> typed DataGroup child span. All candidate chains retained; no live entity registration, evaluated condition or activation claim.'}
        encoded=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        _require_raw_inputs_unchanged(raw_proofs)
        groups._require_unchanged(proof_sources+proof_inputs)
        groups._guard_publication(args.output_json,protected)
        atomic_write_text(args.output_json,encoded)
    except (OSError,ValueError,KeyError,IndexError,RuntimeError) as exc:
        print(f'dynamic-group-owner-join:{str(exc)[:1400]}',file=sys.stderr)
        return 1
    print(f'DynamicStreaming owner join passed: files={len(sources)} parents={len(parents)} children={len(children)}')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
