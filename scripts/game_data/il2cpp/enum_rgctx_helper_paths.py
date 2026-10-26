"""Own token search and bounded concrete-argument depth in class RGCTX setup.

The actual token comparator is its exact five-byte DWORD subtraction/return,
with no invented unwind extent. The complete actual binary-search family has
independent instruction/control/frame checks. Each selected formatter query
replays its exact source path over the freshly read sorted unique module token
array, including actual odd/even midpoint arithmetic and final singleton path.
The actual fifth argument remains the independently proved comparator. Token
differences are bounded to signed DWORD, avoiding subtraction-order aliases.

The actual generic-depth helper has a complete owned graph/frame and only two
exact recursive self calls. Its null path returns zero; count1 nonconstructed
argument path returns one. The entire source preserves EDX, conditional on
normally returning recursive calls preserving it by the same body. No recursive
termination is inferred. Initialized module/context/parameter state, stable
metadata and helpers/guards, nonoverflowing address arithmetic and disjoint
storage remain conditions. No live RGCTX, callback or enum wire admission.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-rgctx-helper-paths.v1'
LABEL='enumRgctxHelperPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def comparator_program(regions,entry):
    g=BytesPath(regions,entry);g.take('8b01','2b02','c3')
    return dict(selectedBytes=g.seen,entry=entry,tokenBytes=4,left='actual key token DWORD',right='actual candidate token DWORD',
        returnsSignedDwordDifference=True,nonnullStableReadableInputsRequired=True,
        boundedDifferenceWithinSignedDwordRequired=True,entryRspUnchanged=True,fullUnwindExtentProved=False)


def search_program(regions,entry,*,tokens,token):
    need('bounded-literal-sorted-unique-token-array',type(tokens)is list and 0<len(tokens)<=1_000_000
        and all(type(v)is int and 0<=v<1<<32 for v in tokens)and tokens==sorted(set(tokens)))
    need('exact-present-token-and-nonoverflowing-comparison',type(token)is int and token in tokens
        and max(tokens[-1]-token,token-tokens[0])<1<<31)
    g=BytesPath(regions,entry);g.take('488bc4','48895808','48896810','48897018','48897820','4155','4156','4157',
        '4883ec20','33db','4d8bf1','498be8','488bf2','4c8be9','4885d2');g.branch('75',True,1)
    g.take('4d85f6');g.branch('74',False,1)
    g.take('48395c2460');g.branch('74',False,1)
    g.take('488b4c2460');guard=g.relative('e8')
    g.take('488d7dff','490faffe','4803fe','483bf7');g.branch('77',False,1)
    loop=g.at;low=0;high=len(tokens)-1;count=len(tokens);comparisons=[]
    while True:
        need('bounded-search-state',0<=low<=high<len(tokens)and count==high-low+1 and len(comparisons)<32)
        half=count>>1;g.take('4c8bfd','49d1ef');g.branch('74',half==0,1)
        if half:
            g.take('40f6c501','498bcd','498d6fff','490f45ef','488bdd','490fafde','4803de','488bd3','ff542460','85c0')
            mid=low+(half if count&1 else half-1);difference=token-tokens[mid]
            comparisons.append(dict(index=mid,candidateToken=tokens[mid],signedDifference=difference,count=count))
            g.branch('74',difference==0,1)
            if difference==0:break
            g.branch('79',difference>=0,1)
            if difference<0:
                g.take('488bfb','492bfe');g.jump('eb',1);high=mid-1;count=half if count&1 else half-1
            else:g.take('4a8d3433','498bef');low=mid+1;count=half
            g.take('483bf7');g.branch('76',True,1)
            need('same-binary-search-loop',g.at==loop)
        else:
            g.take('33db','4885ed');g.branch('74',False,1)
            g.take('488bd6','498bcd','ff542460','33c9','488bde','85c0','480f45d9')
            need('singleton-is-exact-requested-token',tokens[low]==token)
            comparisons.append(dict(index=low,candidateToken=tokens[low],signedDifference=0,count=count));break
    g.take('488bc3','488b5c2440','488b6c2448','488b742450','488b7c2458','4883c420','415f','415e','415d','c3')
    return dict(selectedBytes=g.seen,entry=entry,token=token,inputRangeCount=len(tokens),comparisons=comparisons,
        selectedRangeIndex=comparisons[-1]['index'],elementBytes=12,fifthArgumentEntryRspOffset=40,
        actualComparatorStackOffset=96,actualIndirectGuard=guard,actualComparatorArguments=dict(rcx='unchanged input key',rdx='actual selected candidate'),
        returnedRangeAddress='unchanged incoming table base + selectedRangeIndex*12',
        normalGuardAndComparatorEffectsRequired=True,stableActualTableAndKeyRequired=True,
        nonoverflowingPointerGeometryRequired=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rbp','rsi','rdi','r13','r14','r15'])


def depth_program(regions,entry,*,null):
    need('literal-depth-path',type(null)is bool)
    g=BytesPath(regions,entry);g.take('4055','4883ec20','488be9','4885c9');g.branch('75',not null,1)
    if null:g.take('33c0','4883c420','5d','c3')
    else:
        g.take('48895c2430','4c89742448','4533f6','418bde','3919');g.branch('76',False,1)
        g.take('4889742438','48897c2440','0f1f4000','0f1f840000000000');loop=g.at
        g.take('488b4508','488b0cd8','80790a15');g.branch('75',True,1)
        g.take('8b4500','48ffc3','483bd8');need('same-count1-depth-backedge',g.relative('72',1)==loop)
        g.take('488b7c2440','488b742438','488b5c2430','418d4601','4c8b742448','4883c420','5d','c3')
    return dict(selectedBytes=g.seen,entry=entry,inputInstantiationNull=null,
        selectedCount=None if null else 1,argumentKindMustDifferFrom21=not null,
        returnedEax=0 if null else 1,selectedPathHasNoCalls=True,edxPreserved=True,
        entryRspRestored=True,nonvolatilesRestored=['rbp']if null else['rbx','rbp','rsi','rdi','r14'])


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_class_rgctx_paths import derive as context_source
    from scripts.game_data.il2cpp.enum_constructed_class_paths import _json_set
    from scripts.game_data.il2cpp.enum_reflection_dispatch_paths import decode
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import complete_program
    from scripts.game_data.il2cpp.class_enum_fields_control import _no_register_write
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.levelscript_two_routes_native import _window
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);prior=context_source(image,pins,**arguments);prefix=prior['proof']['selectedPrefix']
    helper_entries=dict(search=prefix['actualRangeSearch'],depth=prior['proof']['selectedMethodSlots'][0]['actualDepthHelper'])
    families={};bodies={}
    for role,target in helper_entries.items():
        body=owned(image,target);rows=[]
        for at,raw in body['regions']:rows+=checked_rows(decode(image.mapper,raw,at),raw,LABEL)
        rows.sort(key=lambda row:int(row['va'],16));recursive={}
        if role=='depth':
            from scripts.game_data.il2cpp.initializer_control import control_transfer
            recursive={int(row['va'],16):target for row in rows if control_transfer(row).get('kind')=='call'}
            need('exact-two-recursive-depth-calls-only',len(recursive)==2 and all(control_transfer(row)['target']==target
                for row in rows if int(row['va'],16)in recursive))
            _no_register_write(rows,0,len(rows),'rdx',calls_allowed=True)
        graph,padding=complete_program(body['regions'],rows,target,recursive_calls=recursive)
        families[role]=dict(windows=body['windows'],control=graph,padding=padding);bodies[role]=body
    comparator=prefix['actualRangeComparator'];raw=image.pe.bytes_at_va(comparator,5)
    comparison=comparator_program([(comparator,raw)],comparator)
    md=image.metadata;queries={}
    for name,selected in prior['proof']['staticFormatterContexts'].items():
        c=selected['context'];module=image.modules[c['image']];count=image.pe.u32_at_va(module+64)
        need('bounded-current-exact-module-directory',0<count<=1_000_000)
        table=image.pe.u64_at_va(module+72);raw_ranges=image.pe.bytes_at_va(table,count*12)
        tokens=[int.from_bytes(raw_ranges[i:i+4],'little')for i in range(0,len(raw_ranges),12)]
        p=search_program(bodies['search']['regions'],helper_entries['search'],tokens=tokens,token=c['token'])
        at=p['selectedRangeIndex']*12;start=int.from_bytes(raw_ranges[at+4:at+8],'little',signed=True)
        slots=int.from_bytes(raw_ranges[at+8:at+12],'little',signed=True)
        need('actual-native-search-selects-same-static-formatter-context',(start,slots)==(c['start'],c['count']))
        queries[name]=dict(selectedSearch=p,moduleRangePointer=table,rangeCount=count,
            selectedRangeRawHex=raw_ranges[at:at+12].hex().upper(),contextStart=start,contextSlots=slots)
    depth=[depth_program(bodies['depth']['regions'],helper_entries['depth'],null=z)for z in(True,False)]
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(classContextSource=prior,completeFamilies=families,selectedTokenSearches=queries,
            tokenComparator=comparison,tokenComparatorWindow=_window(image,comparator,comparator+5,
                'Exact selected token comparator; no unwind extent claim'),selectedDepthPaths=depth,
            depthEdxPreservedByOwnCompleteRecursiveBodyConditional=True),
        actualFormatterTokenSearchAndSelectedDepthTransfersProved=True,actualInitializedRgctxOrCallbackIdentityProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own full actual search/depth families, exact token-comparator leaf, replayed actual sorted-module queries and selected null/concrete-count1 depth paths.',
            conditional=__doc__,structuralOnly='Runtime context source helpers.',
            unresolved=['actual initialized receiver/context and allocation/cache effects','nominal callback/provider binding',
                'concrete enum/list/parent/EOF'])),default=_json_set))
