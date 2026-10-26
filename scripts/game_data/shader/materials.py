"""Stored material values and conditional named parameter-layout coverage.

Presence in a compiled parameter table does not prove a live upload or a shader
instruction read. Offset alternatives stay separate instead of selecting one.


Evidence and admission boundary
-------------------------------
StructuralOnly coverage separates explicit numeric Material overrides from
Shader defaults and retains every named field-offset alternative per conditional
LOD/pass cohort. Missing layouts remain counted; unknown keywords prevent
candidate selection. Repeated named tables do not prove instruction use or
effective upload. Fallback texture names are declarations, not decoded images.
"""
from collections import Counter, defaultdict
import json
import math


def material_parameters(material,shader,candidates):
    saved=material['m_SavedProperties'];declared={p['m_Name']:p for p in shader['declarations']}
    values={}
    for field,kind in [('m_Ints','integer'),('m_Floats','float'),('m_Colors','vector')]:
        for row in saved.get(field,[]):
            name=row['Key'];value=row['Value']
            if name in values:raise ValueError('duplicate stored material numeric property')
            numbers=list(value.values()) if isinstance(value,dict) else [value]
            if any(type(v) not in (int,float) or not math.isfinite(v) for v in numbers):raise ValueError('material numeric value is non-finite or unsupported')
            values[name]=dict(name=name,kind=kind,value=value,source='stored_material',declared=name in declared)
    # Retain all four stored default words. They are declarations, not values
    # proven to be uploaded; texture fallback names never become fake images.
    defaults=[dict(name=p['m_Name'],type=p['m_Type'],words=[p.get(f'm_DefValue[{i}]') for i in range(4)],
                   texture=p.get('m_DefTexture'),source='shader_declaration') for p in shader['declarations'] if p['m_Name'] not in values]
    wanted=set(declared)|set(values)|{t['Key']+'_ST' for t in saved.get('m_TexEnvs',[])}
    groups=defaultdict(list)
    for v in candidates:groups[(v['shaderLOD'],v['subShaderOrdinal'],v['passOrdinal'],v['passName'])].append(v)
    passes=[]
    for (lod,sub,ordinal,name),variants in groups.items():
        resources=Counter();fields=Counter();alternatives=defaultdict(dict);available=0
        for variant in variants:
            layout=shader['parameterLayouts'].get(variant['layoutId'])
            if layout is None:continue
            available+=1
            resources.update({r['name'] for r in layout['resources'] if r['name'] in wanted})
            seen=set()
            for buffer in layout['constantBuffers']:
                for field in buffer['fields']:
                    if field['name'] not in wanted:continue
                    key=(buffer['name'],field['name']);seen.add(key)
                    shape=dict(bufferBytes=buffer['byteSize'],**field)
                    alternatives[key][json.dumps(shape,sort_keys=True)]=shape
            fields.update(seen)
        passes.append(dict(shaderLOD=lod,subShaderOrdinal=sub,passOrdinal=ordinal,passName=name,
            candidateRecords=len(variants),availableParameterRecords=available,
            namedResources=[dict(name=n,presentRecords=c) for n,c in sorted(resources.items())],
            namedFields=[dict(buffer=b,name=n,presentRecords=c,alternatives=list(alternatives[(b,n)].values())) for (b,n),c in sorted(fields.items())]))
    return dict(storedValues=list(values.values()),unoverriddenDeclarations=defaults,passes=passes,
        evidenceBoundary='Stored numeric values and Shader declaration defaults are distinct. Conditional compiled parameter-table name/offset coverage does not prove instruction use, runtime upload, resource binding or shading.')
