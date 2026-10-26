"""Decode admitted Texture2D top mips through the selected AnimeStudio closure.

The independent reader closes every stored mip before supplying only mip zero
to the codec. This does not select shader roles, sampler states or live mip bias.


Evidence and admission boundary
-------------------------------
Exact source admission precedes this conditional codec projection. Managed and
native codec libraries must come from the same admitted CLI closure, without
filesystem fallback or rebuild. Complete output census, pixel lengths and
hashes precede PNG publication; channels are retained with a row flip for export
coordinates, without gamma conversion or normal reconstruction.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from scripts.common import write_json,sha256_file
from scripts.game_data.cooked_collision_corpus import _decoder_closure
from scripts.game_data.extraction.animestudio.managed_sidecar import build_sidecar
from scripts.game_data.extraction.animestudio.setup_dotnet9 import dotnet_environment
from scripts.game_data.unity_scene import scene_identity
from scripts.game_data.unity_texture import read_texture,png_from_bgra
from scripts.repo_paths import REPO_ROOT

SCHEMA='endfield.stored-texture-previews.v1'
BOUNDARY='Decoded stored mip-zero channels, vertically flipped for exported image coordinates; no gamma conversion, normal reconstruction, shader application, live mip selection or runtime material override claim.'


def texture_key(identity):return hashlib.sha256(json.dumps(scene_identity(identity),separators=(',',':')).encode()).hexdigest()


def decode_textures(rows,bodies,*,cli,work_root):
    work_root.mkdir(parents=True,exist_ok=True);run=Path(tempfile.mkdtemp(prefix='textures-',dir=work_root.resolve()))
    inputs=[];selected={};unavailable=[];before=_decoder_closure(cli)
    for row in rows:
        if row['classId']!=28:raise ValueError('texture preview source is not Texture2D')
        identity=scene_identity(row['identity']);key=texture_key(row['identity']);resource=row.get('resource');stream=None
        if key in selected:raise ValueError('duplicate physical texture preview identity')
        try:
            if resource and resource['size']:
                if resource['status']!='exact_owner_archive_span':raise ValueError('Texture2D resource is outside admitted owner archive')
                path=Path(row['rawPath']).parent/resource['file'];stream=path.read_bytes()
                if hashlib.sha256(stream).hexdigest()!=resource['sha256']:raise ValueError('Texture2D archive byte hash differs')
            texture=read_texture(bodies[identity],stream)
        except ValueError as error:
            unavailable.append(dict(identity=row['identity'],diagnostic=str(error)[:800]));continue
        top=texture['mips'][0];payload=texture.pop('payload');raw=payload[:top['byteSize']];input_path=run/(key+'.mip0')
        input_path.write_bytes(raw)
        item=dict(key=key,input=str(input_path),sha256=hashlib.sha256(raw).hexdigest(),width=texture['width'],height=texture['height'],formatId=texture['formatId'])
        inputs.append(item);selected[key]=dict(source=row,descriptor=texture,payloadSha256=hashlib.sha256(payload).hexdigest(),topMipSha256=item['sha256'])
    manifest=run/'inputs.json';write_json(manifest,inputs)
    if not inputs:return dict(schema=SCHEMA,status='unavailable',textures=[],unavailable=unavailable,evidenceBoundary=BOUNDARY)
    helper=build_sidecar(cli,run/'helper',project=REPO_ROOT/'scripts/game_data/extraction/animestudio/texture_decode/TextureDecode.csproj',binary_name='TextureDecode.dll')
    output=run/'decoded';log=run/'decode.log';command=[helper['sdk'],helper['binary'],str(cli.parent.resolve()),str(manifest),str(output)]
    with log.open('wb') as stream:
        result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,env=dotnet_environment(Path(helper['sdk']).parent))
    if result.returncode or log.stat().st_size:raise ValueError(f'Texture2D decoder diagnosed/failure: {log}; '+log.read_text('utf-8',errors='replace')[:1200])
    decoded=json.loads((output/'decoded.json').read_bytes())
    if decoded.get('schema')!='endfield.texture-top-mip-decode.v1':raise ValueError('texture decoder manifest schema differs')
    seen=set();textures=[];expected_files={'decoded.json'}
    for row in decoded['rows']:
        key=row['key']
        if key in seen or key not in selected or row['file']!=key+'.bgra32':raise ValueError('texture decoder identity/file census differs')
        seen.add(key);expected_files.add(row['file']);pixels=(output/row['file']).read_bytes();source=selected[key];desc=source['descriptor']
        if (row['width'],row['height'],row['bytes'])!=(desc['width'],desc['height'],desc['width']*desc['height']*4) or hashlib.sha256(pixels).hexdigest()!=row['sha256']:
            raise ValueError('texture decoder pixel hash/dimensions differ')
        png=run/(key+'.png');png.write_bytes(png_from_bgra(desc['width'],desc['height'],pixels))
        textures.append(dict(source=source['source'],descriptor=desc,payloadSha256=source['payloadSha256'],topMipSha256=source['topMipSha256'],
                             pixelSha256=row['sha256'],pngPath=str(png),pngSha256=sha256_file(png).lower()))
    if seen!=set(selected) or {p.name for p in output.iterdir()}!=expected_files:raise ValueError('texture decoder output census differs')
    if _decoder_closure(cli)!=before or _decoder_closure(Path(helper['binary']))!=helper['closure']:raise ValueError('texture decoder/CLI closure changed')
    for item in inputs:
        if sha256_file(Path(item['input'])).lower()!=item['sha256']:raise ValueError('texture decoder input changed')
    report=dict(schema=SCHEMA,status='complete',textures=textures,unavailable=unavailable,evidenceBoundary=BOUNDARY,
                producer=dict(command=command,helper=helper,cliClosure=before,inputManifest=str(manifest),inputManifestSha256=sha256_file(manifest),log=str(log)))
    write_json(run/'receipt.json',report);return report
