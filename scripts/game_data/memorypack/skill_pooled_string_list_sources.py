"""Selected List<string> count/loop and independently owned pooled callback.

STRING is the actual built-in reference kind, not a CLASS/TypeDef alias. The
parent supplies its exact closed ReadPackable MethodSpec/E8. Fresh typed list
or reused-empty/spare-capacity paths compose finite witnesses and induction;
each selected BeyondStringFormatter callback reads one signed pool index4.
Its own typed allocation/ForceRegister<string>/dictionary/backend and complete
callback source are re-proved. Runtime dictionary contents and provider choice,
normal allocation/lookup/helper effects, matching nonnull exported StringPool,
initialized contexts and disabled collectors remain explicit conditions.
Neither a reference stride8 nor a nominal list request supplies wire width.
This component grants no enclosing owner, root, physical EOF or runtime meaning.
"""
import json

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack.skill_root_child_bindings import need

CAPABILITY='skill-root-pooled-string-list'
LIST='System.Collections.Generic.List`1<string>'


def capability(component,callback):
    """Pure finite composition; derive freshly proves both supplied programs."""
    need('string-list-component-type','string',component['elementType'])
    need('string-list-status','validated-bounded-reference-list-induction',component['status'])
    need('string-list-no-element-owner',True,all(component.get(k)is False for k in
        ('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    need('string-list-count-range',True,isinstance(component.get('countRange'),list)
        and len(component['countRange'])==2 and all(type(n)is int for n in component['countRange'])
        and component['countRange'][0]==-1 and 3<=component['countRange'][1]<=10000)
    need('string-list-path-conditions',True,component.get('nullable')is True
        and component.get('freshListsAdmitted')is True and type(component.get('reusedListsRequireInitialCount'))is int
        and component['reusedListsRequireInitialCount']==0 and component.get('reusedListsRequireCapacityAtLeastCount')is True)
    need('pooled-string-actual-callback',True,all(type(callback.get(k))is int and callback[k]==v
        for k,v in(('stringFormatterSlot',5),('wireBytes',4),('managedReferenceBytes',8))))
    need('pooled-string-selection-boundary',True,callback.get('liveProviderSelectionProved')is False
        and callback.get('wholeOwnerAdmitted')is False)
    witness=component['witnessComponent']
    definition=witness['typedRequest']['methodSpec'][0];target=witness['callTargetRva']
    need('string-list-actual-reader',True,type(definition)is int and definition>0 and type(target)is int and target>0)
    return dict(elementType='string',elementValueType=False,closedListType=LIST,
        collectionCounts=[-1,0],countLimit=component['countRange'][1],positiveCountsAdmitted=True,
        nullable=True,elementCapability='byte-payload',elementGrammarAdmitted=True,
        elementWireBytes=4,elementManagedReferenceBytes=8,stringEncoding='int32-pool-index',
        packableReaderMethodDefinition=definition,packableReaderTargetRva=target,
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False)


def derive(image,pins,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import reference_list_induction_sources,pooled_string_list_sources
    _publication_gate(image,pins)
    component=reference_list_induction_sources.derive(image,pins,typed_request=typed_request,
        call_target=call_target,element_type='string',count_limit=count_limit)
    path=CONTRACTS_DIR/'levelscript_pooled_string_list_native.json';raw=path.read_bytes();fact=json.loads(raw)
    need('string-callback-reviewed-schema','endfield.levelscript-pooled-string-list-native.v1',fact['schema'])
    need('string-callback-reviewed-status','exact-current-build',fact['status'])
    need('string-callback-selected-inputs',pins,fact['nativeInputs'])
    callback=pooled_string_list_sources.validate_string_components(image,fact)
    cap=capability(component,callback)
    need('string-callback-source-bookend',raw,path.read_bytes());_publication_gate(image,pins)
    return dict(schema='endfield.skill-pooled-string-list-sources.v1',nativeInputs=dict(pins),
        status='validated-conditional-components',capabilities={CAPABILITY:cap},
        proof=dict(listComponent=component,stringCallback=callback),requiredExternalCapabilities=['byte-payload'],
        evidenceBoundary=dict(exact='Actual built-in STRING closed list request, current signed count/loop/Add source and induction, independently typed pooled-string formatter/registration/backend/callback source.',
            conditional=__doc__,structuralOnly='Stored pooled string list.',
            unresolved=['runtime provider choice and dictionary contents','enclosing owner/EOF']))
