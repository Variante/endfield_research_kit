"""Typed UTF8 allocation/cache and closed span MethodSpec joins.

The selected-image caller owns freshness, original instruction ranges and
the complete argument-transfer program. Registration sharing stays explicit;
neither an on-disk usage nor a metadata slot identifies a live runtime object.
"""
from __future__ import annotations
import struct
from .formatter_composition import validate_typed_usage_context, _vtable
from .generic_entries import GenericEntries
from .protocol import runtime_type_field_offsets, runtime_type_name
from .reference_layouts import NativeReferenceContext
from .context import method_parameter_owner


def _need(check, expected, actual):
    if expected!=actual: raise ValueError(f'utf8Bindings.{check}: expected={str(expected)[:350]} actual={str(actual)[:350]}')


def validate_encoding_bindings(image, contexts):
    _need('context-roles',{'encodingType','allocationType','span'},set(contexts))
    selected=NativeReferenceContext(image); md=image.metadata
    for role,name,prefix in (('encodingType','System.Text.Encoding','488b05'),
                             ('allocationType','System.Text.UTF8Encoding','488b0d'),
                             ('span','System.Runtime.InteropServices.MemoryMarshal','4c8b0d')):
        row=contexts[role]; validate_typed_usage_context(image,row,label='utf8Bindings.'+role)
        _need(role+'.type-name',name,row['typeName'])
        _need(role+'.opcode',prefix,bytes.fromhex(row['instructionHex'])[:3].hex())
        _need(role+'.usage-tag',6 if role=='span' else 1,row['tag'])
        if role!='span':
            raw=bytes.fromhex(row['typeRawHex']); _need(role+'.class-kind',18,raw[10])
            _need(role+'.ordinary-reference',0,raw[11]); _need(role+'.value-type',False,selected.is_value_type(name))
    _need('utf8-parent','System.Text.Encoding',selected.parent('System.Text.UTF8Encoding'))
    result={}
    for key,owner,name,kind,type_name,static in (
            ('readOnly','System.Text.Encoding','m_isReadOnly',2,'bool',False),
            ('codePage','System.Text.Encoding','m_codePage',8,'int',False),
            ('emitIdentifier','System.Text.UTF8Encoding','_emitUTF8Identifier',2,'bool',False),
            ('throwInvalid','System.Text.UTF8Encoding','_isThrowException',2,'bool',False),
            ('utf8Cache','System.Text.Encoding','utf8Encoding',18,'System.Text.Encoding',True)):
        td=selected.index.types[owner]; fields=[f for f in md.fields_for(td) if md.string(f.name_index)==name]
        _need(key+'.field-count',1,len(fields)); f=fields[0]; pointer=selected.type_pointer(f.type_index)
        raw=image.pe.bytes_at_va(pointer,16)
        _need(key+'.kind',kind,raw[10]); _need(key+'.ordinary',0,raw[11]&0x7f)
        if kind==18: _need(key+'.reference-marker',0,raw[11])
        _need(key+'.type',type_name,selected.type_name(f.type_index))
        _need(key+'.static',static,bool(selected.field_attributes(f.type_index)&0x10))
        result[key]=runtime_type_field_offsets(md,image.pe,image.registration,td.index)[name]
    span=contexts['span']; _need('span-method','CreateReadOnlySpan',span['methodName'])
    _need('span-class-arguments',[],span['classArguments']); _need('span-method-arguments',['byte'],span['methodArguments'])
    method=md.methods[span['methodSpec'][0]]; _need('span-static',True,bool(method.flags&0x10))
    section=md.sections['genericContainers']; at=section.offset+method.generic_container_index*16
    if method.generic_container_index<0 or not section.offset<=at<=section.offset+section.size-16:
        raise ValueError('utf8Bindings.span-generic-container-range')
    owner,count,is_method,start=struct.unpack_from('<iiii',md.buf,at)
    _need('span-generic-owner',[method.index,1,1],[owner,count,is_method])
    variable=method_parameter_owner(md.buf,start,[m.generic_container_index for m in md.methods],source='utf8Bindings')
    _need('span-mvar-owner',[method.index,0],[variable['methodIndex'],variable['ordinal']])
    parameters=list(md.parameters_for(method)); _need('span-parameter-count',2,len(parameters))
    first=image.pe.bytes_at_va(selected.type_pointer(parameters[0].type_index),16)
    _need('span-byref-mvar',bytes((30,32)),first[10:12]); _need('span-mvar-index',start,int.from_bytes(first[:8],'little'))
    second=image.pe.bytes_at_va(selected.type_pointer(parameters[1].type_index),16)
    _need('span-count-kind',8,second[10]); _need('span-count-ordinary',0,second[11]&0x7f)
    _need('span-result',f'System.ReadOnlySpan`1<MVAR[{start}]>',selected.type_name(method.return_type))
    result_type=image.pe.bytes_at_va(selected.type_pointer(method.return_type),16)
    _need('span-result-value-kind',bytes((21,128)),result_type[10:12])
    _need('span-result-value-definition',True,selected.is_value_type('System.ReadOnlySpan`1'))
    instance=image.instantiations.resolve(span['methodSpec'][2]); _need('span-byte-argument-count',1,len(instance.arguments))
    argument=instance.arguments[0]; raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
    _need('span-byte-kind',5,raw[10]); _need('span-byte-ordinary',0,raw[11]&0x7f)
    _need('span-byte-name','byte',runtime_type_name(image.pe,md,argument.type_pointer_va))
    return result


def validate_span_entry(image, context, target):
    rows=GenericEntries(image).observe(context['methodSpec'][0],[],['byte'])
    _need('span-registration-count',1,len(rows)); row=rows[0]
    _need('span-registration-spec',context['methodSpecIndex'],row['methodSpecIndex'])
    _need('span-registration-call-target',target,row['pointer'])
    _need('span-no-adjustor',-1,row['registration']['indices'][2])
    return {'methodDefinitionIndices':row['methodDefinitionIndices'],
            'registrationAndCallerContextProved':True,'runtimeContextResolutionObserved':False,
            'genericFieldOffsetsUsed':False}


def validate_pointer_decoder_bindings(image, methods, layout, vtable_offset, empty_context):
    _need('pointer-method-roles',{'pointer','count','fill'},set(methods)); selected=NativeReferenceContext(image);md=image.metadata
    _need('vtable-offset-range',True,type(vtable_offset) is int and 0<=vtable_offset<1<<20)
    for role,owner,name,parameters in (
            ('pointer','System.Text.Encoding','GetString',['byte*','int']),
            ('count','System.Text.UTF8Encoding','GetCharCount',['byte*','int','System.Text.DecoderNLS']),
            ('fill','System.Text.UTF8Encoding','GetChars',['byte*','int','char*','int','System.Text.DecoderNLS'])):
        row=methods[role];image.validate_method_row(row,label='utf8Bindings.'+role);method=md.methods[row[0]]
        _need(role+'.owner',owner,image.type_name(method.declaring_type));_need(role+'.name',name,md.string(method.name_index))
        _need(role+'.ordinary-instance',True,not method.flags&0x10 and method.generic_container_index<0)
        params=list(md.parameters_for(method));_need(role+'.parameter-count',len(parameters),len(params))
        _need(role+'.parameter-types',parameters,[selected.type_name(p.type_index) for p in params])
        for type_index,kind in [(method.return_type,14 if role=='pointer' else 8),
                               *[(p.type_index,{'byte*':15,'char*':15,'int':8,'System.Text.DecoderNLS':18}[name]) for p,name in zip(params,parameters)]]:
            raw=image.pe.bytes_at_va(selected.type_pointer(type_index),16)
            _need(role+'.abi-kind',kind,raw[10]);_need(role+'.abi-ordinary',0,raw[11]&0x7f)
            if kind in (14,15,18):_need(role+'.reference-or-pointer-marker',0,raw[11])
        _need(role+'.return-type','string' if role=='pointer' else 'int',selected.type_name(method.return_type))
        if role!='pointer':
            _need(role+'.virtual',True,bool(method.flags&0x40));_vtable(image,method.declaring_type,method.slot,method.index,'utf8Bindings.'+role)
            _need(role+'.physical-slot',vtable_offset+16*method.slot,layout[role+'Function'])
    _need('first-character-field',('System.String','char',layout['firstChar']),selected.field('System.String::_firstChar'))
    validate_typed_usage_context(image,empty_context,label='utf8Bindings.emptyString')
    _need('empty-context-class','string',empty_context['typeName']);_need('empty-context-tag',1,empty_context['tag'])
    _need('empty-context-reference',bytes((14,0)),bytes.fromhex(empty_context['typeRawHex'])[10:12])
    td=selected.index.types['System.String']
    _need('empty-field-offset',0,runtime_type_field_offsets(md,image.pe,image.registration,td.index)['Empty'])
    for name,kind,type_name,static in (('_firstChar',3,'char',False),('Empty',14,'string',True)):
        declarations=[f for f in md.fields_for(td) if md.string(f.name_index)==name];_need(name+'.field-count',1,len(declarations))
        field=declarations[0];raw=image.pe.bytes_at_va(selected.type_pointer(field.type_index),16)
        _need(name+'.kind',kind,raw[10]);_need(name+'.ordinary',0,raw[11]&0x7f)
        if kind==14:_need(name+'.reference-marker',0,raw[11])
        _need(name+'.type',type_name,selected.type_name(field.type_index))
        _need(name+'.static',static,bool(selected.field_attributes(field.type_index)&0x10))
    return {'declaredVirtualSlotsMatchPhysicalCallPairs':True,'internalDecoderStateType':'System.Text.DecoderNLS',
            'runtimeReceiverVtableObserved':False,'decoderCharacterSemanticsProved':False}
