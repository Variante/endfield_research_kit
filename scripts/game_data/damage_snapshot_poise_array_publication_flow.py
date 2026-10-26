"""Prove opaque returned pointer publication into the selected Poise store carrier."""
from scripts.game_data.damage_snapshot_cache_flow import _require

def check(raw,pointer,slot):
 _require(len(raw)==27 and raw[:3]==b'\x48\x8b\x0d' and raw[7:9]==b'\x8b\x10' and raw[9]==0xe8 and raw[14:18]==b'\x49\x8d\x4f'+bytes([slot]) and raw[18:22]==b'\x49\x89\x47'+bytes([slot]) and raw[22]==0xe8,'poise-factory-publication-complete','root qword/count load, direct call, slot address and returned64 store, direct post-store call',raw.hex())
 root=pointer+7+int.from_bytes(raw[3:7],'little',signed=True)
 factory=pointer+14+int.from_bytes(raw[10:14],'little',signed=True)
 after=pointer+27+int.from_bytes(raw[23:27],'little',signed=True)
 return {'actualRootStorage':root,'actualOpaqueFactoryTarget':factory,'actualOpaquePostStoreTarget':after,'writtenBits':'first normal call RAX full64 -> anonymous R15 qword slot','postStoreRequest':'RCX receives actual slot address before full64 RAX publication and post-store direct CALL','declaredArrayAllocationOrHeapLayoutProved':False,'conditions':['RAX before countload is valid anonymous dword carrier; selected RIP qword readable','factory normally returns and preserves compatible R15/frame; slot write valid','post-store opaque callee returns preserving R15 and published slot through fresh guard/bridge read','published pointer has compatible backing for subsequent selected array operations']}


def check_poise_array_publication(index,guard,bridge,a):
 from scripts.game_data.damage_snapshot_poise_attribute_flow import physical_ranges
 _require(guard.get('claim')=='poiseAttributeZeroIndexAndSignedGuard' and bridge.get('claim')=='poiseAttributeGuardArrayCarrierAndSelectedLoopJoin' and bridge.get('guardToStoreSelectedFallthroughProved') is True and bridge.get('explicitCalls')==[], 'poise-publication-fresh-cycle','fresh actual zero guard and no-call slot-read bridge',[guard.get('claim'),bridge.get('claim')])
 _require(guard['symbol']==bridge['symbol'] and int(guard['fragmentEnd'],16)==int(bridge['fragmentEntry'],16),'poise-publication-same-cycle','same actual guard fallthrough and slot read',bridge['symbol'])
 end=int(guard['fragmentEntry'],16);pointer=end-27
 ranges=physical_ranges(index,pointer,end)
 proof=check(index.pe.bytes_at_va(pointer,27),pointer,a['arrayCarrierDisp8'])
 reader=int(bridge['fragmentEntry'],16)
 _require(index.pe.bytes_at_va(reader,4)==b'\x49\x8b\x77'+bytes([a['arrayCarrierDisp8']]),'poise-publication-same-slot','fresh actual R15 slot to RSI read',index.pe.bytes_at_va(reader,4).hex())
 return {**proof,'claim':'poiseOpaqueNormalPointerPublicationToSelectedArrayCarrier','symbol':guard['symbol'],'fragmentEntry':hex(pointer),'fragmentEnd':hex(end),'actualSelectedSlotRead':hex(reader),'actualPhysicalPdataRanges':ranges,
  'tier':'conditional','normalReturnedBitsToArrayCarrierReadProved':True,'typedArrayOrHeaderLayoutProved':False,
  'boundary':'Every byte in the preceding twenty-seven-byte physical slice proves anonymous RIP qword and dword argument loads, an actual direct opaque CALL, slot-address preparation and full64 returned-RAX publication, followed by an actual opaque post-store CALL. Its normal continuation falls directly into the fresh complete zero-index/signed guard and no-call bridge that reads the identical anonymous R15 slot into RSI for the selected eight-byte indexed store. The two opaque calls must return normally preserving the compatible carrier/frame; the post-store call and all temporary/storage writes must preserve the published slot until that read. Valid pointer backing/layout and all selected guard/provider conditions remain explicit. Neither callee is assigned allocator or write-barrier semantics; typeinfo/root meaning, declared array type, nested/header adjustment, original constructor receiver origin and live output remain open.'}
