"""Complete buffered value-load macros with exact cursor consumption.

Widths here come from literal guards, captured byte slices and all four native
Reader updates. A caller still must bind each macro to a named current field,
its nominal layout, full source-to-store flow and complete lifecycle/frame.
No managed layout supplies a wire width and no default EC path is widened.
"""
import re
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import buff_ec_profiles_native as ec

LABEL='generatedInlineValue'
REGISTERS=('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi',*('r'+str(i)for i in range(8,16)))

def need(k,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+k+':'+str(detail)[:700])

def peek(g,n=1):return bytes(g.bytes.get(g.at+i,0)for i in range(n))

def conditional(g,codes,selected):
    first=peek(g)[0];long=first==15;opcode=peek(g,2)[1]if long else first
    need('reviewed-condition',opcode&15 in codes and(opcode>>4==8 if long else opcode>>4==7))
    g.branch(('0f'if long else'')+format(opcode,'02x'),selected(opcode&15),4 if long else 1)

def _payload_load(g):
    """One literal low4/8/16 SSE lane or zero-extended byte/DWORD/QWORD."""
    start=g.at;prefix=peek(g)[0];rex=0
    if 0x40<=prefix<=0x4f:rex=g.read(1)[0]
    prefix=peek(g,3)
    if prefix[:3]in(bytes.fromhex('f30f10'),bytes.fromhex('f20f10')):
        kind='sse';width=4 if prefix[0]==243 else 8;g.take(prefix[:3].hex())
    elif prefix[:2]==bytes.fromhex('0f10'):kind='sse';width=16;g.take('0f10')
    elif prefix[:2]==bytes.fromhex('0fb6'):kind='integer';width=1;g.take('0fb6')
    elif prefix[0]==139:kind='integer';width=8 if rex&8 else 4;g.take('8b')
    else:raise ValueError(LABEL+'.actual-payload-load:'+prefix.hex())
    modrm=g.read(1)[0];mod=modrm>>6;number=((modrm>>3)&7)+(8 if rex&4 else 0)
    need('payload-from-plain-RAX',mod in(0,1)and modrm&7==0 and not rex&3)
    displacement=int.from_bytes(g.read(1),'little',signed=True)if mod==1 else 0
    need('nonnegative-bounded-payload-slice',0<=displacement<16 and displacement+width<=16)
    register='xmm'+str(number)if kind=='sse'else REGISTERS[number]
    need('payload-does-not-destroy-RAX-address',kind=='sse'or register!='rax'or displacement==0)
    return dict(register=register,sourceOffset=displacement,bytes=width,loadInstructionVa=start,kind=kind)

def guarded_program(regions,entry,offsets,*,reader='rbx',output='rdi'):
    """Literal enough-buffer guard, payload capture and complete four updates."""
    if(reader,output)==('rbp','rsi'):
        from scripts.game_data.memorypack.generated_rbp_scalar_capture_sources import program
        return program(regions,entry,offsets,reader=reader,output=output)
    if(reader,output)==('rbx','rdi'):
        data={at+i:b for at,raw in regions for i,b in enumerate(raw)}
        def at(offset,length):return bytes(data.get(entry+offset+i,0)for i in range(length))
        if at(0,7)==bytes((0x83,0x7b,offsets['bufferLength'],24,0x48,0x8b,0x37)):
            from scripts.game_data.memorypack.levelscript_posrot_capture_sources import capture_program
            return capture_program(regions,entry,offsets)
        if at(0,7)==bytes((0x83,0x7b,offsets['bufferLength'],36,0x48,0x8b,0x37)):
            from scripts.game_data.memorypack.skill_animation_clip_raw_sources import capture_program
            return capture_program(regions,entry,offsets)
        if(at(0,7)in(bytes((0x83,0x7b,offsets['bufferLength'],12,0x48,0x8b,0x37)),bytes((0x83,0x7b,offsets['bufferLength'],12,0x48,0x8b,0x3f)))and at(7,2)==bytes.fromhex('0f8c')
            and at(13,9)==bytes((0x48,0x8b,0x43,offsets['currentPtr']))+bytes.fromhex('ba0c000000')):
            from scripts.game_data.memorypack.generated_integer_vector_capture_sources import program
            return program(regions,entry,offsets,reader=reader,output=output)
    if reader=='r15'and output=='r14':
        from scripts.game_data.memorypack.generated_called_advance_sources import program
        return program(regions,entry,offsets,reader=reader,output=output)
    if reader=='rdi'and output=='rbx':
        data={at+i:b for at,raw in regions for i,b in enumerate(raw)}
        if bytes(data.get(entry+i,0)for i in range(7))==bytes((0x83,0x7f,offsets['bufferLength'],24,0x48,0x8b,0x33)):
            from scripts.game_data.memorypack.generated_initial24_capture_sources import program
            return program(regions,entry,offsets,reader=reader,output=output)
        from scripts.game_data.memorypack.generated_color_capture_sources import program
        return program(regions,entry,offsets,reader=reader,output=output)
    if reader=='rdi'and output=='rsi':
        data={at+i:b for at,raw in regions for i,b in enumerate(raw)}
        prefix=bytes(data.get(entry+i,0)for i in range(7))
        if prefix in(bytes((0x83,0x7f,offsets['bufferLength'],12,0x48,0x8b,0x1e)),
                      bytes((0x83,0x7f,offsets['bufferLength'],4,0x4c,0x8b,0x36))):
            from scripts.game_data.memorypack.generated_rdi_advance_capture_sources import program
            return program(regions,entry,offsets,reader=reader,output=output)
        from scripts.game_data.memorypack.generated_rdi_scalar_capture_sources import program
        return program(regions,entry,offsets,reader=reader,output=output)
    if(reader,output)==('rdi','r14'):
        from scripts.game_data.memorypack.generated_rdi_advance_capture_sources import program
        return program(regions,entry,offsets,reader=reader,output=output)
    if(reader,output)==('rbx','r14'):
        data={at+i:b for at,raw in regions for i,b in enumerate(raw)}
        need('literal-RBX-R14-DWORD-profile',bytes(data.get(entry+i,0)for i in range(7))==
             bytes((0x83,0x7b,offsets['bufferLength'],4))+bytes.fromhex('498b3e'))
    need('explicit-reviewed-reader-output-registers',reader=='rbx'and output in('rsi','rdi','r14'))
    need('four-distinct-small-offsets',set(offsets)>={'currentPtr','bufferLength','advancedCount','consumed'}and
        len({offsets[k]for k in('currentPtr','bufferLength','advancedCount','consumed')})==4 and
        all(type(offsets[k])is int and 0<=offsets[k]<128 for k in('currentPtr','bufferLength','advancedCount','consumed')))
    c,r,a,u=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry);g.take('837b'+r);width=g.read(1)[0]
    need('literal-finite-source-width',width in(1,4,8,12,16));wrapper_load=None
    prefix=peek(g,3)
    if prefix[0]in(0x48,0x49,0x4c,0x4d)and prefix[1]==0x8b and prefix[2]>>6==0 and \
        (prefix[2]&7)+(8 if prefix[0]&1 else 0)==REGISTERS.index(output):
        register=REGISTERS[((prefix[2]>>3)&7)+(8 if prefix[0]&4 else 0)]
        need('preserved-wrapper-load-register',register in('rbp','rsi','rdi','r12','r13','r14','r15'))
        wrapper_load=dict(instructionVa=g.at,register=register,outputRegister=output);g.take(prefix.hex())
    conditional(g,(12,13),lambda code:code==13)
    pointer_site=g.at;g.take('488b43'+c);slices=[];spills=[]
    while peek(g,3)not in(bytes.fromhex('8b6b'+r),bytes.fromhex('8b73'+r),bytes.fromhex('8b7b'+r)):
        if peek(g,4)==bytes.fromhex('0f114424'):
            at=g.at;g.take('0f114424');displacement=g.read(1)[0]
            captured=[s for s in slices if s['register']=='xmm0'and s['bytes']==16]
            need('actual-captured-sixteen-byte-spill',len(captured)==1 and not spills and 32<=displacement<128)
            spills.append(dict(displacement=displacement,bytes=16,sourceOffset=captured[0]['sourceOffset'],register='xmm0',storeInstructionVa=at));continue
        if peek(g,5)==bytes.fromhex('f20f114424'):
            at=g.at;g.take('f20f114424');displacement=g.read(1)[0]
            captured=[s for s in slices if s['register']=='xmm0'and s['bytes']==8]
            need('actual-captured-eight-byte-spill',len(captured)==1 and not spills and 32<=displacement<128)
            spills.append(dict(displacement=displacement,bytes=8,sourceOffset=captured[0]['sourceOffset'],register='xmm0',storeInstructionVa=at));continue
        need('bounded-native-load-count',len(slices)<4)
        slices.append(_payload_load(g))
    covered=[i for record in slices for i in range(record['sourceOffset'],record['sourceOffset']+record['bytes'])]
    need('all-and-only-captured-source-bytes',sorted(covered)==list(range(width)),slices)
    need('distinct-live-payload-registers',len({s['register']for s in slices})==len(slices))
    need('RAX-address-survives-until-last-capture',all(s['register']!='rax'for s in slices[:-1]))
    remaining_byte=peek(g,2)[1];remaining={0x6b:'rbp',0x73:'rsi',0x7b:'rdi'}[remaining_byte]
    need('remaining-does-not-clobber-payload-or-reader',remaining not in{s['register']for s in slices}and remaining not in(reader,output)
        and(wrapper_load is None or remaining!=wrapper_load['register']))
    remaining_site=g.at;g.take('8b'+format(remaining_byte,'02x')+r)
    reg_code={0x6b:5,0x73:6,0x7b:7}[remaining_byte]
    if width==1:g.take('83'+format(0xe8|reg_code,'02x')+'01')
    else:g.take('83'+format(0xc0|reg_code,'02x')+bytes((-width&255,)).hex())
    conditional(g,(8,9),lambda code:code==9)
    if width==1:g.take('48ff43'+c,'ff43'+a,'ff43'+u)
    else:
        w=bytes((width,)).hex();g.take('488343'+c+w,'8343'+a+w,'8343'+u+w)
    g.take('89'+format(remaining_byte,'02x')+r)
    return dict(selectedBytes=g.seen,guardInstructionVa=entry,sourcePointerInstructionVa=pointer_site,
        wireBytes=width,capturedSourceSlices=slices,wrapperLoad=wrapper_load,
        remainingRegister=remaining,remainingLoadInstructionVa=remaining_site,
        readerOffsets={k:offsets[k]for k in('currentPtr','bufferLength','advancedCount','consumed')},
        allFourReaderUpdatesProved=True,completeSourceBitsCaptured=True,
        sourceLocalValues=spills,managedLayoutUsedForWidth=False,
        condition='Enough contiguous disjoint buffered input and nonnegative remaining length. Each captured register byte slice must independently reach its named current field; full frame and nonvolatile preservation remain caller obligations.')

def selected_rows(rows,program):
    """Every selected byte must belong to an entire decoded instruction."""
    from scripts.game_data.memorypack.generated_vector_member_sources import selected_rows as join
    return join(rows,program['selectedBytes'])

def fast_path(rows,header,reader,offsets,*,output='rdi',terminal_target=None,cached_accesses=None,final_setter_target=None,zero_prover=None,disabled_collector=None):
    """Existing strict normal branches plus freshly proved inline macros."""
    need('literal-terminal',terminal_target is None or type(terminal_target)is int and terminal_target>0)
    need('callable-only-owned-zero-prover',zero_prover is None or callable(zero_prover))
    need('literal-disabled-collector',disabled_collector is None or type(disabled_collector)is int and disabled_collector>0)
    need('literal-final-setter-terminal',final_setter_target is None or type(final_setter_target)is int and final_setter_target>0
        and final_setter_target!=terminal_target)
    by={ec.va(r):r for r in rows};need('unique-owned-instructions',len(by)==len(rows))
    regions=[(ec.va(r),ec.raw(r))for r in rows];macros={};macro_errors={}
    widths=('1|4|8|c|10|18'if(reader,output)==('rdi','rbx')else
            '1|4|8|c|10|18|24'if(reader,output)==('rbx','rdi')else'1|4|8|c|10')
    for r in rows:
        if re.fullmatch(rf"cmp dword \[{reader}\+{offsets['bufferLength']:#x}\], 0x(?:{widths})",r['text']):
            try:program=guarded_program(regions,ec.va(r),offsets,reader=reader,output=output)
            except ValueError as error:macro_errors[ec.va(r)]=str(error);continue
            macros[ec.va(r)]=program
    at=ec.va(header);seen=[];decisions=[];flags=None;flag_site=None;selected=[]
    need('literal-cached-access-map',cached_accesses is None or type(cached_accesses)is dict)
    cached_accesses=cached_accesses or{}
    while True:
        need('owned-boundary-no-loop',at in by and at not in seen,hex(at));r=by[at]
        if at in cached_accesses:
            from scripts.game_data.memorypack.generated_cached_access_sources import coherent_access
            supplied=cached_accesses[at]['program'];program=coherent_access(regions,at,wrapper=supplied['wrapperRegister'],
                base_slot=supplied['baseHolderOffset'],cache_slot=supplied['typedCacheOffset'])
            part=selected_rows(rows,program);need('no-repeated-cached-access',not set(seen)&{ec.va(q)for q in part})
            seen.extend(ec.va(q)for q in part)
            for edge in(program['metadataShortcut']['edge'],program['nonnullEdge'],program['equalCacheEdge']):
                decisions.append(dict(instruction=by[edge['instructionVa']],condition='Current metadata initialized and same nonnull compatible holders; exact independently bound getter',taken=edge['taken']))
            at=program['selectedEnd'];flags=None;continue
        if at in macros:
            program=macros[at];part=selected_rows(rows,program)
            need('no-repeated-macro-instructions',not set(seen)&{ec.va(q)for q in part})
            seen.extend(ec.va(q)for q in part);selected.append(program)
            last=part[-1];at=ec.va(last)+len(ec.raw(last));flags=None;continue
        need('complete-decoded-selected-instruction',not r['text'].startswith('db '),r)
        seen.append(at);flow=ec.control_transfer(r);end=at+len(ec.raw(r));text=r['text']
        if flow['kind']=='conditional':
            code=flow['conditionCode'];prior=flags or''
            if at==ec.va(header)+len(ec.raw(header))and code in(4,5):taken,reason=code==4,'current member count matches'
            elif prior.startswith('test ')and code in(4,5):
                left,_,right=prior[5:].partition(', ');need('self-null-test',left==right);taken,reason=code==5,'current reference nonnull'
            elif prior.startswith('cmp qword ')and prior.endswith(', 0x0')and code in(4,5):taken,reason=code==5,'current initialized context/storage'
            elif prior.startswith('cmp dword ')and'[rip 'in prior and prior.endswith(', 0x0')and code in(4,5):taken,reason=code==4,'current disabled collector'
            elif re.fullmatch(r'cmp dword \[\w+\+0xe0\], 0x0',prior)and code in(4,5):taken,reason=code==5,'current class initialized'
            elif callable(zero_prover)and code in(4,5)and flag_site in by:
                compare=by[flag_site];raw=ec.raw(compare);op=compare.get('memoryRegisterComparisonOperation',{});address=op.get('memoryAddress',{})
                need('finite-owned-EBP-zero-DWORD-comparison',op.get('bits')==32 and op.get('register')=='ebp'
                    and op.get('memoryReadBytes')==4 and op.get('memoryWriteBytes')==0
                    and op.get('memoryIsLeftOperand')is True and op.get('preservesRegisters')is True)
                zero=zero_prover([flag_site],'rbp')
                need('same-independent-whole-zero-at-comparison',zero.get('register')=='rbp'and zero.get('value')==0
                    and zero.get('zeroOnEveryOrdinaryPath')is True and flag_site in zero.get('sites',[]))
                if raw==bytes.fromhex('39a9e0000000'):
                    need('exact-class-ready-zero-comparison',address.get('base')=='rcx'and address.get('index')is None
                        and address.get('displacement')==224 and not address.get('ripRelative'))
                    taken,reason=code==5,'current class initialized; independently proved whole EBP zero'
                else:
                    need('exact-current-zero-collector-comparison',disabled_collector is not None and len(raw)==6
                        and raw[:2]==bytes.fromhex('392d')and address.get('ripRelative')is True
                        and address.get('absoluteAddress')==disabled_collector
                        and flag_site+6+int.from_bytes(raw[2:],'little',signed=True)==disabled_collector)
                    taken,reason=code==4,'current disabled collector; independently proved whole EBP zero'
            else:raise ValueError(LABEL+'.unowned-conditional:'+str((r,prior,dict(precedingMacroRefusal=macro_errors[flag_site])if flag_site in macro_errors else{})))
            need('owned-conditional-target',flow['target']in by);decisions.append(dict(instruction=r,condition=reason,taken=taken));at=flow['target']if taken else end
        elif flow['kind']=='jump':
            if flow['target']in{t for t in(terminal_target,final_setter_target)if t is not None}:
                need('external-terminal',flow['target']not in by);break
            need('owned-jump',flow['target']in by,dict(instruction=r,target=flow['target']));at=flow['target']
        elif flow['kind']=='return':break
        else:
            need('ordinary-flow',flow['kind']in('next','call','indirectCall','registerCall'));at=end
        if text.split()[0]in('cmp','test','sub','add','xor','and','or','inc','dec','shl','shr','sar'):flags=text;flag_site=ec.va(r)
        if flow['kind']in('call','indirectCall','registerCall'):flags=None
    return [by[a]for a in seen],decisions,selected
