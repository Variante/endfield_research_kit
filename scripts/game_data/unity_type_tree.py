"""Bounded independent value decoder for serialized Unity type-tree nodes.

Only declared primitive, string, map, byte-buffer, array and compound layouts
participate. Nodes come from authenticated metadata; unsupported shapes fail
instead of inferring a schema or changing a class-specific reader's coverage.


Evidence and admission boundary
-------------------------------
Exact declared-field decoding consumes body EOF and checks complete generic
JSON while preserving primitive float widths. Byte-buffer bounds and compound
item budgets are distinct. Generic Material fields retain UV-set indices,
double-sided GI and tails omitted by dedicated JSON. Matching texture keys to
the exact Shader's declared properties is structuralOnly, not sampler binding
or runtime keyword selection; parsed-form Shader names can exist when the root
object name is empty.
"""
from __future__ import annotations

import base64
import math
import struct

from scripts.game_data.unity_scene import _Reader

PRIMITIVES={'SInt8':'b','UInt8':'B','short':'h','SInt16':'h','unsigned short':'H','UInt16':'H',
            'int':'i','SInt32':'i','unsigned int':'I','UInt32':'I','Type*':'I','long long':'q',
            'SInt64':'q','unsigned long long':'Q','UInt64':'Q','FileSize':'Q','float':'f','double':'d'}


class Float32(float):
    """Retain primitive width when comparing round-trip JSON decimals."""


def decode_object(nodes,raw,*,max_items=2_000_000,max_depth=256,omit_when=None):
    if not nodes or nodes[0]['level']!=0:
        raise ValueError('type tree lacks one root node')
    roots=[];stack=[]
    for node in nodes:
        level=node['level']
        if level<0 or level>=max_depth or level>len(stack):
            raise ValueError('type-tree nesting level skips a parent or exceeds depth limit')
        stack=stack[:level];item=dict(node,children=[])
        if stack:stack[-1]['children'].append(item)
        else:roots.append(item)
        stack.append(item)
    if len(roots)!=1:raise ValueError('type tree has multiple roots')
    conditions=omit_when or {}
    top=roots[0]['children'];top_names=[n['name'] for n in top]
    for field,(dependency,expected_type,expected_value) in conditions.items():
        if (top_names.count(field)!=1 or top_names.count(dependency)!=1
                or top_names.index(dependency)>=top_names.index(field)
                or top[top_names.index(dependency)]['type']!=expected_type):
            raise ValueError(f'conditional field {field}: prior declared {dependency} layout differs')
    reader=_Reader(raw);budget=max_items

    def length(label,min_width,*,buffer=False):
        nonlocal budget
        count,=reader.unpack('i',label+'.count')
        if count<0 or (not buffer and count>budget) or count>(len(raw)-reader.offset)//max(1,min_width):
            raise ValueError(f'{label}: array count {count} exceeds body/item bounds at {reader.offset}')
        if not buffer:budget-=count
        return count

    def value(node,path):
        kind=node['type'];children=node['children'];align=bool(node['metaFlags']&0x4000)
        if kind in PRIMITIVES:
            if children:raise ValueError(f'{path}: primitive has children')
            result,=reader.unpack(PRIMITIVES[kind],path)
            if kind in ('float','double') and not math.isfinite(result):raise ValueError(f'{path}: non-finite stored number')
            if kind=='float':result=Float32(result)
        elif kind=='bool':
            result=reader.boolean(path)
        elif kind=='char':
            result=chr(reader.unpack('H',path)[0])
        elif kind=='string':
            size,=reader.unpack('i',path+'.length')
            result=reader.take(size,path).decode('utf-8',errors='strict');reader.align()
        elif kind=='TypelessData':
            if len(children)!=2 or children[0]['name']!='size' or children[1]['name']!='data':
                raise ValueError(f'{path}: unsupported TypelessData node shape')
            result=base64.b64encode(reader.take(length(path,1,buffer=True),path)).decode('ascii')
        elif len(children)==1 and children[0]['type']=='Array':
            array=children[0];members=array['children'];align|=bool(array['metaFlags']&0x4000)
            if len(members)!=2 or members[0]['name']!='size' or members[1]['name']!='data':
                raise ValueError(f'{path}: unsupported array node shape')
            element=members[1]
            packed_bytes=(element['type']=='UInt8' and not element['children'] and not element['metaFlags']&0x4000)
            count=length(path,max(1,element['byteSize']),buffer=packed_bytes)
            if kind=='map':
                pair=element['children']
                if len(pair)!=2 or [p['name'] for p in pair]!=['first','second']:
                    raise ValueError(f'{path}: unsupported map pair shape')
                result=[dict(Key=value(pair[0],f'{path}[{i}].Key'),Value=value(pair[1],f'{path}[{i}].Value')) for i in range(count)]
            elif packed_bytes:
                result=list(reader.take(count,path))
            else:
                result=[value(element,f'{path}[{i}]') for i in range(count)]
        elif not children and node['byteSize']==0:
            result={}
        elif children:
            result={}
            for child in children:
                if path=='$' and child['name'] in conditions:
                    dependency,_,expected=conditions[child['name']]
                    if result[dependency]==expected:continue
                if child['name'] in result:raise ValueError(f'{path}: duplicate compound field {child["name"]}')
                result[child['name']]=value(child,path+'.'+child['name'])
        else:
            raise ValueError(f'{path}: unsupported type-tree leaf {kind!r}')
        if align:reader.align()
        return result

    out=value(roots[0],'$');reader.finish();return out


def check_json(decoded,typed,*,path='$'):
    """Check complete generic JSON with the declared primitive's float width."""
    if isinstance(decoded,Float32):
        if not isinstance(typed,(int,float)) or isinstance(typed,bool) or struct.unpack('<f',struct.pack('<f',typed))[0]!=decoded:
            raise ValueError(f'{path}: float32 raw/JSON value differs')
    elif isinstance(decoded,dict):
        if not isinstance(typed,dict) or decoded.keys()!=typed.keys():raise ValueError(f'{path}: raw/JSON field set differs')
        for k,v in decoded.items():check_json(v,typed[k],path=path+'.'+k)
    elif isinstance(decoded,list):
        if not isinstance(typed,list) or len(decoded)!=len(typed):raise ValueError(f'{path}: raw/JSON array length differs')
        for i,(a,b) in enumerate(zip(decoded,typed)):check_json(a,b,path=f'{path}[{i}]')
    elif type(decoded)!=type(typed) or decoded!=typed:
        raise ValueError(f'{path}: raw/JSON value differs: expected={decoded!r}; actual={str(typed)[:120]}')
