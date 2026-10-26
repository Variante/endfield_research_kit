"""Finite BlowOff priority dropdown, independently selected by its own type.

The exact nominal Original/wrapper must satisfy the complete Int32 dropdown
source programs: actual int/int base, distinct holder16/cache24/cache32/cache40,
owned refresh/construction/GetValue, MC4 pool4/bool1/int4/bool1 and all four
new/existing/FF frames. Reusing those instruction algorithms grants no sibling
identity or enum interpretation. Fresh own canonical adapter and actual
reference Reader remain mandatory. Coherent initialized compatible contexts,
normal callbacks/typed allocation, disabled collector and disjoint stable
buffered storage are conditions. Runtime priority selection/blow-off effects,
provider choice, unselected error/refill paths and enclosing action/EOF remain
unresolved.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPE='Beyond.Gameplay.Core.BlowOffCharacterAction+BlackboardCharBlowOffPriorityValue'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_BlowOffCharacterAction_BlackboardCharBlowOffPriorityValueForMemoryPack'
CAPABILITY='skill-blackboard-blowoff-priority'


def bind_source(record,pins):
    from scripts.game_data.memorypack.skill_dropdown_blackboard_sources import ORDER
    cap=record.get('capability',{});proof=record.get('proof',{});scope=proof.get('scope',{})
    need('BlowOff-priority-own-nominal',(TYPE,WRAPPER),(cap.get('typeName'),cap.get('wrapperName')))
    need('BlowOff-priority-same-native-source',pins,scope.get('nativeInputs'))
    need('BlowOff-priority-own-MC4-source',True,scope.get('wrappedType')==TYPE and scope.get('wrapperName')==WRAPPER
        and type(scope.get('memberCount'))is int and scope['memberCount']==4 and scope.get('sourceScopeAdmitted')is True)
    need('BlowOff-priority-exact-current-fields',[('blackboardKey','string'),('useBlackboardKey','bool'),('value','int'),('useCustomValue','bool')],
        [(r.get('fieldName'),r.get('declaredType'))for r in scope.get('events',[])])
    need('BlowOff-priority-exact-wire-order',[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in ORDER],cap.get('orderedReads'))
    need('BlowOff-priority-complete-source-admissions',True,all(cap.get(k)is True for k in
        ('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted','ownConcreteGetterSemanticsProved',
            'ownConcreteFactorySemanticsProved','nullable','nullAdmitted')))
    need('BlowOff-priority-literal-layout',True,all(type(cap.get(k))is int and cap[k]==v for k,v in
        (('memberCount',4),('positiveWireBytes',11),('nullWireBytes',1),('nullMarker',255)))
        and all(type(cap.get(k))is int and cap[k]>0 for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')))
    paths=proof.get('programs',[])
    need('BlowOff-priority-complete-source-frames',True,len(paths)==4 and all(type(p.get('existing'))is bool
        and type(p.get('wrapperNull'))is bool and p.get('frame',{}).get('entryRspRestored')is True
        and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})
    return cap


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_dropdown_blackboard_sources import _derive_one
    from scripts.game_data.memorypack.skill_blackboard_int_sources import derive as base_source
    from scripts.game_data.memorypack.generated_action_sources import _prepare
    _publication_gate(image,pins);base=base_source(image,pins);targets,barrier,disabled=_prepare(image,pins)
    record=_derive_one(image,pins,TYPE,base,targets,barrier,disabled);cap=bind_source(record,pins)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-blowoff-priority-sources.v1',status='validated-conditional-blowoff-priority',
        nativeInputs=pins,capabilities={CAPABILITY:cap},requiredExternalCapabilities=['byte-payload'],proof=record['proof'],wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own exact BlowOff priority nominal and complete MC4/int-base/cache/factory/getter/canonical ordinary adapter/actual reference Reader source programs.',
            conditional=__doc__,structuralOnly='Stored Int32 blackboard priority configuration.',
            unresolved=['runtime priority/effects and provider/callback selection','noncoherent own-cache prehook','enclosing action/union/root/EOF']))))
