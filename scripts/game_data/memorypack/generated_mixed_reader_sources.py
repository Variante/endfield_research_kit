"""Compose fresh typed hidden12 and scalar/reference generated member sources."""
from scripts.game_data.memorypack import buff_ec_profiles_native as ec
from scripts.game_data.il2cpp.initializer_control import control_transfer

LABEL='generatedMixedReader'
def need(key,condition,detail=None):
 if not condition:raise ValueError(LABEL+'.'+key+':'+str(detail)[:900])

def derive_scope(image,pins,wrapper,targets,barrier,claim,enums,method,family,windows,rows,header_proof,header):
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_action_sources as actions,generated_member_sources as members,generated_vector_member_sources as vectors
 from scripts.game_data.memorypack import generated_primitive_sources as primitives,generated_vector3_source as vector3
 from scripts.game_data.memorypack.generated_value_programs import complete_program
 from scripts.game_data.memorypack.generated_module_frame_sources import owns
 if owns(wrapper.wrapped_type)or wrapper.wrapped_type=='Beyond.Gameplay.RunePuzzleData':
  from scripts.game_data.memorypack.generated_inline_value_scope import derive_scope as inline_scope
  return inline_scope(image,pins,wrapper,targets,barrier,claim,enums,method,family,windows,rows,header_proof,header,program_prover=complete_program)
 if any(k in claim['anonymousReadOrder']for k in('value24:Beyond.Gameplay.View.CameraControlStateInitialParam','value24:Beyond.PosRot','value16:UnityEngine.Color','value16:UnityEngine.Quaternion','value16:Beyond.AABB','value12:UnityEngine.Vector3Int','value36:Beyond.Montage.AnimationClipAsyncInfo','managed:Beyond.Gameplay.BodyTypeDef')):
  from scripts.game_data.memorypack.generated_inline_value_scope import derive_scope as inline_scope
  return inline_scope(image,pins,wrapper,targets,barrier,claim,enums,method,family,windows,rows,header_proof,header,program_prover=complete_program)
 base=image.pe.image_base;offsets=ec.source_offsets(image);reader=header_proof['readerRegister'];output=header_proof['outputRegister']
 rbp_profile=header_proof.get('headerAddress')is not None and claim['anonymousReadOrder']==['value12:UnityEngine.Vector3']*3
 try:path,choices=ec.fast_path(rows,header,reader,offsets)
 except ValueError:
  from scripts.game_data.memorypack.generated_inline_value_scope import derive_scope as inline_scope
  return inline_scope(image,pins,wrapper,targets,barrier,claim,enums,method,family,windows,rows,header_proof,header,program_prover=complete_program)
 contexts,skipped=actions._contexts(image,rows)
 by_context={base+c['instructionRva']:c for c in contexts};calls=[]
 for i,row in enumerate(path):
  if control_transfer(row)['kind']!='call':continue
  rcx=ec.last_write(path,i,'rcx');rdx=ec.last_write(path,i,'rdx')
  if rcx is not None and(rcx['text']==f'mov rcx, {reader}'or(rcx['text'].startswith('lea rcx, [rsp+')or rbp_profile and rcx['text']=='lea rcx, [rbp-0x10]')and rdx is not None and rdx['text']==f'mov rdx, {reader}'):
   calls.append((i,row))
 need('one-actual-source-per-current-member',len(calls)==len(wrapper.members),(len(calls),len(wrapper.members)))
 inventory={w.name:w for w in image.memorypack_wrappers.values()};getter_cache={};setters=[members._derive_setter(image,m,inventory,barrier,getter_cache,pins=pins)for m in wrapper.members]
 events=[];requirements=[];primitive_sources={};values={};used=set();ctx=NativeReferenceContext(image)
 primitive_modes={'byte':'bool','raw-byte':'raw-byte','scalar32':'int32','scalar64':'int64','raw4':'float32','float64':'float64'}
 for n,((position,row),member,kind)in enumerate(zip(calls,wrapper.members,claim['anonymousReadOrder'],strict=True)):
  target=control_transfer(row)['target'];hidden=kind=='value12:UnityEngine.Vector3';argument=ec.last_write(path,position,'r8'if hidden else'rdx')
  context=by_context.get(ec.va(argument))if argument is not None else None
  event=dict(memberIndex=n,fieldName=member.name,declaredType=member.declared_type,kind=kind,instruction=ec.site(row,base),sourceTargetRva=target-base)
  if context is not None:
   need('exact-source-context-owner-nominal',context['methodOwner']=='MemoryPack.MemoryPackReader'and context['fullTypeName']==member.declared_type)
   event['context']=context;used.add(context['instructionRva'])
  if hidden:
   cap=vector3.derive(image,pins,context=context,source_target=target)if context is not None else vector3.derive_forwarder(image,pins,source_target=target)
   type_layout=vectors.layout(image,ctx,member.declared_type)
   need('current-source-setter-layout-join',cap['wireBytes']==setters[n]['storedBytes']==type_layout['managedBytes'])
   event.update(mode='typed-hidden-value',resultAbi='hidden-local',actualSourceProved=True,wireBytes=12)
   if context is None:event['sourceContextMode']='owned-closed-forwarder'
   values[str(n)]=dict(typeName=member.declared_type,layout=type_layout,sourceProgram=cap['proof']['actualProgram'],typedSource=cap,
    actualSourceProved=True,wireBytes=12,resultAbi='hidden-local-to-owned-field')
  elif kind=='value4:Beyond.Audio.AudioId':
   from scripts.game_data.memorypack.nominal_int32_value_sources import derive as derive_nominal4
   need('typed-nominal4-context',context is not None)
   cap=derive_nominal4(image,pins,context=context,source_target=target);need('same-nominal4-setter-width',cap['wireBytes']==setters[n]['storedBytes']==4)
   primitive_sources[str(n)]=cap;event['wireBytes']=4
  elif kind in('value4:UnityEngine.LayerMask','value4:Beyond.Gameplay.Core.GameplayTag'):
   cap=targets['value4'][member.declared_type]
   need('same-current-atomic4-request',context is not None and context['methodName']=='ReadUnmanaged'and context['typeKind']==17 and context['register']=='rdx'
       and cap['typeDefinition']==context['typeDefinition']and cap['readerMethodDefinition']==context['methodSpec'][0]and cap['targetRva']==target-base)
   need('same-current-atomic4-setter',cap['wireBytes']==setters[n]['storedBytes']==4 and cap['resultRegister']=='eax')
   primitive_sources[str(n)]=cap;event['wireBytes']=4
  elif kind in primitive_modes:
   mode=primitive_modes[kind];key=(mode,target);cache=targets['_primitiveCache']
   if key not in cache:cache[key]=primitives.derive(image,target,mode,offsets)
   primitive_sources[str(n)]=cache[key];event['wireBytes']=cache[key]['wireBytes']
   if context is not None:need('primitive-typed-ReadUnmanaged',context['methodName']=='ReadUnmanaged')
   elif ctx.is_enum(member.declared_type):raise ValueError(LABEL+'.enum-owned-context-missing:'+member.declared_type)
  elif kind=='byte-payload':need('actual-current-pool-source',target==targets['string']);event['wireBytes']=4
  elif kind.startswith('reference:'):
   need('current-ordinary-reference-context',context is not None and context['typeKind']in(18,21)and not bytes.fromhex(context['argumentRawHex'])[11]&128 and context['methodName']in('ReadValue','ReadPackable'))
   need('actual-current-reference-source',target==base+targets[context['methodName']]['targetRva'])
   requirements.append(dict(memberIndex=n,fieldName=member.name,typeName=member.declared_type,readMethod=context['methodName'],methodDefinition=context['methodSpec'][0],sourceTargetRva=target-base,context=context,positiveGrammarAdmitted=False))
  else:raise ValueError(LABEL+'.unsupported-source-kind:'+kind)
  events.append(event)
 need('every-current-context-bound',used=={c['instructionRva']for c in contexts})
 if rbp_profile:
  from scripts.game_data.memorypack.generated_rbp_vector_sources import program as rbp_program
  program=rbp_program([(base+w['startRva'],image.window_bytes(w))for w in windows],base+header_proof['memberCountInstruction'][0],
   events=events,setters=setters,header=header_proof,base=base,path=path)
 else:program=complete_program(rows,path,events,setters,contexts,reader=reader,output=output,base=base,barrier=base+barrier,disabled_collector=base+targets['_disabledCollectorFlagRva'])
 return dict(schema='endfield.generated-action-source-scope.v2',nativeInputs=dict(pins),wrapperName=wrapper.name,wrappedType=wrapper.wrapped_type,
  memberCount=len(events),claim=claim,method=method,family=family,codeWindows=windows,headerProof=header_proof,enumBackings=enums,contexts=contexts,skippedRuntimeCells=skipped,
  events=events,childRequirements=requirements,primitiveSources=primitive_sources,valueTypeSources=values,setterTransfers=[],richProgram=program,richSetters=setters,
  selectedProgram=[ec.site(r,base)for r in path],selectedConditions=[dict(instruction=ec.site(c['instruction'],base),condition=c['condition'],taken=c['taken'])for c in choices],
  sourceScopeAdmitted=True,wholeWrapperAdmitted=False,positiveGrammarAdmitted=False,
  evidenceBoundary='Complete current typed hidden12 source/local/split-store plus scalar/reference getter/setter/value-flow program, joined to independently current nominal fields and full source/setter bodies. Full initialized entry/lifecycle/frame and child grammar remain independently required.')
