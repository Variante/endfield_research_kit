"""Authenticate the current conditional generated Int32-list source grammar."""
import json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts,validate_typed_usage_context
from scripts.game_data.il2cpp.consumer_instructions import decode_consumer_instructions
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.memorypack import int_list_sources as source,pooled_source_helper
from scripts.game_data.memorypack.scalar_param_native import reader_offsets
from scripts.game_data.memorypack.list_reference_sources import validate_list_element_context
from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context

CONTRACT_PATH=CONTRACTS_DIR/'levelscript_int_list_native.json'
SCHEMA='endfield.levelscript-int-list-native.v1'
LABEL='levelscriptIntListNative'
KIND='List<int>'


def need(check,expected,actual):
 if expected!=actual:raise ValueError(f'{LABEL}.{check}: expected={str(expected)[:320]} actual={str(actual)[:320]}')


def _validate_native(image,fact):
 need('bodyRoles',['Add','Clear','arrayCopy','arrayFastCopy','capacity','contextResolver','dispatcher','growth','integer','list','providerBackend'],sorted(fact['bodies']))
 base=image.pe.image_base;selected=NativeReferenceContext(image);entries=GenericEntries(image);contexts=fact['genericContexts'];validate_generic_contexts(image,contexts,label=LABEL)
 need('contextOwners',['MemoryPack.Formatters.ListFormatter`1','MemoryPack.Formatters.UnmanagedFormatter`1','System.Collections.Generic.List`1'],[c['typeName'] for c in contexts])
 offsets=reader_offsets(image,LABEL);offsets['totalLength']=selected.field('MemoryPack.MemoryPackReader::totalLength')[2]-16;need('readerFields',fact['readerFields'],offsets)
 fail=lambda check,expected,actual:need(check,expected,actual)
 validate_list_element_context(image,contexts[0],entries,fail=fail);validate_capacity_constructor_context(image,contexts[0],contexts[2],entries,fail=fail)
 bodies={}
 for role,record in fact['bodies'].items():
  windows=record['windows'];image.check_windows(windows,label=LABEL);regions=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])) for w in windows]
  if record.get('registration') is not None:
   entry=entries.resolve(record['methodDefinition'],['int'],[]);need(role+'.registration',record['registration'],json.loads(json.dumps(entry)));need(role+'.entry',record['entryRva'],entry['pointer']-base)
   argument=image.instantiations.resolve(entry['classInstantiation']['index']).arguments;need(role+'.argumentCount',1,len(argument));raw=image.pe.bytes_at_va(argument[0].type_pointer_va,16);need(role+'.argumentAbi',(8,128),(raw[10],raw[11]))
  if record['ownership']=='completeUnwindFamily':
   expected=sorted(tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(record['entryRva'])['ranges']);need(role+'.ownedWindows',expected,sorted((w['startRva'],w['endRva']) for w in windows))
  elif record['ownership']=='closedLeafEntry' and role=='Clear':
   leaf=decode_closed_leaf_entry(image.mapper,regions[0][1],base+record['entryRva']);need(role+'.closedBytes',len(regions[0][1]),sum(len(bytes.fromhex(r['bytes'])) for r in leaf['rows']))
  elif role!='contextResolver' or record['ownership']!='selectedInitializedPrefixes':raise ValueError(LABEL+'.ownership:'+role)
  bodies[role]=(regions,base+record['entryRva'])
 for role,name,owner in [('list','Deserialize',contexts[0]['definition']),('integer','Deserialize',contexts[1]['definition']),('capacity','.ctor',contexts[2]['definition']),('Add','Add',contexts[2]['definition']),('Clear','Clear',contexts[2]['definition']),('growth','AddWithResize',contexts[2]['definition'])]:
  record=fact['bodies'][role];method=image.metadata.methods[record['methodDefinition']];need(role+'.method',(owner,name,False),(method.declaring_type,image.metadata.string(method.name_index),bool(method.flags&0x10)))
  if role in ('list','integer'):
   parameters=list(image.metadata.parameters_for(method));need(role+'.arity',2,len(parameters));need(role+'.result','void',selected.type_name(method.return_type));raws=[image.pe.bytes_at_va(selected.type_pointer(p.type_index),16) for p in parameters];need(role+'.reader','MemoryPack.MemoryPackReader',selected.type_name(parameters[0].type_index));need(role+'.byrefs',[True,True],[bool(raw[11]&0x20) for raw in raws]);need(role+'.outputKind',21 if role=='list' else 19,raws[1][10])
   word=image.metadata.sections['vtableMethods'];td=image.metadata.types[owner];encoded=struct.unpack_from('<I',image.metadata.buf,word.offset+4*(td.vtable_start+5))[0];need(role+'.slotFive',(1,3,method.index),(encoded&1,encoded>>29,(encoded&0x1fffffff)>>1))
   if role=='list':need('list.ownedOutput',image.pe.bytes_at_va(selected.type_pointer(contexts[0]['entries'][0]['index']),16)[:8],raws[1][:8])
   else:
    section=image.metadata.sections['genericContainers'];definition,arity,is_method,start=struct.unpack_from('<iiii',image.metadata.buf,section.offset+td.generic_container_index*16);need('integer.ownedOutput',(td.index,1,0,start),(definition,arity,is_method,int.from_bytes(raws[1][:8],'little')))
 slots={r['relativeSlot']:r for r in contexts[2]['entries']};owner=image.metadata.types[contexts[2]['definition']];section=image.metadata.sections['genericContainers'];definition,count,is_method,start=struct.unpack_from('<iiii',image.metadata.buf,section.offset+owner.generic_container_index*16);need('ListOwnedVar',(owner.index,1,0),(definition,count,is_method))
 for slot,name in [(11,'AddWithResize'),(12,'EnsureCapacity'),(24,'set_Capacity')]:
  row=slots[slot];spec=entries.specs[row['index']];method=image.metadata.methods[spec[0]];need('growthContext',(3,name,slots[11]['methodSpec'][1],-1,owner.index,False,'void'),(row['kind'],row['methodName'],spec[1],spec[2],method.declaring_type,bool(method.flags&0x10),selected.type_name(method.return_type)));params=list(image.metadata.parameters_for(method));need(name+'.arity',1,len(params));raw=image.pe.bytes_at_va(selected.type_pointer(params[0].type_index),16)
  if slot==11:need(name+'.ownedArgument',(19,0,start),(raw[10],raw[11],int.from_bytes(raw[:8],'little')))
  else:need(name+'.capacityArgument',(8,128,'int'),(raw[10],raw[11],selected.type_name(params[0].type_index)))
 calls={key:base+value for key,value in fact['calls'].items()};need('sameDispatcher',bodies['dispatcher'][1],calls['dispatcher']);need('sameGrowth',bodies['growth'][1],calls['grow']);need('sameCapacity',bodies['capacity'][1],calls['capacity'])
 for role,key in [('providerBackend','backend'),('contextResolver','resolveClass'),('arrayCopy','arrayCopy')]:need('calledBody.'+role,bodies[role][1],calls[key])
 methods=[m for m in image.metadata.methods_for(selected.index.types['System.Type']) if image.metadata.string(m.name_index)=='GetTypeFromHandle'];need('typeHandleMethodCount',1,len(methods));method=methods[0];need('typeHandleMethod',('System.Type',['System.RuntimeTypeHandle'],True,calls['typeFromHandle']),(selected.type_name(method.return_type),[selected.type_name(p.type_index) for p in image.metadata.parameters_for(method)],bool(method.flags&0x10),image.method_pointer_va(method)))
 proofs=[source.source(*bodies['list'],offsets,calls,null=True,count=0)]+[source.source(*bodies['list'],offsets,calls,new=new,count=count) for new in (False,True) for count in range(4)]+[source.source(*bodies['list'],offsets,calls,grow=True,count=1)]
 proofs.extend([source.integer(*bodies['integer'],offsets),source.dispatcher(*bodies['dispatcher'],offsets,prepare=calls['prepare'],callback=bodies['integer'][1]),source.clear(*bodies['Clear'])]);proofs.extend(source.add(*bodies['Add'],grow=grow,growth=calls['grow']) for grow in (False,True))
 growth={key:calls[key] for key in ('resolveClass','arrayClassReady','allocateRawArray','zeroMemory','arrayCopy')};proofs.extend(source.growth(*bodies['growth'],growth,empty=empty) for empty in (False,True));capacity=dict(resolveClass=calls['resolveClass'],arrayAllocate=calls['arrayAllocate'],barrier=calls['barrier']);proofs.extend(source.capacity(*bodies['capacity'],capacity,positive=positive) for positive in (False,True));proofs.extend([source.initialized_class(*bodies['contextResolver'],indexed=True),source.copy_array(*bodies['arrayCopy'],fast=bodies['arrayFastCopy'][1]),source.fast_copy(*bodies['arrayFastCopy'],move=calls['move'])])
 need('selectedPrograms',fact['selectedPrograms'],json.loads(json.dumps([p['selectedBytes'] for p in proofs])))
 provider=source.backend(*bodies['providerBackend'],{key:calls[key] for key in ('resolveClass','hash','equals')});need('backendProgram',fact['backendProgram'],json.loads(json.dumps(provider['selectedBytes'])));need('sameProviderClass',proofs[1]['provider']['classCell'],provider['providerClassCell']);validate_typed_usage_context(image,fact['backendContext'],label=LABEL);usage=fact['backendContext'];need('backendContext',('System.Collections.Concurrent.ConcurrentDictionary`2','TryGetValue',['System.Type','MemoryPack.IMemoryPackFormatter'],[]),(usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments']));need('backendMethodCell',base+usage['usageCellRva'],provider['methodInfoCell'])
 for usage in fact['factory']['usages']:validate_typed_usage_context(image,usage,label=LABEL)
 factory=fact['factory'];need('factoryTypes',['System.Collections.Generic.List`1','MemoryPack.Formatters.ListFormatter`1'],[u['typeName'] for u in factory['usages'][:2]]);image.check_windows(factory['windows'],label=LABEL);image.check_instruction_windows(factory['instructions'],label=LABEL)
 regions=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])) for w in factory['windows']];mapping=source.factory_pair(regions,base+factory['entryRva'],type_handle=base+factory['typeHandleRva'],add=base+factory['addRva']);need('factoryUsageCells',[base+u['usageCellRva'] for u in factory['usages']],[mapping[key] for key in ('keyTypeCell','valueTypeCell','addMethodInfoCell')]);usage=factory['usages'][2];need('factoryAdd',('System.Collections.Generic.Dictionary`2','Add',['System.Type','System.Type'],[]),(usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments']))
 need('factoryAddEntry',base+factory['addRva'],entries.resolve(usage['methodSpec'][0],['object','object'],[])['pointer'])
 receiver=factory['receiverInstructions'];image.check_instruction_windows(receiver,label=LABEL);start=receiver[0][0];raw=b''.join(bytes.fromhex(row[1]) for row in receiver);need('factoryReceiverContiguous',raw,image.pe.bytes_at_va(base+start,len(raw)));source.factory_receiver(decode_consumer_instructions(image.mapper,raw,base+start))
 owner=selected.index.types['MemoryPack.MemoryPackFormatterProvider'];fields=[f for f in image.metadata.fields_for(owner) if image.metadata.string(f.name_index)=='CollectionFormatters'];need('factoryFieldCount',1,len(fields));field=fields[0];offsets=runtime_type_field_offsets(image.metadata,image.pe,image.registration,owner.index);need('factoryField',('System.Collections.Generic.Dictionary`2<System.Type,System.Type>',True,8),(selected.type_name(field.type_index),bool(selected.field_attributes(field.type_index)&0x10),offsets['CollectionFormatters']))
 return dict(programs=len(proofs),wireCountBytes=4,wireElementBytes=4,nullCount=-1)


def validate(*,gameassembly=None,metadata=None,contract_path=CONTRACT_PATH):
 try:
  path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw)
  need('schema',(SCHEMA,'exact-current-build',KIND),(fact['schema'],fact['status'],fact['codecKind']));need('nativeInputs',['GameAssembly.dll','UnityPlayer.dll','global-metadata.dat'],sorted(fact['nativeInputs']))
  if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.both-native-paths-required')
  pins=fact['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
  if gate.status!='validated':return dict(status=gate.status,codecKinds=[],detail=gate.detail,failedGate='installed_native_inputs')
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return dict(codecKinds=[],**failed)
  proof=_validate_native(open_native_image(gate.gameassembly,gate.metadata),fact);after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,codecKinds=[],detail='Native inputs changed: '+after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return dict(codecKinds=[],**failed)
  if raw!=path.read_bytes():raise ValueError(LABEL+'.contract-changed-during-validation')
  return dict(status='validated',codecKinds=[KIND],nativeInputs=pins,proof=proof,evidenceBoundary=fact['evidenceBoundary'])
 except (OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error) as error:return dict(codecKinds=[],**native_validation_failure(error,label=LABEL,source_path=contract_path))
