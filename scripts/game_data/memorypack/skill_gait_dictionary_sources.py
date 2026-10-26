"""Current exact static-out gait/Single dictionary source, independently typed.

The actual direct call body is proved without claiming that an absent closed
registration aliases a different instantiation. Provider/callback and helper
context compatibility remain explicit conditions of this finite source.
"""
import json
from scripts.game_data.memorypack import skill_gait_dictionary_programs as paths

OWNER='Beyond.SerializeFieldDictionary`2'
KEY='Beyond.Gameplay.Core.MovementComponent+GroundedMoveGait'
TYPE=OWNER+'<'+KEY+',float>'
CAPABILITY='skill-gait-single-dictionary'
LABEL='skillGaitDictionarySource'


def need(key,condition):
 if not condition:raise ValueError(LABEL+'.'+key)


def validate_event(event,setter):
 context=event.get('context',{});binding=event.get('staticOutSourceBinding',{});u=context.get('typedRequest',{})
 raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
 need('exact-static-reference-event',event.get('kind')=='reference:'+TYPE and event.get('declaredType')==TYPE
  and event.get('mode')=='typed-static-out-reference'and event.get('resultAbi')=='out-reference-local'
  and event.get('actualSourceProved')is True and event.get('referenceBytes')==setter.get('storedBytes')==8
  and context.get('contextMode')=='owned-static-out-gait-dictionary'and context.get('methodOwner')==OWNER
  and context.get('methodName')=='DeserializeV2'and context.get('fullTypeName')==TYPE and context.get('register')=='r8'
  and context.get('resultAbi')=='void-byref-reference8'
  and(u.get('typeName'),u.get('methodName'),u.get('classArguments'),u.get('methodArguments'))==(OWNER,'DeserializeV2',[KEY,'float'],[])
  and len(raw)==16 and raw[10]==21 and not raw[11]&128)
 need('same-actual-static-source-binding',binding==dict(typeName=TYPE,sourceTargetRva=event.get('sourceTargetRva'),
  readerMethodDefinition=context['methodSpec'][0],context=context,resultAbi='void-byref-reference8',referenceBytes=8,actualSourceProved=True))
 return context


def parent_setup(image,rows,path,events,header,*,base):
 """Own exact parent class-state guard and each fresh reference-local reset."""
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.memorypack import buff_ec_profiles_native as ec
 from scripts.game_data.memorypack.generated_header_sources import _owned_zero_source
 selected=[e for e in events if e.get('mode')=='typed-static-out-reference']
 need('finite-actual-three-parent-fields',len(selected)==3 and all(e['declaredType']==TYPE for e in selected)
  and(header.get('readerRegister'),header.get('outputRegister'))==('rdi','rbx')and header.get('ordinaryZeroFamily')is not None)
 initializers=[]
 for event in selected:
  position=next(i for i,row in enumerate(path)if ec.site(row,base)==event['instruction'])
  argument=ec.last_write(path,position,'rdx');op=argument.get('addressOperation',{})if argument else{}
  displacement=op.get('displacement')
  need('literal-static-out-RDX-home',op.get('destination')=='rdx'and op.get('base')=='rsp'and op.get('index')is None
   and not op.get('ripRelative')and type(displacement)is int and 32<=displacement<128)
  matches=[row for row in path[:position]if ec.raw(row)==bytes.fromhex('48896c24')+bytes((displacement,))]
  need('actual-positive-reference-reset',len(matches)==1);store=matches[0]
  proof=_owned_zero_source(rows,base+header['ordinaryZeroFamily']['entryRva'],[ec.va(store)],'rbp',base,header['ordinaryZeroFamily'])
  initializers.append(dict(instruction=ec.site(store,base),displacement=displacement,
   entryRspOffset=displacement-header['nullFrameBytes'],zeroSource=proof))
 comparisons=[(i,row)for i,row in enumerate(path)if ec.raw(row)==bytes.fromhex('39a9e0000000')]
 need('one-actual-class-state-comparison',len(comparisons)==1);position,compare=comparisons[0]
 load=ec.last_write(path,position,'rcx');need('literal-RIP-owned-class-load',load is not None and ec.raw(load)[:3]==bytes.fromhex('488b0d'))
 usage=derive_typed_usage_context(image,ec.va(load)-base,label=LABEL+'.parentClass')
 need('actual-closed-dictionary-class-token',usage.get('tag')==1 and usage.get('typeName')==TYPE
  and bytes.fromhex(usage.get('typeRawHex',''))[10:12]==bytes((21,0)))
 edge=path[position+1];flow=control_transfer(edge)
 need('literal-selected-nonzero-class-state',flow.get('kind')=='conditional'and flow.get('conditionCode')==4
  and ec.va(path[position+2])==ec.va(edge)+len(ec.raw(edge)))
 zero=_owned_zero_source(rows,base+header['ordinaryZeroFamily']['entryRva'],[ec.va(compare)],'rbp',base,header['ordinaryZeroFamily'])
 return dict(typeName=TYPE,initializedZeroLocals=initializers,classGuard=dict(load=ec.site(load,base),typedRequest=usage,
  comparison=ec.site(compare,base),zeroSource=zero,edge=ec.site(edge,base),selectedNextInstruction=ec.site(path[position+2],base)),
  initializedClassStateObserved=False,condition='The actual typed class-state DWORD at E0 is nonzero; only the exact selected fallthrough is used. Cold initialization has no admission.')


def request_context(image,instruction_rva):
 """A separate semantic context family, never a Reader method-arg alias."""
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 u=derive_typed_usage_context(image,instruction_rva,label=LABEL);ctx=NativeReferenceContext(image);md=image.metadata
 need('actual-closed-class-only-request',u.get('tag')==6 and u.get('instructionHex','').startswith('4C8B05')
  and(u.get('typeName'),u.get('methodName'),u.get('classArguments'),u.get('methodArguments'))==
   (OWNER,'DeserializeV2',[KEY,'float'],[])and u['methodSpec'][1]>=0 and u['methodSpec'][2]==-1)
 from scripts.game_data.memorypack import scalar_param_native as scalar
 arguments=image.instantiations.resolve(u['methodSpec'][1]).arguments
 need('two-actual-closed-class-arguments',len(arguments)==2)
 scalar.ordinary(image,arguments[0].type_pointer_va,17,LABEL+'.closedKey')
 scalar.ordinary(image,arguments[1].type_pointer_va,12,LABEL+'.closedValue')
 key_raw=image.pe.bytes_at_va(arguments[0].type_pointer_va,16)
 need('exact-owned-Gait-enum-carrier',int.from_bytes(key_raw[:8],'little')==ctx.index.types[KEY].index and ctx.is_enum(KEY))
 method=md.methods[u['methodSpec'][0]];definition=ctx.index.types[OWNER];parameters=list(md.parameters_for(method))
 need('owned-static-void-two',method.declaring_type==definition.index and bool(method.flags&16)
  and ctx.type_name(method.return_type)=='void'and method.parameter_count==len(parameters)==2)
 reader_raw=image.pe.bytes_at_va(ctx.type_pointer(parameters[0].type_index),16)
 out_raw=image.pe.bytes_at_va(ctx.type_pointer(parameters[1].type_index),16)
 need('exact-Reader-byref-ABI',ctx.type_name(parameters[0].type_index)=='MemoryPack.MemoryPackReader'and reader_raw[10:12]==bytes((17,32)))
 need('exact-reference-out-byref-ABI',out_raw[10:12]==bytes((21,32)))
 output=ContextSymbols(image).type(ctx.type_pointer(parameters[1].type_index))
 need('own-open-output-class-and-VARs',output['definition']['name']==OWNER and
  [(a['parameterOwner'].get('typeIndex'),a['parameterOwner'].get('ordinal'))for a in output['classArguments']]==[(definition.index,0),(definition.index,1)])
 return dict(instructionRva=u['instructionRva'],instructionHex=u['instructionHex'],methodSpecIndex=u['methodSpecIndex'],
  methodSpec=u['methodSpec'],methodOwner=OWNER,methodName='DeserializeV2',fullTypeName=TYPE,register='r8',
  contextMode='owned-static-out-gait-dictionary',typeKind=21,typeDefinition=definition.index,typedRequest=u,
  resultAbi='void-byref-reference8',readerParameterRawHex=reader_raw.hex().upper(),outputParameterRawHex=out_raw.hex().upper())


def _context(image):
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 ctx=NativeReferenceContext(image);definition=ctx.index.types[OWNER];row=ContextSymbols(image).context(definition.index,slots=[5,21,22,23,24])
 slots={e['relativeSlot']:e for e in row['entries']}
 allocation=slots[21]['type']
 need('owned-allocation-class',allocation['definition']['name']==OWNER)
 def variables(arguments,ordinals):
  need('owned-class-parameter-identities',[(a['parameterOwner'].get('typeIndex'),a['parameterOwner'].get('ordinal'))for a in arguments]==[(definition.index,n)for n in ordinals])
 variables(allocation['classArguments'],[0,1])
 for slot,owner,name,args,ordinals in((5,'System.Collections.Generic.Dictionary`2','set_Item','classArguments',[0,1]),
   (22,OWNER,'.ctor','classArguments',[0,1]),(23,'MemoryPack.MemoryPackFormatterProvider','GetFormatter','methodArguments',[0]),
   (24,'MemoryPack.MemoryPackFormatterProvider','GetFormatter','methodArguments',[1])):
  actual=slots[slot];need('actual-owned-helper:'+str(slot),(actual['typeName'],actual['methodName'])==(owner,name));variables(actual[args],ordinals)
 return row


def derive(image,pins,*,context,source_target):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,primitive_param,buff_ec_profiles_native as ec
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 _publication_gate(image,pins);base=image.pe.image_base
 need('literal-actual-target',type(source_target)is int and source_target>base)
 fresh=request_context(image,context['instructionRva']);need('same-independently-owned-context',json.loads(json.dumps(fresh))==json.loads(json.dumps(context)))
 typed=_context(image);actual=pointer.owned(image,source_target);rows=actual['rows'];offsets=scalar.reader_offsets(image,LABEL)
 # The exact byte model below verifies every call position and every transfer.
 # Deriving its symbols from actual E8s never grants those helpers semantics.
 calls=[control_transfer(r)['target']for r in rows if ec.raw(r)[:1]==b'\xe8']
 names=['header','context','type','allocate','context','context','constructor','barrier','context','keyProvider','context',
  'valueProvider','keyDispatch','valueDispatch','context','context','setItem']
 need('bounded-actual-direct-helper-sequence',len(calls)>=len(names));symbols={}
 for name,target in zip(names,calls):
  need('same-repeated-helper:'+name,name not in symbols or symbols[name]==target);symbols[name]=target
 checked=[paths.program(actual['regions'],source_target,offsets,symbols,count=count)for count in(-1,0,1,2,3)]
 induction=prove_induction(checked[1:],initial='418bef',increment='ffc5',comparison='413bee',counter='ebp',saved_count='R14D',
  max_count=4096,mode_key='newDictionary',backedge_sites=checked[2]['backedgeSites'])
 primitive_param.object_header_source(image,vector_recorder(image)(symbols['header']-base,fragments=True),offsets)
 barrier=_barrier(image,symbols['barrier'])
 ctx=NativeReferenceContext(image);enum=ctx.index.types[KEY];fields=[f for f in image.metadata.fields_for(enum)if not ctx.field_attributes(f.type_index)&16]
 need('own-exact-Int32-enum-backing',ctx.is_enum(KEY)and len(fields)==1 and image.metadata.string(fields[0].name_index)=='value__'
  and ctx.type_name(fields[0].type_index)=='int')
 scalar.ordinary(image,ctx.type_pointer(fields[0].type_index),8,LABEL+'.key')
 helpers={name:dict(targetRva=target-base,windows=pointer.owned(image,target)['windows'],rows=pointer.owned(image,target)['rows'])
  for name,target in symbols.items()if name in('constructor','keyProvider','valueProvider','keyDispatch','valueDispatch','setItem')}
 result=dict(schema='endfield.skill-gait-dictionary-source.v1',status='validated-conditional-static-out-source',nativeInputs=dict(pins),
  typeName=TYPE,keyType=KEY,valueType='float',context=context,sourceTargetRva=source_target-base,
  readerMethodDefinition=context['methodSpec'][0],resultAbi='void-byref-reference8',referenceBytes=8,
  actualSourceProved=True,closedPointerEquivalenceProved=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
  proof=dict(context=typed,actualWindows=actual['windows'],actualSourceRegions=[[at-base,raw.hex()]for at,raw in actual['regions']],
   programs=checked,induction=induction,symbolRvas={k:v-base for k,v in symbols.items()},readerOffsets=offsets,barrier=barrier,helpers=helpers),
  evidenceBoundary=dict(exact='Own static void Reader&/reference-out& ABI and class-only MethodSpec, separately selected class-owned K/V allocation/ctor/providers/set_Item slots, complete actual null/new/positive source and EBP4096 induction, exact local/raw key/value transfer and full selected frames.',
   conditional='Initialized exact helper contexts and provider state; initially null output for non-FF; normal compatible allocation/constructor/context/provider/set_Item returns, stable disjoint buffered input and nonwrapping counters. Nominal enum and Single callback source/selection are independent.',
   unresolved=['actual key/value dispatcher callback joins','closed runtime MethodInfo/provider selection','parent reference-local/named field/full frame join']))
 _publication_gate(image,pins);return json.loads(json.dumps(result))
