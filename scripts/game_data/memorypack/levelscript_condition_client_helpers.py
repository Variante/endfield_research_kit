"""Actual inline condition header and closed reference reader source joins.

The closed twelve-byte tail sources have no invented unwind extent. Each one
supplies its freshly authenticated MethodInfo and jumps to an independently
proved reference reader. The alternative ready-RGCTX path loads the exact
ReadPackable slot-zero ReadValue context. No pointer equivalence is inferred.
"""
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='storyConditionClientHelpers'


def need(key,condition):
 if not condition:raise ValueError(LABEL+'.'+key)


def before_program(regions,entry,offsets):
 rem=bytes((offsets['bufferLength'],)).hex();cur=bytes((offsets['currentPtr'],)).hex()
 g=BytesPath(regions,entry);g.take('4883ec28','3b51'+rem);g.branch('0f8f',False)
 g.take('488b41'+cur,'4883c428','c3')
 return dict(selectedBytes=g.seen,normalReturn=True,entryRspRestored=True,
  incomingReaderUnchanged=True,readerWrites=0,currentPointerReturned=True,
  condition='Incoming signed count is one and coherent Reader.bufferLength is at least one. Refill and negative counts are excluded.')


def advance_program(regions,entry,offsets,*,zero=False):
 need('literal-advance-path',type(zero)is bool)
 cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
 g=BytesPath(regions,entry);g.take('85d2');g.branch('74',zero,1)
 if not zero:
  g.take('48895c2410','57','4883ec20','4863fa','488bd9','4889742430','8b71'+rem,'2bf7')
  g.branch('0f88',False);g.take('48017b'+cur,'017b'+adv,'017b'+used,'8973'+rem,
   '488b742430','488b5c2438','4883c420','5f')
 g.take('c3')
 return dict(selectedBytes=g.seen,normalReturn=True,entryRspRestored=True,zeroCount=zero,
  currentPointerAdds='same signed incoming count'if not zero else 0,
  advancedCountAdds='same signed incoming count'if not zero else 0,
  consumedCountAdds='same signed incoming count'if not zero else 0,
  bufferLengthSubtracts='same signed incoming count'if not zero else 0,
  condition='Count zero, or positive count one with sufficient nonnegative Reader remainder, coherent nonwrapping cursor accounting and disjoint storage. Error/refill paths are excluded.')


def ushort_program(regions,entry,offsets):
 cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','8379'+rem+'02','488bfa','488bd9')
 g.branch('0f8c',False);g.take('488b41'+cur,'0fb700','668907','8b7b'+rem,'83c7fe')
 g.branch('0f88',False);g.take('488343'+cur+'02','8343'+adv+'02','8343'+used+'02','897b'+rem,
  '488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,wireBytes=2,outputBytes=2,readerRegister='rcx',outputRegister='rdx',
  suppliedMethodInfoUnused=True,allFourReaderUpdatesProved=True,normalReturn=True,entryRspRestored=True,
  condition='Sufficient buffered little-endian UInt16 input, stable disjoint Reader/output/frame and coherent nonwrapping cursor accounting; refill/errors excluded.')


def forwarder_program(regions,entry,canonical):
 g=BytesPath(regions,entry);site=g.at;cell=g.relative('488b15');target=g.relative('e9')
 need('exact-reference-reader-tail',target==canonical)
 return dict(selectedBytes=g.seen,contextInstructionVa=site,contextCellVa=cell,nestedTargetVa=target,
  exactSelectedSourceBytes=12,sameReader=True,nonvolatileRegistersUntouched=True,normalTailReturn=True,
  fullFunctionExtentClaimed=False,pointerEquivalenceClaimed=False)


def derive_common(image,pins,selection,core,routes):
 from scripts.game_data.il2cpp.context import method_parameter_owner
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_generic_contexts
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import modelview_reference_sources,pointer_param as pointer,scalar_param_native as scalar
 from scripts.game_data.memorypack.packable_reference_sources import validate_packable_context
 from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
 base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 offsets=scalar.reader_offsets(image,LABEL);need('actual-inline-current-pointer-slot',offsets['currentPtr']==80)
 helpers={}
 for role,key,function in(('before','beforeTargetVa',before_program),('advance','advanceTargetVa',advance_program),('ushort','rawHeaderTargetVa',ushort_program)):
  target=selection[key];body=pointer.owned(image,target)
  programs=[function(body['regions'],target,offsets)]
  if role=='advance':programs.append(function(body['regions'],target,offsets,zero=True))
  helpers[role]=dict(entryRva=target-base,programs=programs,windows=body['windows'],regions=[(a,b.hex().upper())for a,b in body['regions']])
 usage=derive_typed_usage_context(image,selection['rawHeaderUsage']['instructionVa']-base,label=LABEL+'.actual-ushort')
 need('actual-closed-ushort-request',(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))
  ==(6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],['ushort']))
 method=md.methods[usage['methodSpec'][0]];need('own-ushort-method-ABI',not method.flags&16 and method.parameter_count==1 and ctx.type_name(method.return_type)=='void')
 scalar.ordinary(image,ctx.type_pointer(method.return_type),1,LABEL+'.void')
 args=image.instantiations.resolve(usage['methodSpec'][2]).arguments;need('sole-ushort-argument',len(args)==1)
 scalar.ordinary(image,args[0].type_pointer_va,7,LABEL+'.ushort')
 section=md.sections['genericContainers'];at=section.offset+method.generic_container_index*16
 need('bounded-ushort-generic-owner',method.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16)
 owner,count,is_method,start=struct.unpack_from('<iiii',md.buf,at)
 parameter=method_parameter_owner(md.buf,start,[m.generic_container_index for m in md.methods],source=LABEL)
 formal,=md.parameters_for(method);raw=image.pe.bytes_at_va(ctx.type_pointer(formal.type_index),16)
 need('same-sole-owned-out-MVAR',(owner,count,is_method)==(method.index,1,1)and parameter.get('methodIndex')==method.index
  and parameter.get('ordinal')==0 and raw[10:12]==bytes((30,32))and int.from_bytes(raw[:8],'little')==start)
 helpers['ushort']['typedRequest']=usage;helpers['ushort']['parameterOwner']=parameter
 value=core['readValue'];need('same-reviewed-value-reader-inputs',value['nativeInputs']==pins)
 body=pointer.owned(image,base+value['entryRva']);need('complete-reviewed-value-source-windows',body['windows']==value['ownedWindows'])
 validate_generic_contexts(image,value['contexts'],label=LABEL+'.ReadValue')
 def fail(key,expected,actual):raise ValueError(LABEL+'.'+key+':expected='+str(expected)[:300]+':actual='+str(actual)[:300])
 entries=GenericEntries(image)
 packable=validate_packable_context(image,value['contexts'][0],value['contexts'][1]['definition'],entries,fail=fail)
 generic=validate_read_value_context(image,value['contexts'][1],value['contexts'][2],entries,fail=fail)
 program=modelview_reference_sources.read_value(body['regions'],body['pointer'],{k:base+v for k,v in routes['symbolRvas'].items()})
 helpers['readValue']=dict(entryRva=value['entryRva'],packableContext=packable,valueContext=generic,program=program,
  windows=body['windows'],regions=[(a,b.hex().upper())for a,b in body['regions']],pointerEquivalenceClaimed=False)
 return helpers


def bind_returning(image,path,typed_request,bound,helpers,*,canonical):
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.levelscript_two_routes_native import _window
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 base=image.pe.image_base;target=path['childTargetVa'];mode=path['childUsage'].get('contextMode','direct-rdx')
 if mode=='ready-r14-rgctx56-slot0':
  need('exact-ready-nested-ReadValue-source',target-base==helpers['readValue']['entryRva']
   and bound['methodDefinition']==helpers['readValue']['packableContext']['packableDefinition'])
  return dict(mode=mode,actualTargetRva=target-base,nestedReadValueDefinition=helpers['readValue']['valueContext']['readerMethodDefinition'],
   actualSource=helpers['readValue'],closedInflationObserved=False,pointerEquivalenceClaimed=False)
 need('actual-direct-MethodInfo-source-mode',mode=='direct-rdx')
 if target==canonical:return dict(mode='actual-canonical-returning-reader',actualTargetRva=target-base,pointerEquivalenceClaimed=False)
 raw=image.pe.bytes_at_va(target,12);program=forwarder_program([(target,raw)],target,canonical)
 usage=derive_typed_usage_context(image,target-base,label=LABEL+'.closed-tail-request')
 argument=typed_request['methodArguments'][0]
 nested=bind_typed_read(image,usage,method_name='ReadPackable',argument=argument,kind=18,reference=True)
 need('same-exact-closed-forwarder-method-and-carrier',nested==bound)
 return dict(mode='actual-closed-context-tail',actualTargetRva=target-base,program=program,typedRequest=usage,
  windows=[_window(image,target,target+12,'actual complete two-instruction selected tail source; no unwind extent claimed')],
  sourceRegions=[(target,raw.hex().upper())],pointerEquivalenceClaimed=False)
