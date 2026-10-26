"""Complete TransformDesc MC4 and its independent ordinary reference adapter.

This finite child has no containing-route or runtime transform interpretation.
Each supplied parent must independently join its actual MethodSpec, reached
Reader, whole reference field and complete enclosing source/frame paths.
"""
import json
from scripts.game_data.memorypack import animation_transform_desc_codec as codec

TYPE=codec.TYPE
WRAPPER=codec.WRAPPER
CAPABILITY=codec.CAPABILITY
WIRE=codec.WIRE
SCHEMA='endfield.animation-transform-desc-components.v1'


def need(check,condition):
    if not condition:raise ValueError('animationTransformDescComponents.'+check)


def compose(source,pins):
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    need('own-complete-source',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and source.get('wrapperName')==WRAPPER and source.get('wrappedType')==TYPE
        and source.get('completeSelectedCallerAdmitted')is True and source.get('wholeOwnerAdmitted')is False
        and [(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]==
            [('pos','UnityEngine.Vector3'),('rot','UnityEngine.Vector3'),('usePos','bool'),('useRot','bool')])
    compiled,pending=compile_member_program(source,pins,wrapper_name=WRAPPER,type_name=TYPE,value4={})
    need('complete-own-MC4-program',pending==[]and compiled['memberCount']==4 and compiled['reads']==codec.ORDER
        and compiled['requiredCapabilities']==[]and compiled['childBindings']==[])
    cap=dict(typeName=TYPE,wrapperName=WRAPPER,memberCount=4,orderedReads=codec.ORDER,nullable=True,nullMarker=255,
        nullWireBytes=1,positiveWireBytes=27,wireBytes=None,wholeGrammarAdmitted=True,directWrapperGrammarAdmitted=True,
        ordinaryOriginalReadValueAdmitted=False,ownConcreteGetterSemanticsProved=False,ownConcreteFactorySemanticsProved=False,
        actualContainingRouteAdmitted=False,wholeOwnerAdmitted=False)
    codec.require_capability(cap)
    return dict(schema=SCHEMA,status='compiled-conditional-transform-desc-wrapper',nativeInputs=pins,
        capabilities={CAPABILITY:cap},requiredExternalCapabilities=[],compiled=compiled,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def derive(image,pins,*,source):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.pointer_param import leaf
    _publication_gate(image,pins);component=compose(source,pins)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    method=source['method'];actual=image.metadata.methods[method[0]]
    need('fresh-own-reader-and-ordered-members',image.type_name(actual.declaring_type)==WRAPPER
        and image.metadata.string(actual.name_index)=='Deserialize'
        and image.method_pointer_va(actual)==image.pe.image_base+method[3]
        and [(m.name,m.declared_type)for m in wrapper.members]==[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
    image.check_windows(source['codeWindows'],label='animationTransformDesc.retained-complete-source')
    pair=derive_pair(image,TYPE,WRAPPER);adapter=derive_adapter(image,pins,pair,wrapper)
    need('same-own-complete-reader-and-getter',adapter['getterMethod']==source['lifecycle']['GetValue']['method']
        and adapter['pairForwarder']['readerMethod']==source['method'])
    getter=leaf(image,image.pe.image_base+adapter['getterMethod'][3],['488B4110','C3'])
    reference=reference_reader_abi(image,pins);cap=component['capabilities'][CAPABILITY]
    cap.update(ordinaryOriginalReadValueAdmitted=True,ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        originalTypeDefinition=image.named_types[TYPE].index,callbackSelectionConditional=True,
        **{k:reference[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')})
    codec.require_capability(cap,ordinary=True);_publication_gate(image,pins)
    component.update(status='validated-conditional-transform-desc-components',
        proof=dict(source=source,pair=pair,adapter=adapter,getter=getter,referenceReaders=reference))
    return json.loads(json.dumps(component))


def bind_parent(source,scope,read,pins,usage,component,capability=CAPABILITY):
    from scripts.game_data.memorypack.generated_reader_sources import constructed_getter_join
    from scripts.game_data.memorypack.skill_root_child_bindings import bind_read_value
    need('own-independent-ordinary-child',capability==CAPABILITY and component.get('schema')==SCHEMA
        and component.get('status')=='validated-conditional-transform-desc-components'and component.get('nativeInputs')==pins
        and component.get('requiredExternalCapabilities')==[]and component.get('parentFieldAdmitted')is False
        and component.get('wholeOwnerAdmitted')is False)
    cap=codec.require_capability(component['capabilities'][CAPABILITY],ordinary=True)
    proof=component.get('proof',{});child_source=proof.get('source',{});child=compose(child_source,pins)
    adapter=proof.get('adapter',{});reference=proof.get('referenceReaders',{})
    need('independent-whole-child-and-ordinary-adapter',component.get('compiled')==child['compiled']
        and adapter.get('schema')=='endfield.reference-object-adapter-source.v1'and adapter.get('nativeInputs')==pins
        and adapter.get('typeName')==TYPE and adapter.get('wrapperName')==WRAPPER and adapter.get('pair')==proof.get('pair')
        and adapter.get('getterMethod')==child_source['lifecycle']['GetValue']['method']
        and adapter.get('pairForwarder',{}).get('readerMethod')==child_source.get('method')
        and child_source['lifecycle']['GetValue']['program'].get('fullReferenceOutput')is True
        and adapter.get('callbackBinding',{}).get('runtimeSelectionObserved')is False
        and all(cap.get(k)==reference.get(k)for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')))
    need('whole-exact-parent-source',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==scope.get('nativeInputs')==pins and source.get('sourceScope')==scope
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False)
    index=read.get('memberIndex');context=read.get('context',{})
    need('same-owned-reference-field',type(index)is int and 0<=index<len(source.get('orderedSourceReads',[]))
        and source['orderedSourceReads'][index]==read and scope.get('events')==source['orderedSourceReads']
        and read.get('declaredType')==TYPE and read.get('kind')=='reference:'+TYPE
        and read.get('mode')is None and read.get('sourceContextMode')is None)
    argument=bytes.fromhex(context.get('argumentRawHex',''));load=bytes.fromhex(context.get('instructionHex',''))
    site,encoded=read.get('instruction',[None,'']);call=bytes.fromhex(encoded)
    need('actual-nominal-RDX-context-and-reference-E8',len(argument)==16 and argument[10:12]==bytes((18,0))
        and int.from_bytes(argument[:8],'little')==context.get('typeDefinition')==cap['originalTypeDefinition']
        and context.get('register')=='rdx'and context.get('typeKind')==18
        and len(load)==7 and load[:3]==bytes.fromhex('488b15')
        and(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))==
            (usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec'))
        and [context.get('instructionRva'),context.get('instructionHex')]in scope.get('selectedProgram',[])
        and tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE])
        and type(site)is int and len(call)==5 and call[0]==0xe8
        and site+5+int.from_bytes(call[1:],'little',signed=True)==read.get('sourceTargetRva'))
    rich=scope.get('richProgram',{});selected=rich.get('selectedProgram',[]);setters=source.get('setters',[])
    need('complete-parent-reference-flow',rich.get('completeSelectedNormalProgram')is True
        and rich.get('childGrammarAdmitted')is False and rich.get('wholeOwnerAdmitted')is False
        and selected==scope.get('selectedProgram')and read['instruction']in selected
        and [r for r in rich.get('sources',[])if r.get('memberIndex')==index]==
            [dict(memberIndex=index,instruction=read['instruction'],resultAbi='rax')]
        and index<len(setters)and setters[index]==scope.get('richSetters',[])[index])
    setter=setters[index];member=setter['member'];method=setter['method']
    stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index]
    need('whole-reference-through-own-named-setter',len(stores)==1 and stores[0].get('sourceOffset')==0
        and type(stores[0].get('storedBytes'))is int and stores[0]['storedBytes']==8 and stores[0].get('instruction')in selected
        and setter.get('storedBytes')==8 and setter.get('parameterTypeRecordHex')==context.get('argumentRawHex')
        and setter.get('incomingValueStoredUnchanged')is True and setter.get('childGrammarAdmitted')is False
        and method[0]==member.get('methodIndex')and method[1]==member.get('declaringWrapper')
        and method[2]=='set___'+str(read['fieldName'])+'__'and member.get('name')==read['fieldName']
        and member.get('declaredType')==TYPE and setter.get('targetField')==source.get('wrappedType')+'::'+read['fieldName'])
    store_at,store_hex=stores[0]['instruction'];store_call=bytes.fromhex(store_hex)
    need('actual-parent-named-setter-call',len(store_call)==5 and store_call[0]==0xe8
        and store_at+5+int.from_bytes(store_call[1:],'little',signed=True)==method[3]
        and constructed_getter_join(source['lifecycle'],setters)==source.get('constructedGetterJoin'))
    paths=source.get('programs',[])
    need('all-four-complete-parent-frames',len(paths)==4
        and {(p.get('existing'),p.get('wrapperNull'))for p in paths}=={(False,False),(False,True),(True,False),(True,True)}
        and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool
            and p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
    binding=bind_read_value(pins,dict(fieldName=read['fieldName'],typeName=TYPE,typedRequest=usage,sourceTargetRva=read['sourceTargetRva']),component,CAPABILITY)
    return dict(binding,parentMemberIndex=index,completeReferenceFieldAndFramesProved=True,ordinaryReferenceIdentityClaimed=True)
