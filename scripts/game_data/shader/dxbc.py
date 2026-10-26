"""Exact DXBC container framing and token-encoded program stage."""
import hashlib
import struct

STAGES={0:'fragment',1:'vertex',2:'geometry',3:'hull',4:'domain',5:'compute'}


def read_dxbc(raw):
    if len(raw)<32 or raw[:4]!=b'DXBC':raise ValueError('DXBC header/magic truncated or differs')
    version,size,count=struct.unpack_from('<III',raw,20)
    end=32+count*4
    if version!=1 or size!=len(raw) or count>4096 or end>len(raw):raise ValueError('DXBC version/length/chunk count differs')
    chunks=[];ranges=[];stages=[]
    for i in range(count):
        at,=struct.unpack_from('<I',raw,32+i*4)
        if at<end or at+8>len(raw):raise ValueError('DXBC chunk offset outside container')
        fourcc=raw[at:at+4];length,=struct.unpack_from('<I',raw,at+4)
        if at+8+length>len(raw):raise ValueError('DXBC chunk byte range outside container')
        ranges.append((at,at+8+length));item=dict(fourCC=fourcc.decode('ascii'),offset=at,byteSize=length)
        if fourcc in (b'SHDR',b'SHEX'):
            if length<8 or length%4:raise ValueError('DXBC token body length differs')
            token,words=struct.unpack_from('<II',raw,at+8);stage=STAGES.get(token>>16)
            if stage is None or words*4!=length:raise ValueError('DXBC stage/token word census differs')
            item.update(stage=stage,major=(token>>4)&15,minor=token&15);stages.append(stage)
        chunks.append(item)
    cursor=end
    for start,stop in sorted(ranges):
        if start!=cursor:raise ValueError('DXBC chunks overlap or leave undeclared bytes')
        cursor=stop
    if cursor!=len(raw) or len(stages)!=1:raise ValueError('DXBC EOF or executable chunk census differs')
    return dict(stage=stages[0],sha256=hashlib.sha256(raw).hexdigest(),byteSize=len(raw),chunks=chunks)
