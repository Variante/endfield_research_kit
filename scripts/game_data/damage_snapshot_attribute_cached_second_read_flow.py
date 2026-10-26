"""Prove the second anonymous-word selection into the complete cached return."""
from scripts.game_data.damage_snapshot_cache_flow import _require

def check(raw,pointer,expected_target,second_word_disp):
 expected=b'\x48\x85\x46'+bytes([second_word_disp])+b'\xeb'
 _require(len(raw)==6 and raw[:5]==expected,'cache-second-read-complete','complete TEST64 secondword,RAX and short JMP',raw.hex())
 actual=pointer+6+int.from_bytes(raw[-1:],'little',signed=True)
 _require(actual==expected_target,'cache-second-read-common-tail','exact fresh SETA/common-cache-read/footer entry',actual)
 return {'selectedBytes':6,'flagMeaningProved':False,'carryClearedByTest':True,'normalReturnSelection':'TEST64 clears CF; subsequent fresh SETA AL reflects nonzero tested bits; selected AL0 enters same cache read and restoring return','conditions':['signed incoming index at least64; mask remains one shifted by low-six bits','same current receiver/array/index and valid saved-frame/read backing; all other raw entry predicates select','anonymous second-word bit names and index upper limit remain open']}


def check_attribute_cached_second_read(index,entry,a):
 from scripts.game_data.damage_snapshot_poise_attribute_flow import physical_ranges
 _require(entry.get('claim')=='poiseAttributeSelectedEntryCachedReturnAndSavedState' and entry.get('functionEntryToSelectedRetProved') is True and entry.get('selectedEntryToRetBytes')==267,'cache-second-read-fresh-entry','fresh complete actual entry/cache read/restoring RET',entry.get('claim'))
 pointer=entry['actualExcludedTargets']['index-other-half'];common=int(entry['fragmentEnd'],16)-61
 _require(index.pe.bytes_at_va(common,3)==b'\x0f\x97\xc0','cache-second-read-seta','actual common SETA AL',index.pe.bytes_at_va(common,3).hex())
 ranges=physical_ranges(index,pointer,pointer+6)
 proof=check(index.pe.bytes_at_va(pointer,6),pointer,common,a['flagDisp8']+8)
 _require(all(not pointer<=target<pointer+6 for name,target in entry['actualExcludedTargets'].items() if name!='index-other-half'),'cache-second-read-other-excluded','other excluded guards outside alternate selected slice',entry['actualExcludedTargets'])
 return {**proof,'claim':'attributeSelectedEntrySecondAnonymousWordCachedReturn','symbol':entry['symbol'],'fragmentEntry':hex(pointer),'fragmentEnd':hex(pointer+6),'actualCommonReturnPath':hex(common),'actualPhysicalPdataRanges':ranges,
  'tier':'conditional','completeEntryToSelectedRetProved':True,'otherPathsOrLiveSelectionProved':False,'indexBelow128Proved':False,
  'boundary':'The fresh complete actual entry path supplies the same incoming ordinary Int32 signextended RBX and masked one-bit RAX. Its actual signed-index other-half branch selects this complete six-byte TEST64 of the second anonymous qword and direct jump into the authenticated SETA AL/common guarded eight-byte array load and complete saved-state restoring RET. TEST clears carry; selected AL zero selects the normal cached bits. All remaining entry predicates, compatible current receiver/index, valid heap/frame storage and noninterference remain conditions. Signed index at least64 does not prove index below128. Anonymous flag meanings, nested layout, actual values, all other paths and live output remain unproved.'}
