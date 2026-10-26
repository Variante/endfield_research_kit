"""Own initialized Bitset formatter forwarder; its inlined cold resolver is excluded."""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.Actions.Param`1<Beyond.GEnums.BitsetType>'


def need(key,condition):
 if not condition:raise ValueError('bitsetParamForwarder.'+key)


def program(regions,entry,*,reader_target):
 g=BytesPath(regions,entry)
 g.take('4055','56','4883ec48');flag=g.relative('803d')+1;g.take('00','498bf0','488bea')
 g.branch('0f85',True)
 class_site=g.at;class_cell=g.relative('488b0d');g.take('83b9e000000000')
 guard=g.at;g.branch('75',True,1);cold=guard+2
 need('exact-ready-class-skips-one-owned-call',g.at==cold+5 and all(cold+i in g.bytes for i in range(5)))
 raw=bytes(g.bytes[cold+i]for i in range(5));need('excluded-class-initializer-is-E8',raw[0]==232)
 class_init=cold+5+int.from_bytes(raw[1:],'little',signed=True)
 g.take('4533c0','488bd6','488bcd','4883c448','5e','5d')
 need('exact-owned-wrapper-tail',g.relative('e9')==reader_target)
 return dict(selectedBytes=g.seen,entry=entry,end=g.at,metadataInitializedFlagCell=flag,
  wrapperClassInstructionVa=class_site,wrapperClassCell=class_cell,excludedClassInitializer=dict(site=cold,target=class_init,bytes=raw.hex().upper()),
  selectedCallCount=0,metadataInitializedRequired=True,wrapperClassInitializedRequired=True,coldMetadataPathAdmitted=False,
  sameIncomingReaderRdxToTailRcx=True,sameIncomingOutputR8ToTailRdx=True,tailMethodInfoR8Zero=True,
  tailTargetVa=reader_target,entryRspRestored=True,allWin64IntegerNonvolatilesRestored=True,
  frame=dict(stackReservation=72,pushedNonvolatiles=['rbp','rsi'],selectedSavedEntryHomes=[[-8,8],[-16,8]],
   ordinaryCallShadowBytes=32),physicalFunctionExtentProved=False,liveInitializationObserved=False)


def derive(image,pair,wrapper):
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack.pointer_param import owned,methods
 need('exact-nominal-Bitset-Param',wrapper.wrapped_type==TYPE and pair['registration']['originalType']==TYPE
  and pair['registration']['wrapperType']==wrapper.name)
 row=pair['composition']['methods'][1];image.validate_method_row(row,label='bitsetParamForwarder.method')
 reader=methods(image,wrapper)['Deserialize'];target=image.method_pointer_va(reader)
 source=owned(image,image.pe.image_base+row[3]);proof=program(source['regions'],source['pointer'],reader_target=target)
 usage=derive_typed_usage_context(image,proof['wrapperClassInstructionVa']-image.pe.image_base,label='bitsetParamForwarder.actual-class')
 need('own-current-wrapper-class',(usage.get('tag'),usage.get('typeName'))==(1,wrapper.name))
 return json.loads(json.dumps(dict(schema='endfield.bitset-Param-forwarder-source.v1',
  sourceProgram=proof,sourceWindows=source['windows'],sourceRegions=[[a,b.hex().upper()]for a,b in source['regions']],
  actualWrapperClass=usage,readerMethod=[reader.index,wrapper.name,'Deserialize',target-image.pe.image_base],
  coldMetadataPathAdmitted=False,liveInitializationObserved=False,
  condition='Own metadata-initialized byte and matching wrapper class initialization flag are nonzero; actual metadata-owned static wrapper reader is selected. Complete incoming reader/output transfer and restored normal frame before its zero-context tail. The inlined cold resolver and class initialization call are excluded, with no claim of their effects or runtime execution.')))
