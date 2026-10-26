"""Complete selected generated concrete reader programs and source joins.

The initialized new, existing and FF entry paths are separate exact programs.
Current child call identities produce obligations; this component does not
admit a child grammar, union selection or effective runtime provider.
"""
from __future__ import annotations
import json,re
from scripts.game_data.il2cpp.initializer_control import control_transfer,_ALIASES
from scripts.game_data.il2cpp.body_claims import _writes_register
from scripts.game_data.memorypack import buff_ec_profiles_native as ec
from scripts.game_data.memorypack import generated_action_sources as actions
from scripts.game_data.memorypack import generated_member_sources as members
from scripts.game_data.memorypack import generated_lifecycle_sources as lifecycle

LABEL='generatedReaderSource'
NONVOLATILE={'rbx','rbp','rsi','rdi','r12','r13','r14','r15'}


def need(check,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+check+':'+str(detail)[:1000])


class _Path:
    def __init__(self,rows,entry):self.by={ec.va(r):r for r in rows};self.at=entry;self.seen=[]
    def row(self):
        need('selected-owned-boundary',self.at in self.by and self.at not in{ec.va(r)for r in self.seen},hex(self.at));return self.by[self.at]
    def take(self,text=None,site=None):
        row=self.row();need('selected-instruction',(text is None or row['text']==text)and(site is None or site==[ec.va(row),ec.raw(row).hex().upper()]),(text,row))
        self.seen.append(row);self.at+=len(ec.raw(row));return row
    def branch(self,fact):
        row=self.row();flow=control_transfer(row);need('owned-boolean-branch',flow['kind']=='conditional'and flow['conditionCode']in(4,5),row)
        # fact describes whether the compared operands are equal/zero.
        taken=fact if flow['conditionCode']==4 else not fact;self.take();self.at=flow['target']if taken else self.at;return row
    def jump(self):
        row=self.row();flow=control_transfer(row);need('owned-unconditional-jump',flow['kind']=='jump',row);self.take();self.at=flow['target']
    def call(self,target):
        row=self.row();flow=control_transfer(row);need('actual-callee',flow['kind']=='call'and flow['target']==target,(target,row));return self.take()


def _absolute(site,base):return[base+site[0],site[1]]


def _inline_output_publication(g,*,base,disabled_flag,output,allocated):
    """Publish the whole fresh wrapper under the exact disabled collector flag."""
    stores={('rsi','rbx'):'48891e',('r14','rdi'):'49893e',('rbx','rsi'):'488933',('rsi','rdi'):'48893e'}
    need('finite-inline-output-publication-roles',(output,allocated)in stores,
        dict(outputRegister=output,allocatedRegister=allocated))
    row=g.row();compare=row.get('memoryImmediateComparisonOperation',{});address=compare.get('sourceAddress',{})
    raw=ec.raw(row)
    need('same-current-disabled-output-collector',type(disabled_flag)is int and disabled_flag>0
        and len(raw)==7 and raw[:2]==bytes.fromhex('833d')and raw[-1]==0
        and compare.get('bits')==32 and compare.get('immediateValue')==0 and compare.get('preservesRegisters')is True
        and address.get('ripRelative')is True and address.get('absoluteAddress')==base+disabled_flag
        and ec.va(row)+7+int.from_bytes(raw[2:6],'little',signed=True)==base+disabled_flag,row)
    start=len(g.seen);g.take();store=g.row();move=store.get('memoryOperation',{});address=move.get('address',{})
    need('same-whole-allocated-wrapper-output-store',move.get('direction')=='store'and move.get('memoryBytes')==8
        and move.get('register')==allocated and address.get('base')==output and address.get('index')is None
        and address.get('displacement')==0 and not address.get('ripRelative')and move.get('writesFlags')is False
        and ec.raw(store)==bytes.fromhex(stores[(output,allocated)]),store)
    g.take();edge=g.row();need('disabled-output-collector-equality-edge',control_transfer(edge).get('conditionCode')==4,edge);g.branch(True)
    return dict(selectedProgram=[ec.site(r,base)for r in g.seen[start:]],disabledCollectorFlagRva=disabled_flag,
        allocatedRegister=allocated,outputRegister=output,wholeFreshWrapperStored=True,activeCollectorAdmitted=False)


def prefix_program(rows,entry,header,*,base,prehook,constructor,allocate,barrier,existing,ff,reader_reuse=False,prehook_source=None,inline_constructor_prover=None,owned_partition=None,disabled_flag=None):
    """Initialized ordinary helper/inline header entry and actual allocation."""
    need('entry-mode',type(existing)is bool and type(ff)is bool and type(reader_reuse)is bool and header['mode']in('helper','inline'))
    need('callable-only-inline-constructor-prover',inline_constructor_prover is None or callable(inline_constructor_prover))
    helper=header['mode']=='helper';g=_Path(rows,entry);reader=header['readerRegister'];output=header['outputRegister'];local=header.get('headerLocalDisplacement')
    header_address=header.get('headerAddress')
    local_operand=f'[rsp+{local:#x}]'if local is not None else None
    if header_address is not None:
        need('exact-proved-RBP-header-address',header_address.get('baseRegister')=='rbp'and
            header_address.get('rspDisplacement')==local and type(header_address.get('displacement'))is int
            and header_address.get('baseAliasInstruction')in header['prologue'])
        local_operand=f"[rbp+{header_address['displacement']:#x}]"
    for site in header['prologue']:g.take(site=_absolute(site,base))
    saves={base+header['readerSave'][0],base+header['outputSave'][0]};flag=None;image_bases=[];zero_entry=None;zero_uses=[];zero_locals=[]
    zero_graph=owned_partition if owned_partition is not None else header.get('ordinaryZeroFamily')
    def comparison(row):
        op=row.get('memoryRegisterComparisonOperation',{})
        if op:return op
        # The mapper supplies no semantic record for this exact byte CMP.
        # Decode its one literal memory-first RIP/BL form independently.
        raw=ec.raw(row)
        if len(raw)==6 and raw[:2]==bytes.fromhex('381d'):
            return dict(bits=8,register='bl',memoryReadBytes=1,memoryWriteBytes=0,
                memoryIsLeftOperand=True,preservesRegisters=True,
                memoryAddress=dict(ripRelative=True,absoluteAddress=ec.va(row)+6+int.from_bytes(raw[2:],'little',signed=True)))
        return {}
    def zero_compare(row,bits,*,operand=None,flag_address=None):
        from scripts.game_data.memorypack.generated_header_sources import _owned_zero_source
        op=comparison(row);address=op.get('memoryAddress',{})
        need('literal-proved-zero-comparison',zero_entry is not None and op.get('bits')==bits and
            _ALIASES.get(op.get('register'))==zero_entry['register']and op.get('memoryReadBytes')==bits//8 and
            op.get('memoryWriteBytes')==0 and op.get('memoryIsLeftOperand')is True and op.get('preservesRegisters')is True and
            (operand is None and address.get('ripRelative')is True and type(address.get('absoluteAddress'))is int and
                (flag_address is None or address['absoluteAddress']==flag_address)or
             operand is not None and address.get('base')==operand[0]and address.get('displacement')==operand[1]and
                address.get('index')is None and not address.get('ripRelative')),row)
        proof=_owned_zero_source(rows,entry,[ec.va(row)],zero_entry['register'],base,zero_graph)
        zero_uses.append(dict(instruction=ec.site(row,base),bits=bits,zeroSource=proof))
        return address
    while saves or flag is None:
        row=g.row();at=ec.va(row);raw=ec.raw(row)
        if at in saves:g.take(site=_absolute(header['readerSave']if at==base+header['readerSave'][0]else header['outputSave'],base));saves.remove(at)
        else:
            match=re.fullmatch(r'xor (ebx), \1',row['text'])
            if match:
                from scripts.game_data.memorypack.generated_header_sources import _owned_zero_source
                register=_ALIASES[match[1]];by={ec.va(r):r for r in rows};next_at=at+len(raw)
                while next_at in by and control_transfer(by[next_at])['kind']=='next'and not comparison(by[next_at]):
                    next_at+=len(ec.raw(by[next_at]))
                need('zero-before-actual-byte-metadata-flag',zero_entry is None and flag is None and next_at in by and
                    comparison(by[next_at]).get('bits')==8)
                proof=_owned_zero_source(rows,entry,[next_at],register,base,zero_graph)
                need('literal-entry-whole-zero-definition',[at,raw.hex(' ')]in[[a,bytes.fromhex(h).hex(' ')]for a,h in proof['literalZeroInstructions']])
                zero_entry=dict(register=register,instruction=ec.site(row,base));g.take();continue
            address=row.get('addressOperation',{})
            if address.get('ripRelative')and address.get('absoluteAddress')==base:
                register=address.get('destination')
                need('actual-saved-nonvolatile-image-base',register in NONVOLATILE-{reader,output}and address.get('destinationBits')==64
                    and address.get('readsMemory')is False and address.get('writesFlags')is False and len(raw)==7 and raw[1]==0x8d
                    and raw[2]&0xc7==5 and at+7+int.from_bytes(raw[3:7],'little',signed=True)==base
                    and register not in{r['register']for r in image_bases},row)
                image_bases.append(dict(instruction=ec.site(row,base),register=register,imageBase=base));g.take();continue
            if zero_entry is not None and comparison(row):
                need('one-initialized-entry-flag',flag is None);flag=zero_compare(row,8)['absoluteAddress'];g.take()
            else:
                need('one-initialized-entry-flag',flag is None and len(raw)==7 and raw[:2]==b'\x80\x3d'and raw[-1]==0,row)
                flag=at+len(raw)+int.from_bytes(raw[2:6],'little',signed=True);g.take()
    g.branch(False)
    if prehook is None:
        if helper:
            expected={f'lea rdx, {local_operand}',f'mov byte {local_operand}, 0x0',f'mov rcx, {reader}'}
            if g.row()['text']=='xor ebp, ebp'and header.get('ordinaryZeroFamily')is not None:
                row=g.row();need('literal-direct-header-whole-EBP-zero',ec.raw(row)==bytes.fromhex('33ed'))
                zero_entry=dict(register='rbp',instruction=ec.site(row,base));g.take()
                while expected or g.row().get('memoryOperation',{}).get('direction')=='store':
                    row=g.row()
                    if row['text']in expected:expected.remove(row['text']);g.take();continue
                    move=row.get('memoryOperation',{});address=move.get('address',{});offset=address.get('displacement')
                    need('finite-direct-header-zero-local',len(zero_locals)<4 and move.get('direction')=='store'
                        and move.get('register')=='rbp'and move.get('memoryBytes')==8 and move.get('writesFlags')is False
                        and address.get('base')=='rsp'and address.get('index')is None and not address.get('ripRelative')
                        and type(offset)is int and 32<=offset<128 and offset not in[item['displacement']for item in zero_locals]
                        and ec.raw(row)==bytes.fromhex('48896c24')+bytes((offset,)))
                    home=offset-header['nullFrameBytes'];header_home=local-header['nullFrameBytes']
                    need('direct-header-zero-local-disjoint-frame',(-header['nullFrameBytes']<=home and home+8<=0 or 8<=home and home+8<=40)
                        and not home<=header_home<home+8
                        and all(home+8<=saved or saved+8<=home for saved in header['nullSavedHomes'].values())
                        and all(home+8<=old['entryRspOffset']or old['entryRspOffset']+8<=home for old in zero_locals))
                    from scripts.game_data.memorypack.generated_header_sources import _owned_zero_source
                    proof=_owned_zero_source(rows,entry,[ec.va(row)],'rbp',base,zero_graph)
                    need('same-direct-header-whole-zero-definition',zero_entry['instruction'][0]in[at-base for at,h in proof['literalZeroInstructions']])
                    zero_locals.append(dict(instruction=ec.site(row,base),displacement=offset,entryRspOffset=home,zeroSource=proof));g.take()
                need('complete-direct-header-null-locals',bool(zero_locals))
            else:
                for _ in range(3):
                    row=g.row();need('direct-header-exact-arguments',row['text']in expected,row);expected.remove(row['text']);g.take()
    elif g.row()['text']in(f'mov rdi, [{output}]',f'mov rbp, [{output}]',f'mov r15, [{output}]'):
        receiver=g.row()['text'].split()[1].rstrip(',')
        owned=prehook_source or{};program=owned.get('program',{})
        need('independent-own-inlined-prehook',not helper and type(owned.get('method'))is list and len(owned['method'])==4
            and base+owned['method'][3]==prehook and program.get('entryRspRestored')is True and program.get('serializedFieldWrites')==0
            and type(program.get('cacheSlot'))is int and 16<program['cacheSlot']<128 and receiver not in(reader,output))
        g.take(f'mov {receiver}, [{output}]');g.take(f'test {receiver}, {receiver}');g.branch(not existing)
        if existing:
            row=g.row();raw=ec.raw(row)
            if zero_entry is not None and comparison(row):
                zero_compare(row,8,flag_address=program.get('initializedFlag'))
            else:
                need('same-owned-inlined-prehook-metadata',len(raw)==7 and raw[:2]==b'\x80\x3d'and raw[-1]==0
                    and ec.va(row)+7+int.from_bytes(raw[2:6],'little',signed=True)==program.get('initializedFlag'),row)
            g.take();g.branch(False)
            if zero_entry is not None and comparison(g.row()):
                zero_compare(g.row(),64,operand=(receiver,program['cacheSlot']));g.take()
            else:g.take(f"cmp qword [{receiver}+{program['cacheSlot']:#x}], 0x0")
            g.branch(False)
    else:
        expected={f'mov rcx, [{output}]'}
        if helper:expected.add(f'mov byte {local_operand}, 0x0')
        if header.get('ordinaryZeroFamily')is not None:
            g.take(f'mov rcx, [{output}]');expected.remove(f'mov rcx, [{output}]')
            row=g.row();need('literal-ordinary-setup-EBP-zero',ec.raw(row)==bytes.fromhex('33ed')and row['text']=='xor ebp, ebp')
            zero_entry=dict(register='rbp',instruction=ec.site(row,base));g.take()
            while expected or g.row().get('memoryOperation',{}).get('direction')=='store':
                row=g.row()
                if row['text']in expected:expected.remove(row['text']);g.take();continue
                move=row.get('memoryOperation',{});address=move.get('address',{});offset=address.get('displacement')
                need('finite-owned-zero-stack-store',len(zero_locals)<4 and move.get('direction')=='store'
                    and move.get('register')=='rbp'and move.get('memoryBytes')==8 and move.get('writesFlags')is False
                    and address.get('base')=='rsp'and address.get('index')is None and not address.get('ripRelative')
                    and type(offset)is int and 32<=offset<128 and offset not in[row['displacement']for row in zero_locals]
                    and ec.raw(row)==bytes.fromhex('48896c24')+bytes((offset,)))
                home=offset-header['nullFrameBytes'];header_home=local-header['nullFrameBytes']
                need('zero-stack-local-disjoint-owned-frame',(-header['nullFrameBytes']<=home and home+8<=0 or 8<=home and home+8<=40)
                    and not home<=header_home<home+8
                    and all(home+8<=saved or saved+8<=home for saved in header['nullSavedHomes'].values())
                    and all(home+8<=old['entryRspOffset']or old['entryRspOffset']+8<=home for old in zero_locals))
                from scripts.game_data.memorypack.generated_header_sources import _owned_zero_source
                proof=_owned_zero_source(rows,entry,[ec.va(row)],'rbp',base,zero_graph)
                need('same-owned-setup-zero-definition',zero_entry['instruction'][0]in[at-base for at,h in proof['literalZeroInstructions']])
                zero_locals.append(dict(instruction=ec.site(row,base),displacement=offset,entryRspOffset=home,zeroSource=proof));g.take()
            need('complete-owned-initialized-zero-locals',bool(zero_locals))
        else:
            for _ in range(len(expected)):
                row=g.row();need('initial-output-and-header-local',row['text']in expected,row);expected.remove(row['text']);g.take()
        if header_address is not None and ec.raw(g.row())==bytes.fromhex('48c7453800000000'):
            need('own-UpperBody-prefix-null-local',helper and header['nullFrameBytes']==72
                and(header_address.get('baseRegister'),header_address.get('displacement'),
                    header_address.get('rspDisplacement'),reader,output)==('rbp',40,88,'rdi','rbx'))
            for displacement,home in((56,104),(-16,32),(-8,40)):
                row=g.row();need('exact-UpperBody-prefix-three-null-locals',ec.raw(row)==bytes.fromhex('48c745')
                    +displacement.to_bytes(1,'little',signed=True)+b'\0'*4)
                g.take();zero_locals.append(dict(instruction=ec.site(row,base),displacement=home,
                    entryRspOffset=home-72,zeroSource=None,literalZero=True,
                    frameAddress=dict(baseRegister='rbp',displacement=displacement,rspDisplacement=home)))
        g.take('test rcx, rcx');g.branch(not existing)
        if existing:
            g.take('xor edx, edx');g.call(prehook)
            if g.row()['text']=='nop':g.take()
            if control_transfer(g.row())['kind']=='jump':g.jump()
    if helper:
        if prehook is not None:g.take(f'lea rdx, {local_operand}');g.take(f'mov rcx, {reader}')
        g.call(base+header['helperTargetRva'])
        g.take('test al, al');g.branch(ff)
    else:
        g.take(site=_absolute(header['bufferPredicate'],base));edge=g.row();flow=control_transfer(edge)
        need('same-inline-buffer-predicate',ec.site(edge,base)==header['bufferEdge']and flow['kind']=='conditional'and flow['conditionCode']in(12,13));g.take()
        if flow['conditionCode']==13:g.at=flow['target']
        for site in header['sourceProgram']:
            row=g.row();need('same-owned-inline-header-update',ec.site(row,base)==site);flow=control_transfer(row);g.take()
            if flow['kind']=='conditional':
                need('same-inline-nonnegative-edge',flow['conditionCode']in(8,9))
                if flow['conditionCode']==9:g.at=flow['target']
        g.take(site=_absolute(header['nullCompare'],base));g.branch(ff)
    allocation=None
    if ff:
        for site in header['nullReturnProgram']:
            row=g.row();need('same-checked-FF-return',_absolute(site,base)==[ec.va(row),ec.raw(row).hex().upper()])
            flow=control_transfer(row);g.take()
            if flow['kind']=='jump':g.at=flow['target']
            elif flow['kind']=='conditional':
                need('same-disabled-collector-FF-edge',flow['conditionCode']==4 and header['nullReturn']['disabledCollectorFlagRva']is not None);g.at=flow['target']
        need('FF-full-return',control_transfer(g.seen[-1])['kind']=='return'or control_transfer(g.seen[-1])['kind']=='jump'and control_transfer(g.seen[-1])['target']==barrier)
    else:
        # Some register homes are saved only on the positive branch, before
        # the allocation/count join. Their exact entry-relative homes are
        # independently checked by frame_program over the complete path.
        while re.fullmatch(r'mov \[rsp\+0x[0-9a-f]+\], (?:rbx|rbp|rsi|rdi|r1[2345])|movaps \[rsp\+0x[0-9a-f]+\], xmm(?:[6-9]|1[0-5])',g.row()['text']):g.take()
        if zero_entry is not None and comparison(g.row()):
            zero_compare(g.row(),64,operand=(output,0));g.take()
        else:g.take(f'cmp qword [{output}], 0x0')
        g.branch(not existing)
        if not existing:
            use=g.row();raw=ec.raw(use);need('actual-wrapper-allocation-class-load',len(raw)==7 and raw[:3]==b'\x48\x8b\x0d',use);g.take()
            g.call(allocate)
            save=g.row();match=re.fullmatch(r'mov (rbx|rbp|rsi|rdi|r1[2345]), rax',save['text'])
            need('allocated-wrapper-preserved',match is not None and match[1]!=output and(reader_reuse or match[1]!=reader),save);allocation_register=match[1];g.take()
            g.take('test rax, rax');g.branch(False)
            inline=None;publication=None
            if inline_constructor_prover is not None and(ec.raw(g.row())[:2]==b'\x80\x3d'or
                    (allocation_register,output)in(('r15','rsi'),('r15','r14'))and owned_partition is not None and ec.raw(g.row())[:2]==b'\x38\x1d'):
                inline=inline_constructor_prover(rows,g.at,allocation_register,output)
                parsed=inline.get('program',{})
                need('complete-current-inline-constructor-role',inline.get('schema')=='endfield.generated-inline-constructor-fragment.v1'
                    and inline.get('completeSelectedConstructionFragment')is True and inline.get('sameFreshWrapperInOutput')is True
                    and inline.get('callerFrameProved')is False and inline.get('childGrammarAdmitted')is False
                    and type(inline.get('wrapperConstructorMethod'))is list and len(inline['wrapperConstructorMethod'])==4
                    and base+inline['wrapperConstructorMethod'][3]==constructor
                    and parsed.get('wrapperRegister')==allocation_register and parsed.get('outputRegister')==output
                    and(parsed.get('sameFreshOriginalInBothHolders')is True or
                        inline.get('wrappedType')=='Beyond.Gameplay.Core.CharInteractPerform.CharInteractPerformActor'
                        and inline.get('directHolderOnly')is True and parsed.get('directHolderOnly')is True
                        and parsed.get('baseHolderOffset')==16 and parsed.get('typedCacheOffset')is None
                        and parsed.get('sameFreshOriginalInOwnedHolder')is True))
                from scripts.game_data.memorypack.generated_vector_member_sources import selected_rows
                part=selected_rows(rows,parsed['selectedBytes'])
                need('same-entire-inline-constructor-selected-program',[ec.site(r,base)for r in part]==inline['selectedProgram']
                    and part and ec.va(part[0])==g.at and type(parsed.get('selectedEnd'))is int)
                for i,row in enumerate(part):
                    need('exact-inline-construction-owned-step',g.at==ec.va(row));flow=control_transfer(row);g.take(site=_absolute(ec.site(row,base),base))
                    next_at=ec.va(part[i+1])if i+1<len(part)else parsed['selectedEnd']
                    if flow['kind']=='conditional':need('inline-construction-exact-conditional-edge',next_at in(g.at,flow['target']));g.at=next_at
                    elif flow['kind']=='jump':need('inline-construction-exact-jump',next_at==flow['target']);g.at=next_at
                    else:need('inline-construction-only-ordinary-step',flow['kind']in('next','call')and next_at==g.at)
            else:
                g.take('xor edx, edx');need('actual-wrapper-constructor-receiver',g.row()['text']in('mov rcx, rax',f'mov rcx, {allocation_register}'));g.take();g.call(constructor)
                if g.row().get('memoryImmediateComparisonOperation'):
                    publication=_inline_output_publication(g,base=base,disabled_flag=disabled_flag,output=output,allocated=allocation_register)
                else:
                    pending={f'mov rcx, {output}',f'mov [{output}], {allocation_register}'}
                    for _ in range(2):
                        row=g.row();need('same-allocated-wrapper-output',row['text']in pending,row);pending.remove(row['text']);g.take()
                    g.call(barrier)
            allocation=dict(usageInstruction=ec.site(use,base),allocatedRegister=allocation_register,outputRegister=output)
            if inline is not None:allocation['inlineConstruction']=inline
            if publication is not None:allocation['inlineOutputPublication']=publication
            if g.row()['text']=='nop':g.take()
            flow=control_transfer(g.row())
            if flow['kind']=='jump':
                need('direct-allocation-exact-rejoin',flow['target']==base+(header.get('resultLoad')or header['memberCountInstruction'])[0]);g.jump()
        if header.get('resultLoad')is not None:g.take(site=_absolute(header['resultLoad'],base))
        need('prefix-exact-count-join',g.at==base+header['memberCountInstruction'][0],(hex(g.at),header['memberCountInstruction']))
    result=dict(selectedRows=g.seen,initializedFlag=flag,existing=existing,wrapperNull=ff,allocation=allocation,
        condition='Initialized current generated metadata; supplied output is null for allocation or contains a coherent compatible wrapper for reuse. Normal owned lifecycle/allocation/header ABI and disabled reference barrier; sufficient buffered input. FF and positive count paths are separate.')
    if image_bases:result['literalImageBaseLoads']=image_bases
    if zero_locals:result['initializedZeroLocals']=zero_locals
    if zero_entry is not None:result['entryZeroRegister']=dict(**zero_entry,actualUses=zero_uses)
    return result


def positive_program(rows,scope,base):
    """Every normal count/read/setter/return instruction must have a role."""
    by={ec.va(r):r for r in rows};path=[by[base+s[0]]for s in scope['selectedProgram']];at=0
    need('same-fresh-selected-source-bytes',all(ec.site(row,base)==site for row,site in zip(path,scope['selectedProgram'],strict=True)))
    if 'richProgram'in scope:
        need('complete-rich-current-program',scope['richProgram']['completeSelectedNormalProgram']and scope['richProgram']['selectedProgram']==scope['selectedProgram'])
        return path
    need('positive-start-count',ec.site(path[0],base)==scope['headerProof']['memberCountInstruction']);at+=1
    edge=control_transfer(path[at]);need('positive-exact-count-edge',edge['kind']=='conditional'and edge['conditionCode']in(4,5));at+=1
    for event,transfer in zip(scope['events'],scope['setterTransfers'],strict=True):
        source=base+event['instruction'][0];source_index=next(i for i,r in enumerate(path)if ec.va(r)==source)
        argument=ec.last_write(path,source_index,'rcx');need('reader-argument',argument is not None and argument['text']==f'mov rcx, {scope["headerProof"]["readerRegister"]}')
        allowed={ec.va(argument),base+transfer['wrapperLoad'][0]}
        context=event.get('context')
        if context is not None:allowed.add(base+context['instructionRva'])
        setup=path[at:source_index];need('complete-source-argument-setup',{ec.va(r)for r in setup}==allowed and len(setup)==len(allowed),(event['memberIndex'],setup,allowed));at=source_index
        need('selected-actual-source',ec.site(path[at],base)==event['instruction']);at+=1
        if 'transferProgram'in transfer:
            sites=transfer['transferProgram'];part=path[at:at+len(sites)]
            need('complete-inline-field-transfer',len(part)==len(sites)and[ec.site(r,base)for r in part]==sites)
            at+=len(sites)
        else:
            physical=by[base+transfer['setterCall'][0]];need('complete-six-instruction-setter-transfer',at+5<len(path)and path[at+5]is physical)
            at+=6
    tail=path[at:];terminal=scope.get('referenceBarrierTargetRva');end=control_transfer(path[-1])
    tail_barrier=terminal is not None and end['kind']=='jump'and end['target']==base+terminal
    need('complete-positive-return',bool(tail)and end['kind']=='return'or tail_barrier and (bool(tail)or scope['setterTransfers'][-1].get('referenceBarrierTail')==ec.site(path[-1],base)))
    for row in tail:
        text=row['text'];flow=control_transfer(row);move=row.get('memoryOperation',{});address=move.get('address',{})
        alias=re.fullmatch(r'lea r11, \[rsp\+0x([0-9a-f]+)\]',text);owned_alias=False
        if alias:
            displacement=int(alias[1],16)
            encodings=[bytes.fromhex('4c8d9c24')+displacement.to_bytes(4,'little')]
            if displacement<128:encodings.append(bytes.fromhex('4c8d5c24')+bytes((displacement,)))
            owned_alias=0<=displacement<256 and ec.raw(row)in encodings
        need('return-tail-only',flow['kind']in('jump','return')or text.startswith(('add rsp, ','pop '))or
            owned_alias or text=='mov rsp, r11'and ec.raw(row)==bytes.fromhex('498be3')or
            move.get('direction')=='load'and address.get('base')in('rsp','r11')and move.get('register')in NONVOLATILE,row)
    return path


def frame_program(path,*,header_local,source_locals=None,value_locals=None,hidden_locals=None,copied_locals=None,base=None,tail_barrier=None,value_lifetimes=None,tail_setter=None,header_result_load=None,initialized_zero_locals=None,header_address=None,source_frame_alias=None):
    """Exact saved homes; optional completed-source field stores bound reuse.

    The supplied field-store roles come from the independently complete fresh
    source VM. Every byte marker is rejoined to this selected caller path, and
    the full destination field must be covered before a spill home can die.
    Original register homes remain protected throughout the whole path.
    """
    need('one-explicit-terminal-frame-role',tail_setter is None or type(tail_setter)is int and tail_setter>0 and tail_barrier is None)
    tail_target=tail_barrier if tail_setter is None else tail_setter
    delta=0;homes={};original={r:True for r in NONVOLATILE};saved=[];header_home=None;local_homes=set();value_homes=[];frame_aliases={};frame_alias_proofs=[];entry_rbx_home=None
    vector_homes={};vector_original={f'xmm{n}':True for n in range(6,16)};hidden_homes=[];physical_hidden_homes=[];copy_homes=[];header_reuse=[];hidden_identities={}
    physical_copy_homes=[];copy_ends={};copy_lifetime_proofs=[];copy_lifetime_ends={}
    zero_sites={item['instruction'][0]:item for item in initialized_zero_locals or[]};zero_homes=set();zero_proofs=[]
    local_sites={item['zeroInstruction'][0]:item for item in source_locals or[]}
    value_sites={item['storeInstruction'][0]:item for item in value_locals or[]}
    hidden_sites={item['sourceInstruction'][0]:item for item in hidden_locals or[]}
    copy_sites={item['storeInstruction'][0]:item for item in copied_locals or[]}
    trigger_frame=source_frame_alias is not None and source_frame_alias.get('profile')=='mission-trigger44-RAX-RBP-frame.v1'
    upper_static_frame=source_frame_alias is not None and source_frame_alias.get('profile')=='animation-upper-extra-static-frame.v1'
    module_frame=source_frame_alias is not None and source_frame_alias.get('profile')=='finite-module-rbp-value-locals.v1'
    if source_frame_alias is not None:
        if module_frame:
            from scripts.game_data.memorypack.generated_module_frame_sources import require_descriptor
            require_descriptor(source_frame_alias)
            need('same-independent-Module-header-frame',isinstance(header_address,dict)
                and header_address.get('baseAliasInstruction')==source_frame_alias['baseAliasInstruction']
                and header_address.get('entryRspAliasInstruction')==source_frame_alias.get('entryRspAliasInstruction')
                and(header_address.get('displacement'),header_address.get('entryRspOffset'),header_local)in(
                    (24,16,88),(111,16,184))and header_address.get('rspDisplacement')==header_local)
        elif upper_static_frame:
            need('exact-finite-UpperBody-static-source-frame',header_address is not None and source_frame_alias==dict(
                profile='animation-upper-extra-static-frame.v1',baseRegister='rbp',entryRspOffset=-24,currentRspBytes=72,
                rspRelativeBaseOffset=48,baseAliasInstruction=header_address.get('baseAliasInstruction'))
                and header_address.get('displacement')==40 and header_address.get('entryRspOffset')==16
                and header_address.get('rspDisplacement')==header_local==88)
        elif trigger_frame:
            need('exact-finite-Trigger44-RBP-source-frame',header_address is not None and source_frame_alias==dict(
                profile='mission-trigger44-RAX-RBP-frame.v1',baseRegister='rbp',entryRspOffset=-95,currentRspBytes=168,rspRelativeBaseOffset=73,
                baseAliasInstruction=header_address.get('baseAliasInstruction'),entryRspAliasInstruction=header_address.get('entryRspAliasInstruction'))
                and header_address.get('baseAliasProfile')=='entry-RAX-RBP-95-header.v1'and header_address.get('displacement')==103
                and header_address.get('entryRspOffset')==8 and header_address.get('rspDisplacement')==header_local==176)
        else:need('exact-finite-RBP-three-Vector3-source-frame',header_address is not None and source_frame_alias==dict(
            profile='rbp-frame-three-Vector3.v1',baseAliasInstruction=header_address.get('baseAliasInstruction'),
            baseRegister='rbp',entryRspOffset=-8,currentRspBytes=72,rspRelativeBaseOffset=64,
            hiddenLocalBytes=12,hiddenLocalDisplacement=48,argumentLocalDisplacement=32,storedSourceSlices=[[0,8],[8,4]])
            and header_address.get('baseRegister')=='rbp'and header_address.get('displacement')==16
            and header_address.get('entryRspOffset')==8 and header_address.get('rspDisplacement')==header_local==80)
    if local_sites or value_sites or hidden_sites or copy_sites or zero_sites:need('explicit-source-local-image-base',type(base)is int);local_base=base
    need('explicit-complete-field-store-lifetimes',value_lifetimes is None or type(value_lifetimes)is list)
    lifetime_ends={};value_ends={};physical_value_homes=[];lifetime_proofs=[];hidden_ends={};hidden_lifetime_proofs=[];hidden_lifetime_ends={}
    if value_lifetimes is not None:
        indices={ec.va(row):i for i,row in enumerate(path)};need('unique-frame-selected-boundaries',len(indices)==len(path))
        for site,item in value_sites.items():
            if 'memberIndex'not in item or base+site not in indices:continue
            member=item['memberIndex'];width=item['fieldBytes'];start=indices[base+site]
            need('literal-spilled-member-byte-range',type(member)is int and member>=0 and type(width)is int and 0<width<=16)
            stores=[s for s in value_lifetimes if s['memberIndex']==member];covered=[];positions=[]
            for store in stores:
                instruction=store['instruction'];address=base+instruction[0]
                need('lifetime-current-selected-store-bytes',address in indices and ec.site(path[indices[address]],base)==instruction)
                offset,count=store['sourceOffset'],store['storedBytes']
                need('lifetime-literal-field-byte-slice',type(offset)is int and type(count)is int and 0<=offset<offset+count<=width)
                covered.extend(range(offset,offset+count));positions.append(indices[address])
            need('lifetime-entire-field-stored-after-spill',sorted(covered)==list(range(width))and positions and min(positions)>start)
            end=max(positions);lifetime_ends[site]=end
            lifetime_proofs.append(dict(memberIndex=member,displacement=item['displacement'],bytes=item['bytes'],
                storeInstruction=item['storeInstruction'],fieldBytes=width,fieldStores=stores,liveThroughInstruction=ec.site(path[end],base)))
        if hidden_sites:
            from scripts.game_data.memorypack.generated_field_lifetime_sources import hidden_certificates
            active_hidden=[item for site,item in hidden_sites.items()if base+site in indices]
            hidden_lifetime_proofs=hidden_certificates(path,base=base,hidden_locals=active_hidden,field_stores=value_lifetimes)
            hidden_lifetime_ends={p['sourceInstruction'][0]:p['liveThroughPathIndex']for p in hidden_lifetime_proofs}
            if module_frame and source_frame_alias.get('ownerType')=='Beyond.Gameplay.Core.CharInteractPerform.CharNpcMontageActionData':
                from scripts.game_data.memorypack.generated_field_lifetime_sources import montage_copy_certificates
                active_copies=[item for site,item in copy_sites.items()if base+site in indices]
                copy_lifetime_proofs=montage_copy_certificates(path,base=base,hidden_locals=active_hidden,
                    copied_locals=active_copies,hidden_certificates=hidden_lifetime_proofs)
                copy_lifetime_ends={c['storeInstruction'][0]:p['liveThroughPathIndex']for p in copy_lifetime_proofs for c in p['copiedLocals']}
    for index,row in enumerate(path):
        value_homes=[span for span in value_homes if value_ends.get(span,len(path))>=index]
        hidden_homes=[span for span in hidden_homes if hidden_ends.get(span,len(path))>=index]
        copy_homes=[span for span in copy_homes if copy_ends.get(span,len(path))>=index]
        text=row['text'];move=row.get('memoryOperation',{});address=move.get('address',{});flow=control_transfer(row)
        entry_rbp=header_address is not None and header_address.get('baseAliasProfile')=='entry-RAX-RBP-95-header.v1'
        if index==0 and not entry_rbp and ec.raw(row)==bytes.fromhex('488bc4')and len(path)>1 and ec.raw(path[1])==bytes.fromhex('48895820'):
            need('exact-entry-RAX-RBX-home-pair',text=='mov rax, rsp'and len(path)>1 and delta==0
                and ec.va(path[1])==ec.va(row)+3 and ec.raw(path[1])==bytes.fromhex('48895820')
                and path[1]['text']=='mov [rax+0x20], rbx',row)
            entry_rbx_home=dict(instructions=[ec.site(row,base or 0),ec.site(path[1],base or 0)],register='rbx',entryRspOffset=32,bytes=8)
            continue
        if index==1 and entry_rbx_home is not None:
            need('entry-RAX-whole-original-RBX-save',delta==0 and original['rbx']and not homes
                and ec.raw(row)==bytes.fromhex('48895820')and text=='mov [rax+0x20], rbx'
                and(not move or move.get('direction')=='store'and move.get('memoryBytes')==8
                    and move.get('register')=='rbx'and move.get('writesFlags')is False
                    and address.get('base')=='rax'and address.get('index')is None
                    and address.get('displacement')==32 and not address.get('ripRelative')),row)
            homes['rbx']=32;saved.append(('rbx',32));continue
        if text=='mov rax, rsp'and entry_rbp:
            need('exact-entry-RAX-frame-alias',delta==0 and ec.raw(row)==bytes.fromhex('488bc4')
                and header_address.get('entryRspAliasInstruction')==ec.site(row,base or 0)and'rax'not in frame_aliases,row)
            frame_aliases['rax']=0;continue
        if text=='lea rbp, [rax-0x5f]'and entry_rbp:
            need('exact-entry-RAX-to-RBP-frame-base',delta==-8 and homes.get('rbp')==-8 and original['rbp']
                and frame_aliases.get('rax')==0 and ec.raw(row)==bytes.fromhex('488d68a1')
                and header_address.get('baseAliasInstruction')==ec.site(row,base or 0)
                and(header_address.get('displacement'),header_address.get('entryRspOffset'),header_local)in((103,8,176),(111,16,184))
                and header_address.get('rspDisplacement')==header_local,row)
            frame_aliases['rbp']=-95;original['rbp']=False
            frame_alias_proofs.append(dict(instruction=ec.site(row,base or 0),entryRspOffset=-95));continue
        if text=='mov rbp, rsp'and header_address is not None:
            need('exact-owned-RBP-header-frame-alias',ec.raw(row)==bytes.fromhex('488bec')and
                header_address.get('baseRegister')=='rbp'and header_address.get('baseAliasInstruction')==ec.site(row,base or 0)
                and type(homes.get('rbp'))is int and delta<=homes['rbp']<0 and homes['rbp']%8==0
                and original['rbp']and 'rbp'not in frame_aliases,row)
            frame_aliases['rbp']=delta;original['rbp']=False
            frame_alias_proofs.append(dict(instruction=ec.site(row,base or 0),entryRspOffset=delta));continue
        frame_alias=re.fullmatch(r'lea r11, \[rsp\+0x([0-9a-f]+)\]',text)
        if frame_alias:
            displacement=int(frame_alias[1],16)
            encodings={bytes.fromhex('4c8d9c24')+displacement.to_bytes(4,'little')}if 0<=displacement<2**31 else set()
            if 0<=displacement<128:encodings.add(bytes.fromhex('4c8d5c24')+bytes((displacement,)))
            need('exact-owned-frame-base-alias',ec.raw(row)in encodings and delta<=delta+displacement<=0,row)
            frame_aliases['r11']=delta+displacement;frame_alias_proofs.append(dict(instruction=ec.site(row,base or 0),entryRspOffset=delta+displacement));continue
        if flow['kind']=='call'or _writes_register(row,'r11'):frame_aliases.pop('r11',None)
        if flow['kind']=='call'or _writes_register(row,'rax'):frame_aliases.pop('rax',None)
        if text=='mov rsp, r11':
            need('exact-current-frame-base-stack-restore',ec.raw(row)==bytes.fromhex('498be3')and 'r11'in frame_aliases,row)
            delta=frame_aliases['r11'];continue
        if text.startswith('push '):
            register=text[5:];need('saved-push-original',register in NONVOLATILE and original[register]);delta-=8;need('one-saved-home',register not in homes);homes[register]=delta;saved.append((register,delta));continue
        if text.startswith('pop '):
            register=text[4:];need('matching-popped-home',homes.get(register)==delta);original[register]=True;delta+=8;continue
        if text.startswith('sub rsp, '):delta-=int(text.split(', ')[1],16);continue
        if text.startswith('add rsp, '):delta+=int(text.split(', ')[1],16);continue
        if zero_sites and ec.va(row)-local_base in zero_sites:
            item=zero_sites[ec.va(row)-local_base];displacement=item['displacement'];home=delta+displacement;proof=item.get('zeroSource',{})
            if'literalZero'in item:
                from scripts.game_data.memorypack.animation_extra_parent_sources import validate_zero
                validate_zero(row,item,base)
                need('own-extra-prefix-zero-frame-home',home==item['entryRspOffset']
                    and(not item['literalZero']or upper_static_frame and frame_aliases.get('rbp')==-24
                        and frame_aliases['rbp']+item['frameAddress']['displacement']==home))
            else:
                need('exact-owned-prefix-zero-local',ec.site(row,base)==item['instruction']and ec.raw(row)==bytes.fromhex('48896c24')+bytes((displacement,))
                    and move.get('direction')=='store'and move.get('register')=='rbp'and move.get('memoryBytes')==8
                    and home==item['entryRspOffset']and proof.get('register')=='rbp'and proof.get('value')==0
                    and proof.get('zeroOnEveryOrdinaryPath')is True and ec.va(row)in proof.get('sites',[]))
            need('initialized-zero-local-disjoint-owned-frame',(delta<=home and home+8<=0 or 8<=home and home+8<=40)
                and all(home+8<=old or old+8<=home for old in homes.values())
                and all(home+8<=old or old+16<=home for old in vector_homes.values())
                and(header_home is None or not home<=header_home<home+8)
                and all(home+8<=old or old+size<=home for old,size in value_homes+hidden_homes+copy_homes)
                and all(old==home or home+8<=old or old+8<=home for old in zero_homes))
            zero_homes.add(home);zero_proofs.append(dict(item));continue
        if hidden_sites and ec.va(row)-local_base in hidden_sites:
            item=hidden_sites[ec.va(row)-local_base];displacement=item['displacement'];size=item['bytes'];home=delta+displacement
            if item.get('frameAddress')is not None:
                if module_frame:
                    from scripts.game_data.memorypack.generated_module_frame_sources import require_hidden
                    actual=item['frameAddress'];require_hidden(source_frame_alias,item['memberIndex'],item.get('nominalTypeName'),size,displacement)
                    need('same-owned-Module-RBP-hidden-home',delta==-source_frame_alias['currentRspBytes']
                        and frame_aliases.get('rbp')==source_frame_alias['entryRspOffset']and type(item.get('nominalTypeDefinition'))is int
                        and actual==dict(baseRegister='rbp',displacement=displacement-source_frame_alias['rspRelativeBaseOffset'],rspDisplacement=displacement)
                        and frame_aliases['rbp']+actual['displacement']==home)
                elif upper_static_frame:
                    from scripts.game_data.memorypack.animation_extra_dictionary_sources import TYPES
                    actual=item['frameAddress']
                    need('same-owned-UpperBody-static-reference-home',size==8 and delta==-72 and frame_aliases.get('rbp')==-24
                        and item.get('sourceAbi')=='void-byref-reference8'and item.get('nominalTypeName')in TYPES
                        and type(item.get('nominalTypeDefinition'))is int
                        and(actual.get('displacement'),displacement)in((56,104),(-16,32),(-8,40))
                        and actual==dict(baseRegister='rbp',displacement=actual['displacement'],rspDisplacement=displacement)
                        and frame_aliases['rbp']+actual['displacement']==home)
                elif trigger_frame:
                    actual=item['frameAddress'];expected=(44,64,-9,'Beyond.Gameplay.Core.TriggerShapeData')if size==44 else(12,48,-25,'UnityEngine.Vector3')
                    need('same-owned-Trigger-RBP-hidden-home',delta==-168 and frame_aliases.get('rbp')==-95
                        and(size,displacement,actual.get('displacement'),item.get('nominalTypeName'))==expected
                        and type(item.get('nominalTypeDefinition'))is int
                        and actual==dict(baseRegister='rbp',displacement=expected[2],rspDisplacement=displacement)
                        and frame_aliases['rbp']+actual['displacement']==home)
                else:need('same-owned-RBP-Vector3-hidden-home',source_frame_alias is not None and delta==-72 and frame_aliases.get('rbp')==-8
                    and size==12 and displacement==48 and item.get('memberIndex')in(0,1,2)
                    and item['frameAddress']==dict(baseRegister='rbp',displacement=-16,rspDisplacement=48)
                    and frame_aliases['rbp']-16==home)
            named24=size==24 and item.get('nominalTypeName')=='Beyond.Gameplay.View.CameraControlStateInitialParam'and type(item.get('nominalTypeDefinition'))is int
            named32=size==32 and item.get('nominalTypeName')=='Cinemachine.CinemachineImpulseManager+EnvelopeDefinition'and type(item.get('nominalTypeDefinition'))is int
            body32=size==32 and item.get('nominalTypeName')=='Beyond.Gameplay.BodyTypeDef'and type(item.get('nominalTypeDefinition'))is int
            named36=size==36 and item.get('nominalTypeName')=='Beyond.Montage.AnimationClipAsyncInfo'and type(item.get('nominalTypeDefinition'))is int
            bounds36=size==36 and item.get('nominalTypeName')=='Beyond.Gameplay.TrackingBounds'and type(item.get('nominalTypeDefinition'))is int
            trigger44=size==44 and item.get('nominalTypeName')=='Beyond.Gameplay.Core.TriggerShapeData'and type(item.get('nominalTypeDefinition'))is int
            named40=size==40 and item.get('nominalTypeName')=='Beyond.Gameplay.Core.SmartTargetSelectSetting'and type(item.get('nominalTypeDefinition'))is int
            sk_morph40=size==40 and item.get('nominalTypeName')=='Beyond.Gameplay.Core.SkMorphPlaySetting'and type(item.get('nominalTypeDefinition'))is int
            entity40=size==40 and item.get('nominalTypeName')=='Beyond.Gameplay.Core.EntityPtr'and type(item.get('nominalTypeDefinition'))is int and item.get('opaqueRuntimeStorageRanges')==[[24,40]]and item.get('selectedBarrierValueOffsets')==[24]and item.get('runtimeReferenceLayoutAdmitted')is False and item.get('completeRuntimePaddingMapAdmitted')is False
            named56=size==56 and item.get('nominalTypeName')=='Beyond.Gameplay.View.Animation.AlphaBlend'and type(item.get('nominalTypeDefinition'))is int
            from scripts.game_data.memorypack.skill_gait_dictionary_sources import TYPE as GAIT_DICTIONARY
            from scripts.game_data.memorypack.animation_extra_dictionary_sources import TYPES as EXTRA_DICTIONARIES
            static8=size==8 and item.get('sourceAbi')=='void-byref-reference8'and item.get('nominalTypeName')in({GAIT_DICTIONARY}|set(EXTRA_DICTIONARIES))and type(item.get('nominalTypeDefinition'))is int and item.get('initiallyZeroLocalRequired')is True
            if static8:
                need('actual-static-output-local-was-initialized-null',home in zero_homes)
                zero_homes.remove(home)
            need('hidden-result-actual-source-call',flow['kind']=='call'and ec.site(row,base)==item['sourceInstruction']and type(size)is int and(size in(12,16)or named24 or named32 or body32 or named36 or bounds36 or trigger44 or named40 or sk_morph40 or entity40 or named56 or static8)and 32<=displacement<256)
            need('hidden-result-owned-stack',delta<=home and home+size<=0 or 8<=home and home+size<=40)
            need('hidden-result-disjoint-live-frame',all(home+size<=old or old+8<=home for old in homes.values())and
                all(home+size<=old or old+16<=home for old in vector_homes.values())and
                (header_home is None or not home<=header_home<home+size)and all(home+size<=old or old+8<=home for old in local_homes)and
                all(home+size<=old or old+count<=home for old,count in value_homes+copy_homes),
                dict(memberIndex=item.get('memberIndex'),home=home,bytes=size,originalHomes=homes,vectorHomes=vector_homes,
                    headerHome=header_home,referenceHomes=sorted(local_homes),valueHomes=value_homes,copyHomes=copy_homes))
            hidden_homes.append((home,size))
            physical_hidden_homes.append((home,size))
            hidden_identities[(home,size)]=(item.get('memberIndex'),item.get('nominalTypeName'),item.get('nominalTypeDefinition'))
            if ec.va(row)-local_base in hidden_lifetime_ends:hidden_ends[(home,size)]=hidden_lifetime_ends[ec.va(row)-local_base]
        if copy_sites and ec.va(row)-local_base in copy_sites:
            item=copy_sites[ec.va(row)-local_base];displacement=item['displacement'];size=item['bytes'];home=delta+displacement
            named24=item.get('nominalTypeName')=='Beyond.Gameplay.View.CameraControlStateInitialParam'and type(item.get('nominalTypeDefinition'))is int
            query=item.get('nominalTypeName')=='Beyond.Gameplay.Core.GameplayTagQuery'and type(item.get('nominalTypeDefinition'))is int
            quaternion=item.get('nominalTypeName')=='UnityEngine.Quaternion'and type(item.get('nominalTypeDefinition'))is int
            aabb=item.get('nominalTypeName')=='Beyond.AABB'and type(item.get('nominalTypeDefinition'))is int
            body32=item.get('nominalTypeName')=='Beyond.Gameplay.BodyTypeDef'and type(item.get('nominalTypeDefinition'))is int
            named56=item.get('nominalTypeName')=='Beyond.Gameplay.View.Animation.AlphaBlend'and type(item.get('nominalTypeDefinition'))is int
            bounds36=item.get('nominalTypeName')=='Beyond.Gameplay.TrackingBounds'and type(item.get('nominalTypeDefinition'))is int
            entity40=item.get('nominalTypeName')=='Beyond.Gameplay.Core.EntityPtr'and type(item.get('nominalTypeDefinition'))is int
            rbp_vector=item.get('frameAddress')is not None;module_self_copy=False
            if rbp_vector:
                if module_frame:
                    from scripts.game_data.memorypack.generated_module_frame_sources import copy_spec
                    actual=item['frameAddress'];spec=copy_spec(source_frame_alias,item['memberIndex'],item.get('nominalTypeName'),size,
                        item.get('sourceOffset'),item.get('sourceRegister'),actual.get('displacement'))
                    need('same-owned-Module-RBP-argument-home',delta==-source_frame_alias['currentRspBytes']
                        and frame_aliases.get('rbp')==source_frame_alias['entryRspOffset']and type(item.get('nominalTypeDefinition'))is int
                        and actual==dict(baseRegister='rbp',displacement=displacement-source_frame_alias['rspRelativeBaseOffset'],rspDisplacement=displacement)
                        and frame_aliases['rbp']+actual['displacement']==home)
                    expected=bytes.fromhex(spec['instructionHex']);module_self_copy=spec['selfCopy']
                    if module_self_copy:need('same-owned-LangKey-hidden-self-copy',size==16 and item.get('sourceOffset')==0
                        and(home,size)in hidden_homes and hidden_identities.get((home,size))==(
                            item['memberIndex'],item['nominalTypeName'],item['nominalTypeDefinition']))
                elif trigger_frame:
                    field=item.get('nominalTypeName');offset=item.get('sourceOffset');register=item.get('sourceRegister')
                    encodings={('Beyond.Gameplay.Core.TriggerShapeData',16,0,'xmm0',112):'0f294527',
                        ('Beyond.Gameplay.Core.TriggerShapeData',16,16,'xmm1',128):'0f294d37',
                        ('Beyond.Gameplay.Core.TriggerShapeData',8,32,'xmm0',144):'f20f114547',
                        ('Beyond.Gameplay.Core.TriggerShapeData',4,40,'rax',152):'89454f',
                        ('UnityEngine.Vector3',8,0,'xmm0',32):'f20f1145d7',('UnityEngine.Vector3',4,8,'rax',40):'8945df'}
                    encoding=encodings.get((field,size,offset,register,displacement))
                    need('same-owned-Trigger-RBP-argument-copy',delta==-168 and frame_aliases.get('rbp')==-95
                        and encoding is not None and type(item.get('nominalTypeDefinition'))is int
                        and item['frameAddress']==dict(baseRegister='rbp',displacement=displacement-73,rspDisplacement=displacement)
                        and frame_aliases['rbp']+item['frameAddress']['displacement']==home)
                    expected=bytes.fromhex(encoding)
                else:
                    need('same-owned-RBP-Vector3-argument-copy',source_frame_alias is not None and delta==-72 and frame_aliases.get('rbp')==-8
                    and item.get('nominalTypeName')=='UnityEngine.Vector3'and item.get('memberIndex')in(0,1,2)
                    and(size,item.get('sourceOffset'),displacement)in((8,0,32),(4,8,40))
                    and item['frameAddress']==dict(baseRegister='rbp',displacement=displacement-64,rspDisplacement=displacement)
                    and frame_aliases['rbp']+item['frameAddress']['displacement']==home
                    and any(h.get('memberIndex')==item['memberIndex']and h.get('bytes')==12 and h.get('displacement')==48 for h in hidden_locals or[]))
                    expected=bytes.fromhex('f20f1145e0'if size==8 else'8945e8')
            elif bounds36:
                register=item.get('sourceRegister')
                need('exact-Bounds36-local-slice',(size,item.get('sourceOffset'),register)in((16,0,'xmm0'),(16,16,'xmm1'),(4,32,'rax')))
                expected=bytes.fromhex('0f294424'if size==16 and register=='xmm0'else'0f294c24'if size==16 else'894424')+bytes((displacement,))
            elif named24:
                need('exact-named24-local-slice',(size,item.get('sourceOffset'))in((16,0),(8,16)))
                expected=bytes.fromhex('0f294424'if size==16 else'f20f114c24')+bytes((displacement,))
            elif query:
                need('exact-owned-Query16-frame-self-copy',size==16 and item.get('sourceOffset')==0
                    and item.get('sameOwnedHiddenLocalCopy')is True and(home,size)in hidden_homes
                    and hidden_identities.get((home,size))==(item.get('memberIndex'),item['nominalTypeName'],item['nominalTypeDefinition']),item)
                expected=bytes.fromhex('f30f7f4424')+bytes((displacement,))
            elif quaternion:
                from scripts.game_data.memorypack.leveldata_quaternion_forwarder_sources import owns_member
                need('exact-owned-Quaternion16-frame-self-copy',owns_member(item.get('parentType'),item.get('fieldName'),'UnityEngine.Quaternion')
                    and(size,displacement,item.get('sourceOffset'),item.get('sourceRegister'))==(16,48,0,'xmm0')
                    and item.get('sameOwnedHiddenLocalCopy')is True and(home,size)in hidden_homes
                    and hidden_identities.get((home,size))==(item.get('memberIndex'),item['nominalTypeName'],item['nominalTypeDefinition']),item)
                expected=bytes.fromhex('f30f7f442430')
            elif aabb:
                from scripts.game_data.memorypack.generated_aabb_field_sources import owns_member
                need('exact-owned-AABB16-frame-self-copy',owns_member(item.get('parentType'),item.get('fieldName'),'Beyond.AABB')
                    and(size,displacement,item.get('sourceOffset'),item.get('sourceRegister'))==(16,32,0,'xmm0')
                    and item.get('sameOwnedHiddenLocalCopy')is True and(home,size)in hidden_homes
                    and hidden_identities.get((home,size))==(item.get('memberIndex'),item['nominalTypeName'],item['nominalTypeDefinition']),item)
                expected=bytes.fromhex('660f7f442420')
            elif body32:
                register=item.get('sourceRegister');offset=item.get('sourceOffset')
                need('exact-owned-BodyType32-frame-copy',size==16 and(offset,register)in((0,'xmm0'),(16,'xmm1'))
                    and any(count==32 and hidden_identities.get((old,count))==(
                        item.get('memberIndex'),item['nominalTypeName'],item['nominalTypeDefinition'])for old,count in hidden_homes),item)
                expected=bytes.fromhex('0f294424'if register=='xmm0'else'0f294c24')+bytes((displacement,))
            elif entity40:
                key=(size,item.get('sourceOffset'),item.get('sourceRegister'),displacement)
                encodings={(16,0,'xmm0',32):'0f29442420',(16,16,'xmm1',48):'0f294c2430',
                    (8,32,'xmm0',64):'f20f11442440'}
                need('same-owned-opaque-Entity40-frame-copy',key in encodings
                    and item.get('originalHiddenLocal')==dict(displacement=80,bytes=40)
                    and item.get('opaqueRuntimeBitsPreserved')is True
                    and(delta+80,40)in hidden_homes and hidden_identities.get((delta+80,40))==(
                        item.get('memberIndex'),item['nominalTypeName'],item['nominalTypeDefinition']),item)
                expected=bytes.fromhex(encodings[key])
            elif named56:
                register=item.get('sourceRegister')
                need('exact-Alpha56-local-slice',(size,item.get('sourceOffset'),register)in
                    ((16,0,'xmm0'),(16,16,'xmm1'),(16,32,'xmm0'),(8,48,'xmm1'))
                    and 32<=displacement<256 and(size!=16 or(8+home)%16==0))
                number=0 if register=='xmm0'else 1;short=displacement<128
                expected=bytes.fromhex('0f29'if size==16 else'f20f11')+bytes(((0x44 if short else 0x84)|(number<<3),0x24))+displacement.to_bytes(1 if short else 4,'little')
            else:expected=(bytes.fromhex('f20f114424')if size==8 else bytes.fromhex('894424'))+bytes((displacement,))
            need('exact-hidden-value-local-copy',type(size)is int and(size in(4,8)or(named24 or query or quaternion or aabb or body32 or named56 or bounds36 or entity40 or(trigger_frame or module_frame)and rbp_vector)and size==16)and 32<=displacement<(256 if named56 or(trigger_frame or module_frame)and rbp_vector else 128)and ec.site(row,base)==item['storeInstruction']and ec.raw(row)==expected,item)
            need('copied-value-owned-stack',delta<=home and home+size<=0 or 8<=home and home+size<=40)
            need('copied-value-disjoint-live-frame',all(home+size<=old or old+8<=home for old in homes.values())and all(home+size<=old or old+16<=home for old in vector_homes.values())and
                (header_home is None or not home<=header_home<home+size)and all(home+size<=old or old+8<=home for old in local_homes)
                and all(home+size<=old or old+count<=home for old,count in value_homes)
                and all(home+size<=old or old+count<=home for old,count in hidden_homes if not((query or quaternion or aabb or module_self_copy)and(old,count)==(home,size))),
                dict(copy=item,home=home,bytes=size,originalHomes=homes,vectorHomes=vector_homes,headerHome=header_home,
                    referenceHomes=sorted(local_homes),valueHomes=value_homes,hiddenHomes=hidden_homes))
            if not module_self_copy:
                copy_homes.append((home,size));physical_copy_homes.append((home,size))
                if ec.va(row)-local_base in copy_lifetime_ends:copy_ends[(home,size)]=copy_lifetime_ends[ec.va(row)-local_base]
            continue
        vector_store=re.fullmatch(r'movaps \[rsp\+0x([0-9a-f]+)\], (xmm(?:[6-9]|1[0-5]))',text)
        vector_load=re.fullmatch(r'movaps (xmm(?:[6-9]|1[0-5])), \[rsp\+0x([0-9a-f]+)\]',text)
        if vector_store or vector_load:
            register=vector_store[2]if vector_store else vector_load[1];displacement=int(vector_store[1]if vector_store else vector_load[2],16);home=delta+displacement
            number=int(register[3:]);prefix=(bytes((0x44,))if number>=8 else b'')+bytes((0x0f,0x29 if vector_store else 0x28))
            encodings={prefix+bytes((0x84|((number&7)<<3),0x24))+displacement.to_bytes(4,'little')}if 0<=displacement<256 else set()
            if 0<=displacement<128:encodings.add(prefix+bytes((0x44|((number&7)<<3),0x24,displacement)))
            need('exact-aligned-vector-home-instruction',ec.raw(row)in encodings and (8+home)%16==0,row)
            if vector_store:
                need('original-vector-saved-once',vector_original[register]and register not in vector_homes and displacement>=32 and delta<=home and home+16<=0)
                need('vector-home-disjoint-live-frame',all(home+16<=old or old+8<=home for old in homes.values())and
                    all(home+16<=old or old+16<=home for old in vector_homes.values())and
                    (header_home is None or not home<=header_home<home+16)and all(home+16<=old or old+8<=home for old in local_homes)and
                    all(home+16<=old or old+count<=home for old,count in value_homes+hidden_homes+copy_homes))
                vector_homes[register]=home
            else:
                need('exact-original-vector-home-restore',vector_homes.get(register)==home);vector_original[register]=True
            continue
        if value_sites and ec.va(row)-local_base in value_sites:
            item=value_sites[ec.va(row)-local_base];displacement=item['displacement'];size=item['bytes'];home=delta+displacement
            vector2=item.get('nominalTypeName')=='UnityEngine.Vector2'and type(item.get('nominalTypeDefinition'))is int and item.get('sourceMode')=='typed-register-vector2'and item.get('resultRegister')=='rax'and item.get('fieldBytes')==8 and item.get('sourceOffset')==0
            expected=bytes.fromhex('4889442460')if vector2 else bytes.fromhex('f20f114424'if size==8 else'0f114424')+bytes((displacement,))
            need('complete-finite-value-local-store',type(size)is int and size in(8,16)and 32<=displacement<128 and
                (not vector2 or size==8 and displacement==96)and ec.site(row,base)==item['storeInstruction']and ec.raw(row)==expected)
            need('value-local-owned-stack',delta<=home and home+size<=0 or 8<=home and home+size<=40)
            if header_result_load is not None and header_home is not None and home<=header_home<home+size:
                need('finite-current-Vector2-header-home-reuse'if vector2 else'finite-current-Int3-header-home-reuse',(item.get('nominalTypeName')=='UnityEngine.Vector3Int'
                    and type(item.get('nominalTypeDefinition'))is int and item.get('fieldBytes')==12 or vector2)and size==8
                    and displacement==header_local and home==header_home)
                lifetimes=[p for p in lifetime_proofs if p['memberIndex']==item.get('memberIndex')and p['storeInstruction']==item['storeInstruction']]
                need('complete-independent-replacement-field-lifetime',len(lifetimes)==1)
                from scripts.game_data.memorypack.generated_header_lifetime_sources import prove
                certificate=prove(path,base=base,header_local=header_local,result_load=header_result_load,reuse_store=item['storeInstruction'])
                header_reuse.append(dict(certificate,entryRspOffset=home,sourceMemberIndex=item['memberIndex'],fieldLifetime=lifetimes[0]))
                header_home=None
            need('value-local-disjoint-original-homes',all(home+size<=old or old+8<=home for old in homes.values())and
                (header_home is None or not home<=header_home<home+size)and all(home+size<=old or old+8<=home for old in local_homes)and
                all(home+size<=old or old+count<=home for old,count in value_homes+hidden_homes+copy_homes)and all(home+size<=old or old+16<=home for old in vector_homes.values()),
                dict(instruction=ec.site(row,base or 0),memberIndex=item.get('memberIndex'),entryRspOffset=home,bytes=size,
                    currentRspOffset=delta,originalHomes=homes,headerHome=header_home,referenceHomes=sorted(local_homes),
                    valueHomes=value_homes,hiddenHomes=hidden_homes,copyHomes=copy_homes,vectorHomes=vector_homes))
            value_homes.append((home,size));physical_value_homes.append((home,size))
            if ec.va(row)-local_base in lifetime_ends:value_ends[(home,size)]=lifetime_ends[ec.va(row)-local_base]
            continue
        if local_sites and ec.va(row)-local_base in local_sites:
            item=local_sites[ec.va(row)-local_base];displacement=item['displacement'];home=delta+displacement
            need('complete-source-local-zero',item['bytes']==8 and displacement>=32 and text==f'mov qword [rsp+{displacement:#x}], 0x0'and ec.raw(row).hex().upper()==item['zeroInstruction'][1])
            need('source-local-owned-stack',delta<=home and home+8<=0 or 8<=home and home+8<=40)
            need('source-local-disjoint-original-homes',all(home+8<=old or old+8<=home for old in homes.values())and(header_home is None or not home<=header_home<home+8)and all(home+8<=old or old+size<=home for old,size in value_homes+hidden_homes+copy_homes)and all(home+8<=old or old+16<=home for old in vector_homes.values()))
            local_homes.add(home);continue
        rbp_header=header_address is not None and text==f"mov byte [rbp+{header_address.get('displacement',-1):#x}], 0x0"
        if header_local is not None and(text==f'mov byte [rsp+{header_local:#x}], 0x0'or rbp_header):
            if rbp_header:
                need('same-owned-RBP-header-frame-home','rbp'in frame_aliases and
                    ec.raw(row)==bytes.fromhex('c645')+bytes((header_address['displacement'],0))and
                    frame_aliases['rbp']+header_address['displacement']==header_address['entryRspOffset']==delta+header_local)
            header_home=delta+header_local;need('header-local-disjoint-homes',all(not old<=header_home<old+8 for old in homes.values())and all(not old<=header_home<old+16 for old in vector_homes.values())and all(not old<=header_home<old+size for old,size in hidden_homes+value_homes+copy_homes));continue
        if move.get('direction')=='store'and(address.get('base')=='rsp'or entry_rbp and address.get('base')=='rax'):
            register=move.get('register');need('only-original-nonvolatile-home-store',move.get('memoryBytes')==8 and register in NONVOLATILE and original[register]and address.get('index')is None,row)
            origin=delta if address['base']=='rsp'else frame_aliases.get('rax')
            need('same-entry-RAX-original-home',address['base']=='rsp'or origin==delta==0)
            home=origin+address['displacement'];need('unique-disjoint-original-home',register not in homes and all(not old<=home<old+8 and not home<=old<home+8 for old in homes.values())and(header_home is None or not home<=header_home<home+8)and all(home+8<=old or old+8<=home for old in local_homes)and all(home+8<=old or old+size<=home for old,size in value_homes+hidden_homes+copy_homes)and all(home+8<=old or old+16<=home for old in vector_homes.values()));homes[register]=home;saved.append((register,home));continue
        restored=False
        if move.get('direction')=='load'and(address.get('base')=='rsp'or address.get('base')in frame_aliases)and move.get('register')in NONVOLATILE:
            register=move['register'];origin=delta if address['base']=='rsp'else frame_aliases[address['base']]
            need('exact-original-home-restore',move['memoryBytes']==8 and address.get('index')is None and homes.get(register)==origin+address['displacement'],row);original[register]=True;restored=True
        for register in NONVOLATILE:
            if not restored and _writes_register(row,register):need('original-saved-before-write',register in homes,row);original[register]=False
        for register in vector_original:
            if _writes_register(row,register):need('original-vector-saved-before-write',register in vector_homes,row);vector_original[register]=False
        if flow['kind']=='call':need('every-call-aligned-and-shadowed',delta<=-32 and(8+delta)%16==0,row)
        if flow['kind']=='return'or flow['kind']=='jump'and index==len(path)-1 and tail_target is not None:
            need('full-entry-frame-and-nonvolatile-return',index==len(path)-1 and delta==0 and all(original.values())and all(vector_original.values())and(flow['kind']=='return'or flow['target']==tail_target),(delta,original,vector_original))
    need('one-final-return',path and(control_transfer(path[-1])['kind']=='return'or control_transfer(path[-1])['kind']=='jump'and tail_target is not None and control_transfer(path[-1])['target']==tail_target))
    result=dict(savedHomes=saved,entryRspRestored=True,allWin64IntegerNonvolatilesRestored=True)
    if entry_rbx_home is not None:result['entryOriginalRbxHome']=entry_rbx_home
    if zero_proofs:result['initializedZeroLocalProofs']=zero_proofs
    if header_reuse:result['retiredHeaderLocalLifetimes']=header_reuse
    if local_homes:result['sourceReferenceLocalHomes']=sorted(local_homes)
    if physical_value_homes:result['sourceValueLocalHomes']=sorted(physical_value_homes)
    if lifetime_proofs:result['sourceValueLocalLifetimes']=lifetime_proofs
    if physical_hidden_homes:result['hiddenSourceLocalHomes']=sorted(set(physical_hidden_homes))
    if hidden_lifetime_proofs:result['hiddenSourceLocalLifetimes']=hidden_lifetime_proofs
    if physical_copy_homes:result['copiedSourceLocalHomes']=sorted(set(physical_copy_homes))
    if copy_lifetime_proofs:result['copiedSourceLocalLifetimes']=copy_lifetime_proofs
    if vector_homes:result['restoredVectorHomes']=vector_homes
    if frame_alias_proofs:result['frameBaseAliases']=frame_alias_proofs
    if source_frame_alias is not None:result['sourceFrameAlias']=source_frame_alias
    return result


def zero_header_program(rows,entry,header_target,base,barrier):
    """Actual byte-header helper, output local and zero-member self-test."""
    from scripts.game_data.memorypack import generated_header_sources as header_source
    from scripts.game_data.il2cpp.initializer_control import _ALIASES
    by={ec.va(r):r for r in rows};roles=header_source._arguments(rows,entry);reader=roles['reader'];output=roles['output'];calls=[]
    for i,row in enumerate(rows[:-2]):
        flow=control_transfer(row)
        if flow['kind']=='call'and flow['target']==header_target and rows[i+1]['text']=='test al, al':calls.append((i,row))
    need('zero-one-actual-header-call',len(calls)==1);i,call=calls[0];argument=ec.last_write(rows,i,'rdx');rcx=ec.last_write(rows,i,'rcx')
    need('zero-header-arguments',argument is not None and rcx is not None and rcx['text']==f'mov rcx, {reader}')
    text=argument['text'];need('zero-owned-header-local',text.startswith('lea rdx, [rsp+0x')and text.endswith(']'));local=int(text.split('+')[1][:-1],16)
    need('zero-local-outside-call-home',local>=32)
    edge=control_transfer(rows[i+2]);need('zero-FF-guard',edge['kind']=='conditional'and edge['conditionCode']==4)
    null=header_source._null_tail(rows,edge['target'],entry,output,base,barrier,None);candidates=[]
    for row in rows:
        load=row.get('byteMemoryZeroExtensionOperation',{});address=load.get('sourceAddress',{});at=ec.va(row)+len(ec.raw(row));test=by.get(at)
        if address.get('base')!='rsp'or address.get('index')is not None or address.get('displacement')!=local or load.get('memoryReadBytes')!=1 or test is None:continue
        register=_ALIASES.get(load.get('destinationRegister'));left,sep,right=test['text'].removeprefix('test ').partition(', ')
        if sep and left==right and _ALIASES.get(left)==register:candidates.append((row,test))
    need('zero-one-actual-header-test',len(candidates)==1);load,test=candidates[0]
    return dict(mode='helper',readerRegister=reader,outputRegister=output,readerSave=ec.site(roles['readerSave'],base),outputSave=ec.site(roles['outputSave'],base),
        headerLocalDisplacement=local,helperTargetRva=header_target-base,prologue=[ec.site(row,base)for row in null['frame']['prologue']],
        nullReturnProgram=[ec.site(row,base)for row in null['rows']],nullReturn=dict(disabledCollectorFlagRva=None),
        resultLoad=ec.site(load,base),memberCountInstruction=ec.site(test,base))


def zero_return_program(rows,header,base):
    """Actual zero self-test must join a complete return with no child calls."""
    g=_Path(rows,base+header['memberCountInstruction'][0]);test=g.take();left,sep,right=test['text'].removeprefix('test ').partition(', ')
    need('zero-exact-self-test',sep and left==right);g.branch(True)
    while True:
        row=g.row();flow=control_transfer(row);move=row.get('memoryOperation',{});address=move.get('address',{});text=row['text']
        need('zero-return-only',flow['kind']in('jump','return')or text.startswith(('add rsp, ','pop '))or
            move.get('direction')=='load'and address.get('base')=='rsp'and move.get('register')in NONVOLATILE,row)
        if flow['kind']=='jump':g.jump();continue
        g.take()
        if flow['kind']=='return':break
    return g.seen


def constructed_getter_join(life,setters):
    """A new receiver supplies only caches its actual constructor writes."""
    constructors=[f for f in life['factories']if f['method'][2]=='.ctor']
    need('one-selected-wrapper-constructor',len(constructors)==1)
    ctor=constructors[0];program=ctor['program'];written={program['typedCacheOffset']}if program['typedCacheOffset']is not None else set()
    holder=ctor['holderSetter']
    if holder.get('profile')=='inline-current-wrapper-holder-writes':
        for store in holder['program']:
            need('constructed-whole-reference',store['bytes']==8 and store['sameAllocatedReference'])
            written.add(store['offset'])
    else:written.update(holder['program']['holderOffsets'])
    need('constructor-base-and-own-cache',life['baseHolder'][2]in written and(life['typedCache']is None or life['typedCache'][2]in written))
    joins=[]
    for setter in setters:
        getter=setter['getter']
        if getter is None:
            offset=setter['program'].get('holderOffset')
            if offset is None and setter['profile']=='direct-base-holder-setter':
                holder=setter.get('directHolder',{});program=setter['program'];native=program.get('selectedBytes',[])
                need('own-direct-BeyondCurve-holder-declaration',setter.get('managedValueLayout',{}).get('typeName')=='Beyond.FAnimationCurve'
                    and isinstance(holder.get('field'),(list,tuple))and list(holder['field'])==list(life['baseHolder'])
                    and holder.get('inheritedFieldAliasUsed')is False
                    and holder.get('openGenericOffsetUsed')is False and holder['field'][2]==16
                    and program.get('sourceSlices')==[[0,16]]and program.get('storedBytes')==16
                    and program.get('wholeInputBitsStoredUnchanged')is True and len(native)>=2
                    and[native[0][1].lower(),native[1][1].lower()]==['4883ec28','488b4910'])
                offset=holder['field'][2]
            need('direct-setter-construction',(setter['profile']=='direct-base-holder-setter'or setter['profile']=='metadata-field-binding'and setter['setterImplementationAdmitted']is False)and offset in written)
            joins.append(dict(method=setter['method'],mode='constructed-base-holder'));continue
        need('same-constructed-base-holder',getter['baseHolder'][2]==life['baseHolder'][2])
        offset=getter['typedCache'][2]
        if offset in written:mode='constructed-cache'
        else:
            inline=setter.get('inlineCompatibleRefresh')
            if inline is not None:
                need('actual-inherited-inline-cache-refresh',setter['profile']=='inline-coherent-cache-setter'and inline['sameBaseReferenceCachedBeforeField']and inline['emptyOrDifferentCacheAdmitted']and inline['baseSlot']==getter['baseHolder'][2]and inline['cacheSlot']==offset and inline['typeName']==getter['typedCache'][1])
                mode='exact-compatible-inline-setter-refresh-from-constructed-base';joins.append(dict(method=setter['method'],cacheOffset=offset,mode=mode));continue
            need('unconstructed-cache-requires-actual-refresh-call',setter['profile']=='cached-getter-setter'and getter['refreshAdmitted'],
                dict(method=setter['method'],cacheOffset=offset,profile=setter['profile'],refresh=getter.get('refreshPendingReason')))
            mode='exact-compatible-refresh-from-constructed-base'
        joins.append(dict(method=setter['method'],cacheOffset=offset,mode=mode))
    return dict(constructorMethod=ctor['method'],constructedReferenceOffsets=sorted(written),setters=joins,
        inheritedCacheCoherenceAssumed=False)


def _wrapper_allocator(image,wrapper,life,rows):
    """A native Original factory cannot name the managed wrapper allocator."""
    if life.get('typedOriginalFactoryMode')is None:
        allocators={f['program']['allocationTarget']for f in life['factories']}
    else:
        from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
        need('explicit-native-Original-factory-mode',life['typedOriginalFactoryMode']=='scriptable-object-generic'
            and all(f['program'].get('typedFactoryMode')=='scriptable-object-generic'
                and'allocationTarget'not in f['program']and f.get('originalAllocation')is None for f in life['factories']))
        base=image.pe.image_base;allocators=set()
        for index,row in enumerate(rows[:-1]):
            raw=ec.raw(row);call=rows[index+1]
            if len(raw)!=7 or raw[:3]!=bytes.fromhex('488b0d')or ec.raw(call)[:1]!=b'\xe8':continue
            try:usage=derive_typed_usage_context(image,ec.va(row)-base,label=LABEL+'.wrapperAllocationCandidate')
            except(ValueError,KeyError,IndexError):continue
            if(usage['tag'],usage['typeName'])==(1,wrapper.name):allocators.add(control_transfer(call)['target'])
    need('one-actual-typed-wrapper-allocator',len(allocators)==1,sorted(allocators))
    return next(iter(allocators))


def _derive(image,pins,wrapper,wrappers,targets,barrier,disabled_flag,getter_cache,*,formatter_prover=None,direct_factory_prover=None,typed_factory_prover=None):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import pointer_param as pointer
    base=image.pe.image_base
    if not wrapper.members:return _derive_zero(image,pins,wrapper,wrappers,barrier,getter_cache,
        formatter_prover=formatter_prover,direct_factory_prover=direct_factory_prover,typed_factory_prover=typed_factory_prover)
    scope=actions._derive(image,pins,wrapper.name,targets,barrier,disabled_flag)
    life=lifecycle._derive(image,pins,wrapper,wrappers,barrier,getter_cache,
        formatter_prover=formatter_prover,direct_factory_prover=direct_factory_prover,typed_factory_prover=typed_factory_prover)
    fields=scope['richSetters']if 'richProgram'in scope else[members._derive_setter(image,member,wrappers,barrier,getter_cache,pins=pins)for member in wrapper.members]
    construction=constructed_getter_join(life,fields)
    from scripts.game_data.memorypack.generated_owned_code_sources import source_family
    family,windows,rows,partition=source_family(image,pins,entry_rva=scope['method'][3])
    need('same-current-owned-reader-family',family==scope['family']and windows==scope['codeWindows'])
    need('same-fresh-code-table-partition',partition==scope.get('ownedCodePartition'))
    allocate=_wrapper_allocator(image,wrapper,life,rows)
    mm=pointer.methods(image,wrapper);arguments=dict(base=base,prehook=image.method_pointer_va(mm['OnDeserialized'])if 'OnDeserialized'in mm else None,constructor=image.method_pointer_va(mm['.ctor']),allocate=allocate,barrier=base+barrier,prehook_source=life.get('coherentPrehook'),owned_partition=partition,disabled_flag=disabled_flag)
    def inline_constructor(rows,entry,wrapper_register,output_register):
        from scripts.game_data.memorypack.generated_inline_constructor_sources import derive_fragment
        return derive_fragment(image,pins,wrapper=wrapper,lifecycle=life,rows=rows,entry=entry,
            wrapper_register=wrapper_register,output_register=output_register,barrier=base+barrier,owned_partition=partition)
    arguments['inline_constructor_prover']=inline_constructor
    positive=positive_program(rows,scope,base);programs=[]
    for existing,ff in((False,False),(True,False),(False,True),(True,True)):
        selected=prefix_program(rows,base+scope['method'][3],scope['headerProof'],**arguments,existing=existing,ff=ff)
        path=selected.pop('selectedRows')+([]if ff else positive)
        rich=scope.get('richProgram',{});value_locals=rich.get('sourceLocalValues')
        montage_copies=rich.get('sourceFrameAlias',{}).get('ownerType')=='Beyond.Gameplay.Core.CharInteractPerform.CharNpcMontageActionData'
        from scripts.game_data.memorypack.leveldata_quaternion_forwarder_sources import owns_member as quaternion_member
        quaternion_copies=any(item.get('nominalTypeName')=='UnityEngine.Quaternion'and item.get('sameOwnedHiddenLocalCopy')is True
            and item.get('parentType')==scope.get('wrappedType')and quaternion_member(scope.get('wrappedType'),item.get('fieldName'),'UnityEngine.Quaternion')
            for item in rich.get('sourceLocalCopies',[]))
        from scripts.game_data.memorypack.generated_aabb_field_sources import owns_member as aabb_member
        aabb_copies=any(item.get('nominalTypeName')=='Beyond.AABB'and item.get('sameOwnedHiddenLocalCopy')is True
            and item.get('parentType')==scope.get('wrappedType')and aabb_member(scope.get('wrappedType'),item.get('fieldName'),'Beyond.AABB')
            for item in rich.get('sourceLocalCopies',[]))
        lifetimes=rich.get('fieldStores')if montage_copies or quaternion_copies or aabb_copies or any('memberIndex'in item for item in value_locals or[])or any(item.get('sourceAbi')=='void-byref-reference8'for item in rich.get('hiddenSourceLocals',[]))else None
        tail=None if ff else scope.get('namedSetterTail')
        if tail is not None:
            need('same-last-proved-setter-tail',tail.get('memberIndex')==len(fields)-1 and tail.get('method')==fields[-1]['method']
                and tail.get('completeSourceAndArgumentTransferProved')is True and tail.get('fullRestoredCallerFrameRequired')is True
                and tail.get('instruction')==ec.site(path[-1],base)and control_transfer(path[-1])['target']==base+fields[-1]['method'][3])
        frame=frame_program(path,header_local=scope['headerProof'].get('headerLocalDisplacement'),source_locals=rich.get('sourceLocalReferences'),value_locals=value_locals,hidden_locals=rich.get('hiddenSourceLocals'),copied_locals=rich.get('sourceLocalCopies'),base=base,tail_barrier=base+barrier if ff or scope.get('referenceBarrierTargetRva')==barrier else None,value_lifetimes=lifetimes,
            tail_setter=base+fields[-1]['method'][3]if tail is not None else None,
            header_result_load=scope['headerProof'].get('resultLoad')if not ff and scope['headerProof'].get('mode')=='helper'else None,
            initialized_zero_locals=selected.get('initializedZeroLocals',[])+([]if ff else rich.get('initializedZeroLocals',[])),
            header_address=scope['headerProof'].get('headerAddress'),source_frame_alias=(
                rich.get('sourceFrameAlias')if not ff or any(z.get('literalZero')is True for z in selected.get('initializedZeroLocals',[]))else None))
        allocation=None
        if selected['allocation']is not None:
            allocation=derive_typed_usage_context(image,selected['allocation']['usageInstruction'][0],label=LABEL+'.wrapperAllocation')
            need('exact-current-wrapper-allocation',(allocation['tag'],allocation['typeName'])==(1,wrapper.name))
        programs.append(dict(**selected,selectedProgram=[ec.site(r,base)for r in path],frame=frame,wrapperAllocation=allocation))
    return dict(schema='endfield.generated-concrete-reader-source.v1',nativeInputs=pins,wrapperName=wrapper.name,wrappedType=wrapper.wrapped_type,
        method=scope['method'],family=family,codeWindows=windows,programs=programs,lifecycle=life,setters=fields,constructedGetterJoin=construction,sourceScope=scope,
        orderedSourceReads=scope['events'],childRequirements=scope['childRequirements'],
        completeSelectedCallerAdmitted=True,childGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary='Every initialized new/existing positive and FF entry path, source/helper/return transfer, exact concrete callback, current nominal lifecycle and setter implementation is independently joined. Child grammar, enclosing union/parent selection, incompatible/noncoherent/throwing/refill paths and runtime provider remain separate.')


def _derive_zero(image,pins,wrapper,wrappers,barrier,getter_cache,*,formatter_prover=None,direct_factory_prover=None,typed_factory_prover=None):
    """Own the real zero-header program; empty metadata alone admits nothing."""
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import pointer_param as pointer,buff_profile_source
    from scripts.game_data.buff_frontiers_regenerate import _method_row
    base=image.pe.image_base;mm=pointer.methods(image,wrapper)
    life=lifecycle._derive(image,pins,wrapper,wrappers,barrier,getter_cache,
        formatter_prover=formatter_prover,direct_factory_prover=direct_factory_prover,typed_factory_prover=typed_factory_prover)
    method=_method_row(image,[0,wrapper.name,'Deserialize',1]);family,windows,rows=ec.family(image,method[3]);regions=[(base+w['startRva'],image.window_bytes(w))for w in windows]
    allocate=_wrapper_allocator(image,wrapper,life,rows)
    headers=[]
    for i,row in enumerate(rows[:-1]):
        if ec.raw(row)[:1]==b'\xe8'and rows[i+1]['text']=='test al, al':headers.append(control_transfer(row)['target'])
    need('zero-one-header-helper',len(headers)==1)
    symbols=dict(prehook=image.method_pointer_va(mm['OnDeserialized'])if 'OnDeserialized'in mm else None,constructor=image.method_pointer_va(mm['.ctor']),
        allocate=allocate,barrier=base+barrier,header=headers[0]if headers else None)
    header=None
    if headers:
        hf,hw,hr=ec.family(image,headers[0]-base);program=buff_profile_source.object_header_program(hr,headers[0],ec.source_offsets(image));by={ec.va(r):r for r in hr}
        header=dict(family=hf,codeWindows=hw,program=[ec.site(by[a],base)for a in program],wireBytes=1,nullMarker=255)
    programs=[];zero_header=zero_header_program(rows,base+method[3],headers[0],base,barrier)
    for existing,ff in((False,False),(True,False),(False,True),(True,True)):
        program=prefix_program(rows,base+method[3],zero_header,base=base,prehook=symbols['prehook'],constructor=symbols['constructor'],
            allocate=symbols['allocate'],barrier=symbols['barrier'],existing=existing,ff=ff,reader_reuse=True)
        path=program.pop('selectedRows')+([]if ff else zero_return_program(rows,zero_header,base));frame=frame_program(path,header_local=zero_header['headerLocalDisplacement'])
        typed=None
        if program['allocation']is not None:
            typed=derive_typed_usage_context(image,program['allocation']['usageInstruction'][0],label=LABEL+'.zeroWrapperAllocation');need('zero-exact-wrapper-allocation',(typed['tag'],typed['typeName'])==(1,wrapper.name))
        programs.append(dict(**program,selectedProgram=[ec.site(row,base)for row in path],frame=frame,wrapperAllocation=typed))
    return dict(schema='endfield.generated-concrete-reader-source.v1',nativeInputs=pins,wrapperName=wrapper.name,wrappedType=wrapper.wrapped_type,
        method=method,family=family,codeWindows=windows,memberCount=0,programs=programs,lifecycle=life,setters=[],headerSource=header,
        orderedSourceReads=[],childRequirements=[],completeSelectedCallerAdmitted=True,childGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary='Complete initialized zero-header existing/new and FF caller programs, exact own concrete callback and current lifecycle. The actual byte program checks header zero rather than inferring it from empty metadata. Enclosing parent/union selection, noncoherent/error/refill paths and runtime provider remain independent.')


def derive(image,pins,wrapper_name,*,formatter_prover=None,direct_factory_prover=None,typed_factory_prover=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins);targets,barrier,disabled_flag=actions._prepare(image,pins)
    inventory=list(image.memorypack_wrappers.values());wrappers={w.name:w for w in inventory};need('unique-current-wrapper-inventory',len(wrappers)==len(inventory))
    proof=_derive(image,pins,wrappers[wrapper_name],wrappers,targets,barrier,disabled_flag,{},
        formatter_prover=formatter_prover,direct_factory_prover=direct_factory_prover,typed_factory_prover=typed_factory_prover)
    _publication_gate(image,pins);return json.loads(json.dumps(proof))


def derive_many(image,pins,wrapper_names,*,formatter_prover=None,direct_factory_prover=None,typed_factory_prover=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    need('bounded-distinct-owners',0<len(wrapper_names)<=512 and len(set(wrapper_names))==len(wrapper_names))
    _publication_gate(image,pins);targets,barrier,disabled_flag=actions._prepare(image,pins)
    inventory=list(image.memorypack_wrappers.values());wrappers={w.name:w for w in inventory};need('unique-current-wrapper-inventory',len(wrappers)==len(inventory));cache={};owners=[]
    for name in wrapper_names:
        try:owners.append(dict(status='complete-reader-source-proved',proof=_derive(image,pins,wrappers[name],wrappers,targets,barrier,disabled_flag,cache,
            formatter_prover=formatter_prover,direct_factory_prover=direct_factory_prover,typed_factory_prover=typed_factory_prover)))
        except(ValueError,KeyError,IndexError,TypeError)as error:owners.append(dict(status='pendingReview',wrapperName=name,reason=str(error)[:2400]))
    _publication_gate(image,pins);return json.loads(json.dumps(dict(nativeInputs=pins,owners=owners,wholeOwnerAdmitted=False)))
