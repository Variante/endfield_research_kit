"""Current generated member return transfers and metadata-owned setters.

The shared caller checks preserve the full native return representation for
byte, DWORD, QWORD and floating sources. Getter/factory and child framing are
separate capabilities; a named call never proves those implementations.
"""
from __future__ import annotations
import json,re
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.memorypack import buff_ec_profiles_native as ec

LABEL='generatedMemberSource'
NONVOLATILE={'rbx','rbp','rsi','rdi','r12','r13','r14','r15'}


def need(check,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+check+':'+str(detail)[:700])


def return_abi(event):
    kind=event['kind']
    if kind in('byte','raw-byte'):return'byte'
    if kind=='scalar32'or kind.startswith('value4:'):return'eax'
    if kind in('raw4','float64'):return'xmm0'
    if kind in('scalar64','byte-payload','value8:UnityEngine.Vector2','value8:UnityEngine.Vector2Int',
            'value8:Beyond.Gameplay.AI.EnemyCheckAIMarker+EnemyCheckAIMarkerInfo',
            'value8:Beyond.Gameplay.Core.CharInteractPerform.HandIKParams')or kind.startswith('reference:'):return'rax'
    raise ValueError(LABEL+'.unsupported-return-kind:'+kind)


def _direct_call_transfers(rows,events,setter_targets,base,*,normal_path,reader,output,ordinal_start=0,event_count=None):
    """Exact source-to-setter normal calls, including owned null throws."""
    need('setter-count',len(events)==len(setter_targets))
    by={ec.va(row):index for index,row in enumerate(rows)};by_va={ec.va(row):row for row in rows};result=[]
    need('unique-owned-instructions',len(by)==len(rows))
    path_indices={ec.va(row):index for index,row in enumerate(normal_path)}
    for local_ordinal,(event,target)in enumerate(zip(events,setter_targets)):
        ordinal=ordinal_start+local_ordinal;total=len(events)if event_count is None else event_count
        start=base+event['instruction'][0];path_index=path_indices[start]
        part=[by_va[ec.va(row)]for row in normal_path[path_index+1:path_index+7]]
        need('complete-call-transfer',len(part)==6,event['memberIndex'])
        test,branch,method_info,transfer,receiver,call=part
        operands=test['text'].removeprefix('test ').split(', ')
        need('receiver-null-test',test['text'].startswith('test ')and len(operands)==2 and
            operands[0]==operands[1]and operands[0]in NONVOLATILE,event['memberIndex'])
        register=operands[0];need('same-setter-receiver',receiver['text']==f'mov rcx, {register}')
        need('reader-not-overwritten-by-receiver',register!=reader)
        wrapper_load=ec.last_write(normal_path,path_index,register)
        need('receiver-from-current-output',wrapper_load is not None and wrapper_load['text']==f'mov {register}, [{output}]')
        output_write=ec.last_write(normal_path,path_index,output)
        need('output-pointer-preserved',output_write is None or
            ordinal==total-1 and register==output and output_write is wrapper_load)
        flow=control_transfer(branch)
        need('receiver-nonnull-edge',flow['kind']=='conditional'and flow['conditionCode']in(4,5))
        null_at=flow['target']if flow['conditionCode']==4 else ec.va(branch)+len(ec.raw(branch))
        normal_at=ec.va(branch)+len(ec.raw(branch))if flow['conditionCode']==4 else flow['target']
        need('receiver-exact-normal-edge',normal_at==ec.va(method_info))
        exception=by_va.get(null_at);terminal=by_va.get(null_at+5)
        need('owned-nonreturning-null-exit',exception is not None and ec.raw(exception)[:1]==b'\xe8'and
            terminal is not None and ec.raw(terminal)==b'\xcc')
        abi=return_abi(event);moves={'byte':{b'\x0f\xb6\xd0',b'\x8a\xd0'},'eax':{b'\x8b\xd0'},
            'rax':{b'\x48\x8b\xd0'},'xmm0':{b'\x0f\x28\xc8'}}
        need('zero-MethodInfo-and-whole-value',ec.raw(method_info)==b'\x45\x33\xc0'and ec.raw(transfer)in moves[abi],
            dict(member=event['memberIndex'],returnAbi=abi,transfer=transfer))
        actual=control_transfer(call);need('actual-named-setter-call',actual['kind']=='call'and actual['target']==target)
        result.append(dict(memberIndex=event['memberIndex'],sourceCall=event['instruction'],
            returnAbi=abi,transfer=ec.site(transfer,base),receiver=register,setterCall=ec.site(call,base),
            wrapperLoad=ec.site(wrapper_load,base),setterTargetRva=target-base,
            ownedNullExit=ec.site(exception,base),setterImplementationAdmitted=False))
    return result



_VALUE_REGISTERS={'rax':0,'rcx':1,'rdx':2,'rbx':3,'rsp':4,'rbp':5,'rsi':6,'rdi':7,**{'r'+str(i):i for i in range(8,16)}}
_VALUE_DWORDS={r:(r[1:]+'x'if r in('rax','rbx','rcx','rdx')else 'e'+r[1:]if r in('rbp','rsi','rdi','rsp')else r+'d')for r in _VALUE_REGISTERS}
_VALUE_DWORDS.update(rax='eax',rbx='ebx',rcx='ecx',rdx='edx')
_VALUE_BYTES=dict(rax='al',rbx='bl',rcx='cl',rdx='dl',rbp='bpl',rsp='spl',rsi='sil',rdi='dil',**{'r'+str(i):'r'+str(i)+'b'for i in range(8,16)})
def _store_encoding(destination,source,field,width):
 b=_VALUE_REGISTERS[destination];r=_VALUE_REGISTERS[source];rex=(0x48 if width==8 else 0x40)|(4 if r>=8 else 0)
 prefix=bytes((rex,))if width==8 or r>=8 or width==1 and r>=4 else b''
 size=1 if field<128 else 4;return prefix+bytes((0x88 if width==1 else 0x89,(0x40 if size==1 else 0x80)|((r&7)<<3)|b))+field.to_bytes(size,'little',signed=True)
def inline_field_transfer(rows,event,setter,base,*,normal_path,reader,output,ordinal,total,barrier):
 by={ec.va(r):r for r in rows};start=next(i for i,r in enumerate(normal_path)if ec.va(r)==base+event['instruction'][0]);at=start+1;selected=[];calls=[];nulls=[]
 def row():
  need('complete-inline-field-transfer',at<len(normal_path));return by[ec.va(normal_path[at])]
 def take(text=None,raw=None):
  nonlocal at
  r=row();need('inline-transfer-instruction',(text is None or r['text']==text)and(raw is None or ec.raw(r)==raw),dict(expected=text,row=r));selected.append(r);at+=1;return r
 def guard(register):
  take('test '+register+', '+register);branch=take();flow=control_transfer(branch);need('inline-owned-null-branch',flow['kind']=='conditional'and flow['conditionCode']in(4,5))
  null=flow['target']if flow['conditionCode']==4 else ec.va(branch)+len(ec.raw(branch));normal=ec.va(branch)+len(ec.raw(branch))if flow['conditionCode']==4 else flow['target'];need('inline-exact-normal-edge',normal==ec.va(row()))
  call=by.get(null);end=by.get(null+5);need('inline-owned-null-throw',call is not None and ec.raw(call)[:1]==b'\xe8'and end is not None and ec.raw(end)==b'\xcc');nulls.append(ec.site(call,base))
 abi=return_abi(event);value='rax';saved=None
 # A getter may clobber volatile source returns, so every returned bit is first
 # saved in an actual Win64 nonvolatile register, owned by the full frame proof.
 if row()['text'].startswith(('movzx ','mov ')):
  found=None
  for register in NONVOLATILE:
   n=_VALUE_REGISTERS[register];rex=bytes((0x44,))if n>=8 else b''
   variants={'byte':(f'movzx {_VALUE_DWORDS[register]}, al',rex+b'\x0f\xb6'+bytes((0xc0+((n&7)<<3),))),
    'eax':(f'mov {_VALUE_DWORDS[register]}, eax',rex+b'\x8b'+bytes((0xc0+((n&7)<<3),))),
    'rax':(f'mov {register}, rax',bytes((0x48|(4 if n>=8 else 0),0x8b,0xc0+((n&7)<<3))))}
   if abi in variants and(row()['text'],ec.raw(row()))==variants[abi]:found=register;break
  if found is not None:saved=take();value=found
 test=row()['text'];match=re.fullmatch(r'test (\w+), \1',test);need('inline-wrapper-null-test',match is not None and match[1]in NONVOLATILE,test);receiver=match[1]
 wrapper_load=ec.last_write(normal_path,start,receiver);need('inline-wrapper-from-output',wrapper_load is not None and wrapper_load['text']==f'mov {receiver}, [{output}]')
 need('inline-reader-survives-wrapper',receiver!=reader)
 output_write=ec.last_write(normal_path,start,output);need('inline-output-preserved',output_write is None or ordinal==total-1 and receiver==output and output_write is wrapper_load)
 guard(receiver);getter=setter['getter'];field=setter['fieldOffset']
 if row()['text']=='xor edx, edx':
  need('inline-getter-whole-return-preserved',saved is not None and getter is not None)
  take('xor edx, edx',bytes.fromhex('33d2'));take(f'mov rcx, {receiver}');call=take();flow=control_transfer(call)
  need('inline-exact-current-getter-call',flow['kind']=='call'and flow['target']==base+getter['method'][3]);calls.append(ec.site(call,base));guard('rax');destination='rax';profile='called-compatible-getter-inline-store'
 else:
  need('inline-direct-current-holder',getter is None and setter['profile']=='direct-base-holder-setter'and saved is None)
  holder=setter['program']['holderOffset'];take(f'mov rcx, [{receiver}+{holder:#x}]');guard('rcx');destination='rcx';profile='direct-holder-inline-store'
 # A final direct store may be scheduled between exact frame restores. Their
 # homes and all widths are independently checked by the full caller frame.
 if ordinal==total-1:
  while row().get('memoryOperation',{}).get('direction')=='load'and row()['memoryOperation'].get('address',{}).get('base')=='rsp':take()
 width={'byte':1,'eax':4,'rax':8}.get(abi);need('inline-source-return-width',width is not None and setter['storedBytes']==width)
 reference=event['kind'].startswith('reference:')or event['kind']=='byte-payload'
 reference_store_first=reference and destination=='rcx'and row()['text']==f'mov [{destination}+{field:#x}], {value}'
 if reference and not reference_store_first:take(f'lea rcx, [{destination}+{field:#x}]')
 val=_VALUE_BYTES[value]if width==1 else _VALUE_DWORDS[value]if width==4 else value
 store=take(f'mov [{destination}+{field:#x}], {val}',_store_encoding(destination,value,field,width))
 if reference:
  if reference_store_first:
   if row()['text']==f'add rcx, {field:#x}':
    encoded=b'\x48\x83\xc1'+bytes((field,))if field<128 else b'\x48\x81\xc1'+field.to_bytes(4,'little',signed=True)
    take(raw=encoded)
   else:take(f'lea rcx, [rcx+{field:#x}]')
  restores=[]
  while ordinal==total-1 and (row().get('memoryOperation',{}).get('direction')=='load'and row()['memoryOperation'].get('address',{}).get('base')=='rsp'and row()['memoryOperation'].get('register')in NONVOLATILE or row()['text'].startswith('add rsp, ')or row()['text'].startswith('pop ')and row()['text'][4:]in NONVOLATILE):restores.append(take())
  call=take();flow=control_transfer(call);need('inline-exact-current-reference-barrier',flow['kind']in('call','jump')and flow['target']==barrier)
  if flow['kind']=='jump':need('final-restored-reference-tail',ordinal==total-1 and at==len(normal_path))
  else:need('restores-require-terminal-barrier',not restores);calls.append(ec.site(call,base))
 result=dict(memberIndex=event['memberIndex'],sourceCall=event['instruction'],returnAbi=abi,receiver=receiver,wrapperLoad=ec.site(wrapper_load,base),
  setterTargetRva=setter['method'][3],setterImplementationAdmitted=False,profile=profile,fieldOffset=field,storedBytes=width,
  transferProgram=[ec.site(r,base)for r in selected],actualCalls=calls,ownedNullExits=nulls,store=ec.site(store,base),
  sourceReturnSaved=ec.site(saved,base)if saved is not None else None,fieldGetter=getter,
  normalWholeSourceValueStoredUnchanged=True)
 if reference and flow['kind']=='jump':result['referenceBarrierTail']=ec.site(call,base)
 return result


def call_transfers(rows,events,setter_targets,base,*,normal_path,reader,output,setter_proofs=None,barrier=None):
    if setter_proofs is None:
        return _direct_call_transfers(rows,events,setter_targets,base,normal_path=normal_path,reader=reader,output=output)
    need('independent-setter-proof-count',len(events)==len(setter_proofs)==len(setter_targets)and type(barrier)is int)
    result=[]
    for ordinal,(event,target,setter)in enumerate(zip(events,setter_targets,setter_proofs,strict=True)):
        need('same-current-named-setter-target',setter['method'][3]==target-base)
        try:
            transfer,=_direct_call_transfers(rows,[event],[target],base,normal_path=normal_path,reader=reader,output=output,ordinal_start=ordinal,event_count=len(events))
        except(ValueError,KeyError,IndexError):
            transfer=inline_field_transfer(rows,event,setter,base,normal_path=normal_path,reader=reader,output=output,
                ordinal=ordinal,total=len(events),barrier=barrier)
        result.append(transfer)
    return result


def _body(image,pointer,*,pins=None):
    base=image.pe.image_base;regions=[];rows=[];partition=None
    try:
        family,windows,rich=ec.family(image,pointer-base)
        for window in windows:
            at=base+window['startRva'];raw=image.window_bytes(window);regions.append((at,raw))
            rows+=image.mapper.decode_x64_subset(raw,at,stop_offset=len(raw))
    except(ValueError,IndexError):
        if pins is None:raise
        from scripts.game_data.memorypack.generated_owned_code_sources import source_family
        family,windows,rows,partition=source_family(image,pins,entry_rva=pointer-base)
        need('failed-linear-body-requires-owned-data-partition',partition is not None)
        regions=[(base+w['startRva'],image.window_bytes(w))for w in windows]
    result=dict(pointer=pointer,family=family,windows=windows,regions=regions,rows=rows)
    if partition is not None:result['ownedCodePartition']=partition
    return result


def _displacement(prefix,offset):
    need('field-displacement',type(offset)is int and 16<=offset<2**31)
    raw=bytearray.fromhex(prefix);size=1 if offset<128 else 4
    raw[-1]=(raw[-1]&63)|(64 if size==1 else 128)
    return(raw+offset.to_bytes(size,'little',signed=True)).hex()


def base_setter_program(rows,*,holder,field,mode,barrier):
    """Complete ordinary base setters with either exact null-guard direction."""
    from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
    from scripts.game_data.il2cpp.zero_wrapper_programs import Joins,_branch,_exact
    modes={'normalized-byte-return':('dl','8850'),'int32-return':('edx','8950'),
        'qword-return':('rdx','488950'),'single-return':('xmm1','f30f1148'),
        'double-return':('xmm1','f20f1148')}
    need('base-setter-mode',mode in modes or mode=='reference-return')
    reference=mode=='reference-return';register='rcx'if reference else'rax'
    g=ProgramGrammar(rows,label=LABEL+'.baseSetter');joins=Joins(LABEL+'.baseSetter')
    g.take('sub rsp, 0x28');_exact(g,f'mov {register}, [rcx+{holder:#x}]',_displacement('488b49'if reference else'488b41',holder))
    g.take(f'test {register}, {register}')
    predicate=control_transfer(g.rows[g.cursor]);need('base-null-guard',predicate['kind']=='conditional'and predicate['conditionCode']in(4,5))
    positive=predicate['conditionCode']==5
    if positive:
        joins.edge('store',_branch(g,'jne'));call=g.row();flow=control_transfer(call)
        need('base-owned-null-call',flow['kind']=='call');g.take('int3');joins.mark('store',g)
    else:joins.edge('null',_branch(g,'je'))
    if reference:
        _exact(g,f'mov [rcx+{field:#x}], rdx',_displacement('488951',field))
        if field==128 and g.rows[g.cursor]['text']=='sub rcx, -0x80':
            _exact(g,'sub rcx, -0x80','4883e980')
        else:
            encoded='4883c1'+bytes((field,)).hex()if field<128 else'4881c1'+field.to_bytes(4,'little').hex()
            _exact(g,f'add rcx, {field:#x}',encoded)
        g.take('add rsp, 0x28')
        tail=_branch(g,'jmp');need('base-actual-barrier',tail['target']==barrier)
    else:
        value,prefix=modes[mode]
        _exact(g,f'{"movss"if mode=="single-return"else"movsd"if mode=="double-return"else"mov"} [rax+{field:#x}], {value}',_displacement(prefix,field))
        g.take('add rsp, 0x28','ret')
    if not positive:
        joins.mark('null',g);call=g.row();flow=control_transfer(call)
        need('base-owned-null-call',flow['kind']=='call');g.take('int3')
    g.finish()
    return dict(profile='ordinary-base-setter',holderOffset=holder,fieldOffset=field,mode=mode,
        completeOriginalProgram=True,localJoins=joins.finish(),normalIncomingValueStoredUnchanged=True,
        ordinaryFrameRestored=True,normalReturnViaBarrier=reference)


def coherent_getter_program(regions,entry,*,base_slot,cache_slot,mode,path_factory=None):
    """Selected equality return; refresh and initialization are unadmitted."""
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    need('coherent-getter-slots',type(base_slot)is int and type(cache_slot)is int and
        16<=base_slot<cache_slot<128 and mode in('rbx','rdi'))
    need('coherent-getter-path-factory',path_factory is None or callable(path_factory))
    g=(BytesPath if path_factory is None else path_factory)(regions,entry)
    def peek(n=1):return bytes(g.bytes[g.at+i]for i in range(n))
    def edge(code,taken):
        short,near={4:('74','0f84'),5:('75','0f85')}[code]
        if peek()==bytes.fromhex(short):g.branch(short,taken,1)
        else:g.branch(near,taken)
    if mode=='rbx':g.take('4053','4883ec20')
    else:g.take('48895c2408','57','4883ec20')
    flag=g.relative('803d')+1;g.take('00','488bd9'if mode=='rbx'else'488bf9')
    edge(4,False)if peek()in(b'\x74',)or peek(2)==b'\x0f\x84'else edge(5,True)
    reg='7b'if mode=='rbx'else'7f';b=bytes((base_slot,)).hex();c=bytes((cache_slot,)).hex()
    g.take('4883'+reg+c+'00')
    edge(4,False)if peek()==b'\x74'or peek(2)==b'\x0f\x84'else edge(5,True)
    g.take('488b43'+b if mode=='rbx'else'488b47'+b,'483943'+c if mode=='rbx'else'483947'+c)
    edge(4,True)if peek()==b'\x74'or peek(2)==b'\x0f\x84'else edge(5,False)
    g.take('488b43'+c if mode=='rbx'else'488b47'+c)
    if mode=='rdi':g.take('488b5c2430')
    g.take('4883c420','5b'if mode=='rbx'else'5f','c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag,baseSlot=base_slot,cacheSlot=cache_slot,
        fullSameReferenceReturned=True,normalReturn=True,entryRspRestored=True,
        condition='Initialized wrapper with equal nonnull original/cache references and stable compatible disjoint storage. Refresh and cold paths are separate.')


def cached_qword_setter_program(regions,entry,*,getter,field):
    """Current whole RDX/RBX scalar with either owned nonnull branch form."""
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    need('cached-qword-field-domain',type(field)is int and 16<=field<2**31)
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bda','33d2');g.call(getter);g.take('4885c0')
    _nonnull_edge(g);g.take(_displacement('488958',field),'4883c420','5b','c3')
    return dict(selectedBytes=g.seen,field=field,storedBytes=8,unchangedArgumentStored=True,normalReturn=True,
        entryRspRestored=True,nonvolatileRbxRestored=True,
        condition='The independently current ordinary typed getter returns the compatible nonnull Original; whole incoming RDX is preserved in RBX and stored exactly once to the bound named scalar field. Complete own frame restores RBX; source framing and runtime invocation remain separate.')


def cached_floating_setter_program(regions,entry,*,getter,field,mode):
    """Own unchanged XMM1 scalar through a normal nonnull cached getter."""
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    need('cached-floating-mode',mode in('single-return','double-return'))
    g=BytesPath(regions,entry);g.take('4883ec38','0f29742420','33d2','0f28f1');g.call(getter);g.take('4885c0')
    _nonnull_edge(g)
    g.take(_displacement('f30f1170'if mode=='single-return'else'f20f1170',field),
        '0f28742420','4883c438','c3')
    return dict(selectedBytes=g.seen,storedBytes=4 if mode=='single-return'else 8,fieldOffset=field,
        incomingFloatingBitsStoredUnchanged=True,entryRspRestored=True,nonvolatileXmm6Restored=True,
        condition='The exact independently proved getter returns a compatible nonnull original and preserves Win64 nonvolatiles. Null and throwing paths are separate.')


def _nonnull_edge(g):
    first=bytes((g.bytes[g.at],));pair=bytes(g.bytes[g.at+i]for i in range(2))
    if first==b'\x75':g.branch('75',True,1)
    elif first==b'\x74':g.branch('74',False,1)
    elif pair==b'\x0f\x85':g.branch('0f85',True)
    else:g.branch('0f84',False)


def inline_cached_setter_program(regions,entry,*,field,mode,base_slot,cache_slot,barrier,path_factory=None,image_base=None):
    """Complete initialized coherent inline getter/store normal path."""
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    need('inline-cached-role-domain',mode in('normalized-byte-return','int32-return','qword-return','reference-return','single-return','double-return')and
        16<=base_slot<cache_slot<128)
    need('callable-only-selected-path-factory',path_factory is None or callable(path_factory))
    prefix_bytes={p+i:b for p,raw in regions for i,b in enumerate(raw)}
    prefix=bytes(prefix_bytes.get(entry+i,0)for i in range(6))
    if prefix in(bytes.fromhex('40554883ec50'),bytes.fromhex('40534883ec50')):
        need('actual-large-setter-image-base',type(image_base)is int and image_base>=0)
        from scripts.game_data.memorypack.generated_cached_setter_sources import program
        return program(regions,entry,field=field,mode=mode,base_slot=base_slot,cache_slot=cache_slot,
            image_base=image_base,path_factory=path_factory)
    floating=mode in('single-return','double-return');reference=mode=='reference-return'
    g=(BytesPath if path_factory is None else path_factory)(regions,entry)
    if floating:g.take('4883ec38')
    else:g.take('4056','4883ec20')
    flag=g.relative('803d')+1;g.take('00')
    if floating:g.take('0f29742420','0f28f1','48897c2430','488bf9')
    else:g.take({'normalized-byte-return':'0fb6f2','int32-return':'8bf2','qword-return':'488bf2','reference-return':'488bf2'}[mode],'48895c2430','488bd9')
    _nonnull_edge(g)
    b=bytes((base_slot,)).hex();c=bytes((cache_slot,)).hex();address='47'if floating else'43';test='7f'if floating else'7b'
    g.take('4883'+test+c+'00');_nonnull_edge(g)
    g.take('488b'+address+b,'4839'+address+c)
    # Cache equality is JE-taken or JNE-fallthrough, with original branch bytes.
    first=bytes((g.bytes[g.at],));pair=bytes(g.bytes[g.at+i]for i in range(2))
    if first==b'\x74':g.branch('74',True,1)
    elif first==b'\x75':g.branch('75',False,1)
    elif pair==b'\x0f\x84':g.branch('0f84',True)
    else:g.branch('0f85',False)
    g.take('488b4b'+c if reference else'488b'+address+c,'488b7c2430'if floating else'488b5c2430','4885c9'if reference else'4885c0');_nonnull_edge(g)
    prefix={'normalized-byte-return':'408870','int32-return':'8970','qword-return':'488970','reference-return':'488971','single-return':'f30f1170','double-return':'f20f1170'}[mode]
    g.take(_displacement(prefix,field))
    if reference:
        # SUB r64, signed imm8 is an exact positive field-address adjustment
        # only when that negative immediate equals this independently bound
        # field displacement. In particular SUB RCX,-128 does not truncate
        # the incoming pointer or borrow the unsigned ADD imm8 semantics.
        signed_adjustment=bytes(g.bytes.get(g.at+i,0)for i in range(4))
        if signed_adjustment[:3]==bytes.fromhex('4883e9'):
            need('inline-reference-exact-signed-field-address',
                int.from_bytes(signed_adjustment[3:],'little',signed=True)<0 and
                -int.from_bytes(signed_adjustment[3:],'little',signed=True)==field)
            g.take(signed_adjustment.hex())
        else:g.take('4883c1'+bytes((field,)).hex()if field<128 else'4881c1'+field.to_bytes(4,'little').hex())
    if floating:g.take('0f28742420','4883c438','c3')
    else:
        g.take('4883c420','5e')
        if reference:need('inline-actual-barrier',g.relative('e9')==barrier)
        else:g.take('c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag,fieldOffset=field,baseSlot=base_slot,cacheSlot=cache_slot,
        normalIncomingValueStoredUnchanged=True,entryRspRestored=True,nonvolatilesRestored=True,
        refreshAdmitted=False,normalReturnViaBarrier=reference,
        condition='Initialized matching metadata and equal nonnull compatible original/cache references, valid disjoint frame/field storage, and disabled barrier preserving Win64 ABI. Noncoherent refresh and initialization paths remain separate.')


def inline_predicate_getter_refresh_program(regions,entry,*,base_slot,cache_slot,predicate,barrier,refresh):
    """Exact current inlined compatible-class refresh, before warm return."""
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    need('inline-refresh-domain',base_slot==16 and cache_slot in(24,32,40)and refresh in('empty','different'))
    g=BytesPath(regions,entry);g.take('4053','4883ec20');flag=g.relative('803d')+1;g.take('00','488bd9');_nonnull_edge(g)
    c=bytes((cache_slot,)).hex();g.take('48837b'+c+'00')
    def eq(fact):
        first=bytes((g.bytes[g.at],));pair=bytes(g.bytes[g.at+i]for i in range(2))
        code=4 if first==b'\x74'or pair==b'\x0f\x84'else 5
        prefix=('74'if code==4 else'75')if first in(b'\x74',b'\x75')else('0f84'if code==4 else'0f85')
        g.branch(prefix,fact if code==4 else not fact,1 if len(prefix)==2 else 4)
    eq(refresh=='empty')
    if refresh=='different':g.take('488b4310','483943'+c);eq(False)
    g.take('48897c2430','488b7b10','4885ff');eq(False)
    first=g.relative('488b15');g.take('488b0f');g.call(predicate);g.take('84c0');eq(False)
    g.take('488bc7','488943'+c);second=g.relative('488b15');g.take('488b0f');g.call(predicate)
    g.take('488d4b'+c);g.call(barrier);g.take('488b7c2430');g.jump('eb',1)if g.bytes.get(g.at)==0xeb else g.jump('e9')
    g.take('488b43'+c,'4883c420','5b','c3');need('inline-refresh-same-class',first==second)
    return dict(selectedBytes=g.seen,initializedFlag=flag,baseSlot=base_slot,cacheSlot=cache_slot,refresh=refresh,
        sameBaseReferenceCachedAndReturned=True,normalReturn=True,entryRspRestored=True,
        condition='Initialized getter, compatible nonnull base, exact current predicate returns true normally on the selected first test, and disabled reference barrier preserving Win64 ABI. Predicate outcome and execution are conditional.')


def _getter_refresh(image,body,*,base_slot,cache_slot,original,barrier):
    """Both compatible refresh paths, with actual typed class and cast body."""
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import modelview_factory_sources as factories,pooled_string_list_sources as lists
    base=image.pe.image_base;calls={control_transfer(r)['target']for r in body['rows']if ec.raw(r)[:1]==b'\xe8'}
    candidates=[]
    for cast in sorted(calls-{barrier}):
        for profile in('rbx','rdi','inline-predicate-rbx','split-comparison-rbx','split-short-backward-rbx','split-initialized-short-backward-rbx','split-predicate-rbx'):
            programs=[]
            try:
                for refresh in('empty','different'):
                    if profile=='rbx':
                        need('refresh-base-rbx',base_slot==16)
                        proof=factories.cached_rbx(body['regions'],body['pointer'],dict(cast=cast,barrier=barrier),cache=cache_slot,refresh=refresh)
                    elif profile=='inline-predicate-rbx':
                        proof=inline_predicate_getter_refresh_program(body['regions'],body['pointer'],base_slot=base_slot,cache_slot=cache_slot,predicate=cast,barrier=barrier,refresh=refresh)
                    elif profile=='split-comparison-rbx':
                        from scripts.game_data.memorypack.generated_split_cache_refresh_sources import program
                        proof=program(body['regions'],body['pointer'],base_slot=base_slot,cache_slot=cache_slot,cast=cast,barrier=barrier,refresh=refresh)
                    elif profile=='split-short-backward-rbx':
                        from scripts.game_data.memorypack.generated_split_cache_refresh_sources import short_backward_program
                        proof=short_backward_program(body['regions'],body['pointer'],base_slot=base_slot,cache_slot=cache_slot,cast=cast,barrier=barrier,refresh=refresh)
                    elif profile=='split-initialized-short-backward-rbx':
                        from scripts.game_data.memorypack.generated_split_cache_refresh_sources import initialized_short_backward_program
                        proof=initialized_short_backward_program(body['regions'],body['pointer'],base_slot=base_slot,cache_slot=cache_slot,cast=cast,barrier=barrier,refresh=refresh)
                    elif profile=='split-predicate-rbx':
                        from scripts.game_data.memorypack.generated_split_predicate_cache_refresh_sources import program
                        proof=program(body['regions'],body['pointer'],base_slot=base_slot,cache_slot=cache_slot,predicate=cast,barrier=barrier,refresh=refresh)
                    else:
                        proof=lists.cached_list_getter(body['regions'],body['pointer'],base_slot=base_slot,cache_slot=cache_slot,
                            cast=cast,barrier=barrier,metadata_init=None,refresh=refresh)
                    selected={at+i for at,h in proof['selectedBytes']for i in range(len(bytes.fromhex(h)))}
                    usages=[]
                    for row in body['rows']:
                        if ec.va(row)in selected and ec.raw(row)[:3]==bytes.fromhex('488b15'):
                            typed=derive_typed_usage_context(image,ec.va(row)-base,label=LABEL+'.refreshClass')
                            need('exact-current-refresh-class',(typed['tag'],typed['typeName'])==(1,original));usages.append(typed)
                    need('two-refresh-class-uses',len(usages)==2)
                    programs.append(dict(path=refresh,program=proof,classUsages=usages))
                cast_body=_body(image,cast);predicates={control_transfer(r)['target']for r in cast_body['rows']if ec.raw(r)[:1]==b'\xe8'}
                if profile in('inline-predicate-rbx','split-predicate-rbx'):cast_program=dict(actualCompatibleClassPredicateRequired=True,predicateOutcomeProved=False)
                else:
                    need('one-compatible-cast-predicate',len(predicates)==1)
                    cast_program=lists.compatible_list_cast(cast_body['regions'],cast,predicates.pop(),null=False)
                candidates.append(dict(profile=profile,programs=programs,cast=dict(targetRva=cast-base,
                    family=cast_body['family'],codeWindows=cast_body['windows'],program=cast_program),
                    initializedCompatibleNonNullBaseRequired=True,emptyOrDifferentCacheAdmitted=True,
                    predicateOutcomeObserved=False,barrierTargetRva=barrier-base))
            except(ValueError,KeyError,IndexError):pass
    if len(candidates)!=1:
        summaries=[]
        for candidate in candidates[:8]:
            paths=[];classes=set()
            for item in candidate['programs']:
                selected=item['program']['selectedBytes']
                paths.append(dict(path=item['path'],selectedStartRva=min(at for at,_ in selected)-base,
                    selectedEndRva=max(at+len(bytes.fromhex(raw))for at,raw in selected)-base,
                    selectedBytes=sum(len(bytes.fromhex(raw))for _,raw in selected)))
                classes.update(u['usageCellRva']for u in item['classUsages'])
            summaries.append(dict(profile=candidate['profile'],castTargetRva=candidate['cast']['targetRva'],
                classCellRvas=sorted(classes)[:4],paths=paths,
                castWindows=[{key:w.get(key)for key in('startRva','endRva','sha256')}for w in candidate['cast']['codeWindows'][:2]],
                omittedCastWindows=max(0,len(candidate['cast']['codeWindows'])-2)))
        diagnostic=dict(expected=1,actual=len(candidates),typeName=original,methodName='get___instance',
            getterTargetRva=body['pointer']-base,baseSlot=base_slot,cacheOffset=cache_slot,candidates=summaries,
            omittedCandidates=max(0,len(candidates)-len(summaries)))
        raise ValueError(LABEL+'.one-complete-compatible-refresh:'+json.dumps(diagnostic,sort_keys=True,separators=(',',':')))
    return candidates[0]


def _coherent_getter(image,ctx,wrapper,getter,cache,*,barrier=None,pins=None):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    pointer=image.method_pointer_va(getter);cache_key=(pointer,wrapper.type_definition,getter.index,barrier)
    if cache_key in cache:return cache[cache_key]
    md=image.metadata;own=md.types[wrapper.type_definition]
    need('unique-current-wrapper-name',len(image.named_type_definitions.get(wrapper.name,()))==1 and
        image.named_type_definitions[wrapper.name][0].index==wrapper.type_definition)
    need('unique-current-original-name',len(image.named_type_definitions.get(wrapper.wrapped_type,()))==1)
    scalar.owned_method_abi(image,ctx,getter.index,own.index,(wrapper.wrapped_type,18,True),[],LABEL+'.getter')
    typed=ctx.field(wrapper.name+'::__realInstance')
    need('owned-typed-cache',typed[:2]==(wrapper.name,wrapper.wrapped_type))
    base_fields=[];name=ctx.parent(wrapper.name);seen=set()
    while name not in('','object','System.Object'):
        need('getter-base-depth',name not in seen and len(seen)<32);seen.add(name)
        td=ctx.index.types[name]
        for field in md.fields_for(td):
            field_name=md.string(field.name_index)
            if field_name in('___instance','__instance')and not ctx.field_attributes(field.type_index)&16:
                base_fields.append(ctx.field(name+'::'+field_name))
        name=ctx.parent(name)
    need('one-owned-base-holder',len(base_fields)==1,base_fields)
    from scripts.game_data.memorypack.lock_camera_member_sources import DERIVED_TYPES,original_ancestry
    base_field=base_fields[0];ancestry=set();name=wrapper.wrapped_type;constructed_ancestry=None
    from scripts.game_data.memorypack import constructed_action_ancestry_sources as constructed
    if name in constructed.TYPES or constructed.has_closed_node_parent(ctx,name):
        constructed_ancestry=constructed.derive(ctx,name);ancestry.update(constructed_ancestry['ancestry'])
    elif name in DERIVED_TYPES:ancestry.update(original_ancestry(ctx,name))
    else:
        while name not in('','object','System.Object'):
            need('original-ancestry-depth',name not in ancestry and len(ancestry)<32);ancestry.add(name);name=ctx.parent(name)
    need('original-derives-declared-base-holder',base_field[1]in ancestry,base_field)
    body=_body(image,pointer,pins=pins);proofs=[]
    for mode in('rbx','rdi'):
        try:proofs.append(coherent_getter_program(body['regions'],pointer,base_slot=base_field[2],cache_slot=typed[2],mode=mode))
        except(ValueError,KeyError,IndexError):pass
    if not proofs:
        from scripts.game_data.memorypack.generated_large_cached_sources import getter_program
        try:proofs.append(getter_program(body['regions'],pointer,base_slot=base_field[2],cache_slot=typed[2],image_base=image.pe.image_base))
        except(ValueError,KeyError,IndexError):pass
    need('one-complete-coherent-getter-profile',len(proofs)==1)
    proof=dict(method=[getter.index,wrapper.name,image.metadata.string(getter.name_index),pointer-image.pe.image_base],
        family=body['family'],codeWindows=body['windows'],program=proofs[0],baseHolder=base_field,typedCache=typed,
        coherentNonNullSamePointerReturn=True,refreshAdmitted=False,
        condition='Current initialized getter with equal nonnull original/cache references. Their compatible nominal identity and construction must be composed independently.')
    if constructed_ancestry is not None:proof['constructedOriginalAncestry']=constructed_ancestry
    if barrier is not None:
        try:
            if proofs[0].get('getterProfile')=='rsi-zero-rbp-image-base-inline-collector':
                from scripts.game_data.memorypack.generated_large_cached_sources import compatible_refresh
                proof['compatibleRefresh']=compatible_refresh(image,body,base_slot=base_field[2],cache_slot=typed[2],original=wrapper.wrapped_type,barrier=barrier)
            else:proof['compatibleRefresh']=_getter_refresh(image,body,base_slot=base_field[2],cache_slot=typed[2],original=wrapper.wrapped_type,barrier=barrier)
            proof['refreshAdmitted']=True
        except(ValueError,KeyError,IndexError)as error:proof['refreshPendingReason']=str(error)[:1000]
    cache[cache_key]=proof;return proof


def direct_field_binding(image,member,wrappers):
    """Fresh field/holder identity for an actual inline store, no setter claim."""
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import scalar_param_native as scalar
    ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member);md=image.metadata
    need('direct-field-reference-wrapper',not ctx.is_value_type(wrapper.wrapped_type))
    parameter,=md.parameters_for(method);raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16);kind=raw[10]
    reference=kind in(14,18,20,29)or kind==21 and not raw[11]&128
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[(member.declared_type,kind,reference)],LABEL+'.inlineFieldDeclaration')
    need('direct-field-nongeneric-setter-declaration',method.generic_container_index<0)
    widths={2:1,4:1,5:1,6:2,7:2,8:4,9:4,10:8,11:8,12:4,13:8}
    if reference:width=8
    elif kind in widths:width=widths[kind]
    elif kind==17 and member.declared_type=='UnityEngine.Vector2':width=8
    else:
        need('direct-field-enum',kind==17 and ctx.is_enum(member.declared_type));td=ctx.index.types[member.declared_type]
        backing,=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
        need('direct-field-enum-value',md.string(backing.name_index)=='value__');r=image.pe.bytes_at_va(ctx.type_pointer(backing.type_index),16)
        need('direct-field-enum-integer',r[10]in(4,5,6,7,8,9,10,11));scalar.ordinary(image,ctx.type_pointer(backing.type_index),r[10],LABEL+'.inlineEnumBacking');width=widths[r[10]]
    holder_name,holder=field(wrapper.name,{'___instance','__instance'})
    need('direct-field-current-holder',holder==(wrapper.name,wrapper.wrapped_type,16))
    holder_field,=[f for f in md.fields_for(md.types[wrapper.type_definition])if wrapper.name+'::'+md.string(f.name_index)==holder_name]
    scalar.ordinary(image,ctx.type_pointer(holder_field.type_index),18,LABEL+'.inlineHolder',reference=True)
    need('direct-field-offset',type(offset)is int and offset>=16)
    return dict(method=[method.index,wrapper.name,md.string(method.name_index),image.method_pointer_va(method)-image.pe.image_base],
        member=member.row(),targetField=target,fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=width,
        profile='metadata-field-binding',getter=None,program=dict(holderOffset=16),holder=holder,
        setterImplementationAdmitted=False,fieldStoreImplementationProved=False)


def _derive_setter(image,member,wrappers,barrier,getter_cache,*,pins=None):
    if member.declared_type=='Beyond.PosRot':
        from scripts.game_data.memorypack.generated_posrot_field_sources import derive_setter
        return derive_setter(image,pins,member,wrappers,barrier,getter_cache)
    from scripts.game_data.memorypack.lock_camera_member_sources import BASE_WRAPPERS,derive_setter as closed_lock_setter
    if member.declaring_wrapper in BASE_WRAPPERS:
        return closed_lock_setter(image,pins,member,wrappers,barrier,getter_cache)
    from scripts.game_data.memorypack.constructed_action_accessor_sources import selected_owner as closed_action_owner,derive_setter as closed_action_setter
    if closed_action_owner(wrappers,member.declaring_wrapper,image=image)is not None:
        return closed_action_setter(image,pins,member,wrappers,barrier,getter_cache)
    if member.declared_type=='Beyond.Gameplay.View.CameraControlStateInitialParam':
        from scripts.game_data.memorypack.generated_camera_initial_value_sources import derive_setter
        return derive_setter(image,pins,member,wrappers)
    if member.declared_type=='System.Nullable`1<float>':
        from scripts.game_data.memorypack.generated_nullable_value_sources import derive_setter
        need('explicit-selected-inputs-for-constructed-setter',isinstance(pins,dict)and bool(pins))
        return derive_setter(image,pins,member,wrappers,getter_cache)
    from scripts.game_data.memorypack import generated_managed_value_sources as managed
    if member.declared_type=='Beyond.Gameplay.Core.SmartTargetSelectSetting':
        from scripts.game_data.memorypack.generated_smart_target_field_sources import derive_setter
        return derive_setter(image,pins,member,wrappers,barrier,getter_cache)
    if member.declared_type=='Cinemachine.CinemachineImpulseManager+EnvelopeDefinition':
        from scripts.game_data.memorypack.generated_envelope_field_sources import derive_setter
        return derive_setter(image,pins,member,wrappers,barrier,getter_cache)
    if member.declared_type=='Beyond.Gameplay.BodyTypeDef':
        from scripts.game_data.memorypack.generated_body_type_field_sources import derive_setter
        return derive_setter(image,pins,member,wrappers,barrier,getter_cache)
    if member.declared_type=='Beyond.Gameplay.Core.EntityPtr':
        from scripts.game_data.memorypack.generated_entity_ptr_field_sources import derive_setter
        return derive_setter(image,pins,member,wrappers,barrier,getter_cache)
    if member.declared_type=='Beyond.Gameplay.Core.SkMorphPlaySetting':
        from scripts.game_data.memorypack.generated_sk_morph_field_sources import derive_setter
        return derive_setter(image,pins,member,wrappers,barrier,getter_cache)
    if member.declared_type in('Beyond.Gameplay.TrackingBounds','Beyond.Gameplay.Core.TriggerShapeData'):
        from scripts.game_data.memorypack.generated_outer_value_field_sources import derive_setter
        return derive_setter(image,pins,member,wrappers,barrier,getter_cache)
    if member.declared_type=='Beyond.Montage.AnimationClipAsyncInfo':
        from scripts.game_data.memorypack.generated_animation_clip_field_sources import derive_setter
        return derive_setter(image,pins,member,wrappers,barrier,getter_cache)
    if member.declared_type=='Beyond.FAnimationCurve':
        from scripts.game_data.memorypack.generated_beyond_curve_field_sources import derive_setter
        return derive_setter(image,pins,member,wrappers,barrier,getter_cache)
    if member.declared_type=='Beyond.Gameplay.View.Animation.AlphaBlend':
        from scripts.game_data.memorypack.generated_alpha_blend_field_sources import derive_setter
        return derive_setter(image,pins,member,wrappers,barrier,getter_cache)
    if member.declared_type=='UnityEngine.Vector3Int':
        from scripts.game_data.memorypack.generated_integer_vector_capture_sources import derive_setter
        return derive_setter(image,pins,member,wrappers,barrier,getter_cache)
    if member.declared_type in managed.NOMINALS:return managed._derive_setter(image,member,wrappers,barrier,getter_cache)
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata,prove_cached_field_setter
    from scripts.game_data.memorypack import modelview_holder_sources as holders,subgame_world_models as world
    from scripts.game_data.memorypack import scalar_param_native as scalar,pointer_param as pointer
    ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member)
    need('reference-original-setter-profile',not ctx.is_value_type(wrapper.wrapped_type),wrapper.wrapped_type)
    md=image.metadata;parameters=list(md.parameters_for(method));parameter=parameters[0]
    raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16);kind=raw[10]
    reference=kind in(14,18,20,29)or kind==21 and not raw[11]&128
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),
        [(member.declared_type,kind,reference)],LABEL+'.setter')
    need('nongeneric-member-setter',method.generic_container_index<0)
    body=_body(image,image.method_pointer_va(method),pins=pins);mm=pointer.methods(image,wrapper)
    getter=mm.get('get___instance');getter_proof=None;proof=None;profile=None;inline_refresh=None;inline_collector=None
    if member.kind=='bool'or member.width==1:mode='normalized-byte-return';stored_bytes=1
    elif member.kind in('scalar32','enum')and member.width==4:mode='int32-return';stored_bytes=4
    elif member.kind=='float32':mode='single-return';stored_bytes=4
    elif member.kind=='float64':mode='double-return';stored_bytes=8
    elif member.kind in('scalar64','enum')and member.width==8:mode='qword-return';stored_bytes=8
    elif reference:mode='reference-return';stored_bytes=8
    elif member.declared_type in('UnityEngine.LayerMask','Beyond.Gameplay.Core.GameplayTag','Beyond.Audio.AudioId'):
        mode='int32-return';stored_bytes=4
    elif member.declared_type=='UnityEngine.Vector2':
        need('Vector2-value-setter',kind==17 and not reference)
        mode='qword-return';stored_bytes=8
    elif member.declared_type=='UnityEngine.Vector2Int':
        from scripts.game_data.memorypack.generated_int2_member_sources import setter_layout
        need('own-Int2-ordinary-value-setter',kind==17 and not reference)
        layout=setter_layout(image,ctx,ctx.type_pointer(parameter.type_index));mode='qword-return';stored_bytes=8
    elif member.declared_type=='Beyond.Gameplay.AI.EnemyCheckAIMarker+EnemyCheckAIMarkerInfo':
        from scripts.game_data.memorypack.skill_ai_marker_value_sources import layout as marker_layout
        need('own-marker-ordinary-value-setter',kind==17 and not reference)
        layout=marker_layout(image,ctx);mode='qword-return';stored_bytes=8
    elif member.declared_type=='Beyond.Gameplay.Core.CharInteractPerform.HandIKParams':
        from scripts.game_data.memorypack.char_hand_ik_sources import layout as hand_layout
        need('own-HandIK-ordinary-value-setter',kind==17 and not reference)
        layout=hand_layout(image,ctx);mode='qword-return';stored_bytes=8
    elif member.declared_type in('UnityEngine.Vector3','UnityEngine.Quaternion'):
        from scripts.game_data.memorypack import generated_vector_member_sources as vectors
        need('named-vector-value-setter',kind==17 and not reference)
        layout=vectors.layout(image,ctx,member.declared_type);stored_bytes=layout['managedBytes'];mode='value-pointer-'+str(stored_bytes)
    elif member.declared_type=='UnityEngine.Color':
        from scripts.game_data.memorypack import generated_vector_member_sources as vectors
        from scripts.game_data.memorypack.unity_color_sources import layout as color_layout
        need('owned-Color-ordinary-value-setter',kind==17 and not reference)
        layout=color_layout(image,ctx);stored_bytes=layout['managedBytes'];mode='value-pointer-16'
    elif member.declared_type=='Beyond.AABB':
        from scripts.game_data.memorypack import generated_vector_member_sources as vectors
        from scripts.game_data.memorypack.generated_aabb_field_sources import owns_member,layout as aabb_layout
        need('own-Node-AABB-ordinary-value-setter',kind==17 and not reference and owns_member(wrapper.wrapped_type,member.name,member.declared_type))
        layout=aabb_layout(image,ctx);stored_bytes=layout['managedBytes'];mode='value-pointer-16'
    else:raise ValueError(LABEL+'.unsupported-setter-value:'+str((member.declared_type,member.kind,member.width)))
    errors=[]
    if getter is not None:
        try:getter_proof=_coherent_getter(image,ctx,wrapper,getter,getter_cache,barrier=image.pe.image_base+barrier,pins=pins)
        except(ValueError,KeyError,IndexError)as error:errors.append(str(error)[:1000])
    if getter_proof is not None:
        getter_target=image.method_pointer_va(getter)
        try:
            calls=[control_transfer(r)['target']for r in body['rows']if ec.raw(r)[:1]==b'\xe8']
            other=[at for at in calls if at!=getter_target]
            need('one-owned-setter-null-call',len(other)==1,other)
            symbols=dict(getter=getter_target,nullThrow=other[0],barrier=image.pe.image_base+barrier)
            if mode.startswith('value-pointer-'):
                proof=vectors.setter_program(body['regions'],body['pointer'],getter=getter_target,field=offset,width=stored_bytes)
            elif mode=='qword-return':
                try:
                    if offset<128:proof=holders.qword_setter(body['regions'],body['pointer'],getter=getter_target,field=offset)
                    else:proof=world.owned_scalar(body['regions'],body['pointer'],getter_target,slot=offset,width=8)
                except(ValueError,KeyError,IndexError):
                    try:proof=cached_qword_setter_program(body['regions'],body['pointer'],getter=getter_target,field=offset)
                    except(ValueError,KeyError,IndexError):
                        if member.declared_type!='UnityEngine.Vector2':raise
                        from scripts.game_data.memorypack.generated_vector2_cached_setter_sources import derive_setter
                        return derive_setter(image,pins,member,wrappers,barrier,getter_cache)
            elif mode in('single-return','double-return'):
                proof=cached_floating_setter_program(body['regions'],body['pointer'],getter=getter_target,field=offset,mode=mode)
            else:
                try:proof=prove_cached_field_setter(body['rows'],field_offset=offset,mode=mode,symbols=symbols,label=LABEL+'.cached')
                except(ValueError,KeyError,IndexError):
                    if mode!='reference-return'or getter_proof['program'].get('getterProfile')!='rsi-zero-rbp-image-base-inline-collector':raise
                    from scripts.game_data.memorypack.generated_large_cached_sources import reference_setter_program
                    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
                    inline_collector=_barrier(image,image.pe.image_base+barrier)
                    proof=reference_setter_program(body['regions'],body['pointer'],getter=getter_target,field=offset,
                        disabled=image.pe.image_base+inline_collector['result']['disabledFlagRva'])
            profile='cached-getter-setter'
        except(ValueError,KeyError,IndexError)as error:errors.append(str(error)[:1000])
        if proof is None:
            try:
                proof=inline_cached_setter_program(body['regions'],body['pointer'],field=offset,mode=mode,
                    base_slot=getter_proof['baseHolder'][2],cache_slot=getter_proof['typedCache'][2],barrier=image.pe.image_base+barrier,
                    image_base=image.pe.image_base)
                profile='inline-coherent-cache-setter'
                try:
                    from scripts.game_data.memorypack.generated_inline_refresh_sources import derive as inline_refresh_source
                    inline_refresh=inline_refresh_source(image,body,original=wrapper.wrapped_type,field=offset,mode=mode,
                        base_slot=getter_proof['baseHolder'][2],cache_slot=getter_proof['typedCache'][2],barrier=image.pe.image_base+barrier)
                except(ValueError,KeyError,IndexError):pass
            except(ValueError,KeyError,IndexError)as error:errors.append(str(error)[:1000])
    if proof is None:
        try:
            holder_name,holder=field(wrapper.name,{'___instance','__instance','__realInstance'})
            need('base-typed-holder',holder==(wrapper.name,wrapper.wrapped_type,16),holder)
            try:proof=base_setter_program(body['rows'],holder=holder[2],field=offset,mode=mode,barrier=image.pe.image_base+barrier)
            except(ValueError,KeyError,IndexError):
                from scripts.game_data.memorypack import generated_vector_member_sources as vectors
                if reference:
                    from scripts.game_data.memorypack.generated_inline_reference_setter_sources import program
                    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
                    holder_field,=[f for f in md.fields_for(md.types[wrapper.type_definition])
                        if wrapper.name+'::'+md.string(f.name_index)==holder_name]
                    scalar.ordinary(image,ctx.type_pointer(holder_field.type_index),18,LABEL+'.inlineReferenceHolder',reference=True)
                    inline_collector=_barrier(image,image.pe.image_base+barrier)
                    proof=program(body['regions'],body['pointer'],holder=holder[2],field=offset,
                        disabled=image.pe.image_base+inline_collector['result']['disabledFlagRva'])
                elif member.declared_type=='UnityEngine.Vector2'and mode=='qword-return':
                    proof=vectors.base_vector2_setter_program(body['regions'],body['pointer'],holder=holder[2],field=offset)
                elif member.declared_type=='UnityEngine.Vector3'and mode=='value-pointer-12':
                    proof=vectors.base_vector_setter_program(body['regions'],body['pointer'],holder=holder[2],field=offset,width=12)
                elif member.declared_type=='UnityEngine.Quaternion'and mode=='value-pointer-16':
                    proof=vectors.base_vector_setter_program(body['regions'],body['pointer'],holder=holder[2],field=offset,width=16)
                elif member.declared_type=='UnityEngine.Color'and mode=='value-pointer-16':
                    proof=vectors.base_vector_setter_program(body['regions'],body['pointer'],holder=holder[2],field=offset,width=16)
                elif member.declared_type=='Beyond.AABB'and mode=='value-pointer-16':
                    proof=vectors.base_vector_setter_program(body['regions'],body['pointer'],holder=holder[2],field=offset,width=16)
                else:raise
            profile='direct-base-holder-setter';getter_proof=None
        except(ValueError,KeyError,IndexError)as error:errors.append(str(error)[:1000])
    need('complete-owned-setter-profile',proof is not None,dict(wrapperName=wrapper.name,fieldName=member.name,
        declaringWrapper=member.declaring_wrapper,methodIndex=method.index,targetRva=body['pointer']-image.pe.image_base,
        fieldOffset=offset,mode=mode,attempts=errors))
    result=dict(method=[method.index,wrapper.name,md.string(method.name_index),body['pointer']-image.pe.image_base],
        member=member.row(),targetField=target,fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=stored_bytes,
        sourceFamily=body['family'],codeWindows=body['windows'],profile=profile,program=proof,getter=getter_proof,
        incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False,
        evidenceBoundary='Current named metadata-owned field and ordinary setter ABI; complete selected store/return with compatible nonnull holder or independently checked coherent getter. Child framing, construction, noncoherent refresh and runtime invocation are not admitted.')
    if inline_refresh is not None:result['inlineCompatibleRefresh']=inline_refresh
    if inline_collector is not None:result['inlineDisabledCollectorSource']=inline_collector
    if member.declared_type in('UnityEngine.Color','UnityEngine.Vector2Int','Beyond.Gameplay.AI.EnemyCheckAIMarker+EnemyCheckAIMarkerInfo','Beyond.Gameplay.Core.CharInteractPerform.HandIKParams','Beyond.AABB'):result['nominalValueLayout']=layout
    if member.declared_type=='UnityEngine.Vector2Int':
        result['ordinarySourceRows']=body['rows']
        result['ordinarySourceRegions']=[[at,raw.hex().upper()]for at,raw in body['regions']]
    if member.declared_type=='Beyond.AABB':
        result['ordinarySourceRows']=body['rows']
        result['ordinarySourceRegions']=[[at-image.pe.image_base,raw.hex().upper()]for at,raw in body['regions']]
    return result


def derive_many(image,pins,wrapper_names):
    """Fresh selected-image setter components, retaining every exact refusal."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.generated_action_sources import _prepare
    need('bounded-distinct-owners',0<len(wrapper_names)<=512 and len(set(wrapper_names))==len(wrapper_names))
    _publication_gate(image,pins);_,barrier,_=_prepare(image,pins)
    inventory=list(image.memorypack_wrappers.values());wrappers={w.name:w for w in inventory};cache={};members={};owners=[]
    need('unique-current-wrapper-inventory',len(wrappers)==len(inventory))
    for name in wrapper_names:
        wrapper=wrappers[name];indices=[]
        for member in wrapper.members:
            index=member.method_index;indices.append(index)
            if index in members:continue
            try:members[index]=dict(status='setter-source-proved',proof=_derive_setter(image,member,wrappers,barrier,cache,pins=pins))
            except(ValueError,KeyError,IndexError,TypeError)as error:
                members[index]=dict(status='pendingReview',member=member.row(),reason=str(error)[:2400])
        owners.append(dict(wrapperName=name,memberMethods=indices,allSetterComponentsProved=all(members[i]['status']=='setter-source-proved'for i in indices),
            wholeWrapperAdmitted=False,childGrammarAdmitted=False))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(nativeInputs=pins,owners=owners,members=members,wholeCatalogAdmitted=False)))
