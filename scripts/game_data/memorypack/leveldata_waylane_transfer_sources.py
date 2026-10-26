"""WayLane's padded nominal value16 canonical adapter; collection stays separate."""
import json
import struct
from scripts.game_data.memorypack.leveldata_waylane_sources import TYPE,derive_record


def bind_record(record):
 if (record.get('schema')!='endfield.story-waylane-record-source.v1'or record.get('status')!='validated-current-value-wrapper-source'
   or record.get('typeName')!=TYPE or type(record.get('managedBytes'))is not int or record['managedBytes']!=16
   or record.get('referenceLaneOffsets')!=[8]or record.get('paddingByteRanges')!=[[4,8]]
   or sorted((r.get('name'),r.get('typeName'),r.get('field'))for r in record.get('fields',[]))!=[
    ('laneDir','uint[]',[TYPE,'uint[]',24]),('totalLane','int',[TYPE,'int',16])]
   or record.get('getter',{}).get('outputBytes')!=16 or record.get('getter',{}).get('sourceBitsUnchanged')is not True
   or record.get('childGrammarAdmitted')is not False or record.get('positiveCollectionAdmitted')is not False
   or record.get('wholeOwnerAdmitted')is not False):raise ValueError('storyWayLaneTransfer.exact-padded-nominal-record')
 return record


def derive_adapter(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources,primitive_param,event_args_paths
 from scripts.game_data.memorypack import scalar_param_native as scalar
 from scripts.game_data.memorypack.managed_value16_sources import nonnull_program
 from scripts.game_data.memorypack.skill_root_tag_query_transfer import adapter16_program
 from scripts.game_data.il2cpp.formatter_value_paths import BytesPath,deserialize_slot
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 need=lambda k,e,a:scalar.need('storyWayLaneTransfer',k,e,a)
 _publication_gate(image,pins);record=bind_record(derive_record(image,pins));need('same-native-record',pins,record['nativeInputs'])
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image)
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 pair=record['pair'];pointer.registered_pair(image,pair,wrapper,label='storyWayLaneTransfer.registeredPair')
 face,=pair['composition']['interfaces'];getter=md.methods[face['getValueMethodIndex']]
 scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(TYPE,17,False),[],'storyWayLaneTransfer.getter')
 pointer.leaf(image,image.method_pointer_va(getter),['0F104210','488BC1','0F1101','C3'])
 td=md.types[wrapper.type_definition];section=md.sections['interfaceOffsets'];at=section.offset+td.interface_offsets_start*8
 ordinal=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
 context,context_proof=buff_ptr_sources._adapter_context(image,ge);sources={};symbols={};registrations={}
 for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull')):
  method=buff_ptr_sources._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
  registrations[role]=ge.resolve(method.index,[TYPE,'object'],[]);symbols[role]=registrations[role]['pointer'];sources[role]=pointer.owned(image,symbols[role])
 def call(role,offset):return buff_ptr_sources._call(sources[role],offset)
 for name,offset in dict(peek=45,typeHandle=103,creationTest=126,activate=153,nonnull=182).items():
  actual=call('adapter',offset)
  if name in symbols:need('same-canonical-nonnull-entry',symbols[name],actual)
  symbols[name]=actual
 ff=BytesPath(sources['adapter']['regions'],symbols['adapter']+52).relative('0f85')
 symbols['header']=BytesPath(sources['adapter']['regions'],ff+8).relative('e8')
 for name,offset in dict(resolve=66,wrapperProvider=82,wrapperInvoke=117,indexed=157,prepare=171,barrier=294).items():symbols[name]=call('nonnull',offset)
 need('same-context-resolver',symbols['resolve'],call('nonnull',140))
 need('same-named-type-handle',base+pair['registration']['helperMethods']['typeFromHandle'][3],symbols['typeHandle'])
 programs=dict(adapter=[adapter16_program(sources['adapter']['regions'],symbols['adapter'],symbols,**mode)for mode in({},{'create':False},{'null':True})],
  nonnull=[nonnull_program(sources['nonnull']['regions'],symbols['nonnull'],symbols,ordinal=ordinal,reference_lane=8,wrapper_null=value)for value in(False,True)])
 for role in('wrapperInvoke','peek','header'):sources[role]=pointer.owned(image,symbols[role])
 invocation=deserialize_slot(sources['wrapperInvoke']['regions'],symbols['wrapperInvoke'],prepare=symbols['prepare'],
  callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
 offsets=scalar.reader_offsets(image,'storyWayLaneTransfer');peek=event_args_paths.peek(sources['peek']['regions'],symbols['peek'],offsets)
 header=vector_recorder(image)(symbols['header']-base);primitive_param.object_header_source(image,header,offsets)
 collector=_barrier(image,symbols['barrier'])
 method=buff_ptr_sources._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2','Deserialize')
 observed=ge.observe(method.index,[TYPE,wrapper.name],[])
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-waylane-value-transfer.v1',status='validated-conditional-padded-value16-transfer',nativeInputs=pins,
  typeName=TYPE,wrapperName=wrapper.name,managedBytes=16,referenceLaneOffsets=[8],paddingByteRanges=[[4,8]],
  record=record,proof=dict(registrations=registrations,adapterContext=context,adapterContextProof=context_proof,interfaceOrdinal=ordinal,
   programs=programs,wrapperInvocation=invocation,peek=peek,header=header,collector=collector,
   closedWrapperDeserializeObserved=observed,closedWrapperCallbackPointerEqualityInferred=False,
   symbolRvas={key:target-base for key,target in symbols.items()},sourceWindows={key:value['windows']for key,value in sources.items()}),
  canonicalAdapterAdmitted=True,actualCallbackEqualsCanonicalRequired=True,liveFormatterSelectionObserved=False,
  canonicalFFWireBytes=1,canonicalFFDefaultManagedBytes=16,
  arrayGrammarAdmitted=False,positiveCollectionAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Fresh nominal WayLane value16/ref8/padding4..7 source/getter/zeroing, canonical adapter FF/create/reuse and nonnull wrapper/null/interface conversion, exact full16 copy and ref8 barrier.',
   conditional='Selected ready callback equals the proved canonical entry, coherent closed MethodInfo represents the independently registered WayLane/wrapper pair, and normal compatible provider/allocation effects with disjoint buffered storage hold. Padding is copied unchanged; it supplies no wire bytes.',
   unresolved=['UInt32 array wire/count source','actual closed list callback/dispatcher/Add and parent','runtime formatter/provider selection','whole owner/physical EOF']))))
