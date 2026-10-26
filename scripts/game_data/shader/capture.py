"""Read saved graphics shader archives without promoting registration to draws."""
import hashlib
import json
from pathlib import Path
import re
from scripts.game_data.shader.dxbc import read_dxbc

STAGES={0:'vertex',4:'fragment'}


def selected_archive(directory,wanted):
    manifest=directory/'manifest.json';raw=manifest.read_bytes();doc=json.loads(raw)
    if doc.get('schema')!='endfieldCapture.shaderArchive.v1':raise ValueError('unsupported graphics shader archive schema')
    registrations=doc.get('registrations')
    if not isinstance(registrations,list) or len(registrations)>65536:raise ValueError('shader registration census outside bounds')
    result={};cache={}
    for row in registrations:
        digest=row['sha256'];stage=STAGES.get(row['stage'])
        if digest not in wanted or stage is None:continue
        if not re.fullmatch(r'[0-9a-f]{64}',digest) or row['file']!=f'{digest}-s{row["stage"]}.dxbc':raise ValueError('selected shader archive filename differs')
        if digest not in cache:
            path=directory/row['file']
            if not 0<path.stat().st_size<=16*1024*1024:raise ValueError('selected shader archive byte size outside bounds')
            code=path.read_bytes();frame=read_dxbc(code)
            if frame['sha256']!=digest:raise ValueError('selected shader archive content hash differs')
            cache[digest]=(code,frame)
        code,frame=cache[digest]
        if frame['stage']!=stage or len(code)!=row['bytecodeSize'] or int(digest[:16],16)!=row['identityHash']:
            raise ValueError('selected shader archive stage/size/identity differs')
        key=(row['stage'],row['identityHash'],row['bytecodeSize'])
        if key in result and result[key]['sha256']!=digest:raise ValueError('ambiguous draw shader identity prefix')
        result[key]=dict(sha256=digest,stage=stage,bytecode=code)
    return result,dict(path=str(manifest),sha256=hashlib.sha256(raw).hexdigest())


def observed_constants(draw,stage,slot,required_bytes):
    if type(required_bytes)!=int or not 0<required_bytes<=65536:raise ValueError('executable CB span outside bounds')
    choices=[c for c in draw.get('constantBuffers',[]) if c['stage']==stage and c['slot']==slot]
    if len(choices)!=1:return dict(status='unresolved',reason='no unique draw constant-buffer observation')
    c=choices[0]
    if not c.get('rangeValid') or not c.get('metadataValid'):return dict(status='unresolved',reason='draw constant-buffer range/metadata unavailable')
    count=c.get('capturedConstants');text=c.get('dataHex')
    if type(count)!=int or not 0<=count<=4096 or not isinstance(text,str) or not re.fullmatch(r'[0-9a-f]*',text) or len(text)!=count*32:
        raise ValueError('draw constant-buffer prefix byte census differs')
    first,num=c.get('firstConstant'),c.get('numConstants')
    if type(first)!=int or first<0 or type(num)!=int or not 0<num<=4096 or count>num:
        raise ValueError('draw constant-buffer captured/bound range census differs')
    if len(text)//2<required_bytes:return dict(status='unresolved',reason='captured prefix does not cover executable declaration',capturedBytes=len(text)//2,requiredBytes=required_bytes)
    return dict(status='direct',bufferId=c['bufferId'],firstConstant=c['firstConstant'],numConstants=c['numConstants'],capturedBytes=len(text)//2,
        prefixSha256=hashlib.sha256(bytes.fromhex(text)).hexdigest(),
        evidenceBoundary='Saved draw-local constant-buffer observation with complete declared prefix. This does not identify a source Material or prove an executed instruction read.')
