"""Prove the selected second anonymous-word bit operation and exact shared tail."""
from scripts.game_data.damage_snapshot_cache_flow import _require

def check(raw,pointer,a,target):
 expected=b'\x48\x89\x44\x24\x30\x48\x8b\x46'+bytes([a['flagDisp8']+8])+b'\x48\x0f\xb3\xe8\xeb'
 _require(len(raw)==15 and raw[:14]==expected,'cache-second-half-complete','first-word spill, second-word load, BTR64, complete short jump',raw.hex())
 actual=pointer+15+int.from_bytes(raw[-1:],'little',signed=True)
 _require(actual==target,'cache-second-half-tail','same fresh second-word spill/load/header/store tail',actual)
 return {'selectedBytes':15,'firstAnonymousQwordUnchangedToLocal':True,'secondAnonymousQwordMaskedBitCleared':True,'typedFlagMeaningProved':False,'indexCondition':'prior EBP low32 masked to63 and signed EBX >=64; later unsigned array-count guard still required','valueCarrier':'XMM6 untouched by every selected instruction'}


def join(bridge,raw,pointer,a):
 _require(bridge.get('claim')=='attributeOpaqueNormalReturnBitsThroughCachePublication','cache-second-half-fresh','fresh actual CALL/prefix/store relation',bridge.get('claim'))
 _require(pointer==bridge['excludedTargets']['other-half'],'cache-second-half-selected-edge','actual selected signed JGE target',pointer)
 tail=int(bridge['fragmentEnd'],16)-50
 proof=check(raw,pointer,a,tail)
 return {**proof,'tier':'conditional','normalOpaqueReturnBitsStillReachStore':True,'sourceCounterNonnegativeOrLess128Proved':False,
  'conditions':['all preceding prefix guards select, except signed index>=64 selects this actual edge','actual normal opaque callee return/frame/carriers and XMM6 capture conditions remain','common tail temporary/header/array storage is valid and noninterfering; same unsigned count guard selects','first qword is unchanged, second qword bit index is masked low-six; index may exceed127']}


def check_attribute_cache_second_half(index,bridge,a):
 from scripts.game_data.damage_snapshot_poise_attribute_flow import physical_ranges
 _require(bridge.get('normalCallXmm0ToSavedXmm6BitsProved') is True and bridge.get('selectedCallerBytes')==135,'cache-second-half-complete-witness','fresh complete CALL/prefix/store witness',[bridge.get('selectedCallerBytes'),bridge.get('normalCallXmm0ToSavedXmm6BitsProved')])
 pointer=bridge['excludedTargets']['other-half'];tail=int(bridge['fragmentEnd'],16)-50
 common=b'\x48\x89\x44\x24\x38\x0f\x10\x44\x24\x30'
 _require(index.pe.bytes_at_va(tail,10)==common,'cache-second-half-common-tail','complete second-word spill and sixteen-byte temporary reload',index.pe.bytes_at_va(tail,10).hex())
 ranges=physical_ranges(index,pointer,pointer+15)
 proof=join(bridge,index.pe.bytes_at_va(pointer,15),pointer,a)
 _require(all(not pointer<=target<pointer+15 for name,target in bridge['excludedTargets'].items() if name!='other-half'),'cache-second-half-other-excluded','other guards outside selected alternative fragment',bridge['excludedTargets'])
 return {**proof,'claim':'attributeSecondAnonymousWordBitClearAndSameCacheReturnTail','symbol':bridge['symbol'],'fragmentEntry':hex(pointer),'fragmentEnd':hex(pointer+15),'actualCommonTail':hex(tail),'actualPhysicalPdataRanges':ranges,
  'boundary':'The fresh preceding CALL/caller prefix supplies the actual signed-index other-half edge and masked EBP bit index. All fifteen bytes at that edge preserve XMM6, spill the unchanged first anonymous qword, load and BTR64-clear one masked bit in the second qword, and jump exactly to the authenticated second-word spill/temporary reload and fresh common header/array-store/restoring-return tail. This conditional alternate path requires signed EBX at least64, all other preceding guards, normal opaque-call return with preserved carriers/frame, valid backing and noninterference. The raw selection does not prove index below128 or nonnegative origins generally. Flag names, nested layouts, opaque numeric generation, other paths and live results remain open.'}
