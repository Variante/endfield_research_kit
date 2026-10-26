"""Offline normal hashing for the exact nested resource-handle value domain.

Ready metadata, cached classes, spare allocation storage, selected import ABI
and exact live callback/MethodInfo pairs are conditions, never observations.
"""
import hashlib
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import leveldata_patrol_value_hash_programs as paths

SCHEMA='endfield.story-patrol-value-hash-sources.v1'
HANDLE='Beyond.Resource.FAssetProxyHandle'
UNTRACKED='Beyond.Resource.FAssetProxyUntrackedHandle'
ID='Beyond.Resource.FAssetObjectID'
OBJECT='Beyond.Resource.FObjectHandle'
KIND='Beyond.Resource.EAssetProxyHandleType'
LOG='Beyond.ELogChannel'
DOMAIN={HANDLE:[('m_untrackedHandle',UNTRACKED,16,17)],
    UNTRACKED:[('m_handleObjectID','int',16,8),('m_assetProxyID',ID,20,17),('m_assetProxyObj',OBJECT,24,17),
        ('m_handleType',KIND,28,17),('m_logChannel',LOG,29,17),('m_mainVersion','int',32,8)],
    ID:[('<objectIntID>k__BackingField','int',16,8)],OBJECT:[('m_handleID','int',16,8)],
    KIND:[('value__','byte',16,5)],LOG:[('value__','byte',16,5)]}


def need(check,condition):
    if not condition:raise ValueError('patrolValueHashSources.'+check)


def norm(v):return json.loads(json.dumps(v))


def same(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))


def packet(image,at,span=None):
    from scripts.game_data.memorypack.leveldata_patrol_checkpoint_helper_sources import packet as owned
    if span is None:return dict(**owned(image,at),boundary='complete-native-owned-family')
    b=image.pe.bytes_at_va(at,span);rva=at-image.pe.image_base
    return dict(entryRva=rva,regions=[[rva,b.hex().upper()]],windows=[dict(startRva=rva,endRva=rva+span,
        sha256=hashlib.sha256(b).hexdigest().upper())],boundary='selected-span-no-physical-extent')


def raw(p,base):
    from scripts.game_data.memorypack.leveldata_patrol_checkpoint_helper_sources import verify_packet,regions
    verify_packet(p);return regions(p,base)


def method(image,ctx,owner,name):
    md=image.metadata;ms=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==name
        and m.parameter_count==(2 if name=='InternalGetHashCode'else 0)]
    need('unique-own-method:'+owner+'.'+name,len(ms)==1);m,=ms
    return m,dict(method=[m.index,owner,name,image.method_pointer_va(m)-image.pe.image_base],token=m.token,slot=m.slot,
        parameters=[ctx.type_name(p.type_index)for p in md.parameters_for(m)],returnType=ctx.type_name(m.return_type))


def fields(image,ctx):
    from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
    md=image.metadata;out={}
    for name in DOMAIN:
        td=ctx.index.types[name];offsets=runtime_type_field_offsets(md,image.pe,image.registration,td.index)
        own=[]
        for f in md.fields_for(td):
            ptr=ctx.type_pointer(f.type_index);b=image.pe.bytes_at_va(ptr,16)
            own.append(dict(name=md.string(f.name_index),typeName=ctx.type_name(f.type_index),offset=offsets[md.string(f.name_index)],
                kind=b[10],typeIndex=f.type_index,typePointer=ptr,typeRawHex=b.hex(),static=bool(ctx.field_attributes(f.type_index)&16)))
        out[name]=dict(typeDefinition=td.index,parent=ctx.parent(name),valueType=ctx.is_value_type(name),enum=ctx.is_enum(name),
            fields=[f for f in own if not f['static']],staticFields=[f for f in own if f['static']],instanceLayoutOnly=True,
            ownHashMethods=[dict(methodDefinition=m.index,slot=m.slot,parameters=m.parameter_count)
                for m in md.methods_for(td)if md.string(m.name_index)=='GetHashCode'])
    return out


def _programs(p):
    b=p['imageBase'];h=p['helpers'];rr={k:raw(v,b)for k,v in h.items()}
    def one(k,fn,**kw):return fn(rr[k],b+h[k]['entryRva'],**kw)
    return norm(dict(handle=one('internal',paths.internal),untracked=one('internal',paths.internal,field_kinds=(8,17,17,17,17,8)),
        boxes=[one('boxField',paths.box_field,payload_bytes=n)for n in(1,4,20)],readyFields=one('prepareFields',paths.ready_fields),
        readyClass=one('prepareArray',paths.ready_class),stackProbe=one('stackProbe',paths.stack_probe),
        newObjects=[one('newObject',paths.new_object,payload_bytes=n)for n in(1,4,20)],
        plain=one('allocatePlain',paths.allocate_plain),references=one('allocateReferences',paths.allocate_references),
        classFromType=one('classFromType',paths.class_from_type),ordinaryClass=one('ordinaryClass',paths.ordinary_class),
        definitionClass=one('definitionClass',paths.definition_class),initializedClass=one('classInit',paths.initialized_class),
        arrayClass=one('arrayClass',paths.array_class),arrayLookup=one('arrayLookup',paths.array_lookup),arrayFind=one('arrayFind',paths.array_find),
        typeHash=one('typeHash',paths.type_hash),typeEquals=one('typeEquals',paths.type_equals),
        assetIdHash=one('assetIdHash',paths.boxed_id_hash),objectHash=one('objectHash',paths.boxed_id_hash,asset=False),
        enumHash=one('enumHash',paths.enum_byte_hash),zero=[paths.zero_payload(rr['zero']+rr['zeroTable'],b+h['zero']['entryRva'],count=n)for n in(8,24)]))


def _links(g):
    for k in('handle','untracked'):
        for c in g[k]['calls']:yield c['role'],c['targetVa']
    for x in g['boxes']:
        for c in x['calls']:yield {'prepareClass':'prepareArray','copyPayload':'copy'}.get(c['role'],c['role']),c['targetVa']
    for x in g['newObjects']:
        for c in x['calls']:yield {'prepareClass':'prepareArray'}.get(c['role'],c['role']),c['targetVa']
    yield 'ordinaryClass',g['classFromType']['ordinaryClassTargetVa']
    yield 'definitionClass',g['ordinaryClass']['classDefinitionCall']['targetVa']
    yield 'arrayLookup',g['arrayClass']['lookupCall']['targetVa']
    yield 'arrayFind',g['arrayLookup']['findCall']['targetVa']
    for c in g['arrayFind']['calls']:yield c['role'],c['targetVa']


def _callbacks(p):
    h=p['helpers'];m=p['methods']
    return {name:dict(targetRva=h[role]['entryRva'],methodDefinition=m[methodRole]['method'][0],slot=2,
        boxedReceiver=True,selectedMethodInfoRequiredActualNominal=True,selectionObserved=False)
        for name,role,methodRole in((UNTRACKED,'wrapper','wrapper'),(ID,'assetIdHash','assetId'),(OBJECT,'objectHash','object'),
            (KIND,'enumHash','enum'),(LOG,'enumHash','enum'))}


def _imports(image,programs):
    pe=image.pe;b=pe.image_base;buf=pe.buf;optional=int.from_bytes(buf[60:64],'little')+24
    directory=int.from_bytes(buf[optional+120:optional+124],'little')
    sites=dict(thread=programs['handle']['sites']['threadGetterIatCellVa'],
        acquire=programs['arrayLookup']['lockIatCellVa'],release=programs['arrayLookup']['unlockIatCellVa']);found={}
    for n in range(256):
        at=b+directory+n*20;d=pe.bytes_at_va(at,20)
        if not any(d):break
        oft=int.from_bytes(d[:4],'little');ft=int.from_bytes(d[16:20],'little');dllAt=b+int.from_bytes(d[12:16],'little');dll=pe.c_string_at_va(dllAt)
        for i in range(20000):
            slot=b+(oft or ft)+i*8;v=pe.u64_at_va(slot)
            if not v:break
            iat=b+ft+i*8
            roles=[role for role,target in sites.items()if target==iat]
            if not roles:continue
            need('named-import-not-ordinal',v<1<<63);nameAt=b+v;name=pe.c_string_at_va(nameAt+2)
            for role in roles:
                need('one-selected-import:'+role,role not in found)
                found[role]=dict(dll=dll,name=name,index=i,iatCellVa=iat,descriptor=packet(image,at,20),
                    lookupSlot=packet(image,slot,8),dllName=packet(image,dllAt,len(dll)+1),functionName=packet(image,nameAt,len(name)+3))
    need('complete-selected-native-imports',set(found)==set(sites));return found


def _verify_imports(p):
    b=p['imageBase'];g=p['programs'];sites=dict(thread=g['handle']['sites']['threadGetterIatCellVa'],
        acquire=g['arrayLookup']['lockIatCellVa'],release=g['arrayLookup']['unlockIatCellVa'])
    need('finite-selected-imports',set(p['imports'])==set(sites))
    for role,name in(('thread','TlsGetValue'),('acquire','AcquireSRWLockShared'),('release','ReleaseSRWLockShared')):
        d=p['imports'][role];desc=raw(d['descriptor'],b)[0][1];slot=raw(d['lookupSlot'],b)[0][1]
        dll=raw(d['dllName'],b)[0][1];function=raw(d['functionName'],b)[0][1]
        oft=int.from_bytes(desc[:4],'little')or int.from_bytes(desc[16:20],'little');ft=int.from_bytes(desc[16:20],'little')
        need('exact-selected-OS-import:'+role,d['dll']=='KERNEL32.dll'and d['name']==name and type(d['index'])is int and 0<=d['index']<20000
            and d['iatCellVa']==sites[role]==b+ft+8*d['index']and b+d['lookupSlot']['entryRva']==b+oft+8*d['index']
            and b+d['dllName']['entryRva']==b+int.from_bytes(desc[12:16],'little')and dll==b'KERNEL32.dll\0'
            and int.from_bytes(slot,'little')==d['functionName']['entryRva']and function[2:]==name.encode()+b'\0')


def _copy(p,pins):
    from scripts.game_data.il2cpp import forward_copy_sources as copying
    from scripts.game_data.il2cpp.protocol import load_native_mapper
    from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH
    c=p['copy'];value=c['proof'];b=p['imageBase'];rr=raw(p['helpers']['copy'],b);mapper=load_native_mapper(NATIVE_MAPPER_PATH)
    need('own-copy-scope',value.get('schema')=='endfield.forward-copy-source.v1'and value.get('nativeInputs')==pins
        and type(value.get('maxBytes'))is int and value['maxBytes']==256 and value['entryRva']==p['helpers']['copy']['entryRva']
        and same(value['proof']['windows'],p['helpers']['copy']['windows']))
    rows=[r for a,s in rr for r in copying.decode(mapper,s,a)];tables={}
    for w in value['proof']['tables']:
        s=bytes.fromhex(w['rawHex']);need('copy-table-hash',len(s)==w['endRva']-w['startRva']and hashlib.sha256(s).hexdigest().upper()==w['sha256'])
        need('unique-copy-table',w['startRva']not in tables);tables[w['startRva']]=s
    rep=c['rep'];s=bytes.fromhex(rep['rawHex']);need('copy-leaf-hash',hashlib.sha256(s).hexdigest().upper()==rep['sha256']and len(s)==16
        and same({k:v for k,v in rep.items()if k!='rawHex'},value['proof']['repReachablePrefix']))
    actual=copying.prove(rr,b+value['entryRva'],rows=rows,tables=tables,rep_rows=copying.decode(mapper,s,b+rep['startRva']),image_base=b,max_bytes=256)
    need('full-copy-replay',same(actual,value['proof']['program']))


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp import forward_copy_sources as copying
    from scripts.game_data.memorypack import leveldata_patrol_retain_programs as wrapper,leveldata_patrol_class_preparation_sources as preparation
    _publication_gate(image,pins);ctx=NativeReferenceContext(image);b=image.pe.image_base;h={};methods={}
    def add(k,at,span=None):
        need('one-helper-target:'+k,k not in h or h[k]['entryRva']==at-b);h[k]=packet(image,at,span);return raw(h[k],b)
    def parse(k,fn,**kw):return fn(raw(h[k],b),b+h[k]['entryRva'],**kw)
    _,methods['wrapper']=method(image,ctx,'System.ValueType','GetHashCode');add('wrapper',b+methods['wrapper']['method'][3])
    w=wrapper.value_hash_objects(raw(h['wrapper'],b),b+h['wrapper']['entryRva'],count=1)
    add('internal',w['calls'][0]['targetVa']);g=parse('internal',paths.internal)
    for c in g['calls']:add(c['role'],c['targetVa'])
    g=parse('boxField',paths.box_field)
    for c in g['calls']:
        k={'prepareClass':'prepareArray','copyPayload':'copy'}.get(c['role'],c['role']);add(k,c['targetVa'])
    g=parse('classFromType',paths.class_from_type);add('ordinaryClass',g['ordinaryClassTargetVa'],19)
    g=parse('ordinaryClass',paths.ordinary_class);add('definitionClass',g['classDefinitionCall']['targetVa'],232)
    g=parse('newObject',paths.new_object)
    for c in g['calls']:add({'prepareClass':'prepareArray'}.get(c['role'],c['role']),c['targetVa'])
    g=parse('arrayClass',paths.array_class);add('arrayLookup',g['lookupCall']['targetVa'])
    g=parse('arrayLookup',paths.array_lookup);add('arrayFind',g['findCall']['targetVa'])
    g=parse('arrayFind',paths.array_find)
    for c in g['calls']:add(c['role'],c['targetVa'])
    # Actual zero helper's selected eight-byte table cell, not a fabricated extent.
    at=b+h['zero']['entryRva'];walk=BytesPath(raw(h['zero'],b),at)
    walk.take('488bc1','4c8bc9');zeroBase=walk.relative('4c8d15');walk.take('0fb6d2','49bb0101010101010101','4c0fafda','66490f6ec3','4983f80f')
    walk.branch('0f87',False);walk.take('0f1f00','4903c8','478b8c82');table=zeroBase+int.from_bytes(walk.read(4),'little');add('zeroTable',table+32,4)
    # Adjustor tokens are local to the owning metadata image. Foreign modules
    # with the same token are never candidates.
    modules=image.mapper.parse_codegen_modules(image.pe,image.code_registration);adjustors={}
    for name,role in((ID,'assetId'),(OBJECT,'object')):
        m,methods[role]=method(image,ctx,name,'GetHashCode');td=ctx.index.types[name]
        owners=[x for x in image.metadata.images if x.type_start<=td.index<x.type_start+x.type_count];need('one-owning-metadata-image',len(owners)==1)
        moduleName=image.metadata.string(owners[0].name_index);mod=modules[moduleName];count=mod['adjustorThunkCount']
        need('bounded-own-adjustor-table',type(count)is int and 0<count<=100000)
        table=image.pe.bytes_at_va(mod['adjustorThunksVa'],count*16);matches=[(i,table[i*16:(i+1)*16])for i in range(count)if int.from_bytes(table[i*16:i*16+4],'little')==m.token]
        need('unique-own-token-adjustor',len(matches)==1);index,row=matches[0];target=int.from_bytes(row[8:],'little')
        adjustors[name]=dict(moduleName=moduleName,moduleHeader=packet(image,mod['moduleVa'],40),tableRow=packet(image,mod['adjustorThunksVa']+index*16,16),
            tableIndex=index,tableCount=count,methodToken=m.token,methodDefinition=m.index,methodTargetRva=methods[role]['method'][3],adjustorTargetRva=target-b)
        add('assetIdHash'if name==ID else'objectHash',target,None if name==ID else 4)
    _,methods['enum']=method(image,ctx,'System.Enum','GetHashCode');add('enumHash',b+methods['enum']['method'][3],96)
    _,methods['internal']=method(image,ctx,'System.ValueType','InternalGetHashCode');add('nominalInternal',b+methods['internal']['method'][3],5)
    copier=copying.derive(image,pins,entry=b+h['copy']['entryRva'],max_bytes=256);rep=dict(copier['proof']['repReachablePrefix'])
    rep['rawHex']=image.pe.bytes_at_va(b+rep['startRva'],16).hex()
    p=dict(imageBase=b,helpers=h,methods=methods,fields=fields(image,ctx),adjustors=adjustors,copy=dict(proof=copier,rep=rep),
        coreTypes={name:dict(typeDefinition=ctx.index.types[name].index,byvalTypeIndex=ctx.index.types[name].byval_type_index,
            rawHex=image.pe.bytes_at_va(ctx.type_pointer(ctx.index.types[name].byval_type_index),16).hex())for name in('System.Object','System.Byte')},
        childClassPreparation=preparation.derive(image,pins,target=w['calls'][1]['targetVa']))
    p['programs']=_programs(p);p['requiredCallbacks']=_callbacks(p);p['imports']=_imports(image,p['programs'])
    v=norm(dict(schema=SCHEMA,status='validated-conditional-patrol-value-hash-sources',nativeInputs=pins,proof=p,
        selectedNativeFieldWalkAndBoxingEffectsProved=True,selectedFiniteNestedChildHashEffectsProved=True,
        runtimeInvocationObserved=False,actualCallbackSelectionObserved=False,actualHashValueObserved=False,playbackProved=False,
        conditions=['Same exact ready nominal value classes and stable field metadata, own runtime type-definition/cache rows, ordinary nonnullable instance field layouts and no replacements. Handle20 contains Untracked20; the latter boxes two four-byte IDs and two Byte-backed enums in original metadata order.',
            'Each actual slot2 callback and MethodInfo must select the independently named ValueType/Enum method or exact owning-image boxed adjustor source recorded here. No unboxed metadata method pointer is treated as a boxed callback.',
            'Same nonnull normal thread-state import result, balanced actual OS cache mutex imports, ready classes, cached System.Object[] class and valid cache hit. Actual callback/import identities and live state remain conditional.',
            'Committed disjoint stack and payload storage; same-size-class spare plain/reference blocks with sufficient rounded payload capacity, zero unused monitor/bounds/reference storage, disabled collection/profiling and no finalizers. Allocation/cache construction, exhausted pools, cold class initialization, nullable/static fields and replacement paths are not selected.',
            'Native seed is low32(class pointer>>3) XOR stored Int32 fields; ValueType wrapper XORs actual selected child hash results. This proves the finite normal byte effects, not a particular live hash value, loaded asset, retention success, event dispatch or playback.']))
    validate(v,pins);_publication_gate(image,pins);return v


def validate(value,pins):
    from scripts.game_data.memorypack import leveldata_patrol_retain_programs as wrapper,leveldata_patrol_class_preparation_sources as preparation
    need('envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-patrol-value-hash-sources'and value.get('nativeInputs')==pins
        and all(value.get(k)is True for k in('selectedNativeFieldWalkAndBoxingEffectsProved','selectedFiniteNestedChildHashEffectsProved'))
        and all(value.get(k)is False for k in('runtimeInvocationObserved','actualCallbackSelectionObserved','actualHashValueObserved','playbackProved')))
    p=value['proof'];b=p['imageBase'];h=p['helpers'];need('image-base',type(b)is int and b>=1<<32)
    expected={'wrapper','internal','prepareFields','stackProbe','boxField','arrayClass','prepareArray','allocateReferences','classFromType','newObject','copy',
        'ordinaryClass','definitionClass','allocatePlain','zero','classInit','arrayLookup','arrayFind','typeHash','typeEquals','zeroTable','assetIdHash','objectHash','enumHash','nominalInternal'}
    need('finite-owned-helper-family',set(h)==expected);g=_programs(p);need('complete-program-replay',same(g,p['programs']))
    for role,at in _links(g):need('actual-child-target:'+role,at==b+h[role]['entryRva'])
    nominal=BytesPath(raw(h['nominalInternal'],b),b+h['nominalInternal']['entryRva']);need('explicit-nominal-tail-source',nominal.relative('e9')==b+h['internal']['entryRva'])
    need('method-family',set(p['methods'])=={'wrapper','internal','assetId','object','enum'})
    for name,kind in(('System.Object',28),('System.Byte',5)):
        d=p['coreTypes'][name];need('own-core-type:'+name,type(d['typeDefinition'])is int and type(d['byvalTypeIndex'])is int
            and len(bytes.fromhex(d['rawHex']))==16 and bytes.fromhex(d['rawHex'])[10]==kind
            and int.from_bytes(bytes.fromhex(d['rawHex'])[:8],'little')==d['typeDefinition'])
    for k,owner,name in(('wrapper','System.ValueType','GetHashCode'),('internal','System.ValueType','InternalGetHashCode'),('assetId',ID,'GetHashCode'),('object',OBJECT,'GetHashCode'),('enum','System.Enum','GetHashCode')):
        m=p['methods'][k];need('method-nominal:'+k,m['method'][1:3]==[owner,name]and m['returnType']=='int'and type(m['method'][0])is int)
        if k in('wrapper','enum'):need('own-boxed-method-source',m['method'][3]==h['wrapper'if k=='wrapper'else'enumHash']['entryRva']and m['slot']==2)
        if k=='internal':need('own-nominal-internal-method',m['method'][3]==h['nominalInternal']['entryRva']and m['parameters']==['object','object[]']and m['slot']==65535)
        else:need('own-parameterless-hash-method',m['parameters']==[]and m['slot']==2)
    for name,fieldsExpected in DOMAIN.items():
        d=p['fields'][name];need('own-value-nominal-layout:'+name,d['valueType']is True and d['enum']is(name in(KIND,LOG))
            and d['parent']==('System.Enum'if name in(KIND,LOG)else'System.ValueType')and d['instanceLayoutOnly']is True
            and same([(f['name'],f['typeName'],f['offset'],f['kind'])for f in d['fields']],fieldsExpected)
            and all(f['static']is False and bytes.fromhex(f['typeRawHex'])[10]==f['kind']for f in d['fields']))
        hashes=[]if name not in(ID,OBJECT)else[dict(methodDefinition=p['methods']['assetId'if name==ID else'object']['method'][0],slot=2,parameters=0)]
        need('exact-inherited-or-own-hash-method:'+name,same(d['ownHashMethods'],hashes))
        for f in d['fields']:
            r=bytes.fromhex(f['typeRawHex']);need('exact-instance-type-attributes',len(r)==16 and not(int.from_bytes(r[8:10],'little')&16))
            if f['kind']==17:need('own-nested-value-type-index',int.from_bytes(r[:8],'little')==p['fields'][f['typeName']]['typeDefinition'])
    for name,role,helper in((ID,'assetId','assetIdHash'),(OBJECT,'object','objectHash')):
        a=p['adjustors'][name];header=raw(a['moduleHeader'],b)[0][1];row=raw(a['tableRow'],b)[0][1]
        need('own-image-adjustor-row',a['moduleName']=='Common.Beyond.dll'and type(a['tableIndex'])is int and 0<=a['tableIndex']<a['tableCount']
            and int.from_bytes(header[24:28],'little')==a['tableCount']and b+a['tableRow']['entryRva']==int.from_bytes(header[32:40],'little')+a['tableIndex']*16
            and int.from_bytes(row[:4],'little')==a['methodToken']==p['methods'][role]['token']
            and a['methodDefinition']==p['methods'][role]['method'][0]and a['methodTargetRva']==p['methods'][role]['method'][3]
            and int.from_bytes(row[8:],'little')==b+a['adjustorTargetRva']==b+h[helper]['entryRva'])
    need('exact-selected-callback-conditions',same(p['requiredCallbacks'],_callbacks(p)))
    _verify_imports(p)
    for count in(1,4):
        w=wrapper.value_hash_objects(raw(h['wrapper'],b),b+h['wrapper']['entryRva'],count=count)
        need('same-actual-native-hash',w['calls'][0]['targetVa']==b+h['internal']['entryRva'])
        preparation.validate(p['childClassPreparation'],pins)
        need('actual-child-class-preparation',all(c['targetVa']==b+p['childClassPreparation']['actualEntryRva']for c in w['calls']if c['role']=='prepareChildClass'))
    _copy(p,pins)
