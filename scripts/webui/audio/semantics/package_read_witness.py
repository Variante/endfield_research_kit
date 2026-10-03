"""Bounded indexed-package comparisons for admitted local read snapshots.

The supplied VFS index is a candidate set, never a complete installed corpus.
Read package headers and sampled DWORDs only; do not extract or decode media.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from scripts.game_data.wwise_package import read_header
from scripts.webui.audio.semantics.package_read_observations import checked_transform_fields

SCHEMA='endfield.audio-package-read-word-witness.v1'
BOUNDARY=('Conditional comparison against the supplied package index. A matching row geometry and sampled encoded words '
          'do not prove a live backing filename, handle lifetime, complete buffer contents, game-decoded PCM or audibility. '
          'Header and sampled-byte hashes identify only the bytes read; no whole-payload digest or complete overlay sweep is claimed.')


def match_indexed_words(rows,hooks,gate,index_path):
    if gate.get('status')!='validated':
        return {'schema':SCHEMA,'status':gate.get('status','missing'),'detail':'validated package read dependency required'}
    cohorts=defaultdict(list)
    for row in rows:
        hook=hooks[row['hook']]
        if hook['sourceKind']!='anonymousPackageReadTransform':continue
        fields,_=checked_transform_fields(row,hook,gate['observerSpec'])
        if fields is None:continue
        geometry=tuple(fields.get(name) for name in ('descriptorKeyLow','descriptorByteLength','descriptorByteOffset','descriptorBlockBytes','descriptorBlockOffset'))
        if None in geometry:continue
        relative=fields.get('transferFilePosition')
        requested,transformed,word=(fields.get(name) for name in ('transferRequestedBytes','transferTransformBytes','bufferFirstWord'))
        if relative is None or None in (requested,transformed,word):continue
        relative-=geometry[2]
        if requested<4 or transformed<4 or not 0<=relative<=geometry[1]-4:continue
        cohorts[geometry].append((row['captureId'],relative,word))
    raw_index=Path(index_path).read_bytes()
    index=json.loads(raw_index)
    matches,skipped=[],[]
    for candidate in index['files']:
        name=candidate['fileName']
        if not name.lower().endswith('.pck'):continue
        path=candidate.get('chunkAbsolutePath')
        if not path or candidate.get('encrypted'):
            skipped.append({'fileName':name,'reason':'absent physical chunk or VFS-encrypted payload'});continue
        offset,length=candidate['offset'],candidate['length']
        try:
            with Path(path).open('rb') as stream:
                before=Path(path).stat()
                if type(offset) is not int or type(length) is not int or offset<0 or length<0 or offset+length>before.st_size:
                    raise ValueError('indexed payload outside physical chunk')
                stream.seek(offset)
                header=read_header(stream,length)
                stream.seek(offset)
                header_digest=hashlib.sha256(stream.read(header['headerBytes'])).hexdigest()
                for entry in header['entries']:
                    geometry=(entry.key&0xffffffff,entry.byte_length,entry.byte_offset,entry.block_bytes,entry.block_offset)
                    samples=cohorts.get(geometry)
                    if not samples:continue
                    comparisons=[]
                    for capture_id,relative,observed in samples:
                        stream.seek(offset+entry.byte_offset+relative)
                        word=stream.read(4)
                        if len(word)!=4:raise ValueError('truncated indexed buffer word')
                        comparisons.append({'captureId':capture_id,'relativeOffset':str(relative),
                            'observedWord':f'{observed:08x}','indexedWord':f'{int.from_bytes(word,"little"):08x}',
                            'comparison':'matched' if observed==int.from_bytes(word,'little') else 'different'})
                    matches.append({'fileName':name,'physicalPath':path,'payloadOffset':str(offset),'payloadBytes':str(length),
                        'headerSha256':header_digest,'sector':entry.sector,'key':str(entry.key),'keyLow':entry.key&0xffffffff,
                        'byteLength':str(entry.byte_length),'byteOffset':str(entry.byte_offset),'blockBytes':entry.block_bytes,
                        'language':entry.language,'sampleCount':len(comparisons),
                        'distinctSampledByteCount':len({byte for _,relative,_ in samples for byte in range(relative,relative+4)}),
                        'matchedWordCount':sum(c['comparison']=='matched' for c in comparisons),
                        'comparisons':comparisons})
                after=Path(path).stat()
                if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
                    raise ValueError('physical package changed during comparison')
        except (OSError,ValueError) as error:
            # A malformed candidate cannot leave partially admitted matches.
            matches=[m for m in matches if m['fileName']!=name or m['physicalPath']!=path]
            skipped.append({'fileName':name,'reason':str(error)[:240]})
    return {'schema':SCHEMA,'status':'conditionalIndexedComparison','indexSha256':hashlib.sha256(raw_index).hexdigest(),
        'indexedFileCount':len(index['files']),'descriptorGeometryCount':len(cohorts),
        'matches':matches,'skipped':skipped,'evidenceBoundary':BOUNDARY}
