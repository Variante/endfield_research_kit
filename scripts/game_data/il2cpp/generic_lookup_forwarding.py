"""Prove a registered generic lookup's argument flow and opaque tail returns.

The whole primary profile keeps initialization/context helpers opaque. Anonymous
offsets are observed from operands, not assigned MethodInfo member names. Named
callee signatures and the selected value-handle layout authenticate call ABI.
"""
from __future__ import annotations

import hashlib
import struct

from .instance_string_field_calls import _at,_raw,_require,_branch,_call,_owner,_type,_instance_field_type
from .ai_blackboard_selection import _method,_generic_arity
from .generic_entries import GenericEntries
from .reference_layouts import NativeReferenceContext

MODE='registered-generic-lookup-forwarding-with-opaque-reference-tail'


class _Program:
    def __init__(self,rows):
        self.rows=rows;self.cursor=0
        _require(bool(rows) and len({_at(r) for r in rows})==len(rows),'lookup-body','unique nonempty boundaries',len(rows))
        _require(all(_raw(r) and not r['text'].startswith('db ') for r in rows),'lookup-decode','complete supported instructions',None)
        for a,b in zip(rows,rows[1:]):
            _require(_at(a)+len(_raw(a))==_at(b),'lookup-contiguity',a,b)

    def peek(self):
        _require(self.cursor<len(self.rows),'lookup-truncated','next complete instruction',self.cursor)
        return self.rows[self.cursor]

    def next(self):
        row=self.peek();self.cursor+=1;return row

    def take(self,raw):
        row=self.next();_require(_raw(row)==raw,'lookup-instruction',raw.hex(),row);return row

    def end(self):
        _require(self.cursor==len(self.rows),'lookup-terminal','matched end of primary program',self.cursor)


def _frame(program,saves):
    slots=[]
    for prefix in saves:
        row=program.next();raw=_raw(row)
        _require(len(raw)==5 and raw[:4]==prefix and 8<=raw[4]<=32 and raw[4]%8==0,
                 'lookup-shadow-save','nonvolatile save in caller shadow space',row)
        slots.append(raw[4])
    _require(len(slots)==len(set(slots)),'lookup-save-overlap','distinct caller shadow slots',slots)
    program.take(b'\x57');row=program.next();raw=_raw(row)
    _require(len(raw)==4 and raw[:3]==b'\x48\x83\xec','lookup-frame','SUB RSP,imm8',row)
    frame=int.from_bytes(raw[3:],'little',signed=True)
    _require(32<=frame<128 and frame%16==0 and all(frame+8+s<128 for s in slots),
             'lookup-frame-size','aligned shadow space and bounded restore displacements',frame)
    return frame,slots


def _restore(program,frame,slots,prefixes):
    for slot,prefix in zip(slots,prefixes):program.take(prefix+bytes([frame+8+slot]))
    program.take(b'\x48\x83\xc4'+bytes([frame]));program.take(b'\x5f')


def _tail_jump(row):
    raw=_raw(row)
    _require(len(raw)==5 and raw[0]==0xe9,'lookup-tail-jump','E9 with complete signed rel32',row)
    return _at(row)+5+int.from_bytes(raw[1:],'little',signed=True)


def validate_forwarding(rows,*,type_from_handle_pointer,nongeneric_lookup_pointer):
    p=_Program(rows);frame,slots=_frame(p,(b'\x48\x89\x5c\x24',b'\x48\x89\x6c\x24',b'\x48\x89\x74\x24'))
    first=p.next();raw=_raw(first)
    _require(len(raw)==5 and raw[:3]==b'\x49\x83\x78' and raw[4]==0 and 0<raw[3]<128 and raw[3]%8==0,
             'lookup-context-test','CMP QWORD [incoming R8+positive aligned disp8],0',first)
    context_offset=raw[3]
    p.take(b'\x49\x8b\xf8');p.take(b'\x48\x8b\xf2');p.take(b'\x48\x8b\xe9')
    branch1=p.next();join=_branch(branch1,opcode=b'\x75')
    metadata_cell=p.next();raw=_raw(metadata_cell)
    _require(len(raw)==7 and raw[:3]==b'\x48\x8d\x0d','lookup-metadata-cell','LEA RCX,RIP-relative cell',metadata_cell)
    cell=_at(metadata_cell)+7+int.from_bytes(raw[3:],'little',signed=True)
    metadata_call=p.next();metadata_helper=_call(metadata_call)
    p.take(b'\x48\x83\x7f'+bytes([context_offset])+b'\x00')
    branch2=p.next();_branch(branch2,opcode=b'\x75',target=join)
    p.take(b'\x48\x8b\xcf');context_init=p.next();context_helper=_call(context_init)
    _require(_at(p.peek())==join,'lookup-context-join','both nonzero tests join exact context reload',hex(join))
    first_reload=p.take(b'\x48\x8b\x5f'+bytes([context_offset]))
    cell_load=p.next();raw=_raw(cell_load)
    _require(len(raw)==7 and raw[:3]==b'\x48\x8b\x0d'
             and _at(cell_load)+7+int.from_bytes(raw[3:],'little',signed=True)==cell,
             'lookup-shared-metadata-cell','MOV RCX from same exact RIP-relative cell',cell_load)
    handle_load=p.take(b'\x48\x8b\x1b');class_init=p.next();class_helper=_call(class_init)
    p.take(b'\x33\xd2');p.take(b'\x48\x8b\xcb');type_call=p.next()
    _require(_call(type_call)==type_from_handle_pointer,'lookup-type-call','selected named Type.GetTypeFromHandle',type_call)
    p.take(b'\x45\x33\xc9');p.take(b'\x4c\x8b\xc0');p.take(b'\x48\x8b\xd6');p.take(b'\x48\x8b\xcd')
    lookup_call=p.next()
    _require(_call(lookup_call)==nongeneric_lookup_pointer,'lookup-nongeneric-call','selected nongeneric overload',lookup_call)
    second_reload=p.take(b'\x48\x8b\x4f'+bytes([context_offset]));p.take(b'\x48\x8b\xd8')
    slot=p.next();raw=_raw(slot)
    _require(len(raw)==4 and raw[:3]==b'\x48\x8b\x49' and 0<raw[3]<128 and raw[3]%8==0,
             'lookup-second-context-slot','positive aligned anonymous QWORD slot',slot)
    slot_offset=raw[3];resolver=p.next();resolver_pointer=_call(resolver)
    p.take(b'\x48\x8b\xd0');p.take(b'\x48\x8b\xcb')
    _restore(p,frame,slots,(b'\x48\x8b\x5c\x24',b'\x48\x8b\x6c\x24',b'\x48\x8b\x74\x24'))
    tail=p.next();tail_pointer=_tail_jump(tail);p.end()
    return {'completePrimaryForwardingProgramProved':True,'contextPointerOffset':context_offset,
        'contextPointerReads':[{'va':_at(first_reload),'phase':'before type helper'},
                               {'va':_at(second_reload),'phase':'after nongeneric lookup'}],
        'anonymousHandleWordReadVa':_at(handle_load),'anonymousHandleWordSlotOffset':0,
        'anonymousTailWordReadVa':_at(slot),'anonymousTailWordSlotOffset':slot_offset,
        'metadataCellVa':cell,'typeHelperCallVa':_at(type_call),'nongenericLookupCallVa':_at(lookup_call),
        'nongenericArguments':{'blackboard':'unchanged incoming RCX reference saved in RBP',
            'key':'unchanged incoming RDX reference saved in RSI',
            'type':'RAX returned by named Type.GetTypeFromHandle, passed in R8',
            'methodInfoRepresentation':'zero R9 word'},
        'tailJumpVa':_at(tail),'tailTargetVa':tail_pointer,
        'tailArguments':{'rcx':'RAX returned by nongeneric GetVariable, saved in RBX',
            'rdx':'RAX returned by opaque helper on the second anonymous context slot'},
        'opaqueHelpers':[{'role':role,'callVa':_at(row),'targetVa':target,'behaviorProved':False}
            for role,row,target in (('metadata-cell helper',metadata_call,metadata_helper),
                ('incoming-context helper',context_init,context_helper),('class-cell helper',class_init,class_helper),
                ('second-context-slot helper',resolver,resolver_pointer))],
        'contextLayoutSemanticsProved':False,'liveMethodInfoSelected':False,'requestedTypeIdentityProved':False,
        'typeHelperAlgorithmProved':False,'nongenericLookupAlgorithmProved':False,'runtimeExecutionKnown':False}


def validate_reference_tail(rows):
    p=_Program(rows);frame,slots=_frame(p,(b'\x48\x89\x5c\x24',))
    p.take(b'\x48\x8b\xfa');p.take(b'\x48\x8b\xd9');p.take(b'\x48\x85\xc9')
    null_branch=p.next();null_entry=_branch(null_branch,opcode=b'\x74')
    p.take(b'\x48\x8b\x09');predicate=p.next();predicate_pointer=_call(predicate)
    p.take(b'\x84\xc0');failure_branch=p.next();failure_entry=_branch(failure_branch,opcode=b'\x74')
    p.take(b'\x48\x8b\xc3');_restore(p,frame,slots,(b'\x48\x8b\x5c\x24',));success_ret=p.take(b'\xc3')
    _require(_at(p.peek())==failure_entry,'lookup-tail-false-edge','zero predicate reaches exact failure entry',hex(failure_entry))
    p.take(b'\x48\x8b\xd7');p.take(b'\x48\x8b\xcb');failure=p.next();failure_pointer=_call(failure)
    p.take(b'\xcc')
    _require(_at(p.peek())==null_entry,'lookup-tail-null-edge','null reference skips predicate and failure call',hex(null_entry))
    p.take(b'\x48\x8b\x5c\x24'+bytes([frame+8+slots[0]]));p.take(b'\x33\xc0')
    p.take(b'\x48\x83\xc4'+bytes([frame]));p.take(b'\x5f');null_ret=p.take(b'\xc3');p.end()
    return {'completePrimaryTailProgramProved':True,
        'nonnullReturn':{'condition':'incoming RCX nonnull and opaque predicate returns nonzero AL',
            'source':'same incoming RCX reference saved in RBX','returnVa':_at(success_ret)},
        'nullReturn':{'condition':'incoming RCX null','rax':0,'returnVa':_at(null_ret),
            'predicateAndFailureCallsSkipped':True},
        'predicate':{'callVa':_at(predicate),'targetVa':predicate_pointer,
            'rcx':'first QWORD read from nonnull incoming reference','rdx':'unchanged incoming RDX word','behaviorProved':False},
        'failure':{'callVa':_at(failure),'targetVa':failure_pointer,
            'rcx':'nonnull incoming reference','rdx':'incoming second word saved in RDI',
            'followedByInt3':True,'behaviorProved':False},
        'castOrCompatibilitySemanticsProved':False,'runtimeExecutionKnown':False}


def validate_handle_layout(*,field_type,field_offset,instance_bytes,native_bytes):
    _require(field_type==(0x18,'nint',False) and field_offset==16 and instance_bytes==24 and native_bytes==8,
             'lookup-handle-layout','sole instance nint at boxed payload start; exact eight-byte value extent',
             [field_type,field_offset,instance_bytes,native_bytes])


def validate_owned_return_type(return_type,parameter):
    _require(type(parameter) is int and parameter>=0
             and return_type==(0x15,'NodeCanvas.Framework.Variable`1<MVAR['+str(parameter)+']>',False),
             'lookup-owned-return-parameter','Variable instantiated with this method container parameter',
             [return_type,parameter])


def prove(index,claim):
    _require(claim.get('mode')==MODE,'lookup-mode',MODE,claim.get('mode'))
    image=index.image;generic=_method(image,claim['genericLookup']);nongeneric=_method(image,claim['nongenericLookup'])
    params=list(image.metadata.parameters_for(generic))
    _require(generic.flags&0x10 and _generic_arity(image.metadata,generic)==1
             and [_type(image,p.type_index) for p in params]==[(0x12,'NodeCanvas.Framework.IBlackboard',False),(0x0e,'string',False)],
             'lookup-generic-signature','static one-method-parameter generic IBlackboard/String lookup',generic.index)
    section=image.metadata.sections['genericContainers'];at=section.offset+generic.generic_container_index*16
    owner,count,is_method,parameter=struct.unpack_from('<iiii',image.metadata.buf,at)
    validate_owned_return_type(_type(image,generic.return_type),parameter)
    params=list(image.metadata.parameters_for(nongeneric))
    _require(nongeneric.flags&0x10 and nongeneric.generic_container_index<0
             and _type(image,nongeneric.return_type)==(0x12,'NodeCanvas.Framework.Variable',False)
             and [_type(image,p.type_index) for p in params]==[(0x12,'NodeCanvas.Framework.IBlackboard',False),
                 (0x0e,'string',False),(0x12,'System.Type',False)],
             'lookup-nongeneric-signature','static IBlackboard/String/Type lookup returning Variable',nongeneric.index)
    type_helper=_method(image,claim['typeFromHandle']);params=list(image.metadata.parameters_for(type_helper))
    _require(type_helper.flags&0x10 and type_helper.generic_container_index<0
             and _type(image,type_helper.return_type)==(0x12,'System.Type',False)
             and [_type(image,p.type_index) for p in params]==[(0x11,'System.RuntimeTypeHandle',False)],
             'lookup-type-signature','static Type.GetTypeFromHandle(RuntimeTypeHandle)',type_helper.index)
    context=NativeReferenceContext(image,index=index);handle=_owner(image,'System.RuntimeTypeHandle')
    _require(handle.generic_container_index<0 and context.parent('System.RuntimeTypeHandle')=='System.ValueType',
             'lookup-handle-owner','nongeneric declared value class',handle.index)
    fields=[f for f in image.metadata.fields_for(handle) if not context.field_attributes(f.type_index)&0x10]
    _require(len(fields)==1,'lookup-handle-fields','one instance payload word',len(fields))
    qualified='System.RuntimeTypeHandle::'+image.metadata.string(fields[0].name_index)
    field_owner,field_name,offset=context.field(qualified)
    _require(0<=handle.index<image.registration['typeDefinitionsSizesCount'],'lookup-handle-size-index','selected size table',handle.index)
    size_va=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+handle.index*8)
    _require(size_va!=0,'lookup-handle-size-pointer','nonzero selected size row',size_va)
    size_raw=image.pe.bytes_at_va(size_va,16)
    _require(len(size_raw)==16,'lookup-handle-size-row','complete selected size row',len(size_raw))
    size,native_size=struct.unpack_from('<Ii',size_raw)
    validate_handle_layout(field_type=_instance_field_type(image,fields[0].type_index),field_offset=offset,
        instance_bytes=size,native_bytes=native_size)
    args=claim['registeredMethodArguments']
    _require(isinstance(args,list) and bool(args) and all(isinstance(a,str) and a for a in args) and len(args)==len(set(args)),
             'lookup-selected-instantiations','distinct explicit method arguments',args)
    entries=GenericEntries(image);registered=[{'methodArgument':a,**entries.resolve(generic.index,[],[a])} for a in args]
    windows=[];programs=[]
    def decoded(ptr):
        _require(ptr in index.extents and not index.chained_fragments.get(ptr),'lookup-primary-owner','exact primary entry without omitted fragments',hex(ptr))
        size=index.extents[ptr]-ptr;_require(0<size<=4096,'lookup-primary-size','bounded primary body',size)
        rows=index._decode(ptr,size);_require(sum(len(_raw(r)) for r in rows)==size,'lookup-primary-coverage',size,len(rows))
        windows.append({'startRva':ptr-image.pe.image_base,'endRva':ptr+size-image.pe.image_base,
            'sha256':hashlib.sha256(image.pe.bytes_at_va(ptr,size)).hexdigest().upper()})
        return rows
    for ptr in sorted({r['pointer'] for r in registered}):
        forwarding=validate_forwarding(decoded(ptr),type_from_handle_pointer=image.method_pointer_va(type_helper),
            nongeneric_lookup_pointer=image.method_pointer_va(nongeneric))
        tail=validate_reference_tail(decoded(forwarding['tailTargetVa']))
        for helper in forwarding['opaqueHelpers']:
            target=helper['targetVa'];helper['exactPrimaryExtentAvailable']=target in index.extents
        programs.append({'entryVa':ptr,'registeredMethodArguments':[r['methodArgument'] for r in registered if r['pointer']==ptr],
            'forwarding':forwarding,'tail':tail,'conditionalNonnullReturnSource':'same opaque Variable reference returned by nongeneric lookup',
            'conditionalNullReturnSource':'zero when nongeneric lookup returned null and all intervening helper calls return normally'})
    return {'method':[generic.index,claim['genericLookup']['type'],claim['genericLookup']['method']],
        'methodOwnedReturnParameter':parameter,'registeredInstantiations':registered,'programs':programs,'codeWindows':windows,
        'typeHelperMethodIndex':type_helper.index,'nongenericLookupMethodIndex':nongeneric.index,
        'handleLayout':{'field':qualified,'fieldOffset':offset,'instanceBytes':size,'nativeBytes':native_size,
            'sizeRowVa':size_va,'sizeRowRawHex':size_raw.hex().upper()},
        'completeForwardingAndConditionalTailProgramsProved':True,
        'stringIndependentRegistrationProved':False,'contextLayoutSemanticsProved':False,'liveMethodInfoSelected':False,
        'nongenericLookupAlgorithmProved':False,'typeHelperAlgorithmProved':False,'castOrCompatibilitySemanticsProved':False,
        'variableValueGetterOrWriteProved':False,'runtimeExecutionKnown':False,'evidenceBoundary':'conditional',
        'condition':'Selected registered physical entry, coherent valid pointer/frame reads and ordinary returning Win64 helpers; nonnull same-reference return additionally requires a nonzero opaque predicate AL result.'}
