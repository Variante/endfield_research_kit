"""Exact current LevelScriptModuleData transport; concrete grammars separate."""
import copy
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.skill_selector_union_sources import branch,jump,peek

TYPE='Beyond.Gameplay.LevelScriptModuleData'
LABEL='storyModuleUnion'


def need(key,condition):
 if not condition:raise ValueError(LABEL+'.'+key)


def program(regions,entry,s,*,tag,count,table,selected,ff=False):
 need('literal-table-selection',type(ff)is bool
  and all(type(n)is int for n in(tag,count,table,selected,s.get('imageBase')))
  and 1<=count<=128 and 0<=tag<count and 0<table-s['imageBase']<2**32)
 g=BytesPath(regions,entry);g.take('48895c2408','4889742418','57','4883ec20')
 ready=g.relative('803d')+1;g.take('00','498bf8','488bda');g.branch('0f84',False)
 g.take('33f6','488d542438','488bcb','6689742438');g.call(s['header'])
 g.take('84c0');g.branch('0f84',ff);usage=None;prepared=False
 if ff:g.take('488937');jump(g)
 else:
  g.take('0fb7742438','83fe'+bytes((count-1,)).hex());g.branch('0f87',False)
  need('literal-image-base',g.relative('488d15')==s['imageBase'])
  g.take('8b84b2'+(table-s['imageBase']).to_bytes(4,'little').hex(),'4803c2','ffe0')
  need('owned-selected-case',selected in g.bytes);g.at=selected
  g.take('488b0f','4885c9');branch(g,4,True)
  site=g.at;cell=g.relative('488b15');g.take('488bcb');g.call(s['packable'])
  if peek(g,3)==bytes.fromhex('488bcf'):g.take('488bcf');prepared=True
  g.take('488907');usage=dict(instruction=site,cell=cell)
  if peek(g)in(b'\xe9',b'\xeb'):jump(g)
 if peek(g,3)==bytes.fromhex('488bcf'):g.take('488bcf');prepared=True
 need('exact-output-address-prepared-for-barrier',prepared);g.call(s['barrier'])
 if peek(g)in(b'\xe9',b'\xeb'):jump(g)
 g.take('488b5c2430','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,initializedFlag=ready,tag=None if ff else tag,canonicalFF=ff,
  childUsage=usage,sameReader=True,sameOutput=True,outputInitiallyNullRequired=not ff,
  clearedOutputBytes=8 if ff else 0,wholeReferenceStoredUnchanged=True,normalReturn=True,
  entryRspRestored=True,nonvolatilesRestored=['rbx','rsi','rdi'],concreteGrammarAdmitted=False,
  condition='Initialized exact selected table, null incoming wrapper output, matching returning ReadPackable context and concrete callback, normal helpers/disabled collector and stable disjoint storage. Existing-output alternatives and live selection remain outside the proof.')


def derive_transport(image,pins):
 return derive_reference_transport(image,pins,type_name=TYPE,
  schema='endfield.levelscript-module-union-transport.v1',status='validated-conditional-module-union-transport',
  evidence_boundary=dict(exact='Every selected current Module table case, actual returning ReadPackable request and reference store, full frame, canonical base adapter and inherited Original transfer.',
   conditional=__doc__,unresolved=['new concrete children and their collections','root dictionary composition for new routes',
    'existing-output alternatives and live callback/provider selection','runtime module behavior']))


def derive_reference_transport(image,pins,*,type_name,schema,status,evidence_boundary,expected_count=None):
 """Fresh finite null-output transport, with nominal identities proved per owner."""
 TYPE=type_name
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
 from scripts.game_data.memorypack import modelview_packable_sources,reference_adapter_sources
 from scripts.game_data.memorypack.current_reference_union_sources import _lineage
 from scripts.game_data.memorypack.levelscript_trigger_union_sources import _target
 from scripts.game_data.memorypack.module_structure_models import enclosing_header
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.skill_action_union_sources import original_lineage
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
 from scripts.game_data.memorypack.union_dispatch import read_union_switch
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 wrappers=image.memorypack_wrappers;by_name={w.name:w for w in wrappers.values()}
 wrapper,=[w for w in wrappers.values()if w.wrapped_type==TYPE]
 switch=read_union_switch(image,wrapper.name,wrappers=wrappers);cases=switch['entries'];count=len(cases)
 need('complete-owned-finite-family',1<=count<=128 and[r['tag']for r in cases]==list(range(count)))
 need('exact-selected-family-count',expected_count is None or count==expected_count)
 entry=int(switch['dispatcherVa'],16);table=int(switch['tableVa'],16);body=pointer.owned(image,entry)
 formatter,=image.named_type_definitions[wrapper.name+'+'+wrapper.name.rsplit('.',1)[-1]+'Formatter']
 method,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize'and not m.flags&16 and m.slot==5]
 need('actual-instance-void-slot5',image.method_pointer_va(method)==entry and ctx.type_name(method.return_type)=='void'and method.parameter_count==2)
 _vtable(image,formatter.index,5,method.index,LABEL+'.slot5')
 scalar.ordinary(image,ctx.type_pointer(method.return_type),1,LABEL+'.void')
 for p,name,kind in zip(md.parameters_for(method),('MemoryPack.MemoryPackReader',wrapper.name),(17,18),strict=True):
  raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)
  need('exact-own-byref-ABI',(ctx.type_name(p.type_index),raw[10:12])==(name,bytes((kind,32))))
 header=_target(body,bytes.fromhex('6689742438e8'),'Module-header')
 barrier=_target(body,bytes.fromhex('488bcfe8'),'Module-barrier')
 core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())
 generic=json.loads((CONTRACTS_DIR/'leveldata_npc_patrol_native.json').read_bytes())
 need('same-selected-reference-inputs',core['nativeInputs']==generic['nativeInputs']==pins)
 routes=copy.deepcopy(generic['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
 reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
 symbols=dict(imageBase=base,header=header,barrier=barrier,packable=base+core['readPackable']['entryRva']);programs=[]
 for selected in cases:
  at=int(selected['bodyVa'],16);tag=selected['tag'];child=by_name[selected['wrapperName']]
  need('direct-table-case',selected['targetVa']==selected['bodyVa'])
  source=program(body['regions'],entry,symbols,tag=tag,count=count,table=table,selected=at)
  usage=derive_typed_usage_context(image,source['childUsage']['instruction']-base,label=LABEL+'.actualChild')
  typed=bind_typed_read(image,usage,method_name='ReadPackable',argument=child.name,kind=18,reference=True)
  need('same-returning-read-definition',typed['methodDefinition']==reference['packableContext']['packableDefinition'])
  word=image.pe.u32_at_va(table+tag*4);need('same-actual-unsigned-table-word',base+word==at)
  programs.append(dict(tag=tag,wrapperName=child.name,wrappedType=child.wrapped_type,source=source,
   typedRequest=usage,typedArgument=typed,tableEntry=dict(rva=table+tag*4-base,rawHex=word.to_bytes(4,'little').hex().upper(),targetRva=word),
   originalLineage=original_lineage(image,ctx,child,TYPE),wrapperLineage=_lineage(ctx,md,child.name,wrapper.name)))
 null=program(body['regions'],entry,symbols,tag=0,count=count,table=table,selected=int(cases[0]['bodyVa'],16),ff=True)
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
 return json.loads(json.dumps(dict(schema=schema,
  status=status,nativeInputs=pins,typeName=TYPE,wrapperName=wrapper.name,
  slot5Method=[method.index,image.type_name(formatter.index),'Deserialize',entry-base],switch=switch,
  ownedWindows=body['windows'],sourceRegions=[(a,b.hex().upper())for a,b in body['regions']],
  symbolRvas={k:v-base for k,v in symbols.items()if k!='imageBase'},programs=programs,canonicalFF=null,
  referencePackable=reference,headerWindows=header_source['windows'],headerPrograms=headers,barrier=_barrier(image,barrier),
  pair=pair,adapter=adapter,baseHolder=holder,baseGetValue=getter_program,inheritedConversions=joins,
  concreteChildGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  runtimeModuleBehaviorProved=False,evidenceBoundary=evidence_boundary)))
