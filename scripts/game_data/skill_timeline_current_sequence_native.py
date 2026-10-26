"""Strict current Skill sequence programs, isolated from the historical v2 reader."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import importlib
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import native_validation_failure,open_native_image
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.levelscript_reader_inputs import (
    snapshot_complete_reader_inputs,snapshot_string_pool_inputs,reader_input_changes)
from scripts.game_data.memorypack import skill_shared_sequence_sources as source,pooled_source_helper
from scripts.game_data.memorypack.skill_contract_provenance import project_contract,validate_projection,contract_json_bytes
from scripts.game_data.memorypack.skill_timeline_current_sequence import validate_program,validate_continuation
from scripts.repo_paths import REPO_ROOT

SCHEMA='endfield.skill-timeline-current-sequence-native.v4'
LABEL='skillTimelineCurrentSequenceNative'
CONTRACT_PATH=CONTRACTS_DIR/'skill_timeline_current_sequence_native.json'
CURRENT_COMPONENTS={
    'layer-mask-raw4':'buff_layer_mask_native',
    'gameplay-tag32':'buff_gameplay_tag_native',
    'blackboard-vector3':'buff_blackboard_vector3_native',
    'blackboard-int':'buff_blackboard_int_native',
}
BOUNDARY={
    'exact':'Only the authenticated current logical wrapper identities, canonical physical tags, member counts, canonical AbilityActionData FF reference and separately authenticated tagged-wrapper FF paths, and finite ordered source programs in this contract. Positive passive maps use their own Event enum and SequenceActionData array proof. Finite selector routes and canonical FF compose actual union callers, concrete readers/lifecycle/setters, independently owned member sources, base adapter/interface conversion and induced positive list sources. The current root continuation composes its complete existing-root caller/return source with its independently bounded named scalar, value/reference record, BuffInputBase union and collection capabilities. Every usable nested source is independently composed on the same selected native image.',
    'conditional':'Selected buffered paths, coherent initialized typed contexts and compatible storage; normal typed allocator, provider, collector, interface and callback ABI. Each child route and collection count is independently bounded at its reached byte.',
    'structuralOnly':'Closed records establish stored framing and source ranges, without gameplay execution, action order or runtime selection claims. A selected whole SkillData file additionally requires all49 source-owned fields, the complete selected existing-root caller/return capability, physical EOF and operation exit bookends; this admits no new/null root or unknown action route.',
    'unresolved':'Unknown current routes, reserved short union markers, unadmitted selector children or list counts, unsupported root child components, fields beyond a selected partial root continuation, new/null roots and runtime provider selection remain closed. Historical v2 facts and old tags provide no fallback.',
}


def _json_fact(value):
    """The exact value that a published reviewed JSON will later reload."""
    return json.loads(json.dumps(value))


def _read(path=CONTRACT_PATH):
    fact=json.loads(Path(path).read_bytes())
    if (set(fact)!={'schema','status','nativeInputs','sourceOwners','programs','routeRequirements',
            'capabilities','nullUnions','proof','evidenceBoundary'}
            or (fact['schema'],fact['status'])!=(SCHEMA,'exact-current-build')
            or fact['sourceOwners']!=sorted(source.UNIFORM_OWNERS)
            or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}
            or fact['evidenceBoundary']!=BOUNDARY):raise ValueError(LABEL+'.contract:identity-or-scope')
    validate_projection(fact['proof'])
    identities=set();wrappers=set()
    for row in fact['programs']:
        validate_program(row);identity=(row['family'],row['tag'])
        if identity in identities or row['wrapperName']in wrappers:raise ValueError(LABEL+'.contract:duplicate-route-or-wrapper')
        if row['sourceOwner']not in source.UNIFORM_OWNERS|{CONTRACT_PATH.name}:raise ValueError(LABEL+'.contract:unreviewed-source-owner')
        identities.add(identity);wrappers.add(row['wrapperName'])
    return fact


def _selected_component(image,inputs,name):
    module=importlib.import_module('scripts.game_data.memorypack.'+name)
    result=module.validate_on_image(image,inputs)
    if result.get('status')!='validated'or result.get('nativeInputs')!=inputs:
        raise ValueError(LABEL+'.child:refused='+name+':'+str(result)[:700])
    return result


def _string_bindings(facts,pooled):
    """Bind every actual parent call to the independently proved pool reader."""
    target=pooled['targetRva'];joined=[]
    for fact in facts:
        wrapper=fact['dispatcher']['wrapperName']
        for read in fact['orderedSourceReads']:
            if read.get('readKind',read.get('kind'))not in('byte-payload','string'):continue
            actual=read.get('sourceTargetRva')
            if actual!=target:
                raise ValueError(LABEL+'.source:pooled-parent-target:'+wrapper+':member='+str(read['memberIndex'])
                    +':expected='+str(target)+':actual='+str(actual))
            joined.append(dict(wrapperName=wrapper,memberIndex=read['memberIndex'],
                sourceCallsiteRva=read['sourceCallsiteRva'],sourceTargetRva=actual))
    return joined


def _external_identities(identities,required,caps,*,label):
    """Bind nominal reference requirements to exact selected child readers."""
    expected={name for name in required if caps[name].get('typeName')is not None}
    if not isinstance(identities,dict)or set(identities)!=expected:
        raise ValueError(LABEL+'.source:'+label+'-external-identity-scope')
    for name,row in identities.items():
        if (not isinstance(row,dict)
                or set(row)!={'typeName','referenceReaderMethodDefinition','referenceReaderTargetRva'}
                or not isinstance(row['typeName'],str)or not row['typeName']
                or type(row['referenceReaderMethodDefinition'])is not int or row['referenceReaderMethodDefinition']<0
                or type(row['referenceReaderTargetRva'])is not int or row['referenceReaderTargetRva']<=0
                or any(caps[name].get(key)!=value for key,value in row.items())):
            raise ValueError(LABEL+'.source:'+label+'-external-identity-join='+name)


def _compose_blackboard(component,inputs,*,kind):
    if kind not in('double','int'):raise ValueError(LABEL+'.source:unreviewed-blackboard-kind')
    nominal='Beyond.Blackboard+Blackboard'+('Double'if kind=='double'else'Int')
    expected=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in(
        ('blackboardKey','pooled-string','byte-payload'),('useBlackboardKey','bool',None),
        ('value','single-bits'if kind=='double'else'int32',None))]
    cap=component.get('capabilities',{}).get('skill-blackboard-'+kind,{})
    if (component.get('status')!='validated-conditional-blackboard-'+kind
            or component.get('nativeInputs')!=inputs or cap.get('typeName')!=nominal
            or type(cap.get('memberCount'))is not int or cap['memberCount']!=3
            or cap.get('orderedReads')!=expected or cap.get('nullMarker')!=255
            or any(cap.get(key)is not True for key in('nullAdmitted','wholeGrammarAdmitted',
                'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
            or type(cap.get('referenceReaderMethodDefinition'))is not int
            or type(cap.get('referenceReaderTargetRva'))is not int):
        raise ValueError(LABEL+'.source:unproved-blackboard-'+kind+'-composition')
    return dict(cap,ordinaryOriginalReadValueAdmitted=True)


def _compose_blackboard_vector(component,inputs,*,dimensions,scalar_cap):
    if type(dimensions)is not int or dimensions not in(2,3):raise ValueError(LABEL+'.source:unreviewed-blackboard-vector')
    name='blackboard-vector'+str(dimensions)
    cap=component.get('capabilities',{}).get('skill-'+name,{})
    if (component.get('status')!='validated-conditional-'+name or component.get('nativeInputs')!=inputs
            or cap.get('typeName')!='Beyond.Blackboard+BlackboardVector'+str(dimensions)
            or type(cap.get('memberCount'))is not int or cap['memberCount']!=dimensions
            or cap.get('orderedReads')!=[dict(fieldName=field,kind='record',childCapability='skill-blackboard-double')for field in('x','y','z')[:dimensions]]
            or any(cap.get(key)is not True for key in('nullAdmitted','wholeGrammarAdmitted',
                'ordinaryOriginalReadValueAdmitted','ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
            or type(cap.get('nullMarker'))is not int or cap['nullMarker']!=255
            or 'fixedWireBytes'not in cap or cap['fixedWireBytes']is not None
            or type(cap.get('referenceReaderMethodDefinition'))is not int
            or type(cap.get('referenceReaderTargetRva'))is not int):
        raise ValueError(LABEL+'.source:unproved-'+name+'-composition')
    inner=component.get('proof',{}).get('blackboardDouble',{})
    if _compose_blackboard(inner,inputs,kind='double')!=scalar_cap:
        raise ValueError(LABEL+'.source:different-'+name+'-scalar-child')
    return dict(cap)


def _compose_blackboard_vector3(component,inputs,*,scalar_cap):
    return _compose_blackboard_vector(component,inputs,dimensions=3,scalar_cap=scalar_cap)


def _compose_ec(component,inputs,caps):
    from scripts.game_data.memorypack.skill_ec_components import ORDERS,NAMES
    selected=component.get('capabilities',{})
    if (component.get('schema')!='endfield.skill-ec-components.v1'
            or component.get('status')!='validated-conditional-finite-ec-components'
            or component.get('nativeInputs')!=inputs or component.get('wholeSkillDataAdmitted')is not False
            or set(selected)!=set(NAMES.values())
            or component.get('requiredExternalCapabilities')!=['SelectorFinder','byte-payload','target-postprocessor-list','target-validator-list']):
        raise ValueError(LABEL+'.source:unproved-ec-component-scope')
    for typename,name in NAMES.items():
        cap=selected[name]
        expected=[]
        for index,(field,kind,child)in enumerate(ORDERS[typename]):
            wire={'bool':'bool-byte','int':'scalar32','pool':'byte-payload','list':'reference-list'}.get(kind,
                'selector-union'if child=='SelectorFinder'else child)
            expected.append(dict(memberIndex=index,fieldName=field,kind=wire,childCapability=child))
        if (cap.get('typeName')!=typename or cap.get('memberCount')!=len(ORDERS[typename])
                or type(cap.get('memberCount'))is not int
                or cap.get('orderedReads')!=expected
                or any(cap.get(key)is not True for key in('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
                    'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved','finiteSelectorRoutesRequireExplicitPrograms'))
                or type(cap.get('referenceReaderMethodDefinition'))is not int or type(cap.get('referenceReaderTargetRva'))is not int
                or type(cap.get('recursiveDepthLimit'))is not int or cap['recursiveDepthLimit']!=64
                or cap.get('nullAdmitted')is not True or type(cap.get('nullMarker'))is not int or cap['nullMarker']!=255):
            raise ValueError(LABEL+'.source:unproved-ec-record='+name)
    caps.update(selected)


def _compose_ec_external(component,caps):
    identities=component.get('requiredExternalSourceIdentities',{})
    if set(identities)!={'SelectorFinder','target-postprocessor-list','target-validator-list'}:
        raise ValueError(LABEL+'.source:ec-external-source-scope')
    for name,identity in identities.items():
        cap=caps.get(name,{})
        if name=='SelectorFinder':
            actual=dict(typeName=cap.get('typeName'),readerMethod='ReadValue',
                readerMethodDefinition=cap.get('referenceReaderMethodDefinition'),readerTargetRva=cap.get('referenceReaderTargetRva'))
            valid=cap.get('positiveRoutesRequireExplicitProgram')is True and cap.get('wholeGrammarAdmitted')is False and bool(cap.get('admittedRouteTags'))
        else:
            actual=dict(typeName=cap.get('closedListType'),readerMethod='ReadPackable',
                readerMethodDefinition=cap.get('packableReaderMethodDefinition'),readerTargetRva=cap.get('packableReaderTargetRva'))
            valid=cap.get('positiveCountsAdmitted')is True and cap.get('elementGrammarAdmitted')is True
        if (actual!=identity or not valid or cap.get('nullAdmitted',cap.get('nullable'))is not True
                or type(actual.get('readerMethodDefinition'))is not int or actual['readerMethodDefinition']<0
                or type(actual.get('readerTargetRva'))is not int or actual['readerTargetRva']<=0):
            raise ValueError(LABEL+'.source:ec-external-source-join='+name)
    if caps.get('byte-payload',{}).get('wholeGrammarAdmitted')is not True:
        raise ValueError(LABEL+'.source:ec-missing-selected-pool')


def _uniform_reference_context(read,contexts,rows,*,base):
    """Join indexed or unindexed declarations to the actual RDX definition."""
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    indexed=['memberIndex'in row for row in contexts]
    if not contexts or any(indexed)and not all(indexed):
        raise ValueError(LABEL+'.source:uniform-reference-context-shape')
    calls=[i for i,row in enumerate(rows)if ec.va(row)==base+read['sourceCallsiteRva']]
    if len(calls)!=1:raise ValueError(LABEL+'.source:uniform-reference-actual-call')
    definition=ec.last_write(rows,calls[0],'rdx')
    if definition is None:raise ValueError(LABEL+'.source:uniform-reference-missing-RDX-definition')
    candidates=[row for row in contexts if row.get('instructionRva')==ec.va(definition)-base]
    if len(candidates)!=1:raise ValueError(LABEL+'.source:uniform-reference-one-actual-context')
    context=candidates[0]
    if 'memberIndex'in context and(type(context['memberIndex'])is not int or context['memberIndex']!=read['memberIndex']):
        raise ValueError(LABEL+'.source:uniform-reference-context-member')
    return dict(context,memberIndex=read['memberIndex'])


def _uniform_reference_bindings(image,inputs,facts,caps):
    """Bind actual nominal parent loads/calls to the composed reference owners."""
    from scripts.game_data.memorypack.skill_root_child_bindings import bind_read_value
    from scripts.game_data.memorypack.skill_timeline_dependencies import _context_binding
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    bindings=[]
    for fact in facts:
        rows=None
        for read in fact['orderedSourceReads']:
            _,name=source._operation(fact['sourceOwner'],read)
            if name not in caps or caps[name].get('typeName')is None:continue
            if rows is None:
                method,=[m for m in fact['methods']if m[1:3]==[fact['dispatcher']['wrapperName'],'Deserialize']]
                _,_,rows=ec.family(image,method[3])
            context=_uniform_reference_context(read,fact['nestedContexts'],rows,base=image.pe.image_base)
            cap=caps[name]
            source_join=_context_binding(image,fact,context,expected_type=cap['typeName'],method_name='ReadValue',
                method_definition=cap['referenceReaderMethodDefinition'],target=cap['referenceReaderTargetRva'],
                type_kind=18,type_definition=context.get('typeDefinition'),label=LABEL+'.uniformReference')
            usage=source_join['usage']
            binding=bind_read_value(inputs,dict(fieldName=read['fieldName'],typeName=caps[name]['typeName'],
                typedRequest=usage,sourceTargetRva=read['sourceTargetRva']),
                dict(nativeInputs=inputs,capabilities={name:caps[name]}),name)
            bindings.append(dict(wrapperName=fact['dispatcher']['wrapperName'],memberIndex=read['memberIndex'],
                actualUsage=usage,actualSourceJoin=source_join,**binding))
    return bindings


def _compose_root(component,inputs,caps):
    """Join an independently rederived complete caller and finite child prefix."""
    from scripts.game_data.memorypack.skill_root_components import root_reads
    if (component.get('schema')!='endfield.skill-root-components.v2'
            or component.get('status')!='validated-conditional-root-prefix-components'
            or component.get('nativeInputs')!=inputs
            or component.get('wholeSkillDataAdmitted')is not False
            or component.get('completeSelectedReturnProved')is not True
            or component.get('orderedReads')!=root_reads()
            or not isinstance(component.get('capabilities'),dict)
            or caps.keys()&component['capabilities'].keys()):
        raise ValueError(LABEL+'.source:unproved-current-root-components')
    claim=component['capabilities'].get('SkillDataContinuation',{})
    reads=validate_continuation(claim);last=claim['lastMemberIndex']
    if (component.get('lastCompleteMember')!=last or type(component['lastCompleteMember'])is not int
            or component.get('nextMemberIndex')!=last+1
            or reads!=component['orderedReads'][:last]):
        raise ValueError(LABEL+'.source:root-continuation-order-or-range')
    external=component.get('requiredExternalCapabilities')
    referenced=list(reads)
    for cap in component['capabilities'].values():
        if not isinstance(cap,dict):raise ValueError(LABEL+'.source:root-child-capability-shape')
        referenced.extend(cap.get('orderedReads',[]))
        if cap.get('elementCapability')is not None:referenced.append(dict(childCapability=cap['elementCapability']))
    required=set()
    for read in referenced:
        if not isinstance(read,dict):raise ValueError(LABEL+'.source:root-child-read-shape')
        child=read.get('childCapability')
        if read.get('kind')=='pooled-string':required.add('byte-payload')
        if child is not None:
            if not isinstance(child,str):raise ValueError(LABEL+'.source:root-child-reference-shape')
            if child not in component['capabilities']:required.add(child)
    if (not isinstance(external,list)
            or any(not isinstance(name,str)or name not in caps or caps[name].get('wholeGrammarAdmitted')is not True for name in external)
            or len(external)!=len(set(external))or set(external)!=required):
        raise ValueError(LABEL+'.source:root-external-capability-join')
    _external_identities(component.get('requiredExternalCapabilityIdentities',{}),required,caps,label='root')
    caps.update(component['capabilities'])
    if last==48:
        if component.get('pendingJoins')!=[]:
            raise ValueError(LABEL+'.source:complete-root-has-pending-joins')
        caps['SkillDataComplete']=dict(memberCount=49,firstMemberIndex=0,lastMemberIndex=48,
            completeSelectedReturnProved=True,allRootChildSourceJoinsProved=True,
            actionGroupUsesSelectedFinitePrograms=True,physicalEofRequired=True,
            existingRootWrapperRequired=True,newOrNullRootAdmitted=False,
            runtimeSelectionObserved=False,wholeTypeAllPossibleRoutesAdmitted=False)


def _compose_buff_filter(component,inputs,caps):
    from scripts.game_data.memorypack.skill_selector_buff_filter_components import CAPABILITY,CHILD_CAPABILITY,TYPE,ORDER
    if (component.get('schema')!='endfield.skill-selector-buff-filter-components.v1'
            or component.get('status')!='validated-conditional-BuffFilter-components'
            or component.get('nativeInputs')!=inputs or component.get('wholeSkillDataAdmitted')is not False
            or set(component.get('capabilities',{}))!={CAPABILITY} or CAPABILITY in caps
            or component.get('requiredExternalCapabilities')!=[CHILD_CAPABILITY]):
        raise ValueError(LABEL+'.source:unproved-BuffFilter-scope')
    cap=component['capabilities'][CAPABILITY]
    if (cap.get('typeName')!=TYPE or type(cap.get('memberCount'))is not int or cap['memberCount']!=2
            or cap.get('orderedReads')!=ORDER or any(cap.get(k)is not True for k in('wholeGrammarAdmitted',
                'ordinaryOriginalReadValueAdmitted','ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved','nullAdmitted'))
            or type(cap.get('nullMarker'))is not int or cap['nullMarker']!=255
            or type(cap.get('referenceReaderMethodDefinition'))is not int or cap['referenceReaderMethodDefinition']<0
            or type(cap.get('referenceReaderTargetRva'))is not int or cap['referenceReaderTargetRva']<=0):
        raise ValueError(LABEL+'.source:unproved-BuffFilter-grammar')
    if caps.get(CHILD_CAPABILITY,{}).get('wholeGrammarAdmitted')is not True:
        raise ValueError(LABEL+'.source:unproved-BuffFilter-child')
    _external_identities(component.get('requiredExternalCapabilityIdentities',{}),{CHILD_CAPABILITY},caps,label='BuffFilter')
    caps[CAPABILITY]=cap


def _compose_selectors(component,inputs,caps,programs,requirements):
    """Join only the finite component's exact declared current route scope."""
    families={'SelectorFinder','SelectorValidator','SelectorPostProcessor'}
    lists={'target-postprocessor-list':'SelectorPostProcessor','target-validator-list':'SelectorValidator'}
    if (component.get('status')!='validated-finite-current-selector-routes'
            or component.get('nativeInputs')!=inputs
            or component.get('wholeSkillDataAdmitted')is not False
            or set(component.get('capabilities',{}))!=families|lists.keys()
            or component.get('nullUnions')!={family:True for family in families}
            or any(type(value)is not bool for value in component['nullUnions'].values())
            or caps.keys()&families):
        raise ValueError(LABEL+'.source:unproved-current-selector-scope')
    identities={(row['family'],row['tag'])for row in programs};by_family={family:[]for family in families}
    for row in component.get('programs',[]):
        validate_program(row);identity=(row['family'],row['tag'])
        if (row['family']not in families or identity in identities
                or row['wrapperNullAdmitted']is not True or row['sourceOwner']!=CONTRACT_PATH.name):
            raise ValueError(LABEL+'.source:selector-route-scope')
        identities.add(identity);by_family[row['family']].append(row['tag'])
    for family,tags in by_family.items():
        selected=component['capabilities'][family]
        if (not tags or selected.get('admittedRouteTags')!=sorted(tags)
                or selected.get('wholeGrammarAdmitted')is not False
                or selected.get('positiveRoutesRequireExplicitProgram')is not True):
            raise ValueError(LABEL+'.source:selector-route-capability='+family)
    for name,family in lists.items():
        old=caps.get(name,{});selected=component['capabilities'][name]
        if (any(selected.get(key)!=old.get(key)for key in('elementType','closedListType',
                'referenceReaderTargetRva','referenceReaderMethodDefinition','packableReaderTargetRva',
                'packableReaderMethodDefinition','nullable'))
                or selected.get('collectionCounts')!=[-1,0]
                or any(type(n)is not int for n in selected['collectionCounts'])
                or selected.get('positiveCountsAdmitted')is not True
                or type(selected.get('countLimit'))is not int or selected['countLimit']!=10000
                or selected.get('elementCapability')!=family
                or selected.get('elementGrammarAdmitted')is not True
                or selected.get('admittedRouteTags')!=by_family[family]):
            raise ValueError(LABEL+'.source:selector-list-parent-join='+name)
    referenced={r['childCapability']for row in component['programs']for r in row['reads']if r['childCapability']is not None}
    from scripts.game_data.memorypack.skill_root_child_bindings import collection_identity
    collections=component.get('requiredExternalCollectionIdentities',{})
    if not isinstance(collections,dict)or not set(collections)<=referenced:
        raise ValueError(LABEL+'.source:selector-collection-identity-scope')
    rows=component.get('proof',{}).get('nonzeroChildren',{}).get('proof',{}).get('collectionChildren',[])
    used=set()
    for row in rows:
        name=row.get('listCapability');source=row.get('source',{})
        if (name!='skill-selector-hitbox-shape-list'or name not in collections
                or source.get('schema')!='endfield.skill-action-nested-record-list.v1'
                or source.get('status')!='validated-conditional-action-nested-record-list'
                or source.get('nativeInputs')!=inputs or source.get('parentFieldAdmitted')is not False
                or source.get('wholeOwnerAdmitted')is not False):
            raise ValueError(LABEL+'.source:selector-collection-source')
        identity=collection_identity(source,name)
        if (identity!=collections[name]or identity['elementCapabilityShape']!=caps.get(identity['elementCapability'])
                or name in caps and caps[name]!=source['capabilities'][name]):
            raise ValueError(LABEL+'.source:selector-collection-element-join')
        caps[name]=source['capabilities'][name];used.add(name)
    if used!=set(collections):raise ValueError(LABEL+'.source:selector-collection-source-bijection')
    if any(name not in caps for name in referenced):
        raise ValueError(LABEL+'.source:selector-child-capability-join:missing')
    managed=component.get('requiredExternalManagedValueIdentities',{})
    if (not isinstance(managed,dict)or not set(managed)<=referenced
            or any(shape!=caps.get(name)for name,shape in managed.items())):
        raise ValueError(LABEL+'.source:selector-managed-value-capability-join')
    _external_identities(component.get('requiredExternalCapabilityIdentities',{}),referenced-set(managed)-set(collections),caps,label='selector')
    for row in component['programs']:
        children=sorted({r['childCapability']for r in row['reads']if r['childCapability']is not None})
        if any(name not in caps or(caps[name].get('elementGrammarAdmitted')is not True if name in collections
                else caps[name].get('wholeGrammarAdmitted')is not True)for name in children):
            raise ValueError(LABEL+'.source:selector-child-capability-join='+row['wrapperName'])
        programs.append(row);requirements[row['family']+':'+str(row['tag'])]=children
    caps.update(component['capabilities'])
    return component['nullUnions']


def _compose_wrapper_nulls(component,inputs,programs):
    """A tagged-wrapper FF proof changes only its exact matching route row."""
    if (component.get('status')!='validated-current-wrapper-null-paths'
            or component.get('nativeInputs')!=inputs
            or component.get('unionNullAdmitted')is not False
            or component.get('positiveGrammarAdmitted')is not False):
        raise ValueError(LABEL+'.source:unproved-wrapper-null-scope')
    expected={(row['family'],row['tag'],row['wrapperName'],row['wrappedType'])for row in programs
        if row['family']=='AbilityActionData'and row['wrapperNullAdmitted']is False}
    actual=[]
    for row in component.get('routes',[]):
        selected=row.get('program',{})
        if (any(type(selected.get(key))is not int for key in('marker','headerBytes','clearedReferenceBytes'))
                or (selected.get('marker'),selected.get('headerBytes'),selected.get('clearedReferenceBytes'))!=(255,1,8)
                or selected.get('normalReturn')is not True or selected.get('entryRspRestored')is not True):
            raise ValueError(LABEL+'.source:wrapper-null-program-boundary')
        actual.append(tuple(row.get(key)for key in('family','tag','wrapperName','wrappedType')))
    if len(actual)!=len(set(actual))or set(actual)!=expected:
        raise ValueError(LABEL+'.source:wrapper-null-route-bijection')
    for row in programs:
        if (row['family'],row['tag'],row['wrapperName'],row['wrappedType'])in expected:
            row['wrapperNullAdmitted']=True


def _compose_actions(component,inputs,caps,programs,requirements):
    """Append disjoint routes only after their exact selected child joins."""
    from scripts.game_data.memorypack.skill_action_component_bindings import prepare_extension
    from scripts.game_data.memorypack import skill_gait_dictionary_components as gait
    for child in component.get('proof',{}).get('staticReferenceChildren',[]):
        if (child.get('schema')!=gait.SCHEMA or child.get('nativeInputs')!=inputs
                or child.get('status')!='validated-conditional-static-out-dictionary'
                or child.get('parentFieldAdmitted')is not False or child.get('wholeOwnerAdmitted')is not False):
            raise ValueError(LABEL+'.source:static-reference-child-scope')
        p=child['proof'];cap=gait.compose(inputs,p['source'],p['single'],p['enum'],p['keyDispatch'])
        if child.get('capabilities')!={gait.CAPABILITY:cap}or(gait.CAPABILITY in caps and caps[gait.CAPABILITY]!=cap):
            raise ValueError(LABEL+'.source:static-reference-child-capability')
        caps[gait.CAPABILITY]=cap
    selected=prepare_extension(component,inputs,caps,programs)
    collections=set(selected['requiredExternalCollectionIdentities'])
    managed=set(selected['requiredExternalManagedValueIdentities'])
    static=set(selected['requiredExternalStaticReferenceIdentities'])
    _external_identities(selected['requiredExternalCapabilityIdentities'],
        set(selected['requiredExternalCapabilities'])-collections-managed-static,caps,label='current-actions')
    if requirements.keys()&selected['routeRequirements'].keys():
        raise ValueError(LABEL+'.source:current-actions-requirement-collision')
    programs.extend(selected['programs']);requirements.update(selected['routeRequirements'])


def _compose_action_reference_records(component,inputs,caps,names):
    """Keep each new ordinary record's exact decoder program and ABI."""
    from scripts.game_data.memorypack.skill_root_children_codec import REFERENCE_RECORDS
    if component.get('nativeInputs')!=inputs:
        raise ValueError(LABEL+'.source:action-record-native-inputs')
    selected={}
    for name in names:
        nominal,order=REFERENCE_RECORDS[name];cap=component['capabilities'].get(name,{})
        expected=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in order]
        if (cap.get('typeName')!=nominal or type(cap.get('memberCount'))is not int
                or cap['memberCount']!=len(order)or cap.get('orderedReads')!=expected
                or type(cap.get('nullMarker'))is not int or cap['nullMarker']!=255
                or not all(cap.get(key)is True for key in('wholeGrammarAdmitted','nullAdmitted',
                    'ordinaryOriginalReadValueAdmitted','ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
                or type(cap.get('referenceReaderMethodDefinition'))is not int or cap['referenceReaderMethodDefinition']<0
                or type(cap.get('referenceReaderTargetRva'))is not int or cap['referenceReaderTargetRva']<=0
                or name in caps):
            raise ValueError(LABEL+'.source:action-record-program='+name)
        selected[name]=cap
    caps.update(selected)


def _compose_pull_collection(component,inputs,caps):
    from scripts.game_data.memorypack import skill_pull_attenuation_sources as owner
    from scripts.game_data.memorypack.skill_pull_attenuation_codec import require_capability
    from scripts.game_data.memorypack.skill_root_child_bindings import collection_identity
    if (component.get('schema')!='endfield.skill-pull-attenuation-list.v1'
            or component.get('status')!='validated-conditional-pull-value-list'
            or component.get('nativeInputs')!=inputs or component.get('wholeOwnerAdmitted')is not False
            or component.get('parentFieldAdmitted')is not False
            or set(component.get('capabilities',{}))!={owner.CAPABILITY,owner.LIST}
            or component.get('requiredExternalCapabilities')!=[owner.CHILD]):
        raise ValueError(LABEL+'.source:pull-value-list-scope')
    cap=require_capability(component['capabilities'][owner.CAPABILITY])
    identity=collection_identity(component,owner.LIST)
    _external_identities(component.get('requiredExternalCapabilityIdentities'),{owner.CHILD},caps,label='pull-value-list')
    proof=component.get('proof',{});child=proof.get('child',{});transfer=proof.get('transfer',{})
    reference=child.get('referenceChild',{})
    if (identity['elementCapabilityShape']!=cap or child.get('nativeInputs')!=inputs
            or child.get('typeName')!=owner.TYPE or child.get('wrapperName')!=owner.WRAPPER
            or transfer.get('nativeInputs')!=inputs or transfer.get('typeName')!=owner.TYPE
            or transfer.get('status')!='proved-selected-pull-value16-transfer'
            or reference.get('nativeInputs')!=inputs or reference.get('capabilities',{}).get(owner.CHILD)!=caps.get(owner.CHILD)
            or owner.CAPABILITY in caps and caps[owner.CAPABILITY]!=cap):
        raise ValueError(LABEL+'.source:pull-value-list-transfer-or-SuperArmor-shape')
    caps[owner.CAPABILITY]=cap


def _compose_action_collections(component,inputs,caps):
    """Join action-only lists to the enclosing operation's exact element caps."""
    from scripts.game_data.memorypack.skill_root_child_bindings import collection_identity
    from scripts.game_data.memorypack.enum_list_native_sources import ENUM_TYPES,SCHEMA as ENUM_LIST_SCHEMA
    from scripts.game_data.memorypack.skill_enum_list_codec import require_capability as require_enum_list,element_capability
    names={'skill-action-target-settings-list','skill-action-blackboard-string-list','skill-action-sequence-list',
        'skill-action-blackboard-double-list','skill-action-blackboard-buff-id-list',
        'skill-action-selector-validator-list','skill-action-selector-postprocessor-list',
        'skill-action-damage-unit-list','damage-cost-data-list','damage-processor-list','skill-action-create-buff-input-list',
        'skill-action-keyword-edit-list','skill-action-global-buff-input-list','skill-action-global-buff-id-list',
        'skill-action-battle-command-mapping-list','skill-action-attribute-override-list',
        'skill-action-read-skill-setting-list','skill-action-switch-option-list','skill-action-ordinary-ability-map-list',
        'skill-action-special-aim-shape-list','skill-action-raycast-data-list','skill-action-camera-transition-and-list','skill-action-pull-attenuation-list','skill-action-projectile-preset-point-list','skill-look-at-target-info-list'}
    enum_names={'skill-enum-list:'+name:name for name in ENUM_TYPES};names.update(enum_names)
    selected=dict(caps)
    for row in component['proof']['collectionChildren']:
        name=row.get('listCapability')
        if name not in names:continue
        if (row.get('schema')!='endfield.skill-action-collection-sources.v1'
                or row.get('status')!='validated-conditional-action-list-child' or row.get('nativeInputs')!=inputs
                or row.get('parentFieldAdmitted')is not False or row.get('wholeSkillDataAdmitted')is not False):
            raise ValueError(LABEL+'.source:action-list-source='+name)
        if name=='skill-action-pull-attenuation-list':_compose_pull_collection(row['proof'],inputs,selected)
        if name in enum_names:
            nominal=enum_names[name];element=element_capability(nominal);child=row['proof'];proof=child.get('proof',{});source=proof.get('source',{})
            callback=row['capabilities'].get(element,{})
            require_enum_list(row['capabilities'].get(name,{}),callback,name=nominal)
            if (child.get('schema')!='endfield.skill-enum-list-child.v1' or child.get('status')!='validated-conditional-enum-list-child'
                    or child.get('nativeInputs')!=inputs or source.get('schema')!=ENUM_LIST_SCHEMA
                    or source.get('status')!='validated-conditional-nominal-enum-lists' or source.get('nativeInputs')!=inputs
                    or child.get('parentFieldAdmitted')is not False or child.get('wholeOwnerAdmitted')is not False
                    or source.get('parentFieldAdmitted')is not False or source.get('wholeOwnerAdmitted')is not False
                    or row['capabilities'][name].get('nativeInputs')!=inputs
                    or source.get('capabilities',{}).get(name)!=row['capabilities'][name]
                    or source.get('capabilities',{}).get(element)!=callback
                    or child.get('capabilities')!={name:row['capabilities'][name],element:callback}
                    or proof.get('actualParentRequestBinding',{}).get('collectionCapability')!=row['capabilities'][name]
                    or tuple(proof['actualParentRequestBinding'].get('sourceRequest',{}).get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
                        !=(6,'MemoryPack.MemoryPackReader','ReadPackable',[],['System.Collections.Generic.List`1<'+nominal+'>'])
                    or proof['actualParentRequestBinding'].get('packableReaderMethodDefinition')!=row['binding'].get('readerMethodDefinition')
                    or proof['actualParentRequestBinding'].get('packableReaderTargetRva')!=row['binding'].get('sourceTargetRva')
                    or element in selected and selected[element]!=callback):
                raise ValueError(LABEL+'.source:enum-list-nominal-child-or-parent='+name)
            selected[element]=callback
        identity=collection_identity(row,name);element=identity['elementCapability']
        if (identity['elementCapabilityShape']!=selected.get(element)
                or row['binding'].get('collectionIdentity')!=identity
                or name in selected and selected[name]!=row['capabilities'][name]):
            raise ValueError(LABEL+'.source:action-list-element-or-identity='+name)
        selected[name]=row['capabilities'][name]
    caps.update(selected)


def _compose_curve(component,inputs):
    from scripts.game_data.memorypack.skill_animation_curve_codec import require_capability
    if (component.get('schema')!='endfield.skill-animation-curve-sources.v1'
            or component.get('status')!='validated-conditional-unity-animation-curve'
            or component.get('nativeInputs')!=inputs or component.get('wholeSkillDataAdmitted')is not False):
        raise ValueError(LABEL+'.source:action-curve-source')
    return require_capability(component['capabilities']['skill-animation-curve'])


def _compose_damage(component,inputs,caps):
    """A complete DamageUnit still owes all enclosing action/list joins."""
    shared={'scalar-payload','blackboard-vector3','skill-root-cost-data','skill-root-attribute-modifier',
        'skill-root-gameplay-tag','byte-payload'}
    owned={'skill-terrain-effect-data','skill-terrain-effect-array','skill-effect-action-config',
        'damage-hit-sound-data','damage-calculation-union','damage-processor-union',
        'damage-cost-data-list','damage-processor-list','damage-gameplay-tag-list','skill-damage-unit'}
    shapes=component.get('requiredExternalCapabilityShapes',{})
    if (component.get('schema')!='endfield.skill-damage-components.v1'
            or component.get('status')!='validated-conditional-complete-DamageUnit-grammar'
            or component.get('nativeInputs')!=inputs or component.get('wholeDamageUnitAdmitted')is not True
            or any(component.get(key)is not False for key in('actualEnclosingParentAdmitted','wholeSkillDataAdmitted'))
            or component.get('requiredExternalCapabilities')!=sorted(shared)or set(shapes)!=shared
            or any(shapes[name]!=caps.get(name)for name in shared)
            or set(component.get('capabilities',{}))!=owned or caps.keys()&owned):
        raise ValueError(LABEL+'.source:complete-DamageUnit-or-shared-join')
    caps.update(component['capabilities'])


def _compose_hit_env(component,inputs,caps):
    from scripts.game_data.memorypack.skill_hit_env_sources import TYPE,CAPABILITY,ORDER,CHILD
    cap=component.get('capabilities',{}).get(CAPABILITY,{})
    if (component.get('schema')!='endfield.skill-hit-env-sources.v1'
            or component.get('status')!='validated-conditional-hit-env-data' or component.get('nativeInputs')!=inputs
            or any(component.get(key)is not False for key in('wholeDamageActionAdmitted','wholeSkillDataAdmitted'))
            or component.get('requiredExternalCapabilities')!=[CHILD]or CAPABILITY in caps
            or cap.get('typeName')!=TYPE or type(cap.get('memberCount'))is not int or cap['memberCount']!=4
            or cap.get('orderedReads')!=ORDER or any(type(read.get('memberIndex'))is not int for read in cap['orderedReads'])
            or type(cap.get('nullMarker'))is not int or cap['nullMarker']!=255
            or not all(cap.get(key)is True for key in('wholeGrammarAdmitted','nullAdmitted','ordinaryOriginalReadValueAdmitted',
                'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved','completeSourceOwnedProgram'))
            or type(cap.get('referenceReaderMethodDefinition'))is not int or cap['referenceReaderMethodDefinition']<0
            or type(cap.get('referenceReaderTargetRva'))is not int or cap['referenceReaderTargetRva']<=0):
        raise ValueError(LABEL+'.source:hit-env-program-or-child-scope')
    _external_identities(component.get('requiredExternalCapabilityIdentities'),{CHILD},caps,label='hit-env')
    caps[CAPABILITY]=cap


def _compose_action_settings(component,inputs,caps,names):
    from scripts.game_data.memorypack.skill_action_setting_codec import require_capability,CAPABILITIES
    from scripts.game_data.memorypack.skill_root_child_bindings import collection_identity
    if (component.get('schema')!='endfield.skill-action-setting-sources.v1'
            or component.get('status')!='validated-conditional-action-settings' or component.get('nativeInputs')!=inputs
            or component.get('wholeSkillDataAdmitted')is not False
            or not names or len(names)!=len(set(names))or not set(names)<=set(CAPABILITIES)):
        raise ValueError(LABEL+'.source:action-settings-scope')
    selected={name:require_capability(component['capabilities'].get(name,{}),name)for name in names}
    required={read['childCapability']for cap in selected.values()for read in cap['orderedReads']if read['childCapability']is not None}
    collections=component.get('requiredExternalCollectionIdentities',{})
    if (component.get('requiredExternalCapabilities')!=sorted(required)or set(collections)!=(required&{'skill-root-pooled-string-list'})
            or set(component.get('capabilities',{}))!=set(selected)|set(collections)
            or set(selected)&caps.keys()):
        raise ValueError(LABEL+'.source:action-settings-child-scope')
    for name,identity in collections.items():
        if (component['capabilities'][name]!=caps.get(name)or collection_identity(component,name)!=identity
                or collection_identity(dict(capabilities=caps),name)!=identity):
            raise ValueError(LABEL+'.source:action-settings-collection='+name)
    _external_identities(component.get('requiredExternalCapabilityIdentities'),required-set(collections),caps,label='action-settings')
    caps.update(selected)


def _compose_create_buff_input(component,inputs,caps):
    from scripts.game_data.memorypack.skill_action_create_buff_input_sources import CAPABILITY,SHARED
    if (component.get('schema')!='endfield.skill-action-create-buff-input-sources.v1'
            or component.get('status')!='validated-conditional-ordinary-create-buff-input'
            or component.get('nativeInputs')!=inputs or set(component.get('capabilities',{}))!={CAPABILITY}
            or any(component.get(key)is not False for key in('wholeEnclosingActionAdmitted','wholeSkillDataAdmitted'))
            or component.get('requiredExternalCapabilities')!=[*SHARED,'byte-payload']
            or set(component.get('requiredExternalCapabilityShapes',{}))!=set(SHARED)
            or any(component['requiredExternalCapabilityShapes'][name]!=caps.get(name)for name in SHARED)
            or component['capabilities'][CAPABILITY].get('generatedWrapperOnly')is not False):
        raise ValueError(LABEL+'.source:ordinary-CreateBuff-input-or-shared-join')
    _compose_action_reference_records(component,inputs,caps,[CAPABILITY])


def _compose_global_buff_input(component,inputs,caps):
    from scripts.game_data.memorypack import skill_global_buff_input_sources as source
    from scripts.game_data.memorypack.skill_action_managed_value_bindings import require_wire_capability
    shared={'skill-root-assign-pair','skill-root-assign-pair-list'}
    if (component.get('schema')!=source.SCHEMA or component.get('status')!='validated-conditional-global-buff-input'
            or component.get('nativeInputs')!=inputs or component.get('wholeOwnerAdmitted')is not False
            or component.get('requiredExternalCapabilities')!=['byte-payload']
            or set(component.get('capabilities',{}))!=shared|{source.CAPABILITY,source.GLOBAL_CAP}
            or any(component['capabilities'][name]!=caps.get(name)for name in shared)
            or source.GLOBAL_CAP in caps or source.CAPABILITY in caps):
        raise ValueError(LABEL+'.source:GlobalBuff-input-or-shared-join')
    require_wire_capability(component,inputs,source.GLOBAL,source.GLOBAL_CAP)
    selected=dict(caps)
    _compose_action_reference_records(component,inputs,selected,[source.CAPABILITY])
    selected[source.GLOBAL_CAP]=component['capabilities'][source.GLOBAL_CAP]
    caps.update(selected)


def _compose_action_geometry(component,inputs,caps):
    from scripts.game_data.memorypack.skill_action_geometry_codec import CAPABILITIES,require_capability
    from scripts.game_data.memorypack.skill_action_geometry_sources import VECTOR,VECTOR_CAP
    if (component.get('schema')!='endfield.skill-action-geometry-sources.v1'
            or component.get('status')!='validated-conditional-action-geometry'or component.get('nativeInputs')!=inputs
            or component.get('wholeSkillDataAdmitted')is not False
            or set(component.get('capabilities',{}))!=set(CAPABILITIES)
            or component.get('requiredExternalCapabilities')!=['blackboard-vector3','byte-payload']
            or set(CAPABILITIES)&caps.keys()):
        raise ValueError(LABEL+'.source:action-geometry-scope')
    selected={name:require_capability(component['capabilities'][name],name)for name in CAPABILITIES}
    _external_identities(component.get('requiredExternalCapabilityIdentities'),{VECTOR_CAP},caps,label='action-geometry')
    if component['proof']['referenceChildren'][VECTOR]['capabilities']['skill-blackboard-vector3']!=caps.get(VECTOR_CAP):
        raise ValueError(LABEL+'.source:action-geometry-vector-shape')
    caps.update(selected)


def _compose_action_nested_records(component,inputs,caps):
    from scripts.game_data.memorypack.skill_action_nested_record_codec import CAPABILITIES,require_capability
    from scripts.game_data.memorypack.skill_action_nested_record_sources import REFERENCES,DOUBLE,RECORDS,ENVELOPE,VALUE_TYPES
    expected={c for spec in RECORDS.values()for n,t,k,c in spec['members']if c is not None}-set(CAPABILITIES)
    if (component.get('schema')!='endfield.skill-action-nested-record-sources.v1'
            or component.get('status')!='validated-conditional-action-nested-records'
            or component.get('nativeInputs')!=inputs or component.get('wholeOwnerAdmitted')is not False
            or set(component.get('capabilities',{}))!=set(CAPABILITIES)
            or component.get('requiredExternalCapabilities')!=sorted(expected)or set(CAPABILITIES)&caps.keys()):
        raise ValueError(LABEL+'.source:action-nested-record-scope')
    selected={name:require_capability(component['capabilities'][name],name)for name in CAPABILITIES}
    managed=component.get('proof',{}).get('managedValueChildren',{})
    if set(managed)!={ENVELOPE}:raise ValueError(LABEL+'.source:action-nested-record-managed-scope')
    _compose_impulse_envelope(managed[ENVELOPE],inputs,caps)
    envelope_cap=VALUE_TYPES[ENVELOPE][0]
    if component.get('requiredExternalManagedValueIdentities')!={envelope_cap:caps[envelope_cap]}:
        raise ValueError(LABEL+'.source:action-nested-record-managed-identity')
    _external_identities(component.get('requiredExternalCapabilityIdentities'),expected-{'byte-payload',envelope_cap},caps,label='action-nested-records')
    children=component.get('proof',{}).get('referenceChildren',{})
    if set(children)!=set(REFERENCES):raise ValueError(LABEL+'.source:action-nested-record-child-scope')
    joined=dict(caps,**selected)
    for nominal,(capability,wire,operation)in REFERENCES.items():
        child=children[nominal]
        if child.get('nativeInputs')!=inputs:raise ValueError(LABEL+'.source:action-nested-record-child-native='+nominal)
        shape=_compose_blackboard(child,inputs,kind='double')if nominal==DOUBLE else child['capabilities'][capability]
        if shape!=joined.get(operation):raise ValueError(LABEL+'.source:action-nested-record-child-shape='+nominal)
    if caps.get('byte-payload',{}).get('wholeGrammarAdmitted')is not True:
        raise ValueError(LABEL+'.source:action-nested-record-pool')
    caps.update(selected)


def _compose_impulse_envelope(component,inputs,caps):
    from scripts.game_data.memorypack.skill_impulse_envelope_codec import CAPABILITY,require_capability
    if (component.get('schema')!='endfield.impulse-envelope-components.v1'
            or component.get('status')!='validated-conditional-impulse-envelope-components'
            or component.get('nativeInputs')!=inputs or component.get('wholeOwnerAdmitted')is not False
            or component.get('parentFieldAdmitted')is not False
            or component.get('requiredExternalCapabilities')!=['curve-profile']
            or set(component.get('capabilities',{}))!={CAPABILITY,'curve-profile'}
            or component['capabilities']['curve-profile']!=caps.get('curve-profile')):
        raise ValueError(LABEL+'.source:impulse-envelope-scope-or-Curve-shape')
    _external_identities(component.get('requiredExternalCapabilityIdentities'),{'curve-profile'},caps,label='impulse-envelope')
    cap=require_capability(component['capabilities'][CAPABILITY])
    if CAPABILITY in caps and caps[CAPABILITY]!=cap:raise ValueError(LABEL+'.source:impulse-envelope-capability-drift')
    caps[CAPABILITY]=cap




def _compose_action_raycast(component,inputs,caps):
    from scripts.game_data.memorypack import skill_raycast_record_sources as owner
    from scripts.game_data.memorypack.skill_raycast_record_codec import CAPABILITIES,require_capability
    if (component.get('schema')!=owner.SCHEMA
            or component.get('status')!='validated-conditional-raycast-records'
            or component.get('nativeInputs')!=inputs or component.get('wholeOwnerAdmitted')is not False
            or set(component.get('capabilities',{}))!=set(CAPABILITIES) or set(CAPABILITIES)&caps.keys()
            or component.get('requiredExternalCapabilities')!=['blackboard-vector3','curve-profile']):
        raise ValueError(LABEL+'.source:raycast-record-scope')
    selected={name:require_capability(component['capabilities'][name],name)for name in CAPABILITIES}
    _external_identities(component.get('requiredExternalCapabilityIdentities'),{'blackboard-vector3','curve-profile'},caps,label='raycast-records')
    children=component.get('proof',{}).get('referenceChildren',{})
    if set(children)!=set(owner.REFERENCES):raise ValueError(LABEL+'.source:raycast-record-child-scope')
    for nominal,(capability,wire,operation)in owner.REFERENCES.items():
        child=children[nominal]
        if child.get('nativeInputs')!=inputs or child.get('capabilities',{}).get(capability)!=caps.get(operation):
            raise ValueError(LABEL+'.source:raycast-record-child-shape='+nominal)
    caps.update(selected)


def _compose_ordinary_ability_map(component,inputs,caps):
    from scripts.game_data.memorypack import skill_ordinary_ability_map_sources as owner
    from scripts.game_data.memorypack.skill_ordinary_ability_map_codec import require_capability,require_collection
    names={owner.CAPABILITY,owner.ARRAY}
    if (component.get('schema')!=owner.SCHEMA
            or component.get('status')!='validated-conditional-ordinary-ability-map'
            or component.get('nativeInputs')!=inputs or component.get('wholeOwnerAdmitted')is not False
            or component.get('parentFieldAdmitted')is not False
            or set(component.get('capabilities',{}))!=names or names&caps.keys()
            or component.get('requiredExternalCapabilities')!=['SequenceActionData']):
        raise ValueError(LABEL+'.source:ordinary-map-scope')
    selected={owner.CAPABILITY:require_capability(component['capabilities'][owner.CAPABILITY]),
        owner.ARRAY:require_collection(component['capabilities'][owner.ARRAY],array=True)}
    _external_identities(component.get('requiredExternalCapabilityIdentities'),{'SequenceActionData'},caps,label='ordinary-map')
    child=component.get('proof',{}).get('arrayChild',{})
    if (child.get('nativeInputs')!=inputs or child.get('capabilities',{}).get('SequenceActionData')!=caps.get('SequenceActionData')
            or child.get('capabilities',{}).get(owner.ARRAY)!=selected[owner.ARRAY]):
        raise ValueError(LABEL+'.source:ordinary-map-array-or-Sequence-shape')
    caps.update(selected)


def _compose_target_filter(component,inputs,caps):
    from scripts.game_data.memorypack import skill_target_filter_sources as owner
    from scripts.game_data.memorypack.skill_target_filter_codec import require_capability
    from scripts.game_data.memorypack.skill_action_managed_value_bindings import require_wire_capability
    shared={owner.QUERY_CAP,'skill-root-gameplay-tag-array','skill-root-gameplay-tag-raw4'}
    if (component.get('schema')!='endfield.skill-target-filter-sources.v1'
            or component.get('status')!='validated-conditional-target-filter'
            or component.get('nativeInputs')!=inputs or component.get('wholeOwnerAdmitted')is not False
            or component.get('requiredExternalCapabilities')!=[owner.QUERY_CAP]
            or set(component.get('capabilities',{}))!=shared|{owner.CAPABILITY} or owner.CAPABILITY in caps
            or any(component['capabilities'][name]!=caps.get(name)for name in shared)):
        raise ValueError(LABEL+'.source:TargetFilter-scope-or-managed-child-shape')
    cap=require_capability(component['capabilities'][owner.CAPABILITY])
    query=require_wire_capability(component,inputs,owner.QUERY,owner.QUERY_CAP)
    if component.get('requiredExternalManagedValueIdentities')!={owner.QUERY_CAP:query}:
        raise ValueError(LABEL+'.source:TargetFilter-managed-identity')
    caps[owner.CAPABILITY]=cap


def _compose_smart_target(component,inputs,caps):
    from scripts.game_data.memorypack.skill_smart_target_value_sources import CAPABILITY
    from scripts.game_data.memorypack.skill_smart_target_value_codec import require_capability
    names={'skill-root-pooled-string-list','skill-root-gameplay-tag-array','skill-root-gameplay-tag-raw4',
        'skill-root-gameplay-tag-query','skill-root-buff-find-settings','skill-root-buff-id','skill-root-buff-id-list'}
    if (component.get('schema')!='endfield.skill-smart-target-components.v1'
            or component.get('status')!='validated-conditional-smart-target-components'
            or component.get('nativeInputs')!=inputs or component.get('wholeOwnerAdmitted')is not False
            or component.get('parentFieldAdmitted')is not False or component.get('requiredExternalCapabilities')!=['byte-payload']
            or set(component.get('capabilities',{}))!=names|{CAPABILITY}or CAPABILITY in caps
            or caps.get('byte-payload',{}).get('wholeGrammarAdmitted')is not True
            or any(component['capabilities'][name]!=caps[name]for name in names&caps.keys())):
        raise ValueError(LABEL+'.source:SmartTarget-scope-or-own-child-shape')
    require_capability(component['capabilities'][CAPABILITY])
    caps.update(component['capabilities'])


def _compose_look_at_target(component,inputs,caps):
    from scripts.game_data.memorypack import skill_look_at_target_sources as owner
    from scripts.game_data.memorypack.skill_look_at_target_codec import require_record,require_target
    if (component.get('schema')!=owner.SCHEMA or component.get('status')!='validated-conditional-look-at-target'
            or component.get('nativeInputs')!=inputs or component.get('parentFieldAdmitted')is not False
            or component.get('wholeOwnerAdmitted')is not False or component.get('requiredExternalCapabilities')!=[owner.CHILD]
            or set(component.get('capabilities',{}))!={owner.CAPABILITY}
            or component.get('requiredExternalCapabilityShapes')!={owner.CHILD:caps.get(owner.CHILD)}):
        raise ValueError(LABEL+'.source:look-at-target-scope-or-child-shape')
    cap=require_record(component['capabilities'][owner.CAPABILITY]);require_target(caps[owner.CHILD])
    _external_identities(component.get('requiredExternalCapabilityIdentities'),{owner.CHILD},caps,label='look-at-target')
    proof=component['proof'];source=proof['source'];owner.require_source(source,inputs);owner.bind_program(proof['compiled'])
    read=source['orderedSourceReads'][2];usage=proof['typedRequest'];bindings=proof['compiled'].get('childBindings',[])
    expected=dict(fieldName='targetSettings',typeName=owner.TARGET,capability=owner.CHILD,
        readerMethodDefinition=caps[owner.CHILD]['referenceReaderMethodDefinition'],sourceTargetRva=caps[owner.CHILD]['referenceReaderTargetRva'])
    if (proof['target'].get('nativeInputs')!=inputs or proof['target'].get('capabilities',{}).get(owner.CHILD)!=caps[owner.CHILD]
            or bindings!=[expected] or read.get('sourceTargetRva')!=expected['sourceTargetRva']
            or usage.get('methodSpec',[None])[0]!=expected['readerMethodDefinition']
            or read.get('context',{}).get('methodSpec')!=usage.get('methodSpec')
            or tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
                !=(6,'MemoryPack.MemoryPackReader','ReadValue',[],[owner.TARGET])
            or any(cap.get(k)!=proof.get('referenceReaders',{}).get(k)for k in('referenceReaderMethodDefinition','referenceReaderTargetRva'))
            or source['lifecycle']['GetValue']['method']!=proof['adapter'].get('getterMethod')
            or source['method']!=proof['adapter'].get('pairForwarder',{}).get('readerMethod')
            or owner.CAPABILITY in caps and caps[owner.CAPABILITY]!=cap):
        raise ValueError(LABEL+'.source:look-at-own-reader-actual-child-or-descendant')
    caps[owner.CAPABILITY]=cap


def _compose_camera_transitions(component,inputs,caps):
    from scripts.game_data.memorypack import skill_camera_transition_sources as owner
    from scripts.game_data.memorypack.skill_camera_transition_codec import require_leaf,require_and,require_collection
    names={owner.LEAF,owner.INNER_LIST,owner.CAPABILITY}
    if (component.get('schema')!='endfield.skill-camera-transition-sources.v1'
            or component.get('status')!='validated-conditional-camera-transitions'
            or component.get('nativeInputs')!=inputs or component.get('wholeOwnerAdmitted')is not False
            or component.get('parentFieldAdmitted')is not False
            or component.get('requiredExternalCapabilities')!=['byte-payload']
            or set(component.get('capabilities',{}))!=names or names&caps.keys()
            or caps.get('byte-payload',{}).get('wholeGrammarAdmitted')is not True):
        raise ValueError(LABEL+'.source:camera-transition-scope-or-pool')
    selected={owner.LEAF:require_leaf(component['capabilities'][owner.LEAF]),
        owner.CAPABILITY:require_and(component['capabilities'][owner.CAPABILITY]),
        owner.INNER_LIST:require_collection(component['capabilities'][owner.INNER_LIST],outer=False)}
    proof=component.get('proof',{});leaf=proof.get('condition',{});inner=proof.get('inner',{})
    if (leaf.get('nativeInputs')!=inputs or inner.get('nativeInputs')!=inputs
            or leaf.get('capabilities')!={owner.LEAF:selected[owner.LEAF]}
            or inner.get('capabilities')!={owner.LEAF:selected[owner.LEAF],owner.INNER_LIST:selected[owner.INNER_LIST]}):
        raise ValueError(LABEL+'.source:camera-transition-descendant-shape')
    caps.update(selected)


def _compose_special_aim(component,inputs,caps):
    from scripts.game_data.memorypack import skill_special_aim_components as owner
    from scripts.game_data.memorypack.skill_special_aim_codec import require_union,require_sector
    names={owner.CAPABILITY,owner.SECTOR}
    if (component.get('schema')!='endfield.skill-special-aim-components.v1'
            or component.get('status')!='validated-conditional-special-aim-union'
            or component.get('nativeInputs')!=inputs or component.get('wholeOwnerAdmitted')is not False
            or set(component.get('capabilities',{}))!=names or names&caps.keys()
            or component.get('requiredExternalCapabilities')!=['scalar-payload']):
        raise ValueError(LABEL+'.source:SpecialAim-scope')
    selected={owner.CAPABILITY:require_union(component['capabilities'][owner.CAPABILITY]),
        owner.SECTOR:require_sector(component['capabilities'][owner.SECTOR])}
    _external_identities(component.get('requiredExternalCapabilityIdentities'),{'scalar-payload'},caps,label='SpecialAim')
    if _compose_blackboard(component['proof']['blackboardDouble'],inputs,kind='double')!=caps.get('scalar-payload'):
        raise ValueError(LABEL+'.source:SpecialAim-double-shape')
    caps.update(selected)


def derive(image,inputs,*,retain_traces=False):
    """Reprove current sources; source names never supply wire widths."""
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec,skill_animation_curve_sources,buff_23_roles_native
    from scripts.game_data import levelscript_pooled_string_list_native as string_lists,skill_selector_list_sources_native
    proof={};programs=[];facts=[];requirements={}
    # Exact current source owners are deliberately finite. No catalog sweep
    # promotes an additional wrapper or similarly named historical route.
    for owner in sorted(source.UNIFORM_OWNERS):
        fact,joined=source.derive_uniform_source(image,inputs,owner)
        fact=dict(fact,wrappedType=source._selected_wrapper(image,fact['dispatcher']['wrapperName']).wrapped_type)
        program=source.compile_uniform_program(owner,fact,wrapper_null_admitted=False)
        fact['sourceOwner']=owner
        programs.append(program);facts.append(fact);proof[owner]=joined
        required=sorted({r['kind']for r in program['reads']if r['kind']in('layer-mask-raw4','gameplay-tag32')})
        requirements[program['family']+':'+str(program['tag'])]=required
    own=source.derive_own_families(image,inputs);programs+=own['programs'];proof['ownFamilies']=own
    for row in own['programs']:requirements[row['family']+':'+str(row['tag'])]=[]
    proof['uniformPrimitives']=source.primitive_sources(image,facts)
    clones=ec.clone_facts(image,inputs)
    generic_kinds={'blackboard-double','blackboard-scalar','blackboard-vector2','blackboard-vector3','curve-profile','direction-profile',
        'nested-generic','scalar-payload','sequence-profile','skill-alert-profile','target-profile','target-settings'}
    for fact in facts:
        for read in fact['orderedSourceReads']:
            kind=read.get('readKind',read.get('kind'))
            if kind in generic_kinds and read['sourceTargetRva']!=clones['ReadValue']['targetRva']:
                raise ValueError(LABEL+'.source:unproved-reference-target:'+fact['dispatcher']['wrapperName'])
    caps={};child={}
    child['ec']=ec.validate_on_image(image,inputs)
    child['curve']=skill_animation_curve_sources.derive(image,inputs)
    child['alert']=buff_23_roles_native.validate_on_image(image,inputs)
    pooled=pooled_source_helper._contract();child['strings']=pooled_source_helper.validate_on_image(image,image.pe.image_base+pooled['targetRva'],inputs)
    child['strings']['parentBindings']=_string_bindings(facts,pooled)
    for name in('target-profile','direction-profile','selector-profile','curve-profile','skill-alert-profile'):
        caps[name]=dict(nullAdmitted=True,wholeGrammarAdmitted=True)
    caps['curve-profile']=_compose_curve(child['curve'],inputs)
    from scripts.game_data.memorypack import skill_blackboard_double_sources,skill_blackboard_int_sources,skill_blackboard_vector2_sources,skill_blackboard_vector3_sources,skill_sequence_reference_sources
    child['blackboardDouble']=skill_blackboard_double_sources.derive(image,inputs)
    caps['scalar-payload']=_compose_blackboard(child['blackboardDouble'],inputs,kind='double')
    caps['byte-payload']=dict(wholeGrammarAdmitted=True,encoding='int32-pool-index',emptyIndex=-1,nullIndex=-2)
    selector=skill_selector_list_sources_native.validate_on_image(image,inputs)
    child['selectorLists']=selector;caps.update(selector['capabilities'])
    string_fact=json.loads(string_lists.CONTRACT_PATH.read_bytes())
    if string_fact['nativeInputs']!=inputs:raise ValueError(LABEL+'.child:string-list-build-mismatch')
    string_lists._validate_native(image,string_fact)
    child['stringList']=dict(sourceOwner=string_lists.CONTRACT_PATH.name,layout=string_fact['layout'])
    from scripts.game_data.memorypack import skill_inherit_buff_string_list_sources as inherit_strings
    inherit_parents=[fact for fact in facts if fact['dispatcher']['wrapperName']==inherit_strings.WRAPPER]
    if len(inherit_parents)!=1:raise ValueError(LABEL+'.child:one-exact-inherit-string-parent')
    child['inheritBuffStringList']=inherit_strings.derive(image,inputs,parent=inherit_parents[0])
    caps['inherit-buff-string-list']=child['inheritBuffStringList']['capabilities'][inherit_strings.CAPABILITY]
    # All required current components have their own exact selected owner.
    # A missing/refused component refuses regeneration and public admission.
    components={}
    for capability,module_name in CURRENT_COMPONENTS.items():
        result=_selected_component(image,inputs,module_name)
        child[capability]=result;caps[capability]=dict(nullAdmitted=True,wholeGrammarAdmitted=True)
        components[capability]=dict(status='validated',module=module_name)
        if capability in('layer-mask-raw4','gameplay-tag32'):
            if result.get('wireBytes')!=4 or result.get('resultRegister')!='eax':raise ValueError(LABEL+'.child:atomic-ABI')
            for fact in facts:
                for read in fact['orderedSourceReads']:
                    if read.get('readKind',read.get('kind'))==capability and read['sourceTargetRva']!=result['targetRva']:
                        raise ValueError(LABEL+'.child:atomic-source-target='+capability)
    child['blackboardInt']=skill_blackboard_int_sources.derive(image,inputs)
    caps['blackboard-int']=_compose_blackboard(child['blackboardInt'],inputs,kind='int')
    child['blackboardVector3']=skill_blackboard_vector3_sources.derive(image,inputs)
    caps['blackboard-vector3']=_compose_blackboard_vector3(child['blackboardVector3'],inputs,scalar_cap=caps['scalar-payload'])
    child['blackboardVector2']=skill_blackboard_vector2_sources.derive(image,inputs)
    caps['blackboard-vector2']=_compose_blackboard_vector(child['blackboardVector2'],inputs,dimensions=2,scalar_cap=caps['scalar-payload'])
    from scripts.game_data.memorypack import skill_ec_components
    child['ecComponents']=skill_ec_components.derive(image,inputs)
    _compose_ec(child['ecComponents'],inputs,caps)
    containers=source.derive_containers(image,inputs);proof['containers']=containers
    from scripts.game_data.memorypack import skill_cost_data_list_sources as cost
    cost_profile=cost.derive_profile(image);cost_proof=cost.derive(image,inputs,cost_profile)
    proof['costData']=dict(profile=cost_profile,proof=cost_proof)
    caps['cost-data']=dict(nullAdmitted=True,wholeGrammarAdmitted=True)
    caps['cost-data-list']=dict(collectionCounts=list(range(-1,18)),nullable=True,
        positiveCountsAdmitted=False,elementCapability='cost-data')
    proof['sequenceReferenceLifecycle']=skill_sequence_reference_sources.derive(image,inputs)
    from scripts.game_data.memorypack import skill_sequence_components
    proof['sequenceComponents']=skill_sequence_components.derive_on_wire(image,inputs,proof['sequenceReferenceLifecycle'],containers['sequence'])
    caps['SequenceActionData']=proof['sequenceComponents']['capabilities']['SequenceActionData']
    proof['uniformReferenceBindings']=_uniform_reference_bindings(image,inputs,facts,caps)
    caps['TimelineActionData']=dict(nullAdmitted=True,wholeGrammarAdmitted=True)
    caps['ForceSyncAnimData']=dict(nullAdmitted=True,wholeGrammarAdmitted=True)
    caps['ActionGroupData']=dict(nullAdmitted=True,wholeGrammarAdmitted=True,
        passiveCounts=list(range(-1,18)),passiveElementsAdmitted=False,timelineCounts=list(range(-1,18)),wholeSkillDataAdmitted=False)
    from scripts.game_data.memorypack import skill_action_group_count_components
    proof['actionGroupCounts']=skill_action_group_count_components._derive_with_parent(image,inputs,containers['actionGroup'])
    caps['ActionGroupData'].update(proof['actionGroupCounts']['bounds'])
    caps['SkillDataPrefix']=dict(memberCount=49,field0='actionGroupData',field0DirectWireBytes=1,
        wholeGrammarAdmitted=True,wholeSkillDataAdmitted=False)
    from scripts.game_data.memorypack import skill_action_null_source,skill_root_components
    action_null=skill_action_null_source.derive(image,inputs)
    if (action_null.get('status')!='validated' or action_null.get('nativeInputs')!=inputs
            or action_null.get('typeName')!=skill_action_null_source.TYPE
            or action_null.get('wrapperName')!=skill_action_null_source.WRAPPER
            or action_null.get('nullAdmitted')is not True
            or (action_null.get('nullMarker'),action_null.get('consumedBytes'),action_null.get('outputBytes'))!=(255,1,8)
            or action_null.get('positiveAdmitted')is not False
            or action_null.get('reservedMarkersAdmitted')is not False):
        raise ValueError(LABEL+'.source:unproved-current-action-null')
    proof['actionNull']=action_null
    continuation=skill_root_components.derive(image,inputs)
    _compose_root(continuation,inputs,caps);proof['rootContinuation']=continuation
    from scripts.game_data.memorypack import skill_selector_buff_filter_components
    buff_filter=skill_selector_buff_filter_components.derive(image,inputs,
        buff_find_component=continuation['proof']['buffFindSettings'])
    _compose_buff_filter(buff_filter,inputs,caps);child['buffFilter']=buff_filter
    from scripts.game_data.memorypack import skill_passive_map_sources
    passive_maps=skill_passive_map_sources.derive(image,inputs)
    if (passive_maps.get('status')!='validated-conditional-passive-map'
            or passive_maps.get('nativeInputs')!=inputs
            or passive_maps.get('wholeSkillDataAdmitted')is not False
            or caps.keys()&passive_maps['capabilities'].keys()):
        raise ValueError(LABEL+'.source:unproved-current-passive-map')
    caps.update(passive_maps['capabilities']);proof['passiveMaps']=passive_maps
    caps['ActionGroupData']['passiveElementsAdmitted']=True
    from scripts.game_data.memorypack import skill_action_nested_record_sources
    child['actionNestedRecords']=skill_action_nested_record_sources._derive_on_children(image,inputs,{
        skill_action_nested_record_sources.DOUBLE:child['blackboardDouble'],
        skill_action_nested_record_sources.VECTOR:child['blackboardVector3'],
        skill_action_nested_record_sources.TARGET:child['ecComponents'],
        skill_action_nested_record_sources.SEQUENCE:proof['sequenceComponents'],
        skill_action_nested_record_sources.CURVE:dict(nativeInputs=inputs,capabilities={'curve-profile':caps['curve-profile']},proof=child['curve']),
    })
    _compose_action_nested_records(child['actionNestedRecords'],inputs,caps)
    from scripts.game_data.memorypack import skill_action_geometry_sources
    child['actionGeometry']=skill_action_geometry_sources._derive_on_children(image,inputs,
        {'Beyond.Blackboard+BlackboardVector3':child['blackboardVector3']})
    _compose_action_geometry(child['actionGeometry'],inputs,caps)
    from scripts.game_data.memorypack import skill_selector_union_sources
    selectors=skill_selector_union_sources._derive_with_ec(image,inputs,child['ecComponents'],
        buff_find_component=continuation['proof']['buffFindSettings'],buff_filter_component=buff_filter,nested_component=child['actionNestedRecords'],
        geometry_component=child['actionGeometry'])
    smart=selectors['proof']['nonzeroChildren']['proof'].get('managedValueChildren',{}).get('Beyond.Gameplay.Core.SmartTargetSelectSetting')
    if smart is not None:
        _compose_smart_target(smart,inputs,caps);child['smartTargetValue']=smart
    selector_nulls=_compose_selectors(selectors,inputs,caps,programs,requirements)
    proof['currentSelectors']=selectors
    _compose_ec_external(child['ecComponents'],caps)
    from scripts.game_data.memorypack import skill_action_components,skill_action_union_sources,skill_action_component_bindings
    transport=skill_action_union_sources.derive(image,inputs)
    inventory={w.name:dict(memberCount=w.serialized_member_count,abstract=w.abstract)
        for w in image.memorypack_wrappers.values()}
    extension=skill_action_component_bindings.extension_names(transport,inputs,programs,inventory)
    from scripts.game_data.memorypack import skill_blackboard_string_sources,skill_action_reference_components
    child['blackboardString']=skill_blackboard_string_sources.derive(image,inputs)
    _compose_action_reference_records(child['blackboardString'],inputs,caps,['skill-blackboard-string'])
    from scripts.game_data.memorypack import skill_blackboard_buff_id_sources
    child['blackboardBuffId']=skill_blackboard_buff_id_sources.derive(image,inputs)
    _compose_action_reference_records(child['blackboardBuffId'],inputs,caps,['skill-blackboard-buff-id'])
    child['actionReferences']=skill_action_reference_components.derive(image,inputs,
        type_names=[*skill_action_reference_components.DEFAULT_TYPES,'Beyond.Gameplay.WeaponVFXOverrideConfig'])
    _compose_action_reference_records(child['actionReferences'],inputs,caps,
        ['skill-action-animator-param','skill-action-alert-data','skill-action-weapon-vfx-override'])
    from scripts.game_data.memorypack import skill_dropdown_blackboard_sources
    child['dropdownBlackboards']=skill_dropdown_blackboard_sources.derive(image,inputs)
    _compose_action_reference_records(child['dropdownBlackboards'],inputs,caps,
        ['skill-blackboard-impact-value','skill-blackboard-super-armor-value'])
    from scripts.game_data.memorypack import skill_blowoff_priority_sources
    child['blowoffPriority']=skill_blowoff_priority_sources.derive(image,inputs)
    _compose_action_reference_records(child['blowoffPriority'],inputs,caps,['skill-blackboard-blowoff-priority'])
    from scripts.game_data.memorypack import skill_damage_components
    child['damageComponents']=skill_damage_components.derive(image,inputs)
    _compose_damage(child['damageComponents'],inputs,caps)
    from scripts.game_data.memorypack import skill_hit_env_sources
    child['hitEnv']=skill_hit_env_sources._derive_on_calculation(image,inputs,child['damageComponents'])
    _compose_hit_env(child['hitEnv'],inputs,caps)
    from scripts.game_data.memorypack import skill_action_setting_sources
    child['actionSettings']=skill_action_setting_sources._derive_on_children(image,inputs,
        {'Beyond.Blackboard+BlackboardDouble':child['blackboardDouble']},
        type_names=['Beyond.Gameplay.Core.KeywordEnhanceEdit','Beyond.Gameplay.Core.BuffIconDurationSourceSetting'])
    _compose_action_settings(child['actionSettings'],inputs,caps,['skill-keyword-enhance-edit','skill-buff-icon-duration-setting'])
    from scripts.game_data.memorypack import skill_action_create_buff_input_sources
    create_union=continuation['proof']['buffInputUnion']['proof']
    child['createBuffInput']=skill_action_create_buff_input_sources._derive_on_source(image,inputs,
        create_union['createBuffInput'],create_union['createAssignPairList'])
    _compose_create_buff_input(child['createBuffInput'],inputs,caps)
    from scripts.game_data.memorypack import skill_global_buff_input_sources
    child['globalBuffInput']=skill_global_buff_input_sources.derive(image,inputs)
    _compose_global_buff_input(child['globalBuffInput'],inputs,caps)
    from scripts.game_data.memorypack import skill_raycast_record_sources
    child['actionRaycast']=skill_raycast_record_sources._derive_on_children(image,inputs,{
        skill_raycast_record_sources.VECTOR:child['blackboardVector3'],
        skill_raycast_record_sources.CURVE:dict(nativeInputs=inputs,capabilities={'curve-profile':caps['curve-profile']},proof=child['curve']),
    })
    _compose_action_raycast(child['actionRaycast'],inputs,caps)
    from scripts.game_data.memorypack import skill_ordinary_ability_map_sources,skill_target_filter_sources,skill_special_aim_components
    child['ordinaryAbilityMap']=skill_ordinary_ability_map_sources._derive_on_sequence(image,inputs,proof['sequenceComponents'])
    _compose_ordinary_ability_map(child['ordinaryAbilityMap'],inputs,caps)
    child['targetFilter']=skill_target_filter_sources.derive(image,inputs)
    _compose_target_filter(child['targetFilter'],inputs,caps)
    child['specialAim']=skill_special_aim_components._derive_on_double(image,inputs,child['blackboardDouble'])
    _compose_special_aim(child['specialAim'],inputs,caps)
    from scripts.game_data.memorypack import skill_camera_transition_sources
    child['cameraTransitions']=skill_camera_transition_sources.derive(image,inputs)
    _compose_camera_transitions(child['cameraTransitions'],inputs,caps)
    from scripts.game_data.memorypack import skill_camera_custom_components,skill_camera_module_components,enum_list_native_sources
    from scripts.game_data.memorypack.skill_camera_custom_composition import compose as compose_camera_custom
    camera_curve=dict(nativeInputs=inputs,capabilities={'curve-profile':caps['curve-profile']},proof=child['curve'])
    child['cameraEnums']=enum_list_native_sources.derive(image,inputs)
    child['cameraModules']=skill_camera_module_components._derive_on_curve(image,inputs,camera_curve)
    child['cameraCustom']=skill_camera_custom_components._derive_on_children(image,inputs,curve=camera_curve,
        enums=child['cameraEnums'],modules=child['cameraModules'],transitions=child['cameraTransitions'])
    caps.update(compose_camera_custom(child['cameraCustom'],inputs,caps))
    from scripts.game_data.memorypack import skill_look_at_target_sources
    child['lookAtTarget']=skill_look_at_target_sources._derive_on_target(image,inputs,child['ecComponents'])
    _compose_look_at_target(child['lookAtTarget'],inputs,caps)
    references={
        'Beyond.Blackboard+BlackboardDouble':child['blackboardDouble'],
        'Beyond.Blackboard+BlackboardInt':child['blackboardInt'],
        'Beyond.Blackboard+BlackboardVector2':child['blackboardVector2'],
        'Beyond.Blackboard+BlackboardVector3':child['blackboardVector3'],
        'Beyond.Gameplay.Core.TargetSettings':child['ecComponents'],
        'Beyond.Gameplay.Core.DirectionSettings':child['ecComponents'],
        'Beyond.Gameplay.Core.Selector+SelectorData':child['ecComponents'],
        'Beyond.Gameplay.Core.BuffFindSettings':continuation['proof']['buffFindSettings'],
        'Beyond.Gameplay.Core.BuffFilterSettings':buff_filter,
        'Beyond.Gameplay.Core.SequenceActionData':proof['sequenceComponents'],
        'Beyond.Gameplay.Core.GameplayTagList':continuation,
        'Beyond.Gameplay.Core.BuffInput':continuation,
        'Beyond.Blackboard+BlackboardString':child['blackboardString'],
        'Beyond.Gameplay.Core.Conditions.BlackboardBuffId':child['blackboardBuffId'],
        'Beyond.Gameplay.Core.AnimatorParamAction':child['actionReferences'],
        'Beyond.Gameplay.Core.SkillAlertData':child['actionReferences'],
        'Beyond.Gameplay.WeaponVFXOverrideConfig':child['actionReferences'],
        'UnityEngine.AnimationCurve':dict(nativeInputs=inputs,capabilities={'curve-profile':caps['curve-profile']},proof=child['curve']),
        'Beyond.Gameplay.EffectActionCfg':child['damageComponents'],
        'Beyond.Gameplay.Core.DamageAction+DamageUnit':child['damageComponents'],
        'Beyond.Gameplay.Core.CalculationBase':child['damageComponents'],
        'Beyond.Gameplay.Core.DamageProcessorBase':child['damageComponents'],
        'Beyond.Gameplay.Core.CastData+CostData':continuation,
        'Beyond.Gameplay.Core.DamageAction+HitEnvData':child['hitEnv'],
        'Beyond.Gameplay.Core.BlackboardImpactValue':child['dropdownBlackboards'],
        'Beyond.Gameplay.Core.BlackboardSuperArmorValue':child['dropdownBlackboards'],
        'Beyond.Gameplay.Core.BlowOffCharacterAction+BlackboardCharBlowOffPriorityValue':child['blowoffPriority'],
        'Beyond.Gameplay.Core.KeywordEnhanceEdit':child['actionSettings'],
        'Beyond.Gameplay.Core.BuffIconDurationSourceSetting':child['actionSettings'],
        'Beyond.Gameplay.Core.CreateBuffActionInput':child['createBuffInput'],
        'Beyond.Gameplay.Core.GlobalBuffInput':child['globalBuffInput'],
        'Beyond.Gameplay.ColliderShapeData':child['actionGeometry'],
        'Beyond.Gameplay.Core.PhysicsCastAction+SourceForwardData':child['actionGeometry'],
        'Beyond.Gameplay.Core.PhysicsCastAction+SourceToTargetData':child['actionGeometry'],
    }
    references.update({name:child['actionNestedRecords']for name in skill_action_nested_record_sources.RECORDS})
    references.update({name:child['actionRaycast']for name in skill_raycast_record_sources.RECORDS})
    references[skill_camera_transition_sources.TYPE]=child['cameraTransitions']
    references[skill_camera_custom_components.TYPE]=child['cameraCustom']
    references[skill_look_at_target_sources.TYPE]=child['lookAtTarget']
    references.update({skill_ordinary_ability_map_sources.TYPE:child['ordinaryAbilityMap'],
        skill_target_filter_sources.TYPE:child['targetFilter'],skill_special_aim_components.TYPE:child['specialAim']})
    actions=skill_action_components._derive_with_transport(image,inputs,transport,extension,reference_children=references,
        selector_component=selectors)
    _compose_action_collections(actions,inputs,caps)
    _compose_actions(actions,inputs,caps,programs,requirements);proof['currentActions']=actions
    from scripts.game_data.memorypack import skill_wrapper_null_sources
    wrapper_nulls=skill_wrapper_null_sources.derive(image,inputs,programs)
    _compose_wrapper_nulls(wrapper_nulls,inputs,programs);proof['wrapperNulls']=wrapper_nulls
    from scripts.game_data.memorypack.skill_timeline_dependencies import validate_dependencies
    dependency_joins={}
    for fact in facts:
        if not fact.get('dependencies'):continue
        withheld=[];declarations=[]
        for dependency in fact['dependencies']:
            if (fact['dispatcher']['wrapperName']=='Beyond.MemoryPack.Beyond_Gameplay_Core_CustomRootMotionAction_DataForMemoryPack'
                    and dependency['path']=='validator_02_native.json'):
                withheld.append(dict(sourceOwner=dependency['path'],admitted=False,
                    reason='This historical descendant supplies no source bytes or routes. Finite current selectors are independently composed by the current selector source owner.'))
            else:declarations.append(dependency)
        parent=dict(fact,dependencies=declarations)
        dependency_joins[fact['dispatcher']['wrapperName']]=dict(
            current=validate_dependencies(image,parent,label=LABEL),withheldDescendants=withheld)
    proof['uniformDependencyJoins']=dependency_joins
    proof['children']=child;proof['componentOwners']=components
    fact=_json_fact(dict(schema=SCHEMA,status='exact-current-build',nativeInputs=dict(inputs),sourceOwners=sorted(source.UNIFORM_OWNERS),
        programs=programs,routeRequirements=requirements,capabilities=caps,
        nullUnions={'AbilityActionData':True,**selector_nulls},
        proof=proof,evidenceBoundary=BOUNDARY))
    return fact if retain_traces else project_contract(fact,image_base=image.pe.image_base)


def _comparison_contract(fact):
    """Compare source semantics independently of one refusal's diagnostic detail.

    A coherent getter's failed zero-candidate refresh remains unadmitted. Its
    older count-only message and newer identity-rich message describe that same
    result. Check the latter against its own getter before normalizing either;
    every other field and refusal is preserved. Re-intern from the root so this
    change cannot make graph node numbering or prior sharing affect equality.
    The reviewed contract and the returned source provenance remain untouched.
    """
    projection=fact['proof'];validate_projection(projection)
    nodes=projection['nodes'];prefix='generatedMemberSource.one-complete-compatible-refresh:'

    def need(check,condition):
        if not condition:raise ValueError(LABEL+'.comparison.refresh-diagnostic:'+check)

    def array(value,label):
        need(label+'-array-reference',isinstance(value,dict)and set(value)=={'$node'})
        node=nodes[value['$node']]
        need(label+'-array',node['kind']=='array')
        return node['items']

    def reason(fields):
        value=fields.get('refreshPendingReason')
        if not isinstance(value,str)or not value.startswith(prefix):return value
        need('nonadmitted-coherent-getter',fields.get('refreshAdmitted')is False
            and fields.get('coherentNonNullSamePointerReturn')is True and 'compatibleRefresh'not in fields)
        method=fields.get('method')
        need('owned-getter-method',isinstance(method,dict)and set(method)=={'$method'})
        method=projection['metadataMethods'][method['$method']]
        need('owned-getter-identity',len(method)==4 and type(method[0])is int and method[0]>=0
            and isinstance(method[1],str)and bool(method[1])and method[2]=='get___instance'
            and type(method[3])is int and method[3]>0)
        base=array(fields.get('baseHolder'),'base-holder');cache=array(fields.get('typedCache'),'typed-cache')
        need('owned-base-and-typed-cache',len(base)==len(cache)==3
            and all(isinstance(v,str)and bool(v)for v in base[:2]+cache[:2])and cache[0]==method[1]
            and type(base[2])is int and base[2]>=16 and type(cache[2])is int and cache[2]>base[2])
        need('owned-code-windows',bool(array(fields.get('codeWindows'),'code-windows')))
        program=fields.get('program')
        need('owned-coherent-program',isinstance(program,dict)and set(program)=={'$node'}
            and nodes[program['$node']]['kind']=='object'and bool(nodes[program['$node']]['members'])
            and isinstance(fields.get('condition'),str)and bool(fields['condition']))
        suffix=value[len(prefix):]
        if suffix!='0':
            try:detail=json.loads(suffix)
            except(ValueError,TypeError)as error:raise ValueError(LABEL+'.comparison.refresh-diagnostic:invalid-detail')from error
            need('exact-zero-candidate-detail',isinstance(detail,dict)and set(detail)=={
                'expected','actual','typeName','methodName','getterTargetRva','baseSlot','cacheOffset','candidates','omittedCandidates'}
                and type(detail.get('expected'))is int and detail['expected']==1
                and type(detail.get('actual'))is int and detail['actual']==0
                and detail.get('candidates')==[]and type(detail.get('omittedCandidates'))is int and detail['omittedCandidates']==0)
            need('same-getter-detail',detail['typeName']==cache[1]and detail['methodName']==method[2]
                and type(detail['getterTargetRva'])is int and detail['getterTargetRva']==method[3]
                and type(detail['baseSlot'])is int and detail['baseSlot']==base[2]
                and type(detail['cacheOffset'])is int and detail['cacheOffset']==cache[2])
        return prefix+'0'

    remapped={};intern={};canonical=[]
    def visit(value):
        if not isinstance(value,dict):return value
        if '$node'not in value:return dict(value)
        index=value['$node']
        if index not in remapped:
            original=nodes[index]
            if original['kind']=='object':
                fields=dict(original['members']);pending=reason(fields)
                node=dict(kind='object',members=[[key,visit(pending if key=='refreshPendingReason'else item)]
                    for key,item in original['members']])
            else:node=dict(kind='array',items=[visit(item)for item in original['items']])
            key=json.dumps(node,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
            if key not in intern:intern[key]=len(canonical);canonical.append(node)
            remapped[index]=intern[key]
        return {'$node':remapped[index]}
    root=visit(projection['root'])
    return dict(fact,proof=dict(projection,root=root,nodes=canonical))


def validate_on_image(image,inputs,*,contract=None,retain_source_provenance=False):
    if type(retain_source_provenance)is not bool:raise ValueError(LABEL+'.source:retain-source-provenance-must-be-bool')
    fact=contract if contract is not None else _read()
    if fact['nativeInputs']!=inputs:raise ValueError(LABEL+'.native:current-build-mismatch')
    expected_comparison=_comparison_contract(fact)
    actual=derive(image,inputs)
    actual_comparison=_comparison_contract(actual)
    validate_claims(expected_comparison,actual_comparison,label=LABEL+'.proof')
    validate_claims(actual_comparison,expected_comparison,label=LABEL+'.declaration')
    result=dict(status='validated',nativeInputs=dict(inputs),programs=fact['programs'],
        routeRequirements=fact['routeRequirements'],capabilities=fact['capabilities'],nullUnions=fact['nullUnions'],
        wholeSkillDataAdmitted=False,evidenceBoundary=fact['evidenceBoundary'])
    if retain_source_provenance:result['sourceProvenance']=fact['proof']
    return result


def _gate(inputs,*,game_root=None,gameassembly=None,metadata=None):
    if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both-selected-paths-required')
    if game_root is not None and gameassembly is None:
        root=Path(game_root);gameassembly=root.parent/'GameAssembly.dll';metadata=root/'il2cpp_data/Metadata/global-metadata.dat'
    return check_installed_native_inputs(inputs['GameAssembly.dll'],inputs['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)


def validate_current_native_contract(*,game_root=None,gameassembly=None,metadata=None,contract_path=CONTRACT_PATH,retain_source_provenance=False):
    try:
        if type(retain_source_provenance)is not bool:raise ValueError(LABEL+'.source:retain-source-provenance-must-be-bool')
        sources=snapshot_complete_reader_inputs()
        path=Path(contract_path);raw=path.read_bytes();fact=_read(path);inputs=fact['nativeInputs']
        gate=_gate(inputs,game_root=game_root,gameassembly=gameassembly,metadata=metadata)
        if gate.status!='validated':return dict(status=gate.status,programs=[],capabilities={},detail=gate.detail,failedCheck='installed-native-inputs')
        if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,inputs):return dict(programs=[],capabilities={},failedCheck='UnityPlayer.dll',**failed)
        result=validate_on_image(open_native_image(gate.gameassembly,gate.metadata),inputs,contract=fact,
            retain_source_provenance=retain_source_provenance)
        after=_gate(inputs,gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':return dict(status=after.status,programs=[],capabilities={},detail=after.detail,failedCheck='installed-native-inputs-bookend')
        if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,inputs):return dict(programs=[],capabilities={},failedCheck='UnityPlayer.dll-bookend',**failed)
        if raw!=path.read_bytes():raise ValueError(LABEL+'.contract:declaration-drift')
        if sources!=snapshot_complete_reader_inputs():raise ValueError(LABEL+'.native:reader-source-drift')
        result['nativeSources']={'GameAssembly.dll':str(Path(gate.gameassembly).resolve()),'global-metadata.dat':str(Path(gate.metadata).resolve())}
        return result
    except(ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError)as error:
        return dict(programs=[],capabilities={},**native_validation_failure(error,label=LABEL,source_path=contract_path))


class CurrentSequenceOperationError(ValueError):pass


_CURRENT_SEQUENCE_SOURCE_GATE=object()


class _CurrentSequenceOperation:
    def __init__(self,proof,game_root,strings,*,_native_source_gate=None):
        self._proof=json.loads(json.dumps({key:value for key,value in proof.items()if key!='sourceProvenance'}))
        self._source_graph=(json.loads(json.dumps(proof['sourceProvenance']))
            if _native_source_gate is _CURRENT_SEQUENCE_SOURCE_GATE and 'sourceProvenance'in proof else None)
        self._native_source_gate=_native_source_gate
        self.game_root=Path(game_root).resolve();self.strings=strings;self.active=True
        self.routes={(r['family'],r['tag']):r for r in self._proof['programs']}
    @property
    def proof(self):return json.loads(json.dumps(self._proof))
    def _active(self):
        if not self.active:raise CurrentSequenceOperationError(LABEL+'.operation:closed')
    def source_provenance(self):
        """Freshly re-proved source semantics, only inside the public operation."""
        self._active()
        if(self._native_source_gate is not _CURRENT_SEQUENCE_SOURCE_GATE or self._source_graph is None
                or self._proof.get('status')!='validated'):
            raise CurrentSequenceOperationError(LABEL+'.operation:public-native-source-gate-required')
        return json.loads(json.dumps(self._source_graph))
    def route(self,family,tag):
        self._active();row=self.routes.get((family,tag))
        if row is None:raise CurrentSequenceOperationError(LABEL+'.route:unproved-current='+family+':'+str(tag))
        for cap in self._proof['routeRequirements'].get(family+':'+str(tag),[]):self.child(cap)
        return json.loads(json.dumps(row))
    def child(self,name):
        self._active();cap=self._proof['capabilities'].get(name)
        if cap is None:raise CurrentSequenceOperationError(LABEL+'.child:unproved-current='+str(name))
        return json.loads(json.dumps(cap))
    def null_action(self):
        self._active()
        if self._proof['nullUnions'].get('AbilityActionData')is not True:raise CurrentSequenceOperationError(LABEL+'.union:unproved-null=AbilityActionData')
    def null_selector(self,family):
        self._active()
        if self._proof['nullUnions'].get(family)is not True:raise CurrentSequenceOperationError(LABEL+'.union:unproved-null='+family)
    def pool_index(self,index):
        self._active();return self.strings.resolve(index)


def prepared_current_sequence(operation):
    if not isinstance(operation,_CurrentSequenceOperation):raise CurrentSequenceOperationError(LABEL+'.operation:invalid-capability')
    operation._active();return operation


@contextmanager
def current_sequence(*,game_root,strings):
    if game_root is None or strings is None or not hasattr(strings,'root')or not callable(getattr(strings,'resolve',None)):
        raise CurrentSequenceOperationError(LABEL+'.operation:explicit-root-and-pool-required')
    root=Path(game_root).resolve();before=snapshot_complete_reader_inputs();pool_root=Path(strings.root).parent
    pool=snapshot_string_pool_inputs(pool_root);proof=validate_current_native_contract(game_root=root,retain_source_provenance=True)
    if proof.get('status')!='validated':raise CurrentSequenceOperationError(LABEL+'.operation:enter:'+str(proof)[:1400])
    selected=proof['nativeSources']
    if(Path(selected['GameAssembly.dll']).resolve()!=root.parent/'GameAssembly.dll'
            or Path(selected['global-metadata.dat']).resolve()!=root/'il2cpp_data/Metadata/global-metadata.dat'):
        raise CurrentSequenceOperationError(LABEL+'.operation:selected-pair-differs')
    operation=_CurrentSequenceOperation(proof,root,strings,_native_source_gate=_CURRENT_SEQUENCE_SOURCE_GATE)
    try:yield operation
    finally:
        operation.active=False;inputs=proof['nativeInputs']
        after=_gate(inputs,gameassembly=Path(selected['GameAssembly.dll']),metadata=Path(selected['global-metadata.dat']))
        if after.status!='validated'or pooled_source_helper.check_unity_input(selected['GameAssembly.dll'],inputs):
            raise CurrentSequenceOperationError(LABEL+'.operation:native-exit-drift')
        current=snapshot_complete_reader_inputs()
        if before!=current:raise CurrentSequenceOperationError(LABEL+'.operation:reader-source-drift:'+str(reader_input_changes(before,current)))
        if pool!=snapshot_string_pool_inputs(pool_root):raise CurrentSequenceOperationError(LABEL+'.operation:string-pool-drift')


def regenerate(*,game_root=None,gameassembly=None,metadata=None,write=False,contract_path=CONTRACT_PATH):
    path=Path(contract_path);before=path.read_bytes()if path.is_file()else None
    sources=snapshot_complete_reader_inputs()
    inputs=pooled_source_helper._contract()['nativeInputs'];gate=_gate(inputs,game_root=game_root,gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':raise ValueError(LABEL+'.regenerate:'+gate.status+':'+gate.detail)
    if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,inputs):raise ValueError(str(failed))
    result=derive(open_native_image(gate.gameassembly,gate.metadata),inputs)
    after=_gate(inputs,gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated'or pooled_source_helper.check_unity_input(gate.gameassembly,inputs):raise ValueError(LABEL+'.regenerate:native-input-drift')
    if before!=(path.read_bytes()if path.is_file()else None):raise ValueError(LABEL+'.regenerate:contract-declaration-drift')
    if sources!=snapshot_complete_reader_inputs():raise ValueError(LABEL+'.regenerate:reader-source-drift')
    if write:path.write_bytes(contract_json_bytes(result))
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in('game-root','gameassembly','metadata'):parser.add_argument('--'+name,type=Path)
    parser.add_argument('--regenerate',action='store_true');parser.add_argument('--write',action='store_true');parser.add_argument('--output-json',type=Path)
    args=parser.parse_args(argv)
    if args.write and not args.regenerate:parser.error('--write requires --regenerate')
    if args.output_json and not args.output_json.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):parser.error('--output-json must be below reports/')
    selected=dict(game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata)
    result=regenerate(**selected,write=args.write)if args.regenerate else validate_current_native_contract(**selected)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True,exist_ok=True);args.output_json.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],programs=len(result.get('programs',[])),wholeSkillDataAdmitted=False)))
    return 0 if result['status']in('validated','exact-current-build')else 2


if __name__=='__main__':raise SystemExit(main())
