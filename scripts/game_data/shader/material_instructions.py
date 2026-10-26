"""Conditional compiled instruction reads for persisted Material keywords."""
from collections import Counter,defaultdict


def material_instruction_reads(candidates):
    groups=defaultdict(list)
    for v in candidates:
        for s in v.get('instructionEvidence',[]):
            groups[(v['shaderLOD'],v['subShaderOrdinal'],v['passOrdinal'],v['passName'],s['stage'])].append(s)
    passes=[]
    for (lod,sub,ordinal,name,stage),records in groups.items():
        resources=Counter();fields=Counter();offsets=defaultdict(set);gaps=Counter();complete=0;dynamic=0;anonymous=0
        for r in records:
            b=r['parameterBindings'];complete+=b['status']=='complete'
            resources.update({(v['name'],v['register'][0]) for v in b.get('namedResourceReferences',[])})
            seen=set()
            for f in b.get('namedFieldReferences',[]):
                key=(f['buffer'],f['name']);seen.add(key);offsets[key].add(f['byteOffset'])
            fields.update(seen)
            gaps.update({(g['register'],g['reason']) for g in b.get('gaps',[])})
            dynamic+=bool(b.get('dynamicConstantBufferReferences'))
            anonymous+=bool(b.get('anonymousConstantBufferReferences'))
        passes.append(dict(shaderLOD=lod,subShaderOrdinal=sub,passOrdinal=ordinal,passName=name,stage=stage,
            candidatePrograms=len(records),completeRegisterJoins=complete,dynamicReadPrograms=dynamic,anonymousReadPrograms=anonymous,
            namedResourceReads=[dict(name=n,kind=k,presentPrograms=count) for (n,k),count in sorted(resources.items())],
            namedFieldReads=[dict(buffer=b,name=n,presentPrograms=count,byteOffsets=sorted(offsets[(b,n)])) for (b,n),count in sorted(fields.items())],
            gaps=[dict(register=r,reason=why,presentPrograms=count) for (r,why),count in sorted(gaps.items())]))
    return dict(passes=passes,evidenceBoundary='Syntactic instruction reads in the conditional keyword-superset candidates. Register joins, anonymous byte reads and dynamic indices are distinct. No runtime selection, executed read, GPU upload, sampler state or resource-content proof.')
