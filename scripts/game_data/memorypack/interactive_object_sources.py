"""Ordinary Original-reference transport for fresh Interactive records.

The source already owns the complete concrete reader, factory, GetValue and
slot-five callback. This component joins that exact callback to the actual
eager pair and canonical adapter, independently from delegated field grammars.
It never admits an unknown child from its reference size or registration name.
"""
import json

from scripts.game_data.memorypack import interactive_parent_bindings as parent

SCHEMA='endfield.interactive-object-reference-source.v1'


def need(check,condition,detail=''):
    if not condition:raise ValueError('interactiveObjectSource.'+check+':'+str(detail)[:1000])


def derive(image,pins,source,*,reference_readers=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins)
    if source.get('memberCount')==0:
        from scripts.game_data.memorypack.generated_record_components import compile_member_program
        compiled,pending=compile_member_program(source,pins,wrapper_name=source['wrapperName'],
            type_name=source['wrappedType'],value4={})
        need('own-complete-zero-member-program',compiled is not None and not pending)
    else:parent.source_scope(source,pins)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==source['wrapperName']]
    life=source['lifecycle'];getter=life.get('GetValue',{})
    need('same-ordinary-nominal-source',wrapper.wrapped_type==source['wrappedType']
        and life.get('wrapperName')==wrapper.name and life.get('wrappedType')==wrapper.wrapped_type
        and getter.get('program',{}).get('fullReferenceOutput')is True
        and getter.get('method',[None,None])[1]==wrapper.name)
    family=life.get('directHolderMode')is not True and 'ownedCoherentGetter'in getter
    pair=derive_pair(image,wrapper.wrapped_type,wrapper.name,owned_getter_family=family)
    formatter=life.get('concreteFormatter',{})
    need('own-complete-concrete-callback',formatter.get('method',[None,None])[1]==
        wrapper.name+'+'+wrapper.name.rsplit('.',1)[-1]+'Formatter'
        and bool(formatter.get('codeWindows'))
        and(formatter.get('program',{}).get('completeOriginalForwarderChecked')is True
            or formatter.get('program',{}).get('completeSelectedFormatterAdmitted')is True))
    def forwarder(selected,selected_pair,selected_wrapper):
        face,=selected_pair['composition']['interfaces']
        need('same-fresh-owned-slot-five-callback',selected is image and selected_wrapper.name==wrapper.name
            and face['formatterDeserializeMethodIndex']==formatter['method'][0]
            and selected_pair['composition']['methods'][1]==formatter['method'])
        selected.check_windows(formatter['codeWindows'],label='interactiveObjectSource.actualCallback')
        return dict(kind='complete-current-generated-concrete-callback',readerMethod=source['method'],
            method=formatter['method'],proof=formatter,childGrammarAdmitted=False,
            actualStaticReaderAliased=False)
    adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=forwarder)
    need('own-complete-getter-interface-return',adapter['getterMethod']==getter['method'])
    readers=reference_reader_abi(image,pins)if reference_readers is None else reference_readers
    need('literal-independent-ordinary-reader',type(readers.get('referenceReaderMethodDefinition'))is int
        and type(readers.get('referenceReaderTargetRva'))is int
        and readers['referenceReaderTargetRva']>0)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,typeName=wrapper.wrapped_type,
        wrapperName=wrapper.name,pair=pair,adapter=adapter,referenceReaders=readers,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        ownConcreteCallbackProved=True,childGrammarAdmitted=False,wholeOwnerAdmitted=False)))


def bind_member(image,pins,parent_source,read,child):
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    transfer=parent.bind_reference_result(parent_source,read,pins)
    usage=parent.fresh_request(image,read)
    need('same-owned-child-transport',child.get('schema')==SCHEMA and child.get('nativeInputs')==pins
        and child.get('typeName')==read['declaredType']
        and all(child.get(k)is True for k in('ownConcreteGetterSemanticsProved',
            'ownConcreteFactorySemanticsProved','ownConcreteCallbackProved'))
        and child.get('childGrammarAdmitted')is False and child.get('wholeOwnerAdmitted')is False)
    bind_typed_read(image,usage,method_name='ReadValue',argument=child['typeName'],kind=18,reference=True)
    reader=child['referenceReaders']
    need('same-actual-returning-reference-helper',usage['methodSpec'][0]==reader['referenceReaderMethodDefinition']
        and read['sourceTargetRva']==reader['referenceReaderTargetRva'])
    return dict(transfer,typedRequest=usage,childType=child['typeName'],ownOriginalWrapperTransportJoined=True)
