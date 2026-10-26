"""Check every instruction on one explicitly conditional native path."""
from scripts.game_data.il2cpp.initializer_control import control_transfer

class _Path:
    def __init__(self,rows):self.rows={int(r['va'],16):r for r in rows};self.at=min(self.rows);self.seen=[]
    def row(self):
        if self.at not in self.rows or self.at in self.seen:raise ValueError('selectedPath.boundary-or-loop')
        result=self.rows[self.at];self.seen.append(self.at);self.at+=len(bytes.fromhex(result['bytes']));return result
    def take(self,*texts):
        for text in texts:
            actual=self.row()
            if actual['text']!=text:raise ValueError('selectedPath.instruction:'+str((text,actual))[:600])
    def branch(self,code,taken):
        row=self.row();flow=control_transfer(row)
        if flow['kind']!='conditional' or flow['conditionCode']!=code or flow['target'] not in self.rows:raise ValueError('selectedPath.predicate-or-target')
        if taken:self.at=flow['target']
    def jump(self):
        row=self.row();flow=control_transfer(row)
        if flow['kind']!='jump' or flow['target'] not in self.rows:raise ValueError('selectedPath.jump-target')
        self.at=flow['target']
    def call(self,target):
        row=self.row();flow=control_transfer(row)
        if flow['kind']!='call' or flow['target']!=target:raise ValueError('selectedPath.call-target')


"""Selected initialized pooled branch, separate from the pool-absent UTF8 fallback."""

def rip(g,register,expected):
    row=g.row();raw=bytes.fromhex(row['bytes']);prefix={'rax':b'\x48\x8b\x05','rdi':b'\x48\x8b\x3d','rbx':b'\x48\x8b\x1d'}[register]
    if len(raw)!=7 or raw[:3]!=prefix or int(row['va'],16)+7+int.from_bytes(raw[3:],'little',signed=True)!=expected:raise ValueError('inlinePooled.global-cell:'+register)

def check(rows,entry,*,wrapper,pool,empty,lookup,mode):
    if mode not in ('null','empty','lookup'):raise ValueError('inlinePooled.mode')
    g=_Path(rows);g.at=entry
    if wrapper not in ('rsi','r14'):raise ValueError('inlinePooled.wrapper-role')
    output,pool_register,output32=('rdi','rbp','edi') if wrapper=='r14' else ('rbx','rbx','ebx')
    rip(g,'rax',pool);g.take('mov rcx, [rax+0xb8]','cmp qword [rcx], 0x0');g.branch(4,False)
    g.take('cmp dword [rbx+0x30], 0x4');g.branch(13,True)
    g.take('mov rax, [rbx+0x50]','mov edi, [rax]','mov ebp, [rbx+0x30]','add ebp, -0x4');g.branch(9,True)
    g.take('add qword [rbx+0x50], 0x4','add dword [rbx+0x40], 0x4','add dword [rbx+0x44], 0x4','mov [rbx+0x30], ebp','cmp edi, -0x2');g.branch(4,mode=='null')
    if mode=='null':g.take(f'xor {output32}, {output32}');g.jump()
    else:
        g.take('cmp edi, -0x1');g.branch(4,mode=='empty')
        if mode=='empty':rip(g,output,empty);g.jump()
        else:
            rip(g,'rax',pool);g.take('mov rcx, [rax+0xb8]',f'mov {pool_register}, [rcx]',f'test {pool_register}, {pool_register}');g.branch(4,False)
            g.take('xor r8d, r8d','mov edx, edi',f'mov rcx, {pool_register}');g.call(lookup);g.jump();g.take(f'mov {output}, rax')
    join=g.at;g.take(f'test {wrapper}, {wrapper}')
    return dict(mode=mode,consumedBytes=4,index='signed Int32 EDI',outputRegister=output,wrapperRegister=wrapper,readerRegisterReusedOnlyAfterAllInputReads=output=='rbx',sourceJoin=join,selectedInstructionAddresses=g.seen,condition='Selected initialized pooled-field branch with matching nonnull coherent pool, at least four contiguous bytes, valid disjoint reader/storage/counters, index -2/-1 or nonnegative respectively and normal ABI-preserving pool lookup. Initialization/hoisted prior-field stores, pool-absent inline UTF8 fallback, cold/refill, typed destination and owning record remain separate.')

"""Authenticate reviewed conditional inline pooled-string sources and typed stores."""
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.string_source_instructions import decode_string_source_instructions
from scripts.game_data.memorypack.struct_output_sources import check_reader_ref_wrapper_abi

def _cell(row,prefix):
    raw=bytes.fromhex(row['bytes'])
    if len(raw)!=7 or raw[:3]!=prefix:raise ValueError('inlinePooled.global-load')
    return int(row['va'],16)+7+int.from_bytes(raw[3:],'little',signed=True)

def _symbols(image,fact):
    base=image.pe.image_base;rows=[]
    for part in image.unwind_index.family(fact['targetRva'])['ranges']:
        a,b=part['runtimeTriple'][:2];rows.extend(decode_string_source_instructions(image.mapper,image.pe.bytes_at_va(base+a,b-a),base+a))
    pool,={_cell(r,b'\x48\x8b\x05') for i,r in enumerate(rows[:-1]) if r['text'].startswith('mov rax, [rip') and rows[i+1]['text']=='mov rcx, [rax+0xb8]'}
    sentinel,=[i for i,r in enumerate(rows) if r['text']=='cmp edi, -0x1'];target=control_transfer(rows[sentinel+1])['target'];empty,=[r for r in rows if int(r['va'],16)==target]
    result=dict(pool=pool,empty=_cell(empty,b'\x48\x8b\x05'),lookup=base+fact['lookupRva'])
    if {k:result[k]-base for k in ('pool','empty')}!=fact['inlineSymbols']:raise ValueError('inlinePooled.reviewed-symbols')
    return result

def _store(image,c,rows,join):
    ctx=NativeReferenceContext(image);holder=ctx.field(c['wrapperName']+'::__instance');target=ctx.field(c['wrappedType']+'::'+c['fieldName'])
    if holder[:2]!=(c['wrapperName'],c['wrappedType']) or target[:2]!=(c['wrappedType'],'string'):raise ValueError('inlinePooled.typed-field')
    value=ctx.is_value_type(c['wrappedType']);wrapper='rsi' if value else 'r14'
    if c['wrapperRegister']!=wrapper:raise ValueError('inlinePooled.typed-register-profile')
    g=_Path(rows);g.at=join;g.take(f'test {wrapper}, {wrapper}')
    def nonnull():
        row=g.row();flow=control_transfer(row)
        if flow['kind']!='conditional' or flow['conditionCode']!=4:raise ValueError('inlinePooled.null-guard')
        trap=next(i for i,r in enumerate(rows) if int(r['va'],16)==flow['target'])
        if control_transfer(rows[trap])['kind']!='call' or rows[trap+1]['text']!='int3':raise ValueError('inlinePooled.null-exit')
    nonnull()
    if not value:
        g.take(f'mov r8, [r14+{holder[2]:#x}]','test r8, r8');nonnull()
    flag=g.row();raw=bytes.fromhex(flag['bytes'])
    if len(raw)!=7 or raw[:2]!=b'\x83\x3d' or raw[-1]!=0:raise ValueError('inlinePooled.barrier-flag')
    if value:offset=holder[2]+target[2]-16;g.take(f'mov [rsi+{offset:#x}], rbx')
    else:
        address=g.row();raw=bytes.fromhex(address['bytes'])
        if len(raw)!=7 or raw[:3]!=b'\x48\x8d\x2d':raise ValueError('inlinePooled.bitmap-address')
        offset=target[2];g.take(f'mov [r8+{offset:#x}], rdi')
    return dict(field=c['fieldName'],declaredType='string',storedOffset=offset,sourceJoinRva=join-image.pe.image_base,wholeOwnerAdmitted=False)

def validate(image,fact,wrapper,field):
    matches=[c for c in fact['inlineSources'] if (c['wrapperName'],c['fieldName'])==(wrapper,field)]
    if len(matches)!=1:raise ValueError(f'inlinePooled.source:unproved-field={wrapper}::{field},matches={len(matches)}')
    c=matches[0];base=image.pe.image_base;ctx=NativeReferenceContext(image);definition=ctx.index.types[wrapper]
    image.validate_method_row(c['readerMethod'])
    if c['readerMethod'][1:3]!=[wrapper,'Deserialize']:raise ValueError('inlinePooled.reader-identity')
    def fail(*args):raise ValueError('inlinePooled.reader-abi:'+str(args)[:700])
    check_reader_ref_wrapper_abi(image,dict(readerMethod=c['readerMethod'],wrapperTypeDefinition=definition.index),fail=fail)
    windows=c['codeWindows'];actual=sorted(tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(c['readerMethod'][3])['ranges'])
    if actual!=sorted((w['startRva'],w['endRva']) for w in windows):raise ValueError('inlinePooled.complete-reader-windows')
    image.check_windows(windows);rows=[]
    for w in windows:rows.extend(decode_string_source_instructions(image.mapper,image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']),base+w['startRva']))
    symbols=_symbols(image,fact);proofs=[check(rows,base+c['entryRva'],wrapper=c['wrapperRegister'],mode=mode,**symbols) for mode in ('null','empty','lookup')]
    join,={p['sourceJoin'] for p in proofs};stored=_store(image,c,rows,join)
    return dict(status='validated',wireEncoding='int32-pool-index',emptyIndex=-1,nullIndex=-2,wrapperName=wrapper,fieldName=field,sourceSiteRva=c['entryRva'],proofs=proofs,storedField=stored,wholeOwnerAdmitted=False,evidenceBoundary=c['evidenceBoundary'])
