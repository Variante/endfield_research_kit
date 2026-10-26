"""Positive Task conditions composed from fresh, independent current sources.

The old Task owner remains FF-only. This explicit owner joins its exact two
records and dictionaries to the complete GameCondition graph. Pure compose
checks relationships; only derive authenticates the selected native image.
Neither entry observes a live provider choice or grants a whole LevelScript.
"""
import json

from scripts.game_data.memorypack import levelscript_task_sources as tasks

SCHEMA='endfield.story-task-game-condition-components.v1'
CAP_SCHEMA='endfield.story-task-game-condition-capability.v1'
CAPABILITY='story-task-map-game-condition'
RECORD_SCHEMA='endfield.story-task-game-condition-record.v1'
TASK_CAP='story-current-task'
CONDITION_CAP='story-current-task-condition'
DICT_CAP='story-current-task-condition-dictionary'
COUNT_LIMIT=16384


def need(key,condition):
 if not condition:raise ValueError('storyTaskGameCondition.'+key)


def _call(instruction,target):
 need('actual-owned-E8',isinstance(instruction,list)and len(instruction)==2
  and type(instruction[0])is int and type(instruction[1])is str and type(target)is int)
 raw=bytes.fromhex(instruction[1])
 need('actual-E8-target',len(raw)==5 and raw[0]==232
  and instruction[0]+5+int.from_bytes(raw[1:],'little',signed=True)==target)


def _request(usage,name,method):
 need('exact-closed-Reader-request',isinstance(usage,dict)
  and(usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
   ('MemoryPack.MemoryPackReader',method,[],[name])
  and isinstance(usage.get('methodSpec'),list)and len(usage['methodSpec'])==3
  and all(type(n)is int for n in usage['methodSpec'])and usage['methodSpec'][0]>=0
  and type(usage.get('instructionRva'))is int and type(usage.get('instructionHex'))is str)


def _condition_binding(source,usage,reference):
 read=source['orderedSourceReads'][0];context=read.get('context',{})
 need('only-actual-TaskCondition-field',(source['wrappedType'],read['memberIndex'],read['fieldName'],read['declaredType'])==
  (tasks.CONDITION,0,'condition',tasks.GAME_CONDITION))
 _request(usage,tasks.GAME_CONDITION,'ReadValue')
 raw=bytes.fromhex(context.get('argumentRawHex',''))
 need('actual-ordinary-reference-MethodInfo',len(raw)==16 and raw[10:12]==bytes((18,0))
  and(context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'),context.get('register'))==
   ('MemoryPack.MemoryPackReader','ReadValue',tasks.GAME_CONDITION,'rdx')
  and(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))==
   (usage['instructionRva'],usage['instructionHex'],usage['methodSpec'])
  and usage['methodSpec'][0]==reference['referenceReaderMethodDefinition']
  and read['sourceTargetRva']==reference['referenceReaderTargetRva'])
 _call(read['instruction'],read['sourceTargetRva'])
 return dict(fieldName='condition',typeName=tasks.GAME_CONDITION,typedRequest=usage,
  sourceInstruction=read['instruction'],sourceTargetRva=read['sourceTargetRva'],
  readerMethodDefinition=usage['methodSpec'][0])


def bind_condition(pins,join,child,capability):
 from scripts.game_data.memorypack.levelscript_game_condition_components import SCHEMA as GRAPH,CAPABILITY as KEY
 from scripts.game_data.codecs.levelscript.current_game_condition import validate
 cap=child.get('capabilities',{}).get(capability);binding=child.get('parentBinding',{})
 need('same-complete-child-and-actual-parent',child.get('schema')==GRAPH and child.get('nativeInputs')==pins
  and capability==KEY and isinstance(cap,dict)
  and all(join.get(k)==binding.get(k)for k in('fieldName','typeName','typedRequest','sourceTargetRva'))
  and(binding.get('fieldName'),binding.get('typeName'))==('condition',tasks.GAME_CONDITION))
 validate(cap);_call(binding['sourceInstruction'],binding['sourceTargetRva'])
 return dict(fieldName='condition',typeName=tasks.GAME_CONDITION,capability=capability,
  readerMethodDefinition=binding['readerMethodDefinition'],sourceTargetRva=binding['sourceTargetRva'],
  actualCallbackEqualsProvedChildRequired=True,runtimeConditionEvaluationAdmitted=False)


def _dictionary(parent,pins,value_type,value_cap):
 source=parent['collection'];name='System.Collections.Generic.Dictionary`2<string,'+value_type+'>'
 usage=parent['typedRequest'];_request(usage,name,'ReadPackable')
 args=source.get('closedCarrier',{}).get('classArguments',[])
 need('independent-closed-dictionary-source',source.get('nativeInputs')==pins and source.get('typeName')==name
  and source.get('typedRequest')==usage and source.get('sourceWitnessClassArguments')==['object','object']
  and source.get('countLimit')==COUNT_LIMIT and type(source['countLimit'])is int and source.get('headerBytes')==4
  and source.get('actualCallbackEqualsCanonicalRequired')is True
  and all(source.get(k)is False for k in('keyGrammarAdmitted','valueGrammarAdmitted','parentFieldAdmitted',
   'wholeOwnerAdmitted','liveFormatterSelectionObserved'))
  and[r.get('name')for r in args]==['string',value_type]
  and[bytes.fromhex(r.get('rawHex',''))[10:12]for r in args]==[bytes((14,0)),bytes((18,0))]
  and[p.get('countProfile')for p in source.get('programs',[])]==['null','zero','all-positive-Int32']
  and all(p.get('normalReturn')is True and p.get('headerBytes')==4 and p.get('insertMode')==2 for p in source['programs'])
  and type(source.get('callTargetRva'))is int and source['callTargetRva']>0)
 return dict(typeName=name,keyType='string',keyWireKind='pooled-string',valueType=value_type,valueCapability=value_cap,
  countLimit=COUNT_LIMIT,headerBytes=4,readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=source['callTargetRva'],
  freshDictionaryRequired=True,sourceWitnessClassArguments=['object','object'],
  actualErasedDictionaryCallbackEqualsProvedSourceRequired=True,compatibleClosedContextsAndTypedHelpersRequired=True,
  actualKeyCallbackEqualsPooledStringRequired=True,actualValueCallbackEqualsProvedChildRequired=True,
  closedPointerEquivalenceProved=source['closedPointerEquivalenceProved'],liveFormatterSelectionObserved=False)


def bind_dictionary(pins,join,child,capability):
 cap=child.get('capabilities',{}).get(capability,{});binding=child.get('parentBinding',{})
 need('same-actual-nested-dictionary-parent',child.get('schema')==SCHEMA and child.get('nativeInputs')==pins
  and capability==DICT_CAP and cap.get('valueType')==tasks.CONDITION and cap.get('valueCapability')==CONDITION_CAP
  and all(join.get(k)==binding.get(k)for k in('fieldName','typeName','typedRequest','sourceTargetRva')))
 _request(join['typedRequest'],cap['typeName'],'ReadPackable');_call(binding['sourceInstruction'],join['sourceTargetRva'])
 need('same-nested-dictionary-definition-and-target',(join['typedRequest']['methodSpec'][0],join['sourceTargetRva'])==
  (cap['readerMethodDefinition'],cap['sourceTargetRva']))
 return dict(fieldName=join['fieldName'],typeName=cap['typeName'],capability=capability,
  readerMethodDefinition=cap['readerMethodDefinition'],sourceTargetRva=cap['sourceTargetRva'],
  freshDictionaryRequired=True,actualCallbackEqualsProvedChildRequired=True)


def _root_binding(owners,pins,parent):
 from scripts.game_data.memorypack import levelscript_owner_sources as root
 need('same-current-root-source',owners.get('nativeInputs')==pins and owners.get('childGrammarAdmitted')is False
  and owners.get('wholeOwnerAdmitted')is False)
 proof=owners['owners'][root.ROOT];program=proof['program'];selected=program['selectedBytes']
 need('exact-root-source-identity',proof['method'][1:3]==[proof['wrapperName'],'Deserialize']
  and program.get('originalType')==root.ROOT and program.get('normalReturn')is True
  and program.get('entryFrameRestored')is True and program.get('existingWrapper')is True)
 entry=selected[0][0];base=entry-proof['method'][3]
 need('same-complete-finite-root-read-plan',program.get('memberCount')==len(root.ROOT_FIELDS)
  and[f['name']for f in proof['fields']]==[n for n,k in root.ROOT_FIELDS]
  and[r['fieldName']for r in program['orderedReads']]==[n for n,k in root.ROOT_FIELDS])
 field,read=next((f,r)for f,r in zip(proof['fields'],program['orderedReads'],strict=True)if f['name']=='taskMap')
 code={at+i:value for at,raw in selected for i,value in enumerate(bytes.fromhex(raw))}
 instruction=[read['sourceCall']-base,bytes(code[read['sourceCall']+i]for i in range(5)).hex().upper()]
 source=parent['collection'];usage=parent['typedRequest']
 need('same-root-actual-typed-dictionary-site',field['typeName']==source['typeName']and field['kind']=='reference'
  and read['fieldName']=='taskMap'and read['storeOffset']==field['offset']
  and read['sourceTarget']-base==source['callTargetRva']
  and read['typedUsage']['instruction']-base==usage['instructionRva']
  and usage in proof['typedUsages'])
 _call(instruction,source['callTargetRva'])
 return dict(ownerType=root.ROOT,fieldName='taskMap',typeName=source['typeName'],typedRequest=usage,
  sourceInstruction=instruction,readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=source['callTargetRva'],
  storeOffset=field['offset'],existingWrapperRequired=True,disabledCollectorRequired=True,
  selectedCallBytesChecked=True,rootProgramFreshlyDerivedRequired=True,rootGrammarAdmitted=False)


def compose(baseline,graph,pins,*,owners):
 """Pure finite joins, without treating supplied facts as fresh authority."""
 from scripts.game_data.memorypack.levelscript_game_condition_components import SCHEMA as GRAPH,CAPABILITY as KEY
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.codecs.levelscript.current_game_condition import validate as validate_graph
 from scripts.game_data.codecs.levelscript.current_task_game_conditions import validate
 need('same-explicit-current-graph',graph.get('schema')==GRAPH and graph.get('nativeInputs')==pins
  and graph.get('status')=='validated-conditional-current-game-condition'
  and graph.get('holds')==[]and set(graph.get('capabilities',{}))=={KEY}
  and graph.get('parentFieldAdmitted')is False and graph.get('wholeOwnerAdmitted')is False)
 cap=graph['capabilities'][KEY];validate_graph(cap)
 need('same-native-Task-source',baseline.get('nativeInputs')==pins and set(baseline.get('records',{}))==set(tasks.PLANS)
  and baseline.get('wholeOwnerAdmitted')is False and baseline['capability']['gameConditionNullOnly']is True)
 reference=baseline['gameConditionNull']['component'];transport=graph['proof']['transport'];adapter=transport['adapter']
 need('independent-same-canonical-base-Original-adapter',reference.get('nativeInputs')==pins
  and cap['rootWrapper']==transport['wrapperName']
  and(reference.get('typeName'),reference.get('wrapperName'))==(tasks.GAME_CONDITION,transport['wrapperName'])
  and reference['pair']['composition']['interfaces']==transport['pair']['composition']['interfaces']
  and reference['callbackBinding']['canonicalTargetRva']==adapter['callbackBinding']['canonicalTargetRva']
  and reference['callbackBinding']['actualCallbackEqualsCanonicalRequired']is True
  and adapter['callbackBinding']['actualCallbackEqualsCanonicalRequired']is True
  and reference['selectedPrograms']['normalReturn']is True and transport['canonicalFF']['clearedOutputBytes']==8)
 records=baseline['records'];condition=records[tasks.CONDITION]['source'];task=records[tasks.TASK]['source']
 for name,row in records.items():tasks.validate_plan(name,row['source'])
 binding=_condition_binding(condition,baseline['gameConditionNull']['typedRequest'],reference)
 graph_child=dict(graph,parentBinding=binding)
 condition_program,pending=compile_member_program(condition,pins,wrapper_name=condition['wrapperName'],type_name=tasks.CONDITION,value4={},
  references={tasks.GAME_CONDITION:(KEY,'game-condition',KEY)},reference_children={tasks.GAME_CONDITION:graph_child},
  typed_requests={0:binding['typedRequest']},reference_binder=bind_condition)
 need('complete-TaskCondition-field-and-frame-program',pending==[])
 parents={r['fieldName']:r for r in baseline['parents']};need('exact-two-dictionary-joins',set(parents)=={'taskMap','conditionDict'})
 root_binding=_root_binding(owners,pins,parents['taskMap'])
 dictionaries={k:_dictionary(parents[k],pins,v,c)for k,v,c in
  (('taskMap',tasks.TASK,TASK_CAP),('conditionDict',tasks.CONDITION,CONDITION_CAP))}
 read=task['orderedSourceReads'][1];nested=dictionaries['conditionDict'];request=parents['conditionDict']['typedRequest']
 _call(read['instruction'],read['sourceTargetRva'])
 need('same-nested-dictionary-actual-site',read['fieldName']=='conditionDict'and read['declaredType']==nested['typeName']
  and read['sourceTargetRva']==nested['sourceTargetRva']and read['context']['methodSpec']==request['methodSpec']
  and read['context']['instructionRva']==request['instructionRva'])
 dictionary_child=dict(schema=SCHEMA,nativeInputs=pins,capabilities={DICT_CAP:nested},
  parentBinding=dict(fieldName='conditionDict',typeName=nested['typeName'],typedRequest=request,
   sourceTargetRva=read['sourceTargetRva'],sourceInstruction=read['instruction']))
 task_program,pending=compile_member_program(task,pins,wrapper_name=task['wrapperName'],type_name=tasks.TASK,value4={},
  collections={nested['typeName']:(DICT_CAP,'task-condition-dictionary',DICT_CAP)},collection_children={1:dictionary_child},
  typed_requests={1:request},collection_binder=bind_dictionary)
 need('complete-Task-field-and-frame-program',pending==[])
 string=baseline['pooledStringKey']['program']
 need('independent-pooled-string-slot-callback',string.get('sameReaderAndOutput')is True and string.get('entryRspRestored')is True
  and string.get('callbackOffsetForSlotFive')==400 and string.get('methodInfoOffsetForSlotFive')==408
  and all(records[n]['adapter']['canonicalRoutes']['symbolRvas']['dispatch']==parents['taskMap']['collection']['symbolRvas']['dispatch']for n in records))
 projected={}
 for name,program in((tasks.TASK,task_program),(tasks.CONDITION,condition_program)):
  source=records[name]['source'];projected[name]=dict(schema=RECORD_SCHEMA,typeName=name,wrapperName=source['wrapperName'],
   fields=[dict(fieldName=n,declaredType=t)for n,t in tasks.PLANS[name]],memberCount=len(tasks.PLANS[name]),program=program,
   readerMethod=source['method'],formatterMethod=source['lifecycle']['concreteFormatter']['method'],
   actualCanonicalCallbackEqualsProvedRecordRequired=True,nullAdmitted=True,positiveAdmitted=True)
 result=dict(schema=CAP_SCHEMA,typeName=dictionaries['taskMap']['typeName'],records=projected,dictionaries=dictionaries,
  condition=cap,conditionBinding=dict(binding,capability=KEY),rootBinding=root_binding,
  countLimit=COUNT_LIMIT,dictionaryEntryLimit=COUNT_LIMIT,
  positiveGameConditionAdmitted=True,storedTaskMapGrammarAdmitted=True,actualKeyCallbackEqualsPooledStringRequired=True,
  actualValueCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
  runtimeConditionEvaluationAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
 validate(result);return result


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack.levelscript_owner_sources import derive as derive_owners
 from scripts.game_data.memorypack.levelscript_game_condition_components import derive as derive_graph
 _publication_gate(image,pins);graph=derive_graph(image,pins)
 result=dict(schema=SCHEMA,status='pendingReview',nativeInputs=pins,capabilities={},proof=dict(gameCondition=graph),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,runtimeConditionEvaluationAdmitted=False)
 if graph['holds']:result['holds']=[dict(h,parentStage='GameCondition')for h in graph['holds']]
 else:
  stage='Task-root-source'
  try:
   owners=derive_owners(image,pins);result['proof']['root']=owners;stage='Task-record-and-dictionary-source'
   baseline=tasks.derive(image,pins,owners);result['proof']['tasks']=baseline;stage='Task-positive-field-composition'
   capability=compose(baseline,graph,pins,owners=owners)
   result.update(status='validated-conditional-Task-game-condition',capabilities={CAPABILITY:capability},holds=[])
  except(ValueError,KeyError,IndexError,TypeError)as error:
   result['holds']=[dict(stage=stage,validator='storyTaskGameCondition',failedGate=str(error).split(':',1)[0],
    reason=str(error)[:2200],sourcePath='scripts/game_data/memorypack/levelscript_task_game_condition_sources.py')]
 _publication_gate(image,pins);return json.loads(json.dumps(result))
