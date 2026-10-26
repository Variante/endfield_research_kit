"""Bounded segmented Shader program directories and Endfield code envelopes.

Evidence and admission boundary
-------------------------------
Exact framing consumes plain-LZ4 segments and complete compressed/decoded
range censuses. Segment zero owns the directory; each record selects its actual
data segment. D3D code-envelope ranges must close complete DXBC containers;
token headers, not serialized carrier names, establish executable stage. One
vertex carrier may hold both vertex and fragment executables. Unsupported
non-D3D records remain opaque.
"""
import hashlib
import struct
from scripts.game_data.lz4_block import decompress_lz4
from scripts.game_data.shader.dxbc import read_dxbc
from scripts.game_data.shader.parameters import read_parameters,_name
from scripts.game_data.unity_scene import _Reader

VERSION=0x0C11FFE2  # Serialized record format marker, not a native address.


def _digest(raw):return hashlib.sha256(raw).hexdigest()


def read_code(raw):
    reader=_Reader(raw);reader.offset=24;count,=reader.unpack('i','native keyword count')
    if not 0<=count<=1024:raise ValueError('native shader keyword count outside bounds')
    keywords=[_name(reader) for _ in range(count)]
    size,=reader.unpack('i','native shader code size');code=reader.take(size,'native shader code')
    tail=raw[reader.offset:];reader.take(len(tail),'opaque native record tail');reader.finish()
    if len(code)<4:raise ValueError('native D3D code envelope header truncated')
    word,=struct.unpack_from('<I',code);snippets=word>>24
    if not 1<=snippets<=16 or 4+snippets*8>len(code):raise ValueError('native D3D snippet directory count differs')
    entries=[struct.unpack_from('<II',code,4+i*8) for i in range(snippets)];header=min(p[0] for p in entries)
    if header<4+snippets*8:raise ValueError('native D3D snippets overlap directory')
    rows=[];ranges=[]
    for i,(start,length) in enumerate(entries):
        if start<header or start+length>len(code):raise ValueError('native D3D snippet range outside envelope')
        bytecode=code[start:start+length];info=read_dxbc(bytecode)
        rows.append(dict(info,ordinal=i,offset=start,bytecode=bytecode));ranges.append((start,start+length))
    cursor=header
    for start,end in sorted(ranges):
        if start!=cursor:raise ValueError('native D3D snippets overlap or leave undeclared data')
        cursor=end
    if cursor!=len(code):raise ValueError('native D3D envelope EOF differs')
    return dict(keywords=keywords,codeByteSize=size,codeSha256=_digest(code),headerWord=word,
        opaqueHeaderByteSize=header-(4+snippets*8),opaqueHeaderSha256=_digest(code[4+snippets*8:header]),
        opaqueTailByteSize=len(tail),opaqueTailSha256=_digest(tail),snippets=rows)


def read_shader(body):
    if body['m_CompressionType']!=3 or body['m_ShaderIsBaked'] is not True:raise ValueError('shader baked/compression branch unsupported')
    platforms=body['platforms'];lods=[]
    if len(platforms)!=len(set(platforms)) or not platforms:raise ValueError('shader platform directory duplicates or is empty')
    for ordinal,blob in enumerate(body['subShaderBlobs']):
        raw=bytes(blob['m_CompressedBlob']);offsets=blob['m_Offsets'];compressed=blob['m_CompressedLengths'];decoded=blob['m_DecompressedLengths']
        if any(len(x)!=len(platforms) for x in (offsets,compressed,decoded)):raise ValueError('shader compressed platform directory shape differs')
        ranges=[];output=[]
        for pi,platform in enumerate(platforms):
            if not offsets[pi] or len(offsets[pi])!=len(compressed[pi]) or len(offsets[pi])!=len(decoded[pi]):raise ValueError('shader segment directory shape differs')
            segments=[]
            for si,(start,size,expected) in enumerate(zip(offsets[pi],compressed[pi],decoded[pi])):
                if type(start)!=int or type(size)!=int or start<0 or size<=0 or start+size>len(raw):raise ValueError('shader compressed range outside blob')
                ranges.append((start,start+size));data=decompress_lz4(raw[start:start+size],expected)
                segments.append(data)
            table=segments[0]
            if len(table)<4:raise ValueError('shader program directory truncated')
            count,=struct.unpack_from('<i',table);table_end=4+count*12
            if not 0<=count<=65536 or table_end>len(table):raise ValueError('shader program directory count outside bounds')
            records=[];spans={i:[] for i in range(len(segments))}
            for index in range(count):
                start,size,segment=struct.unpack_from('<iii',table,4+index*12)
                if not 0<=segment<len(segments) or start<0 or size<24 or start+size>len(segments[segment]) or segment==0 and start<table_end:
                    raise ValueError('shader program record span outside segment')
                data=segments[segment][start:start+size];version,kind,*words=struct.unpack_from('<6I',data)
                if version!=VERSION:raise ValueError('shader program record format marker differs')
                row=dict(index=index,segment=segment,offset=start,byteSize=size,sha256=_digest(data),recordKind=kind,headerWords=words,raw=data)
                if platform==4 and kind==33:row.update(status='complete_dxbc_code',code=read_code(data))
                elif 4<=kind<=11:
                    try:row.update(status='complete_parameter_tables',parameters=read_parameters(data))
                    except ValueError as error:row.update(status='opaque_parameter_record',diagnostic=str(error))
                else:row.update(status='opaque_record_kind')
                records.append(row);spans[segment].append((start,start+size))
            for si,data in enumerate(segments):
                cursor=table_end if si==0 else 0
                for start,end in sorted(set(spans[si])):
                    if start!=cursor:raise ValueError('shader record spans overlap or leave undeclared segment bytes')
                    cursor=end
                if cursor!=len(data):raise ValueError('shader segment EOF differs')
            output.append(dict(platform=platform,platformIndex=pi,records=records,segments=[dict(byteSize=len(d),sha256=_digest(d)) for d in segments]))
        cursor=0
        for start,end in sorted(ranges):
            if start!=cursor:raise ValueError('shader compressed segments overlap or leave undeclared bytes')
            cursor=end
        if cursor!=len(raw):raise ValueError('shader compressed blob EOF differs')
        lods.append(dict(ordinal=ordinal,lod=blob['m_ShaderLOD'],platforms=output))
    return dict(name=body['m_ParsedForm']['m_Name'],lods=lods)
