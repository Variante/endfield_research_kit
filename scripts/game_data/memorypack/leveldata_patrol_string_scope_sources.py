"""Actual warm UnSafeString block lifetime inside the resource request.

The selected path creates no temporary strings. It pops an existing empty
block, pushes it onto the initially empty active stack, then the actual inline
IDisposable callback returns that block to spare pool storage and balances the
active stack. No allocated zero state, ordinary callback alias or cold pool
construction is assumed.
"""
import struct
from scripts.game_data.memorypack import leveldata_patrol_request_programs as paths
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as packets

SCHEMA='endfield.story-patrol-temporary-string-block-sources.v1'
OWNER='Beyond.UnSafeString'
BLOCK=OWNER+'+HgStringBlock'
STACK='System.Collections.Generic.Stack`1'


def need(check,condition):
 if not condition:raise ValueError('patrolStringScope.'+check)


def _programs(p):
 from scripts.game_data.memorypack.leveldata_patrol_event_params_programs import disabled_barrier_program
 base=p['imageBase'];h=p['helpers'];r={k:packets.raw(v,base)for k,v in h.items()}
 return packets.norm(dict(request=paths.request(r['request'],base+h['request']['entryRva']),scope=paths.scope_cached(r['scope'],base+h['scope']['entryRva']),
  push=paths.block_push(r['push'],base+h['push']['entryRva']),dispose=paths.dispose_empty_block(r['dispose'],base+h['dispose']['entryRva']),
  arrayStore=paths.array_store(r['arrayStore'],base+h['arrayStore']['entryRva']),pop=paths.block_pop(r['pop'],base+h['pop']['entryRva']),
  barrier=disabled_barrier_program(r['barrier'],base+h['barrier']['entryRva'])))


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,_vtable
 from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.memorypack import leveldata_patrol_resource_handle_sources as parent,leveldata_patrol_class_preparation_sources as preparation
 _publication_gate(image,pins);source=parent.derive(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 h={'request':packets._parent_packet(source['proof']['callees']['request'],base)}
 r=paths.request(packets.raw(h['request'],base),base+h['request']['entryRva'])
 for role,key in(('scope','stringBlock'),('dispose','disposeStringBlock')):h[role]=packets.packet(image,next(c['targetVa']for c in r['calls']if c['role']==key))
 scope=paths.scope_cached(packets.raw(h['scope'],base),base+h['scope']['entryRva']);h['push']=packets.packet(image,scope['activePushCall']['targetVa'])
 disp=paths.dispose_empty_block(packets.raw(h['dispose'],base),base+h['dispose']['entryRva'])
 prep=preparation.derive(image,pins,target=next(c['targetVa']for c in disp['calls']if c['role']=='prepareBlockClass'))
 for role,key in(('arrayStore','arrayStore'),('pop','activePop')):h[role]=packets.packet(image,next(c['targetVa']for c in disp['calls']if c['role']==key))
 barrier=next(c['targetVa']for c in disp['calls']if c['role']=='barrier');h['barrier']=packets.packet(image,barrier,span=12)
 g=BytesPath(packets.raw(h['barrier'],base),barrier);g.relative('833d');g.take('00','4c8bc1');tail=packets.packet(image,g.relative('74',1),span=1)
 h['barrier']['windows']+=tail['windows'];h['barrier']['regions']+=tail['regions']
 fields={}
 for name in(OWNER,BLOCK):
  td=ctx.index.types[name];offsets=runtime_type_field_offsets(image.metadata,image.pe,image.registration,td.index)
  fields[name]=[dict(name=image.metadata.string(f.name_index),typeName=ctx.type_name(f.type_index),offset=offsets[image.metadata.string(f.name_index)],
   static=bool(ctx.field_attributes(f.type_index)&16))for f in image.metadata.fields_for(td)]
 methods={}
 for role,name,mname in(('scope',OWNER,'Scope'),('dispose',BLOCK,'System.IDisposable.Dispose')):
  td=ctx.index.types[name];m,=[m for m in image.metadata.methods_for(td)if image.metadata.string(m.name_index)==mname]
  methods[role]=dict(definition=m.index,typeDefinition=td.index,typeName=name,name=mname,parameters=[ctx.type_name(p.type_index)for p in image.metadata.parameters_for(m)],
   returnType=ctx.type_name(m.return_type),static=bool(m.flags&16),slot=m.slot,targetRva=image.method_pointer_va(m)-base)
  if role=='dispose':_vtable(image,td.index,m.slot,m.index,'patrolStringScope.ownDispose')
 td=ctx.index.types[BLOCK];section=image.metadata.sections['interfaceOffsets'];at=section.offset+td.interface_offsets_start*8
 rows=list(struct.iter_unpack('<ii',image.metadata.buf[at:at+td.interface_offsets_count*8]));off,=[offset for t,offset in rows if ctx.type_name(t)=='System.IDisposable']
 interface=dict(typeName='System.IDisposable',relativeSlot=0,interfaceOffset=off,effectiveSlot=off,methodDefinition=methods['dispose']['definition'],vtableCount=td.vtable_count)
 symbols=ContextSymbols(image);ge=GenericEntries(image);uses={};requests={}
 sites=[('scope',u)for u in scope['usageSites']]+[('dispose',u)for u in disp['usageSites']]
 for role,u in sites:
  actual=derive_typed_usage_context(image,u['instructionVa']-base,label='patrolStringScope.actualUsage');uses[str(u['instructionVa']-base)]=actual
 for role,site,target in(('push',scope['activePushMethodInfoSite'],scope['activePushCall']['targetVa']),
  ('pop',next(u for u in disp['usageSites']if u['role']=='activePop'),next(c['targetVa']for c in disp['calls']if c['role']=='activePop'))):
  u=derive_typed_usage_context(image,site['instructionVa']-base,label='patrolStringScope.actualStackMethod')
  m=image.metadata.methods[u['methodSpec'][0]];requests[role]=dict(usage=u,actualTargetRva=target-base,returnType=symbols.type(ctx.type_pointer(m.return_type)),
   parameterTypes=[symbols.type(ctx.type_pointer(p.type_index))for p in image.metadata.parameters_for(m)],declaringType=m.declaring_type,
   registrations=ge.observe(m.index,u['classArguments'],u['methodArguments']),canonicalPointerAliasClaimed=False)
 proof=dict(imageBase=base,resourceHandleSource=source,helpers=h,classPreparation=prep,fields=fields,methods=methods,interface=interface,
  actualUsages=uses,stackRequests=requests);proof['programs']=_programs(proof)
 value=packets.norm(dict(schema=SCHEMA,status='validated-conditional-temporary-string-block-lifetime',nativeInputs=pins,proof=proof,
  selectedTemporaryStringBlockPoolEffectsProved=True,actualInlineDisposeAndFullFramesProved=True,
  allocatorZeroStateAssumed=False,temporaryStringCreationOrRecycleEffectsProved=False,coldPoolConstructionProved=False,
  actualPoolCallbackOrBlockIdentityObserved=False,runtimeInvocationObserved=False,playbackProved=False,
  conditions=['Initialized UnSafeString class and compatible stable static fields. The spare block pool is nonempty; its popped block has a nonnull empty string stack. The active block stack is initially empty and has spare capacity. No temporary string is added on this selected request path.',
   'The same actual HgStringBlock callback and MethodInfo are selected through the first matching IDisposable interface record and the second inline marker. Metadata proves the own named interface/vtable relationship, not the live object or callback identity.',
   'Collector is disabled; all pool/active arrays and counters satisfy the actual checked bounds, spare capacity and nonwrapping signed count conditions. Source restoration balances the selected push/pop and returns the block to the pool; it neither allocates nor assumes zeroed allocation.']))
 validate(value,pins);_publication_gate(image,pins);return value


def validate(value,pins):
 from scripts.game_data.memorypack import leveldata_patrol_resource_handle_sources as parent,leveldata_patrol_class_preparation_sources as preparation
 need('envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-temporary-string-block-lifetime'and value.get('nativeInputs')==pins
  and all(value.get(k)is True for k in('selectedTemporaryStringBlockPoolEffectsProved','actualInlineDisposeAndFullFramesProved'))
  and all(value.get(k)is False for k in('allocatorZeroStateAssumed','temporaryStringCreationOrRecycleEffectsProved','coldPoolConstructionProved','actualPoolCallbackOrBlockIdentityObserved','runtimeInvocationObserved','playbackProved')))
 p=value['proof'];base=p['imageBase'];parent.validate(p['resourceHandleSource'],pins);preparation.validate(p['classPreparation'],pins)
 need('exact-helper-set',set(p['helpers'])=={'request','scope','dispose','push','pop','arrayStore','barrier'})
 q=_programs(p);need('complete-selected-source-replay',q==p['programs'])
 need('same-actual-disabled-collector-cell',len({q[k]['collectorDisabledFlagVa']for k in('scope','push','pop','arrayStore','barrier')})==1)
 need('actual-request-source',p['helpers']['request']==packets._parent_packet(p['resourceHandleSource']['proof']['callees']['request'],base))
 for role,callrole in(('scope','stringBlock'),('dispose','disposeStringBlock')):
  need('actual-request-callee:'+role,next(c['targetVa']for c in q['request']['calls']if c['role']==callrole)==base+p['helpers'][role]['entryRva'])
 need('same-active-push-source',q['scope']['activePushCall']['targetVa']==base+p['helpers']['push']['entryRva'])
 for c in q['dispose']['calls']:
  rva=p['classPreparation']['actualEntryRva']if c['role']=='prepareBlockClass'else p['helpers'][{'activePop':'pop'}.get(c['role'],c['role'])]['entryRva']
  need('actual-independent-dispose-child:'+c['role'],c['targetVa']==base+rva)
 need('own-static-and-block-field-sets',set(p['fields'])=={OWNER,BLOCK})
 for name,typ,offset in(('s_blocks',STACK+'<'+BLOCK+'>',0),('s_stackBlocks',STACK+'<'+BLOCK+'>',8),('s_currentBlock',BLOCK,16)):
  row,=[r for r in p['fields'][OWNER]if r['name']==name];need('own-static-field:'+name,row==dict(name=name,typeName=typ,offset=offset,static=True))
 need('own-empty-block-stack-field',p['fields'][BLOCK]==[dict(name='m_stack',typeName=STACK+'<'+OWNER+'>',offset=16,static=False)])
 for role in('scope','dispose'):
  m=p['methods'][role];need('own-method-ABI:'+role,m['typeName']==(OWNER if role=='scope'else BLOCK)and m['name']==('Scope'if role=='scope'else'System.IDisposable.Dispose')
   and m['static']is(role=='scope')and m['parameters']==[]and m['returnType']==('System.IDisposable'if role=='scope'else'void')
   and m['targetRva']==(p['helpers']['scope']['entryRva']if role=='scope'else q['dispose']['selectedCallbackTargetVa']-base))
 i=p['interface'];need('actual-own-IDisposable-slot',i['typeName']=='System.IDisposable'and i['relativeSlot']==0 and i['interfaceOffset']==i['effectiveSlot']==p['methods']['dispose']['slot']==4
  and i['methodDefinition']==p['methods']['dispose']['definition']and i['vtableCount']>4)
 for role in('scope','dispose'):
  for site in q[role]['usageSites']:
   u=p['actualUsages'][str(site['instructionVa']-base)]
   need('actual-typed-cell:'+role,u['instructionRva']+base==site['instructionVa']and u['usageCellRva']+base==site['cellVa'])
   if u['tag']==1:need('own-string-class-context',u['typeName']==OWNER)
   else:need('own-Stack-method-context',u['tag']==6 and u['typeName']==STACK and u['classArguments']==[BLOCK]and u['methodArguments']==[])
 for role in('push','pop'):
  r=p['stackRequests'][role];u=r['usage'];need('own-closed-stack-request:'+role,u['tag']==6 and u['typeName']==STACK and u['methodName']==role.title()and u['classArguments']==[BLOCK]and u['methodArguments']==[]
   and r['actualTargetRva']==p['helpers'][role]['entryRva']and r['canonicalPointerAliasClaimed']is False)
  formal=r['parameterTypes'][0]if role=='push'else r['returnType']
  need('reciprocal-stack-value-parameter',bytes.fromhex(formal['rawHex'])[10]==19 and formal['parameterOwner']['typeIndex']==r['declaringType']and formal['parameterOwner']['ordinal']==0)
 return value
