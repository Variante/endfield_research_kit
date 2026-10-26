"""Selected scalar Param declarations, native registrations and generated wrapper views."""
from __future__ import annotations

import hashlib
import json
import struct

from scripts.game_data import levelscript_param_types as types
from scripts.game_data.il2cpp.context import generic_method_candidates, method_parameter_owner, method_spec_record
from scripts.game_data.il2cpp.protocol import constant_value, field_defaults, runtime_type_field_offsets
from scripts.game_data.memorypack.scalar_param_native import need, owned_method_abi


def raw(row):
    return bytes.fromhex(row[1])


def target(row, opcode):
    encoded = raw(row)
    size = 4 if opcode in (b'\xe8', b'\xe9') or len(opcode) == 2 else 1
    need('paramValueClaims.edge', 'opcode', opcode, encoded[:len(opcode)])
    need('paramValueClaims.edge', 'size', len(opcode) + size, len(encoded))
    return row[0] + len(encoded) + int.from_bytes(encoded[len(opcode):], 'little', signed=True)


def shape(rows, forms, label):
    need(label, 'instructionCount', len(forms), len(rows))
    for n, (row, form) in enumerate(zip(rows, forms)):
        need(label, f'rvaType[{n}]', int, type(row[0]))
        if form is not None:
            need(label, f'opcode[{n}]', bytes.fromhex(form), raw(row))
        if n:
            need(label, f'contiguous[{n}]', rows[n - 1][0] + len(raw(rows[n - 1])), row[0])


def qualified_owner(image, spec):
    owners=[td for td in image.metadata.types if image.type_name(td.index)==spec['type']
            and image.metadata.string(image.metadata.images[image.owners[td.index]].name_index)==spec['image']]
    need('paramValueClaims.owner', 'qualifiedOwnerCount', 1, len(owners))
    return owners[0]


def formal_method(image, context, method, role):
    need('paramValueClaims.'+role, 'staticFlag', role!='predicate', bool(method.flags&16))
    params=image.metadata.parameters_for(method)
    types.ordinary(types.type_record(image,context,method.return_type), 0x1e if role=='value' else 2, 'paramValueClaims.return')
    if role=='predicate':
        need('paramValueClaims.predicate','arity',0,len(params))
        need('paramValueClaims.predicate','definition',types.PARAM_TYPE,image.type_name(method.declaring_type))
        return method.declaring_type
    need('paramValueClaims.'+role,'arity',3,len(params))
    formal=types.type_record(image,context,method.return_type if role=='value' else params[1].type_index)
    types.ordinary(formal,0x1e,'paramValueClaims.formal',byref=role=='tryValue')
    index=int.from_bytes(formal[:8],'little')
    owner=method_parameter_owner(image.metadata.buf,index,[m.generic_container_index for m in image.metadata.methods],source='paramValueClaims.formal')
    need('paramValueClaims.formal','owner',method.index,owner['methodIndex']);need('paramValueClaims.formal','ordinal',0,owner['ordinal'])
    need('paramValueClaims.formal','arity',1,struct.unpack_from('<i',bytes.fromhex(owner['containerRawHex']),4)[0])
    definition=types.param_reference(image,types.type_record(image,context,params[0].type_index),0x1e,index)
    types.ordinary(types.type_record(image,context,params[2].type_index),2,'paramValueClaims.flag')
    if role=='value':
        default=types.type_record(image,context,params[1].type_index);types.ordinary(default,0x1e,'paramValueClaims.default')
        need('paramValueClaims.default','sameFormal',index,int.from_bytes(default[:8],'little'))
    return definition


def prototype_tokens(role):
    return {
        'parameters': [] if role=='predicate' else ['Param<methodArgument0> reference',
                       'ordinary methodArgument0' if role=='value' else 'explicit byref methodArgument0',
                       'ordinary Boolean'],
        'returnType': 'ordinary methodArgument0' if role=='value' else 'ordinary Boolean',
    }


def named_entries(image,specs,context,*,primitive_name,primitive_kind):
    md,pe,reg=image.metadata,image.pe,image.registration
    methods={};definitions={}
    for role in ('value','tryValue','predicate'):
        spec=specs[role];owner=qualified_owner(image,spec);matches=[];refusals=[]
        need('paramValueClaims.'+role,'classArguments',[primitive_name] if role=='predicate' else [],spec['classArguments'])
        need('paramValueClaims.'+role,'methodArguments',[] if role=='predicate' else [primitive_name],spec['methodArguments'])
        need('paramValueClaims.'+role,'callAbi','instance' if role=='predicate' else 'static',spec['callAbi'])
        tokens=prototype_tokens(role)
        for key,value in tokens.items():need('paramValueClaims.'+role,key,value,spec[key])
        for method in md.methods_for(owner):
            if md.string(method.name_index)!=spec['method']: continue
            try: definition=formal_method(image,context,method,role)
            except (ValueError,KeyError,IndexError,struct.error) as exc:
                if len(refusals)<3:refusals.append({'methodIndex':method.index,'detail':str(exc)[:350]})
                continue
            matches.append((method,definition))
        if len(matches)!=1:
            raise ValueError('paramValueClaims.'+role+'.qualifiedFormalMethods: '+json.dumps({
                'type':spec['type'],'method':spec['method'],'image':spec['image'],
                'expected':1,'actual':len(matches),'firstRefusals':refusals},ensure_ascii=False))
        methods[role],definitions[role]=matches[0]
    need('paramValueClaims','sameParameterDefinition',1,len(set(definitions.values())))
    selected={};records={};base=int(reg['methodSpecs'],16)
    count=reg['methodSpecsCount']
    if type(count) is not int or not 0<count<=1_000_000: raise ValueError('paramValueClaims.methodSpecs: unbounded count')
    data=pe.bytes_at_va(base,count*12);wanted={m.index:role for role,m in methods.items()}
    for n,record in enumerate(struct.iter_unpack('<iii',data)):
        if record[0] not in wanted: continue
        role=wanted[record[0]];predicate=role=='predicate'
        spec=method_spec_record(data[n*12:(n+1)*12],len(md.methods),reg['genericInstsCount'],source='paramValueClaims.spec',offset=base+n*12)
        if spec[2 if predicate else 1]!=-1: continue
        inst=image.instantiations.resolve(spec[1 if predicate else 2])
        if len(inst.arguments)!=1: continue
        argument=pe.bytes_at_va(inst.arguments[0].type_pointer_va,16)
        if argument[10]!=primitive_kind or argument[11]&0x7f: continue
        selected[n]=role;records[n]=spec
    code=image.mapper.code_registration_summary(pe,image.code_registration);table_base=int(reg['genericMethodTable'],16)
    table=pe.bytes_at_va(table_base,reg['genericMethodTableCount']*16)
    # Close selected primitive arguments before interpreting relevant registration triples.
    candidates=generic_method_candidates(table,reg['genericMethodTableCount'],reg['methodSpecsCount'],set(selected),
                                         code['genericMethodPointersCount'],code['invokerPointersCount'],source='paramValueClaims.entries',offset=table_base)
    result={}
    for role,method in methods.items():
        rows=[row for row in candidates if selected[row['methodSpecIndex']]==role]
        need('paramValueClaims.'+role,'registeredEntries',1,len(rows))
        row=rows[0];pointer=pe.u64_at_va(int(code['genericMethodPointers'],16)+row['indices'][0]*8)
        if not pointer: raise ValueError('paramValueClaims.'+role+'.registeredPointer: null')
        result[role]={'methodIndex':method.index,'methodSpecIndex':row['methodSpecIndex'],
                      'pointerRva':pointer-pe.image_base,'parameterDefinition':definitions[role],
                      'runtimeReceiverOrMethodInfoOrExclusiveBodyProved':False}
    return result


def decode_rows(index,pointer,size):
    return [[int(row['va'],16)-index.pe.image_base,bytes.fromhex(row['bytes']).hex().upper()]
            for row in index._decode(pointer,size)]


def wrapper_view(image,context,spec,parameter_definition,index,*,primitive_name,primitive_type,primitive_kind,store_prefix):
    need('paramValueClaims.wrapper','holderType','Param<'+primitive_name+'> reference',spec['holderType'])
    need('paramValueClaims.wrapper','methodRoster',['GetValue','set___constValue__','set___idRef__','set___paramSource__'],spec['methods'])
    owner=qualified_owner(image,spec)
    need('paramValueClaims.wrapper','nongenericOwner',-1,owner.generic_container_index)
    fields=[f for f in image.metadata.fields_for(owner) if image.metadata.string(f.name_index)==spec['holder']]
    need('paramValueClaims.wrapper','holderCount',1,len(fields));holder=fields[0]
    holder_raw=types.type_record(image,context,holder.type_index)
    need('paramValueClaims.wrapper','instanceHolder',0,int.from_bytes(holder_raw[8:10],'little')&16)
    need('paramValueClaims.wrapper','sameParameterDefinition',parameter_definition,types.param_reference(image,holder_raw,primitive_kind))
    holder_offset=runtime_type_field_offsets(image.metadata,image.pe,image.registration,owner.index)[spec['holder']]
    methods={};slots={};windows=[]
    for name in spec['methods']:
        matches=[m for m in image.metadata.methods_for(owner) if image.metadata.string(m.name_index)==name]
        need('paramValueClaims.wrapper','namedMethodCount',1,len(matches));method=matches[0]
        getter=name=='GetValue';member=None if getter else name[6:-2]
        result,arguments=(('Beyond.Gameplay.Actions.Param`1<'+primitive_type+'>',21,True),[]) if getter else (
            ('void',1,False),[(primitive_type,primitive_kind,False) if member=='constValue' else ('int',8,False)])
        owned_method_abi(image,context,method.index,owner.index,result,arguments,'paramValueClaims.wrapper.'+name)
        pointer=image.method_pointer_va(method);size=5 if getter else index._extent(pointer)
        rows=decode_rows(index,pointer,size)
        if getter:
            shape(rows,['488b41'+bytes((holder_offset,)).hex(),'c3'],'paramValueClaims.wrapperGetter')
            need('paramValueClaims.wrapper','sameReturnDefinition',parameter_definition,types.param_reference(image,types.type_record(image,context,method.return_type),primitive_kind))
        else:
            need('paramValueClaims.wrapper','setterRows',9,len(rows));encoded=raw(rows[6]);prefix=store_prefix if member=='constValue' else b'\x89\x50'
            need('paramValueClaims.wrapper','storeSize',len(prefix)+1,len(encoded));need('paramValueClaims.wrapper','storeOpcode',prefix,encoded[:-1])
            slots[member]=encoded[-1]
            shape(rows,['4883ec28','488b41'+bytes((holder_offset,)).hex(),'4885c0',None,None,'cc',encoded.hex(),'4883c428','c3'],'paramValueClaims.wrapperSetter')
            need('paramValueClaims.wrapper','nonnullDestination',rows[6][0],target(rows[3],b'\x75'));target(rows[4],b'\xe8')
        methods[name]=method.index;windows.append(window(rows))
    need('paramValueClaims.wrapper','members',{'constValue','idRef','paramSource'},set(slots))
    need('paramValueClaims.wrapper','distinctMemberSlots',3,len(set(slots.values())))
    return {'holderOffset':holder_offset,'slots':slots,'methods':methods,'windows':windows,
            'runtimeReceiverAndStoredCursorJoinProved':False}


def window(rows):
    encoded=b''.join(raw(row) for row in rows)
    return {'startRva':rows[0][0],'endRva':rows[-1][0]+len(raw(rows[-1])),
            'sha256':hashlib.sha256(encoded).hexdigest().upper(),'instructionCount':len(rows)}


def declarations(image,context,spec,names):
    owner=qualified_owner(image,spec);defaults=field_defaults(image.metadata);result={}
    fields=list(image.metadata.fields_for(owner))
    for name in names:
        matches=[f for f in fields if image.metadata.string(f.name_index)==name]
        need('paramValueClaims.declarations','namedFieldCount',1,len(matches));field=matches[0]
        record=types.type_record(image,context,field.type_index);types.ordinary(record,8,'paramValueClaims.declaredInt32')
        need('paramValueClaims.declarations','staticLiteral',0x50,int.from_bytes(record[8:10],'little')&0x50)
        types.ordinary(types.type_record(image,context,defaults[field.index][0]),8,'paramValueClaims.defaultInt32')
        result[name]={'value':constant_value(image.metadata,defaults,field),'fieldIndex':field.index}
    return result


