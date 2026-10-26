"""Whole MC28 CharInteract cursor under an active selected native operation."""
from scripts.game_data.memorypack import char_current_components as component


def need(check,condition):
    if not condition:raise ValueError('charCurrentCodec.'+check)


def require_capability(cap):
    reads=cap.get('orderedReads',[])
    need('whole-source-owned-root28',cap.get('typeName')==component.source.TYPE and cap.get('memberCount')==28
        and len(reads)==28 and[r.get('memberIndex')for r in reads]==list(range(28))
        and len({r.get('fieldName')for r in reads})==28
        and all(cap.get(k)is True for k in('wholeGrammarAdmitted','allTwentyEightFieldsAdmitted',
            'completeDedicatedExistingRootSourceRequired','physicalEOFRequired'))
        and cap.get('rootNullMarkerAdmitted')is False and cap.get('nodeLimit')==16384)
    need('complete-child-capability-set',cap.get('requiredChildCapabilities')==
        sorted({r.get('childCapability')for r in reads if r.get('childCapability')}))
    return cap


def frame(data,selected,*,operation):
    from scripts.game_data.memorypack.char_record_codec import CharRecordReader
    from scripts.game_data.memorypack import char_reference_lists as references,char_value_lists as values
    from scripts.game_data.memorypack import char_union_codec as unions
    from scripts.game_data.memorypack import char_reference_records as custom
    from scripts.game_data.memorypack import char_static_dictionary_components as dictionaries,char_static_dictionary_codec as dictionary_codec
    from scripts.game_data.memorypack import char_tag_dictionary_components as tags,char_tag_dictionary_codec as tag_codec
    cap=require_capability(operation.child(component.CAPABILITY))
    need('same-operation-owned-complete-root',cap==selected['capabilities'][component.CAPABILITY])
    handlers={references.WIRE:references.read,values.WIRE:values.read,unions.WIRE:unions.read,
        dictionaries.WIRE:dictionary_codec.read,tags.WIRE:tag_codec.read,custom.WIRE:custom.read}
    validators={references.WIRE:references.require_capability,values.WIRE:values.require_capability,
        unions.WIRE:unions.require_capability,dictionaries.WIRE:dictionary_codec.require_capability,
        tags.WIRE:tag_codec.require_capability,custom.WIRE:custom.require_capability}
    reader=CharRecordReader(data,'CharInteractPerform.current',operation=operation,
        child_handlers=handlers,child_validators=validators)
    for child in cap['requiredChildCapabilities']:operation.child(child)
    reader.header(28);budget=dict(remaining=16384);fields=[]
    for read in cap['orderedReads']:
        start=reader.pos;wire=read['kind'];child=read['childCapability']
        if wire in('bool-byte','float32-bits','nominal-enum32-bits'):
            need('primitive-root-has-no-child',child is None)
            raw=reader.take(1 if wire=='bool-byte'else 4,read['fieldName']);value=dict(rawHex=raw.hex())
            if wire=='bool-byte':value['value']=raw[0]!=0
        elif wire=='char-interact-record':value=reader.record(child,depth=1,budget=budget)
        else:
            need('own-finite-root-child-wire',wire in handlers)
            validators[wire](child,operation.child(child));value=handlers[wire](reader,child,depth=1,budget=budget)
        fields.append(dict(memberIndex=read['memberIndex'],fieldName=read['fieldName'],typeName=read['typeName'],
            kind=wire,start=start,end=reader.pos,value=value))
    need('whole-physical-EOF',reader.pos==reader.limit==len(data))
    return dict(status='complete-current-char-interact-frame',schemaStatus='named_exact',wholeSchemaExact=True,
        serializedMemberCount=28,bytesConsumed=reader.pos,physicalEOF=True,fields=fields,records=reader.records,
        sourceSelectionConditional=True,runtimeAnimationProved=False,remainingNodeBudget=budget['remaining'])
