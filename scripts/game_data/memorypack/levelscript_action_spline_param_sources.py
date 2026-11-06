"""SplinePtr's own signed Int32 source inside a complete reference Param.

A pointer suffix grants no UInt64 representation. The actual closed nominal,
sole id field, ReadUnmanaged source, EAX transfer and enclosing four paths are
proved separately from the outer canonical reference callback.
"""
import json
from scripts.game_data.memorypack.levelscript_condition_param_sources import need

VALUE='Beyond.Gameplay.Core.SplinePtr'
TYPE='Beyond.Gameplay.Actions.Param`1<'+VALUE+'>'
SCHEMA='endfield.actionmap-spline-param-source.v1'


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.current_reference_param_sources import derive_value4_parent
    from scripts.game_data.memorypack.nominal_int32_value_sources import derive as derive_value
    from scripts.game_data.memorypack.levelscript_condition_param_sources import _reader,_reference_join,_capability
    from scripts.game_data.codecs.levelscript.current_spline_param import validate
    _publication_gate(image,pins)
    parent=derive_value4_parent(image,pins,value_type=VALUE)
    usage=parent['typedRead'];ctx=NativeReferenceContext(image)
    argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
    request=dict(usage,fullTypeName=VALUE,typeDefinition=ctx.index.types[VALUE].index,
        argumentRawHex=image.pe.bytes_at_va(argument.type_pointer_va,16).hex().upper(),
        methodOwner='MemoryPack.MemoryPackReader',register='rdx',typeKind=17)
    target=parent['programs'][0]['sourceCalls']['constValue']
    source=derive_value(image,pins,context=request,source_target=target)
    need('own-Spline-id-field',source['proof']['fieldName']=='id'
        and source['proof']['field']==[VALUE,'int',16])
    need('own-Spline-whole-EAX-setter-transfer',all(p['constantStoredBytes']==4
        and p['constantResultRegister']=='eax'and p['constantSetterArgumentRegister']=='edx'
        for p in parent['programs']))
    reference=_reference_join(image,pins,VALUE);reader=_reader(image,pins)
    need('own-Spline-reference-getter',parent['ownedMethods']['GetValue']['methodIndex']==reference['getterMethodDefinition'])
    cap=_capability(VALUE,'spline-id-int32',4,reader,reference['adapter'])
    cap.update(constantFields=[['id','int',16]],rawValueBitsPreserved=True,runtimeSplineResolutionProved=False)
    validate(cap);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,typeName=TYPE,
        capability=cap,proof=dict(parent=parent,constant=source,canonicalReference=reference,referenceReader=reader),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
