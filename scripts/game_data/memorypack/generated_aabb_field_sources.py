"""Finite Node.bounds AABB source/layout and exact raw16 local self-copy."""
TYPE='Beyond.AABB'
PARENT='Beyond.Simple2DBVHTreeNode'
FIELD='bounds'


def need(check,condition):
    if not condition:raise ValueError('generatedAabbField.'+check)


def owns_member(parent,field,type_name):
    return(parent,field,type_name)==(PARENT,FIELD,TYPE)


def layout(image,ctx):
    from scripts.game_data.memorypack.leveldata_aabb_value_sources import layout as nominal
    return dict(nominal(image,ctx),wireReadAdmitted=False)


def validate_local_copy(row,event,setter,source,locals_,*,register,width,offset):
    """Own full16 MOVDQA self-copy of the actual typed hidden RSP32 value."""
    from scripts.game_data.memorypack.buff_ec_profiles_native import raw
    nominal=event.get('nominalValueLayout',{});parent,_,field=setter.get('targetField','').rpartition('::')
    context=event.get('context')or{};carrier=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('exact-own-Node-AABB-self-copy',owns_member(parent,field,event.get('declaredType'))
        and event.get('fieldName')==FIELD and event.get('kind')=='value16:'+TYPE
        and event.get('sourceContextMode')is None and context.get('methodName')=='ReadUnmanaged'
        and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('fullTypeName')==TYPE
        and context.get('register')=='r8'and context.get('typeKind')==17
        and event.get('mode')=='typed-hidden-value'and event.get('resultAbi')=='hidden-local'
        and event.get('actualSourceProved')is True and type(event.get('wireBytes'))is int and event['wireBytes']==16
        and nominal.get('typeName')==TYPE and nominal.get('managedBytes')==setter.get('storedBytes')==16
        and nominal.get('fields')in([['min','UnityEngine.Vector2',16],['max','UnityEngine.Vector2',24]],
            [('min','UnityEngine.Vector2',16),('max','UnityEngine.Vector2',24)])
        and nominal.get('referenceLaneOffsets')==nominal.get('paddingByteRanges')==[]
        and type(nominal.get('typeDefinition'))is int and nominal['typeDefinition']==context.get('typeDefinition')
        and len(carrier)==16 and carrier[10:12]==bytes((17,128))and int.from_bytes(carrier[:8],'little')==nominal['typeDefinition']
        and source[:1]==('member',)and source[2:4]==(0,16)and(register,width,offset)==('xmm0',16,32)
        and raw(row)==bytes.fromhex('660f7f442420')
        and[locals_.get(offset+i)for i in range(16)]==[(source[1],i)for i in range(16)])
