"""Current generated static-reader header and FF return programs.

Register roles are derived from the entry ABI saves, rather than fixed compiler
slots. Every selected source update, full output clear, barrier selection and
return frame is checked. Positive members and lifecycle hooks remain separate.
"""
from __future__ import annotations
import re
from scripts.game_data.il2cpp.initializer_control import control_transfer,_ALIASES
from scripts.game_data.memorypack import buff_ec_profiles_native as ec,buff_profile_source as source

LABEL='generatedHeaderSource'
NONVOLATILE={'rbx','rbp','rsi','rdi','r12','r13','r14','r15'}


def need(check,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+check+':'+str(detail)[:700])


def _arguments(rows,entry):
    by={ec.va(r):r for r in rows};at=entry;prefix=[]
    while at in by and len(prefix)<40:
        row=by[at]
        if control_transfer(row)['kind']!='next':break
        prefix.append(row);at+=len(ec.raw(row))
    result={}
    for role,argument in(('reader','rcx'),('output','rdx')):
        saved=ec.one(prefix,lambda r:re.fullmatch(r'mov (?:rbx|rbp|rsi|rdi|r1[2345]), '+argument,r['text'])is not None,LABEL+'.'+role)
        register=saved['text'].split()[1].strip(',')
        need(role+'-provenance',ec.last_write(prefix,prefix.index(saved),argument)is None)
        result[role]=register;result[role+'Save']=saved
    need('disjoint-arguments',result['reader']!=result['output'])
    return result


def _frame(rows,tail,entry):
    """Authenticate entry-relative homes and every selected nonvolatile restore."""
    by={ec.va(r):r for r in rows};at=entry;delta=0;saved={};restored=set();prologue=[];aliases={}
    while at in by:
        row=by[at];text=row['text'];move=row.get('memoryOperation',{});address=move.get('address',{})
        alias=re.fullmatch(r'mov (rax|rbp), rsp',text)
        based=re.fullmatch(r'lea rbp, \[(rsp|rax)([+-])0x([0-9a-f]+)\]',text)
        if alias:
            register=alias[1];need('saved-nonvolatile-frame-alias',register=='rax'or register in saved)
            need('exact-prologue-frame-alias',ec.raw(row)==bytes.fromhex('488bc4'if register=='rax'else'488bec'),row)
            need('one-prologue-frame-alias',register not in aliases);aliases[register]=delta
        elif based:
            displacement=int(based[3],16)*(1 if based[2]=='+'else-1)
            need('owned-saved-RBP-frame-base','rbp'in saved and 'rbp'not in aliases and -128<=displacement<128)
            if based[1]=='rax':
                need('exact-entry-RAX-Trigger-frame-base',aliases.get('rax')==0 and saved.get('rbp')==-8
                    and delta==-8 and displacement==-95 and ec.raw(row)==bytes.fromhex('488d68a1'),row)
                aliases['rbp']=-95
            else:
                need('exact-RBP-frame-base-encoding',ec.raw(row)==bytes.fromhex('488d6c24')+displacement.to_bytes(1,'little',signed=True),row)
                aliases['rbp']=delta+displacement
        elif text.startswith('push '):
            register=text[5:];need('push-nonvolatile',register in NONVOLATILE)
            delta-=8;need('unique-save',register not in saved);saved[register]=delta
        elif text.startswith('sub rsp, '):
            need('one-frame-allocation',not any(r['text'].startswith('sub rsp, ')for r in prologue))
            delta-=int(text.split(', ')[1],16)
        elif move.get('direction')=='store'and address.get('base')in('rsp','rax'):
            register=move.get('register');need('home-store',move['memoryBytes']==8 and
                register in NONVOLATILE and address.get('index')is None and not address.get('ripRelative'))
            origin=delta if address['base']=='rsp'else aliases.get('rax')
            need('exact-entry-RAX-save-base',address['base']=='rsp'or origin==delta==0 and ec.raw(row)[:2]==bytes.fromhex('4889'))
            need('unique-save',register not in saved);saved[register]=origin+address['displacement']
        else:break
        prologue.append(row);at+=len(ec.raw(row))
    need('entry-call-alignment',saved and delta<=-32 and (8+delta)%16==0)
    need('disjoint-saved-homes',len(set(saved.values()))==len(saved))
    initial_delta=delta
    for row in tail:
        text=row['text'];move=row.get('memoryOperation',{});address=move.get('address',{})
        match=re.fullmatch(r'lea r11, \[rsp\+0x([0-9a-f]+)\]',text)
        if match:
            need('one-frame-alias','r11'not in aliases);aliases['r11']=delta+int(match[1],16)
        elif text=='mov rsp, r11':
            need('known-frame-alias','r11'in aliases);delta=aliases['r11']
        elif text.startswith('pop '):
            register=text[4:];need('pop-home',saved.get(register)==delta and register not in restored,row)
            restored.add(register);delta+=8
        elif text.startswith('add rsp, '):delta+=int(text.split(', ')[1],16)
        elif move.get('direction')=='load':
            register=move.get('register');home=delta if address.get('base')=='rsp'else aliases.get(address.get('base'))
            need('restore-home',register in saved and move['memoryBytes']==8 and home is not None and
                address.get('index')is None and home+address['displacement']==saved[register]and register not in restored,row)
            restored.add(register)
        if control_transfer(row)['kind']=='call':need('call-frame-alignment',delta<=-32 and (8+delta)%16==0)
    need('complete-return-frame',delta==0 and restored==set(saved),(delta,saved,restored))
    return dict(frameBytes=-initial_delta,savedHomes=saved,prologue=prologue)


def _owned_zero_source(rows,entry,sites,register,base,owned_partition):
    """Reprove a literal nonvolatile zero at explicit current instruction sites."""
    from scripts.game_data.il2cpp.constant_register_sources import prove
    if type(owned_partition)is dict and owned_partition.get('status')=='current-owned-ordinary-zero-family-proved':
        from scripts.game_data.il2cpp.constant_register_sources import prove_ordinary_family
        need('fresh-owned-ordinary-zero-rows',owned_partition.get('entryRva')==entry-base and owned_partition.get('rows')==rows)
        ranges=[(base+w['startRva'],base+w['endRva'])for w in owned_partition['codeWindows']]
        return prove_ordinary_family(rows,entry=entry,register=register,sites=sites,owned_ranges=ranges)
    need('fresh-owned-zero-graph',type(owned_partition)is dict and
        owned_partition.get('status')=='current-owned-code-partition-proved'and
        owned_partition.get('entryRva')==entry-base and owned_partition.get('rows')==rows)
    parts=[p['partition']for p in owned_partition.get('partitions',[])
        if p.get('startRva')==entry-base and set(sites)<={ec.va(r)for r in p.get('partition',{}).get('rows',[])}]
    need('one-complete-entry-zero-graph',len(parts)==1)
    return prove(parts[0],entry=entry,register=register,sites=sites,image_base=base)


def _owned_zero_guard(rows,entry,row,output,base,disabled_flag,owned_partition,ordinary_zero_prover=None):
    """Join the actual DWORD collector comparison and full output clear."""
    from scripts.game_data.il2cpp.constant_register_sources import disabled_guard
    at=ec.va(row)
    following={ec.va(r):r for r in rows}.get(at+len(ec.raw(row)))
    move=(following or{}).get('memoryOperation',{});address=move.get('address',{})
    comparison=row.get('memoryRegisterComparisonOperation',{});register=_ALIASES.get(comparison.get('register'))
    need('zero-guard-whole-output-store',following is not None and move.get('direction')=='store'and
        move.get('memoryBytes')==8 and address.get('base')==output and address.get('index')is None and
        address.get('displacement')==0 and move.get('register')==register and
        comparison.get('preservesRegisters')is True,following)
    zero=(ordinary_zero_prover([at,ec.va(following)],register)if owned_partition is None and callable(ordinary_zero_prover)else
        _owned_zero_source(rows,entry,[at,ec.va(following)],register,base,owned_partition))
    guard=disabled_guard(row,zero,flag_va=base+disabled_flag)
    return zero,guard


def _null_tail(rows,at,entry,output,base,barrier,disabled_flag,owned_partition=None,ordinary_zero_prover=None):
    by={ec.va(r):r for r in rows};tail=[];clear=[];calls=[];zero=set();guard=None;terminal=None;zero_guard=None;output_zero_proof=None
    while True:
        need('null-boundary',at in by and at not in {ec.va(r)for r in tail}and len(tail)<80,hex(at))
        row=by[at];tail.append(row);text=row['text'];flow=control_transfer(row)
        zero_match=re.fullmatch(r'xor (e[a-z]+|r1[2345]d), \1',text)
        move=row.get('memoryOperation',{});address=move.get('address',{})
        comparison=row.get('memoryImmediateComparisonOperation',{})
        register_comparison=row.get('memoryRegisterComparisonOperation',{})
        if zero_match:
            register=_ALIASES.get(zero_match[1],zero_match[1]);need('null-zero-register',register!=output)
            zero.add(register)
        elif move.get('direction')=='store':
            register=move.get('register')
            if register not in zero and callable(ordinary_zero_prover)and register in NONVOLATILE:
                output_zero_proof=ordinary_zero_prover([ec.va(row)],register);zero.add(register)
            need('whole-output-store',move['memoryBytes']==8 and address.get('base')==output and
                address.get('index')is None and address.get('displacement')==0 and move.get('register')in zero,row)
            clear.append(row)
        elif text==f'mov qword [{output}], 0x0':clear.append(row)
        elif comparison:
            need('one-disabled-collector-guard',guard is None and disabled_flag is not None and comparison['bits']==32 and
                comparison['immediateValue']==0 and comparison['sourceAddress'].get('ripRelative')and
                comparison['sourceAddress'].get('absoluteAddress')==base+disabled_flag,row)
            guard=row
        elif register_comparison:
            need('one-owned-zero-collector-guard',guard is None and disabled_flag is not None)
            zero_source,zero_guard=_owned_zero_guard(rows,entry,row,output,base,disabled_flag,owned_partition,ordinary_zero_prover)
            zero.add(zero_source['register']);guard=row
        elif text==f'mov rcx, {output}'or text=='nop':pass
        elif text.startswith('mov '):
            need('null-restore-only',move.get('direction')=='load'or text=='mov rsp, r11',row)
        elif text.startswith('lea r11, [rsp+'):pass
        else:need('null-instruction',text.startswith(('add rsp, ','pop ','ret','call 0x','jmp 0x','je ','jcc ')),row)
        if flow['kind']=='call'or flow['kind']=='jump'and flow['target']not in by:
            argument=ec.last_write(tail,len(tail)-1,'rcx')
            need('null-barrier-argument',argument is not None and argument['text']==f'mov rcx, {output}')
            need('null-actual-barrier',flow['target']==base+barrier and len(clear)==1 and guard is None,flow)
            calls.append(row)
            if flow['kind']=='jump':terminal='barrier-tail';break
        if flow['kind']=='return':terminal='ret';break
        if flow['kind']=='conditional':
            need('disabled-collector-edge',guard is not None and flow['conditionCode']==4 and len(clear)==1 and not calls,row)
            need('collector-flags-preserved',all(r['text'].startswith('mov ')for r in tail[tail.index(guard)+1:-1]))
            at=flow['target'];continue
        need('null-transfer',flow['kind']in('next','call','jump'),row)
        at=flow['target']if flow['kind']=='jump'else at+len(ec.raw(row))
    need('one-null-clear',len(clear)==1)
    need('one-null-barrier-selection',(len(calls)==1 and guard is None)or(not calls and guard is not None))
    frame=_frame(rows,tail,entry)
    result=dict(rows=tail,frame=frame,terminal=terminal,barrierTargetRva=barrier if calls else None,
        disabledCollectorFlagRva=disabled_flag if guard is not None else None)
    if zero_guard is not None:result['disabledCollectorZeroSource']=zero_guard
    if output_zero_proof is not None:result['wholeOutputZeroSource']=output_zero_proof
    return result


def _header_rbp_alias(prologue,saved_homes,base):
    """Locate the byte-exact frame alias after the full frame proved its saves."""
    delta=0;alias=None;entry_alias=None
    for row in prologue:
        if row['text'].startswith('push '):delta-=8
        elif row['text'].startswith('sub rsp, '):delta-=int(row['text'].split(', ')[1],16)
        elif row['text']=='mov rbp, rsp':
            # Saving RBP and choosing the RSP base are different events. Other
            # nonvolatile pushes may precede this exact MOV; _frame proved
            # all of their homes and matching restores independently.
            home=saved_homes.get('rbp')
            need('one-exact-saved-RBP-frame-alias',alias is None and ec.raw(row)==bytes.fromhex('488bec')
                and type(home)is int and delta<=home<0 and home%8==0,row)
            alias=(row,delta)
        elif row['text']=='mov rax, rsp':
            need('exact-entry-RAX-header-alias',entry_alias is None and delta==0 and ec.raw(row)==bytes.fromhex('488bc4'),row)
            entry_alias=row
        elif row['text']=='lea rbp, [rax-0x5f]':
            need('exact-entry-RAX-RBP-header-alias',alias is None and entry_alias is not None and delta==-8
                and ec.raw(row)==bytes.fromhex('488d68a1')and saved_homes.get('rbp')==-8,row)
            alias=(row,-95)
    need('owned-prologue-RBP-header-base',alias is not None)
    return alias,entry_alias


def _helper(rows,entry,count,roles,image,offsets,barrier,disabled_flag,owned_partition=None,ordinary_zero_prover=None):
    reader,output=roles['reader'],roles['output'];base=image.pe.image_base;candidates=[]
    for index,row in enumerate(rows[:-2]):
        if ec.raw(row)[:1]!=b'\xe8'or rows[index+1]['text']!='test al, al':continue
        edge=control_transfer(rows[index+2]);argument=ec.last_write(rows,index,'rdx');rcx=ec.last_write(rows,index,'rcx')
        if edge['kind']=='conditional'and edge['conditionCode']==4 and argument is not None and rcx is not None and \
            rcx['text']==f'mov rcx, {reader}'and re.fullmatch(r'lea rdx, \[(?:rsp|rbp)\+0x[0-9a-f]+\]',argument['text']):
            candidates.append((index,row,argument,edge))
    index,call,argument,edge=ec.one(candidates,lambda x:True,LABEL+'.header-helper')
    local=argument['text'].removeprefix('lea rdx, ');local_base=local[1:4];displacement=int(local[5:-1],16)
    need('header-byte-outside-call-home',local_base=='rbp'or displacement>=32)
    if local_base=='rbp':
        need('exact-RBP-header-address-encoding',0<=displacement<128 and
            ec.raw(argument)==bytes.fromhex('488d55')+bytes((displacement,)),argument)
    stores=[]
    for row in rows[:index]:
        move=row.get('memoryOperation',{});address=move.get('address',{})
        if move.get('direction')=='store'and address.get('base')==local_base and address.get('index')is None and \
            address.get('displacement',-1)<=displacement<address.get('displacement',-1)+move.get('memoryBytes',0):stores.append(row)
        if row['text']==f'mov byte {local}, 0x0':stores.append(row)
    need('header-output-zero',stores and stores[-1]['text']==f'mov byte {local}, 0x0')
    need('output-save-provenance',ec.last_write(rows,index,output)==roles['outputSave'])
    chosen=[]
    for ci,row in enumerate(rows):
        if ci<=index+2 or not row['text'].endswith(', '+hex(count))or not row['text'].startswith('cmp '):continue
        operand=row['text'][4:].split(',')[0]
        if operand=='byte '+local:chosen.append((ci,row,None));continue
        register=_ALIASES.get(operand,operand);load=ec.last_write(rows,ci,register)
        zero=(load or{}).get('byteMemoryZeroExtensionOperation',{});address=zero.get('sourceAddress',{})
        if zero.get('memoryReadBytes')==1 and address.get('base')==local_base and address.get('index')is None and \
            address.get('displacement')==displacement and _ALIASES.get(zero.get('destinationRegister'))==register:
            chosen.append((ci,row,load))
    ci,count_row,loaded=ec.one(chosen,lambda x:True,LABEL+'.helper-member-count')
    for row in rows[index+1:ci]:
        move=row.get('memoryOperation',{});address=move.get('address',{})
        need('header-byte-preserved',not(move.get('direction')=='store'and address.get('base')==local_base and
            address.get('index')is None and address.get('displacement',-1)<=displacement<address.get('displacement',-1)+move.get('memoryBytes',0)),row)
        need('stable-header-frame',not row['text'].startswith(('push ','pop ','sub rsp, ','add rsp, ')),row)
    helper_target=control_transfer(call)['target'];family,windows,body=ec.family(image,helper_target-base)
    program=source.object_header_program(body,helper_target,offsets);by={ec.va(r):r for r in body}
    tail=_null_tail(rows,edge['target'],entry,output,base,barrier,disabled_flag,owned_partition,ordinary_zero_prover)
    extra={}
    if local_base=='rbp':
        alias,entry_alias=_header_rbp_alias(tail['frame']['prologue'],tail['frame']['savedHomes'],base)
        need('RBP-header-base-preserved',ec.last_write(rows,ci,'rbp')==alias[0])
        need('exact-RBP-header-zero-and-count',ec.raw(stores[-1])==bytes.fromhex('c645')+bytes((displacement,0))
            and ec.raw(count_row)==bytes.fromhex('807d')+bytes((displacement,count)),(stores[-1],count_row))
        relative=alias[1]+displacement
        rsp_displacement=tail['frame']['frameBytes']+relative
        need('RBP-header-outside-call-home',rsp_displacement>=32)
        extra['headerAddress']=dict(baseRegister='rbp',displacement=displacement,entryRspOffset=relative,
            rspDisplacement=rsp_displacement,baseAliasInstruction=ec.site(alias[0],base))
        if entry_alias is not None:
            need('finite-entry-RAX-header-frame',tail['frame']['frameBytes']==168
                and(displacement,relative,rsp_displacement)in((103,8,176),(111,16,184))and alias[1]==-95)
            extra['headerAddress'].update(baseAliasProfile='entry-RAX-RBP-95-header.v1',entryRspAliasInstruction=ec.site(entry_alias,base))
    else:
        relative=displacement-tail['frame']['frameBytes'];rsp_displacement=displacement
    need('header-byte-in-owned-frame',(-tail['frame']['frameBytes']<=relative<0 or 8<=relative<40)and
        all(not home<=relative<home+8 for home in tail['frame']['savedHomes'].values()))
    return count_row,tail,dict(mode='helper',call=ec.site(call,base),helperTargetRva=helper_target-base,
        helperFamily=family,helperWindows=windows,helperProgram=[ec.site(by[a],base)for a in program],
        headerLocalDisplacement=rsp_displacement,resultLoad=ec.site(loaded,base)if loaded else None,**extra)


def _inline(rows,entry,count,roles,image,offsets,barrier,disabled_flag,owned_partition=None,ordinary_zero_prover=None):
    base=image.pe.image_base;reader=roles['reader'];by={ec.va(r):r for r in rows}
    null=ec.one(rows,lambda r:re.fullmatch(r'cmp (?:[abcd]l|[sd]il|[bs]pl|r1[2345]b), -0x1',r['text'])is not None,LABEL+'.inline-null')
    register=null['text'][4:].split(',')[0]
    count_row=ec.one(rows,lambda r:r['text']==f'cmp {register}, {hex(count)}',LABEL+'.inline-member-count')
    root=_ALIASES.get(register,register);candidates=[]
    for i,row in enumerate(rows[:-1]):
        zero=rows[i+1].get('byteMemoryZeroExtensionOperation',{})
        if ec.va(row)<ec.va(null)and row['text']==f'mov rax, [{reader}+{offsets["currentPtr"]:#x}]'and \
            _ALIASES.get(zero.get('destinationRegister'))==root:candidates.append((i,row))
    index,start=ec.one(candidates,lambda x:True,LABEL+'.inline-source')
    predicates=[]
    for pi,row in enumerate(rows[:-1]):
        if row['text']!=f'cmp dword [{reader}+{offsets["bufferLength"]:#x}], 0x1':continue
        edge=rows[pi+1];predicate=control_transfer(edge)
        if predicate['kind']=='conditional'and(predicate['conditionCode']==13 and predicate['target']==ec.va(start)or
            predicate['conditionCode']==12 and ec.va(edge)+len(ec.raw(edge))==ec.va(start)):
            predicates.append((row,edge))
    buffer_compare,buffer_edge=ec.one(predicates,lambda x:True,LABEL+'.inline-buffer-predicate')
    path=[];at=ec.va(start)
    while at!=ec.va(null):
        need('inline-source-boundary',at in by and at not in {ec.va(r)for r in path}and len(path)<20)
        row=by[at];path.append(row);flow=control_transfer(row)
        if flow['kind']=='conditional':
            need('inline-nonnegative-edge',flow['conditionCode']in(8,9))
            at=flow['target']if flow['conditionCode']==9 else at+len(ec.raw(row))
        else:
            need('inline-source-transfer',flow['kind']=='next',row);at+=len(ec.raw(row))
    width,program=ec.inline_read(path,0,reader,offsets);need('inline-one-complete-byte',width==1 and path==program)
    need('inline-output-provenance',ec.last_write(rows,index,roles['output'])==roles['outputSave'])
    edge=by[ec.va(null)+len(ec.raw(null))];flow=control_transfer(edge)
    need('inline-exact-ff-edge',flow['kind']=='conditional'and flow['conditionCode']==4)
    tail=_null_tail(rows,flow['target'],entry,roles['output'],base,barrier,disabled_flag,owned_partition,ordinary_zero_prover)
    return count_row,tail,dict(mode='inline',bufferPredicate=ec.site(buffer_compare,base),
        bufferEdge=ec.site(buffer_edge,base),sourceProgram=[ec.site(r,base)for r in path],
        nullCompare=ec.site(null,base),nullEdge=ec.site(edge,base))


def derive(image,rows,entry,count,offsets,barrier,*,disabled_flag=None,owned_partition=None):
    """Return exact current header role proof and its selected count row."""
    need('member-count-domain',type(count)is int and 0<count<250)
    roles=_arguments(rows,entry);failures=[];ordinary_family=None
    def ordinary_zero_prover(sites,register):
        nonlocal ordinary_family
        if owned_partition is not None:
            return _owned_zero_source(rows,entry,sites,register,image.pe.image_base,owned_partition)
        if ordinary_family is None:
            base=image.pe.image_base;family,windows,current=ec.family(image,entry-base)
            need('same-fresh-complete-ordinary-zero-family',current==rows and not any(r['text'].startswith('db ')for r in current))
            ordinary_family=dict(status='current-owned-ordinary-zero-family-proved',entryRva=entry-base,
                family=family,codeWindows=windows,rows=current)
        return _owned_zero_source(rows,entry,sites,register,image.pe.image_base,ordinary_family)
    for builder in(_helper,_inline):
        try:
            count_row,tail,proof=builder(rows,entry,count,roles,image,offsets,barrier,disabled_flag,owned_partition,ordinary_zero_prover);break
        except(ValueError,KeyError,IndexError,TypeError)as error:failures.append(str(error)[:800])
    else:raise ValueError(LABEL+'.unsupported-header:'+str(failures))
    base=image.pe.image_base;frame=tail.pop('frame')
    proof.update(readerRegister=roles['reader'],outputRegister=roles['output'],
        readerSave=ec.site(roles['readerSave'],base),outputSave=ec.site(roles['outputSave'],base),
        memberCountInstruction=ec.site(count_row,base),wireBytes=1,nullMarker=255,outputBytes=8,
        nullReturnProgram=[ec.site(r,base)for r in tail.pop('rows')],nullReturn=tail,
        nullFrameBytes=frame['frameBytes'],nullSavedHomes=frame['savedHomes'],
        prologue=[ec.site(r,base)for r in frame['prologue']],positiveMembersAdmitted=False,entryPrefixAdmitted=False,
        condition='Current static Reader/byref-wrapper ABI with coherent compatible disjoint storage and normal ABI-preserving helpers. Selected initialized/lifecycle source prefix and positive members remain independent. Inline collector guard, when present, is selected disabled.')
    if ordinary_family is not None:proof['ordinaryZeroFamily']=ordinary_family
    return proof,count_row
