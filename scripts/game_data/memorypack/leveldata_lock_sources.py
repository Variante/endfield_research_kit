"""Current Lock2/SingleLock18 under an explicit LangKey/string-list profile."""
TYPE='Beyond.Gameplay.InteractiveLockData'
SINGLE='Beyond.Gameplay.InteractiveSingleLockData'
LANG='Beyond.LangKey'
STRINGS='System.Collections.Generic.List`1<string>'
SINGLES='System.Collections.Generic.List`1<'+SINGLE+'>'
CAP='story-interactive-lock'
SINGLE_CAP='story-interactive-single-lock'
LIMIT=4096
PLAN=(('locks',SINGLES,'single-lock-list'),('logicIdGlobal','ulong','scalar64-bits'))
SINGLE_PLAN=(('interactiveId','ulong','scalar64-bits'),('miniGameIds',STRINGS,'pooled-string-list'),
 ('optionUnlock',LANG,'lang-key'),('overrideViewConfigHash','string','byte-payload'),
 ('panelBtnTxt',LANG,'lang-key'),('panelDecoTxt',LANG,'lang-key'),('panelDesc',LANG,'lang-key'),
 ('panelDescTitle',LANG,'lang-key'),('panelIconSpritePath','string','byte-payload'),('panelTextConfigured','bool','bool-byte'),
 ('panelTitle',LANG,'lang-key'),('questId','string','byte-payload'),('seamlessBlendToPerf','bool','bool-byte'),
 ('skipSubmitBoard','bool','bool-byte'),('submitId','string','byte-payload'),('toastFailed',LANG,'lang-key'),
 ('toastSuccess',LANG,'lang-key'),('unlockType','Beyond.GEnums.InteractiveUnlockType','scalar32'))


def bind_list(pins,join,child,capability):
    from scripts.game_data.memorypack.leveldata_extended_record_sources import STRING_CAP,bind_strings
    if capability==STRING_CAP:return bind_strings(pins,join,child,capability)
    cap=child.get('capabilities',{}).get(capability,{});usage=join['typedRequest']
    if (capability!=SINGLE_CAP or child.get('nativeInputs')!=pins or join['typeName']!=SINGLES
            or cap.get('typeName')!=SINGLES or cap.get('elementType')!=SINGLE
            or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','actualCallbackEqualsProvedChildRequired'))
            or type(cap.get('countLimit'))is not int or cap['countLimit']!=LIMIT
            or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[SINGLES]
            or(cap.get('readerMethodDefinition'),cap.get('sourceTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])):
        raise ValueError('currentLock.exact-single-list-parent')
    return dict(fieldName=join['fieldName'],typeName=SINGLES,capability=SINGLE_CAP,countLimit=LIMIT,
        readerMethodDefinition=cap['readerMethodDefinition'],sourceTargetRva=cap['sourceTargetRva'],
        actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,host):
    import json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar,pooled_source_helper
    from scripts.game_data.memorypack import leveldata_lang_key_components as language
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.leveldata_extended_record_sources import STRING_CAP
    from scripts.game_data.memorypack.pooled_string_list_sources import validate_string_components
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    need=lambda k,e,a:scalar.need('currentLock',k,e,a)
    need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrappers={w.wrapped_type:w for w in derive_from_image(image).values()if w.wrapped_type in(TYPE,SINGLE)}
    generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in(SINGLE,TYPE)])
    strings=validate_string_components(image,_load('levelscript_pooled_string_list_native.json',pins))
    need('independent-pooled-string-wire',(5,4,8),(strings['stringFormatterSlot'],strings['wireBytes'],strings['managedReferenceBytes']))
    records={};caps={};lang=None
    for name,result in zip((SINGLE,TYPE),generated['owners'],strict=True):
        need('complete-generated-source:'+name,'complete-reader-source-proved',result['status']if result['status']=='complete-reader-source-proved'else result)
        source=result['proof'];plan=SINGLE_PLAN if name==SINGLE else PLAN
        need('exact-nominal-plan:'+name,[(n,t)for n,t,k in plan],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
        requests={};children={};collections={};values={};value_children={};proofs={};collection_caps={}
        for read in source['orderedSourceReads']:
            declared=read['declaredType'];index=read['memberIndex']
            if declared not in(LANG,STRINGS,SINGLES):continue
            usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='currentLock.child');requests[index]=usage
            if declared==LANG:
                if lang is None:lang=language.derive(image,pins,typed_request=usage,source_target=base+read['sourceTargetRva'])
                values[LANG]=(language.CAP,'lang-key',language.CAP);value_children[index]=lang
                continue
            element='string'if declared==STRINGS else SINGLE
            listing=reference_list(image,pins,typed_request=usage,call_target=base+read['sourceTargetRva'],element_type=element,count_limit=LIMIT)
            witness=listing['witnessComponent'];key=STRING_CAP if declared==STRINGS else SINGLE_CAP
            if declared==STRINGS:
                cap=dict(closedListType=STRINGS,elementType='string',elementValueType=False,nullable=True,positiveCountsAdmitted=True,
                    elementGrammarAdmitted=True,countLimit=LIMIT,actualCallbackEqualsPooledStringRequired=True,
                    packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=witness['callTargetRva'])
            else:
                cap=dict(typeName=SINGLES,elementType=SINGLE,nullable=True,positiveCountsAdmitted=True,countLimit=LIMIT,
                    actualCallbackEqualsProvedChildRequired=True,readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=witness['callTargetRva'])
            collections[declared]=(key,'pooled-string-list'if declared==STRINGS else'single-lock-list',key)
            children[index]=dict(nativeInputs=pins,capabilities={key:cap});collection_caps[key]=cap
            proofs[read['fieldName']]=dict(source=read,typedRequest=usage,collection=listing)
        program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},
            typed_requests=requests,collections=collections,collection_children=children,collection_binder=bind_list,
            typed_values=values,value_children=value_children,value_binder=language.bind_value if values else None)
        need('complete-current-wire-program:'+name,[],pending)
        need('exact-current-wire-order:'+name,[(n,k)for n,t,k in plan],[(r['fieldName'],r['kind'])for r in program['reads']])
        pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
        need('whole-owned-original:'+name,True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
        need('same-owned-GetValue:'+name,source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
        need('same-owned-slot5:'+name,source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
        pooled={str(r['memberIndex']):pooled_source_helper.validate_on_image(image,base+r['sourceTargetRva'],pins)
            for r in source['orderedSourceReads']if r['kind']=='byte-payload'}
        enums={}
        if name==SINGLE:
            enum=SINGLE_PLAN[-1][1];need('exact-enum-parent','System.Enum',ctx.parent(enum));field=ctx.field(enum+'::value__')
            need('exact-enum-storage',True,field[1]in('int','uint'));enums['unlockType']=dict(typeName=enum,backing=field[1],field=field)
        caps[name]=dict(typeName=name,memberCount=len(plan),program=program,collections=collection_caps,enumBackings=enums,
            nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,wholeGrammarAdmitted=False,countLimit=LIMIT,
            actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
        records[name]=dict(source=source,pair=pair,adapter=adapter,pooled=pooled,children=proofs)
    field,parent=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']=='interactiveLockData')
    need('exact-current-host-list','System.Collections.Generic.List`1<'+TYPE+'>',field['typeName'])
    usage=derive_typed_usage_context(image,parent['typedUsage']['instruction']-base,label='currentLock.hostParent')
    listing=reference_list(image,pins,typed_request=usage,call_target=parent['sourceTarget'],element_type=TYPE,count_limit=LIMIT)
    return json.loads(json.dumps(dict(nativeInputs=pins,records=records,capabilities=caps,langKey=lang,pooledStrings=strings,
        parent=dict(field=field,source=parent,typedRequest=usage,collection=listing),
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
