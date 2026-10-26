"""Prefix-owned Endfield constant-buffer/resource/descriptor table reader.

Candidate boundaries only follow completely parsed CB rows. A unique suffix
must close the entire resource and descriptor tables; arbitrary byte scanning
never supplies a boundary. Uninterpreted header/descriptor words stay explicit.


Evidence and admission boundary
-------------------------------
Exact stored framing includes nested structs and whole constant-buffer rows.
Descriptor-set IDs are keys and may be sparse, rather than row ordinals;
duplicate/out-of-range IDs and malformed binding maxima fail closed. Sparse-ID
support corrects a dedicated AnimeStudio parser defect; fixture validation is
not a rebuilt production exporter or renewed corpus admission. Unknown header
and packed words remain structuralOnly; no GPU slot/upload or sampler claim.
"""
import struct
from scripts.game_data.unity_scene import _Reader


def _name(reader,*,empty=False):
    length,=reader.unpack('i','name length')
    if not 0<=length<=1024:raise ValueError('parameter name length outside bounds')
    value=reader.take(length,'name').decode('utf-8');reader.align()
    if (not value and not empty) or (value and (not value.strip() or any(ord(c)<32 or ord(c)==127 for c in value))):
        raise ValueError('parameter name empty/control characters')
    return value


def _fields(reader,count,size):
    if not 0<=count<=4096:raise ValueError('CB field count outside bounds')
    fields=[];seen=set()
    for _ in range(count):
        field=_name(reader);kind,rows,cols,array,unknown,offset=reader.unpack('6i','CB field words')
        if field in seen or not 0<=kind<=16 or not 1<=rows<=16 or not 1<=cols<=16 or not 0<=array<=65535 or not 0<=offset<size:
            raise ValueError(f'CB field {field!r} shape/offset differs: kind={kind}; rows={rows}; columns={cols}; array={array}; offset={offset}; CB bytes={size}')
        seen.add(field);fields.append(dict(name=field,kind=kind,rows=rows,columns=cols,arraySize=array,unknown=unknown,byteOffset=offset))
    return fields


def _cb(reader):
    name=_name(reader);size,count=reader.unpack('ii','CB size/count')
    if not 0<size<=16*1024*1024:raise ValueError('CB size outside bounds')
    fields=_fields(reader,count,size);count,=reader.unpack('i','CB struct count')
    if not 0<=count<=256:raise ValueError('CB struct count outside bounds')
    structs=[];seen=set()
    for _ in range(count):
        label=_name(reader);offset,array,stride,num=reader.unpack('4i','CB struct words')
        if label in seen or offset<0 or not 0<=array<=65535 or stride<=0 or offset+max(1,array)*stride>size:
            raise ValueError('CB struct name/span differs')
        seen.add(label);structs.append(dict(name=label,byteOffset=offset,arraySize=array,byteSize=stride,fields=_fields(reader,num,stride)))
    return dict(name=name,byteSize=size,fields=fields,structs=structs)


def _suffix(raw,start):
    reader=_Reader(raw);reader.offset=start;count,=reader.unpack('i','resource count')
    if not 0<=count<=4096:raise ValueError('resource count outside bounds')
    resources=[]
    for _ in range(count):
        name=_name(reader,empty=True);kind,=reader.unpack('I','resource kind');width={0:3,1:2,2:2,4:2}.get(kind)
        if width is None or not name and kind!=4:raise ValueError('resource kind/name unsupported')
        resources.append(dict(name=name,kind=kind,words=list(reader.unpack('I'*width,'resource words'))))
    tail=reader.offset;count,=reader.unpack('i','descriptor set count')
    if not 0<count<=32:raise ValueError('descriptor set count outside bounds')
    sets=[];total=0;set_ids=set()
    for index in range(count):
        name=_name(reader);set_id,num,maximum=reader.unpack('iii','descriptor set words')
        if not 0<=set_id<=255 or set_id in set_ids or not 0<=num<=4096 or not -1<=maximum<=65535:raise ValueError(f'descriptor set {name!r}: duplicate/out-of-range id={set_id}; count={num}; maximum={maximum}')
        set_ids.add(set_id)
        bindings=[];seen=set()
        for _ in range(num):
            binding=_name(reader);slot,kind,packed,info=reader.unpack('iiII','descriptor binding words')
            if not 0<=slot<=65535 or slot in seen or not 0<=kind<=9:raise ValueError('descriptor binding slot/type differs')
            seen.add(slot);bindings.append(dict(name=binding,bindingIndex=slot,descriptorType=kind,packedBinding=packed,packedInfo=info))
        if maximum!=max(seen,default=-1):raise ValueError(f'descriptor set {name!r}: expected maximum={max(seen,default=-1)}; actual={maximum}; count={num}')
        sets.append(dict(name=name,setId=set_id,maxBindingIndex=maximum,bindings=bindings));total+=num
    if not total:raise ValueError('parameter record has no descriptor bindings')
    reader.finish();return dict(resourceTableOffset=start,descriptorTableOffset=tail,resources=resources,descriptorSets=sets)


def read_parameters(raw):
    if len(raw)<28:raise ValueError('parameter record header truncated')
    reader=_Reader(raw);reader.offset=24;buffers=[];names=set();candidates=[]
    for _ in range(257):
        boundary=reader.offset
        try:candidates.append(dict(_suffix(raw,boundary),constantBuffers=list(buffers)))
        except (ValueError,UnicodeError,struct.error):pass
        if len(buffers)==256:break
        try:buffer=_cb(reader)
        except (ValueError,UnicodeError,struct.error):break
        if buffer['name'] in names:break
        names.add(buffer['name']);buffers.append(buffer)
    if len(candidates)!=1:raise ValueError(f'parameter prefix/resource/descriptor EOF has {len(candidates)} complete candidates')
    return candidates[0]
