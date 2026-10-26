"""Complete buffered primitive programs used by current generated members."""
from __future__ import annotations
from scripts.game_data.memorypack import buff_ec_profiles_native as ec,scalar_param_native as scalar
from scripts.game_data.memorypack.pooled_inline_sources import _Path
from scripts.game_data.memorypack.vector_layout import vector_recorder

LABEL='generatedPrimitiveSource'
KINDS={'bool':(1,'al-normalized'),'raw-byte':(1,'al'),'int32':(4,'eax'),
    'int64':(8,'rax'),'float32':(4,'xmm0-low32'),'float64':(8,'xmm0-low64')}


def floating_program(rows,entry,offsets,width):
    if type(width)is not int or width not in(4,8):raise ValueError(LABEL+'.float-width')
    g=_Path(rows);g.at=entry
    b,r,c,s=(offsets[n]for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('mov [rsp+0x8], rbx','push rdi','sub rsp, 0x30',
        f'cmp dword [rcx+{r:#x}], {width:#x}','mov rbx, rcx','movaps [rsp+0x20], xmm6')
    g.branch(12,False)
    g.take(f'mov rax, [rbx+{b:#x}]',('movss'if width==4 else'movsd')+' xmm6, [rax]',
        f'mov edi, [rbx+{r:#x}]',f'add edi, -{width:#x}')
    g.branch(8,False)
    g.take(f'add qword [rbx+{b:#x}], {width:#x}',f'add dword [rbx+{c:#x}], {width:#x}',
        f'add dword [rbx+{s:#x}], {width:#x}',f'mov [rbx+{r:#x}], edi','mov rbx, [rsp+0x40]',
        'movaps xmm0, xmm6','movaps xmm6, [rsp+0x20]','add rsp, 0x30','pop rdi','ret')
    return g.seen


def derive(image,target,kind,offsets):
    if kind not in KINDS:raise ValueError(LABEL+'.unsupported-kind:'+str(kind))
    base=image.pe.image_base;family,windows,rows=ec.family(image,target-base);width,result=KINDS[kind]
    if kind in('float32','float64'):
        program=floating_program(rows,target,offsets,width);by={ec.va(r):r for r in rows}
        selected=[ec.site(by[at],base)for at in program]
    else:
        record=vector_recorder(image)(target-base)
        if kind=='bool':scalar.boolean_source(image,record,offsets,LABEL+'.bool')
        elif kind=='raw-byte':scalar.raw_byte_source(image,record,offsets)
        else:scalar.integer_source(image,record,offsets,LABEL+'.'+kind,width=width)
        selected=record['instructions']
    return dict(kind=kind,targetRva=target-base,family=family,codeWindows=windows,selectedProgram=selected,
        wireBytes=width,resultRegister=result,boolNormalized=kind=='bool',
        completeBufferedProgram=True,entryRspRestored=True,nonvolatilesRestored=True,
        conditional='Buffered input with at least the required contiguous bytes and nonwrapping disjoint Reader/source/output/frame. Cold/refill and live invocation remain unobserved.')
