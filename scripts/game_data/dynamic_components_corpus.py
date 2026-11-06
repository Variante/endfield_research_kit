"""Current-source complete DynamicStreaming main corpus and operation gate.

Reads only selected installed/export inputs. No saved decoded rows authorize
native fields, and the operation returns nothing before all exit gates pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from scripts.common import resolve_installed_native_inputs, sha256_file_upper
from scripts.game_data.dynamic_components_binary import decode_complete_main
from scripts.game_data.dynamic_components_native import validate_native_layout
from scripts.game_data.dynamic_stream_area_corpus import MAIN_NAME_RE, load_current_inputs
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs, reader_input_changes
from scripts.source_paths import ExportLayout, configured_animestudio_cli


SCHEMA='endfield.complete-dynamic-components-operation.v1'


def need(check,condition,detail=''):
    if not condition:raise ValueError('dynamicComponents.corpus.'+check+': '+str(detail)[:1200])


def raw_path(export_root,virtual_path):
    text=virtual_path.replace('\\','/')
    need('selected-DynamicStreaming-source',text.startswith('Data/DynamicStreaming/'),virtual_path)
    parts=text.removeprefix('Data/').split('/')
    need('safe-virtual-path',all(p not in ('','.','..')and ':'not in p for p in parts),virtual_path)
    path=Path(export_root)/'raw'/Path(*parts)
    need('selected-raw-root',path.resolve().is_relative_to((Path(export_root)/'raw/DynamicStreaming').resolve()),virtual_path)
    return path


def current_main_files(export_root,*,gameassembly=None,metadata=None,cli=None,expected_input_set_sha256=None):
    """Fresh native proof, exact VFS roster, full roots, and native/source exit."""
    export_root=Path(export_root).resolve();layout=ExportLayout(export_root)
    need('explicit-native-pair', (gameassembly is None)==(metadata is None))
    if gameassembly is None:gameassembly,metadata=resolve_installed_native_inputs()
    gameassembly=Path(gameassembly).resolve();metadata=Path(metadata).resolve()
    need('selected-installed-metadata-layout',len(metadata.parents)>2 and metadata.name.lower()=='global-metadata.dat'
         and metadata.parent.name.lower()=='metadata'and metadata.parent.parent.name.lower()=='il2cpp_data',metadata)
    game_root=metadata.parents[2]
    need('same-selected-native-installation',gameassembly.parent==game_root.parent,(gameassembly,metadata))
    cli=Path(cli or configured_animestudio_cli()).resolve()
    outer_path=layout.evidence_dir/'animestudio/vfs_understanding_latest.json'
    ledger_path=layout.evidence_dir/'animestudio/vfs_understanding_files_latest.jsonl.gz'
    outer=json.loads(outer_path.read_text(encoding='utf-8'))
    for key,expected in [('primaryAssets',game_root/'Persistent'),('fallbackAssets',game_root/'StreamingAssets')]:
        need('authoritative-selected-game-root',Path(outer[key]).resolve()==expected.resolve(),(key,outer[key],expected))
    selected=str(expected_input_set_sha256 or outer['inputSetSha256']).upper()
    reader_inputs=snapshot_complete_reader_inputs()
    native=validate_native_layout(gameassembly,metadata)
    _,sources,provenance=load_current_inputs(outer_path,ledger_path,cli,selected,
        file_name_re=MAIN_NAME_RE,selection_label='fb_main_*.bytes')
    local=sorted(p.resolve()for p in (export_root/'raw/DynamicStreaming').rglob('*.bytes')if MAIN_NAME_RE.search(p.as_posix()))
    wanted=sorted(raw_path(export_root,r['path']).resolve()for r in sources)
    need('complete-distinct-source-roster',bool(sources)and len(wanted)==len(set(wanted))and wanted==local,
         dict(selected=len(wanted),local=len(local),missing=[str(p)for p in wanted if p not in set(local)][:3],extra=[str(p)for p in local if p not in set(wanted)][:3]))
    rows=[];fingerprints=[]
    for source in sources:
        path=raw_path(export_root,source['path']);data=path.read_bytes()
        try:frame=decode_complete_main(data,native=native,source=source)
        except (ValueError,IndexError,KeyError,struct.error) as error:
            raise ValueError(f'dynamicComponents.corpus.complete-source:{source["path"]}: sha256={hashlib.sha256(data).hexdigest().upper()}: {str(error)[:1400]}')from error
        need('complete-source-admission',frame['schemaStatus']=='named_exact'and frame['wholeSchemaExact']is True
             and frame['physicalEOF']is True and frame['bytesConsumed']==len(data)
             and frame['rootFieldCount']==5 and frame['gridFieldCount']==61,source['path'])
        rows.append(dict(source=source,rawPath=path,decoded=frame))
        fingerprints.append(dict(path=str(path),bytes=len(data),sha256=frame['sourceSha256']))
    expected=[(outer_path,provenance['outerReportSha256']),(ledger_path,provenance['ledgerSha256']),
              (cli,provenance['streamCliFingerprint']['currentSha256'])]
    expected.extend((Path(r['path']),r['sha256'])for r in provenance['sourceFingerprints']+provenance['gameBuildFingerprints'])
    expected.extend((Path(r['path']),r['sha256'])for r in fingerprints)
    pins=native['nativeInputs']
    expected.extend([(gameassembly,pins['gameAssemblySha256']),(metadata,pins['metadataSha256']),
                     (gameassembly.parent/'UnityPlayer.dll',pins['unityPlayerSha256'])])
    for path,digest in expected:
        actual=sha256_file_upper(path)if path.is_file()else None
        need('late-input-drift',actual==digest.upper(),dict(path=str(path),expectedSha256=digest,actualSha256=actual))
    after_readers=snapshot_complete_reader_inputs()
    need('late-reader-or-contract-drift',reader_inputs==after_readers,
         reader_input_changes(reader_inputs,after_readers)if reader_inputs!=after_readers and'files'in reader_inputs and'files'in after_readers else'complete raw-reader snapshot changed')
    after=sorted(p.resolve()for p in (export_root/'raw/DynamicStreaming').rglob('*.bytes')if MAIN_NAME_RE.search(p.as_posix()))
    need('late-source-roster-drift',after==local)
    return rows,dict(schema=SCHEMA,nativeStatus='validated',nativeInputs=pins,
        nativeSources={'GameAssembly.dll':str(gameassembly),'global-metadata.dat':str(metadata)},
        exportRoot=str(export_root),animestudio=str(cli),inputSetSha256=selected,
        sourceCounts=dict(attempted=len(sources),closed=len(rows),failed=0),authenticatedFiles=fingerprints,
        authenticatedInputs=[dict(path=str(p),sha256=d.upper())for p,d in expected],
        currentCorpus=provenance,nativePaddingProof=native['padding'],
        nativeStructTypeCount=len(native['records']),nativeNamedFieldCount=sum(len(r['fields'])for r in native['records'].values()),
        nativeSourceReaderExitBookendsPassed=True,allAttemptedOwnersClosed=True,
        allFiveRootFieldsAdmitted=True,allSixtyOneGridFieldsAdmitted=True,
        allReachedStructFieldsAdmitted=True,physicalEOFRequired=True,
        positiveDescriptorTablesAdmitted=False,runtimeActivationProved=False)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export-root',type=Path,default=ExportLayout.configured().root)
    parser.add_argument('--gameassembly',type=Path)
    parser.add_argument('--metadata',type=Path)
    parser.add_argument('--animestudio',type=Path)
    parser.add_argument('--expected-input-set-sha256',required=True)
    parser.add_argument('--output-json',type=Path)
    args=parser.parse_args(argv)
    rows,receipt=current_main_files(args.export_root,gameassembly=args.gameassembly,metadata=args.metadata,
        cli=args.animestudio,expected_input_set_sha256=args.expected_input_set_sha256)
    result=dict(status='passed',receipt=receipt,records=len(rows),
        statusCounts={'named_exact':len(rows)},files=[dict(path=r['source']['path'],bytes=r['decoded']['bytesConsumed'],
        sha256=r['decoded']['sourceSha256'],byteClosure=r['decoded']['byteClosure'])for r in rows])
    if args.output_json:
        from scripts.game_data.memorypack.corpus_gate import _guard_output_path
        need('retained-evidence-output-root',args.output_json.resolve().is_relative_to(ExportLayout(args.export_root).evidence_dir.resolve()))
        protected=[Path(r['rawPath'])for r in rows]
        protected.extend(Path(r['path'])for r in receipt['authenticatedInputs'])
        protected.extend([ExportLayout(args.export_root).evidence_dir/'animestudio/vfs_understanding_latest.json',
                          ExportLayout(args.export_root).evidence_dir/'animestudio/vfs_understanding_files_latest.jsonl.gz'])
        _guard_output_path(args.output_json,protected)
        args.output_json.parent.mkdir(parents=True,exist_ok=True)
        from scripts.game_data.corpus_common import atomic_write_text
        atomic_write_text(args.output_json,json.dumps(result,indent=2)+'\n')
    print('DynamicComponents: '+str(len(rows))+' complete named_exact roots; native/source/reader exit passed',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
