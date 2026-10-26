"""Read a Unity v22 serialized file's complete header/metadata directory.

The caller supplies the header plus metadata bytes, and separately authenticates
the original file length/source. This reader retains ordered external slots and
object spans, including files with type trees. It does not decode object bodies,
assign semantics to type dependencies or bind an external to another VFS layer.
"""
from __future__ import annotations

import struct
import json
from functools import lru_cache

from scripts.game_data.unity_scene import _Reader
from scripts.game_data.contracts import CONTRACTS_DIR


@lru_cache(maxsize=1)
def common_strings():
    contract=json.loads((CONTRACTS_DIR/'unity_common_strings.json').read_bytes())
    if contract['schema']!='unity.serialized-common-strings.v1' or contract['status']!='reviewed':
        raise ValueError('unsupported Unity common-string contract')
    return {int(k):v for k,v in contract['strings'].items()}


def read_directory(data: bytes, *, file_length: int) -> dict:
    if len(data)<48 or struct.unpack_from('>I',data,8)[0]!=22 or data[16]!=0:
        raise ValueError('serialized directory requires a little-endian v22 header')
    size,total,body_start=struct.unpack_from('>IQQ',data,20)
    if (total!=file_length or len(data)!=48+size or not 48<len(data)<=body_start<=total):
        raise ValueError(f'serialized directory header bounds differ: metadata={len(data)}/{48+size}; file={file_length}/{total}; dataOffset={body_start}')
    reader=_Reader(data);reader.offset=48

    def string(label):
        end=data.find(b'\0',reader.offset)
        if end<reader.offset:raise ValueError(f'{label}: missing terminator at {reader.offset}')
        value=reader.take(end-reader.offset,label).decode('utf-8',errors='strict')
        reader.take(1,label+'.terminator');return value

    def count(label,width):
        value,=reader.unpack('i',label)
        if not 0<=value<=(len(data)-reader.offset)//width:
            raise ValueError(f'{label}: count {value} cannot fit remaining metadata')
        return value

    unity_version=string('unityVersion');platform,=reader.unpack('i','platform')
    tree_enabled=reader.boolean('typeTreeEnabled')

    def serialized_type(is_reference):
        class_id,=reader.unpack('i','classId');stripped=reader.boolean('stripped')
        script_index,=reader.unpack('h','scriptIndex')
        if script_index < -1:raise ValueError('serialized type script index below -1')
        script_id=reader.take(16,'scriptId').hex() if ((is_reference and script_index>=0) or (not is_reference and class_id==114)) else None
        old_hash=reader.take(16,'typeHash').hex();nodes=[];dependencies=[];reference_names=[]
        if tree_enabled:
            node_count=count('typeTree.nodeCount',32)
            buffer_size,=reader.unpack('i','typeTree.stringBufferSize')
            if buffer_size<0:raise ValueError('negative type-tree string buffer size')
            for index in range(node_count):
                version,level,flags,type_offset,name_offset,byte_size,node_index,meta_flags,ref_hash=reader.unpack('HBBIIiiiQ',f'typeTree.node[{index}]')
                nodes.append(dict(version=version,level=level,flags=flags,typeOffset=type_offset,nameOffset=name_offset,
                                  byteSize=byte_size,index=node_index,metaFlags=meta_flags,refHash=ref_hash))
            buffer=reader.take(buffer_size,'typeTree.stringBuffer')
            for node in nodes:
                for label in ('typeOffset','nameOffset'):
                    offset=node[label]
                    if offset&0x80000000:
                        value=common_strings().get(offset&0x7FFFFFFF)
                        if value is None:raise ValueError(f'unknown type-tree common-string offset {offset&0x7FFFFFFF}')
                    else:
                        if offset>=len(buffer) or buffer.find(b'\0',offset)<offset:
                            raise ValueError(f'typeTree {label}: local string offset {offset} outside terminated buffer')
                        value=buffer[offset:buffer.index(b'\0',offset)].decode('utf-8',errors='strict')
                    node['type' if label=='typeOffset' else 'name']=value
            if is_reference:
                reference_names=[string('referenceType.'+name) for name in ('class','namespace','assembly')]
            else:
                dependencies=[reader.unpack('i','typeDependency')[0] for _ in range(count('typeDependencies',4))]
        return dict(classId=class_id,stripped=stripped,scriptIndex=script_index,scriptId=script_id,typeHash=old_hash,
                    nodeCount=len(nodes),nodes=nodes,typeDependencies=dependencies,referenceNames=reference_names)

    types=[serialized_type(False) for _ in range(count('types',23))]
    objects=[];seen=set()
    for index in range(count('objects',24)):
        reader.align();pid,start,length,type_index=reader.unpack('qqIi',f'object[{index}]')
        start+=body_start
        if pid in seen or not 0<=type_index<len(types) or not body_start<=start<=total-length:
            raise ValueError(f'object[{index}] duplicate identity, type index or source span differs: PathID={pid}; type={type_index}; start={start}; length={length}')
        seen.add(pid);objects.append(dict(pathId=pid,byteStart=start,byteSize=length,typeIndex=type_index,classId=types[type_index]['classId']))
    spans=sorted((r['byteStart'],r['byteStart']+r['byteSize']) for r in objects)
    if any(a[1]>b[0] for a,b in zip(spans,spans[1:])):raise ValueError('serialized directory object spans overlap')
    scripts=[]
    for index in range(count('scripts',12)):
        file_index,=reader.unpack('i',f'script[{index}].fileIndex');reader.align()
        pid,=reader.unpack('q',f'script[{index}].PathID');scripts.append(dict(fileIndex=file_index,pathId=pid))
    externals=[]
    for index in range(count('externals',22)):
        offset=reader.offset;prefix=string('external.prefix');guid=reader.take(16,'external.guid').hex()
        kind,=reader.unpack('i','external.type');path=string('external.path')
        externals.append(dict(fileId=index+1,metadataOffset=offset,prefix=prefix,guid=guid,type=kind,path=path,
                              fileName=path.replace('\\','/').rsplit('/',1)[-1]))
    refs=[serialized_type(True) for _ in range(count('referenceTypes',23))]
    user_info=string('userInformation');reader.finish()
    return dict(unityVersion=unity_version,platform=platform,fileLength=total,dataOffset=body_start,
                metadataLength=len(data),typeTreeEnabled=tree_enabled,types=types,objects=objects,
                scripts=scripts,externals=externals,referenceTypes=refs,userInformation=user_info)
