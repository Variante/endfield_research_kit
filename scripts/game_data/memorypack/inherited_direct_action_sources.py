"""Four common action operands stored through the declared base-Data reference.

This explicit profile coexists with the separate inherited-setter profile.
It checks reader/wrapper aliases, primitive helpers, null guards and complete
source-to-field bridges; it does not prove creation, error/refill outcomes or
actual action execution.
"""
from __future__ import annotations
from typing import Any,Callable
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, validate_reference_ancestor_chain
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import setter_output_sources as primitives
from scripts.game_data.memorypack import struct_output_sources as structs


def validate_inherited_direct_sources(image: Any,source: dict,record: dict,*,fail: Callable) -> dict:
    proof=record.get('inheritedDirectActionSource') or {}
    order=[('isEnable','byte'),('priorityLevel','scalar32'),('priorityOffset','scalar32'),('serverActionIndex','scalar32')]
    members=record['members'][:4]
    mode=proof.get('mode')
    if (mode not in ('reader-rbx-wrapper-ref-rdi-four-common-direct-stores',
                    'reader-rbx-wrapper-ref-rdi-four-common-direct-stores-through-data-ancestors')
            or (mode=='reader-rbx-wrapper-ref-rdi-four-common-direct-stores' and record.get('inheritedMemberCount')!=4)
            or (mode=='reader-rbx-wrapper-ref-rdi-four-common-direct-stores-through-data-ancestors'
                and (type(record.get('inheritedMemberCount')) is not int or record['inheritedMemberCount']<4
                     or proof.get('commonMemberCount')!=4))
            or len(record['members'])<4
            or [(m['fieldName'],m['kind']) for m in members]!=order):
        fail('inherited-direct-scope','four ordered common direct-store operands',proof)
    selected=NativeReferenceContext(image)
    wrapper=proof['baseWrapperName'];data=proof['baseDataName']
    if mode=='reader-rbx-wrapper-ref-rdi-four-common-direct-stores-through-data-ancestors':
        try:
            validate_reference_ancestor_chain(selected,record['runtimeTypeName'],proof.get('runtimeParentChain'),data)
            validate_reference_ancestor_chain(selected,record['wrapperTypeName'],proof.get('wrapperParentChain'),wrapper)
        except ValueError as error:
            fail('inherited-direct-data-ancestors',proof.get('runtimeParentChain'),str(error))
    elif selected.parent(record['runtimeTypeName'])!=data:
        fail('inherited-direct-base-types',[wrapper,data],[selected.parent(record['wrapperTypeName']),selected.parent(record['runtimeTypeName'])])
    if ((mode=='reader-rbx-wrapper-ref-rdi-four-common-direct-stores' and selected.parent(record['wrapperTypeName'])!=wrapper)
            or selected.is_value_type(wrapper) or selected.is_value_type(data)):
        fail('inherited-direct-base-types',[wrapper,data],[selected.parent(record['wrapperTypeName']),selected.parent(record['runtimeTypeName'])])
    owner,declared,instance=selected.field(wrapper+'::'+proof['baseInstanceField'])
    if owner!=wrapper or declared!=data or not 0<=instance<128:
        fail('inherited-direct-instance-field',[wrapper,data,'disp8 reference'],[owner,declared,instance])
    normal=next(w for w in source['codeWindows'] if w['startRva']==record['readerMethod'][3])
    structs.check_reader_ref_wrapper_abi(image,record,fail=fail)
    program=proof.get('commonPrefixProgram')
    if not isinstance(program,list) or not program or program[0][0]!=normal['startRva']:
        fail('inherited-direct-parent-program','complete normal prefix through four common stores',program)
    structs._check_pointer_aliases(image,normal,program,label='inheritedDirectActionSource',fail=fail)
    last=members[-1]['assignment']
    end=last['rva']+len(bytes.fromhex(last['rawHex']))
    if program[-1][0]+len(bytes.fromhex(program[-1][1]))!=end:
        fail('inherited-direct-parent-extent','entry through the fourth actual common store',program[-1])
    previous=normal['startRva']
    for ordinal,member in enumerate(members):
        field=member['fieldName'];transfer=member.get('inheritedDirectStore') or {}
        field_owner,field_type,offset=selected.field(data+'::'+field)
        if (field_owner!=data or field_type!=member['declaredType'] or not 0<=offset<128
                or ordinal==0 and field_type!='bool'
                or ordinal!=0 and field_type!='int' and not selected.is_enum(field_type)):
            fail('inherited-direct-data-field',[data,member['declaredType'],'primitive disp8'],[field_owner,field_type,offset])
        assignment=member['assignment']
        raw_store=bytes((0x88 if ordinal==0 else 0x89,0x41,offset))
        if (assignment.get('kind')!='direct-store' or assignment.get('baseRegister')!=1
                or assignment.get('fieldOffset')!=offset or assignment.get('fieldOwnerTypeDefinition')!=selected.index.types[data].index
                or assignment.get('rawHex')!=raw_store.hex().upper()):
            fail('inherited-direct-destination',[data,field,raw_store.hex().upper()],assignment)
        if (member.get('primitiveSource') or {}).get('mode')!=('normalized-byte-return' if ordinal==0 else 'scalar32-return'):
            fail('inherited-direct-primitive-mode','Boolean normalization or raw DWORD return',member.get('primitiveSource'))
        primitives.validate_primitive_source(image,source,member,fail=fail)
        context=next((c for c in source['nestedContexts'] if c['instructionRva']==member.get('sourceContextInstructionRva')),None)
        args=transfer.get('argumentProgram')
        mode=transfer.get('argumentMode')
        if mode=='wrapper-reader' and context is None:
            expected=[b'\x48\x8b\x37',b'\x48\x8b\xcb']
        elif mode=='reader-wrapper' and context is None:
            expected=[b'\x48\x8b\xcb',b'\x48\x8b\x37']
        elif mode=='reader-context-wrapper' and context is not None:
            named.check_typed_context(image,context,member['declaredType'],label='inheritedDirectActionSource',fail=fail)
            expected=[b'\x48\x8b\xcb',bytes.fromhex(context['instructionHex']),b'\x48\x8b\x37']
            if not isinstance(args,list) or len(args)!=3 or args[1][0]!=context['instructionRva']:
                fail('inherited-direct-context-position','exact source context between reader and wrapper arguments',args)
        else:
            fail('inherited-direct-argument-mode','explicit reader/wrapper and optional context order',mode)
        structs._program(image,normal,args,expected,label='inheritedDirectActionSource',fail=fail)
        call=member['sourceCall'];bridge=transfer.get('bridgeProgram')
        if (args[0][0]<previous or args[-1][0]+len(expected[-1])!=call['rva']
                or not isinstance(bridge,list) or len(bridge)!=6):
            fail('inherited-direct-source-order','arguments immediately before actual source; complete six-instruction bridge',transfer)
        named.check_call(image,call,label='inheritedDirectActionSource',fail=fail)
        branches=[]
        for index in (1,4):
            raw=bytes.fromhex(bridge[index][1])
            if len(raw)!=6 or raw[:2]!=b'\x0f\x84':
                fail('inherited-direct-null-branch','complete JE rel32 null guard',bridge[index])
            target=bridge[index][0]+6+int.from_bytes(raw[2:],'little',signed=True)
            if normal['startRva']<=target<normal['endRva']:
                fail('inherited-direct-null-target','unproved failure path outside the normal window',target)
            branches.append(raw)
        structs._program(image,normal,bridge,[b'\x48\x85\xf6',branches[0],b'\x48\x8b\x4e'+bytes((instance,)),
            b'\x48\x85\xc9',branches[1],raw_store],label='inheritedDirectActionSource',fail=fail)
        if (bridge[0][0]!=call['rva']+5 or bridge[-1][0]!=assignment['rva']
                or member['sourceToDestinationHex']!=''.join(row[1] for row in bridge[:-1])):
            fail('inherited-direct-source-to-store','uninterrupted actual primitive result -> base-Data store',bridge)
        previous=assignment['rva']+len(raw_store)
    return {'commonOperandsProved':4,'bufferedPayloadBytes':13,'aliasesProvedThroughFourthCommonStore':True,
        'evidenceBoundary':'conditional','condition':'buffered normal sources, coherent declared references and ordinary Win64 returns',
        'wholeActionAdmitted':False,'runtimeExecutionKnown':False,'failureOrRefillParityKnown':False}
