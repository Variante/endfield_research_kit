"""Current LevelScript pooled child composition, independent from whole owners.

Every concrete parent, raw carrier and actual source is joined separately.
General positive counts come from complete exact loop induction, and never
from a typed request, a successful byte probe or historical receipt.
"""
import json

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.memorypack import (
    levelscript_collection_sources as collections,levelscript_param_graph_sources as graph,
    npc_collection_programs,pooled_string_list_sources,scalar_param_native as scalar,
)
from scripts.game_data.memorypack.pointer_param import owned


def derive(image,pins,owner_proof):
    from scripts.game_data import levelscript_interactive_native,levelscript_int_list_native
    from scripts.game_data.memorypack.skill_cost_data_list_sources import derive_reference_list_component
    base=image.pe.image_base;dependencies={}
    def need(k,e,a):scalar.need('currentLevelScriptChildren',k,e,a)
    def load(name):
        raw=(CONTRACTS_DIR/name).read_bytes();dependencies[name]=raw;fact=json.loads(raw)
        need('dependency-build:'+name,pins,fact['nativeInputs']);return fact
    interactive_fact=load('levelscript_interactive_native.json')
    interactive=levelscript_interactive_native._validate_native(image,interactive_fact)
    graph_proof=graph.derive(image,pins)
    ulong=collections.derive_ulong_list(image,pins,owner_proof)
    int_fact=load('levelscript_int_list_native.json')
    levelscript_int_list_native._validate_native(image,int_fact)
    intbody=owned(image,base+int_fact['bodies']['list']['entryRva'])
    ints=collections.int_list_induction(intbody['regions'],intbody['pointer'],
        int_fact['readerFields'],{k:base+v for k,v in int_fact['calls'].items()})
    int_registration=GenericEntries(image).resolve(int_fact['bodies']['list']['methodDefinition'],['int'],[])
    need('exact-int-list-entry',intbody['pointer'],int_registration['pointer'])
    ints=dict(ints,closedRegistration=int_registration,sourceWindows=intbody['windows'])

    parent_rows=[]
    for original,owner in owner_proof['owners'].items():
        for field,read in zip(owner['fields'],owner['program']['orderedReads'],strict=True):
            if field['typeName']not in('System.Collections.Generic.List`1<Beyond.Gameplay.ParamKeyValue>',
                    'System.Collections.Generic.Dictionary`2<int,string>'):continue
            usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='currentLevelScriptChildren.parent')
            need('exact-parent-type',['ReadPackable',[field['typeName']]],
                [usage['methodName'],usage['methodArguments']])
            parent_rows.append(dict(owner=original,field=field,source=read,typedRequest=usage))
    list_parent,= [p for p in parent_rows if p['field']['name']=='properties'and p['owner']=='Beyond.Gameplay.LevelScriptData']
    ref_list=derive_reference_list_component(image,pins,
        typed_request=list_parent['typedRequest'],call_target=list_parent['source']['sourceTarget'],
        element_type='Beyond.Gameplay.ParamKeyValue',count_limit=2)
    body=owned(image,ref_list['entry']['pointer'])
    list_induction=collections.reference_list_induction(body['regions'],body['pointer'],
        {**ref_list['referenceSource'].get('readerFields',{}),**int_fact['readerFields']},
        {k:base+v for k,v in ref_list['symbols'].items()})
    # All four root/Brief properties/map parents use this separately proved
    # current ReadPackable reference source; no suffix/source alias permitted.
    for parent in parent_rows:
        need('same-actual-parent-reference-source',ref_list['callTargetRva'],
            parent['source']['sourceTarget']-base)
    s={k:base+v for k,v in interactive_fact['symbols'].items()}
    uintbody=owned(image,base+interactive_fact['sources']['uintDictionary']['entryRva'])
    uintsymbols=dict(s,indexed=s['context'],constructor=s['dictionaryConstructor'],
        keyDispatch=s['keyDispatcher'],valueDispatch=s['referenceDispatcher'])
    uints=[npc_collection_programs.uint_dictionary(uintbody['regions'],uintbody['pointer'],uintsymbols,count=n)
        for n in(-1,0,1)]
    intdict=owned(image,base+interactive_fact['sources']['intDictionary']['entryRva'])
    intdictproof=collections.int_dictionary_induction(intdict['regions'],intdict['pointer'],s,
        interactive_fact['readerFields'])
    dict_registration=GenericEntries(image).resolve(next(r[1]for r in interactive_fact['entries']
        if r[0]=='intDictionary'),['int','object'],[])
    need('exact-int-reference-dictionary-entry',intdict['pointer'],dict_registration['pointer'])
    string_fact=load('levelscript_pooled_string_list_native.json')
    strings=pooled_string_list_sources.validate_string_components(image,string_fact)
    # Exact nominal interactive child requests already re-derived by its owner.
    requested=[]
    by_instruction={u['instructionRva']:u for u in interactive_fact['usageContexts']}
    for item in interactive['element'][0]['typedUsages']:
        if item['field']not in('componentProperties','globalIntKeyList','globalProperties',
                'mapIntKeyList','mapProperties','properties'):continue
        usage=by_instruction[item['instruction']-base]
        expected=next(f for f in interactive_fact['fields']if f['name']==item['field'])
        need('interactive-exact-child',[expected['typeName']],usage['methodArguments'])
        requested.append(dict(field=expected,source=item,typedRequest=usage))
    for name,raw in dependencies.items():need('dependency-bookend:'+name,raw,(CONTRACTS_DIR/name).read_bytes())
    caps={
        'System.Collections.Generic.List`1<ulong>':dict(countLimit=16384,headerBytes=4,elementBytes=8,counts='-1-or-nonnegative',wholeGrammarAdmitted=True),
        'System.Collections.Generic.List`1<int>':dict(countLimit=16384,headerBytes=4,elementBytes=4,counts='-1-or-nonnegative',wholeGrammarAdmitted=True),
        'System.Collections.Generic.List`1<Beyond.Gameplay.ParamKeyValue>':dict(countLimit=16384,headerBytes=4,counts='-1-or-nonnegative',wholeGrammarAdmitted=True),
        'System.Collections.Generic.Dictionary`2<int,string>':dict(countLimit=16384,headerBytes=4,keyBytes=4,valueBytes=4,counts='-1-or-nonnegative',wholeGrammarAdmitted=True),
        'System.Collections.Generic.Dictionary`2<Beyond.Gameplay.InteractiveComponentType,System.Collections.Generic.List`1<Beyond.Gameplay.ParamKeyValue>>':dict(countLimit=16384,headerBytes=4,keyBytes=4,counts='-1-or-nonnegative',wholeGrammarAdmitted=True),
        'System.Collections.Generic.Dictionary`2<uint,Beyond.Gameplay.LevelInteractiveData>':dict(countLimit=16384,headerBytes=4,keyBytes=4,counts='-1-or-nonnegative',wholeGrammarAdmitted=False,
            recordGrammar='MC25-or-FF;condition-FF-only',
            condition='Each reached record must compose every actual nested child. ConditionRuntimeBase remains FF-only.'),
    }
    return json.loads(json.dumps(dict(nativeInputs=pins,capabilities=caps,
        ownerParents=parent_rows,interactiveParents=requested,
        graph=graph_proof,ulongList=ulong,intList=ints,
        keyValueList=dict(component=ref_list,induction=list_induction),
        intReferenceDictionary=dict(induction=intdictproof,registration=dict_registration,windows=intdict['windows']),
        uintReferenceDictionary=dict(programs=uints,windows=uintbody['windows']),
        pooledStringCallback=strings,interactive=interactive,
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
