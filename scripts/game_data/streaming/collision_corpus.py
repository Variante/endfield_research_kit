"""Project stored Streaming collisions from the current authenticated root gate.

Run after streaming.corpus with the VFS audit's input-set SHA256. Output is a
receipt plus a gzip JSONL file containing one source file per row. Neither is
runtime evidence or a published WebUI collision preview.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import os
import tempfile
from pathlib import Path

from scripts.common import sha256_file_upper
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.streaming import marker17_corpus as gate
from scripts.game_data.streaming import framing as fmt
from scripts.game_data.streaming.collision import project
from scripts.game_data.streaming.collision_native import load, CONTRACT
from scripts.game_data.ecs_collision_native import CONTRACT as ECS_CONTRACT, OWNERSHIP_CONTRACT
from scripts.repo_paths import REPO_ROOT

SCHEMA='endfield.streaming-collision-corpus.v2'


def sweep(*, report_path: Path, outer_path: Path, ledger_path: Path, expected_input_set: str,
          game_root: Path, rows_output: Path, manifest: Path | None = None):
    expected=expected_input_set.upper(); failures=[]; summary=collections.Counter()
    result=dict(schema=SCHEMA,status='failed',publicationEligible=False,inputSetSha256=expected,
                summary={},diagnostics=failures,rows=None)
    temporary=None
    try:
        if len(expected) != 64 or any(c not in '0123456789ABCDEF' for c in expected):
            raise ValueError('input set must be exactly 64 hexadecimal characters')
        paths=gate._source_paths(REPO_ROOT)
        paths.update(collisionReaderSha256=Path(project.__code__.co_filename),
                     collisionGateSha256=Path(__file__),collisionNativeValidatorSha256=Path(load.__code__.co_filename),
                     collisionContractSha256=CONTRACT,ecsContractSha256=ECS_CONTRACT,ecsOwnershipContractSha256=OWNERSHIP_CONTRACT,
                     ecsReaderSha256=REPO_ROOT/'scripts/game_data/ecs_collision.py',
                     ecsValidatorSha256=REPO_ROOT/'scripts/game_data/ecs_collision_native.py')
        if manifest is not None:
            paths.update(collisionAssetReaderSha256=REPO_ROOT/'scripts/game_data/streaming/collision_assets.py',
                         manifestProjectionReaderSha256=REPO_ROOT/'scripts/game_data/dynamic_model_native.py',
                         manifestNativeValidatorSha256=REPO_ROOT/'scripts/game_data/bundle_manifest_native.py',
                         manifestNativeContractSha256=REPO_ROOT/'scripts/game_data/contracts/bundle_manifest_native.json',
                         manifestPlaintextSha256=manifest)
        sources=gate._snapshot_sources(paths,failures,'source-start')
        start=dict(rootReport=sha256_file_upper(report_path),outerSummary=sha256_file_upper(outer_path),ledger=sha256_file_upper(ledger_path))
        root=json.loads(report_path.read_bytes());outer=json.loads(outer_path.read_bytes())
        header,ledger=gate._read_ledger(ledger_path,failures)
        native,ecs,native_gate=load(game_root=game_root)
        result['nativeGate']=native_gate
        if native is None:raise ValueError('native source/decoder gate failed')
        install=game_root.resolve()
        if install.name == 'Endfield_Data':install=install.parent
        native_paths=dict(gameAssemblySha256=install/'GameAssembly.dll',
                          metadataSha256=install/'Endfield_Data/il2cpp_data/Metadata/global-metadata.dat',
                          unityPlayerSha256=install/'UnityPlayer.dll')
        native_hashes={name:sha256_file_upper(path).lower() for name,path in native_paths.items()}
        if native_hashes != native['nativeInputs']:raise ValueError('selected native inputs changed before projection')
        selected=gate._validate_native_profile(native_gate['markerGate'],failures,sources['marker17NativeContractSha256'])
        files,counts=gate._validate_root_report(root,expected,sources,selected,failures)
        result['selection']=dict(directoryFiles=len(files),directoryReferences=counts['references'],supportedReferences=counts['supported'],excludedReferences=counts['unsupported'])
        gate._validate_outer(outer,header,expected,start['ledger'],root,failures)
        joined=gate._join_ledger(files,ledger,failures)
        fingerprints=gate._snapshot_outer_fingerprints(outer,failures,'fingerprint-start')
        if failures:raise ValueError('source authentication failed; see bounded diagnostics')
        candidates=None
        if manifest is not None:
            from scripts.game_data.streaming.collision_assets import load_candidates
            candidates,asset_gate=load_candidates(manifest=manifest,ledger=ledger_path,expected_input_set=expected,game_root=game_root)
            result['manifestCandidateGate']=asset_gate
        rows_output.parent.mkdir(parents=True,exist_ok=True)
        fd,name=tempfile.mkstemp(prefix='.collision.',suffix='.jsonl.gz',dir=rows_output.parent);os.close(fd);temporary=Path(name)
        groups=collections.defaultdict(list)
        for file in files:groups[file['physicalChunkPath']].append(file)
        kinds=collections.Counter();layers=collections.Counter();options=collections.Counter();flags=collections.Counter();selectors=collections.Counter();resource_valid=collections.Counter()
        with gzip.open(temporary,'wt',encoding='utf-8',newline='\n') as output:
            for chunk,group in sorted(groups.items()):
                chunk_path=Path(chunk);stat_start=chunk_path.stat()
                with chunk_path.open('rb') as stream:
                    for file in sorted(group,key=lambda f:f['offset']):
                        source=file['virtualPath'];staged=[]
                        try:
                            offset,length=file['offset'],file['length']
                            if type(offset) is not int or type(length) is not int or offset < 0 or length < 0 or offset+length > stat_start.st_size:raise ValueError('physical range outside chunk')
                            stream.seek(offset);packed=stream.read(length)
                            if len(packed) != length:raise ValueError('short physical read')
                            sha=gate.sha256_bytes(packed);md5=hashlib.md5(packed,usedforsecurity=False).hexdigest().upper()
                            if sha != file['packedSha256'].upper() or md5 != joined[source]['recomputedFileDataMd5'].upper():raise ValueError(f'packed hash mismatch: SHA256={sha}, MD5={md5}')
                            clear=fmt._decode_compressed(packed)
                            root_table=fmt._table_layout(clear,fmt._u32(clear,0))
                            ids,n,_=fmt._bounded_vector(clear,root_table,3,4,source)
                            for row in file['rows']:
                                classification=gate._classify(file,row,selected,failures)
                                gate._validate_row(clear,file,row,classification)
                                summary['referencesAuthenticated']+=1
                                if classification != 'supported':
                                    summary['referencesExcluded']+=1;continue
                                item=project(clear,row,source=source,source_contract=native,ecs_contract=ecs,native_validated=True)
                                if candidates is not None:
                                    from scripts.game_data.streaming.collision_assets import join_candidates
                                    join_candidates(item['meshInputs']+item['resourceInputs'],candidates)
                                ordinal=item['outerRowIndex']
                                if not 0 <= ordinal < n:raise ValueError('root row ID ordinal outside vector')
                                item['serializedRootRowId']=fmt._u32(clear,ids+4+ordinal*4)
                                item['serializedRootRowIdBoundary']='stored row identifier; not ECS.Entity globalIndex or PxActor identity'
                                staged.append(item)
                            output.write(json.dumps(dict(virtualPath=source,physicalChunkPath=chunk_path.as_posix(),
                                physicalChunkSource=file['physicalChunkSource'],metadataProvenance=file['metadataProvenance'],
                                overlayState=file['overlayState'],offset=offset,length=length,packedSha256=sha,ledgerMd5=md5,
                                decodedSha256=gate.sha256_bytes(clear),rows=staged),ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n')
                            summary['filesAuthenticated']+=1
                            for item in staged:
                                summary['definitions']+=1;selectors[str(item['selector'])]+=1;p=item['projection'];layers[str(p['layer'])]+=1
                                for record in p['records']:
                                    kinds[record['kind']]+=1;options[str(record['gameplayOptionsWord'])]+=1;flags[str(record['flagWord'])]+=1
                                    summary['records']+=1
                                    summary['attachmentGateNotEncoded' if record['attachmentGate'] is None else 'attachmentGateTrue' if record['attachmentGate'] else 'attachmentGateFalse']+=1
                                summary['meshSlots']+=len(item['meshInputs'])
                                summary['heightmapResources']+=len(item['resourceInputs'])
                                for mesh in item['meshInputs']+item['resourceInputs']:
                                    resource_valid[str(mesh['nativeValidityPredicate'])]+=1
                                    if candidates is not None:summary[mesh['manifestCandidateStatus']]+=1
                        except (OSError,ValueError,KeyError,TypeError) as exc:
                            summary['filesFailed']+=1
                            if len(failures)<64:failures.append(dict(source=source,check='stored_collision_projection',offset=file.get('offset'),expected='authenticated key/body/resource spans',actual=str(exc)[:1200]))
                        if (summary['filesAuthenticated']+summary['filesFailed'])%1000 == 0:print(f'Streaming collision progress: {dict(summary)}',flush=True)
                stat_end=chunk_path.stat()
                if (stat_start.st_size,stat_start.st_mtime_ns) != (stat_end.st_size,stat_end.st_mtime_ns):raise ValueError(f'physical chunk changed: {chunk}')
        if summary['filesAuthenticated']+summary['filesFailed'] != len(files) or summary['referencesAuthenticated'] != counts['references']:
            failures.append(dict(check='directory_reconciliation',expected=dict(files=len(files),references=counts['references']),actual=dict(summary)))
        end=dict(rootReport=sha256_file_upper(report_path),outerSummary=sha256_file_upper(outer_path),ledger=sha256_file_upper(ledger_path))
        sources_end=gate._snapshot_sources(paths,failures,'source-end')
        fingerprints_end=gate._snapshot_outer_fingerprints(outer,failures,'fingerprint-end')
        native_after={name:sha256_file_upper(path).lower() for name,path in native_paths.items()}
        if start != end or sources != sources_end or fingerprints != fingerprints_end or native_hashes != native_after:raise ValueError('source inputs/code changed during projection')
        result.update(provenance=dict(rootReport=str(report_path.resolve()),outerSummary=str(outer_path.resolve()),ledger=str(ledger_path.resolve()),sourceHashes=sources,authenticatedInputs=start,outerFingerprints=fingerprints,nativeInputHashes=native_hashes),
                      census=dict(kinds=dict(kinds),selectors=dict(selectors),layers=dict(layers),optionWords=dict(options),flagWords=dict(flags),resourceValidity=dict(resource_valid)),
                      evidenceBoundary=native['evidenceBoundary'])
        if not failures:
            digest=sha256_file_upper(temporary);os.replace(temporary,rows_output);temporary=None
            result.update(status='validated',publicationEligible=True,rows=dict(path=str(rows_output.resolve()),sha256=digest,files=summary['filesAuthenticated']))
    except (OSError,ValueError,KeyError,TypeError) as exc:
        failures.append(dict(check='streaming_collision_corpus',source=str(report_path),expected='current authenticated native/source inputs',actual=str(exc)[:1200]))
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
    result['summary']=dict(summary)
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report',type=Path,default=REPO_ROOT/'reports/animestudio/streaming_root_subgraphs_latest.json')
    p.add_argument('--outer-summary',type=Path,default=REPO_ROOT/'reports/animestudio/vfs_understanding_latest.json')
    p.add_argument('--outer-ledger',type=Path,default=REPO_ROOT/'reports/animestudio/vfs_understanding_files_latest.jsonl.gz')
    p.add_argument('--input-set-sha256',required=True)
    p.add_argument('--game-root',type=Path,required=True)
    p.add_argument('--manifest',type=Path,help='optional existing plaintext manifest; authenticate to current VFS and native layout before joining full64 candidates')
    p.add_argument('--output',type=Path,default=REPO_ROOT/'reports/animestudio/streaming_collision_latest.json')
    args=p.parse_args(argv);output=args.output.resolve();rows=output.with_suffix('.jsonl.gz')
    if not any(output.is_relative_to(REPO_ROOT/name) for name in ('reports','tmp','scratch')):p.error('generated output must be under reports/, tmp/ or scratch/')
    report=sweep(report_path=args.report,outer_path=args.outer_summary,ledger_path=args.outer_ledger,
                 expected_input_set=args.input_set_sha256,game_root=args.game_root,rows_output=rows,manifest=args.manifest)
    atomic_write_text(output,json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],summary=report['summary'],diagnostics=report['diagnostics'][:3],output=str(output))))
    return 0 if report['status']=='validated' else 1


if __name__=='__main__':raise SystemExit(main())
