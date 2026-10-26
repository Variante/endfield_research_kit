"""Independent closed-byte cached TLS pool effects for the Patrol data caller.

This source selects the actual named Rent/Return implementations through an
explicit runtime callback/MethodInfo condition. It proves removal and restoration
of the same existing byte array, without allocating, clearing, reading its old
contents or assuming initialized storage from an allocator.
"""
import json
from scripts.game_data.memorypack import leveldata_patrol_buffer_pool_programs as programs
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as packets

SCHEMA='endfield.story-patrol-buffer-pool-sources.v1'
POOL='System.Buffers.TlsOverPerCoreLockedStacksArrayPool`1'


def need(check,condition):
 if not condition:raise ValueError('patrolBufferPoolSources.'+check)


def norm(value):return json.loads(json.dumps(value))


def _programs(p):
 base=p['imageBase'];h=p['helpers']
 return norm(dict(rent=[programs.rent(packets.raw(h['rent'],base),base+h['rent']['entryRva'],size=n)for n in range(1,129)],
  returns=[programs.return_buffer(packets.raw(h['return'],base),base+h['return']['entryRva'],capacity=n)for n in(16,32,64,128)],
  guard=programs.guard(packets.raw(h['guard'],base),base+h['guard']['entryRva'])))


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.memorypack import leveldata_patrol_data_path_sources as parent
 _publication_gate(image,pins);base=image.pe.image_base;source=parent.derive(image,pins);ctx=NativeReferenceContext(image);symbols=ContextSymbols(image);ge=GenericEntries(image)
 td=ctx.index.types[POOL];methods={};helpers={}
 for role,name,slot in(('rent','Rent',4),('return','Return',5)):
  method,=[m for m in image.metadata.methods_for(td)if image.metadata.string(m.name_index)==name and m.slot==slot]
  rows=ge.observe(method.index,['byte'],[]);need('one-actual-byte-callback-registration:'+role,len(rows)==1 and bool(rows[0]['pointer']))
  registration,=rows;parameters=list(image.metadata.parameters_for(method))
  element_type=ctx.type_pointer(method.return_type if role=='rent'else parameters[0].type_index)
  array_raw=image.pe.bytes_at_va(element_type,16);need('own-vector-array-formal:'+role,array_raw[10]==29)
  element=symbols.type(int.from_bytes(array_raw[:8],'little'))
  methods[role]=dict(definition=method.index,typeDefinition=td.index,typeName=POOL,methodName=name,slot=slot,
   parameters=[ctx.type_name(p.type_index)for p in parameters],returnType=ctx.type_name(method.return_type),
   arrayFormalRawHex=array_raw.hex().upper(),arrayElement=element,registration=registration)
  helpers[role]=packets.packet(image,registration['pointer'])
 guard=source['proof']['children']['disposeBufferGuard'];helpers['guard']=packets._parent_packet(guard,base)
 value=norm(dict(schema=SCHEMA,status='validated-conditional-cached-byte-pool-sources',nativeInputs=pins,
  proof=dict(imageBase=base,dataPathSource=source,methods=methods,helpers=helpers),
  selectedByteRentAndReturnSourceEffectsProved=True,sameExistingBufferRemovedAndRestoredProved=True,
  allocationOrZeroStateAssumed=False,runtimeCallbackSelectionObserved=False,runtimeTlsOrBufferObserved=False,
  runtimeInvocationObserved=False,playbackProved=False,
  conditions=['The data caller selects the same ready closed ArrayPool<byte> receiver. Its actual slot4/slot5 callback and MethodInfo pairs select the independently registered owned TlsOverPerCoreLockedStacksArrayPool<byte> Rent/Return methods. No live callback or receiver-class identity is observed.',
   'Requested cached size1..128; the returned array is the existing compatible byte array of length16<<bucket with sufficient capacity. Same-thread valid stable TLS/context/class state, actual TLS import normal result, compatible nonnull bucket arrays, event-source cache and disabled collector are required.',
   'No intervening mutation of the selected same TLS slot between Rent and Return; the slot cleared by Rent is null at Return. The same buffer, pool and closed context are passed by the owning guard, with clearArray false. The caller overwrites the selected encoded prefix before hashing it; old buffer contents are not assumed zero.',
   'Cold TLS/context/class setup, absent buffers, per-core stacks, allocation, clearing, logging/exceptional branches and concurrent aliases outside this selected domain remain separate source alternatives.']))
 value['proof']['programs']=_programs(value['proof']);validate(value,pins);_publication_gate(image,pins);return value


def validate(value,pins):
 from scripts.game_data.memorypack import leveldata_patrol_data_path_sources as parent
 need('source-envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-cached-byte-pool-sources'and value.get('nativeInputs')==pins
  and all(value.get(k)is True for k in('selectedByteRentAndReturnSourceEffectsProved','sameExistingBufferRemovedAndRestoredProved'))
  and all(value.get(k)is False for k in('allocationOrZeroStateAssumed','runtimeCallbackSelectionObserved','runtimeTlsOrBufferObserved','runtimeInvocationObserved','playbackProved')))
 p=value['proof'];base=p['imageBase'];parent.validate(p['dataPathSource'],pins)
 need('exact-owned-helper-and-method-roles',set(p['helpers'])=={'rent','return','guard'}and set(p['methods'])=={'rent','return'})
 actual=_programs(p);need('all-whole-cached-pool-programs',actual==p['programs'])
 for role,name,slot,count in(('rent','Rent',4,1),('return','Return',5,2)):
  m=p['methods'][role];r=m['registration'];array=bytes.fromhex(m['arrayFormalRawHex']);element=m['arrayElement']
  need('own-exact-byte-closed-method:'+role,m['typeName']==POOL and m['methodName']==name and m['slot']==slot
   and type(m['definition'])is int and m['definition']>=0 and len(m['parameters'])==count
   and r['pointer']==base+p['helpers'][role]['entryRva']and m['definition']in r['methodDefinitionIndices']and r['runtimeSelectionObserved']is False
   and len(r['classInstantiation']['arguments'])==1 and r['classInstantiation']['arguments'][0]['raw_type_record_hex'][20:22].upper()=='05'
   and r['methodInstantiation']['arguments']==[])
  need('own-reciprocal-array-VAR:'+role,len(array)==16 and array[10]==29 and bytes.fromhex(element['rawHex'])[10]==19
   and element['parameterOwner']['typeIndex']==m['typeDefinition']and element['parameterOwner']['ordinal']==0)
  need('own-method-value-ABI:'+role,(m['parameters']==['int']and m['returnType'].endswith('[]'))if role=='rent'else
   (m['parameters'][0].endswith('[]')and m['parameters'][1]=='bool'and m['returnType']=='void'))
 data=p['dataPathSource']['proof'];caller=data['programs'][-1]
 need('same-actual-owning-disposal-body',p['helpers']['guard']==packets._parent_packet(data['children']['disposeBufferGuard'],base))
 need('exact-Rent-and-Return-logical-slots',caller['poolRentCallbackClassOffset']==320+16*p['methods']['rent']['slot']
  and caller['poolRentMethodInfoClassOffset']==328+16*p['methods']['rent']['slot']
  and actual['guard']['callbackClassOffset']==320+16*p['methods']['return']['slot']
  and actual['guard']['methodInfoClassOffset']==328+16*p['methods']['return']['slot'])
 need('same-actual-guard-preparation',actual['guard']['preparationCall']['targetVa']==base+data['children']['preparePoolClass']['actualEntryRva'])
 expected=data['children']['indexedContext']['entryRva']
 need('same-exact-typed-context-child',all(c['role']=='indexedContext'and c['targetVa']==base+expected
  for path in[*actual['rent'],*actual['returns']]for c in path['calls']))
 need('same-TLS-source-and-collector',len({path['tlsLookupIatCell']for path in[*actual['rent'],*actual['returns']]})==1
  and len({path['threadRootCellVa']for path in[*actual['rent'],*actual['returns']]})==1
  and len({path['selectedCollectorDisabledCellVa']for path in[*actual['rent'],*actual['returns']]})==1)
 need('all-bounded-request-capacity-bucket-pairs',all(path['bucketSize']in(16,32,64,128)and path['bucketSize']>=path['requestSize']
  and path['bucketIndex']==programs.bucket(path['requestSize'])for path in actual['rent']))
 return value
