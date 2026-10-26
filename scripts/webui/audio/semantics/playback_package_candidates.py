"""Compare captured source words with current headers from a supplied corpus."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.game_data.wwise_package import read_header
from scripts.game_data.wwise_external_package_native import external_path_key
from scripts.game_data.wwise_decoder_provider_native import load_validated_decoder_provider_contract
from scripts.repo_paths import REPO_ROOT
from scripts.webui.audio.semantics.playback_capture import fingerprint


def compare(review_path, corpus_path, *, package_contract=None, package_gate=None):
    review=json.loads(Path(review_path).read_bytes());corpus=json.loads(Path(corpus_path).read_bytes())
    if review.get('schema')!='endfield.audio-playback-capture-review.v8' or corpus.get('schema')!='endfield.wwise-package-corpus.v1' or corpus.get('status')!='complete':
        raise ValueError('reviewed playback observations and complete supplied package corpus required')
    # The raw capture hashes belong to the phase audit. This projection consumes
    # that report and rechecks the candidate headers it reads, without repeating
    # the giant raw scan or claiming a fresh whole-corpus census.
    sources={choice['sourceLookup'] for cohort in review['selectorSerialCandidates']
             for choice in cohort['sourceChoices'] if choice['sourceLookup'] is not None}
    external_paths={}
    if package_contract is not None and package_gate and package_gate.get('status')=='validated':
        saved=Path(review['session'])/'private/source-owner-build-manifest.json'
        pin=next((p for p in review['inputs'] if Path(p['path']).resolve()==saved.resolve()),None)
        receipt=fingerprint(saved)
        if not pin or receipt['sha256']!=pin['sha256'] or receipt['bytes']!=pin['bytes']:
            raise ValueError('captured native recipe differs from the phase review')
        files=json.loads(saved.read_bytes())['files']
        captured=dict(gameAssemblySha256=files['gameAssembly']['sha256'],globalMetadataSha256=files['metadata']['sha256'],akSoundEngineSha256=files['akSoundEngine']['sha256'],akSoundEngineFileSize=files['akSoundEngine']['bytes'])
        if package_contract['nativeInputs']!=captured:
            package_gate=dict(status='mismatched',detail='external key contract differs from captured native inputs')
            package_contract=None
    if package_contract is not None and package_gate and package_gate.get('status')=='validated':
        for row in (review.get('nativeLineage') or {}).get('localTransport',[]):
            path=row['selector'].get('descriptorPath')
            if row['selection']=='singleDescriptorWideSetterInput' and path:
                external_paths.setdefault(external_path_key(path,package_contract),set()).add(path)
    matches=[];diagnostics=[]
    for package in corpus['packages']:
        recorded=[entry for entry in package['entries'] if
                  (entry['sector']=='sounds' and (int(entry['key'])&0xffffffff) in sources) or
                  (entry['sector']=='externals' and int(entry['key']) in external_paths)]
        if not recorded: continue
        path=Path(package['physicalPath']);offset=int(package['payloadOffset']);length=int(package['payloadBytes'])
        try:
            before=path.stat()
            if offset<0 or length<24 or offset+length>before.st_size: raise ValueError('package extent outside chunk')
            with path.open('rb') as stream:
                stream.seek(offset);header=read_header(stream,length)
                stream.seek(offset);digest=hashlib.sha256(stream.read(header['headerBytes'])).hexdigest()
            if digest!=package['headerSha256'].lower(): raise ValueError('current header differs from supplied corpus')
            current={i:e for i,e in enumerate(header['entries'])}
            labels={row['id']:row['label'] for row in header['languageTable']['rows']}
            selected=[]
            for entry in recorded:
                e=current[entry['ordinal']]
                if (e.sector,str(e.key),e.language,str(e.byte_length),str(e.byte_offset),str(e.block_offset),e.block_bytes)!=(entry['sector'],entry['key'],entry['language'],entry['byteLength'],entry['byteOffset'],entry['blockOffset'],entry['blockBytes']):
                    raise ValueError('recorded typed entry differs from current header')
                item=dict(sector=e.sector,key=str(e.key),language=e.language,languageLabel=labels.get(e.language),
                    ordinal=entry['ordinal'],byteOffset=str(e.byte_offset),byteLength=str(e.byte_length))
                if e.sector=='sounds':item.update(matchKind='numericSourceWord',sourceWord=e.key&0xffffffff)
                else:item.update(matchKind='externalFullPathHash',externalPaths=sorted(external_paths[e.key]))
                selected.append(item)
            after=path.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns): raise ValueError('chunk changed during header read')
            matches.append(dict(package=package['path'],physicalPath=str(path.resolve()),payloadOffset=str(offset),
                headerBytes=header['headerBytes'],headerSha256=digest,entries=selected))
        except (OSError,ValueError,KeyError) as error:
            diagnostics.append(dict(package=package['path'],check=str(error)))
    return dict(schema='endfield.playback-package-candidates.v2',status='conditionalSuppliedCorpusCandidates',
        inputs=[fingerprint(Path(review_path)),fingerprint(Path(corpus_path))],matches=matches,diagnostics=diagnostics,
        externalKeyGate=package_gate or dict(status='notRequested'),
        evidenceBoundary=dict(direct='Positive current typed-header entries and exact header digest comparisons against the supplied corpus.',
            conditional='Numeric source words match sound-sector key low words. With selected native hashing admitted, complete observed descriptor paths match full external-sector keys. All matching supplied occurrences remain candidates; headers expose byte extents but do not establish the live selected occurrence.',
            unresolved='Corpus omissions, embedded-bank media, live package/language precedence, stream handle and allocation lifetime, selected encoded payload and its correspondence to captured PCM.'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review',type=Path,default=REPO_ROOT/'reports/audio/playback_capture_current.json')
    parser.add_argument('--corpus',type=Path,default=REPO_ROOT/'reports/audio/package_corpus_current.json')
    parser.add_argument('--game-root',type=Path,help='explicit selected client; required to admit external pathname hashing')
    parser.add_argument('--output',type=Path,default=REPO_ROOT/'reports/audio/playback_package_candidates_current.json');args=parser.parse_args()
    try:
        if REPO_ROOT/'reports' not in args.output.resolve().parents: raise ValueError('output must live under reports/')
        package=None;gate=None
        if args.game_root:
            root=args.game_root.resolve()
            _,audit=load_validated_decoder_provider_contract(gameassembly=root/'GameAssembly.dll',metadata=root/'Endfield_Data/il2cpp_data/Metadata/global-metadata.dat',ak_sound_engine=root/'Endfield_Data/Plugins/x86_64/AkSoundEngine.dll',include_package=True)
            gate=audit.get('externalPackageGate',dict(status=audit['status'],detail=audit.get('detail','external package gate unavailable')))
            if audit['status']=='validated' and gate['status']=='validated':package=gate['contract']
        result=compare(args.review,args.corpus,package_contract=package,package_gate=gate)
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    except (OSError,ValueError,KeyError,TypeError) as error:
        print('Playback package candidates withheld: '+str(error));return 2
    print(f"Playback package candidates: {len(result['matches'])} current headers, {len(result['diagnostics'])} diagnostics -> {args.output}");return 0


if __name__=='__main__':raise SystemExit(main())
