"""Authenticate typed attribute request and old-index Double store."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.il2cpp.context import relative_branch_target

def check_store(rows,pointer,end,attributes_offset,provider,backedge,anonymous):
 forms=[b'\x48\x8b\x85'+struct.pack('<i',attributes_offset),b'\x48\x85\xc0','null-source',b'\x45\x33\xc0',b'\x8b\xd7',b'\x48\x8b\xc8','provider',b'\x48\x85\xf6','null-array',b'\x3b\x7e'+bytes([anonymous['arrayLengthDisp8']]),'unsigned-bounds',b'\x48\x63\xc7',b'\xff\xc7',b'\xf2\x0f\x11\x44\xc6'+bytes([anonymous['arrayPayloadDisp8']]),'backedge']
 _require(len(rows)==len(forms),'poise-attribute-length',len(forms),len(rows));at=pointer;excluded={}
 for row,form in zip(rows,forms):
  raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at,'poise-attribute-contiguity',at,row['va'])
  if isinstance(form,bytes):_require(raw==form,'poise-attribute-instruction',form.hex(),raw.hex())
  elif form in ('provider','backedge'):
   expected=0xe8 if form=='provider' else 0xe9;_require(len(raw)==5 and raw[0]==expected,'poise-attribute-direct','complete direct instruction',raw.hex());target=relative_branch_target(raw,at,source='poiseAttribute')
   _require(target==(provider if form=='provider' else backedge),'poise-attribute-target',form,target)
  else:
   opcode=0x83 if form=='unsigned-bounds' else 0x84
   _require(len(raw)==6 and raw[:2]==bytes([0x0f,opcode]),'poise-attribute-guard',form,raw.hex());target=at+6+int.from_bytes(raw[2:],'little',signed=True)
   _require(not pointer<=target<end,'poise-attribute-excluded','outside selected fragment',target);excluded[form]=target
  at+=len(raw)
 _require(at==end,'poise-attribute-complete',end,at)
 return {'writeWidthBytes':8,'oldIndexOrigin':'EDI Int32 before INC -> signextended RAX; address uses old RAX after EDI increments','indexAdvance':'EDI modulo32 +1, separate from old signextended address index','source':'normal ordinary Double provider XMM0 low64','excludedTargets':excluded,'actualBackedge':backedge,'enumMemberMeaningProved':False,'runtimeArrayLayoutProved':False}

def store_address(base,index_bits,payload):
 _require(type(base) is int and type(index_bits) is int and 0<=index_bits<2**32,'poise-attribute-address-input','base and unsigned Int32 bits',[base,index_bits])
 signed=index_bits if index_bits<2**31 else index_bits-2**32;address=base+payload+8*signed
 return {'signedOldIndex':signed,'address':address,'nonwrapping':0<=base<2**64 and 0<=address and address+8<=2**64,'nextIndexBits':(index_bits+1)%2**32}


def check_provider_metadata(index,provider,spec):
 from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_field,require_ordinary_int32_enum
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 selected=NativeReferenceContext(index.image,index=index)
 owner,typ,offset=selected.field(spec['attributesField'])
 _require((owner,typ)==(spec['abilityType'],spec['attributesType']),'poise-attribute-owner',[spec['abilityType'],spec['attributesType']],[owner,typ])
 require_ordinary_field(selected,spec['attributesField'],typ,'poise.attribute.sourceField')
 methods=[index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(provider,()) if f"{r.get('type')}.{r.get('method')}"==spec['providerSymbol']]
 _require(bool(methods) and all(not m.flags&0x10 for m in methods),'poise-attribute-provider-instance','named ordinary instance provider',provider)
 for method in methods:
  args=index.metadata.parameters_for(method);_require(len(args)==1,'poise-attribute-provider-arity',1,len(args))
  require_ordinary_type(selected,method.return_type,'double','poise.attribute.provider.return')
  require_ordinary_int32_enum(selected,args[0].type_index,spec['attributeEnum'],'poise.attribute.provider.index')
 for name,location in (('this',('register','rcx')),('attributeType',('register','rdx'))):
  _require(index.parameter_location(provider,spec['providerSymbol'],name)==location,'poise-attribute-provider-abi',[name,location],index.parameter_location(provider,spec['providerSymbol'],name))
 return {'selectedAttributeFieldOffset':offset,'providerBodySemanticsProved':False,'providerSymbol':spec['providerSymbol'],'actualProviderTarget':provider}


def check_guard(raw,pointer,end,backedge,anonymous):
 prefix=b'\x33\xdb\x48\x89\x74\x24\x50\x8b\xfb\x66\x66\x0f\x1f\x84\x00\x00\x00\x00\x00'
 _require(len(raw)==49 and raw[:19]==prefix and pointer+49==end,'poise-attribute-init','EBX0/EDI0/full ten-byte NOP',raw.hex())
 _require(backedge==pointer+19,'poise-attribute-backedge-entry','exact same guarded loop entry',backedge)
 _require(raw[19:22]==b'\x48\x8b\x0d' and raw[26:32]==b'\x39\x99'+struct.pack('<i',anonymous['classDwordDisp32']) and raw[32:34]==b'\x0f\x84','poise-attribute-static-guard','opaque RIP pointer and nonzero dword path',raw.hex())
 cold=pointer+38+int.from_bytes(raw[34:38],'little',signed=True)
 _require(not pointer<=cold<end,'poise-attribute-static-excluded','outside selected init/guard',cold)
 _require(raw[38:45]==b'\x48\x8b\x81'+struct.pack('<i',anonymous['staticCarrierDisp32']) and raw[45:47]==b'\x3b\x38' and raw[47]==0x7d,'poise-attribute-signed-bound','opaque bound carrier and signed JGE',raw.hex())
 exit_target=end+int.from_bytes(raw[48:49],'little',signed=True)
 return {'initialIndexBits':0,'actualLoopEntry':backedge,'actualSignedBoundExit':exit_target,'excludedStaticInitializer':cold,'boundFieldNameProved':False,'finiteSelectedIterationCondition':'stable signed Int32 bound N between zero and INT32_MAX, same guarded backedge, all other selected guards/provider normal returns and no index/array/receiver mutation; then selected old indices are zero through N-1 and increment does not overflow signed32'}


def physical_ranges(index,start,end):
 _require(type(start) is int and type(end) is int and start<end and end-start<=4096,'poise-physical-span','bounded nonempty span',[start,end])
 at=start;ranges=[]
 while at<end:
  owners=[(entry,limit) for entry,limit in index.extents.items() if entry<=at<limit]
  _require(len(owners)==1,'poise-physical-owner','one actual pdata range at each byte',[at,owners])
  entry,limit=owners[0];_require(0<limit-entry<=65536,'poise-physical-owner-size','bounded pdata',owners[0]);ranges.append([hex(entry),hex(limit)]);at=min(limit,end)
  _require(len(ranges)<=4,'poise-physical-partition-count','at most four actual ranges',ranges)
 return ranges


def check_poise_attribute_store(index,ctor_proof,spec):
 from scripts.game_data.damage_snapshot_poise_copy_flow import _partition
 _require(ctor_proof.get('claim')=='poiseConstructorRequestAndNormalPackTransfer','poise-attribute-fresh-ctor','fresh actual named constructor request',ctor_proof.get('claim'))
 body=index.body(spec['packType'],'.ctor')
 _require(body.pointer==ctor_proof['actualTargets']['ctor'],'poise-attribute-actual-entry','same fresh actual request target',body.pointer)
 selected_field=spec['attributesField'];owner,name=selected_field.split('::')
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 selected=NativeReferenceContext(index.image,index=index);field_owner,field_type,offset=selected.field(selected_field)
 _require((field_owner,field_type)==(spec['abilityType'],spec['attributesType']),'poise-attribute-source-owner',[spec['abilityType'],spec['attributesType']],[field_owner,field_type])
 marker=b'\x48\x8b\x85'+struct.pack('<i',offset)
 candidates=[int(row['va'],16) for row in body.rows if bytes.fromhex(row['bytes'])==marker]
 _require(len(candidates)<=8,'poise-attribute-candidate-bound','at most eight local field reads',len(candidates));matches=[];rejected=[]
 for pointer in candidates:
  try:
   ranges=physical_ranges(index,pointer,pointer+63);raw=index.pe.bytes_at_va(pointer,63)
   provider=relative_branch_target(raw[24:29],pointer+24,source='poiseAttributeProvider')
   backedge=relative_branch_target(raw[58:63],pointer+58,source='poiseAttributeBackedge')
   proof=check_store(_partition(raw,pointer,[7,3,6,3,2,3,5,3,6,3,6,3,2,6,5]),pointer,pointer+63,offset,provider,backedge,spec['anonymousProgram'])
   typed=check_provider_metadata(index,provider,spec);matches.append((pointer,ranges,proof,typed))
  except ValueError as exc:rejected.append({'pointer':hex(pointer),'reason':str(exc)[:256]})
 _require(len(matches)==1,'poise-attribute-unique','one complete typed provider and old-index store',{'matchingCount':len(matches),'rejected':rejected})
 pointer,ranges,proof,typed=matches[0]
 return {**proof,**typed,'symbol':body.symbol,'claim':'poiseAttributeNormalDoubleToOldIndexStore','fragmentEntry':hex(pointer),'fragmentEnd':hex(pointer+63),'actualPhysicalPdataRanges':ranges,
  'inputCarrierOriginProved':False,'arrayTypeOrNestedHeaderProved':False,
  'boundary':'A fresh actual named constructor target anchors this independent local physical fragment. Conditional on live RBP being the compatible AbilitySystem carrier, its declared ordinary Attributes field supplies the actual ordinary instance GetValue receiver, and EDI bits supply its ordinary Int32 enum argument. Normal ordinary Double XMM0 low64 passes unchanged through the null/unsigned count guards and signextended old-index address into an actual eight-byte store. EDI increments after old RAX is formed; the direct backedge target is exact. Every byte is covered by actual physical pdata ranges, without inferring same managed unwind ownership from adjacency. The carrier origins, array type/nested header/payload layout, valid nonwrapping storage, normal Win64 nonvolatile preservation and complete surrounding CFG remain conditions or unresolved; enum-member meanings, full constructor behavior, snapshot compact/consumer index correspondence and final Poise values are not inferred.'}


def check_poise_attribute_guard(index,store_proof,spec):
 _require(store_proof.get('claim')=='poiseAttributeNormalDoubleToOldIndexStore','poise-guard-fresh-store','fresh exact backedge',store_proof.get('claim'))
 body=index.body(spec['packType'],'.ctor');_require(body.symbol==store_proof['symbol'],'poise-guard-same-anchor',body.symbol,store_proof['symbol'])
 backedge=store_proof['actualBackedge'];pointer=backedge-19;end=pointer+49
 ranges=physical_ranges(index,pointer,end);proof=check_guard(index.pe.bytes_at_va(pointer,49),pointer,end,backedge,spec['anonymousProgram'])
 return {**proof,'symbol':body.symbol,'claim':'poiseAttributeZeroIndexAndSignedGuard','fragmentEntry':hex(pointer),'fragmentEnd':hex(end),'actualPhysicalPdataRanges':ranges,'guardToStoreCfgProved':False,
  'boundary':'The fresh store backedge lands exactly after independently checked zero-index initialization and complete NOP framing, at the selected anonymous class/opaque signed-bound guard. Every selected branch and physical pdata byte range is authenticated. Stable nonnegative signed Int32 bound, ordinary valid storage, the unproved guard-to-store route, preservation of index/array/receiver carriers and all other selected guards/normal returns are explicit recurrence conditions. The local guard and store are separate witnesses; this does not establish full loop CFG, runtime finite execution, bound meaning, concrete enum members or snapshot/consumer index correspondence.'}


def check_bridge_bytes(raw,pointer,end,anonymous):
 forms=[b'\x49\x8b\x77'+bytes([anonymous['arrayCarrierDisp8']]),b'\x48\x85\xed','null-actor','root',b'\x39\x99'+struct.pack('<i',anonymous['classDwordDisp32']),'class-zero',b'\x48\x8b\x81'+struct.pack('<i',anonymous['staticCarrierDisp32']),b'\x48\x8b\x10',b'\x48\x85\xd2','null-opaque',b'\x81\x7a'+bytes([anonymous['opaqueDwordDisp8']])+struct.pack('<i',anonymous['opaqueSignedLimit']),'signed-limit']
 at=0;excluded={}
 for form in forms:
  if isinstance(form,bytes):
   _require(raw[at:at+len(form)]==form,'poise-bridge-instruction',form.hex(),raw[at:at+len(form)].hex());size=len(form)
  elif form=='root':
   size=7;part=raw[at:at+size];_require(len(part)==size and part[:3]==b'\x48\x8b\x0d','poise-bridge-root','complete anonymous RIP qword load',part.hex())
  else:
   size=6;opcode=0x8f if form=='signed-limit' else 0x84;part=raw[at:at+size]
   _require(len(part)==size and part[:2]==bytes([0x0f,opcode]),'poise-bridge-excluded-guard',form,part.hex());target=pointer+at+size+int.from_bytes(part[2:],'little',signed=True)
   _require(not pointer<=target<end,'poise-bridge-excluded-target','outside complete selected bridge',target);excluded[form]=target
  at+=size
 _require(at==len(raw) and pointer+at==end,'poise-bridge-complete','whole guard-to-store selected fallthrough',[at,len(raw),end])
 return {'selectedInstructionCount':len(forms),'actualExcludedTargets':excluded,'explicitCalls':[],'indexCarrierModified':False,'sourceActorCarrierModified':False,
  'arrayCarrierTransfer':'anonymous R15 qword slot -> RSI; selected bridge contains no later RSI writes',
  'classComparisonCondition':'EBX remains the fresh zero carrier; anonymous class dword differs from EBX',
  'opaqueLimitCondition':'nonnull anonymous pointer and signed Int32 dword no greater than reviewed anonymous limit'}


def check_poise_attribute_bridge(index,store_proof,guard_proof,spec):
 _require(store_proof.get('claim')=='poiseAttributeNormalDoubleToOldIndexStore' and guard_proof.get('claim')=='poiseAttributeZeroIndexAndSignedGuard','poise-bridge-fresh-witnesses','fresh local store and actual signed guard',[store_proof.get('claim'),guard_proof.get('claim')])
 _require(store_proof['symbol']==guard_proof['symbol'] and store_proof['actualBackedge']==guard_proof['actualLoopEntry'] and guard_proof['initialIndexBits']==0,'poise-bridge-same-loop','same actual guarded backedge and zero initialization',[store_proof['symbol'],guard_proof['symbol']])
 pointer=int(guard_proof['fragmentEnd'],16);end=int(store_proof['fragmentEntry'],16)
 _require(end-pointer==64,'poise-bridge-span','bounded complete selected bridge',end-pointer)
 ranges=physical_ranges(index,pointer,end);proof=check_bridge_bytes(index.pe.bytes_at_va(pointer,end-pointer),pointer,end,spec['anonymousProgram'])
 return {**proof,'symbol':store_proof['symbol'],'claim':'poiseAttributeGuardArrayCarrierAndSelectedLoopJoin','fragmentEntry':hex(pointer),'fragmentEnd':hex(end),'actualPhysicalPdataRanges':ranges,
  'guardToStoreSelectedFallthroughProved':True,'fullEntryCarrierOriginProved':False,'arrayTypeOrNestedHeaderProved':False,
  'finiteSelectedRecurrenceTier':'conditional',
  'boundary':'The fresh signed-bound fallthrough connects through every actual byte of this independent bridge to the fresh Attributes field/provider/store fragment. The anonymous value-carrier qword supplies RSI; all null/class/signed-limit excluded branches are checked, and the bridge makes no call or index/actor-carrier write. Together with the fresh zero initialization, normal Double request, old-index store, increment and exact guarded backedge, this closes one conditional selected-cycle CFG. Stable nonnegative signed Int32 bound and class selection, compatible current actor/value carriers, valid nonwrapping array/layout storage and normal provider nonvolatile preservation remain conditions. Original constructor receiver/actor origins, nested typed header/array meaning, actual live cycle selection, other branches, enum members and snapshot/consumer index correspondence remain unproved.'}
