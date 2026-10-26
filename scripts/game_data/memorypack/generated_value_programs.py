"""Complete selected generated record programs with explicit value sources.

This pure value-flow checker does not infer wire widths. Its caller must prove
each source and named setter, then join their exact native entries and nominal
types to the events supplied here. Every selected instruction must preserve a
known argument, source byte slice, field, reference barrier or restored frame.
"""
from __future__ import annotations
import json,re
from scripts.game_data.il2cpp.initializer_control import control_transfer,_ALIASES
from scripts.game_data.memorypack import buff_ec_profiles_native as ec

LABEL='generatedValueProgram'
VOLATILE=('rax','rcx','rdx','r8','r9','r10','r11','xmm0','xmm1','xmm2','xmm3','xmm4','xmm5')
NONVOLATILE={'rbx','rbp','rsi','rdi','r12','r13','r14','r15'}

def need(key,condition,detail=None):
 if not condition:raise ValueError(LABEL+'.'+key+':'+str(detail)[:800])

def reg(name):return _ALIASES.get(name,name)

def register_bytes(name):
 if name.startswith('xmm'):return 16
 if name in('rax','rbx','rcx','rdx','rbp','rsp','rsi','rdi')or re.fullmatch(r'r(?:[89]|1[0-5])',name):return 8
 if name.startswith('e')or name.endswith('d'):return 4
 if name.endswith('w'):return 2
 return 1

def _owned_rbp_double_move(row,frame_alias):
 """Re-decode only full scalar8 moves through the owned Trigger frame base."""
 if frame_alias is None or not row['text'].startswith('movsd ')or'[rbp'not in row['text']:return None
 from scripts.game_data.il2cpp.scalar_double_memory import decode_scalar_double_memory_move
 from scripts.game_data.memorypack.generated_module_frame_sources import PROFILE,require_descriptor
 module_frame=frame_alias.get('profile')==PROFILE
 if module_frame:require_descriptor(frame_alias)
 else:need('own-Trigger-frame-for-RBP-scalar-copy',frame_alias.get('profile')=='mission-trigger44-RAX-RBP-frame.v1'
     and frame_alias.get('baseRegister')=='rbp'and frame_alias.get('rspRelativeBaseOffset')==73)
 decoded=decode_scalar_double_memory_move(ec.raw(row),0,ec.va(row))
 need('whole-exact-RBP-scalar-copy',decoded is not None and decoded[1]==len(ec.raw(row))
     and ec.raw(decoded[0])==ec.raw(row)and decoded[0]['text']==row['text']
     and decoded[0]['memoryOperation']['address']['base']=='rbp'
     and decoded[0]['memoryOperation']['address']['index']is None)
 return decoded[0]['memoryOperation']

def _same_Query_local16_copy(row,event,setter,source,locals_,*,register,width,offset):
 """Exact whole padded Query copy back to its already-owned hidden local."""
 layout=setter.get('managedValueLayout',{});raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
 need('exact-owned-Query16-SIMD-local-copy',event.get('kind')=='managed:Beyond.Gameplay.Core.GameplayTagQuery'
     and event.get('declaredType')==layout.get('typeName')=='Beyond.Gameplay.Core.GameplayTagQuery'
     and event.get('sourceContextMode')=='owned-closed-forwarder'and event.get('context')is None
     and event.get('mode')=='typed-managed-value'and event.get('actualSourceProved')is True
     and event.get('resultAbi')=='hidden-local'and'wireBytes'not in event
     and event.get('managedBytes')==layout.get('managedBytes')==setter.get('storedBytes')==width==16
     and event.get('referenceLaneOffsets')==layout.get('referenceLaneOffsets')==[8]
     and layout.get('paddingByteRanges')==[[4,4]]and type(layout.get('typeDefinition'))is int
     and len(raw)==16 and raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==layout['typeDefinition']
     and source[:1]==('member',)and source[2:4]==(0,16)and register=='xmm0'and 32<=offset<128
     and ec.raw(row)==bytes.fromhex('f30f7f4424')+bytes((offset,))
     and[locals_.get(offset+i)for i in range(16)]==[(source[1],i)for i in range(16)],
     dict(memberIndex=source[1]if len(source)>1 else None,instruction=row.get('bytes'),
         kind=event.get('kind'),sourceContextMode=event.get('sourceContextMode'),
         managedBytes=event.get('managedBytes'),referenceLanes=layout.get('referenceLaneOffsets'),
         padding=layout.get('paddingByteRanges'),parameterTypeRecordHex=setter.get('parameterTypeRecordHex'),
         source=source,register=register,width=width,destination=offset,
         sameOwnedLocal=[locals_.get(offset+i)for i in range(16)]==[(source[1],i)for i in range(16)]))
 return True

def _same_body32_local_copy(row,event,setter,source,locals_,*,register,width,offset):
 """Preserve one exact SIMD slice of an independently owned BodyTypeDef32."""
 from scripts.game_data.memorypack.generated_body_type_field_sources import validate_event
 validate_event(event,setter)
 need('exact-owned-BodyType32-local-slice',width==16 and source[0]=='member'
     and(source[2],register)in((0,'xmm0'),(16,'xmm1'))and source[3]>=16 and 32<=offset<2**31-16)
 # Decode-free byte equality binds the one actual RSP store to its displacement;
 # this does not admit arbitrary SIMD instructions or a second nominal value.
 if offset<128:tails=[prefix+'4424'+bytes((offset,)).hex()for prefix in('0f29','0f11','f30f7f')]
 else:tails=[prefix+'8424'+offset.to_bytes(4,'little',signed=True).hex()for prefix in('0f29','0f11','f30f7f')]
 # ModRM differs by eight for XMM1.
 if register=='xmm1':tails=[
     h[:i]+bytes((int(h[i:i+2],16)+8,)).hex()+h[i+2:]
     for h in tails for i in(6 if h.startswith('f3')else 4,)]
 need('exact-owned-BodyType32-local-store-bytes',ec.raw(row).hex().lower()in tails,
     dict(instruction=row.get('bytes'),memberIndex=source[1],sourceOffset=source[2],destination=offset,register=register))
 need('no-other-member-local-overwrite',all(locals_.get(offset+i)in(None,(source[1],source[2]+i))for i in range(16)))
 return True

def complete_program(rows,path,events,setters,contexts,*,reader,output,base,barrier,inline_offsets=None,terminal_target=None,cached_accesses=None,disabled_collector=None,terminal_setter=None,static_out_parent=None,source_frame_alias=None):
 """Prove exact current count-to-RET flow, including hidden local12 values."""
 need('member-setter-bijection',0<len(events)==len(setters))
 need('explicit-exact-terminal-barrier',terminal_target is None or type(terminal_target)is int and terminal_target==barrier and terminal_target>0)
 need('explicit-exact-final-named-setter',terminal_setter is None or type(terminal_setter)is int and terminal_setter>0
     and terminal_setter==base+setters[-1]['method'][3]and terminal_target is None)
 need('explicit-disabled-collector-cell',disabled_collector is None or type(disabled_collector)is int and disabled_collector>0)
 by={ec.va(r):r for r in rows};need('unique-owned-boundaries',len(by)==len(rows))
 need('exact-owned-selected-instructions',all(ec.va(r)in by and ec.raw(r)==ec.raw(by[ec.va(r)])for r in path))
 event_by={base+e['instruction'][0]:(n,e)for n,e in enumerate(events)}
 need('unique-source-calls',len(event_by)==len(events))
 context_by={base+c['instructionRva']:c for c in contexts}
 state={reader:('reader',),output:('output',)};locals_={};stores=[set()for e in events]
 sources=[];field_stores=[];calls=[];null_exits=[];hidden=[];copies=[];inline_homes=[];cache_uses=[];collectors=[];flags=None;pending=None;at=0
 static_zeros={};static_ready=set();class_guard={};class_loads={};class_comparisons={};class_calls={};extra_static_setup=False
 if static_out_parent is not None:
  if static_out_parent.get('schema')=='endfield.animation-extra-static-out-parent.v1':
   from scripts.game_data.memorypack import animation_extra_parent_sources as extra_parent
   extra_parent.validate_setup(static_out_parent,events);extra_static_setup=True
   guards=static_out_parent['classGuards'];ready_calls=static_out_parent['classCalls']
   class_loads={base+g['load'][0]:g for g in guards+ready_calls}
   class_comparisons={base+g['comparison'][0]:g for g in guards}
   class_calls={base+g['call'][0]:g for g in ready_calls}
  else:
   from scripts.game_data.memorypack.skill_gait_dictionary_sources import TYPE
   need('finite-explicit-static-out-parent',static_out_parent.get('typeName')==TYPE
       and len([e for e in events if e.get('mode')=='typed-static-out-reference'])==3
       and len(static_out_parent.get('initializedZeroLocals',[]))==3
       and static_out_parent.get('initializedClassStateObserved')is False)
   class_guard=static_out_parent['classGuard']
   class_loads={base+class_guard['load'][0]:class_guard};class_comparisons={base+class_guard['comparison'][0]:class_guard}
  static_zeros={base+s['instruction'][0]:s for s in static_out_parent['initializedZeroLocals']}
 managed={};named24=set();named32=set();named_body32=set();named36=set();named40=set();named56=set();opaque_entity40=set();outer_raw=set()
 for n,e in enumerate(events):
  if e['kind']=='value36:Beyond.Montage.AnimationClipAsyncInfo':
   from scripts.game_data.memorypack.generated_animation_clip_field_sources import validate_event
   validate_event(e,setters[n]);named36.add(n)
  if e['kind']in('value36:Beyond.Gameplay.TrackingBounds','value44:Beyond.Gameplay.Core.TriggerShapeData'):
   from scripts.game_data.memorypack.generated_outer_value_field_sources import validate_event
   validate_event(e,setters[n]);outer_raw.add(n)
  if e['kind']=='value24:Beyond.PosRot':
   from scripts.game_data.memorypack.generated_posrot_field_sources import validate_event
   validate_event(e,setters[n])
  elif e['kind'].startswith('value24:')and e.get('mode')=='buffered-called-advance-initial24':
   from scripts.game_data.memorypack.generated_initial24_capture_sources import validate_nominal
   validate_nominal(e,setters[n])
  elif e['kind'].startswith('value24:'):
   cap=e.get('nominalHiddenSource',{});layout=setters[n].get('nominalValueLayout',{})
   need('exact-independent-named-hidden24-source',e['kind']=='value24:Beyond.Gameplay.View.CameraControlStateInitialParam'
       and e.get('declaredType')==cap.get('typeName')==layout.get('typeName')=='Beyond.Gameplay.View.CameraControlStateInitialParam'
       and e.get('actualSourceProved')is True and e.get('mode')=='typed-hidden-value'and e.get('resultAbi')=='hidden-local'
       and cap.get('schema')in('endfield.camera-initial-raw24-source.v1','endfield.camera-initial-raw24-forwarder.v1')and cap.get('status')=='validated'
       and e.get('wireBytes')==cap.get('wireBytes')==cap.get('managedBytes')==layout.get('managedBytes')==setters[n]['storedBytes']==24
       and cap.get('typeDefinition')==layout.get('typeDefinition')and type(cap.get('typeDefinition'))is int
       and cap.get('referenceLaneOffsets')==layout.get('referenceLaneOffsets')==[]
       and cap.get('paddingByteRanges')==layout.get('paddingByteRanges')==[[2,4],[9,12],[17,20]]
       and base+cap.get('targetRva',-base)==base+e.get('sourceTargetRva',-base)
       and cap.get('actualSourceProved')is True and cap.get('wrapperWireUsed')is False and cap.get('boolBytesNormalized')is False)
   from scripts.game_data.memorypack.skill_camera_initial_raw_sources import verify
   verify(cap,cap.get('nativeInputs',{}));named24.add(n)
  if e['kind'].startswith('constructed:'):
   layout=setters[n].get('constructedValueLayout',{});context=e.get('context',{});raw=bytes.fromhex(context.get('argumentRawHex',''))
   need('exact-independent-constructed-value-transfer',e['kind']=='constructed:System.Nullable`1<float>'and e.get('declaredType')=='System.Nullable`1<float>'
       and e.get('mode')=='typed-constructed-value'and e.get('resultAbi')=='rax'and e.get('actualSourceProved')is True and 'wireBytes'not in e
       and e.get('concreteTypeKind')==layout.get('concreteTypeKind')==21 and e.get('managedBytes')==layout.get('managedBytes')==setters[n]['storedBytes']==8
       and e.get('referenceLaneOffsets')==layout.get('referenceLaneOffsets')==[]and e.get('paddingByteRanges')==layout.get('paddingByteRanges')==[[1,3]]
       and layout.get('typeName')==e['declaredType']and layout.get('wireGrammarAdmitted')is False
       and context.get('typeKind')==21 and context.get('fullTypeName')==e['declaredType']and context.get('methodOwner')=='MemoryPack.MemoryPackReader'
       and context.get('methodName')=='ReadValue'and context.get('register')=='rdx'and len(raw)==16 and raw[10:12]==bytes((21,128)))
  if e['kind'].startswith('managed:'):
   layout=setters[n].get('managedValueLayout',{})
   if e['kind']=='managed:Beyond.Gameplay.Core.EntityPtr':
    from scripts.game_data.memorypack.generated_entity_ptr_field_sources import validate_event
    validate_event(e,setters[n]);opaque_entity40.add(n);managed[n]=[];continue
   need('exact-proved-nominal-managed-transfer',e.get('mode')=='typed-managed-value'and e.get('actualSourceProved')is True and
       'wireBytes'not in e and e['kind']=='managed:'+e['declaredType']and layout.get('typeName')==e['declaredType']and
       e.get('managedBytes')==layout.get('managedBytes')==setters[n]['storedBytes']and
       e.get('referenceLaneOffsets')==layout.get('referenceLaneOffsets')and
       e.get('resultAbi')in('rax','hidden-local'))
   if e['declaredType']=='Beyond.FAnimationCurve':
    from scripts.game_data.memorypack.generated_beyond_curve_field_sources import validate_event
    validate_event(e,setters[n])
   managed[n]=layout['referenceLaneOffsets']
   if layout['managedBytes']==32 and e['kind']=='managed:Beyond.Gameplay.BodyTypeDef':
    from scripts.game_data.memorypack.generated_body_type_field_sources import validate_event
    validate_event(e,setters[n]);named_body32.add(n)
   elif layout['managedBytes']==32:
    raw=bytes.fromhex(setters[n].get('parameterTypeRecordHex',''));setter=setters[n].get('program',{})
    need('exact-independent-Envelope32-transfer',e['kind']=='managed:Cinemachine.CinemachineImpulseManager+EnvelopeDefinition'
        and layout.get('typeName')=='Cinemachine.CinemachineImpulseManager+EnvelopeDefinition'
        and e.get('resultAbi')=='hidden-local'and e.get('managedBytes')==32 and layout.get('referenceLaneOffsets')==[0,8]
        and layout.get('paddingByteRanges')==[[30,32]]and type(layout.get('typeDefinition'))is int
        and len(raw)==16 and raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==layout['typeDefinition']
        and setter.get('sourceSlices')==[[0,16],[16,16]]and setter.get('barrierReferenceLaneOffset')==0
        and setter.get('wholeInputBitsStoredUnchanged')is True and setter.get('completeSourceBitsStoredUnchanged')is True
        and setter.get('normalFrameAndReturn')is True and setter.get('entryRspRestored')is True)
    named32.add(n)
   elif layout['managedBytes']==40 and e['declaredType']=='Beyond.Gameplay.Core.SkMorphPlaySetting':
    from scripts.game_data.memorypack.generated_sk_morph_field_sources import validate_event
    validate_event(e,setters[n]);named40.add(n)
   elif layout['managedBytes']==40:
    raw=bytes.fromhex(setters[n].get('parameterTypeRecordHex',''))
    need('exact-independent-SmartTarget40-transfer',e['kind']=='managed:Beyond.Gameplay.Core.SmartTargetSelectSetting'
        and layout.get('typeName')=='Beyond.Gameplay.Core.SmartTargetSelectSetting'and
        e.get('managedBytes')==40 and layout.get('referenceLaneOffsets')==[8,24,32]and layout.get('paddingByteRanges')==[[4,8],[20,24]]
        and len(raw)==16 and raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==layout.get('typeDefinition')
        and setters[n].get('program',{}).get('sourceSlices')==[[0,16],[16,16],[32,8]]
        and setters[n]['program'].get('barrierReferenceLaneOffset')==8 and setters[n]['program'].get('wholeInputBitsStoredUnchanged')is True)
    named40.add(n)
   elif layout['managedBytes']==56:
    from scripts.game_data.memorypack.generated_alpha_blend_field_sources import validate_event
    validate_event(e,setters[n]);named56.add(n)
   else:need('finite-existing-managed-domain',layout['managedBytes']in(8,16))
 rbp_origin=None
 if source_frame_alias is not None and source_frame_alias.get('profile')=='animation-upper-extra-static-frame.v1':
  need('finite-owned-UpperBody-static-frame-alias',extra_static_setup
      and static_out_parent.get('sourceFrameAlias')==source_frame_alias
      and source_frame_alias==dict(profile='animation-upper-extra-static-frame.v1',baseRegister='rbp',entryRspOffset=-24,
          currentRspBytes=72,rspRelativeBaseOffset=48,baseAliasInstruction=source_frame_alias.get('baseAliasInstruction')))
  site=source_frame_alias['baseAliasInstruction'];owned=by.get(base+site[0])
  need('actual-owned-UpperBody-frame-alias-bytes',owned is not None and ec.site(owned,base)==site and site[1]=='488BEC')
  rbp_origin=48;state['rbp']=('local',48)
 elif source_frame_alias is not None and source_frame_alias.get('profile')=='finite-module-rbp-value-locals.v1':
  from scripts.game_data.memorypack.generated_module_frame_sources import validate
  rbp_origin=validate(source_frame_alias,events,setters,rows,base);state['rbp']=('local',rbp_origin)
 elif source_frame_alias is not None:
  need('finite-owned-Trigger44-frame-alias',source_frame_alias==dict(profile='mission-trigger44-RAX-RBP-frame.v1',
      baseRegister='rbp',entryRspOffset=-95,currentRspBytes=168,rspRelativeBaseOffset=73,
      baseAliasInstruction=source_frame_alias.get('baseAliasInstruction'),entryRspAliasInstruction=source_frame_alias.get('entryRspAliasInstruction'))
      and len([e for e in events if e.get('kind')=='value44:Beyond.Gameplay.Core.TriggerShapeData'])==1)
  for key,raw in(('entryRspAliasInstruction','488BC4'),('baseAliasInstruction','488D68A1')):
   site=source_frame_alias[key];owned=by.get(base+site[0])
   need('actual-owned-Trigger-frame-alias-bytes',owned is not None and ec.site(owned,base)==site and site[1]==raw)
  rbp_origin=73;state['rbp']=('local',73)
 def reference_lanes(n):
  return managed[n]if n in managed else[0]if events[n]['kind'].startswith('reference:')or events[n]['kind']=='byte-payload'else[]
 def barrier_offsets(n):
  return[24]if n in opaque_entity40 else reference_lanes(n)
 def barrier_address():
  return pending is not None and state.get('rcx')in[('field',pending,lane)for lane in([0]if pending in named32 else[8]if pending in named_body32 else barrier_offsets(pending))]
 need('explicit-cached-access-map',cached_accesses is None or type(cached_accesses)is dict);cached_accesses=cached_accesses or{}
 def value(n,offset,width,normalized=False):return('member',n,offset,width,normalized)
 def row():need('owned-selected-boundary',at<len(path));return path[at]
 def take():
  nonlocal at
  r=row();at+=1;return r
 def clobber():
  for name in VOLATILE:state.pop(name,None)
 def branch(kind):
  r=take();f=control_transfer(r);need('owned-null-branch',f['kind']=='conditional'and f['conditionCode']in(4,5),r)
  target=f['target'];fall=ec.va(r)+len(ec.raw(r));normal=target if f['conditionCode']==5 else fall
  need('selected-exact-nonnull-edge',at<len(path)and ec.va(row())==normal)
  null=fall if f['conditionCode']==5 else target;call=by.get(null);terminal=by.get(null+5)
  need('owned-nonreturning-null-exit',call is not None and ec.raw(call)[:1]==b'\xe8'and terminal is not None and ec.raw(terminal)==b'\xcc')
  null_exits.append(ec.site(call,base))
 def store(n,offset,width,r,normalized):
  nonlocal pending
  need('source-slice-range',0<=offset<offset+width<=setters[n]['storedBytes'])
  need('field-source-order',all(stores[i]==set(range(setters[i]['storedBytes']))for i in range(n)))
  span=set(range(offset,offset+width));need('field-bytes-stored-once',not stores[n]&span)
  if events[n]['kind']=='byte':need('normalized-bool-source',normalized)
  stores[n].update(span);field_stores.append(dict(memberIndex=n,instruction=ec.site(r,base),sourceOffset=offset,storedBytes=width))
  if n in outer_raw:
   transfer=control_transfer(r);full=setters[n]['storedBytes']
   slices=((0,16),(16,16),(32,4))if full==36 else((0,16),(16,16),(32,8),(40,4))
   need('exact-nominal-outer-raw-destination-slices',(offset,width)in slices
       or(offset,width)==(0,full)and transfer['kind']=='call'and transfer['target']==base+setters[n]['method'][3])
  if n in named36:
   transfer=control_transfer(r)
   need('exact-Clip36-destination-slices',(offset,width)in((0,16),(16,16),(32,4))
       or(offset,width)==(0,36)and transfer['kind']=='call'and transfer['target']==base+setters[n]['method'][3])
  if reference_lanes(n)or n in opaque_entity40:
   if n in opaque_entity40:
    from scripts.game_data.memorypack.generated_entity_ptr_field_sources import validate_destination
    validate_destination(offset,width,r,setters[n],base=base,pending=pending)
    if stores[n]==set(range(40)):pending=n
   elif n in named_body32:
    transfer=control_transfer(r)
    need('exact-Body32-destination-slices',pending is None and((offset,width)in((0,16),(16,16))
        or(offset,width)==(0,32)and transfer['kind']=='call'and transfer['target']==base+setters[n]['method'][3]),
        dict(offset=offset,width=width,instruction=ec.site(r,base),setter=setters[n]['method']))
    if stores[n]==set(range(32)):pending=n
   elif n in named32:
    need('exact-Envelope32-destination-slices',(offset,width)in((0,16),(16,16))and pending is None)
    if stores[n]==set(range(32)):pending=n
   elif n in named40:
    need('exact-SmartTarget40-destination-slices',(offset,width)in((0,16),(16,16),(32,8))and pending is None)
    if stores[n]==set(range(40)):pending=n
   elif n in named56:
    own_call=control_transfer(r)
    need('exact-Alpha56-destination-slices',pending is None and((offset,width)in((0,16),(16,16),(32,16),(48,8))
        or(offset,width)==(0,56)and own_call['kind']=='call'and own_call['target']==base+setters[n]['method'][3]))
    if stores[n]==set(range(56)):pending=n
   else:
    need('whole-reference-field-store',offset==0 and width==(setters[n]['storedBytes']if n in managed else 8)and pending is None);pending=n
 # Matching byte member count is the only selected count branch.
 r=take();need('actual-current-member-count',r['text'].startswith('cmp ')and ec.raw(r)[-1]==len(events))
 edge=take();flow=control_transfer(edge);need('matching-count-branch',flow['kind']=='conditional'and flow['conditionCode']in(4,5))
 need('matching-count-edge',at<len(path)and ec.va(row())==(flow['target']if flow['conditionCode']==4 else ec.va(edge)+len(ec.raw(edge))))
 while at<len(path):
  r=row();address=ec.va(r);text=r['text'];f=control_transfer(r)
  if address in class_loads:
   class_guard=class_loads[address]
   usage=class_guard['typedRequest'];need('actual-static-parent-class-load',ec.site(r,base)==class_guard['load']
       and usage.get('tag')==1 and usage.get('instructionRva')==class_guard['load'][0]and usage.get('instructionHex')==class_guard['load'][1]
       and ec.raw(r)[:3]==bytes.fromhex('488b0d'))
   state['rcx']=('class-state',class_guard['load'][0]);take();continue
  if address in static_zeros:
   item=static_zeros[address];proof=item.get('zeroSource',{});start=item['displacement']
   if extra_static_setup:
    extra_parent.validate_zero(r,item,base)
    need('actual-extra-static-local-no-live-overlap',not any(start<=p<start+8 for p in locals_))
   else:
    need('actual-static-output-reference-null-reset',ec.site(r,base)==item['instruction']and ec.raw(r)==bytes.fromhex('48896c24')+bytes((start,))
        and proof.get('register')=='rbp'and proof.get('value')==0 and proof.get('zeroOnEveryOrdinaryPath')is True and address in proof.get('sites',[])
        and not any(start<=p<start+8 for p in locals_))
   static_ready.add(start);take();continue
  if address in class_calls:
   selected=class_calls[address];program=selected['program']
   need('exact-owned-ready-class-call',ec.site(r,base)==selected['call']and f['kind']=='call'
       and f['target']==base+selected['targetRva']and state.get('rcx')==('class-state',selected['load'][0])
       and program.get('calleeCalls')==0 and program.get('argumentRegistersUnchanged')is True)
   take();calls.append(ec.site(r,base));clobber();flags=None;continue
  if address in class_comparisons:
   class_guard=class_comparisons[address]
   proof=class_guard['zeroSource'];need('actual-static-parent-nonzero-state-condition',state.get('rcx')==('class-state',class_guard['load'][0])
       and ec.site(r,base)==class_guard['comparison']and ec.raw(r)==bytes.fromhex('39a9e0000000')
       and proof.get('register')=='rbp'and proof.get('value')==0 and proof.get('zeroOnEveryOrdinaryPath')is True and address in proof.get('sites',[]))
   take();edge=take();flow=control_transfer(edge);need('actual-static-parent-selected-class-edge',ec.site(edge,base)==class_guard['edge']
       and flow.get('kind')=='conditional'and flow.get('conditionCode')==4 and at<len(path)
       and ec.va(row())==ec.va(edge)+len(ec.raw(edge))and ec.site(row(),base)==class_guard['selectedNextInstruction'])
   state.pop('rcx',None);flags=None;continue
  compare=r.get('memoryImmediateComparisonOperation',{})
  if address not in cached_accesses and compare and compare.get('sourceAddress',{}).get('ripRelative'):
   raw=ec.raw(r);cell=address+7+int.from_bytes(raw[2:6],'little',signed=True)if len(raw)==7 else None
   need('exact-current-disabled-collector-comparison',disabled_collector is not None and len(raw)==7 and raw[:2]==b'\x83\x3d'and raw[-1]==0
       and cell==disabled_collector==compare['sourceAddress'].get('absoluteAddress')and compare.get('bits')==32
       and compare.get('immediateValue')==0 and compare.get('writesMemory')is False and pending is None,r)
   take();written=row();move=written.get('memoryOperation',{});a=move.get('address',{});source=state.get(reg(move.get('register','')))
   need('disabled-comparison-followed-by-whole-reference-store',move.get('direction')=='store'and move.get('memoryBytes')==8 and move.get('writesFlags')is False
       and not a.get('ripRelative')and a.get('index')is None and state.get(a.get('base'))==('original',)
       and source is not None and source[:1]==('member',)and source[2:4]==(0,8),written)
   n=source[1];need('same-owned-reference-field-before-disabled-edge',reference_lanes(n)==[0]and setters[n]['storedBytes']==8
       and a.get('displacement',0)==setters[n]['fieldOffset'])
   store(n,0,8,written,source[4]);take();edge=take();flow=control_transfer(edge)
   need('exact-selected-disabled-collector-edge',flow['kind']=='conditional'and flow['conditionCode']==4 and at<len(path)
       and flow['target']==ec.va(row())and pending==n,edge)
   collectors.append(dict(memberIndex=n,disabledFlagRva=disabled_collector-base,comparison=ec.site(r,base),fieldStore=ec.site(written,base),disabledEdge=ec.site(edge,base),
       enabledCollectorPathAdmitted=False,condition='The independently proved current collector cell is zero; the exact whole reference store preserves comparison flags before JE.'))
   pending=None;flags=None;continue
  if address in cached_accesses:
   from scripts.game_data.memorypack.generated_cached_access_sources import coherent_access
   from scripts.game_data.memorypack.generated_vector_member_sources import selected_rows
   access=cached_accesses[address];p=access['program'];n=access['memberIndex']
   need('exact-current-getter-access-order',n==len(sources)-1 and pending is None and not stores[n]
       and state.get(p['wrapperRegister'])==('wrapper',))
   getter=setters[n].get('getter');need('same-current-owned-getter-cache',getter is not None and getter['method']==access['getterMethod']
       and getter['baseHolder']==access['baseHolder']and getter['typedCache']==access['typedCache'])
   actual=coherent_access([(ec.va(q),ec.raw(q))for q in rows],address,wrapper=p['wrapperRegister'],base_slot=p['baseHolderOffset'],cache_slot=p['typedCacheOffset'])
   part=selected_rows(rows,actual['selectedBytes']);need('same-full-cached-access-program',json.dumps(actual,sort_keys=True)==json.dumps(p,sort_keys=True)and path[at:at+len(part)]==part)
   need('same-current-native-metadata-shortcut',access.get('metadata',{}).get('status')=='validated'and access['metadata']['compareRva']==address-base
       and json.dumps(access['metadata']['program'],sort_keys=True)==json.dumps(p['metadataShortcut'],sort_keys=True))
   state['rax']=('original',);state[p['resultRegister']]=('original',);at+=len(part);flags=None
   cache_uses.append(dict(memberIndex=n,program=p,getterMethod=getter['method'],metadata=access['metadata']));continue
  if address in event_by:
   n,e=event_by[address];need('source-call-order',n==len(sources)and pending is None)
   if e.get('mode')in('buffered-inline-value','buffered-inline-scalar','buffered-called-advance-scalar','buffered-called-advance-color16','buffered-called-advance-value12','buffered-called-advance-int-vector12','buffered-called-advance-initial24','buffered-called-advance-clip36','buffered-called-advance-posrot24'):
    from scripts.game_data.memorypack import generated_inline_value_sources as inline
    need('independent-inline-offsets',inline_offsets is not None)
    parsed=inline.guarded_program([(ec.va(q),ec.raw(q))for q in rows],address,inline_offsets,reader=reader,output=output)
    selected=inline.selected_rows(rows,parsed)
    need('same-complete-inline-macro',json.dumps(parsed,sort_keys=True)==json.dumps(e.get('inlineSourceProgram'),sort_keys=True)and path[at:at+len(selected)]==selected)
    width=setters[n]['storedBytes'];need('same-inline-source-setter-width',e.get('wireBytes')==width==parsed['wireBytes'])
    if parsed.get('independentAdvanceSourceRequired'):
     cap=e.get('inlineAdvanceSource',{})
     color=e.get('mode')=='buffered-called-advance-color16'
     vector=e.get('mode')=='buffered-called-advance-value12'
     integer_vector=e.get('mode')=='buffered-called-advance-int-vector12'
     initial24=e.get('mode')=='buffered-called-advance-initial24'
     clip36=e.get('mode')=='buffered-called-advance-clip36'
     posrot24=e.get('mode')=='buffered-called-advance-posrot24'
     if posrot24:
      from scripts.game_data.memorypack.generated_posrot_field_sources import validate_event
      validate_event(e,setters[n])
      need('independent-exact-PosRot24-capture',reader=='rbx'and output=='rdi'
          and parsed.get('actualReaderArgument')==reader and parsed.get('actualSignedCountArgument')==width==24
          and parsed.get('sourceLocalValues')==[]and parsed.get('preservedCaptureRegistersRequired')==['xmm6','xmm7'])
     if clip36:
      from scripts.game_data.memorypack.generated_animation_clip_field_sources import validate_event
      validate_event(e,setters[n])
      need('independent-exact-inline36-capture',reader=='rbx'and output=='rdi'
          and parsed.get('actualReaderArgument')==reader and parsed.get('actualSignedCountArgument')==width==36
          and parsed.get('sourceLocalValues')==[]and parsed.get('preservedCaptureRegistersRequired')==['xmm6','rbp','xmm7'])
     if initial24:
      from scripts.game_data.memorypack.generated_initial24_capture_sources import validate_nominal
      validate_nominal(e,setters[n])
      need('independent-exact-inline24-capture',parsed.get('preservedCaptureRegistersRequired')==['xmm6','xmm7']
          and [(c['register'],c['sourceOffset'],c['bytes'])for c in parsed['capturedSourceSlices']]==[('xmm6',0,16),('xmm7',16,8)]
          and parsed.get('sourceLocalValues')==[]and parsed.get('actualReaderArgument')==reader=='rdi'and output=='rbx'
          and parsed.get('actualSignedCountArgument')==width==24 and parsed.get('boolBytesNormalized')is False
          and parsed.get('paddingBytesCopied')is True and parsed.get('typedReadUnmanagedClaimed')is False)
     if color:
      layout=e.get('inlineNominalLayout',{});raw=bytes.fromhex(setters[n].get('parameterTypeRecordHex',''))
      need('independent-exact-Color-layout-and-before-call-spill',e['kind']=='value16:UnityEngine.Color'and e.get('declaredType')==layout.get('typeName')=='UnityEngine.Color'
          and layout==setters[n].get('nominalValueLayout')and layout.get('managedBytes')==width==16
          and layout.get('referenceLaneOffsets')==layout.get('paddingByteRanges')==[]and len(raw)==16 and raw[10:12]==bytes((17,128))
          and int.from_bytes(raw[:8],'little')==layout.get('typeDefinition')and parsed.get('completeSourceBitsSpilledBeforeAdvance')is True
          and parsed.get('sourceLocalValues')and parsed.get('actualSignedCountArgument')==16)
     if vector:
      layout=e.get('inlineNominalLayout',{});raw=bytes.fromhex(setters[n].get('parameterTypeRecordHex',''))
      high='rsi'if(reader,output)==('rdi','r14')else'r14'
      need('independent-exact-called-Vector3-capture',e['kind']=='value12:UnityEngine.Vector3'and e.get('declaredType')==layout.get('typeName')=='UnityEngine.Vector3'
          and layout.get('managedBytes')==width==12 and len(raw)==16 and raw[10:12]==bytes((17,128))
          and int.from_bytes(raw[:8],'little')==layout.get('typeDefinition')and parsed.get('preservedCaptureRegistersRequired')==['xmm6',high]
          and [(c['register'],c['sourceOffset'],c['bytes'])for c in parsed['capturedSourceSlices']]==[('xmm6',0,8),(high,8,4)]
          and parsed.get('actualSignedCountArgument')==12,
          dict(memberIndex=n,reader=reader,output=output,expectedHighRegister=high,
              actualCapturedSourceSlices=parsed.get('capturedSourceSlices'),nominalType=e.get('declaredType')))
     if integer_vector:
      layout=e.get('inlineNominalLayout',{});raw=bytes.fromhex(setters[n].get('parameterTypeRecordHex',''));setter=setters[n].get('program',{})
      high_register=parsed.get('preservedCaptureRegistersRequired',[None])[0]
      wrapper_register=parsed.get('wrapperLoad',{}).get('register')
      need('independent-exact-called-Int3-capture',e['kind']=='value12:UnityEngine.Vector3Int'and e.get('declaredType')==layout.get('typeName')=='UnityEngine.Vector3Int'
          and layout==setters[n].get('nominalValueLayout')and layout.get('schema')=='endfield.story-integer-vector-layout.v1'
          and layout.get('managedBytes')==width==12 and layout.get('referenceLaneOffsets')==layout.get('paddingByteRanges')==[]
          and[(f.get('name'),f.get('declaredType'),f.get('managedOffset'),f.get('rawKind'))for f in layout.get('fields',[])]==
              [('m_X','int',0,8),('m_Y','int',4,8),('m_Z','int',8,8)]
          and len(raw)==16 and raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==layout.get('typeDefinition')
          and setter.get('sourceSlices')==[[0,8],[8,4]]and setter.get('completeSourceBitsStoredUnchanged')is True
          and setter.get('normalFrameAndReturn')is True and high_register in('rbp','rsi')and parsed.get('preservedCaptureRegistersRequired')==[high_register]
          and(wrapper_register,high_register)in(('rsi','rbp'),('rdi','rsi'))
          and(wrapper_register!=output or n==len(events)-1)
          and [(c['register'],c['sourceOffset'],c['bytes'])for c in parsed['capturedSourceSlices']]==[('xmm0',0,8),(high_register,8,4)]
          and parsed.get('completeLowEightSpilledBeforeAdvance')is True and parsed.get('actualSignedCountArgument')==12)
     need('independent-complete-actual-Advance-source',(e.get('mode')=='buffered-called-advance-scalar'or color or vector or integer_vector or initial24 or clip36 or posrot24)and e.get('actualSourceProved')is True
         and cap.get('targetRva',-base)+base==parsed['advanceTargetVa']and cap.get('completeAdvanceProgramProved')is True
         and cap.get('allFourReaderUpdatesProved')is True and cap.get('entryRspRestored')is True and cap.get('allNonvolatilesRestored')is True
         and cap.get('codeWindows')and all(cap.get('readerOffsets',{}).get(k)==v for k,v in parsed['readerOffsets'].items()))
     clobber()
    else:
     need('complete-inline-four-counter-program',parsed.get('allFourReaderUpdatesProved')is True)
     state['rax']=('inline-source-pointer',);state[parsed['remainingRegister']]=('remaining',)
    if parsed['wrapperLoad']is not None:state[parsed['wrapperLoad']['register']]=('wrapper',)
    for captured in parsed['capturedSourceSlices']:
     state[captured['register']]=value(n,captured['sourceOffset'],captured['bytes'])
    for local in parsed['sourceLocalValues']:
     source=state.get(local['register']);start=local['displacement'];size=local['bytes']
     need('exact-inline-captured-spill',source is not None and source[:4]==('member',n,local['sourceOffset'],size))
     for position,(owner,_)in list(locals_.items()):
      if stores[owner]==set(range(setters[owner]['storedBytes'])):del locals_[position]
     need('inline-spill-no-live-overlap',not any(start<=p<start+size for p in locals_))
     for i in range(size):locals_[start+i]=(n,local['sourceOffset']+i)
     home=dict(displacement=start,bytes=size,storeInstruction=ec.site(by[local['storeInstructionVa']],base),memberIndex=n,fieldBytes=setters[n]['storedBytes'])
     if e.get('mode')=='buffered-called-advance-int-vector12':
      home.update(nominalTypeName=e['declaredType'],nominalTypeDefinition=setters[n]['nominalValueLayout']['typeDefinition'])
     inline_homes.append(home)
    if parsed.get('completeSourceBitsSpilledBeforeAdvance'):
     for captured in parsed['capturedSourceSlices']:state.pop(captured['register'],None)
    if parsed.get('completeLowEightSpilledBeforeAdvance'):
     need('only-current-Int3-low-spill-and-preserved-high',e.get('mode')=='buffered-called-advance-int-vector12'
         and parsed['sourceLocalValues'][0]['register']=='xmm0'and parsed['sourceLocalValues'][0]['bytes']==8
         and state.get(parsed['preservedCaptureRegistersRequired'][0])==value(n,8,4))
     state.pop('xmm0',None)
    at+=len(selected);source=dict(memberIndex=n,instruction=e['instruction'],mode=e['mode'],wireBytes=width,program=parsed)
    if parsed.get('independentAdvanceSourceRequired'):source['actualAdvanceSource']=e['inlineAdvanceSource']
    sources.append(source);flags=None;continue
   if e.get('kind')=='value8:UnityEngine.Vector2Int'or e.get('mode')=='typed-register-integer-vector':
    from scripts.game_data.memorypack.generated_int2_member_sources import validate_event
    validate_event(e,setters[n])
   need('actual-proved-source-entry',f['kind']=='call'and f['target']==base+e['sourceTargetRva'])
   abi=e.get('resultAbi','xmm0'if e['kind']in('raw4','float64')else'rax')
   width=setters[n]['storedBytes'];context=e.get('context')
   if abi=='out-reference-local':
    from scripts.game_data.memorypack import animation_extra_dictionary_sources as extra_static
    if e.get('declaredType')in extra_static.TYPES:validate_event=extra_static.validate_event
    else:
     from scripts.game_data.memorypack.skill_gait_dictionary_sources import validate_event
    validate_event(e,setters[n])
    need('same-static-reference-reader-and-context',state.get('rcx')==('reader',)
        and state.get('r8')==('context',context['instructionRva']))
    target=state.get('rdx');need('static-reference-owned-output-local',target is not None and target[0]=='local'and 32<=target[1]<128)
    start=target[1]
    need('actual-static-reference-local-initially-null',start in static_ready);static_ready.remove(start)
    need('static-reference-local-no-live-overlap',not any(start<=p<start+8 for p in locals_))
    for offset in range(8):locals_[start+offset]=(n,offset)
    hidden.append(dict(memberIndex=n,displacement=start,bytes=8,sourceInstruction=ec.site(r,base),
        sourceAbi='void-byref-reference8',nominalTypeName=e['declaredType'],nominalTypeDefinition=context['typeDefinition'],
        initiallyZeroLocalRequired=True))
    if len(target)>2:hidden[-1]['frameAddress']=target[2]
    clobber()
   elif abi=='hidden-local':
    need('finite-proved-hidden-result',(width in(12,16)or width==24 and n in named24 or width==32 and n in(named32|named_body32)or width==36 and n in named36 or n in outer_raw and width in(36,44)or width==40 and n in(named40|opaque_entity40)or width==56 and n in named56)and e.get('actualSourceProved')is True)
    target=state.get('rcx');need('hidden-output-owned-frame-local',target is not None and target[0]=='local'and 32<=target[1]<256)
    need('same-hidden-reader-context',state.get('rdx')==('reader',)and(context is not None and state.get('r8')==('context',context['instructionRva'])or context is None and e.get('sourceContextMode')=='owned-closed-forwarder'))
    start=target[1]
    # The same compiler temporary can be reused only after every old byte
    # has reached its independently named destination field.
    for position,(owner,_)in list(locals_.items()):
     if stores[owner]==set(range(setters[owner]['storedBytes'])):del locals_[position]
    need('hidden-local-no-live-overlap',not any(start<=p<start+width for p in locals_))
    for offset in range(width):locals_[start+offset]=(n,offset)
    local=dict(memberIndex=n,displacement=start,bytes=width,sourceInstruction=ec.site(r,base))
    if n in named24 or n in named32 or n in named_body32 or n in named36 or n in named40 or n in named56 or n in opaque_entity40 or n in outer_raw:local.update(nominalTypeName=events[n]['declaredType'],nominalTypeDefinition=setters[n]['managedValueLayout'if n in named32 or n in named_body32 or n in named40 or n in named56 or n in opaque_entity40 else'nominalValueLayout']['typeDefinition'])
    elif e['kind']=='managed:Beyond.Gameplay.Core.GameplayTagQuery'and e.get('sourceContextMode')=='owned-closed-forwarder':
     local.update(nominalTypeName=e['declaredType'],nominalTypeDefinition=setters[n]['managedValueLayout']['typeDefinition'])
    elif e['kind']=='value16:UnityEngine.Quaternion'and e.get('sourceContextMode')=='owned-closed-forwarder':
     local.update(nominalTypeName=e['declaredType'],nominalTypeDefinition=e['nominalValueLayout']['typeDefinition'])
    elif e['kind']=='value16:Beyond.AABB':
     from scripts.game_data.memorypack.generated_aabb_field_sources import owns_member
     need('exact-own-AABB-hidden-local',owns_member(setters[n]['targetField'].rpartition('::')[0],e['fieldName'],e['declaredType']))
     local.update(nominalTypeName=e['declaredType'],nominalTypeDefinition=e['nominalValueLayout']['typeDefinition'])
    if n in opaque_entity40:local.update(opaqueRuntimeStorageRanges=[[24,40]],selectedBarrierValueOffsets=[24],runtimeReferenceLayoutAdmitted=False,completeRuntimePaddingMapAdmitted=False)
    if len(target)>2:
     if source_frame_alias is not None and source_frame_alias.get('profile')=='finite-module-rbp-value-locals.v1':
      from scripts.game_data.memorypack.generated_module_frame_sources import require_hidden
      require_hidden(source_frame_alias,n,e['declaredType'],width,target[1])
     else:need('finite-owned-RBP-hidden-local',source_frame_alias is not None and(target[1],width,e['declaredType'])in
         ((64,44,'Beyond.Gameplay.Core.TriggerShapeData'),(48,12,'UnityEngine.Vector3')))
     raw=bytes.fromhex(setters[n]['parameterTypeRecordHex'])
     need('own-RBP-hidden-ordinary-value-parameter',len(raw)==16 and raw[10:12]==bytes((17,128)))
     local.update(frameAddress=target[2],nominalTypeName=e['declaredType'],nominalTypeDefinition=int.from_bytes(raw[:8],'little'))
    hidden.append(local)
    clobber();state['rax']=target
   else:
    need('same-direct-reader',state.get('rcx')==('reader',))
    if context is not None:need('same-direct-typed-context',state.get('rdx')==('context',context['instructionRva']))
    need('finite-proved-return-ABI',abi in('rax','xmm0')and width in(1,4,8))
    clobber();state[abi]=value(n,0,width,e['kind']=='byte')
   take();calls.append(ec.site(r,base));sources.append(dict(memberIndex=n,instruction=ec.site(r,base),resultAbi=abi));flags=None;continue
  if address in context_by:
   c=context_by[address];need('same-current-context-load',ec.site(r,base)==[c['instructionRva'],c['instructionHex']])
   state[reg(c['register'])]=('context',c['instructionRva']);take();continue
  if f['kind']=='conditional':
   need('known-null-flags',flags=='nonnull');branch(flags);flags=None;continue
  setter_tail=f['kind']=='jump'and terminal_setter is not None and f['target']==terminal_setter
  if f['kind']=='jump'and not setter_tail:
   if terminal_target is not None and f['target']==terminal_target:
    need('terminal-barrier-complete-reference-address',at==len(path)-1 and barrier_address())
    take();calls.append(ec.site(r,base));pending=None;continue
   take();need('owned-selected-jump',at<len(path)and f['target']==ec.va(row()));continue
  if f['kind']=='return':need('final-full-return',at==len(path)-1 and pending is None);take();continue
  if f['kind']=='call'or setter_tail:
   if f['target']==barrier:
    need('barrier-owns-actual-reference-field',barrier_address())
    pending=None;calls.append(ec.site(r,base));clobber();take();flags=None;continue
   selected=[(n,s)for n,s in enumerate(setters)if f['target']==base+s['method'][3]]
   if len(selected)==1:
    n,s=selected[0];need('named-setter-owned-wrapper',state.get('rcx')==('wrapper',)and state.get('r8')==('zero',))
    if setter_tail:need('final-named-setter-after-all-sources',at==len(path)-1 and n==len(events)-1 and len(sources)==len(events)and pending is None)
    argument=state.get('xmm1'if events[n]['kind']in('raw4','float64')else'rdx')
    if events[n].get('resultAbi')=='hidden-local':
     need('whole-hidden-named-setter-source',argument is not None and argument[0]=='local'and[locals_.get(argument[1]+i)for i in range(s['storedBytes'])]==[(n,i)for i in range(s['storedBytes'])]);normalized=False
    else:
     need('whole-named-setter-source',argument is not None and argument[:4]==('member',n,0,s['storedBytes']));normalized=argument[4]
    store(n,0,s['storedBytes'],r,normalized);pending=None;calls.append(ec.site(r,base));clobber();take();flags=None;continue
   need('terminal-named-setter-not-getter',not setter_tail)
   getters=[s['getter']for s in setters if s.get('getter')and f['target']==base+s['getter']['method'][3]]
   need('owned-current-compatible-getter',bool(getters)and state.get('rcx')==('wrapper',)and state.get('rdx')==('zero',))
   calls.append(ec.site(r,base));clobber();state['rax']=('original',);take();flags=None;continue
  need('ordinary-instruction-flow',f['kind']=='next',r)
  m=re.fullmatch(r'test (\w+), \1',text)
  if m:
   v=state.get(reg(m[1]));need('known-null-test',v is not None and v[0]in('wrapper','original'))
   flags='nonnull';take();continue
  m=re.fullmatch(r'xor (edx|r8d), \1',text)
  if m:state[reg(m[1])]=('zero',);take();continue
  m=re.fullmatch(r'lea (rcx|rdx), \[rsp\+0x([0-9a-f]+)\]',text)
  if m:state[m[1]]=('local',int(m[2],16));take();continue
  m=re.fullmatch(r'lea (rcx|rdx), \[rbp([+-])0x([0-9a-f]+)\]',text)
  if m:
   displacement=int(m[3],16)*(1 if m[2]=='+'else-1)
   module_frame=source_frame_alias is not None and source_frame_alias.get('profile')=='finite-module-rbp-value-locals.v1'
   if module_frame:
    from scripts.game_data.memorypack.generated_module_frame_sources import source_addresses
    allowed_addresses=source_addresses(source_frame_alias)
   else:allowed_addresses=(('rdx',56),('rdx',-16),('rdx',-8))if rbp_origin==48 else(('rcx',-9),('rcx',-25),('rdx',39),('rdx',-41))
   need('finite-owned-RBP-value-address',source_frame_alias is not None and state.get('rbp')==('local',rbp_origin)
       and(m[1],displacement)in allowed_addresses)
   state[m[1]]=('local',rbp_origin+displacement,dict(baseRegister='rbp',displacement=displacement,rspDisplacement=rbp_origin+displacement));take();continue
  m=re.fullmatch(r'lea r11, \[rsp\+0x([0-9a-f]+)\]',text)
  if m:
   need('restoration-alias-only-after-complete-fields',pending is None and len(sources)==len(events)and all(got==set(range(s['storedBytes']))for got,s in zip(stores,setters)))
   state['r11']=('frame',int(m[1],16));take();continue
  m=re.fullmatch(r'lea rcx, \[(rax|rcx)\+0x([0-9a-f]+)\]',text)
  if m:
   candidates=[(n,lane)for n,s in enumerate(setters)for lane in barrier_offsets(n)if s['fieldOffset']+lane==int(m[2],16)and(pending==n or not stores[n])]
   need('reference-address-owned-named-field',len(candidates)==1 and state.get(m[1])==('original',))
   state['rcx']=('field',*candidates[0]);take();continue
  m=re.fullmatch(r'add rcx, 0x([0-9a-f]+)',text)
  # SUB imm8 sign-extends -128: this exact spelling forms Original+128.
  # It is only a pending whole owned reference's actual barrier address.
  plus128=text=='sub rcx, -0x80'and ec.raw(r)==bytes.fromhex('4883e980')
  if m or plus128:
   need('reference-address-after-owned-store',pending is not None and state.get('rcx')==('original',))
   offset=128 if plus128 else int(m[1],16)
   lane=offset-setters[pending]['fieldOffset'];need('reference-address-actual-managed-lane',lane in barrier_offsets(pending))
   state['rcx']=('field',pending,lane);take();continue
  # Exact scalar SSE loads/stores preserve the lower4/8 captured bytes.
  m=re.fullmatch(r'(movss|movsd) (xmm\d+), \[(rsp|rax)(?:\+0x([0-9a-f]+))?\]',text)
  if m:
   width=4 if m[1]=='movss'else 8;pointer=state.get(m[3])if m[3]!='rsp'else('local',0)
   need('known-hidden-local-pointer',pointer is not None and pointer[0]=='local')
   start=pointer[1]+int(m[4]or'0',16);parts=[locals_.get(start+i)for i in range(width)]
   need('whole-hidden-source-local-load',parts[0]is not None and parts==[(parts[0][0],parts[0][1]+i)for i in range(width)])
   state[m[2]]=value(parts[0][0],parts[0][1],width);take();continue
  m=re.fullmatch(r'(movss|movsd) \[rsp\+0x([0-9a-f]+)\], (xmm\d+)',text)
  if m:
   width=4 if m[1]=='movss'else 8;start=int(m[2],16);v=state.get(m[3]);need('exact-hidden-local-copy',v is not None and v[0]=='member'and v[3]>=width and events[v[1]].get('resultAbi')=='hidden-local'and start>=32)
   for i in range(width):locals_[start+i]=(v[1],v[2]+i)
   copy=dict(displacement=start,bytes=width,storeInstruction=ec.site(r,base),memberIndex=v[1])
   if v[1]in named24:copy.update(nominalTypeName=events[v[1]]['declaredType'],nominalTypeDefinition=setters[v[1]]['nominalValueLayout']['typeDefinition'],sourceOffset=v[2])
   elif v[1]in named56:
    need('exact-Alpha56-tail-local-copy',(width,v[2],m[3])==(8,48,'xmm1'))
    copy.update(nominalTypeName=events[v[1]]['declaredType'],nominalTypeDefinition=setters[v[1]]['managedValueLayout']['typeDefinition'],sourceOffset=v[2],sourceRegister=m[3])
   copies.append(copy);take();continue
  m=re.fullmatch(r'(movss|movsd) \[(rax|rcx)\+0x([0-9a-f]+)\], (xmm\d+)',text)
  if m:
   width=4 if m[1]=='movss'else 8;v=state.get(m[4]);need('owned-floating-field-source',v is not None and v[0]=='member'and v[3]>=width and state.get(m[2])==('original',))
   need('exact-named-floating-field',int(m[3],16)==setters[v[1]]['fieldOffset']+v[2]);store(v[1],v[2],width,r,v[4]);take();continue
  m=re.fullmatch(r'movaps (xmm\d+), (xmm\d+)',text)
  if m:
   need('known-floating-transfer',m[2]in state);state[m[1]]=state[m[2]];take();continue
  m=re.fullmatch(r'movaps (xmm(?:[6-9]|1[0-5])), \[rsp\+0x([0-9a-f]+)\]',text)
  if m:
   # Exact home and incoming bits are independently owned by frame_program.
   state[m[1]]=('restored',m[1]);take();continue
  move=r.get('memoryOperation',{})or _owned_rbp_double_move(r,source_frame_alias)or{};a=move.get('address',{})
  if move:
   need('ordinary-memory-address',a.get('index')is None and not a.get('ripRelative'),r)
   operand=a.get('base');offset=a.get('displacement',0);register=reg(move['register']);width=move['memoryBytes'];v=state.get(operand)
   if move['direction']=='load':
    if v==('output',)and offset==0 and width==8:state[register]=('wrapper',)
    elif v==('wrapper',)and offset==16 and width==8:state[register]=('original',)
    elif(operand=='rsp'or v is not None and v[0]=='local')and(offset if operand=='rsp'else v[1]+offset)in locals_:
     start=offset if operand=='rsp'else v[1]+offset;parts=[locals_.get(start+i)for i in range(width)];need('whole-hidden-local-load',parts[0]is not None and parts==[(parts[0][0],parts[0][1]+i)for i in range(width)])
     state[register]=value(parts[0][0],parts[0][1],width)
    elif(operand=='rsp'or v is not None and v[0]=='frame')and register in NONVOLATILE and width==8:state[register]=('restored',register)
    else:raise ValueError(LABEL+'.unowned-memory-load:'+str((r,v)))
   elif operand=='rsp'or source_frame_alias is not None and operand=='rbp'and v==('local',rbp_origin):
    rbp_copy=operand=='rbp';encoded_offset=offset
    if rbp_copy:offset+=rbp_origin
    source=state.get(register)
    vector2=source is not None and source[0]=='member'and events[source[1]].get('kind')=='value8:UnityEngine.Vector2'
    if vector2:
     e=events[source[1]];layout=e.get('nominalValueLayout',{});parameter=bytes.fromhex(setters[source[1]].get('parameterTypeRecordHex',''))
     need('exact-typed-Vector2-register-local',e.get('declaredType')==layout.get('typeName')=='UnityEngine.Vector2'
         and e.get('mode')=='typed-register-vector2'and e.get('resultAbi')=='rax'and e.get('actualSourceProved')is True
         and e.get('wireBytes')==layout.get('managedBytes')==setters[source[1]]['storedBytes']==width==8
         and layout.get('fields')in([('x','float',16),('y','float',20)],[['x','float',16],['y','float',20]])
         and type(layout.get('typeDefinition'))is int and len(parameter)==16 and parameter[10:12]==bytes((17,128))
         and int.from_bytes(parameter[:8],'little')==layout['typeDefinition']and source[2:4]==(0,8)
         and register=='rax'and offset==96 and ec.raw(r)==bytes.fromhex('4889442460'))
     for i in range(8):locals_[offset+i]=(source[1],i)
     inline_homes.append(dict(memberIndex=source[1],displacement=offset,bytes=8,fieldBytes=8,sourceOffset=0,
         storeInstruction=ec.site(r,base),nominalTypeName='UnityEngine.Vector2',nominalTypeDefinition=layout['typeDefinition'],
         resultRegister='rax',sourceMode='typed-register-vector2'))
    elif source is not None and source[0]=='member'and events[source[1]].get('resultAbi')=='hidden-local':
     query=width==16 and events[source[1]].get('kind')=='managed:Beyond.Gameplay.Core.GameplayTagQuery'
     if query:_same_Query_local16_copy(r,events[source[1]],setters[source[1]],source,locals_,register=register,width=width,offset=offset)
     quaternion_copy=not rbp_copy and events[source[1]].get('kind')=='value16:UnityEngine.Quaternion'and events[source[1]].get('sourceContextMode')=='owned-closed-forwarder'
     if quaternion_copy:
      from scripts.game_data.memorypack.leveldata_quaternion_forwarder_sources import validate_local_copy
      validate_local_copy(r,events[source[1]],setters[source[1]],source,locals_,register=register,width=width,offset=offset)
     aabb_copy=not rbp_copy and events[source[1]].get('kind')=='value16:Beyond.AABB'
     if aabb_copy:
      from scripts.game_data.memorypack.generated_aabb_field_sources import validate_local_copy
      validate_local_copy(r,events[source[1]],setters[source[1]],source,locals_,register=register,width=width,offset=offset)
     body_copy=source[1]in named_body32
     if body_copy and not rbp_copy:_same_body32_local_copy(r,events[source[1]],setters[source[1]],source,locals_,register=register,width=width,offset=offset)
     entity_copy=not rbp_copy and source[1]in opaque_entity40
     if entity_copy:
      from scripts.game_data.memorypack.generated_entity_ptr_field_sources import validate_local_copy
      validate_local_copy(r,events[source[1]],setters[source[1]],source,locals_,register=register,width=width,offset=offset)
     alpha56=source[1]in named56
     outer=source[1]in outer_raw
     if outer:need('exact-outer-vector-local-copy',(width,source[2],register)in((16,0,'xmm0'),(16,16,'xmm1'),(8,32,'xmm0'),(4,32,'rax'),(4,40,'rax')))
     module_copy=rbp_copy and source_frame_alias.get('profile')=='finite-module-rbp-value-locals.v1'
     if module_copy:
      from scripts.game_data.memorypack.generated_module_frame_sources import copy_spec
      spec=copy_spec(source_frame_alias,source[1],events[source[1]]['declaredType'],width,source[2],register,encoded_offset)
      need('exact-Module-frame-copy-bytes',ec.raw(r).hex().lower()==spec['instructionHex'])
     elif rbp_copy:need('exact-Trigger-frame-value-copy',(events[source[1]]['declaredType'],width,source[2],register,encoded_offset)in(
         ('Beyond.Gameplay.Core.TriggerShapeData',16,0,'xmm0',39),('Beyond.Gameplay.Core.TriggerShapeData',16,16,'xmm1',55),
         ('Beyond.Gameplay.Core.TriggerShapeData',8,32,'xmm0',71),('Beyond.Gameplay.Core.TriggerShapeData',4,40,'rax',79),
         ('UnityEngine.Vector3',8,0,'xmm0',-41),('UnityEngine.Vector3',4,8,'rax',-33)))
     if alpha56:need('exact-Alpha56-vector-local-copy',
         (width,source[2],register)in((16,0,'xmm0'),(16,16,'xmm1'),(16,32,'xmm0'))
         or module_copy and(width,source[2],register)==(8,48,'xmm1'),
         dict(memberIndex=source[1],width=width,sourceOffset=source[2],register=register,moduleFrameCopy=module_copy))
     need('whole-hidden-integer-local-copy',source[3]>=width and(width==4 or width==16 and(source[1]in named24 or alpha56 or outer or module_copy or body_copy or entity_copy)or query or quaternion_copy or aabb_copy or(rbp_copy or entity_copy)and width==8)and offset>=32,
         dict(memberIndex=source[1],declaredType=events[source[1]].get('declaredType'),width=width,sourceOffset=source[2],register=register,destination=offset))
     for i in range(width):locals_[offset+i]=(source[1],source[2]+i)
     copy=dict(displacement=offset,bytes=width,storeInstruction=ec.site(r,base),memberIndex=source[1])
     if source[1]in named24:copy.update(nominalTypeName=events[source[1]]['declaredType'],nominalTypeDefinition=setters[source[1]]['nominalValueLayout']['typeDefinition'],sourceOffset=source[2])
     if query:copy.update(nominalTypeName=events[source[1]]['declaredType'],nominalTypeDefinition=setters[source[1]]['managedValueLayout']['typeDefinition'],
         sourceOffset=0,sameOwnedHiddenLocalCopy=True)
     elif quaternion_copy or aabb_copy:copy.update(nominalTypeName=events[source[1]]['declaredType'],nominalTypeDefinition=events[source[1]]['nominalValueLayout']['typeDefinition'],
         sourceOffset=0,sameOwnedHiddenLocalCopy=True,sourceRegister=register,
         parentType=setters[source[1]]['targetField'].rpartition('::')[0],fieldName=events[source[1]]['fieldName'])
     elif body_copy:copy.update(nominalTypeName=events[source[1]]['declaredType'],nominalTypeDefinition=setters[source[1]]['managedValueLayout']['typeDefinition'],sourceOffset=source[2],sourceRegister=register)
     elif alpha56:copy.update(nominalTypeName=events[source[1]]['declaredType'],nominalTypeDefinition=setters[source[1]]['managedValueLayout']['typeDefinition'],sourceOffset=source[2],sourceRegister=register)
     elif entity_copy:copy.update(nominalTypeName=events[source[1]]['declaredType'],nominalTypeDefinition=setters[source[1]]['managedValueLayout']['typeDefinition'],
         sourceOffset=source[2],sourceRegister=register,originalHiddenLocal=dict(displacement=80,bytes=40),opaqueRuntimeBitsPreserved=True)
     if outer:copy.update(nominalTypeName=events[source[1]]['declaredType'],nominalTypeDefinition=setters[source[1]]['nominalValueLayout']['typeDefinition'],sourceOffset=source[2],sourceRegister=register)
     if rbp_copy:
      raw=bytes.fromhex(setters[source[1]]['parameterTypeRecordHex'])
      copy.update(nominalTypeName=events[source[1]]['declaredType'],nominalTypeDefinition=int.from_bytes(raw[:8],'little'),
          sourceOffset=source[2],sourceRegister=register,frameAddress=dict(baseRegister='rbp',displacement=encoded_offset,rspDisplacement=offset))
     copies.append(copy)
    else:need('frame-home-only',register in NONVOLATILE and width==8)
   else:
    source=state.get(register);need('owned-source-field-store',source is not None and source[0]=='member'and source[3]>=width and v is not None and v[0]in('original','field'))
    n,relative=source[1:3]
    need('actual-current-named-field',offset==setters[n]['fieldOffset']+relative if v[0]=='original'else v==('field',n,0)and offset==relative)
    store(n,relative,width,r,source[4])
   take();continue
  m=re.fullmatch(r'mov(?:zx)? (\w+), (\w+)',text)
  if m:
   destination,source=map(reg,m.groups());v=state.get(source);need('known-register-source',v is not None,(r,state))
   width=v[3]if v[0]=='member'else 8
   need('complete-register-source-width',register_bytes(m[2])>=width and register_bytes(m[1])>=width)
   state[destination]=v;take();continue
  if text.startswith(('add rsp, ','pop ')):take();continue
  raise ValueError(LABEL+'.unowned-instruction:'+str(r))
 need('every-current-source-once',len(sources)==len(events))
 need('complete-named-field-byte-coverage',all(got==set(range(s['storedBytes']))for got,s in zip(stores,setters)))
 need('all-owned-context-loads-bound',set(context_by)=={base+e['context']['instructionRva']for e in events if e.get('context')is not None})
 result=dict(selectedProgram=[ec.site(r,base)for r in path],sources=sources,fieldStores=field_stores,actualCalls=calls,ownedNullExits=null_exits,
  hiddenSourceLocals=hidden,sourceLocalCopies=copies,completeSelectedNormalProgram=True,childGrammarAdmitted=False,wholeOwnerAdmitted=False,
  **(dict(initializedZeroLocals=static_out_parent['initializedZeroLocals'],staticOutParentSetup=static_out_parent)if static_out_parent is not None else{}))
 if cache_uses:result['cachedAccesses']=cache_uses
 if collectors:result['conditionalDisabledCollectors']=collectors
 if inline_homes:result['sourceLocalValues']=inline_homes
 if source_frame_alias is not None:result['sourceFrameAlias']=source_frame_alias
 return result
