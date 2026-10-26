"""Prove selected constructor setup and conditional entry-to-array-store provenance."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require

def check(raw,pointer,end,a):
 forms=['proxy-root',b'\x48\x8d\x4c\x24'+bytes([a['outTemporary']]),b'\x48\x8b\xd5','proxy-call',b'\x0f\x10\x44\x24'+bytes([a['outTemporary']]),b'\x49\x8b\xcf',b'\x41\x0f\x11\x07','post-call','proxy-root',b'\x48\x8d\x4c\x24'+bytes([a['outTemporary']]),b'\x49\x8b\xd6','proxy-call',b'\x0f\x10\x44\x24'+bytes([a['outTemporary']]),b'\x49\x8d\x4f'+bytes([a['secondCarrierSlot']]),b'\x41\x0f\x11\x47'+bytes([a['secondCarrierSlot']]),'post-call',b'\x48\x8b\x44\x24'+bytes([a['environmentCurrentStack']]),b'\x49\x8d\x4f'+bytes([a['environmentSlot']]),b'\x49\x89\x47'+bytes([a['environmentSlot']]),b'\x49\x89\x5f'+bytes([a['maskSlot']]),'post-call',b'\x0f\x57\xc0',b'\xf2\x41\x0f\x11\x47'+bytes([a['zeroSlot']]),'class-root',b'\x83\xb8'+struct.pack('<i',a['classDword'])+b'\x00','class-zero',b'\x48\x8b\x80'+struct.pack('<i',a['staticCarrier'])]
 at=0;proxy_roots=[];proxy_calls=[];post_calls=[];excluded=None;class_root=None
 for form in forms:
  if isinstance(form,bytes):
   _require(raw[at:at+len(form)]==form,'poise-setup-instruction',form.hex(),raw[at:at+len(form)].hex());size=len(form)
  elif form.endswith('-root'):
   size=7;prefix=b'\x4c\x8b\x05' if form=='proxy-root' else b'\x48\x8b\x05';part=raw[at:at+7]
   _require(len(part)==7 and part[:3]==prefix,'poise-setup-root',form,part.hex());target=pointer+at+7+int.from_bytes(part[3:],'little',signed=True)
   if form=='proxy-root':proxy_roots.append(target)
   else:class_root=target
  elif form.endswith('-call'):
   size=5;part=raw[at:at+5];_require(len(part)==5 and part[0]==0xe8,'poise-setup-call',form,part.hex());target=pointer+at+5+int.from_bytes(part[1:],'little',signed=True)
   (proxy_calls if form=='proxy-call' else post_calls).append(target)
  else:
   size=6;part=raw[at:at+6];_require(len(part)==6 and part[:2]==b'\x0f\x84','poise-setup-guard','complete JZ',part.hex());excluded=pointer+at+6+int.from_bytes(part[2:],'little',signed=True)
   _require(not pointer<=excluded<end,'poise-setup-excluded','outside whole selected setup and subsequent publication',excluded)
  at+=size
 _require(at==len(raw)==134,'poise-setup-complete','complete selected setup',at)
 _require(len(set(proxy_roots))==len(set(proxy_calls))==len(set(post_calls))==1,'poise-setup-repeated-targets','same actual reloaded root/proxy and opaque post targets',[proxy_roots,proxy_calls,post_calls])
 return {'selectedBytes':134,'actualClassRootStorage':class_root,'actualProxyRoot':proxy_roots[0],'actualOpaqueProxyCall':proxy_calls[0],'actualOpaquePostStoreCall':post_calls[0],'actualExcludedInitializer':excluded,'opaqueCalls':5,
  'rawCarrierWrites':[{'offset':0,'width':16},{'offset':a['secondCarrierSlot'],'width':16},{'offset':a['environmentSlot'],'width':8},{'offset':a['maskSlot'],'width':8},{'offset':a['zeroSlot'],'width':8}],
  'headerFieldMeaningsProved':False,'opaqueProxyProducesTypedOutProved':False,
  'conditions':['all five opaque calls normally preserve nonvolatile carrier/frame values and do not invalidate subsequent saved/root/out/receiver storage','out16 bytes read at call-return time are readable; helpers are not assumed to initialize them','post-store helper writes are noninterfering with selected later slot/pointer publication','opaque class dword nonzero selects final static-carrier load and direct publication fallthrough']}


def check_poise_constructor_setup(index,entry,publication,guard,bridge,store,spec,a):
 from scripts.game_data.damage_snapshot_poise_attribute_flow import physical_ranges
 expected=['poiseConstructorEntryFullWidthArgumentCarriersAndFrame','poiseOpaqueNormalPointerPublicationToSelectedArrayCarrier','poiseAttributeZeroIndexAndSignedGuard','poiseAttributeGuardArrayCarrierAndSelectedLoopJoin','poiseAttributeNormalDoubleToOldIndexStore']
 witnesses=[entry,publication,guard,bridge,store]
 _require([p.get('claim') for p in witnesses]==expected,'poise-setup-fresh-witnesses','fresh complete independently checked fragments',[p.get('claim') for p in witnesses])
 _require(len({p['symbol'] for p in witnesses})==1,'poise-setup-same-constructor','same fresh actual named constructor',[p['symbol'] for p in witnesses])
 pointer=int(entry['fragmentEnd'],16);end=int(publication['fragmentEntry'],16);cycle_end=int(store['fragmentEnd'],16)
 _require(end-pointer==134 and int(publication['fragmentEnd'],16)==int(guard['fragmentEntry'],16) and int(guard['fragmentEnd'],16)==int(bridge['fragmentEntry'],16) and int(bridge['fragmentEnd'],16)==int(store['fragmentEntry'],16),'poise-setup-selected-continuity','complete direct fallthrough from setup through fresh publication and first selected iteration',[pointer,end,cycle_end])
 declaration={**spec,'environmentCurrentStack':entry['conditionalEnvironmentCurrentStackOffset'],'classDword':a['classDwordDisp32'],'staticCarrier':a['staticCarrierDisp32']}
 proof=check(index.pe.bytes_at_va(pointer,134),pointer,cycle_end,declaration)
 ranges=physical_ranges(index,pointer,end)
 root_pointer=guard['actualLoopEntry'];root=index.pe.bytes_at_va(root_pointer,7)
 _require(len(root)==7 and root[:3]==b'\x48\x8b\x0d','poise-setup-guard-root','fresh actual complete guard root load',root.hex())
 root_storage=root_pointer+7+int.from_bytes(root[3:],'little',signed=True)
 _require(root_storage==proof['actualClassRootStorage'],'poise-setup-count-source-root','same actual anonymous root storage',root_storage)
 _require(proof['actualOpaquePostStoreCall']==publication['actualOpaquePostStoreTarget'],'poise-setup-post-target','same actual opaque post-store target',publication['actualOpaquePostStoreTarget'])
 return {**proof,'claim':'poiseSelectedConstructorSetupToFirstAttributeStoreAndCountSource','symbol':entry['symbol'],'fragmentEntry':hex(pointer),'fragmentEnd':hex(end),'actualPhysicalPdataRanges':ranges,
  'tier':'conditional','selectedEntryToFirstStoreEndBytes':cycle_end-int(entry['fragmentEntry'],16),'selectedEntryToFirstStoreCfgProved':True,
  'conditionalEntryThisToArrayCarrierOwnerFlowProved':True,'conditionalRequestedDwordAndGuardBoundSameSourceProved':True,'returnedObjectLengthProved':False,'boxedHeaderAdjustmentProved':False,'firstIterationSelectionCondition':'signed current bound is positive for zero index; all remaining class/null/signed/unsigned guards select and each called path returns normally',
  'boundary':'The fresh complete constructor entry, every byte of this selected setup, actual returned-pointer publication and complete first guard/bridge/provider/store form one explicit selected caller CFG. This closes incoming this-to-R15 and actor/mask carrier continuity only conditional on every opaque call and normal provider preserving carriers/frame and all temporary/receiver/root storage writes being noninterfering. The setup loads the same actual anonymous root storage and static-carrier displacement later used by the guard; its RAX flows into the publication request DWORD load, while the guard compares the DWORD at that same derived address. Equality of requested bits and later signed bound requires unchanged current root/class/static/count backing. No returned-object length or allocator semantics follow. Raw sixteen-byte out-at-return copies, environment/mask stores and low64 zero are exact selected operations, with helper initialization, typed fields/header, whole constructor return, other paths and live values still open.'}
