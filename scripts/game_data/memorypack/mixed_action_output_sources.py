"""RBX reader/RDI ref-wrapper outputs with direct primitives and typed setters.

Only the declared normal buffered/getter paths are proved. Reference source
returns carry no serialized size; independent child readers own their framing.
"""
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import setter_output_sources as outputs
from scripts.game_data.memorypack import reference_output_sources as references
from scripts.game_data.memorypack import struct_output_sources as structs

LABEL='mixedActionOutputSource'

def _program(image,window,rows,expected,fail):
    structs._program(image,window,rows,expected,label=LABEL,fail=fail)

def validate_mixed_action_outputs(image,source,record,*,fail):
    proof=record['mixedActionOutputSource']
    if proof.get('mode')!='reader-rbx-ref-wrapper-rdi':fail('mixed-output-mode','reader RBX, wrapper reference RDI',proof)
    normal=next(w for w in source['codeWindows'] if w['startRva']==record['readerMethod'][3])
    selected=NativeReferenceContext(image)
    parent=proof['parentProgram'];last=record['members'][-1]
    if (not parent or parent[0][0]!=normal['startRva'] or parent[-1][0]!=last['assignment']['rva']
        or len(bytes.fromhex(parent[-1][1]))!=5):fail('mixed-output-parent-extent','entry through final setter',parent)
    # The final dereference deliberately replaces only the wrapper-reference alias.
    final=last['sourceArgumentProgram'];dereferences=[r for r in final if r[1]=='488B3F']
    if len(dereferences)!=1:fail('mixed-output-final-reference','one final RDI dereference',final)
    prefix=[r for r in parent if r[0]<dereferences[0][0]]
    structs.check_reader_ref_wrapper_abi(image,record,fail=fail)
    structs._check_pointer_aliases(image,normal,prefix,label=LABEL,fail=fail)
    references._program(image,normal,parent,fail)
    for at,raw_hex in parent:
        if at<dereferences[0][0]:continue
        raw=bytes.fromhex(raw_hex);decoded=image.mapper.decode_x64_subset(raw,image.pe.image_base+at,stop_offset=len(raw))
        if len(decoded)!=1 or decoded[0]['text'].startswith('db'):fail('mixed-output-final-instruction','one decoded instruction',[at,raw_hex])
        dest=(decoded[0].get('write') or {}).get('register')
        if dest in ('rbx','ebx','bx','bl','bh','rdi','edi','di','dil') and [at,raw_hex]!=dereferences[0]:
            fail('mixed-output-final-alias-clobber','only final RDI dereference',[at,raw_hex,dest])
    outputs._getter(image,record,proof,source,selected,fail)
    getter=proof['getterMethod'];checked=[]
    for ordinal,member in enumerate(record['members'][4:],start=4):
        call=member['sourceCall'];assignment=member['assignment'];args=member['sourceArgumentProgram'];bridge=member['outputTransferProgram']
        context=next((c for c in source['nestedContexts'] if c['instructionRva']==member.get('sourceContextInstructionRva')),None)
        final_member=ordinal==len(record['members'])-1
        if context is not None:
            named.check_typed_context(image,context,member['declaredType'],label=LABEL,fail=fail)
            references._return_type(image,context,fail)
            expected_args=[b'\x48\x8b\xcb',bytes.fromhex(context['instructionHex']),b'\x48\x8b\x37']
        else:
            wrapper_arg=b'\x48\x8b\x3f' if final_member else b'\x48\x8b\x37'
            argument_mode=member.get('sourceArgumentMode')
            if argument_mode=='wrapper-reader':expected_args=[wrapper_arg,b'\x48\x8b\xcb']
            elif argument_mode=='reader-wrapper' and not final_member:expected_args=[b'\x48\x8b\xcb',wrapper_arg]
            else:fail('mixed-output-argument-mode','explicit reader/wrapper order',argument_mode)
            outputs.validate_primitive_source(image,source,member,fail=fail)
        _program(image,normal,args,expected_args,fail);named.check_call(image,call,label=LABEL,fail=fail)
        if args[-1][0]+len(expected_args[-1])!=call['rva'] or not bridge or bridge[0][0]!=call['rva']+5:
            fail('mixed-output-source-extent','arguments/source/transfer contiguous',member['fieldName'])
        mode=member['outputMode']
        if assignment['kind']=='setter':
            actual=[bytes.fromhex(r[1]) for r in bridge]
            if len(actual)!=5:fail('mixed-output-setter-bridge-count',5,bridge)
            move=b'\x48\x8b\xd0' if mode=='reference-return' else b'\x0f\x28\xc8' if mode=='single-return' else None
            if move is None:fail('mixed-output-setter-mode','reference or Single return',mode)
            expected=[b'\x48\x85\xff' if final_member else b'\x48\x85\xf6',
                outputs._branch(actual[1],condition=4,fail=fail),b'\x45\x33\xc0',move,
                b'\x48\x8b\xcf' if final_member else b'\x48\x8b\xce']
            _program(image,normal,bridge,expected,fail)
            if bridge[-1][0]+len(expected[-1])!=assignment['rva']:fail('mixed-output-setter-end','transfer immediately before setter',assignment)
            outputs._setter(image,record,member,source,getter,selected,fail)
        elif assignment['kind']=='direct-store':
            if mode not in ('normalized-byte-return','scalar32-return') or final_member or context is not None:
                fail('mixed-output-direct-mode','non-final primitive through cached getter',mode)
            owner,type_name,offset=selected.field(record['runtimeTypeName']+'::'+member['fieldName'])
            wanted_type='bool' if mode=='normalized-byte-return' else 'int'
            if owner!=record['runtimeTypeName'] or type_name!=wanted_type or member['declaredType']!=wanted_type or not 0<=offset<128:
                fail('mixed-output-direct-field',wanted_type,[owner,type_name,offset])
            actual=[bytes.fromhex(r[1]) for r in bridge]
            if len(actual)!=9:fail('mixed-output-direct-count',9,bridge)
            getter_call=member['getterCall'];named.check_call(image,getter_call,label=LABEL,fail=fail)
            if getter_call['targetRva']!=getter[3] or bridge[5][0]!=getter_call['rva']:
                fail('mixed-output-direct-getter','typed instance getter',getter_call)
            store=bytes((0x40,0x88,0x68,offset)) if mode=='normalized-byte-return' else bytes((0x89,0x68,offset))
            expected=[b'\x0f\xb6\xe8' if mode=='normalized-byte-return' else b'\x8b\xe8',b'\x48\x85\xf6',
                outputs._branch(actual[2],condition=4,fail=fail),b'\x33\xd2',b'\x48\x8b\xce',actual[5],
                b'\x48\x85\xc0',outputs._branch(actual[7],condition=4,fail=fail),store]
            _program(image,normal,bridge,expected,fail)
            if bridge[-1][0]!=assignment['rva'] or assignment['rawHex']!=store.hex().upper() or assignment['fieldOffset']!=offset:
                fail('mixed-output-direct-destination','actual owned primitive store',assignment)
        else:fail('mixed-output-assignment-kind','setter or direct-store',assignment)
        checked.append(member['fieldName'])
    return {'ownedFieldsForwarded':checked,'bufferedPrimitiveSourceWidthsProved':True,
        'referenceGrammarProved':False,'getterSlowPathsKnown':False,'runtimeExecutionKnown':False,
        'evidenceBoundary':'conditional','condition':'selected normal buffered/getter paths, coherent references and ordinary Win64 nonvolatile preservation'}
