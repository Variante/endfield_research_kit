"""Two finite Char root dictionaries with separately owned value grammars.

The source proves marker/count/key/reference insertion flow. Exact callback
selection is conditional on the selected ready provider. The containing root
must independently prove its initially-null out-local and full named transfer.
Ordered entries preserve duplicate keys; no mutable Dictionary is reconstructed.
"""
import json

from scripts.game_data.memorypack import char_perform_positive_dictionary_sources as source
from scripts.game_data.memorypack import char_perform_positive_dictionary_programs as paths

SCHEMA='endfield.char-static-dictionary-components.v1'
WIRE='char-static-reference-dictionary'
CAPABILITIES={source.OWNER+'<'+key+','+value+'>':'char-static-dictionary:'+source.OWNER+'<'+key+','+value+'>'
    for _,key,value in source.DOMAINS.values()}


def need(check,condition):
    if not condition:raise ValueError('charStaticDictionaryComponents.'+check)


def normalized(value):return json.loads(json.dumps(value))


def replay_source(actual,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.char_perform_root_sources import root_existing
    field=actual.get('fieldName');need('finite-own-source-field',field in source.DOMAINS)
    index,key,value=source.DOMAINS[field];typename=source.OWNER+'<'+key+','+value+'>'
    need('same-actual-source-identity',actual.get('schema')==source.SCHEMA and actual.get('nativeInputs')==pins
        and actual.get('status')=='validated-conditional-char-positive-dictionary-source'
        and(actual.get('typeName'),actual.get('keyType'),actual.get('valueType'))==(typename,key,value)
        and actual.get('resultAbi')=='void-byref-reference8'and actual.get('initiallyNullOutputRequired')is True
        and actual.get('callbackGrammarAdmitted')is False and actual.get('parentFieldAdmitted')is False
        and actual.get('wholeOwnerAdmitted')is False and type(actual.get('sourceTargetRva'))is int
        and actual['sourceTargetRva']>0)
    p=actual['proof'];context=p['context'];usage=context['typedRequest'];programs=p['programs']
    need('own-five-complete-source-programs',len(programs)==5 and programs[0].get('selectedBytes'))
    base=programs[0]['selectedBytes'][0][0]-actual['sourceTargetRva']
    need('exact-closed-MethodInfo-and-Reader-output',base>=2**32 and usage.get('tag')==6
        and tuple(usage.get(k)for k in('typeName','methodName','classArguments','methodArguments'))==
            (source.OWNER,'DeserializeV2',[key,value],[])
        and bytes.fromhex(usage.get('instructionHex',''))[:3]==bytes.fromhex('4c8b05')
        and len(bytes.fromhex(usage['instructionHex']))==7
        and len(usage.get('methodSpec',[]))==3 and usage['methodSpec'][1]>=0 and usage['methodSpec'][2]==-1
        and usage['methodSpec'][0]==actual.get('readerMethodDefinition')
        and(context.get('fieldName'),context.get('memberIndex'),context.get('typeName'))==(field,index,typename)
        and context.get('methodInfoRegister')=='r8'and context.get('resultAbi')==actual['resultAbi']
        and bytes.fromhex(context['readerParameterRawHex'])[10:12]==bytes((17,32))
        and bytes.fromhex(context['outputParameterRawHex'])[10:12]==bytes((21,32)))
    arguments=context.get('arguments',[]);need('two-own-nominal-carriers',len(arguments)==2)
    for fact,name,kind in zip(arguments,(key,value),(9 if key=='uint'else 14,18),strict=True):
        raw=bytes.fromhex(fact.get('rawTypeRecordHex',''))
        need('literal-own-argument-carrier',fact.get('typeName')==name and fact.get('typeKind')==kind
            and len(raw)==16 and raw[10:12]==bytes((kind,128 if kind==9 else 0))
            and(kind!=18 or int.from_bytes(raw[:8],'little')==fact.get('typeDefinition')))
    carrier=context.get('outputCarrier',{});owner=p.get('classContext',{})
    need('reciprocal-output-VAR-owners',carrier.get('definition',{}).get('name')==source.OWNER
        and[(a.get('parameterOwner',{}).get('typeIndex'),a.get('parameterOwner',{}).get('ordinal'))
            for a in carrier.get('classArguments',[])]==[(owner.get('definition'),0),(owner.get('definition'),1)])
    raw=regions(p['sourceWindows'],p['sourceRegions'],base,'char-static-dictionary')
    symbols={k:base+v for k,v in p['symbolRvas'].items()};selected=paths.symbols(raw,unsigned=key=='uint')
    need('actual-positive-helper-targets',all(symbols.get(k)==v for k,v in selected.items()))
    checked=[paths.program(raw,base+actual['sourceTargetRva'],p['readerOffsets'],symbols,count=n,unsigned=key=='uint')
        for n in(-1,0,1,2,3)]
    need('whole-source-paths-and-count-induction',normalized(checked)==programs
        and normalized(paths.induction(checked,unsigned=key=='uint',count_limit=p['induction']['maxCount']))==p['induction'])
    if key=='uint':
        header=p.get('header',{});need('own-called-one-byte-marker',isinstance(header,dict)
            and header.get('entryRva')==p['symbolRvas'].get('header'))
        marker_raw=regions(header['windows'],header['regions'],base,'char-static-marker')
        need('complete-marker-byte-program',normalized(paths.object_marker_program(marker_raw,
            base+header['entryRva'],p['readerOffsets']))==header.get('program'))
    else:need('inlined-marker-no-fabricated-helper',p.get('header')is None)
    parent=p['actualParent'];parent_raw=regions(parent['rootWindows'],parent['rootRegions'],base,'char-static-parent')
    root=root_existing(parent_raw,base+parent['method'][3],parent['fieldPlan'],offsets=p['readerOffsets'],source_targets={})
    need('actual-own-whole-root-source',normalized(root)==parent.get('program')and root['entryRspRestored']is True
        and parent.get('existingRootSourceProved')is True and parent.get('newRootSourceAdmitted')is False)
    event=root['fields'][index];call_at,encoded=parent['sourceInstruction'];encoded=bytes.fromhex(encoded)
    need('same-owned-field-MethodInfo-E8',event==parent.get('fieldEvent')and event.get('name')==field
        and event.get('mode')=='out8'and event.get('sourceTarget')==base+actual['sourceTargetRva']
        and usage==parent.get('context')and event['contextCells'][0]['instruction']==base+usage['instructionRva']
        and call_at==event['sourceCall']-base and len(encoded)==5 and encoded[0]==232
        and call_at+5+int.from_bytes(encoded[1:],'little',signed=True)==actual['sourceTargetRva']
        and parent.get('closedClass',{}).get('tag')==1 and parent['closedClass'].get('typeName')==typename)
    for role,helper in p['helpers'].items():
        need('same-owned-helper-entry',helper.get('entryRva')==p['symbolRvas'].get(role))
        regions(helper['windows'],helper['regions'],base,'char-static-'+role)
    return base


def value_dispatch(actual,child,callback,base):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.reference_adapter_sources import dispatch
    need('independent-own-reference-adapter',child.get('schema')=='endfield.reference-object-adapter-source.v1'
        and child.get('nativeInputs')==actual['nativeInputs']and child.get('typeName')==actual['valueType']
        and child.get('callbackBinding',{}).get('canonicalTargetRva')==callback
        and child['callbackBinding'].get('actualCallbackEqualsCanonicalRequired')is True
        and child['callbackBinding'].get('runtimeSelectionObserved')is False
        and child.get('canonicalRoutes',{}).get('symbolRvas',{}).get('main')==callback)
    helper=actual['proof']['helpers']['valueDispatch']
    need('actual-value-helper-entry',helper['entryRva']==actual['proof']['symbolRvas']['valueDispatch'])
    raw=regions(helper['windows'],helper['regions'],base,'char-static-reference-dispatch')
    symbols={k:base+v for k,v in child['canonicalRoutes']['symbolRvas'].items()}
    programs=[dispatch(raw,base+helper['entryRva'],symbols,**options)for options in(
        {},dict(create=False),dict(wrapper_null=True),dict(create=False,wrapper_null=True),dict(null=True))]
    return normalized(dict(sourceTargetRva=helper['entryRva'],callbackTargetRva=callback,programs=programs,
        actualPointerAliasInferred=False,callbackSelectionConditional=True,runtimeSelectionObserved=False))


def compose(actual,pins,key_evidence,child,*,key_dispatch=None,reference_dispatch=None):
    from scripts.game_data.memorypack import char_static_dictionary_callbacks as callbacks
    from scripts.game_data.memorypack.animation_custom_dictionary_components import replay_callback
    from scripts.game_data.memorypack.char_record_components import validate_component as record
    base=replay_source(actual,pins)
    if actual['keyType']=='uint':
        need('independent-unsigned-key-native-base',callbacks.verify_unsigned(key_evidence,pins)==base)
        need('same-complete-UInt32-dispatch',key_dispatch==callbacks.unsigned_dispatch(actual,key_evidence,base))
    else:
        need('independent-string-key-native-base',replay_callback(key_evidence,pins)==base
            and key_evidence.get('typeName')=='string'and key_dispatch is None)
    selected=record(child,pins);children=selected['capabilities'];primary=selected['capability'];cap=children[primary]
    need('own-complete-ordinary-reference-value',cap.get('typeName')==actual['valueType']
        and cap.get('valueStorageKind')=='reference8'and cap.get('ordinaryOriginalCallbackAdmitted')is True
        and cap.get('ordinaryOriginalReadValueAdmitted')is True and cap.get('wholeGrammarAdmitted')is True
        and cap.get('originalTypeDefinition')==actual['proof']['context']['arguments'][1]['typeDefinition'])
    callback=cap['canonicalAdapterTargetRva']
    if actual['keyType']=='uint':
        need('same-actual-whole-reference-dispatch',reference_dispatch==value_dispatch(actual,child['proof']['adapter'],callback,base))
    else:need('source-direct-slot5-no-invented-dispatch',reference_dispatch is None)
    required=sorted(set(selected['requiredExternalCapabilities'])|({'byte-payload'}if actual['keyType']=='string'else set()))
    capability=CAPABILITIES[actual['typeName']]
    primary_cap=dict(typeName=actual['typeName'],keyType=actual['keyType'],valueType=actual['valueType'],
        staticReaderMethodDefinition=actual['readerMethodDefinition'],sourceTargetRva=actual['sourceTargetRva'],
        resultAbi='void-byref-reference8',referenceBytes=8,wholeGrammarAdmitted=True,staticOutReferenceAdmitted=True,
        nullable=True,nullMarker=255,nullWireBytes=1,positiveMarkerDomain=[0,254],nativePositiveHeaderOneEnforced=False,
        countEncoding='signed-int32',countBytes=4,countLimit=actual['proof']['induction']['maxCount'],nodeLimit=16384,
        positiveCountsAdmitted=True,keyWireBytes=4,keyCallback=key_evidence,valueCapability=primary,
        valueCallbackTargetRva=callback,requiredChildCapabilities=children,requiredExternalCapabilities=required,
        callbackSelectionConditional=True,initiallyNullOutputRequired=True,clearExistingDictionaryAdmitted=False,
        orderedEntriesPreserved=True,duplicateKeysPreserved=True,finalMutableDictionaryReconstructed=False,
        actualRuntimeSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        conditions=key_evidence['conditions']+[__doc__])
    from scripts.game_data.memorypack.char_static_dictionary_codec import require_capability
    require_capability(capability,primary_cap)
    return dict(capability=capability,capabilities={**children,capability:primary_cap},requiredExternalCapabilities=required)


def validate_component(component,pins):
    need('own-current-complete-component',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-char-static-dictionary-components'
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    p=component['proof'];rebuilt=compose(p['source'],pins,p['keyEvidence'],p['child'],
        key_dispatch=p.get('keyDispatch'),reference_dispatch=p.get('referenceDispatch'))
    need('same-whole-capability-map',all(component.get(k)==v for k,v in rebuilt.items()))
    return rebuilt


def derive_on_children(image,pins,*,children,fields=tuple(source.DOMAINS),count_limit=4096):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import char_static_dictionary_callbacks as callbacks
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import derive_string
    _publication_gate(image,pins);actual=source.derive(image,pins,fields=fields,count_limit=count_limit)
    unsigned=string=None;owners=[]
    for row in actual['owners']:
        need('independent-value-component-required',row['valueType']in children)
        if row['keyType']=='uint':
            if unsigned is None:unsigned=callbacks.derive_unsigned(image,pins)
            evidence=unsigned;kd=callbacks.unsigned_dispatch(row,evidence,image.pe.image_base)
            child=children[row['valueType']];value=child['capabilities'][child['capability']]
            vd=value_dispatch(row,child['proof']['adapter'],value['canonicalAdapterTargetRva'],image.pe.image_base)
        else:
            if string is None:string=derive_string(image,pins)
            evidence=string;kd=vd=None;child=children[row['valueType']]
        joined=compose(row,pins,evidence,child,key_dispatch=kd,reference_dispatch=vd)
        component=dict(schema=SCHEMA,status='validated-conditional-char-static-dictionary-components',nativeInputs=pins,
            typeName=row['typeName'],**joined,proof=dict(source=row,keyEvidence=evidence,child=child,keyDispatch=kd,referenceDispatch=vd),
            parentFieldAdmitted=False,wholeOwnerAdmitted=False)
        validate_component(component,pins);owners.append(component)
    _publication_gate(image,pins);return normalized(dict(nativeInputs=pins,owners=owners))


def bind_root(root,pins,request,component,capability):
    from scripts.game_data.memorypack.char_current_root_sources import verify
    base=verify(root,pins);selected=validate_component(component,pins)
    need('same-selected-static-capability',capability==selected['capability'])
    cap=selected['capabilities'][capability];p=component['proof']['source'];field=p['fieldName'];index=source.DOMAINS[field][0]
    need('same-actual-root-request',root['requests'][index]==request and request.get('memberIndex')==index
        and request.get('fieldName')==field and request.get('typeName')==cap['typeName']and request.get('mode')=='out8'
        and request.get('initiallyNullOutputProved')is True and request.get('typedRequest')==p['proof']['context']['typedRequest']
        and request.get('sourceTargetRva')==cap['sourceTargetRva']
        and request['typedRequest']['methodSpec'][0]==cap['staticReaderMethodDefinition']
        and request.get('instruction')==p['proof']['actualParent']['sourceInstruction']
        and request.get('actualFieldTransfer')==p['proof']['actualParent']['fieldEvent']
        and request['actualFieldTransfer'].get('temporarySlot')in(103,127)
        and request['actualFieldTransfer'].get('sourceTarget')==base+cap['sourceTargetRva'])
    return dict(fieldName=field,typeName=cap['typeName'],capability=capability,memberIndex=index,
        readerMethodDefinition=cap['staticReaderMethodDefinition'],sourceTargetRva=cap['sourceTargetRva'],
        initiallyNullOutputProved=True,wholeReferenceFieldTransferProved=True,existingRootFrameProved=True,
        actualFieldTransfer=request['actualFieldTransfer'],wholeOwnerAdmitted=False)


def derive(image,pins,*,root,value_children):
    """Fresh finite sources/callbacks joined to already fresh strong records.

    ``value_children`` is keyed by each selected closed dictionary type. This
    keeps the two actual root requests explicit even if a future value type is
    reused by another field. No generated report is read by this builder.
    """
    from scripts.game_data.memorypack.char_current_root_sources import verify
    verify(root,pins);need('finite-explicit-closed-dictionary-children',isinstance(value_children,dict)
        and bool(value_children)and set(value_children)<=set(CAPABILITIES))
    fields=[field for field,(_,key,value)in source.DOMAINS.items()
        if source.OWNER+'<'+key+','+value+'>'in value_children]
    children={source.DOMAINS[field][2]:value_children[source.OWNER+'<'+source.DOMAINS[field][1]+','+source.DOMAINS[field][2]+'>']
        for field in fields}
    result=derive_on_children(image,pins,children=children,fields=fields);owners=[];caps={};required=set()
    for component in result['owners']:
        selected=validate_component(component,pins);typename=component['typeName']
        field=component['proof']['source']['fieldName'];index=source.DOMAINS[field][0]
        binding=bind_root(root,pins,root['requests'][index],component,selected['capability'])
        need('coherent-all-descendant-capabilities',all(k not in caps or caps[k]==v for k,v in selected['capabilities'].items()))
        caps.update(selected['capabilities']);required.update(selected['requiredExternalCapabilities'])
        owners.append(dict(typeName=typename,status=component['status'],proof=component,binding=binding))
    return normalized(dict(schema=SCHEMA,nativeInputs=pins,owners=owners,capabilities=caps,
        requiredExternalCapabilities=sorted(required-set(caps)),wholeOwnerAdmitted=False))
