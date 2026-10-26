"""Selected Original constructor that stores one owned metadata string literal.

The complete entry program loads an initialized literal reference, stores that
whole reference in its exact ordinary String field and tails the independently
proved disabled write barrier for the same field address. This proves neither
the runtime literal initialization nor a physical function extent. The bounded
prefix ends at its owned tail jump; bytes following that jump are not executed
or interpreted as constructor instructions.
"""
import hashlib

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition,detail=None):
    if not condition:raise ValueError('generatedLiteralConstructor.'+check+':'+str(detail)[:700])


def program(data,entry):
    need('bounded-entry',type(data)is bytes and 0<len(data)<=128 and type(entry)is int and entry>0)
    g=BytesPath([(entry,data)],entry);site=g.at;cell=g.relative('488b05')
    g.take('488941');offset=g.read(1)[0]
    need('positive-instance-field',16<=offset<128)
    g.take('4883c1');need('same-field-barrier-address',g.read(1)[0]==offset)
    tail=g.at;target=g.relative('e9')
    return dict(profile='single-owned-string-literal-tail-barrier.v1',selectedBytes=g.seen,programBytes=g.at-entry,
        literalUsage=dict(instructionVa=site,cellVa=cell),fieldOffset=offset,storedBytes=8,
        barrierTail=dict(instructionVa=tail,targetVa=target,fieldAddressOffset=offset),
        sameWholeLoadedReferenceStored=True,stackUnchanged=True,allNonvolatileRegistersUnchanged=True,
        normalReturnViaBarrier=True,physicalFunctionExtentProved=False)


def derive(image,pins,*,context,method,original):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.context import unresolved_usage_index,literal_record
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    _publication_gate(image,pins);ctx=context;md=image.metadata;base=image.pe.image_base
    td=ctx.index.types[original]
    need('owned-reference-original-constructor',not ctx.is_value_type(original)and method.declaring_type==td.index
        and md.string(method.name_index)=='.ctor'and method.generic_container_index<0 and method.parameter_count==0)
    scalar.owned_method_abi(image,ctx,method.index,td.index,('void',1,False),[],'literalConstructor.original')
    entry=image.method_pointer_va(method);data=image.pe.bytes_at_va(entry,128);selected=program(data,entry)
    matches=[]
    for field in md.fields_for(td):
        if ctx.field_attributes(field.type_index)&16:continue
        name=md.string(field.name_index);fact=ctx.field(original+'::'+name)
        if fact[2]!=selected['fieldOffset']:continue
        need('exact-ordinary-string-field',fact[1]=='string',fact)
        scalar.ordinary(image,ctx.type_pointer(field.type_index),14,'literalConstructor.field',reference=True)
        matches.append(dict(fieldIndex=field.index,fieldName=name,typeName='string',offset=fact[2],storedBytes=8))
    need('one-owned-string-field',len(matches)==1,matches)
    cell=selected['literalUsage']['cellVa'];raw=image.pe.bytes_at_va(cell,8)
    table=md.sections['stringLiteral'];pool=md.sections['stringLiteralData']
    index=unresolved_usage_index(raw,table.size//8,tag=5,source='literalConstructor.usage',offset=cell)
    record=bytes(md.buf[table.offset+index*8:table.offset+(index+1)*8])
    offset,length=literal_record(record,pool.size,source='literalConstructor.literal',offset=index*8)
    literal=bytes(md.buf[pool.offset+offset:pool.offset+offset+length])
    windows,barrier,_=_fast_barrier(image,selected['barrierTail']['targetVa'])
    size=selected['programBytes'];source=data[:size]
    _publication_gate(image,pins)
    return dict(method=[method.index,original,'.ctor',entry-base],
        codeWindows=[dict(startRva=entry-base,endRva=entry-base+size,sha256=hashlib.sha256(source).hexdigest().upper(),
            boundary='complete selected literal-store Original constructor entry and tail; physical extent unproved')],
        literalConstructorProgram=selected,staticReferenceFieldStores=matches,
        literalSource=dict(instructionRva=selected['literalUsage']['instructionVa']-base,usageCellRva=cell-base,
            usageRawHex=raw.hex().upper(),literalIndex=index,literalRecordHex=record.hex().upper(),
            literalPoolOffset=offset,literalByteLength=length,literalHex=literal.hex().upper(),
            runtimeLiteralCellInitializationRequired=True),
        barrierWindows=windows,barrierProof=barrier,completeReachableEntryProgramProved=True,
        physicalFunctionExtentProved=False,normalConstructorReturnRequired=True,runtimeExecutionKnown=False,
        condition='Initialized exact metadata literal cell, compatible original receiver, disabled collector and normal barrier return. No serialized field grammar follows from a constructor default.')
