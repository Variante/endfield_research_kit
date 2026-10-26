"""Independent exact anonymous cache publication slice; entry origins conditional."""
from scripts.game_data.damage_snapshot_cache_flow import _require

def check(raw, pointer, end, a, restoring_entry):
 forms=[b'\x48\x8b\x4e'+bytes([a['arrayReferenceDisp8']]),b'\x0f\x11\x46'+bytes([a['flagDisp8']]),b'\x48\x85\xc9','null',b'\x3b\x59'+bytes([a['arrayLengthDisp8']]),'bounds',b'\xf2\x0f\x11\x74\xd9'+bytes([a['arrayPayloadDisp8']]),b'\x0f\x28\xc6','return']
 at=0;excluded={}
 for form in forms:
  if isinstance(form,bytes):
   _require(raw[at:at+len(form)]==form,'cached-store-instruction',form.hex(),raw[at:at+len(form)].hex());size=len(form)
  else:
   size=5 if form=='return' else 6;part=raw[at:at+size];prefix=b'\xe9' if form=='return' else bytes([15,132 if form=='null' else 131])
   _require(len(part)==size and part.startswith(prefix),'cached-store-branch',form,part.hex())
   target=pointer+at+size+int.from_bytes(part[len(prefix):],'little',signed=True)
   if form=='return': _require(target==restoring_entry,'cached-store-restoring-target',restoring_entry,target)
   else:
    _require(not pointer<=target<end,'cached-store-excluded','outside complete selected slice',target);excluded[form]=target
  at+=size
 _require(at==40 and len(raw)==40 and end==pointer+at,'cached-store-complete','complete forty bytes',[at,len(raw),end])
 return {'rawAnonymousHeaderWriteWidthBytes':16,'arrayWriteWidthBytes':8,'arrayValueOrigin':'entry XMM6 low64','normalReturnValue':'same low64 transferred XMM6 to XMM0 before exact restoring-epilogue jump','otherPathsOrHeaderMeaningProved':False,'entryReceiverIndexAndValueOriginsProved':False,'excludedTargets':excluded}


def check_attribute_cache_store(index, entry, spec):
 from scripts.game_data.damage_snapshot_poise_attribute_flow import physical_ranges
 _require(entry.get('claim')=='poiseAttributeSelectedEntryCachedReturnAndSavedState' and entry.get('functionEntryToSelectedRetProved') is True, 'cached-store-fresh-return', 'fresh complete selected restoring path', entry.get('claim'))
 owner, method = spec['providerSymbol'].rsplit('.',1)
 body = index.body(owner,method)
 _require(body.pointer==int(entry['fragmentEntry'],16) and body.symbol==entry['symbol'], 'cached-store-same-provider', 'same actual selected ordinary Double provider', [body.pointer,body.symbol])
 end_return=int(entry['fragmentEnd'],16)
 footer=b'\x0f\x28\x74\x24\x40\x48\x8b\x7c\x24\x60\x48\x8b\x5c\x24\x68\x48\x8b\x6c\x24\x70\x48\x83\xc4\x50\x5e\xc3'
 restoring=end_return-len(footer)
 _require(index.pe.bytes_at_va(restoring,len(footer))==footer,'cached-store-fresh-footer','actual complete restoring footer',restoring)
 a=spec['anonymousProgram'];marker=b'\x48\x8b\x4e'+bytes([a['arrayReferenceDisp8']])
 candidates=[int(row['va'],16) for row in body.rows if bytes.fromhex(row['bytes'])==marker]
 _require(len(candidates)<=8,'cached-store-candidate-bound','at most eight local pointer reloads',len(candidates))
 matches=[];rejected=[]
 for pointer in candidates:
  try:
   ranges=physical_ranges(index,pointer,pointer+40)
   proof=check(index.pe.bytes_at_va(pointer,40),pointer,pointer+40,a,restoring)
   matches.append((pointer,ranges,proof))
  except ValueError as exc: rejected.append({'pointer':hex(pointer),'reason':str(exc)[:256]})
 _require(len(matches)==1,'cached-store-unique','one complete selected raw store/return jump',{'matchingCount':len(matches),'rejected':rejected})
 pointer,ranges,proof=matches[0]
 _require(all(not restoring<=target<end_return for target in proof['excludedTargets'].values()),'cached-store-excluded-footer','excluded paths outside selected restoring footer',proof['excludedTargets'])
 return {**proof,'claim':'attributeAnonymousArrayEightBytePublicationAndRestoringReturn','symbol':body.symbol,'fragmentEntry':hex(pointer),'fragmentEnd':hex(pointer+40),'actualRestoringEntry':hex(restoring),'actualPhysicalPdataRanges':ranges,
  'tier':'conditional','selectedSliceBytes':40,'sourceAndStoreAddressFormEqual':True,
  'sameAddressCondition':'same compatible RSI receiver, unchanged pointer at its anonymous array-reference displacement, same signextended RBX index, same array payload layout and nonwrapping backing',
  'boundary':'Every selected byte proves an anonymous pointer reload, physical sixteen-byte receiver-header write from entry XMM0, nonnull and unsigned-count guards, eight-byte entry-XMM6-low64 array write, identical XMM6-to-XMM0 return bits and a direct jump to the fresh complete saved-state restoring footer. No call occurs in this selected slice. RSI/RBX/XMM6 origins, current valid saved-frame storage and normal return, heap/header layout and noninterference remain conditions. A later selected cached read has the same address expression only when receiver, array pointer and signed index remain identical and neither header nor array backing interferes with them. Header/flag meanings, entry value generation, preceding selected CFG, live selection and final Poise result are unresolved.'}
