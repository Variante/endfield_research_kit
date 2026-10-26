"""Current LevelSpecific tag0/FF transport, separate from spaceship children.

Only the initialized reference-result path with initially null wrapper output
is selected. The existing-output byref overload, unknown/extended tags and
runtime callback/provider choice remain closed. A typed wrapper request does
not supply CabinSlotInfo, dictionary, tuple/list or complete spaceship grammar.
"""
import json
import struct
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.LevelSpecificData'
CHILD='Beyond.Gameplay.SpaceShipSpecificData'
LABEL='storyLevelSpecificTransport'


def caller_program(regions,entry,s,*,ff=False):
 if type(ff)is not bool:raise ValueError(LABEL+'.literal-FF-mode')
 g=BytesPath(regions,entry);g.take('48895c2408','4889742418','57','4883ec20')
 flag=g.relative('803d')+1;g.take('00','498bd8','488bfa');g.branch('75',True,1)
 g.take('33f6','488d542438','488bcf','6689742438');g.call(s['header']);g.take('84c0');g.branch('74',ff,1)
 usage=None
 if ff:g.take('488933');g.jump('eb',1)
 else:
  g.take('0fb7742438','6685f6');g.branch('0f85',False)
  g.take('488b0b','4885c9');g.branch('74',True,1)
  site=g.at;cell=g.relative('488b15');usage=dict(instruction=site,cell=cell)
  g.take('488bcf');g.call(s['packable']);g.take('488903')
 g.take('488bcb','488b5c2430','488b742440','4883c420','5f')
 if g.relative('e9')!=s['barrier']:raise ValueError(LABEL+'.exact-tail-barrier')
 return dict(selectedBytes=g.seen,initializedFlag=flag,canonicalFF=ff,tag=None if ff else 0,headerTarget=s['header'],
  childUsage=usage,childTarget=None if ff else s['packable'],tailBarrierTarget=s['barrier'],
  outputInitiallyNull=not ff,clearedOutputBytes=8 if ff else 0,positiveResultBytes=0 if ff else 8,
  sameReaderAndOutput=True,entryRspRestored=True,nonvolatilesRestored=['rbx','rsi','rdi'],
  normalReturnConditionalOnBarrier=True,existingOutputByrefPathAdmitted=False,concreteChildGrammarAdmitted=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.levelscript_family_regenerate import Build
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,reference_adapter_sources
 from scripts.game_data.memorypack.current_reference_union_sources import _header_target,_lineage
 from scripts.game_data.memorypack.module_structure_models import enclosing_header
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
 from scripts.game_data.memorypack.union_dispatch import read_union_switch
 need=lambda k,e,a:scalar.need(LABEL,k,e,a)
 _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
 wrappers=image.memorypack_wrappers;by={w.wrapped_type:w for w in wrappers.values()};wrapper=by[TYPE];child=by[CHILD]
 formatter_name=wrapper.name+'+'+wrapper.name.rsplit('.',1)[-1]+'Formatter';formatter,=image.named_type_definitions[formatter_name]
 fm,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize'and not m.flags&16 and m.slot==5]
 need('own-slot5-void-two-byrefs',('void',2),(ctx.type_name(fm.return_type),fm.parameter_count))
 _vtable(image,formatter.index,5,fm.index,LABEL+'.slot5');scalar.ordinary(image,ctx.type_pointer(fm.return_type),1,LABEL+'.void')
 for parameter,name,kind in zip(md.parameters_for(fm),('MemoryPack.MemoryPackReader',wrapper.name),(17,18),strict=True):
  raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
  need('owned-slot5-byref',(name,bytes((kind,32))),(ctx.type_name(parameter.type_index),raw[10:12]))
 entry=image.method_pointer_va(fm);body=pointer.owned(image,entry);switch=read_union_switch(image,wrapper.name,wrappers=wrappers)
 need('actual-slot5-and-switch',entry,int(switch['dispatcherVa'],16))
 need('exact-one-nominal-route',[(0,child.name)],[(r['tag'],r['wrapperName'])for r in switch['entries']])
 header=_header_target(body,'table-rsi');header_body=pointer.owned(image,header)
 headers={marker:enclosing_header(header_body['regions'],header,scalar.reader_offsets(image,LABEL),marker=marker)for marker in('short','false')}
 actual={control_transfer(row)['target']for index,row in enumerate(body['rows'])if index and index+1<len(body['rows'])
  and bytes.fromhex(row['bytes'])[:1]==b'\xe8'and body['rows'][index-1]['text']=='mov rcx, rdi'and body['rows'][index+1]['text']=='mov [rbx], rax'}
 need('one-actual-reference-result-source',1,len(actual));packable,=actual
 clone_path=CONTRACTS_DIR/'memorypack_reader_clones_native.json';clone_raw=clone_path.read_bytes();clone_fact=json.loads(clone_raw)
 need('clone-selected-build',pins,clone_fact['nativeInputs'])
 clone,=[row for row in clone_fact['clones']if row['claim']=='MemoryPack.MemoryPackReader.ReadPackable'and row.get('resultAbi')=='reference'and base+row['targetRva']==packable]
 Build(image,pins).prove_reader_clone_target(packable,'MemoryPack.MemoryPackReader.ReadPackable',result_abi='reference')
 collector_path=CONTRACTS_DIR/'model_view_state_controller_native.json';collector_raw=collector_path.read_bytes();collector=json.loads(collector_raw)
 need('collector-selected-build',pins,collector['nativeInputs']);barrier=base+collector['collector']['entryRva'];barrier_proof=_barrier(image,barrier)
 symbols=dict(header=header,packable=packable,barrier=barrier)
 positive=caller_program(body['regions'],entry,symbols);null=caller_program(body['regions'],entry,symbols,ff=True)
 usage=derive_typed_usage_context(image,positive['childUsage']['instruction']-base,label=LABEL+'.child')
 typed=bind_typed_read(image,usage,method_name='ReadPackable',argument=child.name,kind=18,reference=True)
 need('same-actual-reference-result-definition',clone['equivalentMethod'][0],typed['methodDefinition'])
 pair=derive_pair(image,TYPE,wrapper.name)
 def forwarder(selected_image,selected_pair,selected_wrapper):
  face,=selected_pair['composition']['interfaces'];need('own-union-slot5',(wrapper.name,fm.index),(selected_wrapper.name,face['formatterDeserializeMethodIndex']))
  return dict(ownedWindows=body['windows'],programs=[positive],canonicalFF=null,readerTargetMode='independently-proved-inline')
 adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=forwarder)
 getter=pointer.methods(image,wrapper)['GetValue'];getter_entry=image.method_pointer_va(getter)
 getter_proof=pointer.leaf(image,getter_entry,['488B4110','C3']);holder=_wrapper_holder(ctx,image,wrapper);child_holder=_wrapper_holder(ctx,image,child)
 need('base-holder',(TYPE,16),(holder['declaredType'],holder['offset']));need('inherited-base-holder',(TYPE,16),(child_holder['declaredType'],child_holder['offset']))
 need('abstract-base-wrapper',128,md.types[wrapper.type_definition].flags&128)
 face,=pair['composition']['interfaces'];td=md.types[child.type_definition];section=md.sections['interfaceOffsets'];start=section.offset+td.interface_offsets_start*8
 interfaces=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]));found=[(ordinal,offset)for ordinal,(index,offset)in enumerate(interfaces)if index==face['interfaceTypeIndex']]
 need('one-inherited-base-interface',1,len(found));ordinal,offset=found[0];_vtable(image,child.type_definition,offset,getter.index,LABEL+'.baseGetter')
 conversion_entry=base+adapter['canonicalRoutes']['symbolRvas']['conversion'];conversion=pointer.owned(image,conversion_entry)
 transfer=reference_adapter_sources.conversion(conversion['regions'],conversion_entry,base+adapter['canonicalRoutes']['conversionPrepareRva'],getter_entry,ordinal=ordinal)
 _publication_gate(image,pins);need('clone-source-bookend',clone_raw,clone_path.read_bytes());need('collector-source-bookend',collector_raw,collector_path.read_bytes())
 return json.loads(json.dumps(dict(schema='endfield.story-level-specific-transport.v1',status='validated-current-wrapper-transport',nativeInputs=pins,
  typeName=TYPE,wrapperName=wrapper.name,childTypeName=CHILD,childWrapperName=child.name,slot5Method=[fm.index,formatter_name,'Deserialize',entry-base],
  switch=switch,ownedWindows=body['windows'],positive=positive,canonicalFF=null,headerWindows=header_body['windows'],headerPrograms=headers,
  typedRequest=usage,typedArgument=typed,reviewedReferenceReader=clone,barrier=barrier_proof,pair=pair,adapter=adapter,
  originalLineage=_lineage(ctx,md,CHILD,TYPE),wrapperLineage=_lineage(ctx,md,child.name,wrapper.name),
  baseHolder=holder,baseGetValue=getter_proof,derivedHolder=child_holder,inheritedConversion=dict(interfaceOrdinal=ordinal,interfaceOffset=offset,program=transfer),
  concreteOriginalAdapterUsed=False,concreteChildGrammarAdmitted=False,wholeUnionAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Own initialized tag0/FF union, actual typed reference-result wrapper source, whole store/tail barrier/frame, canonical base adapter and inherited GetValue conversion.',
   conditional=__doc__,unresolved=['spaceship reader/factory/children','actual enclosing parent','extended/reserved/unknown tags','existing-output overload','runtime selection','whole owner/physical EOF']))))
