"""Additional proofs for source families containing guarded RVA data tables.

The table partition and ordinary entry graph remain supplied by the maintained
IL2CPP parser. This component proves a current literal image-base definition
dominates each dispatch and cannot be overwritten on a path to that dispatch.
It proves framing and register roles, not formatter or child wire semantics.
"""
import json,re
from scripts.game_data.il2cpp.initializer_control import _ALIASES
from scripts.game_data.il2cpp.consumer_rva_switches import ordinary_entry_program
from scripts.game_data.il2cpp.prefetch_instruction import memory_prefetch_address

LABEL='generatedOwnedCode'

def need(k,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+k+':'+str(detail)[:700])

def _reached(edges,entry,blocked=()):
    blocked=set(blocked);seen=set();pending=[entry]
    while pending:
        at=pending.pop()
        if at in seen or at in blocked:continue
        seen.add(at);pending.extend(edges.get(at,())-seen)
    return seen

def base_certificate(part,*,entry,image_base,post_dispatch_overwrite_registers=()):
    """Require guarded dispatch and actual nonvolatile image-base provenance."""
    need('explicit-post-dispatch-overwrite-domain',type(post_dispatch_overwrite_registers)is tuple and
        post_dispatch_overwrite_registers in((),('rbp',),('rbp','r14')))
    proof=ordinary_entry_program(part,entry=entry);graph=proof['fullGraph'];edges=graph['edges'];reachable=set(graph['reachableInstructions'])
    rows=part['rows'];by={int(r['va'],16):r for r in rows};certificates=[]
    all_dispatch_loads={t['load']for t in part['tables']}
    for register in sorted({t['baseRegister']for t in part['tables']}):
        # These registers have no implicit string/multiply instruction writes;
        # normal external Win64 callees preserve their incoming whole values.
        need('explicit-nonvolatile-image-base',register in('rbx','rbp','r12','r13','r14','r15'))
        targets={t['load']for t in part['tables']if t['baseRegister']==register}
        initializers=[];kills=[];uses=[];post_dispatch_writes=[];post_dispatch_uses=[]
        for at,row in by.items():
            text=row['text'];address=row.get('addressOperation',{});move=row.get('memoryOperation',{});op=row.get('integerOperation',{})
            destination=_ALIASES.get((row.get('write')or{}).get('register'),(row.get('write')or{}).get('register'))
            if address.get('destination')==register and address.get('absoluteAddress')==image_base:
                initializers.append(at);continue
            mentioned=any(_ALIASES.get(token,token)==register for token in re.findall(r'\b(?:r(?:1[0-5]|[89])(?:d|w|b)?|[re]?[abcd]x|[re]?(?:si|di|bp|sp)|[abcd][lh])\b',text))
            if not mentioned:continue
            if destination==register or text=='pop '+register:
                # Whole frame restores and the explicitly selected word-load
                # profiles remain distinct; neither may reach a dispatch.
                a=move.get('address',{})
                restore=text=='pop '+register or move.get('direction')=='load'and move.get('register')==register and \
                    move.get('memoryBytes')==8 and a.get('base')=='rsp'and a.get('index')is None and not a.get('ripRelative')
                word_load=register in post_dispatch_overwrite_registers and move.get('direction')=='load'and \
                    move.get('backingRegister')==register and move.get('registerBits')==32 and move.get('memoryBytes')==4
                if word_load and register=='r14':
                    # This profile retires the literal table base into one
                    # zero-extending buffered scalar load, never a clobber or
                    # a partial frame restore. Every computed dispatch in the
                    # full owned graph must be unreachable from this load.
                    word_load=bytes.fromhex(row['bytes'])==b'\x44\x8b\x30'and text=='mov r14d, [rax]'and \
                        move.get('register')=='r14d'and move.get('registerBitOffset')==0 and \
                        move.get('upperRegisterEffect')=='zero upper 32 bits'and move.get('writesFlags')is False and \
                        a.get('base')=='rax'and a.get('index')is None and a.get('displacement')==0 and not a.get('ripRelative')
                    if word_load:need('post-dispatch-word-load-cannot-reach-any-dispatch',
                        not _reached(edges,at)&all_dispatch_loads,row)
                need('only-whole-frame-base-restore-or-proved-post-dispatch-load',restore or word_load,row)
                if word_load:post_dispatch_writes.append(at)
                kills.append(at);continue
            a=move.get('address',{})
            saved=move.get('direction')=='store'and move.get('register')==register and move.get('memoryBytes')==8 and a.get('base')=='rsp'and a.get('index')is None
            memory_preserves=move.get('direction')in('load','store')and a.get('base')==register and(move.get('direction')=='store'or move.get('backingRegister')!=register)
            added=op.get('operation')=='add'and op.get('bits')==64 and op.get('source')==register and op.get('destination')!=register
            addressed=bool(address)and address.get('base')==register and address.get('destination')!=register
            atomic=row.get('lockedMemoryExchangeOperation',{})
            atomic_preserves=atomic.get('operation')in('cmpxchg','xadd','xchg')and atomic.get('sourceRegister')!=register and atomic.get('accumulatorRegister')!=register
            preserving=saved or memory_preserves or added or addressed or atomic_preserves or text=='push '+register or memory_prefetch_address(bytes.fromhex(row['bytes']))is not None
            post_dispatch_targets=all_dispatch_loads if register=='r14'else targets
            if not preserving and register in post_dispatch_overwrite_registers and not _reached(edges,at)&post_dispatch_targets:
                post_dispatch_uses.append(at);continue
            need('exact-base-preserving-use',preserving,row)
            uses.append(at)
        need('fresh-literal-image-base-load',bool(initializers),register)
        bypass=_reached(edges,entry,initializers)
        need('literal-image-base-dominates-every-load',not targets&bypass,(register,sorted(targets&bypass)))
        for at in kills:
            if at in reachable:
                after=set().union(*(_reached(edges,n)for n in edges[at]))if edges[at]else set()
                need('no-restored-base-reaches-dispatch',not after&targets,(register,at,sorted(after&targets)))
        certificate=dict(register=register,literalImageBaseLoads=sorted(initializers),dispatchLoads=sorted(targets),
            completeExplicitUses=sorted(uses),frameRestores=sorted(set(kills)-set(post_dispatch_writes)),dominanceProved=True,ordinaryWin64CalleesPreserveBaseRequired=True)
        if post_dispatch_writes:certificate['postDispatchWordLoads']=sorted(post_dispatch_writes)
        if post_dispatch_uses:certificate['postDispatchUsesCannotReachAnyDispatch']=sorted(post_dispatch_uses)
        certificates.append(certificate)
    return dict(status='code-table-base-proved',entry=entry,imageBase=image_base,certificates=certificates,
        ordinaryEntry=proof,allTableGuardsCannotBeBypassed=True,allDispatchBasesEqualSelectedImageBase=True,
        nativeBehaviorAdmitted=False,wireGrammarAdmitted=False)

def _json_value(value):
    def convert(item):
        if isinstance(item,set):return sorted(item)
        raise TypeError(type(item).__name__)
    return json.loads(json.dumps(value,default=convert))


def source_family(image,pins,*,entry_rva):
    """Keep the ordinary family unchanged; partition data only when required."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    _publication_gate(image,pins);need('literal-current-entry',type(entry_rva)is int and entry_rva>0)
    try:family,windows,rows=ec.family(image,entry_rva)
    except(ValueError,IndexError):
        # A trailing table can resemble a truncated instruction. Retain its
        # complete owned windows and require the same guarded byte partition;
        # a decoder exception never supplies a code/data boundary itself.
        family,windows=ec.family_windows(image,entry_rva)
        proof=_derive_family(image,pins,entry_rva,family,windows)
        return family,windows,proof['rows'],proof
    if not any(row['text'].startswith('db ')for row in rows):
        _publication_gate(image,pins);return family,windows,rows,None
    proof=_derive_family(image,pins,entry_rva,family,windows)
    return family,windows,proof['rows'],proof


def derive(image,pins,*,entry_rva):
    """Partition only literal current full-unwind ranges, without invented gaps."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    _publication_gate(image,pins);need('literal-current-entry',type(entry_rva)is int and entry_rva>0)
    family,windows=ec.family_windows(image,entry_rva)
    return _derive_family(image,pins,entry_rva,family,windows)


def _derive_family(image,pins,entry_rva,family,windows):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.consumer_rva_switches import partition_consumer_rva_switches
    from scripts.game_data.il2cpp.string_source_instructions import decode_string_source_instructions
    _publication_gate(image,pins);base=image.pe.image_base
    need('literal-current-entry',type(entry_rva)is int and entry_rva>0)
    chunks=[]
    for part in sorted(family['ranges'],key=lambda p:p['runtimeTriple'][0]):
        a,z=part['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,z-a)
        if chunks and chunks[-1][0]+len(chunks[-1][1])==base+a:
            old,data=chunks.pop();chunks.append((old,data+raw))
        else:chunks.append((base+a,raw))
    rows=[];partitions=[]
    for start,raw in chunks:
        try:decoded=decode_string_source_instructions(image.mapper,raw,start)
        except(ValueError,IndexError):decoded=None
        if decoded is None or any(r['text'].startswith('db ')for r in decoded):
            part=partition_consumer_rva_switches(image.mapper,raw,entry=start,image_base=base,
                old_base_registers=('rbp','r12','r13','r14','r15'),destination_registers=('rax','rcx','rdx'),
                padding_forms=(b'\x90',b'\xcc',b'\x66\x90',b'\x0f\x1f\x00'),return_padding=True)
            certificate=base_certificate(part,entry=start,image_base=base,post_dispatch_overwrite_registers=('rbp','r14'))
            partitions.append(dict(startRva=start-base,endRva=start-base+len(raw),partition=part,baseCertificate=certificate))
            rows+=part['rows']
        else:rows+=decoded
    need('at-least-one-exact-owned-data-partition',bool(partitions))
    need('remaining-code-completely-decoded',not any(r['text'].startswith('db ')for r in rows))
    _publication_gate(image,pins)
    return _json_value(dict(status='current-owned-code-partition-proved',nativeInputs=pins,entryRva=entry_rva,
        family=family,codeWindows=windows,rows=rows,partitions=partitions,
        formatterSemanticsAdmitted=False,wireGrammarAdmitted=False))
