"""Current GameCondition large-table transport, without concrete grammars.

The selected canonical path begins with null wrapper output. It independently
proves the nominal cast, each closed returning ReadPackable thunk and original
reference conversion. Existing-output callbacks and runtime evaluation remain
outside this finite source owner.
"""
import copy
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.GameCondition'
LABEL='storyGameConditionUnion'


def need(key,condition):
 if not condition:raise ValueError(LABEL+'.'+key)


def program(regions,entry,s,*,tag,count,table,selected,ff=False):
 need('literal-large-table-selection',type(ff)is bool
  and all(type(n)is int for n in(tag,count,table,selected,s.get('imageBase')))
  and 129<=count<=512 and 0<=tag<count and 0<table-s['imageBase']<2**32)
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742418','57','4883ec20')
 flag=g.relative('803d')+1;g.take('00','498bd8','488bfa');g.branch('0f85',True)
 g.take('33f6','488d542438','4533c0','6689742438','488bcf');g.call(s['header'])
 g.take('84c0');g.branch('0f84',ff);cast_usage=read_usage=read_site=None
 if not ff:
  g.take('0fb7742438','81fe'+(count-1).to_bytes(4,'little').hex());g.branch('0f87',False)
  need('literal-image-base',g.relative('488d15')==s['imageBase'])
  g.take('8b8cb2'+(table-s['imageBase']).to_bytes(4,'little').hex(),'4803ca','ffe1')
  need('owned-selected-table-branch',selected in g.bytes);g.at=selected
  cast_site=g.at;cast_cell=g.relative('488b15');g.take('488b0b');g.call(s['cast'])
  g.take('488bcf','4885c0');g.branch('75',False,1)
  read_site=g.at;read_cell=g.relative('488b15');g.call(s['closedPackable'])
  g.take('488903','488bd0')
  if g.bytes.get(g.at)==0xeb:g.jump('eb',1)
  else:g.jump('e9')
  cast_usage=dict(instruction=cast_site,cell=cast_cell);read_usage=dict(instruction=read_site,cell=read_cell)
 else:g.take('488933','33d2')
 g.take('488bcb');g.call(s['barrier']);g.take('488b5c2430','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,initializedFlag=flag,tag=None if ff else tag,canonicalFF=ff,
  castUsage=cast_usage,childUsage=read_usage,closedReaderTarget=None if ff else s['closedPackable'],
  outputInitiallyNullRequired=not ff,clearedOutputBytes=8 if ff else 0,headerMethodInfoZero=True,
  sameReader=True,sameOutput=True,normalReturn=True,entryRspRestored=True,
  nonvolatilesRestored=['rbx','rsi','rdi'],concreteGrammarAdmitted=False,
  condition='Initialized exact selected union, null incoming wrapper output, nominal cast returns null on that null input, matching actual closed thunk/canonical returning ReadPackable and child callback, normal helper ABI, disabled collector and stable disjoint storage. Existing-output alternatives and live selection are unproved.')


def derive_transport(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
 from scripts.game_data.memorypack import modelview_packable_sources,reference_adapter_sources
 from scripts.game_data.memorypack.current_reference_union_sources import _lineage
 from scripts.game_data.memorypack.levelscript_trigger_union_sources import _target
 from scripts.game_data.memorypack.module_structure_models import enclosing_header
 from scripts.game_data.memorypack.pooled_string_list_sources import compatible_list_cast
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 from scripts.game_data.memorypack.skill_selector_union_sources import closed_packable_thunk_program
 from scripts.game_data.memorypack.skill_action_union_sources import original_lineage
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
 from scripts.game_data.memorypack.union_dispatch import read_union_switch
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 wrappers=image.memorypack_wrappers;by_name={w.name:w for w in wrappers.values()}
 wrapper,=[w for w in wrappers.values()if w.wrapped_type==TYPE]
 switch=read_union_switch(image,wrapper.name,wrappers=wrappers);cases=switch['entries'];count=len(cases)
 need('complete-owned-finite-large-family',129<=count<=512 and[r['tag']for r in cases]==list(range(count)))
 entry=int(switch['dispatcherVa'],16);table=int(switch['tableVa'],16);body=pointer.owned(image,entry)
 formatter,=image.named_type_definitions[wrapper.name+'+'+wrapper.name.rsplit('.',1)[-1]+'Formatter']
 method,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize'and not m.flags&16 and m.slot==5]
 need('actual-instance-void-slot5',image.method_pointer_va(method)==entry and ctx.type_name(method.return_type)=='void'and method.parameter_count==2)
 _vtable(image,formatter.index,5,method.index,LABEL+'.slot5')
 scalar.ordinary(image,ctx.type_pointer(method.return_type),1,LABEL+'.void')
 for p,name,kind in zip(md.parameters_for(method),('MemoryPack.MemoryPackReader',wrapper.name),(17,18),strict=True):
  raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)
  need('exact-own-byref-ABI',(ctx.type_name(p.type_index),raw[10:12])==(name,bytes((kind,32))))
 header=_target(body,bytes.fromhex('6689742438488bcfe8'),'GameCondition-header')
 barrier=_target(body,bytes.fromhex('48893333d2488bcbe8'),'GameCondition-barrier')
 core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())
 generic=json.loads((CONTRACTS_DIR/'leveldata_npc_patrol_native.json').read_bytes())
 need('same-selected-reference-inputs',core['nativeInputs']==generic['nativeInputs']==pins)
 routes=copy.deepcopy(generic['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
 reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
 packable=base+core['readPackable']['entryRva']
 first=int(cases[0]['bodyVa'],16);raw=image.pe.bytes_at_va(first+10,5)
 need('actual-owned-cast-E8',raw[0]==232);cast=first+15+int.from_bytes(raw[1:],'little',signed=True)
 cast_source=pointer.owned(image,cast);cast_program=compatible_list_cast(cast_source['regions'],cast,0,null=True)
 symbols=dict(imageBase=base,header=header,cast=cast,barrier=barrier);programs=[]
 for selected in cases:
  at=int(selected['bodyVa'],16);tag=selected['tag'];child=by_name[selected['wrapperName']]
  need('direct-table-case',selected['targetVa']==selected['bodyVa'])
  raw=image.pe.bytes_at_va(at+30,5);need('actual-returning-closed-reader-E8',raw[0]==232)
  target=at+35+int.from_bytes(raw[1:],'little',signed=True)
  thunk=closed_packable_thunk_program(image.pe.bytes_at_va(target,12),target,packable)
  usage=derive_typed_usage_context(image,at+23-base,label=LABEL+'.actualChild')
  thunk_usage=derive_typed_usage_context(image,thunk['contextInstruction']-base,label=LABEL+'.actualClosedThunk')
  need('same-closed-thunk-nominal-context',all(usage.get(k)==thunk_usage.get(k)for k in('methodSpec','typeName','methodName','classArguments','methodArguments')))
  typed=bind_typed_read(image,usage,method_name='ReadPackable',argument=child.name,kind=18,reference=True)
  need('same-returning-read-definition',typed['methodDefinition']==reference['packableContext']['packableDefinition'])
  source=program(body['regions'],entry,dict(symbols,closedPackable=target),tag=tag,count=count,table=table,selected=at)
  cast_usage=derive_typed_usage_context(image,source['castUsage']['instruction']-base,label=LABEL+'.actualCast')
  need('actual-selected-nominal-cast',(cast_usage.get('tag'),cast_usage.get('typeName'))==(1,child.name))
  word=image.pe.u32_at_va(table+tag*4);need('same-actual-unsigned-table-word',base+word==at)
  programs.append(dict(tag=tag,wrapperName=child.name,wrappedType=child.wrapped_type,source=source,
   typedRequest=usage,typedArgument=typed,nullableCast=cast_usage,closedThunk=thunk,closedThunkUsage=thunk_usage,
   tableEntry=dict(rva=table+tag*4-base,rawHex=word.to_bytes(4,'little').hex().upper(),targetRva=word),
   originalLineage=original_lineage(image,ctx,child,TYPE),wrapperLineage=_lineage(ctx,md,child.name,wrapper.name)))
 null=program(body['regions'],entry,symbols,tag=0,count=count,table=table,selected=first,ff=True)
 pair=derive_pair(image,TYPE,wrapper.name)
 def forwarder(selected_image,selected_pair,selected_wrapper):
  need('same-operation-canonical-forwarder',selected_image is image and selected_wrapper.name==wrapper.name
   and selected_pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex']==method.index)
  return dict(readerTargetMode='independently-proved-inline',ownedWindows=body['windows'],programs=programs,canonicalFF=null)
 adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=forwarder)
 getter=pointer.methods(image,wrapper)['GetValue'];getter_at=image.method_pointer_va(getter)
 getter_program=pointer.leaf(image,getter_at,['488B4110','C3']);holder=_wrapper_holder(ctx,image,wrapper)
 need('abstract-base-original-holder',holder['declaredType']==TYPE and holder['offset']==16
  and md.types[wrapper.type_definition].flags&128==128)
 face,=pair['composition']['interfaces'];section=md.sections['interfaceOffsets'];joins=[]
 conversion_at=base+adapter['canonicalRoutes']['symbolRvas']['conversion'];conversion=pointer.owned(image,conversion_at)
 for row in programs:
  child=by_name[row['wrapperName']];child_holder=_wrapper_holder(ctx,image,child)
  need('same-inherited-original-holder',child_holder['declaredType']==TYPE and child_holder['offset']==16)
  td=md.types[child.type_definition];a=section.offset+td.interface_offsets_start*8
  faces=list(struct.iter_unpack('<ii',md.buf[a:a+td.interface_offsets_count*8]))
  matches=[(ordinal,offset)for ordinal,(index,offset)in enumerate(faces)if index==face['interfaceTypeIndex']]
  need('one-own-inherited-base-interface',len(matches)==1);ordinal,offset=matches[0]
  _vtable(image,child.type_definition,offset,getter.index,LABEL+'.inheritedGetter')
  converted=reference_adapter_sources.conversion(conversion['regions'],conversion_at,
   base+adapter['canonicalRoutes']['conversionPrepareRva'],getter_at,ordinal=ordinal)
  joins.append(dict(wrapperName=child.name,holder=child_holder,interfaceOrdinal=ordinal,interfaceOffset=offset,conversion=converted))
 header_source=pointer.owned(image,header);offsets=scalar.reader_offsets(image,LABEL)
 headers={marker:enclosing_header(header_source['regions'],header,offsets,marker=marker)for marker in('short','extended','false')}
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.levelscript-game-condition-transport.v1',
  status='validated-conditional-game-condition-transport',nativeInputs=pins,typeName=TYPE,wrapperName=wrapper.name,
  slot5Method=[method.index,image.type_name(formatter.index),'Deserialize',entry-base],switch=switch,
  ownedWindows=body['windows'],sourceRegions=[(a,b.hex().upper())for a,b in body['regions']],
  symbolRvas={k:v-base for k,v in symbols.items()if k!='imageBase'},programs=programs,canonicalFF=null,
  referencePackable=reference,cast=dict(windows=cast_source['windows'],program=cast_program),
  headerWindows=header_source['windows'],headerPrograms=headers,barrier=_barrier(image,barrier),
  pair=pair,adapter=adapter,baseHolder=holder,baseGetValue=getter_program,inheritedConversions=joins,
  concreteChildGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  runtimeConditionEvaluationProved=False,evidenceBoundary=dict(exact='Every selected current GameCondition table case, nominal cast, exact closed returning-reader thunk, unchanged reference output, canonical base adapter and inherited Original transfer.',
   conditional=__doc__,unresolved=['concrete child and Param grammars','recursive collection and Task parent composition',
    'existing-output alternatives and live callback/provider selection','runtime condition evaluation']))))
