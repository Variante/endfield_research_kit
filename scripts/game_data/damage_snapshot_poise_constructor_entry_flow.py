"""Prove actual named Poise constructor entry frame and full-width argument carriers."""
from scripts.game_data.damage_snapshot_cache_flow import _require

def check(raw,pointer):
 prefix=b'\x48\x89\x5c\x24\x10\x48\x89\x6c\x24\x18\x57\x41\x56\x41\x57\x48\x83\xec\x30\x80\x3d'
 _require(len(raw)==44 and raw[:21]==prefix and raw[25]==0 and raw[26:38]==b'\x49\x8b\xd9\x4d\x8b\xf0\x48\x8b\xea\x4c\x8b\xf9' and raw[38:40]==b'\x0f\x84','poise-ctor-entry-complete','complete saves/pushes/frame, anonymous byte compare, full64 argument copies and JZ',raw.hex())
 root=pointer+26+int.from_bytes(raw[21:25],'little',signed=True)
 excluded=pointer+44+int.from_bytes(raw[40:44],'little',signed=True)
 _require(not pointer<=excluded<pointer+44,'poise-ctor-entry-excluded','initializer edge outside complete selected entry',excluded)
 return {'selectedBytes':44,'anonymousInitializationByteStorage':root,'actualExcludedInitializer':excluded,'entryFrameDeltaBytes':72,
  'parameterCarrierTransfers':{'this':'RCX full64 -> R15','attacker':'RDX full64 -> RBP','defender':'R8 full64 -> R14','mask':'R9 full64 -> RBX'},
  'selectedEntryCalls':[],'savedPreEntryCarriers':{'rbx':'entrySP+16','rbp':'entrySP+24','rdi':'entrySP-8','r14':'entrySP-16','r15':'entrySP-24'},
  'laterR15PreservationOrFullConstructorCfgProved':False,'conditions':['entry ABI and valid frame/shadow slots','readable anonymous byte nonzero selects fallthrough; MOV transfers preserve its compare flags','later fragments must separately establish carrier/frame preservation and selected CFG']}


def check_poise_constructor_entry(index,request,spec):
 from scripts.game_data.damage_snapshot_poise_attribute_flow import physical_ranges
 _require(request.get('claim')=='poiseConstructorRequestAndNormalPackTransfer','poise-entry-fresh-request','fresh actual ordinary named constructor request',request.get('claim'))
 body=index.body(spec['packType'],'.ctor')
 _require(body.pointer==request['actualTargets']['ctor'],'poise-entry-same-target','same actual fresh constructor CALL target',[body.pointer,request['actualTargets']['ctor']])
 proof=check(index.pe.bytes_at_va(body.pointer,44),body.pointer)
 ranges=physical_ranges(index,body.pointer,body.pointer+44)
 location=index.parameter_location(body.pointer,body.symbol,'actionEnvironment')
 _require(location==('stack',40),'poise-entry-environment-abi','fresh named fifth native argument at callee entry stack40',location)
 return {**proof,'claim':'poiseConstructorEntryFullWidthArgumentCarriersAndFrame','symbol':body.symbol,'fragmentEntry':hex(body.pointer),'fragmentEnd':hex(body.pointer+44),'actualPhysicalPdataRanges':ranges,
  'tier':'conditional','thisToR15EntryTransferProved':True,'environmentEntryStackOffset':location[1],'conditionalEnvironmentCurrentStackOffset':location[1]+proof['entryFrameDeltaBytes'],'environmentLoadObservedInEntry':False,
  'boundary':'The actual named ordinary constructor target from the fresh typed request authenticates every byte of this complete entry fragment. Incoming this RCX becomes R15, attacker RDX becomes RBP, defender R8 becomes R14 and full64 enum mask R9 becomes RBX; the entry performs exact GPR saves, three pushes and a forty-eight-byte allocation. A readable anonymous byte nonzero selects the complete no-call fallthrough, with MOV transfers preserving compare flags; its initializer edge is excluded. Valid entry/frame/shadow storage and compatible request execution remain conditions. The authenticated fifth-argument ABI entry stack position plus actual frame delta gives only a conditional current-stack address; no environment load occurs in this prefix. Later carrier/frame preservation, path to pointer publication or loop, complete constructor return, typed header/field adjustment and live values remain open.'}
