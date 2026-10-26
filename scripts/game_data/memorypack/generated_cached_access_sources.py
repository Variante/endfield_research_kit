"""Exact inlined metadata-ready and coherent cached-holder access programs.

These conditional shortcuts preserve every incoming register except a declared
result register. Their users must separately own wrapper/base/cache declarations,
construction, field transfer and full caller framing. A nonzero metadata flag
and equal nonnull compatible holders are explicit conditions, not runtime facts.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='generatedCachedAccess'

def need(key,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+key+':'+str(detail)[:700])

def _equality(g,*,equal):
    first=g.bytes.get(g.at);long=first==15;opcode=g.bytes.get(g.at+1)if long else first
    need('literal-owned-equality-branch',opcode is not None and opcode&15 in(4,5)and(opcode>>4==8 if long else opcode>>4==7))
    before=g.at;prefix=('0f'if long else'')+format(opcode,'02x');width=4 if long else 1
    target=g.relative(prefix,width);fall=g.at;taken=equal if opcode&15==4 else not equal
    need('both-branch-boundaries-owned',target in g.bytes and fall in g.bytes)
    g.at=target if taken else fall
    return dict(instructionVa=before,conditionCode=opcode&15,target=target,fallthrough=fall,taken=taken,
        selected=g.at,excluded=fall if taken else target)

def metadata_shortcut(regions,entry):
    """Prove cmp flag/normal edge and the complete same-flag cold initializer."""
    hot=BytesPath(regions,entry);flag=hot.relative('803d')+1;hot.take('00');edge=_equality(hot,equal=False)
    cold=BytesPath(regions,edge['excluded']);usages=[];calls=[]
    while cold.bytes.get(cold.at)==0x48:
        site=cold.at;cell=cold.relative('488d0d');target=cold.relative('e8')
        usages.append(dict(instructionVa=site,cellVa=cell));calls.append(target)
        need('bounded-owned-initializer-calls',len(usages)<=8)
    need('at-least-one-shared-initializer',bool(usages)and len(set(calls))==1)
    need('same-metadata-flag-set',cold.relative('c605')+1==flag);cold.take('01')
    need('exact-initialized-normal-rejoin',cold.relative('e9')==edge['selected'])
    return dict(selectedBytes=hot.seen,excludedInitializerBytes=cold.seen,initializedFlagVa=flag,
        selectedEnd=hot.at,initializationUsages=usages,initializationTarget=calls[0],edge=edge,
        initializedFlagNonzeroRequired=True,metadataInitializerExecutionClaimed=False,
        allIncomingRegistersUnchanged=True,normalStateMutations=False)

def coherent_access(regions,entry,*,wrapper,base_slot,cache_slot,metadata=True):
    """Own the exact flag/base/cache equality shortcut to whole original RAX/RCX."""
    enc={'rbx':('7b','43'),'rbp':('7d','45'),'rsi':('7e','46'),'rdi':('7f','47')}
    need('explicit-holder-source-roles',wrapper in enc and type(base_slot)is int and type(cache_slot)is int and
        16<=base_slot<cache_slot<128 and type(metadata)is bool)
    shortcut=metadata_shortcut(regions,entry)if metadata else None
    g=BytesPath(regions,shortcut['selectedEnd']if shortcut else entry);test,load=enc[wrapper];b=bytes((base_slot,)).hex();c=bytes((cache_slot,)).hex()
    g.take('4883'+test+c+'00');nonnull=_equality(g,equal=False)
    g.take('488b'+load+b,'4839'+load+c);same=_equality(g,equal=True)
    prefix=bytes(g.bytes.get(g.at+i,0)for i in range(3))
    if prefix==bytes.fromhex('488b'+load):result='rax';g.take('488b'+load+c)
    else:
        rcx={'rbx':'4b','rbp':'4d','rsi':'4e','rdi':'4f'}[wrapper];g.take('488b'+rcx+c);result='rcx'
    selected=(shortcut['selectedBytes']if shortcut else[])+g.seen
    return dict(selectedBytes=selected,metadataShortcut=shortcut,selectedEnd=g.at,wrapperRegister=wrapper,
        baseHolderOffset=base_slot,typedCacheOffset=cache_slot,resultRegister=result,
        nonnullEdge=nonnull,equalCacheEdge=same,sameWholeOriginalReference=True,
        compatibleNonNullSameHoldersRequired=True,constructionProved=False,refreshAdmitted=False,
        unchangedIncomingRegistersExcept=['rax']if result=='rax'else['rax','rcx'],childGrammarAdmitted=False)

def derive_metadata(image,pins,*,source_target,compare_rva,allowed_type_names):
    """Fresh full owned source, exact flag initializer and closed nominal usages."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.context import unresolved_usage_index
    from scripts.game_data.il2cpp.protocol import runtime_type_name
    from scripts.game_data.memorypack import generated_member_sources as members,scalar_param_native as scalar
    _publication_gate(image,pins);base=image.pe.image_base;body=members._body(image,source_target)
    need('explicit-current-nominal-owner-set',type(allowed_type_names)is set and bool(allowed_type_names)and all(type(n)is str and n for n in allowed_type_names))
    program=metadata_shortcut(body['regions'],base+compare_rva);usages=[]
    for row in program['initializationUsages']:
        cell=row['cellVa'];raw=image.pe.bytes_at_va(cell,8)
        index=unresolved_usage_index(raw,image.registration['typesCount'],tag=1,source=LABEL,offset=cell)
        pointer=image.pe.u64_at_va(int(image.registration['types'],16)+index*8)
        name=runtime_type_name(image.pe,image.metadata,pointer)
        need('same-current-declared-formatter-or-original',name in allowed_type_names,name)
        scalar.ordinary(image,pointer,18,LABEL+'.initializedClass',reference=True)
        usages.append(dict(instructionRva=row['instructionVa']-base,usageCellRva=cell-base,usageRawHex=raw.hex().upper(),
            typeIndex=index,typeName=name,typeRawHex=image.pe.bytes_at_va(pointer,16).hex().upper()))
    _publication_gate(image,pins)
    return dict(schema='endfield.generated-metadata-shortcut.v1',status='validated',nativeInputs=pins,
        sourceTargetRva=source_target-base,compareRva=compare_rva,sourceFamily=body['family'],codeWindows=body['windows'],
        program=program,usages=usages,initializedFlagNonzeroRequired=True,normalStateMutations=False,
        wholeCallerAdmitted=False,childGrammarAdmitted=False,metadataInitializerExecutionClaimed=False)

def collect_programs(rows,setters):
    """Only current independently owned getter holder pairs may select macros."""
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    pairs={(s['getter']['baseHolder'][2],s['getter']['typedCache'][2])for s in setters if s.get('getter')}
    regions=[(ec.va(r),ec.raw(r))for r in rows];found={}
    for row in rows:
        if not ec.raw(row).startswith(bytes.fromhex('803d')):continue
        matches=[]
        for b,c in sorted(pairs):
            for register in('rbx','rbp','rsi','rdi'):
                try:matches.append(coherent_access(regions,ec.va(row),wrapper=register,base_slot=b,cache_slot=c))
                except(ValueError,KeyError,IndexError):continue
        need('unambiguous-current-holder-macro',len(matches)<=1)
        if matches:found[ec.va(row)]=dict(program=matches[0])
    return found

def bind_programs(image,pins,*,source_target,accesses,path,events,setters):
    """Join each selected shortcut to that exact member getter and nominal flag."""
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    base=image.pe.image_base;positions={ec.va(r):i for i,r in enumerate(path)};event_positions=[positions[base+e['instruction'][0]]for e in events];bound={}
    for address,record in accesses.items():
        if address not in positions:continue
        earlier=[n for n,i in enumerate(event_positions)if i<positions[address]]
        need('cached-access-after-current-source',bool(earlier));n=earlier[-1];getter=setters[n].get('getter');program=record['program']
        need('same-member-owned-coherent-getter',getter is not None and getter.get('coherentNonNullSamePointerReturn')is True
            and getter['baseHolder'][2]==program['baseHolderOffset']and getter['typedCache'][2]==program['typedCacheOffset'])
        metadata=derive_metadata(image,pins,source_target=source_target,compare_rva=address-base,
            allowed_type_names={getter['method'][1],getter['typedCache'][1]})
        bound[address]=dict(program=program,metadata=metadata,memberIndex=n,getterMethod=getter['method'],
            baseHolder=getter['baseHolder'],typedCache=getter['typedCache'],constructionProved=False)
    return bound
