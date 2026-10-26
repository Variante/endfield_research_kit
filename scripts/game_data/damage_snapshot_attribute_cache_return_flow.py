"""Prove opaque normal-return bits through anonymous header/cache publication."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require

def check(raw,pointer,end,a,opaque_limit):
 forms=['root',b'\x0f\x28\xf0',b'\x83\xb9'+struct.pack('<i',a['classDwordDisp32'])+b'\x00','class-zero',b'\x48\x8b\x81'+struct.pack('<i',a['staticCarrierDisp32']),b'\x48\x8b\x10',b'\x48\x85\xd2','null',b'\x81\x7a'+bytes([a['opaqueDwordDisp8']])+struct.pack('<i',opaque_limit),'limit',b'\x83\xe5\x3f',b'\x48\x8b\x46'+bytes([a['flagDisp8']]),b'\x83\xfb\x40','other-half',b'\x48\x0f\xb3\xe8',b'\x48\x89\x44\x24\x30',b'\x48\x8b\x46'+bytes([a['flagDisp8']+8]),b'\x48\x89\x44\x24\x38',b'\x0f\x10\x44\x24\x30']
 at=0;edges={}
 for form in forms:
  if isinstance(form,bytes):
   _require(raw[at:at+len(form)]==form,'cache-return-bridge-instruction',form.hex(),raw[at:at+len(form)].hex());size=len(form)
  elif form=='root':
   size=7;_require(len(raw[at:at+size])==size and raw[at:at+3]==b'\x48\x8b\x0d','cache-return-bridge-root','complete RIP qword load',raw[at:at+size].hex())
  else:
   size=2 if form=='other-half' else 6;prefix=b'\x7d' if size==2 else bytes([15,143 if form=='limit' else 132]);part=raw[at:at+size]
   _require(len(part)==size and part.startswith(prefix),'cache-return-bridge-guard',form,part.hex());target=pointer+at+size+int.from_bytes(part[len(prefix):],'little',signed=True)
   _require(not pointer<=target<end,'cache-return-bridge-excluded','outside whole bridge and store',target);edges[form]=target
  at+=size
 _require(at==90 and len(raw)==90,'cache-return-bridge-complete','complete selected ninety-byte prefix',[at,len(raw)])
 return {'normalCallXmm0ToSavedXmm6BitsProved':True,'rawBitClear':'BTR RAX64, RBP64 after EBP AND63 clears one bit of loaded anonymous first qword; second loaded qword is unchanged','rawHeaderValue':'two adjacent local qword stores then unaligned16B load into XMM0','entryIndexAndReceiverProved':False,'opaqueCalleeReturnMeaningProved':False,'excludedTargets':edges}


def check_attribute_cache_return_bridge(index,store,spec,a):
 from scripts.game_data.damage_snapshot_poise_attribute_flow import physical_ranges
 _require(store.get('claim')=='attributeAnonymousArrayEightBytePublicationAndRestoringReturn' and store.get('arrayWriteWidthBytes')==8,'cache-return-fresh-store','fresh complete actual eight-byte store/return',store.get('claim'))
 store_pointer=int(store['fragmentEntry'],16);end=int(store['fragmentEnd'],16);pointer=store_pointer-90
 ranges=physical_ranges(index,pointer-5,end)
 call=index.pe.bytes_at_va(pointer-5,5)
 _require(len(call)==5 and call[0]==0xe8,'cache-return-actual-call','complete immediately preceding direct CALL',call.hex())
 target=pointer+int.from_bytes(call[1:],'little',signed=True)
 proof=check(index.pe.bytes_at_va(pointer,90),pointer,end,a,spec['opaqueSignedLimit'])
 restoring=int(store['actualRestoringEntry'],16)
 _require(all(not restoring<=branch<restoring+26 for branch in proof['excludedTargets'].values()),'cache-return-excluded-footer','outside selected restoring footer',proof['excludedTargets'])
 return {**proof,'claim':'attributeOpaqueNormalReturnBitsThroughCachePublication','symbol':store['symbol'],'fragmentEntry':hex(pointer-5),'fragmentEnd':hex(end),'actualOpaqueCallTarget':hex(target),'actualPhysicalPdataRanges':ranges,
  'selectedCallerBytes':135,'tier':'conditional','opaqueReturnBitsToEightByteStoreAndNormalReturnProved':True,
  'boundary':'The complete actual direct CALL and every selected caller byte are authenticated independently. Conditional on that opaque callee normally returning with the current caller carriers/frame preserved, low64 XMM0 is copied to XMM6, remains unchanged through all selected opaque class/null/signed-limit and signed-index predicates, and reaches the fresh eight-byte array store and identical normal restoring return. Actual BTR64 with a masked low-six register index clears one bit of the anonymous first qword; the second qword is loaded separately and the resulting sixteen bytes are copied into the anonymous receiver header. Valid local/frame/heap storage and absence of interference from temporary, header or array writes remain conditions. The actual callee identity is a physical target; its declared/runtime return type, numeric computation, flag meanings, entry carrier origins, other paths and live output are unproved.'}
