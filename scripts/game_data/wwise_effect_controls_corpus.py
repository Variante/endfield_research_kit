"""Inventory complete stored FX controls from authenticated available banks."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.wwise_bank_settings_corpus import _read_clear, _require, validate_receipt, _fingerprint
from scripts.game_data.wwise_effect_controls import read_effect_controls
from scripts.game_data.wwise_effect_controls_native import load_validated
from scripts.game_data.wwise_package import read_header
from scripts.repo_paths import REPO_ROOT


def inspect_hirc(data,version):
    """Enforce enclosing HIRC counts and lengths before inspecting FX bodies."""
    if len(data)<4:raise ValueError('HIRC count truncated')
    count=struct.unpack_from('<I',data)[0]
    if count>(len(data)-4)//9:raise ValueError('HIRC count exceeds minimum record extent')
    at=4;effects=[]
    for ordinal in range(count):
        if len(data)-at<9:raise ValueError(f'HIRC record header truncated at {at}')
        kind=data[at];size=struct.unpack_from('<I',data,at+1)[0];start=at+5
        if size<4 or size>len(data)-start:raise ValueError(f'HIRC record extent invalid at {at}: size={size} remaining={len(data)-start}')
        identity=struct.unpack_from('<I',data,start)[0];body=data[start+4:start+size]
        if kind in (16,17):
            effects.append(dict(objectId=identity,objectType=kind,ordinal=ordinal,hircOffset=at,objectBytes=size,objectSha256=hashlib.sha256(data[start:start+size]).hexdigest(),**read_effect_controls(body,bank_version=version)))
        at=start+size
    if at!=len(data):raise ValueError(f'HIRC trailing bytes: framed={at} actual={len(data)}')
    return count,effects


def inspect_bank_hirc(data, version, *, source_path, physical_path, bank_key, section_offset):
    """Keep the failed byte field together with its authenticated source span."""
    try:
        return inspect_hirc(data, version)
    except ValueError as error:
        digest = hashlib.sha256(data).hexdigest()
        failure = ValueError(f'{source_path} bank={bank_key} HIRC={section_offset} sha256={digest}: {error}')
        failure.diagnostic = dict(check='effect-controls-HIRC', sourcePath=source_path,
                                 physicalPath=str(physical_path), bankKey=bank_key, hircOffset=section_offset,
                                 hircSha256=digest, reader=getattr(error, 'diagnostic', dict(actual=str(error)[:320])))
        raise failure from error


def sweep(receipt_path,*,expected_input_set,gameassembly,metadata,ak_sound_engine):
    contract,audit=load_validated(gameassembly=gameassembly,metadata=metadata,ak_sound_engine=ak_sound_engine)
    if contract is None:raise ValueError('effect-control native gate '+audit['status']+': '+audit['detail'])
    receipt_path=Path(receipt_path);receipt_bytes=receipt_path.read_bytes();receipt=json.loads(receipt_bytes)
    outer=validate_receipt(receipt,expected_input_set)
    result=dict(schema='endfield.wwise-effect-controls-corpus.v2',status='complete',inputSetSha256=expected_input_set.upper(),nativeGate=audit,nativeInputs=contract['nativeInputs'],packageReceipt=dict(path=str(receipt_path),sha256=hashlib.sha256(receipt_bytes).hexdigest()),banks=0,hircObjects=0,effects=[],classSummary=[],roomSummary={},evidenceBoundary='Authenticated available-package roster, pinned selected native reader and exact complete common FX controls. Absence is confined to these stored definitions: runtime-added bindings, effective states/current controls, target membership and package load precedence remain unobserved.')
    counts=Counter();curves=Counter();identities=Counter();points=Counter()
    for package in receipt['packages']:
        if not package['counts']['banks']:continue
        path=Path(package['physicalPath']);offset=int(package['payloadOffset']);length=int(package['payloadBytes']);before=path.stat()
        with path.open('rb') as stream:
            stream.seek(offset);digest=hashlib.sha256();remaining=length
            while remaining:
                raw=stream.read(min(8<<20,remaining))
                if not raw:raise ValueError('short package payload: '+str(path))
                digest.update(raw);remaining-=len(raw)
            _require('package-payload-sha256',package['path'],package['payloadSha256'].upper(),digest.hexdigest().upper())
            stream.seek(offset);header=read_header(stream,length)
            _require('package-entries',package['path'],[(r['sector'],r['key'],r['language'],r['byteLength'],r['byteOffset']) for r in package['entries']],[(r.sector,str(r.key),r.language,str(r.byte_length),str(r.byte_offset)) for r in header['entries']])
            for entry_ordinal,entry in enumerate(header['entries']):
                if entry.sector!='banks':continue
                result['banks']+=1;at=0;version=None;sections=0
                while at<entry.byte_length:
                    tag,size=struct.unpack('<4sI',_read_clear(stream,entry,offset,at,8))
                    if size>entry.byte_length-at-8:raise ValueError('bank section exceeds entry: '+str(entry.key))
                    if at==0:
                        if tag!=b'BKHD' or size<8:raise ValueError('bank identity prefix missing')
                        version,identity=struct.unpack('<II',_read_clear(stream,entry,offset,at+8,8));_require('bank-key-identity',str(entry.key),entry.key,identity)
                    if tag==b'HIRC':
                        if size>64<<20:raise ValueError('HIRC exceeds bounded read limit')
                        body=_read_clear(stream,entry,offset,at+8,size)
                        total,rows=inspect_bank_hirc(body,version,source_path=package['path'],physical_path=path,bank_key=entry.key,section_offset=at)
                        result['hircObjects']+=total
                        for row in rows:
                            row.update(package=package['path'],physicalPath=str(path),bankKey=entry.key,bankLanguage=entry.language,bankEntryOrdinal=entry_ordinal,sectionOffset=at)
                            result['effects'].append(row);key=row['pluginClassId'];counts[key]+=1;curves[key]+=row['rtpcCurveCount'];points[key]+=sum(r['pointCount'] for r in row['rtpcCurves']);identities[(key,row['objectId'])]+=1
                    at+=8+size;sections+=1
                    if sections>65535:raise ValueError('bank section count exceeds bound')
        after=path.stat();_require('package-changed-during-read',path,(before.st_size,before.st_mtime_ns),(after.st_size,after.st_mtime_ns))
    _require('bank-roster-count','corpus',receipt['summary']['sectorCounts']['banks'],result['banks'])
    _require('package-receipt-changed',receipt_path,hashlib.sha256(receipt_bytes).hexdigest(),hashlib.sha256(receipt_path.read_bytes()).hexdigest())
    for key in ('sourceFingerprints','buildFingerprints'):
        for row in outer[key]:_fingerprint(row)
    for key in sorted(counts):result['classSummary'].append(dict(pluginClassId=key,definitions=counts[key],distinctObjectIds=sum(c==key for c,_ in identities),rtpcCurves=curves[key],rtpcPoints=points[key]))
    room=audit['roomClassId']
    result['roomSummary']=dict(next((r for r in result['classSummary'] if r['pluginClassId']==room),dict(pluginClassId=room,definitions=0,rtpcCurves=0,rtpcPoints=0)),definitionsWithRtpc=sum(row['pluginClassId']==room and row['rtpcCurveCount']>0 for row in result['effects']))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('package-receipt','gameassembly','metadata','ak-sound-engine','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--expected-input-set-sha256',required=True)
    args=parser.parse_args();dest=args.output.resolve()
    if REPO_ROOT/'reports' not in dest.parents:parser.error('--output must be under reports/')
    try:
        result=sweep(args.package_receipt,expected_input_set=args.expected_input_set_sha256,gameassembly=args.gameassembly,metadata=args.metadata,ak_sound_engine=args.ak_sound_engine)
    except (OSError,ValueError,KeyError,TypeError,struct.error) as error:
        result=dict(schema='endfield.wwise-effect-controls-corpus.v2',status='failed',effects=[],diagnostic=getattr(error,'diagnostic',dict(check='effectControlsCorpus',actual=str(error)[:1000])))
    atomic_write_text(dest,json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('status','banks','hircObjects','classSummary','roomSummary','diagnostic') if k in result},indent=2))
    return 0 if result['status']=='complete' else 1


if __name__=='__main__':raise SystemExit(main())
