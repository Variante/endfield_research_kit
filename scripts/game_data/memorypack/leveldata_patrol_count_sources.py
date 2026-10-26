"""Actual Patrol SafeCount clone and its own nominal interface context.

The complete clone is compared with the independently selected ordinary
SafeCount source through the existing source-equivalence algorithm. Both
return zero for null and otherwise preserve the same collection and slot-zero
Count call. Inflated receiver/interface/callback selection and the meaning of
that callback remain separate; a List size is never substituted by name.
"""
import json
from scripts.game_data.memorypack.leveldata_patrol_point_sources import POINT

SCHEMA='endfield.story-patrol-count-source.v1'


def need(check,condition):
 if not condition:raise ValueError('storyPatrolCount.'+check)


def context_join(usage,*,method_definition,formal_parameter,context,argument_raw,point_definition):
 """Reciprocal actual MVAR/interface declaration joins, without inflation."""
 need('exact-actual-SafeCount-request',(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),
  usage.get('classArguments'),usage.get('methodArguments'))==(6,'Beyond.CollectionExtensions','SafeCount',[],[POINT]))
 instruction=bytes.fromhex(usage.get('instructionHex',''));spec=usage.get('methodSpec')
 need('literal-actual-RDX-MethodInfo-and-spec',len(instruction)==7 and instruction[:3]==bytes.fromhex('488b15')
  and isinstance(spec,(tuple,list))and len(spec)==3 and all(type(v)is int for v in spec)
  and spec[0]==method_definition and spec[1]==-1 and spec[2]>=0)
 need('own-ordinary-Point-reference',type(point_definition)is int and point_definition>=0
  and len(argument_raw)==16 and argument_raw[10:12]==bytes((18,0))
  and int.from_bytes(argument_raw[:8],'little')==point_definition)
 need('own-SafeCount-method-context',context.get('definition')==method_definition and context.get('isMethod')is True
  and context.get('typeName')=='Beyond.CollectionExtensions'and context.get('methodName')=='SafeCount')
 entries=context.get('entries',[])
 need('two-exact-owned-interface-context-slots',len(entries)==2
  and[(r.get('relativeSlot'),r.get('kind'))for r in entries]==[(0,2),(1,3)])
 interface,count=entries
 need('actual-ICollection-interface-context',interface.get('type',{}).get('definition',{}).get('name')=='System.Collections.Generic.ICollection`1')
 args=interface['type'].get('classArguments',[])
 need('sole-reciprocal-SafeCount-MVAR',len(args)==1
  and args[0].get('parameterOwner',{}).get('methodIndex')==method_definition
  and type(args[0]['parameterOwner'].get('ordinal'))is int and args[0]['parameterOwner']['ordinal']==0
  and bytes.fromhex(args[0].get('rawHex',''))[10:12]==bytes((30,0)))
 need('formal-IList-same-actual-owned-MVAR',formal_parameter.get('definition',{}).get('name')=='System.Collections.Generic.IList`1'
  and formal_parameter.get('classArguments')==args)
 need('same-ICollection-Count-context',(count.get('typeName'),count.get('methodName'),count.get('classArguments'),count.get('methodArguments'))==
  ('System.Collections.Generic.ICollection`1','get_Count',args,[]))
 return dict(methodDefinition=method_definition,nominalElement=POINT,pointTypeDefinition=point_definition,
  methodContextInterfaceSlot=0,interfaceSelector=0,originalMethodArgumentRetained=True,
  runtimeInflatedInterfaceIdentityObserved=False,actualListCountMeaningProved=False)


def derive(image,pins,*,typed_request,source_target,source_instruction):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
 from scripts.game_data.il2cpp.safe_count_clone_program import check_safe_count_clone
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
 from scripts.game_data.memorypack.unmanaged_enum_member_sources import bind_actual_call
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 validate_typed_usage_context(image,typed_request,label='storyPatrolCount.actual')
 actual_call=bind_actual_call(typed_request,source_instruction,source_target=source_target,base=base)
 image.check_instruction_windows([source_instruction],label='storyPatrolCount.actualE8')
 spec=typed_request['methodSpec'];method=md.methods[spec[0]];params=list(md.parameters_for(method))
 need('own-static-SafeCount-Int32-signature',image.type_name(method.declaring_type)=='Beyond.CollectionExtensions'
  and md.string(method.name_index)=='SafeCount'and method.flags&16 and method.generic_container_index>=0
  and len(params)==1 and ctx.type_name(method.return_type)=='int')
 scalar.ordinary(image,ctx.type_pointer(method.return_type),8,'storyPatrolCount.return')
 scalar.ordinary(image,ctx.type_pointer(params[0].type_index),21,'storyPatrolCount.formal',reference=True)
 argument,=image.instantiations.resolve(spec[2]).arguments
 scalar.ordinary(image,argument.type_pointer_va,18,'storyPatrolCount.Point',reference=True)
 need('own-nongeneric-Point-reference',not ctx.is_value_type(POINT)and ctx.index.types[POINT].generic_container_index<0)
 symbols=ContextSymbols(image);context=symbols.context(method.index,is_method=True)
 formal=symbols.type(ctx.type_pointer(params[0].type_index))
 nominal=context_join(typed_request,method_definition=method.index,formal_parameter=formal,context=context,
  argument_raw=image.pe.bytes_at_va(argument.type_pointer_va,16),point_definition=ctx.index.types[POINT].index)
 interface_count=md.methods[context['entries'][1]['methodSpec'][0]]
 scalar.owned_method_abi(image,ctx,interface_count.index,ctx.index.types['System.Collections.Generic.ICollection`1'].index,
  ('int',8,False),[],'storyPatrolCount.interface')
 need('actual-interface-selector-zero',interface_count.slot==0)
 observed=GenericEntries(image).observe(method.index,[],['object'])
 need('one-independent-nonnull-ordinary-count-source',len(observed)==1 and observed[0]['pointer']
  and observed[0]['registration']['indices'][-1]==-1)
 canonical=pointer.owned(image,observed[0]['pointer']);clone=pointer.owned(image,source_target)
 need('actual-complete-clone-row-schedule',len(clone['rows'])==27)
 target=control_transfer(clone['rows'][11]).get('target')
 need('actual-selected-indexed-context-helper',type(target)is int and target>base)
 raw=image.pe.bytes_at_va(target,15)
 leaf=decode_type_data_initialization_instructions(image.mapper,raw,target)
 equivalence=check_safe_count_clone(canonical['rows'],clone['rows'],leaf)
 def captured(body):return dict(sourceWindows=body['windows'],sourceRegions=[[a,h.hex().upper()]for a,h in body['regions']])
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-SafeCount-source',nativeInputs=pins,
  proof=dict(typedRequest=typed_request,actualCall=actual_call,nominalContextJoin=nominal,formalParameter=formal,
   methodContext=context,independentOrdinaryRegistration=observed[0],canonical=captured(canonical),clone=captured(clone),
   exactIndexedHelperSlice=[target-base,raw.hex().upper()],selectedCloneEquivalence=equivalence),
  nullCollectionReturnsZero=True,nonnullCollectionAndSlotZeroArgumentsPreserved=True,
  actualListCountMeaningProved=False,wholeConversionProved=False,wholeInitializerProved=False,
  runtimeInvocationObserved=False,playbackProved=False,evidenceBoundary=dict(
   exact='Actual closed SafeCount<Point> request/E8, reciprocal own IList/ICollection MVAR context and Count slot-zero ABI, complete clone/canonical programs and exact indexed-context tail slice.',
   conditional=__doc__,unresolved=['runtime inflated List/ICollection class and method pair','actual selected Count callback source and list-size meaning','full conversion/initializer, checkpoints and playback']))))
