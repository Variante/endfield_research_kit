"""Exact ordinary unmanaged-array MVAR ownership, without wire/source admission.

This follows the actual ReadUnmanagedArray -> DangerousReadUnmanagedArray
context and its Empty/allocation/data-reference slots. Each helper owns its
reciprocal generic parameter, exact static/instance ABI and array/byref result.
The current selected source may inline those helpers; no canonical body-pointer
equality, folded Empty entry, element width or executed AsSpan call is inferred.
Concrete bulk source/allocation/data-pointer/byte-copy proof stays with its
caller. Runtime inflation and surrounding parent/child grammar remain open.
"""
import struct

from scripts.game_data.memorypack import scalar_param_native as scalar

LABEL='skillUnmanagedArrayContext'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def _concrete_element(image,ctx,usage,*,element_type,profile):
    """Explicit nominal gates; none supplies an element wire width."""
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    primitives={'uint32':('uint',9),'int32':('int',8),'boolean':('bool',2)}
    need('finite-element-profile',True,profile in('value-record',*primitives))
    if profile in primitives:need('explicit-primitive-name',primitives[profile][0],element_type)
    typed=bind_typed_read(image,usage,method_name='ReadUnmanagedArray',argument=element_type,kind=primitives[profile][1]if profile in primitives else 17)
    if profile in primitives:
        raw=image.pe.bytes_at_va(typed['argumentPointer'],16)
        need('exact-ordinary-primitive-record',bytes((primitives[profile][1],128)),raw[10:12])
    else:need('ordinary-non-enum-element',True,ctx.is_value_type(element_type)and not ctx.is_enum(element_type))
    return typed


def derive(image,usage,*,element_type):
    """Existing ordinary17 non-enum value-record entry; unchanged scope."""
    return _derive_context(image,usage,element_type=element_type,profile='value-record')


def derive_uint32(image,usage):
    """Exact primitive uint09/80 context; no width, count or parent admission."""
    return _derive_context(image,usage,element_type='uint',profile='uint32')


def derive_int32(image,usage):
    """Exact primitive int08/80 context; no width, count or parent admission."""
    return _derive_context(image,usage,element_type='int',profile='int32')


def derive_boolean(image,usage):
    """Exact primitive bool02/80 context; no normalization or width inference."""
    return _derive_context(image,usage,element_type='bool',profile='boolean')


def _derive_context(image,usage,*,element_type,profile):
    from scripts.game_data.il2cpp.context import method_parameter_owner
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,validate_generic_contexts
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    ctx=NativeReferenceContext(image);md=image.metadata;symbols=ContextSymbols(image);ge=GenericEntries(image)
    validate_typed_usage_context(image,usage,label=LABEL+'.caller')
    typed=_concrete_element(image,ctx,usage,element_type=element_type,profile=profile)
    first=symbols.context(usage['methodSpec'][0],is_method=True)
    need('single-first-context-slot',[0],[r['relativeSlot']for r in first['entries']])
    danger=symbols.context(first['entries'][0]['methodSpec'][0],is_method=True)
    need('ordered-dangerous-context-slots',[0,1,2],[r['relativeSlot']for r in danger['entries']])
    helpers=[symbols.context(r['methodSpec'][0],is_method=True)for r in danger['entries']]
    contexts=[first,danger,*helpers];validate_generic_contexts(image,contexts,label=LABEL)
    section=md.sections['genericContainers'];containers=[m.generic_container_index for m in md.methods]
    def owner(row,typename,name,*,static,arity):
        m=md.methods[row['definition']];at=section.offset+m.generic_container_index*16
        need('bounded-owned-generic-container',True,m.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16)
        definition,count,is_method,start=struct.unpack_from('<iiii',md.buf,at)
        identity=method_parameter_owner(md.buf,start,containers,source=LABEL)
        need('reciprocal-MVAR',(m.index,1,1,m.index,0),(definition,count,is_method,identity['methodIndex'],identity['ordinal']))
        need('exact-method-ABI',(typename,name,static,arity),
            (image.type_name(m.declaring_type),md.string(m.name_index),bool(m.flags&16),m.parameter_count))
        return m,start
    def variable(pointer,start):
        raw=image.pe.bytes_at_va(pointer,16)
        need('exact-owned-undecorated-MVAR',(b'\x1e\x00',start),(raw[10:12],int.from_bytes(raw[:8],'little')))
    def array(index,start):
        raw=image.pe.bytes_at_va(ctx.type_pointer(index),16);need('exact-SZARRAY',b'\x1d\x00',raw[10:12])
        variable(int.from_bytes(raw[:8],'little'),start)
    def slot(row,typename,name,start,definition):
        need('method-context-slot-kind',3,row['kind']);spec=ge.specs[row['index']]
        need('same-owned-MethodSpec',row['methodSpec'],list(spec));m=md.methods[spec[0]]
        need('same-nested-method',(typename,name,definition,-1),(image.type_name(m.declaring_type),md.string(m.name_index),m.index,spec[1]))
        args=image.instantiations.resolve(spec[2]).arguments;need('one-owned-MVAR',1,len(args));variable(args[0].type_pointer_va,start)
    fm,fv=owner(first,'MemoryPack.MemoryPackReader','ReadUnmanagedArray',static=False,arity=0);array(fm.return_type,fv)
    dm,dv=owner(danger,'MemoryPack.MemoryPackReader','DangerousReadUnmanagedArray',static=False,arity=0);array(dm.return_type,dv)
    slot(first['entries'][0],'MemoryPack.MemoryPackReader','DangerousReadUnmanagedArray',fv,dm.index)
    declarations=[('System.Array','Empty',0),('MemoryPack.Internal.MemoryMarshalEx','AllocateUninitializedArray',2),
        ('MemoryPack.Internal.MemoryMarshalEx','GetArrayDataReference',1)]
    proofs=[]
    for row,closed,(typename,name,arity)in zip(danger['entries'],helpers,declarations,strict=True):
        method,var=owner(closed,typename,name,static=True,arity=arity);slot(row,typename,name,dv,method.index)
        if name=='GetArrayDataReference':
            parameter,=md.parameters_for(method);array(parameter.type_index,var)
            result=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
            need('element-byref-return',(b'\x1e\x20',var),(result[10:12],int.from_bytes(result[:8],'little')))
            need('data-reference-owned-context',[0,1],[r['relativeSlot']for r in closed['entries']])
            for nested,nt,nn in zip(closed['entries'],('System.MemoryExtensions','System.Runtime.InteropServices.MemoryMarshal'),('AsSpan','GetReference'),strict=True):
                slot(nested,nt,nn,var,nested['methodSpec'][0])
        else:
            array(method.return_type,var)
            need('single-helper-type-context',[0],[r['relativeSlot']for r in closed['entries']])
            carrier=closed['entries'][0];need('helper-type-context-kind',2,carrier['kind'])
            if name=='AllocateUninitializedArray':
                p,q=md.parameters_for(method)
                scalar.ordinary(image,ctx.type_pointer(p.type_index),8,LABEL+'.count')
                scalar.ordinary(image,ctx.type_pointer(q.type_index),2,LABEL+'.pinned')
                array(carrier['index'],var)
            else:
                c=carrier['type'];need('exact-empty-array-class','System.EmptyArray`1',c['definition']['name'])
                argument,=c['classArguments'];variable(argument['typePointerVa'],var)
                td=ctx.index.types['System.EmptyArray`1'];fields=[f for f in md.fields_for(td)
                    if ctx.field_attributes(f.type_index)&16 and not ctx.field_attributes(f.type_index)&64]
                need('sole-empty-array-static-field',1,len(fields));raw=image.pe.bytes_at_va(ctx.type_pointer(fields[0].type_index),16)
                need('empty-static-SZARRAY',b'\x1d\x00',raw[10:12]);parameter=image.pe.bytes_at_va(int.from_bytes(raw[:8],'little'),16)
                at=section.offset+td.generic_container_index*16;definition,count,is_method,start=struct.unpack_from('<iiii',md.buf,at)
                need('empty-class-reciprocal-container',(td.index,1,0),(definition,count,is_method))
                need('static-array-owned-class-VAR',(b'\x13\x00',start),(parameter[10:12],int.from_bytes(parameter[:8],'little')))
        proofs.append(dict(definition=method.index,methodName=name,ownedMethodParameter=var))
    return dict(typedRequest=usage,concreteElement=element_type,concreteElementPointer=typed['argumentPointer'],
        contexts=contexts,helperOwnership=proofs,sourceHelperBodyEquivalenceInferred=False,
        elementGrammarAdmitted=False,countsAdmitted=[],wholeOwnerAdmitted=False)
