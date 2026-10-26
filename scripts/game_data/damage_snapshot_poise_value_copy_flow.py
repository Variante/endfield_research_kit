"""Conditional same-index source-read to producer-store connection."""
from scripts.game_data.damage_snapshot_cache_flow import _require

def link(store,entry):
 _require(store.get('claim')=='poiseAttributeNormalDoubleToOldIndexStore' and entry.get('claim')=='poiseAttributeSelectedEntryCachedReturnAndSavedState','poise-value-copy-fresh-claims','fresh local store and full actual provider path',[store.get('claim'),entry.get('claim')])
 _require(store['providerSymbol']==entry['symbol'] and store['actualProviderTarget']==int(entry['fragmentEntry'],16),'poise-value-copy-actual-target','same actual typed provider',[store['providerSymbol'],entry['symbol']])
 _require(entry.get('functionEntryToSelectedRetProved') is True and entry.get('selectedCalls')==[] and {'rdi','rsi'}.issubset(entry.get('restoredNonvolatileGprs',[])) and store.get('writeWidthBytes')==8,'poise-value-copy-state','actual complete selected return restores destination/index carriers',[entry.get('restoredNonvolatileGprs'),store.get('writeWidthBytes')])
 return {'tier':'conditional','indexConnection':'caller EDI low32 -> provider EDX low32 -> signextended RBX for source read; actual restored RDI -> caller EDI -> signextended old RAX for destination store before increment changes EDI',
  'valueConnection':'source eight-byte memory load -> XMM0 low64 -> normal RET -> caller unchanged XMM0 -> destination eight-byte store',
  'noNumericConversionBetweenLoadAndStore':True,'sourceNestedArrayTypeProved':False,'destinationArrayTypeProved':False,'liveProviderValuesOrFinalPoiseOutputProved':False,
  'conditions':['actual native CALL enters the full proved selected provider path and all source/destination predicates select','valid unchanged caller/callee frame and saved-state storage, compatible current receiver/carriers and no interference','anonymous source/destination array addresses/layout permit the actual eight-byte read and write','the same old Int32 bits supply each request; actual array contents and enum member names are unmeasured']}

def index_addresses(source,destination,bits,source_payload,destination_payload):
 _require(all(type(n) is int for n in (source,destination,bits,source_payload,destination_payload)) and 0<=bits<2**32,'poise-value-copy-address-input','integer bases/payloads and UInt32 bits',[source,destination,bits])
 signed=bits if bits<2**31 else bits-2**32
 src=source+source_payload+8*signed;dst=destination+destination_payload+8*signed
 return {'oldIndexBits':bits,'signedOldIndex':signed,'sourceAddress':src,'destinationAddress':dst,'nextIndexBits':(bits+1)%2**32,'validNonwrappingEightByteSpans':all(0<=a<2**64 for a in (source,destination)) and all(0<=a and a+8<=2**64 for a in (src,dst)),'liveBackingObserved':False}


def check_poise_value_copy(store, entry, source_spec, destination_spec):
 proof = link(store, entry)
 source = source_spec['anonymousProgram']
 destination = destination_spec['anonymousProgram']
 for declaration in (source, destination):
  _require(type(declaration['arrayPayloadDisp8']) is int and 0 <= declaration['arrayPayloadDisp8'] < 128, 'poise-value-copy-payload', 'reviewed positive disp8 payload', declaration['arrayPayloadDisp8'])
 return {**proof, 'claim': 'poiseAttributeSelectedCachedBitsToSameOldIndexStore',
  'symbol': store['providerSymbol'], 'actualProviderTarget': store['actualProviderTarget'],
  'sourcePayloadDisplacement': source['arrayPayloadDisp8'], 'destinationPayloadDisplacement': destination['arrayPayloadDisp8'],
  'sourceAddressExpression': 'sourceArray + sourcePayloadDisplacement + 8 * signedInt32(oldEDI)',
  'destinationAddressExpression': 'destinationArray + destinationPayloadDisplacement + 8 * signedInt32(oldEDI)',
  'boundary': 'Fresh complete actual provider entry/RET and caller request/store witnesses connect the same old Int32 bits and unchanged low64 XMM0 bits. This conditional read-at-call-time to write relation requires the selected normal cached path, valid nonwrapping array and frame storage, compatible current receiver/carriers and noninterference. Anonymous arrays, nested/header type interpretation, enum labels, actual values and final Poise output remain unproved.'}
