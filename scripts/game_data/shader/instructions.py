"""Executable register references joined to stored descriptor/field names.

The checked VS/PS packed-slot lanes are not generalized to other stages. A
declaration match checks executable resource shape and buffer bounds; unmatched
registers, ambiguous names and dynamic field indices stay explicit.
"""
from collections import Counter
import re
from scripts.game_data.shader.dependencies import COMPONENTWISE,operands,instruction_parts

STAGE_PREFIX={'vs':'vertex','ps':'fragment','gs':'geometry','hs':'hull','ds':'domain','cs':'compute'}


def read_disassembly(text,frame):
    stages=[];declarations={};instructions=[];outputs={};literal_depth=0
    for raw in text.splitlines():
        line=raw.strip()
        if not line or line.startswith('//'):continue
        if literal_depth:
            if not re.fullmatch(r'[{}\s,0-9a-fx]+',line):raise ValueError('unsupported immediate constant buffer row')
            literal_depth+=line.count('{')-line.count('}')
            if literal_depth<0:raise ValueError('immediate constant buffer delimiter differs')
            continue
        m=re.fullmatch(r'(vs|ps|gs|hs|ds|cs)_(\d+)_(\d+)',line)
        if m:
            stages.append((STAGE_PREFIX[m[1]],int(m[2]),int(m[3])));continue
        if not stages:raise ValueError('instruction text before DXBC stage header')
        if line.startswith('dcl_'):
            output=re.fullmatch(r'dcl_output(?:_siv)? (o\d+)(?:\.([xyzw]+))?(?:, \w+)?',line)
            if output:
                outputs.setdefault(output[1],set()).update(output[2] or 'xyzw');continue
            if line.startswith('dcl_immediateConstantBuffer'):
                payload=line.removeprefix('dcl_immediateConstantBuffer').strip()
                if not payload.startswith('{') or not re.fullmatch(r'[{}\s,0-9a-fx]+',payload):raise ValueError('unsupported immediate constant buffer declaration')
                literal_depth=payload.count('{')-payload.count('}')
                if literal_depth<0:raise ValueError('immediate constant buffer delimiter differs')
                continue
            m=re.fullmatch(r'dcl_constantbuffer CB(\d+)\[(\d+)\], (immediateIndexed|dynamicIndexed)',line)
            if m:kind='cb';index=int(m[1]);item=dict(kind=kind,index=index,rows=int(m[2]),declaration=line)
            elif line.startswith(('dcl_resource_','dcl_sampler ','dcl_uav_')):
                match=re.search(r'\b([tsu])(\d+)\b',line)
                if match is None:raise ValueError('resource declaration register unavailable')
                kind,index=match[1],int(match[2]);item=dict(kind=kind,index=index,declaration=line)
            else:continue
            key=f'{kind}{index}'
            if key in declarations:raise ValueError('duplicate executable resource declaration')
            declarations[key]=item;continue
        instructions.append(line)
    if literal_depth:raise ValueError('unterminated immediate constant buffer declaration')
    if len(stages)!=1 or stages[0][0]!=frame['stage']:raise ValueError('native/token stage headers disagree')
    tokens=[c for c in frame.get('chunks',[]) if c['fourCC'] in ('SHDR','SHEX')]
    if tokens and (len(tokens)!=1 or stages[0][1:]!=(tokens[0]['major'],tokens[0]['minor'])):
        raise ValueError('native/token shader model headers disagree')
    resource_refs=Counter();cb_refs=[]
    for ordinal,line in enumerate(instructions):
        for kind,index in re.findall(r'\b([tsu])(\d+)\b',line):
            key=kind+index
            if key not in declarations:raise ValueError('instruction references undeclared resource '+key)
            resource_refs[key]+=1
        token,tail=instruction_parts(line);opcode=token.split('(')[0].removesuffix('_sat')
        try:args=operands(tail) if tail else []
        except ValueError as e:raise ValueError(f'{e}: instruction {ordinal}: {line[:320]}') from e
        destination=re.fullmatch(r'(?:r\d+|o\d+)(?:\.([xyzw]+))?',args[0]) if args else None
        for ai,arg in enumerate(args):
          for index,address,swizzle in re.findall(r'\bcb(\d+)\[([^\]]+)\](?:\.([xyzw]+))?',arg):
            key='cb'+index;decl=declarations.get(key)
            if decl is None:raise ValueError('instruction references undeclared CB '+key)
            positions=set(range(4));conservative=True
            if opcode in COMPONENTWISE and destination:
                positions={'xyzw'.index(c) for c in destination[1] or 'xyzw'};conservative=False
            elif opcode in ('dp2','dp3','dp4'):
                positions=set(range(int(opcode[-1])));conservative=False
            elif opcode in ('sample_b_indexable','sample_l_indexable') and ai==4:
                positions={0};conservative=False
            source_swizzle=swizzle or 'xyzw'
            if len(source_swizzle) not in (1,4):raise ValueError('unsupported executable CB source swizzle')
            if address.isdecimal():
                row=int(address)
                if row>=decl['rows']:raise ValueError('instruction CB row outside declaration')
                offsets=sorted({row*16+'xyzw'.index(source_swizzle[0] if len(source_swizzle)==1 else source_swizzle[p])*4 for p in positions})
            else:offsets=None
            cb_refs.append(dict(register=key,address=address,byteOffsets=offsets,instructionOrdinal=ordinal,conservative=conservative))
    return dict(stage=stages[0][0],model=list(stages[0][1:]),instructionCount=len(instructions),declarations=declarations,
        instructions=instructions,
        outputs=[r+'.'+''.join(c for c in 'xyzw' if c in mask) for r,mask in sorted(outputs.items())],
        resourceReferences=dict(resource_refs),constantBufferReferences=cb_refs,
        opcodeCounts=dict(Counter(line.split()[0].split('(')[0] for line in instructions)))


def bind_parameters(executable,layout):
    shift={'vertex':24,'fragment':16}.get(executable['stage'])
    if shift is None:return dict(status='unsupported_stage',bindings=[],gaps=[])
    buffers={b['name']:b for b in layout['constantBuffers']};bindings=[];by_register={};gaps=[]
    for s in layout['descriptorSets']:
        for b in s['bindings']:
            kind={0:'s',2:'t',3:'u',6:'cb',8:'cb',7:('u' if b['packedBinding']&128 else 't')}.get(b['descriptorType'])
            if kind is None:continue
            slot=(b['packedBinding']>>shift)&255
            if slot==255:continue
            key=kind+str(slot);declaration=executable['declarations'].get(key)
            if declaration is None:continue # Stored stage slot can be eliminated in executable code.
            if b['descriptorType']==7 and not declaration['declaration'].startswith(('dcl_resource_structured ', 'dcl_uav_structured ')):
                gaps.append(dict(register=key,name=b['name'],reason='structured descriptor/executable shape differs'));continue
            if kind=='cb':
                buffer=buffers.get(b['name'])
                if buffer is None or declaration['rows']*16>buffer['byteSize']:
                    gaps.append(dict(register=key,name=b['name'],reason='named CB absent or executable span exceeds table'));continue
            value=dict(register=key,name=b['name'],setId=s['setId'],bindingIndex=b['bindingIndex'],descriptorType=b['descriptorType'])
            bindings.append(value);by_register.setdefault(key,[]).append(value)
    named_refs=[];field_refs={};dynamic=[];anonymous=[]
    for key,count in executable['resourceReferences'].items():
        choices=by_register.get(key,[])
        if len(choices)!=1:gaps.append(dict(register=key,reason='executable resource has no unique named descriptor'));continue
        named_refs.append(dict(choices[0],references=count))
    for ref in executable['constantBufferReferences']:
        choices=by_register.get(ref['register'],[])
        if len(choices)!=1:gaps.append(dict(register=ref['register'],reason='executable CB has no unique named descriptor'));continue
        buffer=buffers[choices[0]['name']]
        if ref['byteOffsets'] is None:
            dynamic.append(dict(buffer=buffer['name'],**ref));continue
        covered=set()
        for field in buffer['fields']:
            # Scalar/vector Float fields only: matrix/array packing and other
            # types remain anonymous offsets, not inferred native reads.
            if field['kind']!=0 or field['rows']!=1 or field['arraySize'] or field['columns']>4:continue
            begin=field['byteOffset'];end=begin+field['columns']*4
            if any(begin<=at<end for at in ref['byteOffsets']):
                covered.update(at for at in ref['byteOffsets'] if begin<=at<end)
                key=(buffer['name'],field['name'],begin)
                field_refs.setdefault(key,dict(buffer=buffer['name'],name=field['name'],byteOffset=begin,instructionOrdinals=[]))['instructionOrdinals'].append(ref['instructionOrdinal'])
        remaining=sorted(set(ref['byteOffsets'])-covered)
        if remaining:anonymous.append(dict(buffer=buffer['name'],**dict(ref,byteOffsets=remaining)))
    unique_gaps=list({str(g):g for g in gaps}.values())
    return dict(status='complete' if not unique_gaps else 'partial',bindings=bindings,namedResourceReferences=named_refs,
        namedFieldReferences=list(field_refs.values()),dynamicConstantBufferReferences=dynamic,anonymousConstantBufferReferences=anonymous,gaps=unique_gaps,
        evidenceBoundary='Checked stored VS/PS packed register lanes against executable declarations and CB bounds. Supported operand forms use component masks; other CB references retain conservative swizzle lanes. References describe compiled syntax, not execution, GPU upload, bound payload identity or selected runtime variant.')
