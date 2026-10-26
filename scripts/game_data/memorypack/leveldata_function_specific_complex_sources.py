"""Four finite complex SpecificData wrappers and their ordinary entry child.

Wrapper wire grammars do not select the base union or its inherited GetValue
conversion. The SceneToast entry has a separate ordinary original adapter.
Actual parent callbacks, collection storage and live provider selection stay
conditional; unsupported Condition routes still stop the finite child cursor.
"""
import json

from scripts.game_data.memorypack.leveldata_function_specific_sources import CHILDREN
from scripts.game_data.memorypack.leveldata_extended_record_sources import STRINGS,STRING_CAP
from scripts.game_data.memorypack import leveldata_lang_key_components as language
from scripts.game_data.memorypack import leveldata_condition_components as conditions
from scripts.game_data.memorypack import leveldata_vector3_list_sources as vectors

TAGS=(9,14,15,16)
ENTRY='Beyond.Gameplay.LevelFunctionAreaData+SceneToastRuntimeEntry'
ENTRIES='System.Collections.Generic.List`1<'+ENTRY+'>'
ENTRY_LIST_CAP='story-scene-toast-entry-list'
ENTRY_CAP='story-scene-toast-entry'
ULONGS='System.Collections.Generic.List`1<ulong>'
ULONG_CAP='story-uint64-list'
LIMIT=4096
PLANS={
 CHILDREN[9]:(('entityTypes','Beyond.Gameplay.Core.HideEntityTypeMask','scalar32'),
  ('logicIdWhitelist',ULONGS,'uint64-list'),('npcTypes','Beyond.Gameplay.Core.HideNpcTypeMask','scalar32'),
  ('proxyWhitelist',STRINGS,'pooled-string-list')),
 CHILDREN[14]:(('conditionalEntries',ENTRIES,'scene-entry-list'),('depthText',language.TYPE,'lang-key'),
  ('mainTitle',language.TYPE,'lang-key'),('priority','Beyond.Gameplay.ELevelAreaPriority','scalar32'),
  ('saveId','int','scalar32'),('subTitle',language.TYPE,'lang-key')),
 CHILDREN[15]:(('enterSummonRadius','float','float32-bits'),('inOutZoneTolerance','float','float32-bits'),
  ('specifyTeammatePositions','bool','bool-byte'),('specifyTeammateRotations','bool','bool-byte'),
  ('teammateLookAtPoints',vectors.LIST,'vector3-list'),('teammatePositions',vectors.LIST,'vector3-list')),
 CHILDREN[16]:(('defaultOn','bool','bool-byte'),('npcProxyIds',STRINGS,'pooled-string-list'),
  ('showEnterToast','bool','bool-byte'),('showLeaveToast','bool','bool-byte')),
 ENTRY:(('condition',conditions.TYPE,'condition-runtime'),('depthText',language.TYPE,'lang-key'),
  ('entryLocalId','int','scalar32'),('mainTitle',language.TYPE,'lang-key'),('saveId','int','scalar32'),
  ('subTitle',language.TYPE,'lang-key')),
}
OPERATIONS={'uint64-list':ULONG_CAP,'pooled-string-list':STRING_CAP,'vector3-list':vectors.CAP,
 'scene-entry-list':ENTRY_LIST_CAP,'condition-runtime':conditions.CAP,'lang-key':language.CAP}


def bind_program(name,source,program,pending):
    plan=PLANS.get(name)
    if (plan is None or pending or not isinstance(program,dict)or source.get('wrappedType')!=name
            or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in plan]
            or type(program.get('memberCount'))is not int or program['memberCount']!=len(plan)
            or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
            or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
                (i,n,k,OPERATIONS.get(k))for i,(n,t,k)in enumerate(plan)]
            or program.get('requiredCapabilities')!=sorted({OPERATIONS[k]for n,t,k in plan if k in OPERATIONS})
            or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]!=[
                (n,t,OPERATIONS[k])for n,t,k in plan if k in OPERATIONS]):
        raise ValueError('storySpecificComplex.exact-finite-program:'+str(name))


def bind_collection(pins,join,child,capability):
    from scripts.game_data.memorypack.leveldata_extended_record_sources import bind_strings
    if capability==STRING_CAP:return bind_strings(pins,join,child,capability)
    allowed={ULONG_CAP:(ULONGS,'ulong',8),vectors.CAP:(vectors.LIST,vectors.TYPE,12),ENTRY_LIST_CAP:(ENTRIES,ENTRY,None)}
    if capability not in allowed:raise ValueError('storySpecificComplex.closed-list-capability')
    typename,element,width=allowed[capability];cap=child.get('capabilities',{}).get(capability,{})
    usage=join['typedRequest']
    if (child.get('nativeInputs')!=pins or join['typeName']!=typename or cap.get('typeName')!=typename
            or cap.get('elementType')!=element or type(cap.get('countLimit'))is not int or cap['countLimit']!=LIMIT
            or cap.get('countRange')!=[-1,LIMIT]
            or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','actualCallbackEqualsProvedChildRequired'))
            or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[typename]
            or(cap.get('packableReaderMethodDefinition'),cap.get('packableReaderTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])
            or(width is not None and(type(cap.get('elementWireBytes'))is not int or cap['elementWireBytes']!=width
                or cap.get('initiallyNullListRequired',cap.get('initiallyNullOutputRequired'))is not True))
            or(capability==ENTRY_LIST_CAP and cap.get('finiteElementProfileAdmitted')is not True)):
        raise ValueError('storySpecificComplex.exact-list-parent:'+capability)
    return dict(fieldName=join['fieldName'],typeName=typename,capability=capability,countLimit=LIMIT,
        readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],
        actualCallbackEqualsProvedChildRequired=True,finiteElementProfileAdmitted=True)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.levelscript_collection_sources import derive_ulong_list_component
    from scripts.game_data.memorypack.pooled_string_list_sources import validate_string_components
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    need=lambda k,e,a:scalar.need('storySpecificComplex',k,e,a)
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in PLANS}
    need('exact-five-current-wrappers',set(PLANS),set(wrappers))
    names=(ENTRY,*(CHILDREN[tag]for tag in TAGS))
    generated=generated_reader_sources.derive_many(image,pins,[wrappers[name].name for name in names])
    condition=conditions.derive(image,pins)
    strings=validate_string_components(image,_load('levelscript_pooled_string_list_native.json',pins))
    need('independent-pooled-string-element',(5,4,8),(strings['stringFormatterSlot'],strings['wireBytes'],strings['managedReferenceBytes']))
    lang=None;caps={};records={};entry_adapter=None
    for name,row in zip(names,generated['owners'],strict=True):
        need('complete-owned-source:'+name,'complete-reader-source-proved',row['status']if row['status']=='complete-reader-source-proved'else row)
        source=row['proof'];plan=PLANS[name]
        need('exact-owned-nominal-order:'+name,[(n,t)for n,t,k in plan],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
        requests={};collections={};children={};value_children={};values={};references={};reference_children={};child_proofs={};child_caps={}
        for read in source['orderedSourceReads']:
            index=read['memberIndex'];kind=plan[index][2];declared=read['declaredType']
            if kind not in OPERATIONS:continue
            usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storySpecificComplex.actualChild')
            requests[index]=usage;target=base+read['sourceTargetRva'];key=OPERATIONS[kind]
            if kind=='lang-key':
                if lang is None:lang=language.derive(image,pins,typed_request=usage,source_target=target)
                values[language.TYPE]=(language.CAP,'lang-key',language.CAP);value_children[index]=lang
                child_caps[language.CAP]=lang['capabilities'][language.CAP];continue
            if kind=='condition-runtime':
                references[conditions.TYPE]=(conditions.CAP,'condition-runtime',conditions.CAP)
                reference_children[conditions.TYPE]=dict(nativeInputs=pins,capabilities={conditions.CAP:condition['capability']})
                child_caps[conditions.CAP]=condition['capability'];continue
            if kind=='uint64-list':
                proof=derive_ulong_list_component(image,pins,typed_request=usage,call_target=target,count_limit=LIMIT)
                cap={k:v for k,v in proof.items()if k not in('proof','typedRequest','typedBinding','closedCarrier','evidenceBoundary')}
            elif kind=='vector3-list':
                proof=vectors.derive(image,pins,typed_request=usage,call_target=target);cap=proof['capability']
            else:
                element='string'if kind=='pooled-string-list'else ENTRY
                proof=reference_list(image,pins,typed_request=usage,call_target=target,element_type=element,count_limit=LIMIT)
                witness=proof['witnessComponent']
                if kind=='pooled-string-list':
                    cap=dict(closedListType=STRINGS,elementType='string',elementValueType=False,nullable=True,positiveCountsAdmitted=True,
                        elementGrammarAdmitted=True,countLimit=LIMIT,actualCallbackEqualsPooledStringRequired=True,
                        packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=witness['callTargetRva'])
                else:
                    need('ordinary-entry-source-before-list',True,ENTRY in caps)
                    cap=dict(typeName=ENTRIES,elementType=ENTRY,nullable=True,positiveCountsAdmitted=True,countLimit=LIMIT,
                        countRange=[-1,LIMIT],finiteElementProfileAdmitted=True,actualCallbackEqualsProvedChildRequired=True,
                        packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=witness['callTargetRva'])
                    child_caps[ENTRY_CAP]=caps[ENTRY]
            collections[declared]=(key,kind,key);children[index]=dict(nativeInputs=pins,capabilities={key:cap})
            child_caps[key]=cap;child_proofs[read['fieldName']]=dict(source=read,typedRequest=usage,component=proof)
        program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},
            typed_requests=requests,collections=collections,collection_children=children,collection_binder=bind_collection,
            references=references,reference_children=reference_children,reference_binder=conditions.bind_reference,
            typed_values=values,value_children=value_children,value_binder=language.bind_value)
        bind_program(name,source,program,pending)
        enums={}
        for field,declared,kind in plan:
            if kind!='scalar32'or declared=='int':continue
            need('nominal-enum-parent:'+declared,'System.Enum',ctx.parent(declared));value=ctx.field(declared+'::value__')
            need('nominal-enum32:'+declared,True,value[1]in('int','uint'))
            enums[field]=dict(typeName=declared,backing=value[1],field=list(value))
        need('full-owned-original-reference:'+name,True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
        if name==ENTRY:
            pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
            need('same-owned-entry-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
            need('same-owned-entry-slot5',source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
            entry_adapter=dict(pair=pair,adapter=adapter)
        caps[name]=dict(typeName=name,wrapperName=wrappers[name].name,memberCount=len(plan),program=program,enumBackings=enums,
            childCapabilities=child_caps,concreteFormatterMethod=source['lifecycle']['concreteFormatter']['method'],
            originalGetterMethod=source['lifecycle']['GetValue']['method'],nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,
            finiteFloatProfile=True,wrapperWireGrammarAdmitted=True,wholeGrammarAdmitted=False,
            actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
            concreteOriginalAdapterUsed=name==ENTRY,ordinaryAdapterAdmitted=name==ENTRY,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
        records[name]=dict(source=source,compiled=program,childProofs=child_proofs,enumBackings=enums)
    from scripts.game_data.codecs.leveldata.current_function_specific_complex import validate
    for name,cap in caps.items():validate(name,cap)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.story-function-specific-complex-children.v1',
        status='validated-finite-wrapper-child-grammars',nativeInputs=pins,records=records,capabilities=caps,
        entryAdapter=entry_adapter,langKey=lang,conditions=condition,pooledStringElements=strings,
        wholeUnionAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Four exact generated complex wrapper wire programs, separate complete ordinary SceneToast entry adapter, typed list/count/element and managed LangKey transfers, finite Condition child graph and every actual parent MethodSpec/source/local/store/frame join.',
            conditional=__doc__,unresolved=['base SpecificData union dispatch and inherited conversion','enclosing FunctionArea list/LevelData owner',
                'runtime formatter/provider selection','whole owner/physical EOF']))))
