"""Authenticate the second Poise pointer request, defender store loop and void footer."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require

def guard(raw,pointer,a,footer):
 _require(len(raw)==35 and raw[:3]==b'\x48\x8b\x05' and raw[7:14]==b'\x83\xb8'+struct.pack('<i',a['classDword'])+b'\x00' and raw[14:16]==b'\x0f\x84' and raw[20:27]==b'\x48\x8b\x80'+struct.pack('<i',a['staticCarrier']) and raw[27:29]==b'\x3b\x18' and raw[29:31]==b'\x0f\x8d','defender-guard-complete','root,class,static carrier,signed EBX bound and JGE',raw.hex())
 classroot=pointer+7+int.from_bytes(raw[3:7],'little',signed=True)
 init=pointer+20+int.from_bytes(raw[16:20],'little',signed=True)
 exit=pointer+35+int.from_bytes(raw[31:35],'little',signed=True)
 _require(exit==footer,'defender-guard-footer','actual complete restoring footer',exit)
 _require(not pointer<=init<pointer+35,'defender-guard-excluded','initializer outside selected guard',init)
 return {'actualRootStorage':classroot,'actualExcludedInitializer':init,'actualFooterEntry':exit,'counter':'EBX signed Int32 compared with anonymous bound; JGE selects footer','conditions':['initial EBX0 survives first EDI loop and opaque normal calls','stable signed nonnegative bound and normal/noninterfering selected iteration for finite loop']}

def store(raw,pointer,field_offset,a,provider,backedge):
 forms=[b'\x49\x8b\x86'+struct.pack('<i',field_offset),b'\x48\x85\xc0','null-source',b'\x45\x33\xc0',b'\x8b\xd3',b'\x48\x8b\xc8','call',b'\x48\x85\xff','null-array',b'\x3b\x5f'+bytes([a['arrayLength']]),'bounds',b'\x48\x63\xc3',b'\xff\xc3',b'\xf2\x0f\x11\x44\xc7'+bytes([a['arrayPayload']]),'backedge']
 at=0;excluded={}
 for form in forms:
  if isinstance(form,bytes):
   _require(raw[at:at+len(form)]==form,'defender-store-instruction',form.hex(),raw[at:at+len(form)].hex());size=len(form)
  elif form in ('call','backedge'):
   size=5;part=raw[at:at+size];_require(len(part)==5 and part[0]==(0xe8 if form=='call' else 0xe9),'defender-store-transfer',form,part.hex());target=pointer+at+5+int.from_bytes(part[1:],'little',signed=True)
   _require(target==(provider if form=='call' else backedge),'defender-store-target',form,target)
  else:
   size=6;part=raw[at:at+size];_require(len(part)==6 and part[:2]==bytes([15,131 if form=='bounds' else 132]),'defender-store-guard',form,part.hex());target=pointer+at+6+int.from_bytes(part[2:],'little',signed=True)
   _require(not pointer<=target<pointer+len(raw),'defender-store-excluded','outside complete store',target);excluded[form]=target
  at+=size
 _require(at==len(raw)==63,'defender-store-complete','complete old-index request/store/backedge',at)
 return {'request':'R14 compatible actor field -> RCX, EBX old bits -> EDX, actual ordinary provider','write':'normal XMM0 low64 -> anonymous RDI+payload+8*signedInt32(oldEBX), old address formed before INC EBX32','excludedTargets':excluded,'liveActorOrArrayValuesProved':False}


def bridge(raw,pointer,end,a):
 forms=[b'\x49\x8b\x7f'+bytes([a['arrayCarrier']]),b'\x4d\x85\xf6','null-actor','root',b'\x83\xb9'+struct.pack('<i',a['classDword'])+b'\x00','class-zero',b'\x48\x8b\x81'+struct.pack('<i',a['staticCarrier']),b'\x48\x8b\x10',b'\x48\x85\xd2','null-opaque',b'\x81\x7a'+bytes([a['opaqueDword']])+struct.pack('<i',a['opaqueSignedLimit']),'signed-limit']
 at=0;excluded={}
 for form in forms:
  if isinstance(form,bytes):
   _require(raw[at:at+len(form)]==form,'defender-bridge-instruction',form.hex(),raw[at:at+len(form)].hex());size=len(form)
  elif form=='root':
   size=7;part=raw[at:at+7];_require(len(part)==7 and part[:3]==b'\x48\x8b\x0d','defender-bridge-root','complete RIP qword load',part.hex())
  else:
   size=6;part=raw[at:at+6];_require(len(part)==6 and part[:2]==bytes([15,143 if form=='signed-limit' else 132]),'defender-bridge-guard',form,part.hex());target=pointer+at+6+int.from_bytes(part[2:],'little',signed=True)
   _require(not pointer<=target<end,'defender-bridge-excluded','outside complete selected bridge',target);excluded[form]=target
  at+=size
 _require(at==len(raw)==65 and end==pointer+65,'defender-bridge-complete','whole selected bridge',at)
 return {'actualExcludedTargets':excluded,'explicitCalls':[],'indexAndActorCarrierModified':False,'arrayCarrierTransfer':'same anonymous R15 slot -> RDI; no later RDI writes'}


def footer(raw,entry_frame_delta):
 expected=bytes.fromhex('488b742450488b5c2458488b6c24604883c430415f415e5fc3')
 _require(raw==expected,'poise-ctor-footer-complete','complete RSI/RBX/RBP loads, frame reversal, three matching pops and RET',raw.hex())
 _require(entry_frame_delta==raw[18]+24,'poise-ctor-footer-frame','fresh allocation plus three pushes',entry_frame_delta)
 _require(raw[9]==16+entry_frame_delta and raw[14]==24+entry_frame_delta,'poise-ctor-footer-original-save-slots','original entry RBX/RBP shadow slots reloaded',[raw[9],raw[14]])
 return {'completeFooterBytes':25,'restoredGprs':['rsi','rbx','rbp','r15','r14','rdi'],'explicitFrameAndPushReversal':True,'returnAddressOperation':'normal RET reads and pops original entry return address after frame reversal; resulting SP equals entry SP plus8','wholeConstructorCfgOrHelperPreservationProved':False,'conditions':['fresh guard RSI spill is the unchanged caller RSI at the same actual SP80 slot','valid original saved/pop/return slots, current SP entrySP-frame72, and no writes interfere','normal selected RET and every preceding callee preserve required carrier/frame values']}


def declaration(spec,a):
 return {**spec,'classDword':a['classDwordDisp32'],'staticCarrier':a['staticCarrierDisp32'],'opaqueDword':a['opaqueDwordDisp8'],'opaqueSignedLimit':a['opaqueSignedLimit'],'arrayLength':a['arrayLengthDisp8'],'arrayPayload':a['arrayPayloadDisp8']}


def check_second_factory(index,first_guard,setup,spec,a):
 from scripts.game_data.damage_snapshot_poise_attribute_flow import physical_ranges
 from scripts.game_data.damage_snapshot_poise_array_publication_flow import check as publication
 _require(first_guard.get('claim')=='poiseAttributeZeroIndexAndSignedGuard' and setup.get('claim')=='poiseSelectedConstructorSetupToFirstAttributeStoreAndCountSource','defender-factory-fresh','fresh first guard and entry setup',[first_guard.get('claim'),setup.get('claim')])
 _require(first_guard['symbol']==setup['symbol'],'defender-factory-same-constructor','same actual named constructor',first_guard['symbol'])
 d=declaration(spec,a);pointer=first_guard['actualSignedBoundExit'];raw=index.pe.bytes_at_va(pointer,51)
 prefix=b'\x39\x99'+struct.pack('<i',d['classDword']);static=b'\x48\x8b\x81'+struct.pack('<i',d['staticCarrier'])
 _require(len(raw)==51 and raw[:6]==prefix and raw[6:8]==b'\x0f\x84' and raw[12:19]==static and raw[46:]==b'\x0f\x1f\x44\x00\x00','defender-factory-complete','complete class guard, publication and five-byte NOP',raw.hex())
 excluded=pointer+12+int.from_bytes(raw[8:12],'little',signed=True)
 _require(not pointer<=excluded<pointer+86,'defender-factory-excluded','outside factory and complete following guard',excluded)
 p=publication(raw[19:46],pointer+19,d['arrayCarrier']);guard_pointer=pointer+51;g=guard(index.pe.bytes_at_va(guard_pointer,35),guard_pointer,d,pointer+214)
 _require(g['actualRootStorage']==setup['actualClassRootStorage'],'defender-factory-same-count-root','same actual anonymous root storage',g['actualRootStorage'])
 ranges=physical_ranges(index,pointer,pointer+86)
 return {**p,**g,'claim':'poiseSecondOpaquePointerPublicationAndSignedGuard','symbol':setup['symbol'],'fragmentEntry':hex(pointer),'fragmentEnd':hex(pointer+86),'actualSecondGuardEntry':guard_pointer,'actualFirstClassInitializer':excluded,'actualPhysicalPdataRanges':ranges,
  'tier':'conditional','managedUnwindFamilyProved':False,'returnedObjectLengthOrArrayTypeProved':False,
  'boundary':'The fresh first signed-loop exit lands on every authenticated byte of a second opaque request/returned64 slot publication, post-store CALL, complete NOP and second signed EBX guard. The exact later root load addresses the same anonymous root storage as fresh setup. Current RCX must remain the selected first-guard root and EBX remain zero on initial entry; all callees must normally preserve carriers/frame and the published slot. Requested DWORD and later bound share a derived address only when root/class/static/count backing stays unchanged; no returned-array length, allocator/post-store helper meaning or live type follows. Nonnegative stable bound and all selected iteration/storage conditions remain explicit.'}


def check_defender_store(index,first_store,second,spec,a):
 from scripts.game_data.damage_snapshot_poise_attribute_flow import physical_ranges,check_provider_metadata
 _require(first_store.get('claim')=='poiseAttributeNormalDoubleToOldIndexStore' and second.get('claim')=='poiseSecondOpaquePointerPublicationAndSignedGuard','defender-store-fresh','fresh typed provider and second guard',[first_store.get('claim'),second.get('claim')])
 pointer=int(second['fragmentEnd'],16)+65;end=pointer+63;raw=index.pe.bytes_at_va(pointer,63);provider=first_store['actualProviderTarget'];backedge=second['actualSecondGuardEntry']
 _require(first_store['symbol']==second['symbol'],'defender-store-same-constructor','same actual constructor',first_store['symbol'])
 typed=check_provider_metadata(index,provider,spec)
 proof=store(raw,pointer,typed['selectedAttributeFieldOffset'],declaration({},a),provider,backedge)
 ranges=physical_ranges(index,pointer,end)
 return {**proof,**typed,'claim':'poiseDefenderOrdinaryDoubleToOldIndexSecondArrayStore','symbol':second['symbol'],'fragmentEntry':hex(pointer),'fragmentEnd':hex(end),'actualBackedge':backedge,'writeWidthBytes':8,'actualPhysicalPdataRanges':ranges,
  'tier':'conditional','managedUnwindFamilyProved':False,'boundary':'The complete actual defender fragment reads the declared ordinary Attributes field from compatible current R14 AbilitySystem, passes old EBX bits to the same actual ordinary Double/Int32-enum getter, and transfers normal XMM0 low64 unchanged into an eight-byte RDI array store. It forms the signextended old address before modulo32 EBX increment, then directly branches to the fresh second guard. Current defender/array origins, backing/layout, all raw predicates and normal provider/frame preservation remain conditions; enum labels, actual values and final Poise output remain open.'}


def check_defender_bridge(index,second,store_proof,spec,a):
 from scripts.game_data.damage_snapshot_poise_attribute_flow import physical_ranges
 _require(second.get('claim')=='poiseSecondOpaquePointerPublicationAndSignedGuard' and store_proof.get('claim')=='poiseDefenderOrdinaryDoubleToOldIndexSecondArrayStore','defender-loop-fresh','fresh second guard and actual typed store',[second.get('claim'),store_proof.get('claim')])
 pointer=int(second['fragmentEnd'],16);end=int(store_proof['fragmentEntry'],16)
 _require(end-pointer==65 and second['symbol']==store_proof['symbol'] and second['actualSecondGuardEntry']==store_proof['actualBackedge'],'defender-loop-continuity','same complete guard/store/backedge',[pointer,end])
 proof=bridge(index.pe.bytes_at_va(pointer,65),pointer,end,declaration(spec,a));ranges=physical_ranges(index,pointer,end)
 return {**proof,'claim':'poiseDefenderSecondArrayCarrierAndSelectedCycle','symbol':second['symbol'],'fragmentEntry':hex(pointer),'fragmentEnd':hex(end),'actualPhysicalPdataRanges':ranges,'tier':'conditional','managedUnwindFamilyProved':False,'guardToStoreSelectedFallthroughProved':True,
  'boundary':'Every selected bridge byte connects the fresh second signed guard to the typed defender field/getter/store and exact backedge. It loads the same published anonymous R15 qword slot into RDI, checks each null/class/signed-limit predicate and makes no call or EBX/R14 write. Unlike the first loop, its class comparison uses literal zero while EBX carries the second counter. Initial EBX zero, stable nonnegative signed bound and unchanged compatible carriers/frame/storage remain conditions; pointer/type/layout and live values are not inferred from helper names.'}


def check_constructor_footer(index,entry,first_guard,second,store_proof):
 from scripts.game_data.damage_snapshot_poise_attribute_flow import physical_ranges
 _require(entry.get('claim')=='poiseConstructorEntryFullWidthArgumentCarriersAndFrame' and first_guard.get('claim')=='poiseAttributeZeroIndexAndSignedGuard' and second.get('claim')=='poiseSecondOpaquePointerPublicationAndSignedGuard' and store_proof.get('claim')=='poiseDefenderOrdinaryDoubleToOldIndexSecondArrayStore','poise-footer-fresh','fresh actual frame, RSI spill, second exit and store',[entry.get('claim'),second.get('claim')])
 pointer=second['actualFooterEntry'];_require(pointer==int(store_proof['fragmentEnd'],16) and len({p['symbol'] for p in (entry,first_guard,second,store_proof)})==1,'poise-footer-same-exit','same actual selected footer and constructor',pointer)
 first_spill=int(first_guard['fragmentEntry'],16)+2
 _require(index.pe.bytes_at_va(first_spill,5)==b'\x48\x89\x74\x24\x50','poise-footer-rsi-original-spill','fresh actual caller RSI saved at current SP80',index.pe.bytes_at_va(first_spill,5).hex())
 proof=footer(index.pe.bytes_at_va(pointer,25),entry['entryFrameDeltaBytes']);ranges=physical_ranges(index,pointer,pointer+25)
 return {**proof,'claim':'poiseConstructorSelectedVoidRetAndSavedFrameRestore','symbol':entry['symbol'],'fragmentEntry':hex(pointer),'fragmentEnd':hex(pointer+25),'actualPhysicalPdataRanges':ranges,'tier':'conditional','managedUnwindFamilyProved':False,'declaredReturn':'fresh ordinary named constructor void',
  'boundary':'The actual second signed exit and defender-store fallthrough select this complete restoring footer. Exact RSI/RBX/RBP slots join the fresh first RSI spill and original entry saves, allocation is reversed and matching R15/R14/RDI pushes are popped before normal RET. The ordinary constructor declaration is void, so no return numeric value is claimed. Valid unchanged saved/pop/return slots and current frame continuity, original RSI preservation before its spill, compatible storage and all prior normal callee preservation remain conditions. RET pops the original return address and advances SP beyond entry by eight; this proves the selected footer, not all constructor paths or runtime return.'}
