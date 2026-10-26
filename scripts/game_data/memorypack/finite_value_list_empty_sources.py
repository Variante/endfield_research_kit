"""Selected finite value-list null/empty source, independent of element grammar.

The exact closed BezierKnot ListFormatter is independently selected from its
current registration and actual typed ReadPackable caller. Its signed count
source consumes four bytes for both -1 and zero. The new-zero path constructs
the typed list with the owned static empty array; reused-zero increments the
version and clears its size without touching elements. Complete selected
returns restore all saved integer registers. The local 56-byte initialization
belongs to this formatter's managed temporary, and grants no element wire size.
No element callback runs. Initialized coherent closed contexts, a valid zeroed
fresh allocation or initially empty reused list, normal noninterfering context,
allocation, provider and disabled barrier helpers, sufficient buffered input
and disjoint storage remain conditions. Runtime formatter selection, positive
counts, element grammar, enclosing field/owner and physical EOF are unresolved.

Enums are deliberately absent from this finite admission. An Int32 underlying
field neither selects List<int> nor proves a shared-placeholder callback. An
exact nominal provider/callback/body join is required before adding one.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.skill_root_child_bindings import need

SCHEMA='endfield.finite-value-list-empty-sources.v1'
ELEMENTS={'UnityEngine.Splines.BezierKnot'}


def selected_program(regions,entry,offsets,s,*,count,new=False):
    need('finite-value-list-count-domain',True,type(count)is int and count in(-1,0)and type(new)is bool)
    need('finite-value-list-null-no-allocation',False,count==-1 and new)
    cur,rem,adv,used,total=(bytes((offsets[n],)).hex()for n in
        ('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g=BytesPath(regions,entry)
    g.take('4053','57','4154','4155','4157','4881ece0000000','0f57c0','33c0',
        '837a'+rem+'04','4d8bf9','4d8be8','4889442460','488bda',
        '0f11442430','0f11442440','0f11442450');g.branch('0f8c',False)
    g.take('488b43'+cur,'448b20','8b7b'+rem,'83c7fc');g.branch('0f88',False)
    g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,
        '486343'+used,'488b4b'+total,'482bc8','4963c4','483bc8');g.branch('0f8c',False)
    g.take('4889b42420010000','33f6','4183fcff');g.branch('0f84',count==-1)
    owner=None
    if count==-1:
        g.take('498bcd','49897500');g.call(s['barrier']);g.jump('eb',1)
    else:
        g.take('4889ac2410010000','4c89b42428010000','49397500');g.branch('0f85',not new)
        if new:
            g.take('498b4f20','33d2','488b89c0000000');g.call(s['context'])
            g.take('488bc8');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False)
            g.take('498b4f20','488b91c0000000','488b4a08','48397120');g.branch('0f84',False)
            g.take('4585e4');g.branch('0f88',False)
            g.take('498b4720','488b88c0000000','488b6908','488b4520','488b88c0000000');g.branch('0f84',True)
            g.take('33d2');g.call(s['context']);g.take('39b0e0000000');g.branch('0f84',False)
            g.take('488b4d20','33d2','488b89c0000000');g.call(s['context'])
            g.take('488b88b8000000','488b01');g.jump('e9')
            g.take('488d4f10','48894710');g.call(s['barrier'])
            g.take('498bcd','49897d00');g.call(s['barrier'])
        else:
            g.take('498b4720','498b7d00','488b88c0000000','488b4110','48397020');g.branch('75',True,1)
            g.take('ff471c','897718');g.jump('e9')
        owner=g.at;owner_cell=g.relative('488b0d')
        g.take('39b1e0000000');g.branch('0f84',False)
        g.take('498b4720','488b88c0000000','488b4918');g.call(s['provider'])
        g.take('4c8bf0','4585e4');g.branch('0f8e',True)
        g.take('488bac2410010000','4c8bb42428010000')
    g.take('488bb42420010000','4881c4e0000000','415f','415d','415c','5f','5b','c3')
    return dict(selectedBytes=g.seen,collectionCount=count,newList=new,headerBytes=4,
        signedCountBits=32,countRegister='r12d',readerRegister='rbx',outputRegister='r13',
        countAndReaderUpdatesUnchanged=True,elementCallbacks=0,providerResultUsed=False,
        providerOwnerUsage=None if owner is None else dict(instruction=owner,cell=owner_cell),
        returnedReference=0 if count==-1 else'exact selected typed list',
        originalListSizeRequired=None if count==-1 or new else 0,
        newAllocationZeroedRequired=count==0 and new,
        typedStaticEmptyArrayStored=count==0 and new,listItemsOffset=16,listCountOffset=24,listVersionOffset=28,
        existingZeroVersionIncremented=count==0 and not new,existingZeroElementsTouched=False,
        entryRspRestored=True,nonvolatilesRestored=['rbx','rdi','r12','r13','r15','rsi']+
            (['rbp','r14']if count==0 else[]),normalReturn=True,elementWireBytes=None)


def derive(image,pins,*,typed_request,call_target,element_type):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.skill_value_list_context import derive as context_source
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack import int_list_sources,scalar_param_native as scalar
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    _publication_gate(image,pins)
    need('finite-value-list-exact-element',True,element_type in ELEMENTS)
    need('finite-value-list-literal-parent-target',True,type(call_target)is int and call_target>image.pe.image_base)
    context,body=context_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=element_type)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);rows=body['rows'];s={}
    for role,before,after in(('context','mov rcx, [rcx+0xc0]',None),
            ('allocate','mov rcx, rax','mov rdi, rax'),
            ('provider','mov rcx, [rcx+0x18]',None),('barrier','mov [r13+0x0], rsi',None)):
        targets={control_transfer(r)['target']for i,r in enumerate(rows)
            if i and i+1<len(rows)and bytes.fromhex(r['bytes'])[:1]==b'\xe8'
            and rows[i-1]['text']==before and(after is None or rows[i+1]['text']==after)}
        need('finite-value-list-unique-source-helper:'+role,1,len(targets));s[role],=targets
    offsets=scalar.reader_offsets(image,'finiteValueListEmpty');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    programs=[selected_program(body['regions'],body['pointer'],offsets,s,count=-1)]+[
        selected_program(body['regions'],body['pointer'],offsets,s,count=0,new=new)for new in(False,True)]
    sites={p['providerOwnerUsage']['instruction']for p in programs if p['providerOwnerUsage']is not None}
    need('finite-value-list-one-provider-owner',1,len(sites));site,=sites
    owner=derive_typed_usage_context(image,site-base,label='finiteValueListEmpty.providerOwner')
    need('finite-value-list-named-provider-owner',(1,'MemoryPack.MemoryPackFormatterProvider'),(owner['tag'],owner['typeName']))
    resolver=_load('levelscript_int_list_native.json',pins)['bodies']['contextResolver']
    need('finite-value-list-actual-context-resolver',resolver['entryRva'],s['context']-base)
    image.check_windows(resolver['windows'],label='finiteValueListEmpty.contextResolver')
    resolver_program=int_list_sources.initialized_class(
        [(base+w['startRva'],image.window_bytes(w))for w in resolver['windows']],s['context'],indexed=True)
    barrier_windows,barrier,_=_fast_barrier(image,s['barrier'])
    cap=dict(elementType=element_type,elementValueType=True,elementEnum=False,closedListType=context['closedListType'],
        nullable=True,collectionCounts=[-1,0],headerBytes=4,countLimit=0,positiveCountsAdmitted=False,
        elementCapability=None,elementGrammarAdmitted=False,elementCallbacksAdmitted=False,elementWireBytes=None,
        packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-finite-empty-value-list',nativeInputs=pins,
        capability=cap,proof=dict(context=context,programs=programs,providerOwner=owner,
            sourceWindows=body['windows'],sourceHelperRvas={k:v-base for k,v in s.items()},
            contextResolver=resolver,contextResolverProgram=resolver_program,
            barrierWindows=barrier_windows,barrierProgram=barrier,
            constructorProfile='actual inlined zero-capacity construction; owned capacity/empty-array contexts',
            clearProfile='actual inlined initially-empty size/version update; no element clear callback'),
        evidenceBoundary=dict(exact='Exact nominal closed non-enum value-list entry/context and actual ReadPackable parent target; complete signed count -1/new-zero/reused-zero cursor, output, inline constructor/Clear and return programs.',
            conditional=__doc__,structuralOnly='Stored nullable empty list; no positive element representation.',
            unresolved=['actual parent field/output/cursor join','positive counts and element grammar','enum nominal provider/callback selection','runtime formatter selection','cold/refill/malformed paths','whole owner/physical EOF']))))
