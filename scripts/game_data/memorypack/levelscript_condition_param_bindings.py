"""Actual constructed-reference Param requests, separate from field frames."""
import json

from scripts.game_data.memorypack.levelscript_condition_param_sources import SCHEMA,CAP_PREFIX

LABEL='storyConditionParamBinding'


def need(key,condition):
 if not condition:raise ValueError(LABEL+'.'+key)


def _validate_capability(component,capability):
 from scripts.game_data.codecs.levelscript.current_condition_param import validate as primitive
 from scripts.game_data.codecs.levelscript.current_condition_enum_param import validate as enum
 from scripts.game_data.codecs.levelscript.current_condition_storage_param import validate as storage
 from scripts.game_data.codecs.levelscript.current_condition_int2_param import validate as int2
 from scripts.game_data.codecs.levelscript.current_condition_list_param import validate as listing
 from scripts.game_data.codecs.levelscript.current_condition_script_task_param import validate as task
 from scripts.game_data.codecs.levelscript.current_action_dedicated_param import validate as dedicated
 from scripts.game_data.memorypack.levelscript_condition_enum_param_components import SCHEMA as ENUM_SCHEMA
 from scripts.game_data.memorypack.levelscript_condition_storage_param_components import SCHEMA as STORAGE_SCHEMA
 from scripts.game_data.memorypack.levelscript_int2_param_sources import SCHEMA as INT2_SCHEMA
 from scripts.game_data.memorypack.levelscript_condition_list_param_components import SCHEMA as LIST_SCHEMA
 from scripts.game_data.memorypack.levelscript_script_task_param_sources import SCHEMA as TASK_SCHEMA
 from scripts.game_data.memorypack.levelscript_action_dedicated_param_components import SCHEMA as DEDICATED_SCHEMA
 validators={SCHEMA:primitive,ENUM_SCHEMA:enum,STORAGE_SCHEMA:storage,INT2_SCHEMA:int2,LIST_SCHEMA:listing,TASK_SCHEMA:task,DEDICATED_SCHEMA:dedicated}
 schema=component.get('schema');need('explicit-owned-Param-domain',schema in validators)
 cap=component.get('capabilities',{}).get(capability,{})
 validators[schema](cap)
 return cap


def derive_binding(image,pins,*,typed_request,source_target,source_instruction,component,capability):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_pointer_extent
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 _publication_gate(image,pins);base=image.pe.image_base
 need('same-native-owned-Param-child',component.get('nativeInputs')==pins)
 cap=_validate_capability(component,capability)
 need('same-exact-capability-name',capability==CAP_PREFIX+cap['typeName'])
 validate_typed_usage_context(image,typed_request,label=LABEL)
 bound=bind_typed_read(image,typed_request,method_name='ReadValue',argument=cap['typeName'],kind=21,reference=True)
 argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
 ctx=NativeReferenceContext(image);carrier=closed_generic_reference_pointer_extent(ctx,argument.type_pointer_va)
 need('same-fresh-closed-Param-definition-and-value',carrier['type']==cap['typeName']and carrier['bytes']==8
  and carrier['argumentTypes']==[cap['valueType']]
  and carrier['definitionTypeIndex']==ctx.index.types['Beyond.Gameplay.Actions.Param`1'].index)
 need('actual-reader-definition-and-source',bound['methodDefinition']==cap['readerMethodDefinition']
  and type(source_target)is int and source_target-base==cap['sourceTargetRva'])
 need('actual-owned-source-instruction',isinstance(source_instruction,(tuple,list))and len(source_instruction)==2
  and type(source_instruction[0])is int and source_instruction[0]>=0 and type(source_instruction[1])is str)
 raw=bytes.fromhex(source_instruction[1])
 need('exact-E8-source-target',len(raw)==5 and raw[0]==232
  and source_instruction[0]+5+int.from_bytes(raw[1:],'little',signed=True)==source_target-base)
 image.check_instruction_windows([source_instruction],label=LABEL+'.actual-parent-call')
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-condition-Param-parent-request.v1',nativeInputs=pins,
  typeName=cap['typeName'],capability=capability,capabilitySnapshot=cap,typedRequest=typed_request,
  sourceInstruction=list(source_instruction),readerMethodDefinition=bound['methodDefinition'],sourceTargetRva=source_target-base,
  actualArgumentRawHex=image.pe.bytes_at_va(argument.type_pointer_va,16).hex().upper(),closedCarrier=carrier,
  actualRequestProved=True,actualSourceCallProved=True,pointerEquivalenceClaimed=False,
  parentFieldAdmitted=False,parentArgumentLocalStoreFrameRequired=True,wholeOwnerAdmitted=False)))


def bind_reference(pins,join,child,capability):
 """The enclosing compiler must supply its actual full source context and E8."""
 cap=_validate_capability(child,capability)
 usage=join.get('typedRequest',{});context=join.get('sourceContext',{});site=usage.get('instructionRva')
 binding=child.get('parentBindings',{}).get(str(site),{})
 need('same-owned-child-schema-and-scope',child.get('nativeInputs')==pins
  and capability==CAP_PREFIX+cap['typeName']and join.get('typeName')==cap['typeName'])
 need('actual-closed-ReadValue-request',(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),
  usage.get('classArguments'),usage.get('methodArguments'))==(6,'MemoryPack.MemoryPackReader','ReadValue',[],[cap['typeName']])
  and isinstance(usage.get('methodSpec'),(tuple,list))and len(usage['methodSpec'])==3
  and all(type(n)is int for n in usage['methodSpec'])and type(site)is int and site>=0)
 raw=bytes.fromhex(context.get('argumentRawHex',''))
 need('actual-constructed-reference-source-context',len(raw)==16 and raw[10:12]==bytes((21,0))
  and(context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'),context.get('register'),context.get('typeKind'))
     ==('MemoryPack.MemoryPackReader','ReadValue',cap['typeName'],'rdx',21)
  and type(context.get('typeKind'))is int
  and(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))
     ==(site,usage.get('instructionHex'),usage['methodSpec']))
 need('fresh-actual-Param-parent-binding',binding.get('schema')=='endfield.story-condition-Param-parent-request.v1'
  and binding.get('nativeInputs')==pins and binding.get('typeName')==cap['typeName']and binding.get('capability')==capability
  and binding.get('capabilitySnapshot')==cap and binding.get('typedRequest')==usage
  and binding.get('sourceInstruction')==join.get('sourceInstruction')
  and bytes.fromhex(binding.get('actualArgumentRawHex',''))==raw
  and binding.get('actualRequestProved')is True and binding.get('actualSourceCallProved')is True
  and binding.get('parentFieldAdmitted')is False and binding.get('pointerEquivalenceClaimed')is False)
 carrier=binding.get('closedCarrier',{})
 owners=[r for r in child.get('owners',[])if r.get('typeName')==cap['typeName']]
 need('one-owned-complete-Param-child-proof',len(owners)==1 and owners[0].get('status')=='validated-conditional-Param-child'
  and owners[0].get('capability')==cap)
 original_carrier=owners[0].get('proof',{}).get('closedCarrier',{})
 need('same-closed-carrier-and-reference-reader',carrier.get('type')==cap['typeName']and carrier.get('argumentTypes')==[cap['valueType']]
  and type(carrier.get('bytes'))is int and carrier['bytes']==8
  and type(carrier.get('definitionTypeIndex'))is int and carrier['definitionTypeIndex']==original_carrier.get('definitionTypeIndex')
  and carrier.get('definitionTypeRecordHex')==original_carrier.get('definitionTypeRecordHex')
  and type(binding.get('readerMethodDefinition'))is int and type(binding.get('sourceTargetRva'))is int
  and(binding['readerMethodDefinition'],binding['sourceTargetRva'])
     ==(usage['methodSpec'][0],join.get('sourceTargetRva'))==(cap['readerMethodDefinition'],cap['sourceTargetRva']))
 return dict(fieldName=join['fieldName'],typeName=cap['typeName'],capability=capability,
  readerMethodDefinition=cap['readerMethodDefinition'],sourceTargetRva=cap['sourceTargetRva'],
  sourceReferenceKind=21,referenceOutputBytes=8,closedCarrierProved=True,
  actualCallbackEqualsProvedChildRequired=True,parentArgumentLocalStoreFrameRequired=True,parentFieldAdmitted=False)
