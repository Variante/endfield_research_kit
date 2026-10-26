"""Selected declared Int32/enum call-lane transfers; caller authenticates native inputs."""
def check_int32_enum_transfer(metadata, pe, registration, source_index, call, register, parameter,
                           target_owner, target_method, *, source_field=None):
    from types import SimpleNamespace
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    try:
        context=NativeReferenceContext(SimpleNamespace(metadata=metadata,pe=pe,registration=registration))
        if type(source_index) is not int or not 0<=source_index<len(metadata.methods):
            raise ValueError('source declaration outside metadata')
        source=metadata.methods[source_index]; targets=call.get('resolved') or []
        if len(targets)!=1 or (targets[0].get('type'),targets[0].get('method'))!=(target_owner,target_method):
            raise ValueError('unique declared target required')
        target_index=targets[0].get('methodIndex')
        if type(target_index) is not int or not 0<=target_index<len(metadata.methods):
            raise ValueError('target declaration outside metadata')
        target=metadata.methods[target_index]
        if (metadata.type_full_name(metadata.types[target.declaring_type]),metadata.string(target.name_index))!=(target_owner,target_method):
            raise ValueError('target metadata identity differs')
        for method in (source,target):
            owner=metadata.types[method.declaring_type]
            if sum(metadata.type_full_name(td)==metadata.type_full_name(owner) for td in metadata.types)!=1:
                raise ValueError('ambiguous declared owner')
            if (method.generic_container_index>=0 or owner.generic_container_index>=0
                    or context.is_value_type(metadata.type_full_name(owner)) or context.type_name(method.return_type)!='void'):
                raise ValueError('nongeneric reference owner and ordinary Void method required')
            context.require_ordinary_kind(method.return_type,0x01)
        source_params=[p for p in metadata.parameters_for(source) if metadata.string(p.name_index)==parameter]
        if len(source_params)!=1:raise ValueError('unique source parameter required')
        lane=('rcx','rdx','r8','r9').index(register)-(0 if target.flags&0x10 else 1)
        target_params=list(metadata.parameters_for(target))
        if not 0<=lane<len(target_params):raise ValueError('matching selected enum parameter lane required')
        target_type=target_params[lane].type_index;kind=context.type_name(target_type)
        if (sum(metadata.type_full_name(td)==kind for td in metadata.types)!=1 or not context.is_enum(kind)
                or context.field(kind+'::value__')[1]!='int'):
            raise ValueError('unique selected Int32-backed target enum required')
        context.require_ordinary_kind(target_type,0x11)
        parameter_type=source_params[0].type_index
        if source_field is None:
            context.require_ordinary_kind(parameter_type,0x11)
            if context.type_name(parameter_type)!=kind:raise ValueError('matching selected source enum required')
            expected={'param:'+parameter,'low32(param:'+parameter+')'}
        else:
            context.require_ordinary_kind(parameter_type,0x12)
            owner,stored,offset=context.field(source_field)
            owners=[td for td in metadata.types if metadata.type_full_name(td)==owner]
            if context.type_name(parameter_type)!=owner or stored!='int' or len(owners)!=1 or type(offset) is not int or offset<16:
                raise ValueError('selected packet reference and Int32 field required')
            fields=[field for field in metadata.fields_for(owners[0]) if metadata.string(field.name_index)==source_field.partition('::')[2]]
            if len(fields)!=1:raise ValueError('unique selected packet field required')
            context.require_ordinary_kind(fields[0].type_index,0x08)
            expected={f'low32(param:{parameter}+{offset:#x})'}
        origin=(call.get('argumentOrigins') or {}).get(register)
        if origin not in expected:raise ValueError('complete incoming Int32 bits do not reach the call lane')
        return dict(status='validated',type=kind,argumentRegister=register,argumentOrigin=origin,
                    boundary='Declared Int32 representation and ordinary CFG transfer; no reference or runtime-execution claim.')
    except (KeyError,IndexError,ValueError,RuntimeError) as error:
        return dict(status='mismatched',detail=str(error)[:500])
