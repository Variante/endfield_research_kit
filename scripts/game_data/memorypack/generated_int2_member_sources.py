"""Finite ordinary Int2 source, parameter and whole-register member joins.

The dedicated child owns the actual ReadUnmanaged source. This gate ties its
RAX bits to the independently named two-Int32 setter parameter. The common
caller program still proves every transfer/store and the complete frame.
"""
import json

TYPE='UnityEngine.Vector2Int'
LABEL='generatedInt2Member'


def need(key,value):
    if not value:raise ValueError(LABEL+'.'+key)


def check_layout(layout):
    need('exact-two-Int32-layout',layout.get('schema')=='endfield.story-integer-vector-layout.v1'
        and layout.get('typeName')==TYPE and type(layout.get('typeDefinition'))is int
        and layout.get('managedBytes')==8 and layout.get('fieldCount')==2
        and layout.get('referenceLaneOffsets')==layout.get('paddingByteRanges')==[]
        and[(f.get('name'),f.get('declaredType'),f.get('managedOffset'),f.get('rawKind'))for f in layout.get('fields',[])]==
            [('m_X','int',0,8),('m_Y','int',4,8)])


def setter_layout(image,ctx,parameter_pointer):
    from scripts.game_data.memorypack.leveldata_integer_vector_layout import derive_layout
    layout=dict(derive_layout(image,type_pointer=parameter_pointer),typeDefinition=ctx.index.types[TYPE].index)
    check_layout(layout)
    return layout


def validate_event(event,setter):
    layout=setter.get('nominalValueLayout',{});check_layout(layout)
    raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('own-ordinary-Int2-parameter',len(raw)==16 and raw[10:12]==bytes((17,128))
        and int.from_bytes(raw[:8],'little')==layout['typeDefinition']and setter.get('storedBytes')==8)
    need('exact-typed-register-event',event.get('declaredType')==TYPE and event.get('kind')=='value8:'+TYPE
        and event.get('mode')=='typed-register-integer-vector'and event.get('resultAbi')=='rax'
        and event.get('wireBytes')==8 and event.get('actualSourceProved')is True
        and event.get('nominalIntegerLayout')==layout)
    context=event.get('context',{});bound=event.get('typedIntegerSourceBinding',{})
    need('actual-owned-rdx-context',context.get('methodOwner')=='MemoryPack.MemoryPackReader'
        and context.get('methodName')=='ReadUnmanaged'and context.get('register')=='rdx'
        and context.get('fullTypeName')==TYPE and context.get('typeKind')==17
        and context.get('typeDefinition')==layout['typeDefinition']and context.get('argumentRawHex','').upper()==raw.hex().upper()
        and isinstance(context.get('methodSpec'),(list,tuple))and len(context['methodSpec'])==3)
    need('same-independently-proved-register-source',bound.get('typeName')==TYPE
        and bound.get('typeDefinition')==layout['typeDefinition']and bound.get('readerMethodDefinition')==context['methodSpec'][0]
        and bound.get('targetRva')==event.get('sourceTargetRva')and bound.get('wireBytes')==bound.get('managedBytes')==8
        and bound.get('resultAbi')=='register-value'and bound.get('resultRegister')=='rax'and bound.get('rawInt32Axes')==['x','y'])
    return layout


def bind_event(event,setter,proof,*,base,pins):
    from scripts.game_data.memorypack.leveldata_int2_read_sources import bind
    need('same-selected-native-inputs',proof.get('nativeInputs')==pins)
    bound=bind(event['context'],base+event['sourceTargetRva'],proof,base=base)
    layout=setter.get('nominalValueLayout',{});check_layout(layout)
    child_layout=dict(proof['proof']['nominalLayout'],typeDefinition=proof['typeDefinition'])
    need('same-independent-setter-and-read-layout',json.loads(json.dumps(layout))==json.loads(json.dumps(child_layout)))
    event.update(mode='typed-register-integer-vector',resultAbi='rax',actualSourceProved=True,wireBytes=8,
        nominalIntegerLayout=layout,typedIntegerSourceBinding=bound)
    validate_event(event,setter)
    return dict(typeName=TYPE,layout=layout,typedSource=proof,sourceProgram=proof['proof']['actualProgram'],
        actualSourceProved=True,wireBytes=8,resultAbi='register-value-to-owned-field')
