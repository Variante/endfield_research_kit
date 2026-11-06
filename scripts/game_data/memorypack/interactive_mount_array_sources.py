"""NameMountPointDef's own buffered value16 array source; wire child separate."""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
TYPE='Beyond.Gameplay.View.NameMountPointDef'


def need(check,condition):
    if not condition:raise ValueError('interactiveMountArray.'+check)


def byref_program(regions,entry,offsets,*,count):
    need('finite-count-witness',type(count)is int and -1<=count<=3)
    g=BytesPath(regions,entry);symbols={};calls=[];callbacks=[];edges=[]
    def call(role):
        at=g.at;target=g.relative('e8');need('same-helper-'+role,role not in symbols or symbols[role]==target)
        symbols[role]=target;calls.append(dict(role=role,instructionVa=at,targetVa=target))
    c,r,a,u,total=(bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g.take('4053','55','57','4156','4157','4883ec40','4983783800','498bd8','4c8bf2','488be9');g.branch('75',True,1)
    g.take('837d'+r+'04');g.branch('7d',True,1)
    g.take('488b45'+c,'448b38','8b7d'+r,'83c7fc');g.branch('79',True,1)
    g.take('488345'+c+'04','8345'+a+'04','8345'+u+'04','897d'+r,
        '486345'+u,'488b4d'+total,'482bc8','4963c7','483bc8');g.branch('0f8c',False)
    g.take('4183ffff','0f95c0','84c0');g.branch('0f84',count==-1)
    provider_classes=[];initialized_types=[]
    if count==-1:
        g.take('33ff','498bce','49893e','4883c440','415f','415e','5f','5d','5b')
        need('null-reference-barrier-tail',g.relative('e9')>0)
    else:
        g.take('4c89a42480000000','4585ff');g.branch('0f84',count==0)
        if count==0:
            g.take('488b4b38','488b4908');call('empty')
            flag=g.relative('833d')+1;g.take('00','498906');g.branch('0f84',True)
        else:
            g.take('4889742478','4c89ac2488000000','49833e00');image_base=g.relative('4c8d25');g.branch('74',True,1)
            g.take('488b4338','488b4010','f6803801000001');g.branch('75',True,1)
            g.take('498bd7','488bc8');call('allocate')
            flag=g.relative('833d')+1;g.take('00','498906');g.branch('74',True,1)
            provider_classes.append(dict(site=g.at,cell=g.relative('488b0d')))
            g.take('83b9e000000000');g.branch('75',True,1)
            g.take('488b4338');g.relative('488d35');g.take('33ff','4c8b6818','4c896c2470','49397d38');g.branch('0f85',True)
            initialized_types.append(dict(site=g.at,cell=g.relative('488b0d')))
            g.take('498b5d38','488b1b','39b9e0000000');g.branch('75',True,1)
            g.take('33d2','488bcb');call('typeHandle')
            provider_classes.append(dict(site=g.at,cell=g.relative('488b0d')))
            g.take('4c8be8','39b9e0000000');g.branch('75',True,1)
            provider_ready=g.relative('40383d')+1;g.branch('0f85',True)
            provider_classes.append(dict(site=g.at,cell=g.relative('488b0d')))
            g.take('39b9e0000000');g.branch('75',True,1)
            g.take('498bcd');call('provider')
            g.take('488b742470','488bd8','4c8bac2488000000','488b4e38','488b4108','f6803801000001');g.branch('75',True,1)
            g.take('4885db');g.branch('0f84',False)
            g.take('488b0b','488bd0');call('assignable');g.take('84c0');g.branch('0f84',False)
            g.take('4585ff');g.branch('7e',False,1);g.take('660f1f440000');loop=g.at
            for index in range(count):
                need('same-loop-entry',g.at==loop)
                g.take('498b06','4885c0');g.branch('0f84',False)
                g.take('3b7818');g.branch('0f83',False)
                g.take('448bcf','4c8bc5','4983c102','488bd3','49c1e104','4c03c8')
                callbacks.append(g.at);call('dispatch')
                g.take('ffc7','413bff');edge=g.at;g.branch('7c',index+1<count,1);edges.append(edge)
            g.take('488b742478')
        g.take('4c8ba42480000000','4883c440','415f','415e','5f','5d','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newArray=True,
        symbols=symbols,helperCalls=calls,elementCallbackSites=callbacks,backedgeSites=sorted(set(edges)),
        elementManagedBytes=16,elementWireBytes=None,initiallyNullArrayRequired=True,entryRspRestored=True,
        arrayDataOffset=32,providerClasses=provider_classes,initializedTypes=initialized_types,
        headerBytes=4,elementGrammarAdmitted=False,wholeOwnerAdmitted=False)


def derive(image,pins,*,typed_request,call_target):
    return _derive(image,pins,typed_request=typed_request,call_target=call_target,inlined_front=False)


def derive_inlined_front(image,pins,*,typed_request,call_target):
    """Actual byref callee; the parent separately proves the inlined front.

    The request names the outer no-argument ReadArray. Its reciprocal context
    slot0 names the executed one-byref overload. This grants no parent local,
    zero initialization, argument transfer or source-pointer alias.
    """
    return _derive(image,pins,typed_request=typed_request,call_target=call_target,inlined_front=True)


def _derive(image,pins,*,typed_request,call_target,inlined_front):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,validate_generic_contexts,derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack import scalar_param_native as scalar,animation_state_array_sources as arrays
    from scripts.game_data.memorypack.array_reference_sources import validate_read_array_context
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    _publication_gate(image,pins);ctx=NativeReferenceContext(image);base=image.pe.image_base;td=ctx.index.types[TYPE]
    validate_typed_usage_context(image,typed_request,label='interactiveMountArray')
    need('own-closed-ReadArray',tuple(typed_request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
        ==(6,'MemoryPack.MemoryPackReader','ReadArray',[],[TYPE]))
    argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
    raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
    need('own-ordinary-value-element',raw[10:12]==b'\x11\x80'and int.from_bytes(raw[:8],'little')==td.index
        and ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)and td.generic_container_index<0)
    fields=[[image.metadata.string(f.name_index),*ctx.field(TYPE+'::'+image.metadata.string(f.name_index))[1:]]
        for f in image.metadata.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    need('own-MountPoint-and-name-layout',fields==[['mountPoint','Beyond.Gameplay.MountPoint',16],['name','string',24]])
    sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    need('own-boxed32-managed16',(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4))==(32,16))
    if inlined_front:
        front=None;fp=None;byref=owned(image,call_target)
    else:
        front=owned(image,call_target);fp=arrays.return_program(front['regions'],call_target)
        byref=owned(image,fp['byrefTargetVa'])
    offsets=scalar.reader_offsets(image,'interactiveMountArray')
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    programs=[byref_program(byref['regions'],byref['pointer'],offsets,count=n)for n in(-1,0,1,2,3)]
    induction=prove_induction(programs[1:],initial='33ff',increment='ffc7',comparison='413bff',counter='edi',
        saved_count='r15d',max_count=4096,mode_key='newArray',backedge_sites=programs[2]['backedgeSites'])
    symbols=programs[-1]['symbols'];sy=ContextSymbols(image)
    first=sy.context(typed_request['methodSpec'][0],is_method=True)
    second=sy.context(first['entries'][0]['methodSpec'][0],is_method=True)
    validate_generic_contexts(image,[first,second],label='interactiveMountArray')
    fm=image.metadata.methods[second['entries'][5]['methodSpec'][0]]
    declaration=arrays.formatter_declaration(image,ctx,fm,image.metadata.methods[first['definition']].declaring_type)
    closed=validate_read_array_context(image,[first,second],typed_request,GenericEntries(image),argument.type_pointer_va,fm.index,
        fail=lambda k,e,a:need(k,e==a))
    classes=[]
    for site in programs[-1]['providerClasses']:
        usage=derive_typed_usage_context(image,site['site']-base,label='interactiveMountArray.provider')
        need('own-provider-class',usage.get('tag')==1 and usage.get('typeName')=='MemoryPack.MemoryPackFormatterProvider');classes.append(usage)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.interactive-mount-point-byref-array-source.v1'if inlined_front else'endfield.interactive-mount-point-array-source.v1',nativeInputs=pins,
        typeName=TYPE+'[]',elementType=TYPE,elementValueType=True,elementManagedBytes=16,elementWireBytes=None,
        arrayReaderMethodDefinition=typed_request['methodSpec'][0],arrayReaderTargetRva=call_target-base,typedRequest=typed_request,
        resultAbi='void-byref-reference8'if inlined_front else'rax',countRange=[-1,4096],countLimit=4096,initiallyNullArrayRequired=True,actualSourceProved=True,
        elementGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(layout=dict(typeDefinition=td.index,fields=fields,managedBytes=16,referenceLaneOffsets=[8],paddingByteRanges=[[4,8]]),
            frontWindows=None if front is None else front['windows'],byrefWindows=byref['windows'],frontProgram=fp,programs=programs,
            induction=induction,arrayContext=closed,formatterDeclaration=declaration,providerClasses=classes,
            helperWindows={k:owned(image,target)['windows']for k,target in symbols.items()}),
        condition='Exact ready coherent nominal contexts and original selected callback, typed normal allocation/provider/cast effects, fresh null output and sufficient disjoint buffered storage. Wire child, runtime selection and enclosing parent remain separate.')))
