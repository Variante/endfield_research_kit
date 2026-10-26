"""SmartTargetSelectSetting value40 with independently proved wire children.

The own actual hidden40 Reader/adapter and complete wrapper precede every
child join. BuffFindSettings and its Query/string-list closure, BuffId-list
count/callback/induction, and the wrapper's actual Query16 frontend remain
distinct. Matching current contexts, callbacks and normal compatible buffered
helpers are conditions; parent field/local/frame and runtime choice stay open.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need,bind_read_value,bind_read_packable_list
from scripts.game_data.memorypack.skill_smart_target_value_sources import TYPE,WRAPPER,FIND,QUERY,CAPABILITY,ORDER

FIND_CAP='skill-root-buff-find-settings'
LIST_CAP='skill-root-buff-id-list'
QUERY_CAP='skill-root-gameplay-tag-query'


def compose(pins,transfer,find,listing,query_read):
    """Pure scope and actual-call joins; public derive supplies fresh owners."""
    need('smart-target-actual-value-source',(pins,TYPE,WRAPPER,40,'hidden-local',True),
        tuple(transfer.get(k)for k in('nativeInputs','typeName','wrapperName','managedBytes','resultAbi','actualSourceProved')))
    need('smart-target-transfer-scope',('endfield.skill-smart-target-value-transfer.v1','proved-conditional-smart-target-value40-read',False,False),
        tuple(transfer.get(k)for k in('schema','status','wireGrammarAdmitted','parentFieldAdmitted')))
    child=transfer['proof']['childSource'];requests=child['requests'];symbols=child['symbolRvas']
    need('smart-target-whole-own-wrapper',(pins,TYPE,WRAPPER,ORDER),tuple(child[k]for k in('nativeInputs','typeName','wrapperName','wireOrder')))
    need('smart-target-wrapper-unadmitted-children',True,child.get('childGrammarAdmitted')is False and child.get('wholeOwnerAdmitted')is False)
    need('smart-target-exact-find-component',('endfield.skill-root-buff-find-components.v1','validated-conditional-components',pins),
        tuple(find.get(k)for k in('schema','status','nativeInputs')))
    find_binding=bind_read_value(pins,dict(fieldName='smartTargetBuffFindSettings',typeName=FIND,
        typedRequest=requests['find'],sourceTargetRva=symbols['find']),find,FIND_CAP)
    list_binding=bind_read_packable_list(pins,dict(fieldName='smartTargetBuffIds',typeName=child['typedArguments']['buffIds']['argumentType'],
        typedRequest=requests['buffIds'],sourceTargetRva=symbols['buffIds']),listing,LIST_CAP)
    need('smart-target-own-Query-frontend',(pins,QUERY,16,'hidden-local',True,False,symbols['query'],requests['query']['methodSpec'][0]),
        tuple(query_read.get(k)for k in('nativeInputs','typeName','managedBytes','resultAbi','actualSourceProved','wireGrammarAdmitted','sourceTargetRva','readerMethodDefinition')))
    need('smart-target-Query-source-scope',('endfield.skill-nominal-value-read-sources.v1','proved-conditional-typed-nominal-value-read'),
        tuple(query_read.get(k)for k in('schema','status')))
    need('smart-target-own-Query-request',requests['query'],query_read['proof']['typedRequest'])
    query_cap=find['capabilities'][QUERY_CAP];query_transfer=query_read['proof']['adapter']
    need('smart-target-strong-Query-wire',True,query_cap.get('typeName')==QUERY and query_cap.get('wholeGrammarAdmitted')is True
        and query_cap.get('nullReturnsDefaultValue')is True and query_cap.get('managedBytes')==16)
    need('smart-target-literal-Query-reader-identities',True,
        type(query_cap.get('valueReaderMethodDefinition'))is int and type(query_cap.get('valueDispatcherTargetRva'))is int)
    need('smart-target-same-Query-dispatch-and-formal',
        (query_cap['valueReaderMethodDefinition'],query_cap['valueDispatcherTargetRva'],requests['query']['methodSpec'][0]),
        (query_transfer['readerMethodDefinition'],query_transfer['dispatcherTargetRva'],query_transfer['readerMethodDefinition']))
    caps=dict(find['capabilities'])
    for name,cap in listing['capabilities'].items():
        if name in caps:need('smart-target-identical-shared-child:'+name,caps[name],cap)
        caps[name]=cap
    cap=dict(typeName=TYPE,memberCount=4,managedBytes=40,referenceLaneOffsets=[8,24,32],nullable=True,
        nullMarker=255,nullWireBytes=1,positiveWireBytes=None,wireBytes=None,nullReturnsDefaultValue=True,
        wholeGrammarAdmitted=True,ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        actualValueReadValueAdmitted=True,ordinaryOriginalReadValueAdmitted=False,
        orderedReads=ORDER,valueReaderMethodDefinition=transfer['readerMethodDefinition'],
        valueSourceTargetRva=transfer['sourceTargetRva'],valueDispatcherTargetRva=transfer['proof']['symbolRvas']['dispatch'],
        callbackSelectionConditional=True,wholeOwnerAdmitted=False)
    caps[CAPABILITY]=cap
    return dict(capabilities=caps,bindings=dict(find=find_binding,buffIds=list_binding,
        query=dict(typeName=QUERY,actualFrontendTargetRva=symbols['query'],
            readerMethodDefinition=query_transfer['readerMethodDefinition'],dispatcherTargetRva=query_transfer['dispatcherTargetRva'])))


def derive(image,pins,*,typed_request,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_smart_target_value_transfer import derive as transfer_source
    from scripts.game_data.memorypack.skill_root_buff_find_components import derive as find_source
    from scripts.game_data.memorypack.skill_root_buff_id_lists import derive as list_source
    from scripts.game_data.memorypack.skill_nominal_value_read_sources import derive as query_frontend
    _publication_gate(image,pins);base=image.pe.image_base
    transfer=transfer_source(image,pins,typed_request=typed_request,source_target=source_target)
    child=transfer['proof']['childSource'];find=find_source(image,pins)
    listing=list_source(image,pins,typed_request=child['requests']['buffIds'],call_target=base+child['symbolRvas']['buffIds'])
    query=query_frontend(image,pins,typed_request=child['requests']['query'],source_target=base+child['symbolRvas']['query'])
    selected=compose(pins,transfer,find,listing,query);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-smart-target-components.v1',
        status='validated-conditional-smart-target-components',nativeInputs=pins,**selected,requiredExternalCapabilities=['byte-payload'],
        proof=dict(transfer=transfer,find=find,buffIdList=listing,queryFrontend=query),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Own current SmartTarget MC4/new/FF/default40/hidden40 and actual parent ReadValue/provider/canonical adapter, exact delegated ordinary BuffFindSettings and Query/string-list closure, actual closed BuffId-list positive source/induction and separate Query frontend-to-wire join.',
            conditional=__doc__,structuralOnly='Stored target-selection configuration.',
            unresolved=['actual parent local/whole-field/frame','enclosing selector/Skill/physical EOF','live provider/callback selection','runtime target selection']))))
