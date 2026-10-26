"""Own positive List<GameCondition> source, without recursive element grammar.

The exact closed reference-list carrier, constructor/Clear/provider/Add paths
and bounded counted loop are proved on the selected image. A recursive owner
must separately bind the actual element callback to complete GameCondition
wire grammar and own its parent local/field/frames and shared node budget.
"""
import json
from scripts.game_data.memorypack import reference_list_value_sources as native

TYPE='Beyond.Gameplay.GameCondition'
LIST=native.list_type(TYPE)
SCHEMA='endfield.story-game-condition-list-source.v1'


def need(key,condition):
 if not condition:raise ValueError('storyConditionListSource.'+key)


def verify(component,pins):
 need('exact-source-only-component',component.get('schema')==SCHEMA
  and component.get('status')=='proved-conditional-game-condition-list-source'and component.get('nativeInputs')==pins
  and component.get('typeName')==LIST and component.get('elementType')==TYPE
  and component.get('listFramingProved')is True and component.get('elementGrammarAdmitted')is False
  and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False
  and component.get('recursiveGrammarAdmitted')is False and'capabilities'not in component)
 source=component.get('proof',{}).get('listSource',{});w,base=native.verify_source(source,pins)
 need('same-own-closed-nominal-list',source.get('elementType')==TYPE and source.get('closedListType')==LIST
  and type(component.get('countLimit'))is int and component['countLimit']==source['countLimit']
  and w.get('elementType')==TYPE and w.get('closedCarrier',{}).get('name')==LIST
  and tuple(w.get('typedRequest',{}).get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
   (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[LIST]))
 args=w['closedCarrier'].get('classArguments',[])
 need('one-owned-CLASS18-element-carrier',isinstance(args,list)and len(args)==1 and args[0].get('name')==TYPE
  and len(bytes.fromhex(args[0].get('rawHex','')))==16 and bytes.fromhex(args[0]['rawHex'])[10:12]==bytes((18,0)))
 return w,base


def derive(image,pins,*,typed_request,call_target,count_limit=4096):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 _publication_gate(image,pins)
 need('finite-own-actual-list-request',tuple(typed_request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
  (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[LIST]))
 source=native.derive_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE,count_limit=count_limit)
 component=dict(schema=SCHEMA,status='proved-conditional-game-condition-list-source',nativeInputs=pins,typeName=LIST,
  elementType=TYPE,countLimit=count_limit,listFramingProved=True,elementGrammarAdmitted=False,parentFieldAdmitted=False,
  recursiveGrammarAdmitted=False,wholeOwnerAdmitted=False,proof=dict(listSource=source),
  actualElementCallbackEqualsProvedChildRequired=True,liveCallbackSelectionObserved=False)
 w,_=verify(component,pins)
 need('same-actual-closed-request-and-target',w['typedRequest']==typed_request and w['callTargetRva']==call_target-image.pe.image_base)
 _publication_gate(image,pins)
 return json.loads(json.dumps(component))


def bind_request(pins,join,component):
 w,_=verify(component,pins);usage=join.get('typedRequest',{});instruction=join.get('sourceInstruction',[])
 need('same-actual-parent-list-request',join.get('typeName')==LIST and usage==w.get('typedRequest')
  and isinstance(usage.get('methodSpec'),list)and len(usage['methodSpec'])==3 and all(type(x)is int for x in usage['methodSpec'])
  and type(join.get('sourceTargetRva'))is int and join['sourceTargetRva']==w.get('callTargetRva'))
 need('literal-parent-E8-instruction',isinstance(instruction,(tuple,list))and len(instruction)==2
  and type(instruction[0])is int and instruction[0]>=0 and type(instruction[1])is str)
 raw=bytes.fromhex(instruction[1])
 need('same-actual-parent-E8-target',len(raw)==5 and raw[0]==0xe8
  and instruction[0]+5+int.from_bytes(raw[1:],'little',signed=True)==join['sourceTargetRva'])
 return dict(fieldName=join['fieldName'],typeName=LIST,elementType=TYPE,readerMethodDefinition=usage['methodSpec'][0],
  sourceTargetRva=join['sourceTargetRva'],typedRequest=usage,sourceInstruction=list(instruction),
  countLimit=component['countLimit'],listSource=component['proof']['listSource'],actualParentRequestAndCallJoined=True,
  actualElementCallbackEqualsProvedChildRequired=True,elementGrammarAdmitted=False,recursiveGrammarAdmitted=False,
  parentFieldAdmitted=False,parentLocalStoreAndAllFramesRequired=True,wholeOwnerAdmitted=False)


def derive_member(image,pins,*,parent_source,member_index,count_limit=4096):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 _publication_gate(image,pins);scope=parent_source.get('sourceScope',{});reads=parent_source.get('orderedSourceReads',[])
 need('same-complete-current-parent-source',parent_source.get('schema')=='endfield.generated-concrete-reader-source.v1'
  and parent_source.get('nativeInputs')==scope.get('nativeInputs')==pins and parent_source.get('completeSelectedCallerAdmitted')is True
  and parent_source.get('childGrammarAdmitted')is False and parent_source.get('wholeOwnerAdmitted')is False
  and type(member_index)is int and 0<=member_index<len(reads)and reads==scope.get('events'))
 read=reads[member_index];context=read.get('context',{})
 need('same-actual-reference-list-source',read.get('memberIndex')==member_index and read.get('declaredType')==LIST
  and read.get('kind')=='reference:'+LIST and context.get('methodOwner')=='MemoryPack.MemoryPackReader'
  and context.get('methodName')=='ReadPackable'and context.get('fullTypeName')==LIST and context.get('typeKind')==21)
 usage=derive_typed_usage_context(image,context['instructionRva'],label='storyConditionListSource.parent')
 need('same-current-parent-context',(usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec'))==
  (context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec')))
 component=derive(image,pins,typed_request=usage,call_target=image.pe.image_base+read['sourceTargetRva'],count_limit=count_limit)
 binding=bind_request(pins,dict(fieldName=read['fieldName'],typeName=LIST,typedRequest=usage,
  sourceTargetRva=read['sourceTargetRva'],sourceInstruction=read['instruction']),component)
 need('actual-source-owned-by-complete-parent',read['instruction']in scope.get('selectedProgram',[]))
 image.check_windows(parent_source['codeWindows'],label='storyConditionListSource.parent')
 image.check_instruction_windows([read['instruction']],label='storyConditionListSource.actual-call')
 component['parentBinding']=binding;_publication_gate(image,pins)
 return component
