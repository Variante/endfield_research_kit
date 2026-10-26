"""Offline ASCII source for Patrol's actual cached Encoding and virtual calls.

The cached object's live slot20 and slot21 targets and MethodInfos must select
these independently owned UTF8 methods. Nominal declarations do not observe or
establish those runtime selections. Unicode and cold cache/setup are excluded.
"""
import json
from scripts.game_data.memorypack import leveldata_patrol_encoding_programs as paths

SCHEMA='endfield.story-patrol-encoding-ascii-sources.v1'
ENCODING='System.Text.Encoding'
UTF8='System.Text.UTF8Encoding'
ENDIAN='System.BitConverter'
STRING='string'


def need(check,condition,detail=None):
    if not condition:raise ValueError('patrolEncodingSources.'+check+(':'+str(detail)[:500]if detail is not None else''))


def norm(value):return json.loads(json.dumps(value))


def same(left,right):return json.dumps(left,sort_keys=True,separators=(',',':'))==json.dumps(right,sort_keys=True,separators=(',',':'))


def packet(image,at):
    from scripts.game_data.memorypack.leveldata_patrol_checkpoint_helper_sources import packet as owned
    return owned(image,at)


def raw(own,base):
    from scripts.game_data.memorypack.leveldata_patrol_checkpoint_helper_sources import verify_packet,regions
    verify_packet(own);return regions(own,base)


def _programs(p):
    base=p['imageBase'];h=p['helpers'];rr={k:raw(v,base)for k,v in h.items()}
    getter=paths.cached_getter_program(rr['getter'],base+h['getter']['entryRva'])
    wrappers=[paths.string_wrapper_program(rr['stringGetBytes'],base+h['stringGetBytes']['entryRva'],length=n)for n in range(128)]
    internal=[paths.ascii_internal_program(rr['internalGetBytes'],base+h['internalGetBytes']['entryRva'],length=n,source_alignment=a)for n in range(128)for a in(0,2)]
    # The owned bytes are replayed for every finite case. Repeated byte walks
    # are omitted from the presentation; no digest substitutes for that replay.
    for g in wrappers[1:]:g.pop('selectedBytes')
    for g in internal:g.pop('selectedBytes')
    return norm(dict(getter=getter,stringWrappers=wrappers,ascii=internal))


def _sites(programs):
    result={}
    def add(owner,u,name=None):
        value=dict(owner=owner,cellVa=u['cellVa'],typeName=name,role=u.get('role'))
        need('one-owned-site',u['instructionVa']not in result or result[u['instructionVa']]==value)
        result[u['instructionVa']]=value
    for u in programs['getter']['classUsages']:add('getter',u,u['typeName'])
    for u in programs['stringWrappers'][0]['contextUsages']:add('stringGetBytes',u)
    for g in programs['ascii']:
        for u in g['classUsages']:add('internalGetBytes',u,u['typeName'])
    return result


def _field_metadata(image,ctx,name):
    from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
    td=ctx.index.types[name];md=image.metadata;fs=list(md.fields_for(td));offsets=runtime_type_field_offsets(md,image.pe,image.registration,td.index)if fs else{}
    return dict(typeDefinition=td.index,parent=ctx.parent(name),fields=[dict(name=md.string(f.name_index),typeName=ctx.type_name(f.type_index),
        offset=offsets.get(md.string(f.name_index)),static=bool(ctx.field_attributes(f.type_index)&16))for f in fs])


def _method(image,ctx,owner,params,*,slot,static=False,name='GetBytes'):
    md=image.metadata;td=ctx.index.types[owner];found=[]
    for m in md.methods_for(td):
        if md.string(m.name_index)!=name or [ctx.type_name(v.type_index)for v in md.parameters_for(m)]!=params:continue
        found.append(m)
    need('unique-owned-method:'+owner+'.'+name,len(found)==1);m,=found
    need('owned-method-declaration-and-slot',m.declaring_type==td.index and m.generic_container_index==-1
        and m.parameter_count==len(params)and bool(m.flags&16)==static and m.slot==slot)
    return dict(method=[m.index,owner,name,image.method_pointer_va(m)-image.pe.image_base],parameters=params,
        returnType=ctx.type_name(m.return_type),slot=m.slot,static=static)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp import ready_context_sources
    from scripts.game_data.memorypack import leveldata_patrol_data_path_sources as parent,leveldata_patrol_class_preparation_sources as preparation
    _publication_gate(image,pins);base=image.pe.image_base;source=parent.derive(image,pins);ctx=NativeReferenceContext(image)
    methods=dict(getter=_method(image,ctx,ENCODING,[],slot=65535,static=True,name='get_UTF8'),
        stringGetBytes=_method(image,ctx,UTF8,['string','int','int','byte[]','int'],slot=20),
        internalGetBytes=_method(image,ctx,UTF8,['char*','int','byte*','int','System.Text.EncoderNLS'],slot=21))
    need('actual-data-caller-getter',methods['getter']['method'][3]==source['proof']['children']['getEncoding']['entryRva'])
    helpers={role:packet(image,base+m['method'][3])for role,m in methods.items()}
    proof=dict(imageBase=base,dataPathSource=source,methods=methods,helpers=helpers,
        fields={name:_field_metadata(image,ctx,name)for name in(ENCODING,UTF8,ENDIAN,'System.String')})
    programs=_programs(proof);proof['programs']=programs
    proof['requiredRuntimeCallbacks']={role:dict(logicalSlot=methods[role]['slot'],callbackTargetRva=methods[role]['method'][3],callbackMethodDefinition=methods[role]['method'][0],methodInfoMethodDefinition=methods[role]['method'][0],declaringType=UTF8,selectionObserved=False)for role in('stringGetBytes','internalGetBytes')}
    w=programs['stringWrappers'][0];calls={c['role']:c['targetVa']for c in w['calls']}
    proof['readyContext']=ready_context_sources.derive(image,pins,entry=calls['readyContext'])
    proof['classPreparation']=preparation.derive(image,pins,target=calls['prepareEncodingClass'])
    proof['typedRequests']={str(at-base):derive_typed_usage_context(image,at-base,label='patrolEncoding.actualContext')for at in _sites(programs)}
    value=norm(dict(schema=SCHEMA,status='validated-conditional-patrol-ASCII-encoding-sources',nativeInputs=pins,proof=proof,
        cachedUTF8GetterSourceProved=True,actualSlot20And21SourcesProved=True,asciiOutputByteMappingProved=True,
        lengthRange=[0,127],utf16AlignmentModulo4=[0,2],inputCodeUnitRange=[0,127],wholeUnicodeEncodingProved=False,
        runtimeCallbackSelectionObserved=False,liveStringOrBufferObserved=False,runtimeInvocationObserved=False,playbackProved=False,
        conditions=['The cached Encoding reference is nonnull and stable; its actual slot20 callback and MethodInfo select the owned UTF8 string method. Its actual slot21 callback and MethodInfo select the owned UTF8 internal method. These identities are explicit runtime conditions, not nominal-to-live aliases.',
            'Nonnull compatible UTF16 string of length0..127, every code unit0..127, index0/count equals string length. Nonnull disjoint byte array of sufficient capacity and byte index0. Input pointer alignment is0 or2 modulo4; relevant low32 pointer ranges do not wrap.',
            'The exact Encoding static cache, UTF8 classes, contexts and metadata are ready and stable. The packed path requires the actual BitConverter little-endian static flag true; EncoderNLS state is null. Normal Win64 ABI and valid disjoint storage.',
            'This source proof does not execute an Encoding object, observe pool capacity/callbacks, load assets, or establish the Unicode/cold/fallback/exceptional alternatives.']))
    validate(value,pins);_publication_gate(image,pins);return value


def validate(value,pins):
    from scripts.game_data.il2cpp import ready_context_sources
    from scripts.game_data.memorypack import leveldata_patrol_data_path_sources as parent,leveldata_patrol_class_preparation_sources as preparation
    need('source-envelope',value.get('schema')==SCHEMA and value.get('nativeInputs')==pins and value.get('status')=='validated-conditional-patrol-ASCII-encoding-sources'
        and all(value.get(k)is True for k in('cachedUTF8GetterSourceProved','actualSlot20And21SourcesProved','asciiOutputByteMappingProved'))
        and all(value.get(k)is False for k in('wholeUnicodeEncodingProved','runtimeCallbackSelectionObserved','liveStringOrBufferObserved','runtimeInvocationObserved','playbackProved'))
        and same(value.get('lengthRange'),[0,127])and same(value.get('utf16AlignmentModulo4'),[0,2])and same(value.get('inputCodeUnitRange'),[0,127]))
    p=value['proof'];base=p['imageBase'];need('image-base',type(base)is int and base>=1<<32)
    parent.validate(p['dataPathSource'],pins);ready_context_sources.validate(p['readyContext'],pins);preparation.validate(p['classPreparation'],pins)
    need('finite-owned-helper-and-method-roles',set(p['helpers'])==set(p['methods'])=={'getter','stringGetBytes','internalGetBytes'})
    programs=_programs(p);need('all-finite-ASCII-cases-replayed',same(programs,p['programs']))
    source=p['dataPathSource']['proof'];caller=source['programs'][-1];w=programs['stringWrappers'][0]
    g=p['helpers']['getter'];child=source['children']['getEncoding']
    need('same-fresh-parent-complete-getter-source',g==dict(entryRva=child['entryRva'],windows=child['sourceWindows'],regions=[[a-base,h.upper()]for a,h in child['sourceRegions']]))
    need('actual-parent-getter-E8-and-virtual20',caller['encodingGetterTargetVa']==base+g['entryRva']
        and caller['encodingCallbackClassOffset']==640 and caller['encodingMethodInfoClassOffset']==648)
    for role,owner,params,slot,static,ret,name in(('getter',ENCODING,[],65535,True,ENCODING,'get_UTF8'),
        ('stringGetBytes',UTF8,['string','int','int','byte[]','int'],20,False,'int','GetBytes'),
        ('internalGetBytes',UTF8,['char*','int','byte*','int','System.Text.EncoderNLS'],21,False,'int','GetBytes')):
        m=p['methods'][role];need('own-named-method-identity:'+role,m['method'][1:3]==[owner,name]
            and type(m['method'][0])is int and m['method'][0]>=0 and m['method'][3]==p['helpers'][role]['entryRva']
            and same(m['parameters'],params)and type(m['slot'])is int and m['slot']==slot and m['static']is static and m['returnType']==ret)
    need('explicit-exact-runtime-callback-and-MethodInfo-conditions',same(p['requiredRuntimeCallbacks'],{role:dict(logicalSlot=p['methods'][role]['slot'],callbackTargetRva=p['methods'][role]['method'][3],callbackMethodDefinition=p['methods'][role]['method'][0],methodInfoMethodDefinition=p['methods'][role]['method'][0],declaringType=UTF8,selectionObserved=False)for role in('stringGetBytes','internalGetBytes')}))
    for c in w['calls']:
        role=c['role'];actual=p['readyContext']['actualEntryRva']if role=='readyContext'else p['classPreparation']['actualEntryRva']
        need('actual-normal-wrapper-helper-E8',c['targetVa']==base+actual)
    need('same-actual-parent-Encoding-preparation',p['classPreparation']['actualEntryRva']==source['children']['prepareEncodingClass']['actualEntryRva'])
    need('slot21-source-and-MethodInfo-arguments',w['internalCallbackClassOffset']==656 and w['internalMethodInfoClassOffset']==664
        and w['internalLogicalSlot']==21 and w['internalArguments']['stack6']==0)
    fields=p['fields'];need('finite-owned-nominal-metadata',set(fields)=={ENCODING,UTF8,ENDIAN,'System.String'}
        and fields[UTF8]['parent']==ENCODING and all(type(v['typeDefinition'])is int and v['typeDefinition']>=0 for v in fields.values()))
    def own_field(owner,offset,typename,static):
        found=[f for f in fields[owner]['fields']if type(f.get('offset'))is int and f['offset']==offset and f['typeName']==typename and f['static']is static]
        need('unique-owned-field:'+owner+':'+str(offset),len(found)==1);return found[0]
    need('own-named-static-and-string-fields',[own_field(ENCODING,32,ENCODING,True)['name'],own_field(ENDIAN,0,'bool',True)['name'],own_field('System.String',16,'int',False)['name'],own_field('System.String',20,'char',False)['name']]==['utf8Encoding','IsLittleEndian','_stringLength','_firstChar'])
    sites=_sites(programs);need('all-and-only-owned-typed-sites',set(p['typedRequests'])=={str(at-base)for at in sites})
    for at,s in sites.items():
        u=p['typedRequests'][str(at-base)];cells={a+i:b for a,bb in raw(p['helpers'][s['owner']],base)for i,b in enumerate(bb)}
        try:encoded=bytes(cells[at+i]for i in range(7))
        except KeyError as error:raise ValueError('patrolEncodingSources.unowned-typed-site')from error
        need('exact-complete-actual-context-load',u['instructionRva']==at-base and u['usageCellRva']==s['cellVa']-base
            and encoded.hex().upper()==u['instructionHex'].upper()and encoded[:3]in(bytes.fromhex('488b05'),bytes.fromhex('488b0d'))
            and at+7+int.from_bytes(encoded[3:],'little',signed=True)==s['cellVa'])
        encoded_usage=int.from_bytes(bytes.fromhex(u['usageRawHex']),'little');tag=u['tag'];index=(encoded_usage&((1<<29)-1))>>1
        need('actual-uninitialized-context-carrier',type(tag)is int and tag in(1,6)and encoded_usage&1==1 and encoded_usage>>29==tag)
        if s['typeName']is not None:
            t=bytes.fromhex(u['typeRawHex']);need('same-own-class-descriptor',tag==1 and u['typeName']==s['typeName']
                and type(u['typeIndex'])is int and u['typeIndex']==index and len(t)==16 and t[10]==18
                and int.from_bytes(t[:8],'little')==fields[s['typeName']]['typeDefinition'])
        elif tag==6:
            expected={'spanImplicit':('System.Span`1','op_Implicit',['byte'],[]),'memoryReference':('System.Runtime.InteropServices.MemoryMarshal','GetReference',[],['byte'])}[s['role']]
            need('actual-method-context-carrier',type(u['methodSpecIndex'])is int and u['methodSpecIndex']==index
                and len(u['methodSpec'])==3 and all(type(v)is int for v in u['methodSpec'])
                and same([u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']],list(expected)))
        else:need('actual-class-context-carrier',type(u['typeIndex'])is int and u['typeIndex']==index)
    return dict(cachedUTF8GetterSourceProved=True,actualSlot20And21SourcesProved=True,asciiOutputByteMappingProved=True,
        lengthRange=[0,127],utf16AlignmentModulo4=[0,2],inputCodeUnitRange=[0,127],wholeUnicodeEncodingProved=False,
        runtimeCallbackSelectionObserved=False,runtimeInvocationObserved=False,playbackProved=False)
