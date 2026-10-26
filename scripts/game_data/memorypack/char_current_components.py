"""Join the complete dedicated Char root to each exact nominal child grammar."""
from scripts.game_data.memorypack import char_current_root_sources as source

SCHEMA='endfield.char-interact-current-components.v1'
CAPABILITY='char-interact-current'


def need(check,condition):
    if not condition:raise ValueError('charCurrentComponents.'+check)


def _child(component,pins):
    schema=component.get('schema')
    if schema=='endfield.char-interact-reference-list-components.v1':
        from scripts.game_data.memorypack import char_reference_lists as owner
    elif schema=='endfield.char-interact-value-list-components.v1':
        from scripts.game_data.memorypack import char_value_lists as owner
    elif schema=='endfield.char-interact-record-components.v1':
        from scripts.game_data.memorypack import char_record_components as owner
    else:
        from scripts.game_data.memorypack import char_static_dictionary_components as owner
        need('own-static-dictionary-schema',schema==owner.SCHEMA)
    return owner.validate_component(component,pins),owner.WIRE


def compose(root,children,pins,*,pooled_capability):
    source.verify(root,pins);requests=root['requests'];complex_rows=[r for r in requests if r['mode']in('reference','out8')]
    need('all-and-only-nominal-root-children',isinstance(children,dict)and set(children)=={r['typeName']for r in complex_rows})
    caps={};required=set();validated={};reads=[];bindings=[]
    for name,component in children.items():
        own,wire=_child(component,pins);cap=own['capabilities'][own['capability']]
        need('whole-exact-nominal-child',cap.get('typeName',cap.get('closedListType'))==name
            and cap.get('wholeGrammarAdmitted')is True)
        need('coherent-complete-root-child-capabilities',all(k not in caps or caps[k]==v for k,v in own['capabilities'].items()))
        caps.update(own['capabilities']);required.update(own['requiredExternalCapabilities'])
        validated[name]=(own['capability'],cap,wire)
    for row in requests:
        index=row['memberIndex'];mode=row['mode'];name=row['typeName'];child=None;binding=None
        if mode in('reference','out8'):
            child,cap,wire=validated[name];usage=row['typedRequest']
            if mode=='out8':
                from scripts.game_data.memorypack import char_static_dictionary_components as dictionaries
                need('own-static-out-dictionary-wire',wire==dictionaries.WIRE)
                binding=dictionaries.bind_root(root,pins,row,children[name],child)
            elif name.startswith('System.Collections.Generic.List`1<'):
                need('own-root-closed-list-and-actual-reader',usage.get('methodName')=='ReadPackable'
                    and usage.get('methodArguments')==[name]and usage.get('classArguments')==[]
                    and usage.get('methodSpec')==cap.get('sourceMethodSpec')
                    and usage['methodSpec'][0]==cap.get('packableReaderMethodDefinition')
                    and row['sourceTargetRva']==cap.get('packableReaderTargetRva'))
                binding=dict(actualTypedListReaderAndWholeNamedField=True)
            else:
                need('own-root-ordinary-record-reader',name==source.TYPE.rsplit('.',1)[0]+'.SubSpecialPerformEntryData'
                    and wire=='char-interact-record'and cap.get('ordinaryOriginalReadValueAdmitted')is True
                    and cap.get('ordinaryOriginalCallbackAdmitted')is True and cap.get('valueStorageKind')=='reference8'
                    and usage.get('methodName')=='ReadValue'and usage.get('methodArguments')==[name]
                    and usage['methodSpec'][0]==cap.get('referenceReaderMethodDefinition')
                    and row['sourceTargetRva']==cap.get('referenceReaderTargetRva'))
                binding=dict(ordinaryOriginalCallbackAndWholeNamedField=True)
            bindings.append(dict(memberIndex=index,fieldName=row['fieldName'],typeName=name,capability=child,
                sourceTargetRva=row['sourceTargetRva'],binding=binding))
        else:
            need('only-source-proved-primitive-fields',mode in('bool','float','enum'))
            wire={'bool':'bool-byte','float':'float32-bits','enum':'nominal-enum32-bits'}[mode]
        reads.append(dict(memberIndex=index,fieldName=row['fieldName'],typeName=name,kind=wire,childCapability=child))
    caps[CAPABILITY]=dict(typeName=source.TYPE,wrapperName=root['wrapperName'],memberCount=28,orderedReads=reads,
        wholeGrammarAdmitted=True,allTwentyEightFieldsAdmitted=True,rootNullMarkerAdmitted=False,
        completeDedicatedExistingRootSourceRequired=True,physicalEOFRequired=True,nodeLimit=16384,
        requiredChildCapabilities=sorted({r['childCapability']for r in reads if r['childCapability']}),
        runtimeAnimationProved=False)
    need('independent-selected-pool-capability',pooled_capability.get('wholeGrammarAdmitted')is True
        and pooled_capability.get('encoding')=='int32-pool-index'and pooled_capability.get('wireBytes')==4
        and pooled_capability.get('emptyIndex')==-1 and pooled_capability.get('nullIndex')==-2
        and('byte-payload'not in caps or caps['byte-payload']==pooled_capability))
    caps['byte-payload']=pooled_capability;required.add('byte-payload')
    return dict(schema=SCHEMA,status='validated-conditional-char-interact-current-components',nativeInputs=pins,
        capability=CAPABILITY,capabilities=caps,requiredExternalCapabilities=sorted(required-set(caps)),bindings=bindings,
        proof=dict(root=root,children=children,pooledCapability=pooled_capability),wholeOwnerGrammarAdmitted=True,publicDecoderActivated=False,runtimeAnimationProved=False)


def validate_component(component,pins):
    need('own-whole-current-Char-component',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('wholeOwnerGrammarAdmitted')is True and component.get('publicDecoderActivated')is False)
    proof=component['proof'];checked=compose(proof['root'],proof['children'],pins,pooled_capability=proof['pooledCapability'])
    need('same-full-root-and-child-composition',component==checked)
    return {k:checked[k]for k in('capability','capabilities','requiredExternalCapabilities')}
