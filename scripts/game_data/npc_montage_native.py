"""Selected current Montage sparse grammar; no positive collection admission."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,reader_input_changes
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_extent
from scripts.game_data.il2cpp.protocol import canonical_type_name
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,validate_generic_contexts,derive_typed_usage_context
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.string_source_programs import prove_collection_header
from scripts.game_data.il2cpp.string_source_instructions import decode_utf8_decoder_instructions
from scripts.game_data.memorypack import pooled_source_helper,scalar_param_native as scalar,int_list_sources,utf8_source_helper,reference_adapter_sources
from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
from scripts.game_data.memorypack.montage_sources import validate_fields
from scripts.game_data.memorypack.montage_factory_sources import validate_factories
from scripts.game_data.memorypack.montage_collection_sources import reference_program,value_program

CONTRACT_PATH=CONTRACTS_DIR/'npc_montage_native.json'
SCHEMA='endfield.memorypack-npc-montage-native.v1'
LABEL='npcMontage'

def need(check,expected,actual):
 if actual!=expected:raise ValueError(f'{LABEL}.{check}:expected={str(expected)[:250]} actual={str(actual)[:400]}')

def _list(image,record,argument,context,entries):
 base=image.pe.image_base;ctx=NativeReferenceContext(image);td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1'];method,=[m for m in image.metadata.methods_for(td) if image.metadata.string(m.name_index)=='Deserialize'];actual=entries.resolve(method.index,[argument],[])
 need('list-registration',record['entry'],json.loads(json.dumps(actual)))
 need('list-owned-source',sorted(tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(actual['pointer']-base)['ranges']),sorted((w['startRva'],w['endRva']) for w in record['windows']));image.check_windows(record['windows'],label=LABEL+'.list')
 parameters=list(image.metadata.parameters_for(method));need('list-instance-arity',(False,2,'void'),(bool(method.flags&16),len(parameters),ctx.type_name(method.return_type)))
 reader=ctx.index.types['MemoryPack.MemoryPackReader'];byval=image.pe.bytes_at_va(ctx.type_pointer(reader.byval_type_index),16);formal=image.pe.bytes_at_va(ctx.type_pointer(parameters[0].type_index),16)
 need('reader-byval-kind-flags',b'\x11\x80',byval[10:12]);need('reader-byref-kind-flags',b'\x11\x20',formal[10:12]);need('reader-identity',reader.index,int.from_bytes(formal[:8],'little'));need('reader-parent','System.ValueType',ctx.parent('MemoryPack.MemoryPackReader'));need('reader-same-definition',byval[:8],formal[:8])
 slots={r['relativeSlot']:r for r in context['entries']};list_type=image.pe.bytes_at_va(ctx.type_pointer(slots[0]['index']),16);formal=image.pe.bytes_at_va(ctx.type_pointer(parameters[1].type_index),16);need('list-formal-kind-flags',b'\x15\x20',formal[10:12]);need('list-byval-kind-flags',b'\x15\x00',list_type[10:12]);need('list-same-owned-carrier',list_type[:8],formal[:8])
 return actual,[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])) for w in record['windows']]

def _collections(image,pins,fact,records):
 base=image.pe.image_base;ctx=NativeReferenceContext(image);entries=GenericEntries(image);context=fact['listContext'];validate_generic_contexts(image,[context],label=LABEL)
 def fail(*args):raise ValueError(LABEL+'.list-context:'+str(args)[:1000])
 validate_list_formatter_base_context(image,context,entries,fail=fail);slots={r['relativeSlot']:r for r in context['entries']};parent=next(r for r in records if r['type']=='Beyond.Montage.NPCMontageAnim');fields={f['name']:f for f in parent['fields']};reference=fact['referenceList'];value=fact['valueList']
 need('reference-list-fields',['decoEntities','dynamicEntities'],reference['fields']);need('value-list-field','montageOverrideTransitions',value['field']);need('all-list-fields',set(reference['fields']+[value['field']]),{f['name'] for f in parent['fields'] if f['kind']=='list'})
 for name in [*reference['fields'],value['field']]:
  row=fields[name];usage=row['typedContext'];validate_typed_usage_context(image,usage,label=LABEL+'.list-parent');need('parent-method',('MemoryPack.MemoryPackReader','ReadPackable',[],[row['declaredType']]),tuple(usage[k] for k in ('typeName','methodName','classArguments','methodArguments')))
  td=ctx.index.types[parent['type']];field,=[f for f in image.metadata.fields_for(td) if image.metadata.string(f.name_index)==name];closed=closed_generic_reference_extent(ctx,field.type_index);need('list-field',row['declaredType'],closed['type']);call=image.instantiations.resolve(usage['methodSpec'][2]).arguments;need('list-call-arity',1,len(call));raw=image.pe.bytes_at_va(call[0].type_pointer_va,16);need('list-call-kind-flags',b'\x15\x00',raw[10:12]);need('list-call-carrier',bytes.fromhex(closed['declaredTypeRecordHex'])[:8],raw[:8])
  if name in reference['fields']:
   element,=closed['argumentTypes'];need('reference-element-parent',(False,'object'),(ctx.is_value_type(element),ctx.parent(element)))
  else:need('value-element',[value['element']],closed['argumentTypes']);need('value-element-kind',True,ctx.is_value_type(value['element']))
 factory_path=CONTRACTS_DIR/'levelscript_int_list_native.json';factory_fact=json.loads(factory_path.read_bytes());need('factory-inputs',pins,factory_fact['nativeInputs']);factory=factory_fact['factory']
 for usage in factory['usages']:validate_typed_usage_context(image,usage,label=LABEL+'.factory')
 need('factory-pair',['System.Collections.Generic.List`1','MemoryPack.Formatters.ListFormatter`1'],[u['typeName'] for u in factory['usages'][:2]]);image.check_windows(factory['windows'],label=LABEL);image.check_instruction_windows(factory['instructions'],label=LABEL)
 mapping=int_list_sources.factory_pair([(base+w['startRva'],image.window_bytes(w)) for w in factory['windows']],base+factory['entryRva'],type_handle=base+factory['typeHandleRva'],add=base+factory['addRva']);need('factory-cells',[base+u['usageCellRva'] for u in factory['usages']],[mapping[k] for k in ('keyTypeCell','valueTypeCell','addMethodInfoCell')])
 receiver=factory['receiverInstructions'];image.check_instruction_windows(receiver,label=LABEL);raw=b''.join(bytes.fromhex(r[1]) for r in receiver);need('factory-receiver-contiguous',raw,image.pe.bytes_at_va(base+receiver[0][0],len(raw)));from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
 int_list_sources.factory_receiver(decode_type_data_initialization_instructions(image.mapper,raw,base+receiver[0][0]))
 usage=factory['usages'][2];need('factory-add-declaration',('System.Collections.Generic.Dictionary`2','Add',['System.Type','System.Type'],[]),tuple(usage[k] for k in ('typeName','methodName','classArguments','methodArguments')));need('factory-add-entry',base+factory['addRva'],entries.resolve(usage['methodSpec'][0],['object','object'],[])['pointer'])
 owner=ctx.index.types['MemoryPack.MemoryPackFormatterProvider'];field,=[f for f in image.metadata.fields_for(owner) if image.metadata.string(f.name_index)=='CollectionFormatters'];from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
 need('factory-receiver-field',('System.Collections.Generic.Dictionary`2<System.Type,System.Type>',True,8),(ctx.type_name(field.type_index),bool(ctx.field_attributes(field.type_index)&16),runtime_type_field_offsets(image.metadata,image.pe,image.registration,owner.index)['CollectionFormatters']))
 allocation=derive_typed_usage_context(image,receiver[0][0]-12,label=LABEL+'.factory-allocation');need('factory-allocation-type',(1,ctx.type_name(field.type_index)),(allocation['tag'],allocation['typeName']));need('factory-allocation-carrier',image.pe.bytes_at_va(ctx.type_pointer(field.type_index),8),image.pe.bytes_at_va(ctx.type_pointer(allocation['typeIndex']),8))
 constructor=derive_typed_usage_context(image,receiver[3][0],label=LABEL+'.factory-constructor');need('factory-dictionary-constructor',('System.Collections.Generic.Dictionary`2','.ctor',['System.Type','System.Type'],[]),tuple(constructor[k] for k in ('typeName','methodName','classArguments','methodArguments')))
 store_owner=derive_typed_usage_context(image,receiver[-3][0],label=LABEL+'.factory-static-owner');need('factory-static-owner',(1,'MemoryPack.MemoryPackFormatterProvider'),(store_owner['tag'],store_owner['typeName']));need('factory-static-store-instructions',['488B88B8000000','48897908'],[bytes.fromhex(r[1]).hex().upper() for r in receiver[-2:]])
 offsets=scalar.reader_offsets(image,LABEL);offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16;entry,regions=_list(image,reference,'object',context,entries);symbols={k:base+v for k,v in reference['symbolRvas'].items()}
 for count in (-1,0):
  for new in (False,True):reference_program(regions,entry['pointer'],offsets,symbols,count=count,new=new)
 entry,regions=_list(image,value,value['element'],context,entries);symbols={k:base+v for k,v in value['symbolRvas'].items()};need('value-constructor',entries.resolve(slots[1]['methodSpec'][0],[value['element']],[])['pointer'],symbols['constructor'])
 header=utf8_source_helper._contract();need('header-inputs',pins,header['nativeInputs']);body=header['bodies']['header'];need('header-call',base+body['entryRva'],symbols['header']);need('header-ownership',sorted(tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(body['entryRva'])['ranges']),sorted((w['startRva'],w['endRva']) for w in body['codeWindows']));image.check_windows(body['codeWindows'],label=LABEL+'.header');normal=[];cold=[]
 for w in body['codeWindows']:
  rows=decode_utf8_decoder_instructions(image.mapper,image.window_bytes(w),base+w['startRva'])
  if not normal or int(rows[0]['va'],16)==int(normal[-1]['va'],16)+len(bytes.fromhex(normal[-1]['bytes'])):normal+=rows
  else:cold+=rows
 hs={k:base+v for k,v in header['opaqueCalls'].items()};hs.update({k:base+header['methods'][k][3] for k in ('getNextSpan','insufficient')});prove_collection_header(normal,cold,offsets,hs)
 value_program(regions,entry['pointer'],symbols,null=True)
 for new in (False,True):value_program(regions,entry['pointer'],symbols,new=new)

def _validate_native(image,fact):
 ctx=NativeReferenceContext(image);pins=fact['nativeInputs'];records=validate_fields(image,pins,fact['fieldSources']);layout=fact['layout'];need('root-type','Beyond.Montage.NPCMontageJson',layout['root']);need('record-types',{'Beyond.Montage.NPCMontageJson','Beyond.Montage.NPCMontageAnim','Beyond.NPC.Animation.AnimClipInfo'},set(layout['records']))
 actual={}
 for record in records:
  rows=[]
  for field in record['fields']:
   wire='raw'+str(field['component']['proof']['bufferedCopyBytes']) if 'component' in field else {'bool':'bool','enum':'i32','scalar32':'i32','scalar64':'i64','float32':'f32','string':'pool','list':'null-empty-list'}.get(field['kind'],'i32' if field['declaredType']=='Beyond.Gameplay.Core.GameplayTag' else 'record')
   rows.append(dict(name=field['name'],type=field['declaredType'],wire=wire))
  actual[record['type']]=rows
 need('stored-layout',layout['records'],actual);need('registered-originals',set(actual),{r['originalType'] for r in fact['registrations']});need('factory-originals',set(actual),{r['original'] for r in fact['factories']})
 for flow in fact['registrations']:validate_eager_wrap_registration(image,flow,label=LABEL)
 reference_adapter_sources.validate_reference_routes(image,fact['referenceRoutes'],fact['compositions']);need('adapter-originals',set(actual),{r['original'] for r in fact['referenceRoutes']['wrappers']});validate_factories(image,fact['factories']);_collections(image,pins,fact,records)
 for raw in fact['rawValues']:
  td=ctx.index.types[raw['type']];need('raw-value-kind',True,ctx.is_value_type(raw['type']));fields=[f for f in image.metadata.fields_for(td) if not ctx.field_attributes(f.type_index)&16];actual_fields=[[image.metadata.string(f.name_index),canonical_type_name(ctx.type_name(f.type_index)),ctx.field(raw['type']+'::'+image.metadata.string(f.name_index))[2]-16] for f in fields];need('raw-value-fields',raw['fields'],actual_fields);pointer=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*td.index);need('raw-value-sizes',[raw['serializedBytes']+16,raw['nativeAbiBytes']],[image.pe.u32_at_va(pointer),image.pe.u32_at_va(pointer+4)])
 return layout

def validate(*,game_root=None,gameassembly=None,metadata=None,contract_path=None):
 path=Path(contract_path or CONTRACT_PATH)
 try:
  sources=snapshot_complete_reader_inputs()
  raw=path.read_bytes();fact=json.loads(raw);need('contract-schema',(SCHEMA,'exact-current-build'),(fact['schema'],fact['status']));need('pin-scope',{'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'},set(fact['nativeInputs']));need('string-encoding','int32-pool-index',fact['layout']['stringEncoding']);need('collection-counts',[-1,0],fact['layout']['collectionCounts'])
  if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.explicit-native-pair: both paths required')
  root=Path(game_root).resolve() if game_root is not None else None;pins=fact['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=Path(gameassembly).resolve() if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,metadata=Path(metadata).resolve() if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
  if gate.status!='validated':return dict(status=gate.status,failedGate='installed_native_inputs',detail=gate.detail)
  selected_gameassembly=Path(gate.gameassembly).resolve();selected_metadata=Path(gate.metadata).resolve()
  failed=pooled_source_helper.check_unity_input(selected_gameassembly,pins)
  if failed:return failed
  layout=_validate_native(open_native_image(selected_gameassembly,selected_metadata),fact);after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=selected_gameassembly,metadata=selected_metadata)
  if after.status!='validated':return dict(status=after.status,failedGate='installed_native_inputs_after',detail=after.detail)
  failed=pooled_source_helper.check_unity_input(selected_gameassembly,pins)
  if failed:return failed
  if raw!=path.read_bytes():raise ValueError(LABEL+'.contract-changed-during-validation')
  source_after=snapshot_complete_reader_inputs()
  if sources!=source_after:raise ValueError(LABEL+'.reader-sources-changed:'+str(reader_input_changes(sources,source_after)))
  return dict(status='validated',layout=layout,rawValues=fact['rawValues'],nativeInputs=pins,nativeSources={'GameAssembly.dll':str(selected_gameassembly),'global-metadata.dat':str(selected_metadata)},evidenceBoundary=fact['evidenceBoundary'])
 except (OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,StopIteration) as error:return native_validation_failure(error,label=LABEL,source_path=path)
