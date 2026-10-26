"""Authenticate selected cached Double return; nested field meaning remains open."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require

def check_cached(raw,pointer,end,anonymous):
 forms=[b'\x8b\xcd',b'\xb8\x01\x00\x00\x00',b'\x83\xe1\x3f',b'\x48\xd3\xe0',b'\x83\xfb\x40','index-other-half',b'\x48\x85\x46'+bytes([anonymous['flagDisp8']]),b'\x0f\x97\xc0',b'\x84\xc0','nonzero-flag',b'\x48\x8b\x4e'+bytes([anonymous['arrayReferenceDisp8']]),b'\x48\x85\xc9','null-array',b'\x3b\x59'+bytes([anonymous['arrayLengthDisp8']]),'invalid-index',b'\xf2\x0f\x10\x44\xd9'+bytes([anonymous['arrayPayloadDisp8']]),b'\x0f\x28\x74\x24\x40',b'\x48\x8b\x7c\x24\x60',b'\x48\x8b\x5c\x24\x68',b'\x48\x8b\x6c\x24\x70',b'\x48\x83\xc4\x50',b'\x5e',b'\xc3']
 at=0;edges={}
 for form in forms:
  if isinstance(form,bytes):
   _require(raw[at:at+len(form)]==form,'attributes-cache-instruction',form.hex(),raw[at:at+len(form)].hex());size=len(form)
  else:
   opcode={'index-other-half':0x7d,'nonzero-flag':0x75,'null-array':0x84,'invalid-index':0x83}[form]
   size=2 if opcode in (0x7d,0x75) else 6;part=raw[at:at+size]
   prefix=bytes([opcode]) if size==2 else bytes([0x0f,opcode]);_require(len(part)==size and part.startswith(prefix),'attributes-cache-guard',form,part.hex())
   disp=int.from_bytes(part[1:] if size==2 else part[2:],'little',signed=True);target=pointer+at+size+disp
   _require(not pointer<=target<end,'attributes-cache-excluded','outside selected cache read/RET',target);edges[form]=target
  at+=size
 _require(at==len(raw) and pointer+at==end,'attributes-cache-full-return','complete selected bytes/RET',[at,len(raw),end])
 return {'selectedInstructionCount':len(forms),'selectedReturnWidth':'XMM0 low64 ordinary Double bits','selectedMask':'zeroextended EAX1 -> RAX64 shifted by (EBP low32 & 63)','flagSelection':'TEST64 clears CF; SETA AL is one iff ZF zero, then selected AL0 means tested bits zero','address':f"anonymous array RCX +{anonymous['arrayPayloadDisp8']}+signextended incoming index*8",'excludedTargets':edges,'nestedArrayFieldMeaningProved':False,'fullEntryOrOtherPathsProved':False,'conditions':['live RSI compatible selected receiver, RBX signextended parameter and EBP same low32 bits','signed index less than64 and unsigned index below anonymous array length','valid nonwrapping actual read address and compatible array backing/layout','valid saved-frame slots, unchanged frame and normal restoring RET']}


def check_poise_cached_attribute(index,store_proof,spec):
 from scripts.game_data.damage_snapshot_poise_attribute_flow import physical_ranges
 _require(store_proof.get('claim')=='poiseAttributeNormalDoubleToOldIndexStore','poise-cached-fresh-provider','fresh ordinary typed provider request',store_proof.get('claim'))
 owner,method=spec['providerSymbol'].rsplit('.',1);body=index.body(owner,method)
 _require(body.pointer==store_proof['actualProviderTarget'] and body.symbol==store_proof['providerSymbol'],'poise-cached-same-provider','same actual named ordinary Double provider',[body.pointer,body.symbol])
 marker=b'\x8b\xcd';candidates=[int(row['va'],16) for row in body.rows if bytes.fromhex(row['bytes'])==marker]
 _require(len(candidates)<=8,'poise-cached-candidate-bound','at most eight local transfers',len(candidates));matches=[];rejected=[]
 for pointer in candidates:
  try:
   ranges=physical_ranges(index,pointer,pointer+83);proof=check_cached(index.pe.bytes_at_va(pointer,83),pointer,pointer+83,spec['anonymousProgram']);matches.append((pointer,ranges,proof))
  except ValueError as exc:rejected.append({'pointer':hex(pointer),'reason':str(exc)[:256]})
 _require(len(matches)==1,'poise-cached-unique','one complete selected cache-read/RET',{'matchingCount':len(matches),'rejected':rejected})
 pointer,ranges,proof=matches[0]
 return {**proof,'symbol':body.symbol,'claim':'poiseAttributeSelectedCachedDoubleReturn','fragmentEntry':hex(pointer),'fragmentEnd':hex(pointer+83),'actualPhysicalPdataRanges':ranges,
  'boundary':'The fresh ordinary Double provider identity anchors an independent selected physical cache fragment. The exact full-width shift uses the masked low-six count; TEST clears carry, SETA reflects nonzero tested bits, and selected AL zero avoids the excluded branch. Nonnull anonymous array and unsigned count guards select an eight-byte load into the ordinary Double return register, followed by complete frame restoration and RET. Current RSI/RBX/EBP identity with the compatible receiver/parameter, valid nonwrapping array storage/layout and saved-frame continuity remain conditions. Nested typed cache/header interpretation, earlier entry-to-fragment CFG, all other provider paths, flag semantics or full Attributes.GetValue formula remain unproved; this is one conditional raw cached-return path, not proof every caller receives that cache value.'}


def check_prefix(raw,pointer,end,a):
 forms=[b'\x48\x89\x5c\x24\x10',b'\x48\x89\x6c\x24\x18',b'\x56',b'\x48\x83\xec\x50',b'\x48\x8b\xf1',b'\x48\x63\xda','root',b'\x0f\x57\xc0',b'\xf2\x0f\x11\x44\x24\x78',b'\x8b\xeb','class-zero-0',b'\x48\x8b\x81'+struct.pack('<i',a['staticCarrierDisp32']),b'\x48\x89\x7c\x24\x60',b'\x0f\x29\x74\x24\x40']
 for n,limit in enumerate(a['opaqueSignedLimits']):
  if n:forms+=['class-zero-'+str(n),b'\x48\x8b\x81'+struct.pack('<i',a['staticCarrierDisp32'])]
  forms += [b'\x48\x8b\x10',b'\x48\x85\xd2','null-'+str(n),b'\x81\x7a'+bytes([a['opaqueDwordDisp8']])+struct.pack('<i',limit),'limit-'+str(n)]
 # Each class condition represents two complete instructions.
 at=0;excluded={}
 for form in forms:
  if isinstance(form,bytes):
   _require(raw[at:at+len(form)]==form,'attributes-prefix-instruction',form.hex(),raw[at:at+len(form)].hex());size=len(form)
  elif form=='root':
   size=7;part=raw[at:at+size];_require(len(part)==7 and part[:3]==b'\x48\x8b\x0d','attributes-prefix-root','complete RIP qword load',part.hex())
  else:
   if form.startswith('class-zero'):
    cmp=b'\x83\xb9'+struct.pack('<i',a['classDwordDisp32'])+b'\x00'
    _require(raw[at:at+7]==cmp,'attributes-prefix-class','complete zero dword compare',raw[at:at+7].hex());at+=7
   size=6;opcode=0x8f if form.startswith('limit-') else 0x84;part=raw[at:at+size]
   _require(len(part)==size and part[:2]==bytes([0x0f,opcode]),'attributes-prefix-branch',form,part.hex());target=pointer+at+size+int.from_bytes(part[2:],'little',signed=True)
   _require(not pointer<=target<end,'attributes-prefix-excluded','outside selected prefix',target);excluded[form]=target
  at+=size
 _require(at==len(raw) and pointer+at==end,'attributes-prefix-complete','complete entry to cached fragment',[at,len(raw),end])
 return {'entryThisTransfer':'RCX full64 -> RSI','entryIndexTransfer':'EDX signedInt32 -> RBX full64; same low32 -> EBP','selectedCalls':[],'frameDelta':88,'actualExcludedTargets':excluded,'nestedHeaderMeaningProved':False,'guardSemanticsProved':False}


def check_complete_cached_path(prefix_raw,cached_raw,pointer,anonymous):
 _require(isinstance(anonymous.get('opaqueSignedLimits'),list) and len(anonymous['opaqueSignedLimits'])==3,'attributes-full-prefix-limits','three independently selected raw signed comparisons',anonymous.get('opaqueSignedLimits'))
 prefix_end=pointer+len(prefix_raw);end=prefix_end+len(cached_raw)
 prefix=check_prefix(prefix_raw,pointer,prefix_end,anonymous);cached=check_cached(cached_raw,prefix_end,end,anonymous)
 _require(len(prefix_raw)==184 and len(cached_raw)==83,'attributes-full-selected-span','complete supported entry and restoring cached path',[len(prefix_raw),len(cached_raw)])
 edges={**prefix['actualExcludedTargets'],**cached['excludedTargets']}
 _require(all(not pointer<=target<end for target in edges.values()),'attributes-full-excluded-targets','outside whole entry-to-RET selected path',edges)
 allocation=prefix_raw[14];frame=allocation+8
 _require(allocation==cached_raw[80] and prefix_raw[4]+frame==cached_raw[71] and prefix_raw[9]+frame==cached_raw[76] and prefix_raw[63]==cached_raw[66] and prefix_raw[68]==cached_raw[61],'attributes-full-save-restore','every exact saved value slot reloaded after same frame allocation',[allocation,frame])
 return {'selectedEntryToRetBytes':len(prefix_raw)+len(cached_raw),'selectedCalls':[],'entryThisTransfer':prefix['entryThisTransfer'],'entryIndexTransfer':prefix['entryIndexTransfer'],
  'actualExcludedTargets':edges,'frameAllocationBytes':allocation,'frameDeltaBytes':frame,
  'restoredNonvolatileGprs':['rbx','rbp','rdi','rsi'],'restoredXmm6WidthBytes':16,'untouchedNonvolatileGprs':['r12','r13','r14','r15'],
  'checkedCurrentStackSaveOffsets':{'rbx':cached_raw[71],'rbp':cached_raw[76],'rdi':cached_raw[66],'rsi':allocation,'xmm6':cached_raw[61],'zeroedTemporaryQword':prefix_raw[36]},
  'returnAddressOperation':'after allocation reversal and RSI pop, RET reads and pops original entry return address; post-return SP equals entry SP plus eight',
  'functionEntryToSelectedRetProved':True,'managedUnwindFamilyProved':False,'nestedHeaderMeaningProved':False,'otherPathsOrLiveSelectionProved':False}


def check_poise_cached_entry(index,store_proof,cached_proof,spec):
 from scripts.game_data.damage_snapshot_poise_attribute_flow import physical_ranges
 _require(store_proof.get('claim')=='poiseAttributeNormalDoubleToOldIndexStore' and cached_proof.get('claim')=='poiseAttributeSelectedCachedDoubleReturn','attributes-full-fresh-witnesses','fresh actual typed provider and complete cached RET',[store_proof.get('claim'),cached_proof.get('claim')])
 owner,method=spec['providerSymbol'].rsplit('.',1);body=index.body(owner,method)
 _require(body.pointer==store_proof['actualProviderTarget'] and body.symbol==cached_proof['symbol']==store_proof['providerSymbol'],'attributes-full-same-provider','same actual selected ordinary Double method',[body.pointer,body.symbol])
 prefix_end=int(cached_proof['fragmentEntry'],16);end=int(cached_proof['fragmentEnd'],16)
 _require(prefix_end-body.pointer==184 and end-prefix_end==83,'attributes-full-native-span','fresh complete prefix/cached RET spans',[body.pointer,prefix_end,end])
 ranges=physical_ranges(index,body.pointer,end)
 proof=check_complete_cached_path(index.pe.bytes_at_va(body.pointer,prefix_end-body.pointer),index.pe.bytes_at_va(prefix_end,end-prefix_end),body.pointer,spec['anonymousProgram'])
 return {**proof,'symbol':body.symbol,'claim':'poiseAttributeSelectedEntryCachedReturnAndSavedState','fragmentEntry':hex(body.pointer),'fragmentEnd':hex(end),'actualPhysicalPdataRanges':ranges,
  'boundary':'The fresh ordinary Double provider actual entry transfers its current this pointer to RSI and signextends incoming ordinary Int32 enum bits into RBX, with identical low32 EBP bits. Every selected opaque class/null/signed-limit predicate, direct fallthrough and full-width cache-mask/read instruction is checked from exact bytes through complete RET. The selected path makes no call. Each actually saved nonvolatile GPR and sixteen-byte XMM6 value is reloaded from its matching slot, allocation and pushed RSI are undone, and RET normally pops the original return address. Valid current-frame/shadow storage and noninterference, compatible receiver and anonymous array/layout backing, and all selected raw predicates remain conditions. Adjacent physical pdata ranges do not prove one managed unwind family. Nested typed header/cache fields, flag meanings, other paths and live method selection remain unresolved; the proof establishes one selected normal cached-bit return and saved-state relation, not full Attributes.GetValue formula semantics.'}
