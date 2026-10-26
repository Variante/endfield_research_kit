"""Authenticate generated reference-Param null branches, excluding positive values."""
import hashlib
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.memorypack import primitive_param as primitive,scalar_param_native as scalar
from scripts.game_data.memorypack.pooled_inline_sources import _Path


def exact(g,text,encoded):
    row=g.row();scalar.need('nullableClassParam',text,(text,bytes.fromhex(encoded)),(row['text'],bytes.fromhex(row['bytes'])));return row


def path(rows,pointer,offsets):
    label='nullableClassParam';g=_Path(rows);g.at=pointer;called=g.rows[pointer]['text']=='mov [rsp+0x10], rbx'
    if called:g.take('mov [rsp+0x10], rbx','mov [rsp+0x18], rsi','push rdi','sub rsp, 0x20')
    else:g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rbp','mov [rsp+0x18], rsi','push rdi','sub rsp, 0x50')
    flag=g.row();raw=bytes.fromhex(flag['bytes']);scalar.need(label,'byte-initialization-flag',(7,b'\x80\x3d',0),(len(raw),raw[:2],raw[-1]));header=None
    if called:
        g.take('mov rbx, rdx','mov rsi, rcx');g.branch(5,True);g.take('lea rdx, [rsp+0x30]');exact(g,'mov [rsp+0x30], 0x0','c644243000');g.take('mov rcx, rsi')
        header=g.row();scalar.need(label,'header-call','call',control_transfer(header)['kind']);g.take('test al, al');g.branch(4,True)
        g.take('mov rcx, rbx');clear=exact(g,'mov [rbx], 0x0','48c70300000000');barrier=g.row();scalar.need(label,'ordinary-barrier-call','call',control_transfer(barrier)['kind'])
        g.take('mov rbx, [rsp+0x38]','mov rsi, [rsp+0x40]','add rsp, 0x20','pop rdi','ret')
    else:
        g.take('mov rdi, rdx','mov rbx, rcx');g.branch(4,False);cur,rem,adv,used=(offsets[n] for n in ('currentPtr','bufferLength','advancedCount','consumed'))
        exact(g,f'cmp [rbx+{rem:#x}], 0x1','837b'+bytes((rem,1)).hex());g.branch(12,False)
        g.take(f'mov rax, [rbx+{cur:#x}]');exact(g,'movzx esi, [rax]','0fb630');g.take(f'mov ebp, [rbx+{rem:#x}]','sub ebp, 0x1');g.branch(8,False)
        for offset,prefix in ((cur,'48ff43'),(adv,'ff43'),(used,'ff43')):exact(g,f'inc [rbx+{offset:#x}]',prefix+bytes((offset,)).hex())
        g.take(f'mov [rbx+{rem:#x}], ebp');exact(g,'cmp sil, -0x1','4080feff');g.branch(4,True)
        clear=exact(g,'mov [rdi], 0x0','48c70700000000');g.take('mov rcx, rdi');g.jump()
        g.take('mov rbx, [rsp+0x60]','mov rbp, [rsp+0x68]','mov rsi, [rsp+0x70]','add rsp, 0x50','pop rdi');barrier=g.row();scalar.need(label,'ordinary-barrier-tail','jump',control_transfer(barrier)['kind'])
    return dict(profile='called-header' if called else 'inline-header',selectedInstructions=g.seen,headerCall=header,nullStore=clear,barrier=barrier)


def derive(image,inputs,value_type):
    label='nullableClassParam';base=image.pe.image_base;build=Build(image,inputs);ctx=NativeReferenceContext(image);wrapped='Beyond.Gameplay.Actions.Param`1<'+value_type+'>'
    wrappers=[w for w in build.wrappers.values() if w.wrapped_type==wrapped];scalar.need(label,'one-wrapper',1,len(wrappers));wrapper=wrappers[0]
    scalar.need(label,'typed-members',[('constValue',value_type),('idRef','int'),('paramSource','int'),('path','string')],[(m.name,m.declared_type) for m in wrapper.members])
    scalar.need(label,'owned-reference-holder',(wrapper.name,wrapped,16),ctx.field(wrapper.name+'::__instance'));scalar.need(label,'generic-Param-is-reference',False,ctx.is_value_type('Beyond.Gameplay.Actions.Param`1'))
    md=image.metadata;methods={md.string(m.name_index):m for m in md.methods_for(md.types[wrapper.type_definition])};method=methods['Deserialize'];pointer=image.method_pointer_va(method)
    primitive.reader_abi(image,ctx,method,wrapper);parts=sorted(tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(pointer-base)['ranges']);rows=[];windows=[];scalar.need(label,'owned-entry',pointer-base,parts[0][0])
    for a,b in parts:
        raw=image.pe.bytes_at_va(base+a,b-a);rows.extend(build.body._decode(base+a,b-a));windows.append(dict(startRva=a,endRva=b,sha256=hashlib.sha256(raw).hexdigest().upper()))
    offsets=scalar.reader_offsets(image,label);program=path(rows,pointer,offsets);source=None
    if program['headerCall'] is not None:
        target=control_transfer(program['headerCall'])['target'];end=build.body.extents[target];raw=image.pe.bytes_at_va(target,end-target);decoded=build.body._decode(target,end-target)
        source=dict(window=dict(startRva=target-base,endRva=end-base,sha256=hashlib.sha256(raw).hexdigest().upper()),instructions=[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in decoded]);primitive.object_header_source(image,source,offsets)
    getter=methods['GetValue'];scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(wrapped,21,True),[],label+'.getter')
    at=image.method_pointer_va(getter);raw=image.pe.bytes_at_va(at,5);decoded=build.body._decode(at,5);scalar.program(image,[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in decoded],[b'\x48\x8b\x41\x10',b'\xc3'],label+'.getter')
    return dict(schema='endfield.memorypack-null-class-param-proof.v1',wrappedType=wrapped,wrapperName=wrapper.name,nullableMarker=255,positiveAdmitted=False,wireBytes=1,
        callerMethod=[method.index,wrapper.name,'Deserialize',pointer-base],ownedWindows=windows,program=program,headerSource=source,readerOffsets=offsets,
        getter=dict(methodIndex=getter.index,pointerRva=at-base,bytes=raw.hex().upper(),returnedReferenceBits=64),
        evidenceBoundary=dict(direct='Typed reference Param/wrapper, initialized caller aliases, one-byte header, FF output clear and complete ordinary return/tail; the nonnull getter has the declared reference return.',
            conditional='Initialized metadata; valid disjoint buffer, reader, byref output, frame and saved-register slots; one contiguous byte, nonoverflowing counters, ordinary ABI-preserving header/barrier and compatible normal reference formatter/wrapper route.',
            unresolved=['every positive Param or nested value representation','cold metadata initialization/refill and live formatter/cache selection','owning action execution']))
