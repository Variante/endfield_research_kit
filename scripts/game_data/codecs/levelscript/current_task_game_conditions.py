"""Explicit positive current Task cursor; no root activation or evaluation."""
import struct

from scripts.game_data.codecs.levelscript.current_collections import Reader
from scripts.game_data.codecs.levelscript.param_graph import ParamGraphDecodeError
from scripts.game_data.codecs.levelscript import current_game_condition as conditions
from scripts.game_data.memorypack import levelscript_task_sources as tasks
from scripts.game_data.memorypack import levelscript_task_game_condition_sources as source


def need(key,condition):
 if not condition:raise ParamGraphDecodeError('currentTaskGameConditions.'+key)


def validate(cap):
 need('complete-owned-current-Task-capability',isinstance(cap,dict)and cap.get('schema')==source.CAP_SCHEMA
  and type(cap.get('countLimit'))is int and cap['countLimit']==source.COUNT_LIMIT
  and type(cap.get('dictionaryEntryLimit'))is int and cap['dictionaryEntryLimit']==source.COUNT_LIMIT
  and all(cap.get(k)is True for k in('positiveGameConditionAdmitted','storedTaskMapGrammarAdmitted',
   'actualKeyCallbackEqualsPooledStringRequired','actualValueCallbackEqualsProvedChildRequired'))
  and all(cap.get(k)is False for k in('liveFormatterSelectionObserved','runtimeConditionEvaluationAdmitted',
   'parentFieldAdmitted','wholeOwnerAdmitted')))
 conditions.validate(cap.get('condition',{}))
 records=cap.get('records');dictionaries=cap.get('dictionaries')
 need('exact-two-record-and-dictionary-domain',isinstance(records,dict)and set(records)==set(tasks.PLANS)
  and isinstance(dictionaries,dict)and set(dictionaries)=={'taskMap','conditionDict'})
 from scripts.game_data.memorypack.levelscript_game_condition_components import CAPABILITY as CONDITION
 operations={tasks.TASK:[('bool-byte',None),('task-condition-dictionary',source.DICT_CAP),('bool-byte',None),('scalar32',None)],
  tasks.CONDITION:[('game-condition',CONDITION),('bool-byte',None),('scalar32',None)]}
 for name,plan in tasks.PLANS.items():
  row=records[name];program=row.get('program',{});reads=program.get('reads',[])
  need('exact-compiled-record-plan',row.get('schema')==source.RECORD_SCHEMA and row.get('typeName')==name
   and type(row.get('wrapperName'))is str and row.get('memberCount')==len(plan)
   and row.get('nullAdmitted')is True and row.get('positiveAdmitted')is True
   and row.get('actualCanonicalCallbackEqualsProvedRecordRequired')is True
   and row.get('fields')==[dict(fieldName=n,declaredType=t)for n,t in plan]
   and program.get('memberCount')==len(plan)and len(reads)==len(plan)
   and[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in reads]==
    [(i,n,*operations[name][i])for i,(n,t)in enumerate(plan)]
   and program.get('requiredCapabilities')==sorted(c for k,c in operations[name]if c is not None))
  for key in('readerMethod','formatterMethod'):
   method=row.get(key)
   need('own-record-method-declaration',isinstance(method,list)and len(method)==4 and type(method[0])is int
    and type(method[3])is int and method[3]>0 and method[2]=='Deserialize'
    and method[1]==(row['wrapperName']if key=='readerMethod'else row['wrapperName']+'+'+row['wrapperName'].rsplit('.',1)[-1]+'Formatter'))
  bindings=program.get('childBindings',[])
  need('exact-one-record-child-binding',len(bindings)==1)
  binding=bindings[0];field=plan[0 if name==tasks.CONDITION else 1]
  expected=CONDITION if name==tasks.CONDITION else source.DICT_CAP
  need('exact-owned-record-child-binding',(binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))==(*field,expected)
   and type(binding.get('readerMethodDefinition'))is int and binding['readerMethodDefinition']>=0
   and type(binding.get('sourceTargetRva'))is int and binding['sourceTargetRva']>0)
 for key,value,child in(('taskMap',tasks.TASK,source.TASK_CAP),('conditionDict',tasks.CONDITION,source.CONDITION_CAP)):
  row=dictionaries[key];name='System.Collections.Generic.Dictionary`2<string,'+value+'>'
  need('independent-exact-typed-dictionary',row.get('typeName')==name
   and(row.get('keyType'),row.get('keyWireKind'),row.get('valueType'),row.get('valueCapability'))==('string','pooled-string',value,child)
   and type(row.get('countLimit'))is int and row['countLimit']==source.COUNT_LIMIT and row.get('headerBytes')==4
   and row.get('sourceWitnessClassArguments')==['object','object']
   and all(row.get(k)is True for k in('freshDictionaryRequired','actualErasedDictionaryCallbackEqualsProvedSourceRequired',
    'compatibleClosedContextsAndTypedHelpersRequired','actualKeyCallbackEqualsPooledStringRequired','actualValueCallbackEqualsProvedChildRequired'))
   and type(row.get('closedPointerEquivalenceProved'))is bool and row.get('liveFormatterSelectionObserved')is False
   and type(row.get('readerMethodDefinition'))is int and row['readerMethodDefinition']>=0
   and type(row.get('sourceTargetRva'))is int and row['sourceTargetRva']>0)
 need('same-root-dictionary-nominal',cap.get('typeName')==dictionaries['taskMap']['typeName'])
 root=cap.get('rootBinding',{});dictionary=dictionaries['taskMap']
 need('actual-enclosing-root-field-binding',root.get('ownerType')=='Beyond.Gameplay.LevelScriptData'
  and(root.get('fieldName'),root.get('typeName'))==('taskMap',dictionary['typeName'])
  and all(root.get(k)is True for k in('existingWrapperRequired','disabledCollectorRequired',
   'selectedCallBytesChecked','rootProgramFreshlyDerivedRequired'))
  and root.get('rootGrammarAdmitted')is False and type(root.get('storeOffset'))is int and root['storeOffset']>=16
  and(root.get('readerMethodDefinition'),root.get('sourceTargetRva'))==
   (dictionary['readerMethodDefinition'],dictionary['sourceTargetRva']))
 source._request(root.get('typedRequest'),dictionary['typeName'],'ReadPackable')
 need('same-root-dictionary-definition',root['typedRequest']['methodSpec'][0]==root['readerMethodDefinition'])
 source._call(root.get('sourceInstruction'),root['sourceTargetRva'])
 nested=records[tasks.TASK]['program']['childBindings'][0];dictionary=dictionaries['conditionDict']
 need('same-nested-dictionary-call',(nested['readerMethodDefinition'],nested['sourceTargetRva'])==
  (dictionary['readerMethodDefinition'],dictionary['sourceTargetRva']))
 binding=cap.get('conditionBinding',{});actual=records[tasks.CONDITION]['program']['childBindings'][0]
 need('same-actual-GameCondition-call',all(binding.get(k)==actual.get(k)for k in
  ('fieldName','typeName','capability','readerMethodDefinition','sourceTargetRva')))
 source._request(binding.get('typedRequest'),tasks.GAME_CONDITION,'ReadValue')
 need('same-GameCondition-definition',binding['typedRequest']['methodSpec'][0]==binding['readerMethodDefinition'])
 source._call(binding.get('sourceInstruction'),binding['sourceTargetRva'])


def read(reader,field,cap,*,dictionary_budget=None,condition_budget=None,param_budget=None):
 validate(cap)
 def budget(value,limit,name):
  if value is None:return[limit]
  need('literal-shared-'+name,isinstance(value,list)and len(value)==1 and type(value[0])is int and 0<=value[0]<=limit)
  return value
 entries=budget(dictionary_budget,cap['dictionaryEntryLimit'],'dictionary-budget')
 nodes=budget(condition_budget,cap['condition']['nodeLimit'],'condition-budget')
 elements=budget(param_budget,cap['condition']['paramElementLimit'],'Param-budget')
 def boolean(path):
  value=reader.number('<B',path);return dict(value=bool(value),rawByte=value)
 def dictionary(path,value):
  start=reader.offset;reader.need(4,path+'.count');count=struct.unpack_from('<i',reader.data,start)[0]
  if not -1<=count<=cap['countLimit']:raise ParamGraphDecodeError(f'{path}:task-dictionary-count-limit,offset={start},actual={count}')
  if max(count,0)>entries[0]:raise ParamGraphDecodeError(f'{path}:task-dictionary-entry-budget,offset={start},actual={count}')
  entries[0]-=max(count,0);reader.offset+=4;rows=[];seen=set()
  for i in range(max(0,count)):
   child=path+'['+str(i)+']';at=reader.offset;key=reader.string(child+'.key')
   if key is None:raise ParamGraphDecodeError(f'{child}:null-dictionary-key,offset={at}')
   if key in seen:raise ParamGraphDecodeError(f'{child}:duplicate-key,offset={at},actual={key!r}')
   seen.add(key);item=value(child+'.value');rows.append(dict(keyOffset=at,endOffset=reader.offset,key=key,value=item))
  return dict(startOffset=start,endOffset=reader.offset,status='null'if count==-1 else'present',
   count=None if count==-1 else count,entries=None if count==-1 else rows)
 def condition(path):
  start=reader.offset
  if not reader.member(path,3):return None
  value=conditions.read(reader,path+'.condition',cap['condition'],budget=nodes,param_budget=elements)
  main=boolean(path+'.isMainObjective');objective=reader.number('<i',path+'.objectiveEnum')
  return dict(startOffset=start,endOffset=reader.offset,serializedMemberCount=3,
   condition=value,isMainObjective=main,objectiveEnumRaw=objective)
 def task(path):
  start=reader.offset
  if not reader.member(path,4):return None
  tracked=boolean(path+'.canBeTracked');children=dictionary(path+'.conditionDict',condition)
  manual=boolean(path+'.needManualCheck');kind=reader.number('<i',path+'.taskType')
  return dict(startOffset=start,endOffset=reader.offset,serializedMemberCount=4,
   canBeTracked=tracked,conditionDict=children,needManualCheck=manual,taskTypeRaw=kind)
 result=dictionary(field,task)
 result.update(sourceBoundary='conditional',positiveGameConditionAdmitted=True,
  runtimeFormatterSelectionObserved=False,runtimeConditionEvaluationAdmitted=False)
 return result


def decode(data,offset,*,strings,capability):
 reader=Reader(data,offset,strings,'taskMap');result=read(reader,'taskMap',capability)
 return result,reader.offset


def conditional_sources(cap):
 validate(cap)
 rows=[dict(typeName=row['typeName'],sourceWitnessClassArguments=row['sourceWitnessClassArguments'],
  actualCallbackEqualsCanonicalRequired=True,compatibleClosedContextsAndTypedHelpersRequired=True,
  actualKeyCallbackEqualsPooledStringRequired=True,actualValueCallbackEqualsProvedChildRequired=True,
  freshDictionaryRequired=True,closedPointerEquivalenceProved=row['closedPointerEquivalenceProved'],
  countLimit=row['countLimit'],sharedDictionaryEntryLimit=cap['dictionaryEntryLimit'],runtimeFormatterSelectionObserved=False)
  for row in cap['dictionaries'].values()]
 graph=cap['condition'];rows.append(dict(typeName=graph['typeName'],rootWrapper=graph['rootWrapper'],
  actualWrapperCallbackEqualsProvedConcreteRequired=True,actualRecursiveCallbackEqualsProvedBaseRequired=True,
  countLimit=graph['countLimit'],nodeLimit=graph['nodeLimit'],depthLimit=graph['depthLimit'],paramElementLimit=graph['paramElementLimit'],
  budgetsSharedAcrossTaskMap=True,runtimeFormatterSelectionObserved=False,runtimeConditionEvaluationAdmitted=False))
 return rows
