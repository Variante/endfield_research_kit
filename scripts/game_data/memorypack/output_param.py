"""Prove closed ParamOutput readers without inferring a serialized T value."""
from __future__ import annotations
import hashlib
from functools import lru_cache
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import primitive_param as primitive, scalar_param_native as scalar, pooled_source_helper
from scripts.game_data.memorypack.wrapper_members import derive_from_image

LABEL='memorypackOutputParam'


@lru_cache(maxsize=2)
def _context(image):
    """Pure immutable-image indexes; every public gate still runs afresh."""
    return NativeReferenceContext(image),image.unwind_index


def caller_program(image,record,setters):
    """Closed current profiles; only initialized nonnull-holder paths are claimed."""
    rows=record['instructions'];count=len(rows)
    if count==52:return primitive.setter_call_program(image,record,setters,output=True),rows[38][0]
    if count==51:
        expected=[b'\x48\x89\x5c\x24\x18',b'\x57',b'\x48\x83\xec\x20',None,b'\x48\x8b\xda',b'\x48\x8b\xf9',None,
            None,None,None,None,None,None,None,b'\x48\x8d\x54\x24\x30',b'\xc6\x44\x24\x30\x00',b'\x48\x8b\xcf',None,b'\x84\xc0',None,
            b'\x48\x89\x74\x24\x38',b'\x48\x83\x3b\x00',None,b'\x0f\xb6\x74\x24\x30',b'\x40\x80\xfe\x02',None,
            b'\x48\x8b\x33',b'\x48\x8b\xcf',None,b'\x48\x85\xf6',None,b'\x45\x33\xc0',b'\x8b\xd0',b'\x48\x8b\xce',None,
            b'\x48\x8b\x1b',b'\x48\x8b\xcf',None,b'\x48\x85\xdb',None,None,b'\xcc',b'\x45\x33\xc0',b'\x48\x8b\xd0',b'\x48\x8b\xcb',None,
            b'\x48\x8b\x74\x24\x38',b'\x48\x8b\x5c\x24\x40',b'\x48\x83\xc4\x20',b'\x5f',b'\xc3']
        branches=((6,b'\x75',14),(30,b'\x74',40),(39,b'\x75',42))
        initializers=((7,b'\x48\x8d\x0d'),(8,b'\xe8'),(9,b'\x48\x8d\x0d'),(10,b'\xe8'),(11,b'\x48\x8d\x0d'),(12,b'\xe8'))
        calls={'header':17,'null':19,'paramTarget':28,'path':37}
        stores={'paramTarget':34,'path':45};flag,store=3,13;restore=rows[47][0]
        cold=((22,b'\x0f\x84'),(25,b'\x0f\x85'));other_calls=(40,)
    elif count==77:
        expected=[b'\x48\x89\x5c\x24\x10',b'\x48\x89\x74\x24\x18',b'\x57',b'\x48\x83\xec\x20',None,b'\x48\x8b\xda',b'\x48\x8b\xf1',None,
            None,None,None,None,None,None,None,b'\x48\x8d\x54\x24\x30',b'\xc6\x44\x24\x30\x00',b'\x48\x8b\xce',None,b'\x84\xc0',None,
            b'\x48\x83\x3b\x00',None,None,None,b'\x48\x8b\xf8',b'\x48\x85\xc0',None,b'\x33\xd2',b'\x48\x8b\xc8',None,
            b'\x48\x8b\xcb',b'\x48\x89\x3b',None,b'\x80\x7c\x24\x30\x02',None,b'\x48\x8b\x3b',b'\x48\x8b\xce',None,
            b'\x48\x85\xff',None,b'\x45\x33\xc0',b'\x8b\xd0',b'\x48\x8b\xcf',None,b'\x48\x8b\x1b',b'\x48\x8b\xce',None,
            b'\x48\x85\xdb',None,b'\x45\x33\xc0',b'\x48\x8b\xd0',b'\x48\x8b\xcb',None,None,None,b'\xcc',None,None,None,
            b'\x33\xd2',b'\x48\x8b\xcb',None,b'\x44\x8a\x44\x24\x30',b'\x45\x33\xc9',b'\xb2\x02',b'\x48\x8b\xc8',None,b'\xcc',
            b'\x48\x8b\xcb',b'\x48\xc7\x03\x00\x00\x00\x00',None,b'\x48\x8b\x5c\x24\x38',b'\x48\x8b\x74\x24\x40',b'\x48\x83\xc4\x20',b'\x5f',b'\xc3']
        branches=((7,b'\x75',15),(20,b'\x0f\x84',69),(22,b'\x75',34),(27,b'\x74',55),(35,b'\x75',57),
                  (40,b'\x74',55),(49,b'\x74',55),(54,b'\xeb',72))
        initializers=((8,b'\x48\x8d\x0d'),(9,b'\xe8'),(10,b'\x48\x8d\x0d'),(11,b'\xe8'),(12,b'\x48\x8d\x0d'),(13,b'\xe8'),
                      (23,b'\x48\x8b\x0d'),(57,b'\x48\x8b\x0d'),(58,b'\x48\x8b\x1d'))
        calls={'header':18,'paramTarget':38,'path':47,'barrier':71}
        stores={'paramTarget':44,'path':53};flag,store=4,14;restore=None;cold=();other_calls=(24,30,33,55,59,62,67)
    else:raise ValueError(f'{LABEL}.caller:unproved-instruction-count={count}')
    scalar.program_extent(rows,record['window'],LABEL);scalar.program(image,rows,expected,LABEL)
    def target(n,opcode):
        rva,encoded=rows[n];raw=bytes.fromhex(encoded);size=len(opcode)+(1 if opcode in (b'\x74',b'\x75',b'\xeb') else 4)
        scalar.need(LABEL,'controlShape',(size,opcode),(len(raw),raw[:len(opcode)]))
        return rva+size+int.from_bytes(raw[len(opcode):],'little',signed=True)
    for n,opcode,dest in branches:scalar.need(LABEL,'branchTarget',rows[dest][0],target(n,opcode))
    for n,opcode in cold:scalar.need(LABEL,'coldOutsidePrimary',False,record['window']['startRva']<=target(n,opcode)<record['window']['endRva'])
    for n,prefix in initializers:
        raw=bytes.fromhex(rows[n][1]);scalar.need(LABEL,'initializationShape',(len(prefix)+4,prefix),(len(raw),raw[:len(prefix)]))
    for n in other_calls:target(n,b'\xe8')
    for name,n in stores.items():scalar.need(LABEL,'namedSetter:'+name,setters[name],target(n,b'\xe8'))
    before=bytes.fromhex(rows[flag][1]);after=bytes.fromhex(rows[store][1])
    scalar.need(LABEL,'initFlagShapes',(7,b'\x80\x3d',0,7,b'\xc6\x05',1),(len(before),before[:2],before[-1],len(after),after[:2],after[-1]))
    scalar.need(LABEL,'sameInitFlag',rows[flag][0]+7+int.from_bytes(before[2:6],'little',signed=True),rows[store][0]+7+int.from_bytes(after[2:6],'little',signed=True))
    targets={name:target(n,b'\x0f\x84' if name=='null' else b'\xe8') for name,n in calls.items()}
    if count==77:targets['null']=rows[69][0]
    return targets,restore


def derive_output(image, inputs, wrapped_type):
    if not wrapped_type.startswith('Beyond.Gameplay.Actions.ParamOutput`1<') or not wrapped_type.endswith('>'):
        raise ValueError(LABEL+'.closed-output-type-required')
    base=image.pe.image_base;md=image.metadata;ctx,unwind=_context(image);index=image.body_index
    matches=[w for w in derive_from_image(image).values() if w.wrapped_type==wrapped_type]
    scalar.need(LABEL,'oneWrapper',1,len(matches));wrapper=matches[0]
    scalar.need(LABEL,'members',[('paramTarget','int'),('path','string')],[(m.name,m.declared_type) for m in wrapper.members])
    scalar.need(LABEL,'holder',(wrapper.name,wrapped_type,16),ctx.field(wrapper.name+'::__instance'))
    def record(pointer, *, owned=False, end=None):
        end=end if end is not None else index.extents[pointer]
        ranges=[]
        if owned:
            ranges=sorted(tuple(r['runtimeTriple'][:2]) for r in unwind.family(pointer-base)['ranges'])
            scalar.need(LABEL,'primaryRange',True,(pointer-base,end-base) in ranges)
            for a,b in ranges:
                if base+a==end:end=base+b
        rows=index._decode(pointer,end-pointer)
        return {'pointerRva':pointer-base,'window':{'startRva':pointer-base,'endRva':end-base,
            'sha256':hashlib.sha256(image.pe.bytes_at_va(pointer,end-pointer)).hexdigest().upper()},
            'instructions':[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in rows],
            **({'contiguousOwnedRanges':[[a,b] for a,b in ranges if pointer-base<=a<end-base]} if owned else {})}
    methods={};slots={}
    for name in ('GetValue','Deserialize','set___paramTarget__','set___path__'):
        found=[m for m in md.methods_for(md.types[wrapper.type_definition]) if md.string(m.name_index)==name]
        scalar.need(LABEL,'oneMethod:'+name,1,len(found));method=found[0];pointer=image.method_pointer_va(method)
        methods[name]={'methodIndex':method.index,**record(pointer,owned=name=='Deserialize',end=pointer+5 if name=='GetValue' else None)}
        if name=='Deserialize':primitive.reader_abi(image,ctx,method,wrapper)
        else:
            result=(wrapped_type,21,True) if name=='GetValue' else ('void',1,False)
            arguments=[('string',14,True)] if name=='set___path__' else [('int',8,False)] if name=='set___paramTarget__' else []
            scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,result,arguments,LABEL)
        if name.startswith('set___'):
            field=name[6:-2];rows=methods[name]['instructions']
            position=6 if field=='paramTarget' or bytes.fromhex(rows[3][1])==b'\x75\x06' else 4
            slots[field]=bytes.fromhex(rows[position][1])[-1]
            scalar.parameter_setter(image,rows,name=field,slot=slots[field],width=4,label=LABEL)
    occupied=[at for name,width in (('paramTarget',4),('path',8)) for at in range(slots[name],slots[name]+width)]
    scalar.need(LABEL,'disjointOwnedSlots',(12,True),(len(set(occupied)),all(16<=n<128 for n in occupied)))
    scalar.program(image,methods['GetValue']['instructions'],[b'\x48\x8b\x41\x10',b'\xc3'],LABEL+'.getter')
    targets,restore=caller_program(image,methods['Deserialize'],{n:methods['set___'+n+'__']['pointerRva'] for n in slots})
    offsets=scalar.reader_offsets(image,LABEL)
    header=record(base+targets['header']);primitive.object_header_source(image,header,offsets)
    integer=record(base+targets['paramTarget']);scalar.integer_source(image,integer,offsets,LABEL+'.integer')
    strings=pooled_source_helper.validate_on_image(image,base+targets['path'],inputs)
    ranges=[tuple(r['runtimeTriple'][:2]) for r in unwind.family(methods['Deserialize']['pointerRva'])['ranges']
            if r['runtimeTriple'][0]<=targets['null']<r['runtimeTriple'][1]]
    scalar.need(LABEL,'oneOwnedNullFragment',1,len(ranges));start,end=ranges[0]
    null={**record(base+targets['null'],end=base+end),'ownerRva':methods['Deserialize']['pointerRva'],
          'fragmentStartRva':start,'fragmentEndRva':end}
    if restore is None:
        scalar.program_extent(null['instructions'],null['window'],LABEL+'.null')
        scalar.program(image,null['instructions'],[b'\x48\x8b\xcb',b'\x48\xc7\x03\x00\x00\x00\x00',None,
            b'\x48\x8b\x5c\x24\x38',b'\x48\x8b\x74\x24\x40',b'\x48\x83\xc4\x20',b'\x5f',b'\xc3'],LABEL+'.null')
        barrier=targets['barrier']
    else:barrier=primitive.null_output_program(image,null,restore)
    rows=methods['set___path__']['instructions'];rva,encoded=rows[9 if bytes.fromhex(rows[3][1])==b'\x75\x06' else 7];raw=bytes.fromhex(encoded)
    scalar.need(LABEL,'pathBarrierTail',b'\xe9',raw[:1])
    scalar.need(LABEL,'sameBarrier',barrier,rva+5+int.from_bytes(raw[1:],'little',signed=True))
    return {'wrapperName':wrapper.name,'wrappedType':wrapped_type,'typeDefinition':wrapper.type_definition,
        'methods':methods,'ownedFieldSlots':slots,'targets':targets,'headerSource':header,'int32Source':integer,
        'readerFieldOffsets':offsets,'pooledSource':strings,'nullBranch':null,'barrierTargetRva':barrier,
        'evidenceBoundary':{'direct':'Closed typed wrapper, ordinary ABI, owned Int32 and reference setters, complete mc2 caller, buffered header/Int32 source, pooled path and unwind-owned null output program.',
            'conditional':'Initialized compatible nonnull wrapper/holder, disjoint storage, sufficient buffers and matching StringPool; ABI-preserving callees and barrier.',
            'unresolved':['cold refill/allocation paths','live/default provider or holder selection','enclosing owner and corpus admission']}}
