"""Compare saved compressed GPU mip chains to immutable stored texture payloads.

The source preview receipt is a frozen publication input, not a current-build
admission. Byte equality can establish content; it cannot identify a Material.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
from scripts.common import write_json
from scripts.game_data.unity_texture import read_texture
from scripts.repo_paths import REPO_ROOT

DXGI_BLOCKS={71:10,72:10,77:12,78:12,80:26,83:27,98:25,99:25}


def source_tails(receipt):
    if receipt.get('schema')!='endfield.stored-texture-previews.v1' or receipt.get('status')!='complete':raise ValueError('stored texture preview receipt unavailable')
    result=defaultdict(list)
    for row in receipt['textures']:
        source=row['source'];raw_path=Path(source['rawPath']);json_path=Path(source['jsonPath'])
        if hashlib.sha256(raw_path.read_bytes()).hexdigest()!=source['rawSha256']:raise ValueError('frozen Texture2D body changed')
        raw=json_path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=source['jsonSha256']:raise ValueError('frozen Texture2D decoded body changed')
        resource=source.get('resource');stream=None
        if resource and resource['size']:
            if resource['status']!='exact_owner_archive_span':raise ValueError('frozen Texture2D archive span unavailable')
            stream=(raw_path.parent/resource['file']).read_bytes()
            if hashlib.sha256(stream).hexdigest()!=resource['sha256']:raise ValueError('frozen Texture2D archive bytes changed')
        texture=read_texture(json.loads(raw),stream);payload=texture['payload']
        if hashlib.sha256(payload).hexdigest()!=row['payloadSha256']:raise ValueError('frozen texture payload receipt differs')
        for mip in texture['mips']:
            tail=payload[mip['offset']:];h=hashlib.sha256(tail).hexdigest()
            result[(texture['formatId'],mip['width'],mip['height'],texture['mipCount']-mip['mip'],len(tail),h)].append(
                dict(identity=source['identity'],name=source['name'],rawSha256=source['rawSha256'],sourceFirstMip=mip['mip'],storedColorSpace=texture['storedColorSpace']))
    return result


def texture_payload(frame_dir,metadata,record):
    if record['resourceKind']!=3 or record['stage']!=4 or record['captureKind']!=3:return None
    if record['format'] not in DXGI_BLOCKS or record['viewFormat'] not in DXGI_BLOCKS or DXGI_BLOCKS[record['format']]!=DXGI_BLOCKS[record['viewFormat']]:return None
    if not record['completed'] or not record['attempted'] or record['failure'] or record['hresult']:return None
    if (record['depthOrArray'],record['sampleCount'],record['arrayCount'],record['firstArraySlice'],record['firstMip'])!=(1,1,1,0,0):return None
    if record['blobLayoutOrder']!='array-mip-depth-row' or record['subresourceCount']!=record['mipLevels'] or record['mipCount']!=record['mipLevels']:return None
    width,height,mips=record['width'],record['height'],record['mipLevels']
    if type(width)!=int or type(height)!=int or min(width,height)<=0 or width*height>16777216 or not 1<=mips<=max(width,height).bit_length():raise ValueError('captured texture dimensions outside bounds')
    block=8 if DXGI_BLOCKS[record['format']] in (10,26) else 16
    expected=sum(((max(1,width>>i)+3)//4)*((max(1,height>>i)+3)//4)*block for i in range(mips))
    if record['blobBytes']!=expected or record['requestedBytes']!=expected:raise ValueError('captured texture mip byte census differs')
    name=metadata['resourcesFile']
    if name!='resources.bin':raise ValueError('captured resource blob filename differs')
    path=frame_dir/name;offset=record['blobOffset']
    if type(offset)!=int or offset<0 or offset+expected>path.stat().st_size:raise ValueError('captured texture range exceeds blob')
    with path.open('rb') as f:f.seek(offset);payload=f.read(expected)
    if len(payload)!=expected:raise ValueError('captured texture blob truncated')
    return DXGI_BLOCKS[record['format']],width,height,mips,len(payload),hashlib.sha256(payload).hexdigest()


def same_draw_payload(record,draw,metadata):
    if not metadata.get('resourcePayloadDrawLocal') or record.get('deferredCopyPhase')!=1:return False
    if record.get('deferredUnifiedCallOrdinal')!=draw.get('unifiedCallOrdinal') or record.get('deferredPresentEpoch')!=draw.get('presentEpoch'):return False
    matches=[r for r in draw.get('boundResources',[]) if r.get('kind')==3 and r.get('stage')==4 and r.get('slot')==record['slot']]
    return len(matches)==1 and matches[0]['objectId']==record['objectId'] and matches[0]['viewId']==record['viewId']


def collect(draw_report,preview_receipt):
    if draw_report.get('schema')!='endfield.selected-shader-saved-draw-corpus.v1' or draw_report.get('status')!='complete':raise ValueError('saved draw corpus is incomplete')
    tails=source_tails(preview_receipt);frames=defaultdict(list)
    for session in draw_report['sessions']:
        for draw in session['draws']:frames[draw['metadata']].append(draw)
    rows=[];counts=Counter(dict(completeCompressedPayloads=0,storedMipTailMatches=0,sameDrawPayloads=0,sameDrawStoredMipTailMatches=0))
    for name,draws in frames.items():
        path=Path(name);raw=path.read_bytes()
        if any(hashlib.sha256(raw).hexdigest()!=d['metadataSha256'] for d in draws):raise ValueError('saved frame changed after draw census')
        m=json.loads(raw)
        for ordinal,record in enumerate(m['selectedResourceRecords']):
            key=texture_payload(path.parent,m,record)
            if key is None:continue
            counts['completeCompressedPayloads']+=1;candidates=tails.get(key,[])
            owners=[d for d in draws if same_draw_payload(record,d,m)]
            if candidates:counts['storedMipTailMatches']+=1
            if owners:counts['sameDrawPayloads']+=1
            if candidates and owners:counts['sameDrawStoredMipTailMatches']+=1
            rows.append(dict(metadata=name,selectedRecordOrdinal=ordinal,slot=record['slot'],payloadSha256=key[-1],resourceFormat=record['format'],viewFormat=record['viewFormat'],
                width=key[1],height=key[2],mipCount=key[3],sourceCandidates=candidates,sameDrawOrdinals=[d['drawOrdinal'] for d in owners]))
    return dict(schema='endfield.stored-texture-saved-payload-joins.v1',status='complete',counts=dict(counts),rows=rows,
        evidenceBoundary='Exact complete compressed mip-tail content comparisons against frozen stored preview inputs. Same-draw joins additionally require copy phase, call/Present and bound object/view equality. Content equality does not identify a source Material; unjoined frame-end payloads do not prove draw-local contents.')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--draw-report',type=Path,required=True);p.add_argument('--texture-receipt',type=Path,required=True);args=p.parse_args(argv)
    try:
        r=collect(json.loads(args.draw_report.read_bytes()),json.loads(args.texture_receipt.read_bytes()));write_json(REPO_ROOT/'reports/assets/stored_texture_saved_payload_joins.json',r)
        print('Saved texture payload joins:',r['counts'],flush=True);return 0
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as e:print('Saved texture payload comparison failed:',str(e)[:1600],flush=True);return 1


if __name__=='__main__':raise SystemExit(main())
