"""Own nominal Unity Color layout; actual parent bytes select its wire source.

Four ordinary Single fields occupy managed16 with no references or padding.
This declaration does not provide an input width, quaternion alias, wrapper
header, factory, parent frame or runtime color semantics. A separate actual
capture/Advance/store program must supply any raw16 operation.
"""
import json

TYPE='UnityEngine.Color'
LABEL='unityColorSource'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def layout(image,ctx):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md=image.metadata;td=ctx.index.types[TYPE]
    need('plain-nonenumeration-current-value',ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)
        and ctx.parent(TYPE)=='System.ValueType'and td.generic_container_index<0)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[(md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:])for f in fields]
    need('own-rgba-Single-fields',actual==[(axis,'float',16+4*i)for i,axis in enumerate('rgba')])
    for field in fields:scalar.ordinary(image,ctx.type_pointer(field.type_index),12,LABEL+'.Single')
    need('bounded-current-size-row',0<=td.index<image.registration['typeDefinitionsSizesCount'])
    sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*td.index)
    need('independent-boxed-and-native16',(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4))==(32,16))
    return dict(typeName=TYPE,typeDefinition=td.index,fields=actual,managedBytes=16,boxedBytes=32,
        referenceLaneOffsets=[],paddingByteRanges=[],wireReadAdmitted=False,managedSizeUsedForWireWidth=False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _publication_gate(image,pins);nominal=layout(image,NativeReferenceContext(image));_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.unity-color-layout.v1',status='validated-layout-only',
        nativeInputs=pins,layout=nominal,wireGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Current independent ordinary Color/r/g/b/a Single declarations and boxed/native layout.',
            structuralOnly='Stored four-Single representation; neither source bytes nor runtime meaning.',
            unresolved=['actual parent capture/Advance/whole field/local/frame','wrapper framing and factory','enclosing owner/physical EOF']))))
