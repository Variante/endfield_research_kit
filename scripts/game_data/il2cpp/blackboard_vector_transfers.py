"""Compose exact pair-copy lane instructions used by Blackboard list assignment.

Instruction decoding alone does not prove list traversal or vector preservation
across a helper call. Reuse the maintained MOVQ and PSRLDQ operand readers.
"""
from __future__ import annotations
from .method_carrier_instructions import decode_carrier_vector_transfer,decode_carrier_vector_byte_shift
from .stack_argument_flow import decode_stack_flow
from .reference_layouts import NativeReferenceContext


def decode_high_double_unpack(data,offset,start_va):
    if not 0<=offset<len(data) or data[offset]!=0x66:return None
    at=offset+1;rex=0
    if at<len(data) and 0x40<=data[at]<=0x4f:rex=data[at];at+=1
    if data[at:at+2]!=b'\x0f\x15':return None
    at+=2
    if at>=len(data):raise ValueError('blackboard-vector: truncated UNPCKHPD ModRM')
    modrm=data[at];at+=1
    if modrm>>6!=3:return None
    destination=f'xmm{((modrm>>3)&7)|((rex&4)<<1)}';source=f'xmm{(modrm&7)|((rex&1)<<3)}'
    return {'offset':offset,'va':hex(start_va+offset),'bytes':data[offset:at].hex(' '),
        'text':f'unpckhpd {destination}, {source}',
        'write':{'register':destination,'value':f'low64=previous({destination}).high64; high64=previous({source}).high64'},
        'highDoubleUnpack':{'source':source,'destination':destination,'destinationLow64Source':'previous destination high64',
            'destinationHigh64Source':'previous source high64','preservesBitsAbove127':True,
            'writesMemory':False,'writesFlags':False}},at


def decode_blackboard_vectors(mapper,raw,start):
    class Adapter:
        def decode_one_x64(self,data,offset,at):
            for decoder in (decode_carrier_vector_transfer,decode_carrier_vector_byte_shift,decode_high_double_unpack):
                result=decoder(data,offset,at)
                if result is not None:return result
            return mapper.decode_one_x64(data,offset,at)
    return decode_stack_flow(Adapter(),raw,start)


def prove_dynamic_pair_field_copy(index,body):
    from .program_grammar import ProgramGrammar
    from .body_claims import _named_direct_call
    from .vector_preservation import prove_vector_neutral_entry
    label='blackboard-dynamic-field-copy'
    if body.symbol!='Beyond.Blackboard.AssignDynamic' or not index.matches_parameters(body.pointer,
            ['System.Collections.Generic.List`1<Beyond.Blackboard+DataPair>']):raise ValueError(label+'.typed-list-body')
    context=NativeReferenceContext(index.image,index=index);pair='Beyond.Blackboard+DataPair'
    if not context.is_value_type(pair) or [context.field(pair+'::'+f)[1:] for f in ('key','valueDouble','valueStr','isDynamic')]!=[
            ('string',16),('double',24),('string',32),('bool',40)]:raise ValueError(label+'.pair-fields')
    rows=decode_blackboard_vectors(index.mapper,index.pe.bytes_at_va(body.pointer,body.size),body.pointer)
    candidates=[n for n,r in enumerate(rows) if r['text']=='movups xmm2, [rax+rcx*1]']
    failures=[]
    for n in candidates:
        try:
            g=ProgramGrammar(rows[n:],label=label)
            g.take('movups xmm2, [rax+rcx*1]','movups xmm3, [rax+0x10+rcx*1]',
                   'lea rcx, [rsp+0x20]','movq [rsp+0x20], xmm2')
            call=g.row();b=bytes.fromhex(call['bytes'])
            if len(b)!=5 or b[0]!=0xe8:g.fail('first-helper','complete direct call',call)
            helper=int(call['va'],16)+5+int.from_bytes(b[1:],'little',signed=True)
            proof=prove_vector_neutral_entry(index.mapper,index.pe.bytes_at_va(helper,256),helper)
            g.take('unpckhpd xmm2, xmm2','lea rcx, [rsp+0x30]',
                   'movsd [rsp+0x28], xmm2','movq [rsp+0x30], xmm3')
            g.call(helper)
            g.take('movups xmm0, [rsp+0x20]','lea rdx, [rsp+0x40]','xor r8d, r8d',
                   'psrldq xmm3, 0x8','mov rcx, rbp','movd eax, xmm3',
                   'movaps [rsp+0x40], xmm0','mov [rsp+0x38], al',
                   'movups xmm1, [rsp+0x30]','movaps [rsp+0x50], xmm1')
            sink=g.row()
            if _named_direct_call(index,sink,'Beyond.Blackboard._AssignDynamicInternal') is None:
                g.fail('sink','named dynamic entry',sink)
            g.finish(prefix=True)
            return {'evidenceBoundary':'conditional','copiedFields':['key','valueDouble','valueStr','isDynamic'],
                'fieldCopyStartOffset':rows[n]['offset'],'fieldCopyEndOffset':sink['offset']+len(bytes.fromhex(sink['bytes'])),
                'helperVectorPreservation':proof,'loopTraversalProved':False,
                'condition':'Selected correct source-record address, unchanged destination alias and caller stack buffers across the vector-neutral helpers. Count/index traversal, helper memory noninterference and whole method ownership remain separate.'}
        except ValueError as exc:failures.append(str(exc)[:640])
    raise ValueError(label+'.no-complete-field-copy-program: expected=selected pair loads/copies/named sink; actual='+str(failures[:2]))


def check_dynamic_pair_field_copy(index,body):
    try:prove_dynamic_pair_field_copy(index,body)
    except (ValueError,KeyError,IndexError) as exc:return str(exc)
    return None
