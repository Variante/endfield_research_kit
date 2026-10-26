"""Named setter numerical choice, typed local store and full selected returns."""
from scripts.game_data.damage_snapshot_cache_flow import _require


def check_setter_rows(rows, pointer, fields, providers):
    from scripts.game_data.il2cpp.context import relative_branch_target
    _require(len(rows)==50,'poise-setter-row-count',50,len(rows))
    raw=[bytes.fromhex(x['bytes']) for x in rows];at=pointer
    for row,b in zip(rows,raw):
        _require(int(row['va'],16)==at,'poise-setter-contiguous',hex(at),row['va']);at+=len(b)
    poise=fields['poise'];controller=fields['controller']
    _require(all(type(v) is int and 0<=v<2**31 for v in (poise,controller)),
             'poise-setter-field-displacements','nonnegative signed disp32',fields)
    exact={0:'4053',1:'4883ec40',2:'488bd9',3:'0f297c2420',5:'33d2',6:'0f28f9',8:'84c0',
        10:'488b8b'+controller.to_bytes(4,'little').hex(),11:'4885c9',13:'33d2',15:'84c0',
        17:'0f29742430',18:'33d2',19:'488bcb',22:'0f28f0',23:'83b9e000000000',
        26:'0f28d6',27:'0f57c9',28:'0f28c7',31:'0f28d0',
        32:'f30f5c93'+poise.to_bytes(4,'little').hex(),33:'0f28742430',35:'0f2fca',
        37:'0f287c2420',38:'4883c440',39:'5b',40:'c3',41:'0f287c2420',
        42:'f30f1183'+poise.to_bytes(4,'little').hex(),43:'4883c440',44:'5b',45:'c3',49:'cc'}
    for n,form in exact.items():_require(raw[n].hex()==form,'poise-setter-instruction',[n,form],[n,raw[n].hex()])
    _require(len(raw[4])==5 and raw[4][0]==0xb9,'poise-setter-patch-id','complete Int32 immediate',raw[4].hex())
    for n,prefix,size in ((21,'488b0d',7),(25,'4c8b0d',7),(30,'f30f100d',8),(34,'0f5415',7)):
        _require(len(raw[n])==size and raw[n].hex().startswith(prefix),'poise-setter-rip-instruction',[prefix,size],raw[n].hex())
    calls={}
    for n,key in ((7,'patch'),(14,'recovery'),(20,'maxPoise'),(29,'opaqueCandidate'),(46,'excludedInitializer'),(48,'excludedThrow')):
        _require(len(raw[n])==5 and raw[n][0]==0xe8,'poise-setter-call-encoding','complete direct E8',raw[n].hex())
        target=relative_branch_target(raw[n],int(rows[n]['va'],16),source='poiseSetter')
        if key in providers:_require(target==providers[key],'poise-setter-provider-target',hex(providers[key]),hex(target))
        calls[key]=hex(target)
    edges={}
    for n,opcode,destination in ((9,b'\x0f\x85',None),(12,b'\x0f\x84',48),(16,b'\x75',37),
            (24,b'\x74',46),(36,b'\x72',41),(47,b'\xeb',25)):
        b=raw[n];width=4 if len(opcode)==2 else 1
        _require(len(b)==len(opcode)+width and b[:len(opcode)]==opcode,'poise-setter-branch-encoding',[n,opcode.hex()],b.hex())
        target=int(rows[n]['va'],16)+len(b)+int.from_bytes(b[len(opcode):],'little',signed=True)
        _require((target==int(rows[destination]['va'],16)) if destination is not None else not pointer<=target<at,
                 'poise-setter-branch-target',destination,hex(target));edges[str(n)]=hex(target)
    literals={}
    for n,key,width in ((30,'threshold',4),(34,'mask',16)):
        b=raw[n];target=int(rows[n]['va'],16)+len(b)+int.from_bytes(b[-4:],'little',signed=True)
        literals[key]={'operand':hex(target),'widthBytes':width,'instructionEnd':hex(int(rows[n]['va'],16)+len(b))}
    return {'selectedEntryExtent':[hex(pointer),hex(at)],'actualCalls':calls,'actualEdges':edges,
        'actualLiteralOperands':literals,'actualPatchInt32':int.from_bytes(raw[4][1:],'little',signed=True),
        'frameDeltaBytes':72,'normalRetStackDeltaBytes':8,'xmm7SavedEntryRelativeOffset':-40,'xmm6SavedEntryRelativeOffset':-24,
        'incomingValueCarrier':'XMM1.low32 -> XMM7; ordinary Single declaration and Windows x64 floating slot condition',
        'candidateCarrier':'post-call XMM0.low32, not proved typed managed helper return',
        'operationOrder':'post-call XMM0 -> XMM2; SUBSS current typed m_poise; ANDPS actual mask; COMISS threshold XMM1,masked difference XMM2; JB selects local store',
        'ordinaryOpaqueHelperPrototypeProved':False,'clampMinMaxSemanticsProved':False,'allOtherPathsProved':False}


def check_literal(index, item, expected_hex):
    from scripts.game_data.damage_snapshot_normal_attack_poise_flow import check_operand_pe
    pointer=int(item['operand'],16);width=item['widthBytes'];expected=bytes.fromhex(expected_hex)
    _require(width in (4,16) and len(expected)==width,'poise-setter-literal-width',width,len(expected))
    actual=index.pe.bytes_at_va(pointer,width)
    _require(actual==expected,'poise-setter-literal-bits',expected.hex(),actual.hex())
    rva=pointer-index.pe.image_base
    sections=[s for s in index.pe.sections if s['virtualAddress']<=rva and rva+width<=s['virtualAddress']+s['rawSize']]
    _require(len(sections)==1,'poise-setter-complete-literal-section','unique complete raw-backed span',len(sections))
    proofs=[check_operand_pe(index.pe,pointer+offset) for offset in range(0,width,4)]
    return {**item,'selectedDiskBytes':actual.hex(),'uniqueCompleteRawSection':True,
        'fourByteChunkPEProofs':proofs,'liveOperandUnmodifiedObserved':False}


def check_poise_setter(index, spec):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.context import relative_branch_target
    from scripts.game_data.damage_snapshot_abi import require_ordinary_field,require_ordinary_type
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    from scripts.game_data.damage_snapshot_primary_attr_flow import partition
    from scripts.game_data.damage_snapshot_atk_scale_flow import check_physical_coverage
    selected=NativeReferenceContext(index.image,index=index);body=index.body(spec['type'],spec['method'])
    require_ordinary_type(selected,index.types[spec['type']].byval_type_index,spec['type'],'poiseSetter.receiver',reference_kind=0x12)
    _check_named_provider(index,body.pointer,body.symbol,['float'],'void',is_static=False)
    fields={}
    for key,qualified,typ in (('poise',spec['poiseField'],'float'),('controller',spec['controllerField'],spec['controllerType'])):
        owner,actual,offset=selected.field(qualified)
        _require((owner,actual)==(spec['type'],typ),'poise-setter-field-owner',[spec['type'],typ],[owner,actual])
        require_ordinary_field(selected,qualified,typ,'poiseSetter.'+key);fields[key]=offset
    _require(body.size==spec['entryExtentBytes'],'poise-setter-entry-extent',spec['entryExtentBytes'],body.size)
    rows=partition(index.pe.bytes_at_va(body.pointer,body.size),body.pointer,spec['entryInstructionLengths'])
    providers={key:relative_branch_target(bytes.fromhex(rows[n]['bytes']),int(rows[n]['va'],16),source='poiseSetterProvider')
        for key,n in (('patch',7),('recovery',14),('maxPoise',20))}
    for key,params,ret,static in (('patch',['int'],'bool',True),('recovery',[],'bool',False),('maxPoise',[],'float',False)):
        _check_named_provider(index,providers[key],spec['providers'][key],params,ret,is_static=static)
    proof=check_setter_rows(rows,body.pointer,fields,providers)
    literals={key:check_literal(index,item,spec['literalBytes'][key]) for key,item in proof['actualLiteralOperands'].items()}
    ranges=check_physical_coverage(index.extents,[rows]);result=[]
    for write in (False,True):
        indices=list(range(37))+list(range(41,46)) if write else list(range(41))
        result.append({**proof,'symbol':body.symbol,'claim':'poiseSetterSelectedPostCallCarrierTypedLocalWrite' if write else 'poiseSetterSelectedPostCallCarrierNoLocalWrite',
            'selectedInstructionIndices':indices,'selectedPhysicalPdataRanges':ranges,'literalProvenance':literals,
            'typedFields':{'poise':spec['poiseField'],'controller':spec['controllerField']},
            'actualComparisonCondition':'COMISS normally returns CF=1 (ordered threshold smaller or unordered)' if write else 'COMISS normally returns CF=0 (ordered threshold greater/equal)',
            'localPoiseStoreEmitted':write,'localPoiseStoreWidthBytes':4 if write else 0,
            'wholeInvocationFieldPreservationProved':False,'appliedOrDisplayedPoiseObserved':False,
            'boundary':'Complete selected named setter entry-to-RET: ordinary false IsPatched, nonnull typed controller, ordinary false inPoiseRecovery, anonymous static readiness nonzero, and actual COMISS carry predicate select the numerical path. Incoming ordinary Single declaration/receiver, typed field owners, ordinary named Bool/Single provider declarations, raw argument transfers, SUBSS/ANDPS/COMISS order, full frame/RBX/XMM6/XMM7 restore and selected local store/no-local-store are independently checked. Candidate q is actual post-call XMM0.low32; no ordinary managed prototype, Clamp/min/max identity or value semantics is assigned to its anonymous helper. The old field is the value loaded at SUBSS time, not an entry snapshot. Original code/threshold/mask unchanged at invocation, valid compatible receiver/class/context/save/frame/return storage, normal callee ABI/saved-state and storage noninterference and floating environment/normal instruction completion remain conditions. JB follows CF including normally returning unordered comparisons; NaN, denormals, exceptions, signed zero and rounding are not simplified. No-local-store describes this tail only, not effects of earlier callees or whole invocation preservation. Other patch/recovery/initializer/null/throw paths, complete runtime virtual target selection, live operands and applied/displayed Poise remain unproved.'})
    return result
