"""Fresh selected ModelView source models over authenticated owned native bytes."""
import json
from scripts.game_data.memorypack import modelview_sources as named,modelview_holder_sources as holder,modelview_curve_sources as curve,modelview_graph_sources as graph,modelview_registration_sources as registration,modelview_collection_sources as collection,modelview_envelope_sources as envelope,modelview_long_sources as long,modelview_factory_sources as factory,modelview_reader_sources as reader,modelview_reference_sources as reference,modelview_union_sources as union,char_perform_action_sources as value,char_perform_tag_sources as tags,pooled_string_list_sources as lists,int_list_sources as ints
from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry

MODELS={
 'named.scalar_result':named.scalar_result,'named.audio_id_source':named.audio_id_source,'named.vector_result':named.vector_result,
 'holder.coherent_getter':holder.coherent_getter,'holder.vector_setter':holder.vector_setter,'holder.qword_setter':holder.qword_setter,
 'graph.inline_result':graph.inline_result,'graph.envelope_result32':graph.envelope_result32,'graph.condition_value16':graph.condition_value16,
 'curve.unity_curve':curve.unity_curve,'registration.lazy_init':registration.lazy_init,'registration.lazy_key':registration.lazy_key,'collection.reference_loop':collection.reference_loop,
 'envelope.main':envelope.main,'envelope.not_null':envelope.not_null,'envelope.conversion':envelope.conversion,'envelope.typed_provider':envelope.typed_provider,
 'value.value_leaf':value.value_leaf,'value.read_value32':value.read_value32,'tags.peek_null':tags.peek_null,'tags.read_null_positive':tags.read_null_positive,
 'long.list_source':long.list_source,'long.add64':long.add64,'long.formatter':long.formatter,'long.dispatch':long.dispatch,'ints.capacity':ints.capacity,'ints.initialized_class':ints.initialized_class,
 'factory.create_instance':factory.create_instance,'factory.cached_rbx':factory.cached_rbx,'factory.checked_cast':factory.checked_cast,'factory.dual_setter':factory.dual_setter,'factory.wrapper_constructor':factory.wrapper_constructor,
 'lists.compatible_list_cast':lists.compatible_list_cast,'lists.cached_list_getter':lists.cached_list_getter,
 'reader.prefix':reader.prefix,'reader.on_deserialized':reader.on_deserialized,'reader.normal_return':reader.normal_return,'reader.inline_prefix':reader.inline_prefix,
 'reference.read_value':reference.read_value,'reference.get_value':reference.get_value,'union.new_child':union.new_child,
}


def need(k,e,a):
 if e!=a:raise ValueError('modelViewPrograms.'+k+':expected='+str(e)[:240]+':actual='+str(a)[:240])


def validate_programs(image,profile):
 base=image.pe.image_base;regions={}
 for key,p in profile['programs'].items():
  windows=p['windows'];bounds=sorted((w['startRva'],w['endRva'])for w in windows)
  if p['ownership']=='complete-unwind-family':need('owned:'+key,sorted(tuple(r['runtimeTriple'][:2])for r in image.unwind_index.family(p['ownerRva'])['ranges']),bounds)
  elif p['ownership']=='complete-leaf':
   entry=base+p['ownerRva'];leaf=decode_closed_leaf_entry(image.mapper,image.pe.bytes_at_va(entry,512),entry);end=max(int(r['va'],16)+len(bytes.fromhex(r['bytes']))for r in leaf['rows']);need('leaf:'+key,[(entry-base,end-base)],bounds)
  else:
   domain={c['model']for c in profile['calls']if c['program']==key}
   if p['ownership']=='getter-selected-tail':need('tail-domain',{'reference.get_value'},domain);need('tail-shape',[(p['ownerRva'],p['ownerRva']+7)],bounds)
   elif p['ownership']=='lazy-key-selected-interval':need('key-domain',{'registration.lazy_key'},domain)
   elif p['ownership']=='indexed-context-selected-prefix':need('context-domain',{'ints.initialized_class'},domain)
   else:raise ValueError('modelViewPrograms.unreviewed-ownership:'+str(p['ownership']))
  image.check_windows(windows,label='modelViewPrograms');regions[key]=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in windows]
 need('source-model-domain',set(MODELS),{c['model']for c in profile['calls']});proofs=[]
 for c in profile['calls']:
  if not any(a<=c['entry']<a+len(b)for a,b in regions[c['program']]):raise ValueError('modelViewPrograms.entry-not-owned')
  try:q=MODELS[c['model']](regions[c['program']],c['entry'],*c['args'],**c['kwargs'])
  except (ValueError,KeyError,IndexError)as e:raise ValueError('modelViewPrograms.source:'+c['model']+':'+str(c['entry'])+':'+str(e))from e
  need('fresh-selected-instructions:'+c['model'],c['expected']['selectedBytes'],json.loads(json.dumps(q['selectedBytes'])));proofs.append(q)
 return regions,proofs
