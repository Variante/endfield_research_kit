"""Bounded current FunctionArea-specific graph; unknown child routes stay closed."""
import json

from scripts.game_data.memorypack.leveldata_function_specific_sources import TYPE,CAP,CHILDREN
from scripts.game_data.memorypack.leveldata_function_specific_leaves import TAGS,PLANS
from scripts.game_data.memorypack.leveldata_function_specific_complex_sources import TAGS as COMPLEX_TAGS

PROFILES={'basic14':TAGS,'complex4':COMPLEX_TAGS,'all18':tuple(CHILDREN)}

PARENT='Beyond.Gameplay.LevelFunctionAreaData'
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
LIST_CAP='story-function-specific-list'
COUNT_LIMIT=4096
NODE_LIMIT=16384


def bind_parent(pins,read,usage,collection):
    witness=collection.get('witnessComponent',{})
    spec=usage.get('methodSpec')
    if (collection.get('nativeInputs')!=pins
            or collection.get('status')!='validated-bounded-reference-list-induction'
            or collection.get('elementType')!=TYPE or collection.get('countRange')!=[-1,COUNT_LIMIT]
            or collection.get('nullable')is not True or collection.get('freshListsAdmitted')is not True
            or any(collection.get(k)is not False for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted'))
            or read.get('fieldName')!='specificDatas'or read.get('declaredType')!=LIST
            or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[LIST]
            or witness.get('elementType')!=TYPE or witness.get('callTargetRva')!=read.get('sourceTargetRva')
            or witness.get('typedRequest',{}).get('methodSpec')!=spec
            or type(read.get('sourceTargetRva'))is not int or read['sourceTargetRva']<=0
            or not isinstance(spec,(list,tuple))or not spec or type(spec[0])is not int or spec[0]<0):
        raise ValueError('storyFunctionSpecific.exact-current-list-parent')
    return dict(ownerType=PARENT,fieldName='specificDatas',typeName=LIST,capability=LIST_CAP,elementType=TYPE,
        readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=read['sourceTargetRva'],
        countLimit=COUNT_LIMIT,nullable=True,positiveCountsAdmitted=True,
        actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,*,profile='complex4'):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar
    from scripts.game_data.memorypack.leveldata_function_specific_sources import derive_transport
    from scripts.game_data.memorypack.leveldata_function_specific_leaves import derive as derive_leaves
    from scripts.game_data.memorypack.leveldata_function_specific_complex_sources import derive as derive_complex
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
    need=lambda k,e,a:scalar.need('storyFunctionSpecificComponents',k,e,a)
    need('finite-explicit-profile',True,type(profile)is str and profile in PROFILES)
    _publication_gate(image,pins);base=image.pe.image_base
    transport=derive_transport(image,pins);proofs={};records={};capabilities={};routes={};tags=PROFILES[profile]
    for key,derive_child in(('basic',derive_leaves),('complex',derive_complex)):
        if(profile=='complex4'and key=='basic')or(profile=='basic14'and key=='complex'):continue
        proof=derive_child(image,pins);proofs[key]=proof;records.update(proof['records']);capabilities.update(proof['capabilities'])
    inherited={row['wrapperName']:row for row in transport['inheritedConversions']}
    for tag in tags:
        route,=[row for row in transport['programs']if row['tag']==tag];name=CHILDREN[tag]
        selected=capabilities[name];source=records[name]['source']
        need('same-closed-concrete-wrapper:'+str(tag),(route['wrapperName'],name),(source['wrapperName'],source['wrappedType']))
        need('same-owned-concrete-callback:'+str(tag),route['wrapperName'],selected['concreteFormatterMethod'][1].split('+',1)[0])
        conversion=inherited[route['wrapperName']]
        # The concrete typed GetValue is a different interface method. The
        # actual base adapter calls the inherited base GetValue. Join their
        # shared base holder and the independently proved cache/constructor
        # identity, rather than equating those distinct declarations.
        life=source['lifecycle'];coherent=life.get('coherentGetter',{});construction=source.get('constructedGetterJoin',{})
        need('same-actual-base-holder:'+str(tag),(TYPE,16),tuple(life['baseHolder'][1:]))
        need('same-proved-cache-base-holder:'+str(tag),life['baseHolder'],coherent.get('baseHolder'))
        need('same-reference-cache-return:'+str(tag),True,coherent.get('coherentNonNullSamePointerReturn'))
        need('base-holder-constructed-before-reader:'+str(tag),True,16 in construction.get('constructedReferenceOffsets',[]))
        need('no-unproved-inherited-cache-alias:'+str(tag),False,construction.get('inheritedCacheCoherenceAssumed'))
        need('actual-inherited-conversion-holder:'+str(tag),(TYPE,16),(conversion['holder']['declaredType'],conversion['holder']['offset']))
        routes[str(tag)]=dict(tag=tag,typeName=name,wrapperName=route['wrapperName'],wrapperNullAdmitted=True,
            actualWrapperCallbackEqualsProvedConcreteRequired=True,capability=selected)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==PARENT]
    parent=generated_reader_sources.derive(image,pins,wrapper.name)
    read,=[r for r in parent['orderedSourceReads']if r['fieldName']=='specificDatas']
    usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyFunctionSpecific.parent')
    listing=reference_list(image,pins,typed_request=usage,call_target=base+read['sourceTargetRva'],element_type=TYPE,count_limit=COUNT_LIMIT)
    binding=bind_parent(pins,read,usage,listing)
    cap=dict(typeName=TYPE,profileAdmitted=True,nullAdmitted=True,positiveAdmitted=True,wholeGrammarAdmitted=False,
        actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
        profileId=profile,admittedRouteTags=list(tags),routes=routes,nodeLimit=NODE_LIMIT,countLimit=COUNT_LIMIT,
        listParent=binding,concreteOriginalAdapterUsed=False)
    from scripts.game_data.codecs.leveldata.current_function_specific import validate
    validate(cap)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.story-function-specific-components.v2',
        status='validated-finite-current-specific-profile',nativeInputs=pins,transport=transport,children=proofs,
        parent=dict(source=parent,read=read,typedRequest=usage,collection=listing,binding=binding),capability=cap,
        wholeUnionAdmitted=False,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False,
        evidenceBoundary=dict(exact='Own current union/table/typed-wrapper source and inherited base conversion, complete finite concrete wrapper grammars and actual FunctionArea.specificDatas list source/count induction.',
            conditional='Initially null positive union output, matching compatible ready base/concrete/list callbacks, coherent contexts/cache/holder, buffered disjoint storage and normal helpers/barriers. The flat profile separately bounds list counts and total union nodes.',
            unresolved=['concrete routes outside the selected finite profile','actual outer LevelData parent/owner operation',
                'runtime execution/provider selection','whole owner/physical EOF']))))
