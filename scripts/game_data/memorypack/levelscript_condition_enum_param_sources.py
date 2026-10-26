"""Explicit enum-valued Param sources; carrier and backing select no adapter.

Each requested Param is first joined to its current wrapper's actual reference
holder and its sole closed class argument. Only an independently named enum
with signed Int32 or unsigned Byte backing enters the corresponding existing
byte/source prover. Lists, pointers and other value types remain outside this
owner. Source success grants no ordinary canonical adapter, outer field, union
or corpus admission, and does not alter the default enum-list domain.
"""
import json
import struct

LABEL='levelscriptConditionEnumParam'
SCHEMA='endfield.levelscript-condition-enum-param-source.v1'
PARAM='Beyond.Gameplay.Actions.Param`1'


def need(check,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+check+':'+str(detail)[:900])


def require_nominal(type_name,carrier,enum):
    """Pure joins over fresh raw type/field declarations; no native admission."""
    raw=bytes.fromhex(carrier.get('rawHex',''))
    definition=carrier.get('definition',{})
    declared=bytes.fromhex(definition.get('rawHex',''))
    need('actual-reference-Param-carrier',type(type_name)is str and type_name==carrier.get('name')
         and len(raw)==len(declared)==16 and raw[10:12]==bytes((21,0))
         and declared[10:12]==bytes((18,0))and definition.get('name')==PARAM)
    arguments=carrier.get('classArguments',[])
    need('sole-actual-closed-enum-argument',len(arguments)==1)
    argument=arguments[0];argument_raw=bytes.fromhex(argument.get('rawHex',''))
    td=enum.get('typeDefinition')
    need('current-own-ordinary-enum',type(td)is int and td>=0 and enum.get('isEnum')is True
         and enum.get('isValueType')is True and enum.get('parentType')=='System.Enum'
         and enum.get('genericContainerIndex')==-1 and enum.get('typeName')==argument.get('name')
         and len(argument_raw)==16 and argument_raw[10:12]==bytes((17,128))
         and int.from_bytes(argument_raw[:8],'little')==td)
    fields=enum.get('instanceFields',[])
    need('one-own-enum-backing-field',len(fields)==1 and fields[0].get('name')=='value__'
         and fields[0].get('owner')==enum['typeName']and fields[0].get('offset')==16)
    backing=fields[0];kinds={'int':(8,'i32',4),'byte':(5,'raw-u8',1)}
    need('independently-supported-enum-backing',backing.get('typeName')in kinds,backing.get('typeName'))
    kind,wire,width=kinds[backing['typeName']];backing_raw=bytes.fromhex(backing.get('rawHex',''))
    need('exact-ordinary-backing-record',len(backing_raw)==16 and backing_raw[10:12]==bytes((kind,128)))
    return dict(typeName=type_name,valueType=enum['typeName'],enumTypeDefinition=td,
        backingType=backing['typeName'],constantWireKind=wire,constantWireBytes=width,
        enumByteProfile=backing['typeName']=='byte',genericHeapLayoutInferred=False,
        canonicalAdapterAdmitted=False,parentFieldAdmitted=False)


def _nominal(image,ctx,type_name):
    from scripts.game_data.il2cpp.context import type_parameter_owner
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import scalar_param_native as scalar
    wrappers=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==type_name]
    need('one-current-requested-Param-wrapper',len(wrappers)==1,type_name)
    wrapper=wrappers[0];md=image.metadata
    holder=[f for f in md.fields_for(md.types[wrapper.type_definition])
            if md.string(f.name_index)=='__instance'and not ctx.field_attributes(f.type_index)&16]
    need('one-own-current-wrapper-reference-holder',len(holder)==1)
    fact=ctx.field(wrapper.name+'::__instance')
    need('exact-current-reference-holder',(fact[0],fact[1],fact[2])==(wrapper.name,type_name,16))
    pointer=ctx.type_pointer(holder[0].type_index)
    scalar.ordinary(image,pointer,21,LABEL+'.holder',reference=True)
    carrier=ContextSymbols(image).type(pointer)
    need('actual-owned-Param-definition',carrier.get('definition',{}).get('name')==PARAM)
    definition=ctx.index.types[PARAM];declared=bytes.fromhex(carrier['definition']['rawHex'])
    need('same-current-generic-Param-definition',len(declared)==16
         and int.from_bytes(declared[:8],'little')==definition.index)
    section=md.sections['genericContainers'];at=section.offset+definition.generic_container_index*16
    need('bounded-owned-Param-class-container',definition.generic_container_index>=0
         and section.offset<=at<=section.offset+section.size-16)
    owner,count,is_method,start=struct.unpack_from('<iiii',md.buf,at)
    need('one-owned-Param-class-parameter',(owner,count,is_method)==(definition.index,1,0)and start>=0)
    parameter_owner=type_parameter_owner(md.buf,start,[t.generic_container_index for t in md.types],source=LABEL)
    need('reciprocal-Param-class-parameter',parameter_owner.get('typeIndex')==definition.index
         and parameter_owner.get('ordinal')==0)
    arguments=carrier.get('classArguments',[])
    need('one-current-Param-class-argument',len(arguments)==1)
    value=arguments[0]['name']
    common=dict(wrapperName=wrapper.name,wrapperTypeDefinition=wrapper.type_definition,
        holderField=list(fact),carrier=carrier,
        classContainer=dict(ownerTypeDefinition=owner,arity=count,isMethod=is_method,startParameter=start,
            parameterOwner=parameter_owner))
    if not ctx.is_enum(value):
        return dict(**common,typeName=type_name,valueType=value,isEnum=False,enumClassificationProved=True)
    td=ctx.index.types[value]
    fields=[]
    for field in md.fields_for(td):
        if ctx.field_attributes(field.type_index)&16:continue
        name=md.string(field.name_index);fact=ctx.field(value+'::'+name)
        fields.append(dict(owner=value,name=name,typeName=fact[1],offset=fact[2],
            rawHex=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16).hex().upper()))
    enum=dict(typeName=value,typeDefinition=td.index,isEnum=ctx.is_enum(value),isValueType=ctx.is_value_type(value),
        parentType=ctx.parent(value),genericContainerIndex=td.generic_container_index,instanceFields=fields)
    identity=require_nominal(type_name,carrier,enum)
    return dict(**common,**identity,isEnum=True,enumClassificationProved=True,enumDeclaration=enum)


def derive_one(image,pins,*,type_name):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import primitive_param
    _publication_gate(image,pins)
    nominal=_nominal(image,NativeReferenceContext(image),type_name)
    if not nominal['isEnum']:
        _publication_gate(image,pins)
        return dict(typeName=type_name,valueType=nominal['valueType'],status='outside-enum-source-scope',
            nativeInputs=dict(pins),nominal=nominal,sourceAdmitted=False,canonicalAdapterAdmitted=False,
            parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    if type_name=='Beyond.Gameplay.Actions.Param`1<Beyond.GEnums.BitsetType>':
        from scripts.game_data.memorypack.levelscript_bitset_param_sources import derive as derive_bitset
        proof=derive_bitset(image,pins)
    else:
        options=dict(value_type=nominal['valueType'])
        if nominal['enumByteProfile']:options['enum_byte']=True
        proof=primitive_param.derive_parameter(image,pins,'int',**options)
    need('existing-own-complete-enum-Param-source',proof.get('status')=='validated')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-enum-param-source',
        nativeInputs=pins,typeName=type_name,valueType=nominal['valueType'],
        constantWireKind=nominal['constantWireKind'],constantWireBytes=nominal['constantWireBytes'],
        nominal=nominal,proof=proof,sourceAdmitted=True,canonicalAdapterAdmitted=False,
        formatterCallbackSelectionAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        runtimeInvocationObserved=False,
        evidenceBoundary=dict(exact=('Current own reference Param carrier, sole ordinary nominal enum argument and independently owned backing; complete selected warm factories/GetValue/setters/four reader paths, actual inline raw4 constant and separate auxiliary Int32/pooled path sources. No constant ReadUnmanaged MethodInfo is claimed.'
            if proof.get('sourceProfile')=='bitset-inline-enum-raw4'else
            'Current own reference Param carrier, sole ordinary nominal enum argument and independently owned backing; existing complete generated Param source, allocation/GetValue/setters, exact typed ReadUnmanaged source and pooled path.'),
            conditional='Ready coherent current classes/MethodInfos, normal compatible allocator/constructor/barrier ABI, initialized matching string pool, disjoint buffered Reader/output/frame. No runtime invocation is observed.',
            unresolved=['ordinary Param canonical registration/adapter and actual outer ReadValue joins',
                'generic heap fields outside the actual proved setters','outer record/union/corpus grammar']))))


def derive(image,pins,*,parameter_types):
    """Independent finite outcomes; caller selects actual parent Param names."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    need('bounded-distinct-explicit-Param-selection',isinstance(parameter_types,(list,tuple))
         and 0<len(parameter_types)<=256 and all(type(n)is str and n for n in parameter_types)
         and len(set(parameter_types))==len(parameter_types))
    _publication_gate(image,pins)
    owners=[]
    for name in sorted(parameter_types):
        try:owners.append(derive_one(image,pins,type_name=name))
        except(ValueError,KeyError,IndexError,TypeError)as error:
            owners.append(dict(typeName=name,status='pendingReview',reason=str(error)[:2200],
                sourceAdmitted=False,canonicalAdapterAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='finite-enum-param-source-outcomes',nativeInputs=pins,
        owners=owners,complete=sum(o['status']=='validated-conditional-enum-param-source'for o in owners),
        outsideScope=sum(o['status']=='outside-enum-source-scope'for o in owners),
        held=[dict(typeName=o['typeName'],reason=o['reason'])for o in owners if o['status']=='pendingReview'],
        canonicalAdapterAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
