"""Two independent nominal Param constants and their actual source programs.

NpcBehaviorTag uses its own raw four-byte ReadUnmanaged path, independent of
its unused MC1 wrapper. ForbidPhaseItem uses an ordinary reference callback
and its complete finite generated record subtree. Neither identity follows
from a matching width, pointer, enum name or a retained report.
"""
import json,struct

NPC='Beyond.Gameplay.AI.Config.NpcBehaviorTag'
FORBID='Beyond.Gameplay.ForbidSettings+ForbidPhaseItem'
PHASE='Beyond.Gameplay.PhaseForbidParams'
TYPES=(NPC,FORBID)
SCHEMA='endfield.actionmap-nominal-constant-capability.v1'
RECORD_SCHEMA='endfield.actionmap-nominal-record-capability.v1'


def need(check,value,detail=None):
 if not value:raise ValueError('actionNominalParam.'+check+(':'+str(detail)[:1800]if detail is not None else''))


def npc_layout(image,ctx):
 from scripts.game_data.memorypack import scalar_param_native as scalar
 md=image.metadata;td=ctx.index.types[NPC];tag='Beyond.Gameplay.Core.GameplayTag'
 need('own-nongeneric-Npc-value',ctx.is_value_type(NPC)and not ctx.is_enum(NPC)and td.generic_container_index<0 and ctx.parent(NPC)=='System.ValueType')
 fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 actual=[[md.string(f.name_index),*ctx.field(NPC+'::'+md.string(f.name_index))[1:]]for f in fields]
 need('own-Npc-tag-field',actual==[['tag',tag,16]])
 scalar.ordinary(image,ctx.type_pointer(fields[0].type_index),17,'actionNominalParam.NpcTag')
 child=ctx.index.types[tag];fs=[f for f in md.fields_for(child)if not ctx.field_attributes(f.type_index)&16]
 need('own-GameplayTag-Int32',ctx.is_value_type(tag)and not ctx.is_enum(tag)and child.generic_container_index<0
  and len(fs)==1 and ctx.field(tag+'::'+md.string(fs[0].name_index))==(tag,'int',16))
 scalar.ordinary(image,ctx.type_pointer(fs[0].type_index),8,'actionNominalParam.GameplayTag')
 sizes=[]
 for definition in(td,child):
  need('owned-size-table-index',0<=definition.index<image.registration['typeDefinitionsSizesCount'])
  at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+definition.index*8)
  pair=(image.pe.u32_at_va(at),image.pe.u32_at_va(at+4));need('independent-managed4-layout',pair==(20,4));sizes.append(list(pair))
 return dict(typeName=NPC,typeDefinition=td.index,fields=actual,tagDefinition=child.index,
  tagField=[md.string(fs[0].name_index),'int',16],boxedBytes=20,managedBytes=4,
  referenceLaneOffsets=[],paddingByteRanges=[],sizeRows=sizes,enum=False,wireGrammarInferredFromSize=False)


def _npc(image,pins):
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.context import method_parameter_owner
 from scripts.game_data.memorypack.current_reference_param_sources import derive_value4_parent
 from scripts.game_data.memorypack import scalar_param_native as scalar
 from scripts.game_data.memorypack.nominal_int32_value_sources import _buffered_source
 ctx=NativeReferenceContext(image);md=image.metadata;parent=derive_value4_parent(image,pins,value_type=NPC)
 nominal=npc_layout(image,ctx);usage=parent['typedRead'];base=image.pe.image_base
 argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
 scalar.ordinary(image,argument.type_pointer_va,17,'actionNominalParam.NpcArgument')
 raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
 need('own-Npc-closed-value-argument',usage.get('tag')==6 and usage['methodSpec'][1]==-1
  and int.from_bytes(raw[:8],'little')==nominal['typeDefinition']and raw[11]&0x80)
 method=md.methods[usage['methodSpec'][0]];section=md.sections['genericContainers'];at=section.offset+method.generic_container_index*16
 need('own-Npc-generic-instance-source',method.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16
  and image.type_name(method.declaring_type)=='MemoryPack.MemoryPackReader'and md.string(method.name_index)=='ReadUnmanaged'
  and not method.flags&16 and method.parameter_count==0)
 owner,count,is_method,start=struct.unpack_from('<iiii',md.buf,at)
 parameter=method_parameter_owner(md.buf,start,[m.generic_container_index for m in md.methods],source='actionNominalParam.Npc')
 returned=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
 need('own-Npc-reciprocal-return-MVAR',(owner,count,is_method)==(method.index,1,1)and parameter['methodIndex']==method.index
  and parameter['ordinal']==0 and returned[10:12]==bytes((30,0))and int.from_bytes(returned[:8],'little')==start)
 target=parent['programs'][0]['sourceCalls']['constValue'];offsets=scalar.reader_offsets(image,'actionNominalParam.Npc')
 actual=_buffered_source(image,target,offsets);registered=GenericEntries(image).resolve(method.index,[],[NPC])
 canonical=actual if registered['pointer']==target else _buffered_source(image,registered['pointer'],offsets)
 need('own-Npc-whole-raw4-transfer',all(p['constantStoredBytes']==4 and p['constantResultRegister']=='eax'
  and p['constantSetterArgumentRegister']=='edx'for p in parent['programs'])
  and actual['wireBytes']==canonical['wireBytes']==4 and actual['resultRegister']==canonical['resultRegister']=='eax')
 cap=dict(schema=SCHEMA,valueType=NPC,wireKind='npc-behavior-tag-raw4',wireBytes=4,fieldOrder=['tag'],
  rawBitsPreserved=True,wrapperFramingUsed=False,firstFFIsRawData=True,constantSourceProved=True,fullParamSourceProved=True,
  actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,runtimeValueEvaluationAdmitted=False,wholeOwnerAdmitted=False)
 return dict(currentParent=parent,layout=nominal,typedRequest=usage,closedArgumentRawHex=raw.hex().upper(),
  methodParameterOwner=parameter,returnTypeRawHex=returned.hex().upper(),actualRawSource=actual,registeredRawSource=canonical,
  closedRegistration=registered,actualPointerEqualsRegistered=registered['pointer']==target,pointerAliasInferred=False),cap


def _record_inventory(image):
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack.wrapper_members import derive_from_image
 ctx=NativeReferenceContext(image);all_wrappers=list(derive_from_image(image).values());selected={};pending=[FORBID]
 while pending:
  name=pending.pop(0)
  if name in selected:continue
  need('bounded-finite-Forbid-subtree',len(selected)<8 and name in(FORBID,PHASE),name)
  wrappers=[w for w in all_wrappers if w.wrapped_type==name];need('one-own-Forbid-subtree-wrapper',len(wrappers)==1,name)
  td=ctx.index.types[name];need('ordinary-nongeneric-reference-child',not ctx.is_value_type(name)and not ctx.is_enum(name)and td.generic_container_index<0,name)
  wrapper=wrappers[0];selected[name]=wrapper
  for member in wrapper.members:
   typ=member.declared_type
   if typ in('bool','byte','int','uint','long','ulong','float','double','string')or ctx.is_enum(typ):continue
   need('explicit-finite-record-reference-child',typ in(FORBID,PHASE),dict(owner=name,field=member.name,typeName=typ))
   pending.append(typ)
 need('exact-Forbid-Phase-subtree',set(selected)=={FORBID,PHASE})
 need('exact-Forbid-member-order',[(m.name,m.declared_type)for m in selected[FORBID].members]==[('forbidPhaseParams',PHASE),('phaseName','string')])
 return selected


def observe(image,pins):
 """Capture independent root/child declarations and owned bodies before admission."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack.wrapper_members import derive_from_image
 from scripts.game_data.memorypack import pointer_param as pointer
 _publication_gate(image,pins);ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base
 wrappers=list(derive_from_image(image).values());owners=[]
 for name in(NPC,FORBID,PHASE):
  td=ctx.index.types.get(name);record=dict(typeName=name,wrappers=[],originalMethods=[])
  if td is None:record['pending']='current-nominal-definition-absent';owners.append(record);continue
  record['fields']=[[md.string(f.name_index),ctx.type_name(f.type_index),ctx.field_attributes(f.type_index)]for f in md.fields_for(td)]
  for method in md.methods_for(td):
   if md.string(method.name_index)!='.ctor':continue
   row=dict(name='.ctor',index=method.index,targetRva=image.method_pointer_va(method)-base)
   try:
    body=pointer.owned(image,base+row['targetRva']);row.update(sourceWindows=body['windows'],sourceRegions=[[a,b.hex().upper()]for a,b in body['regions']])
   except(ValueError,KeyError,IndexError)as e:row['pending']=str(e)[:1500]
   record['originalMethods'].append(row)
  for wrapper in[w for w in wrappers if w.wrapped_type==name]:
   selected=dict(wrapperName=wrapper.name,members=[m.row()for m in wrapper.members],methods=[])
   for method in md.methods_for(md.types[wrapper.type_definition]):
    role=md.string(method.name_index)
    if role not in('.ctor','CreateInstance','GetValue','Deserialize')and not role.startswith('set___'):continue
    row=dict(name=role,index=method.index,targetRva=image.method_pointer_va(method)-base)
    try:
     body=pointer.owned(image,base+row['targetRva']);row.update(sourceWindows=body['windows'],sourceRegions=[[a,b.hex().upper()]for a,b in body['regions']])
    except(ValueError,KeyError,IndexError)as e:row['pending']=str(e)[:1500]
    selected['methods'].append(row)
   record['wrappers'].append(selected)
  owners.append(record)
 _publication_gate(image,pins)
 return dict(schema='endfield.actionmap-nominal-child-observations.v1',nativeInputs=pins,owners=owners,nativeAdmissionGranted=False)


def _forbid(image,pins):
 from scripts.game_data.memorypack.current_reference_param_sources import derive_reference_parent
 from scripts.game_data.memorypack.levelscript_condition_param_sources import _reader
 from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.skill_root_child_bindings import bind_read_value
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 selected=_record_inventory(image);reader=_reader(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 parent=derive_reference_parent(image,pins,value_type=FORBID,reader_method='ReadValue',constant_kind=18)
 argument,=image.instantiations.resolve(parent['typedRead']['methodSpec'][2]).arguments
 scalar.ordinary(image,argument.type_pointer_va,18,'actionNominalParam.ForbidArgument',reference=True)
 need('own-Forbid-ordinary-class-argument',int.from_bytes(image.pe.bytes_at_va(argument.type_pointer_va,16)[:8],'little')==ctx.index.types[FORBID].index
  and parent['typedRead']['methodSpec'][1]==-1 and not ctx.is_value_type(FORBID))
 need('same-own-Forbid-ReadValue-definition-and-target',parent['typedRead']['methodSpec'][0]==reader['readerMethodDefinition']
  and parent['programs'][0]['sourceCalls']['constValue']==base+reader['sourceTargetRva'])
 source_batch=generated_reader_sources.derive_many(image,pins,[w.name for w in selected.values()]);sources={}
 for row in source_batch['owners']:
  need('complete-Forbid-record-source',row.get('status')=='complete-reader-source-proved',row)
  sources[row['proof']['wrappedType']]=row['proof']
 components={};programs={};proofs={};visiting=set()
 def record(name):
  if name in components:return components[name]
  need('acyclic-finite-Forbid-record-graph',name not in visiting);visiting.add(name)
  source=sources[name];wrapper=selected[name];pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrapper)
  getter=source['lifecycle']['GetValue'];face,=pair['composition']['interfaces']
  need('same-own-record-source-and-canonical-adapter',adapter['typeName']==name and adapter['wrapperName']==wrapper.name
   and adapter['getterMethod']==getter['method']and adapter['pair']==json.loads(json.dumps(pair))
   and face['formatterDeserializeMethodIndex']==source['lifecycle']['concreteFormatter']['method'][0]
   and getter['program'].get('fullReferenceOutput')is True)
  references={};children={};typed={}
  for read in source['orderedSourceReads']:
   i=read['memberIndex'];typ=read['declaredType']
   if typ in selected:
    child=record(typ);references[typ]=(typ,'actionmap-nominal-record',typ);children[typ]=child
    typed[i]=derive_typed_usage_context(image,read['context']['instructionRva'],label='actionNominalParam.record')
  program,pending=compile_member_program(source,pins,wrapper_name=wrapper.name,type_name=name,value4={},
   references=references,reference_children=children,typed_requests=typed,reference_binder=bind_read_value)
  need('complete-finite-Forbid-record-grammar',not pending,pending)
  cap=dict(schema=RECORD_SCHEMA,typeName=name,wrapperName=wrapper.name,memberCount=program['memberCount'],program=program,
   fields=[{k:r[k]for k in('memberIndex','fieldName','declaredType')}for r in source['orderedSourceReads']],
   enumBackings=source.get('sourceScope',{}).get('enumBackings',[]),
   ordinaryOriginalReadValueAdmitted=True,wholeGrammarAdmitted=True,referenceReaderMethodDefinition=reader['readerMethodDefinition'],
   referenceReaderTargetRva=reader['sourceTargetRva'],canonicalAdapterTargetRva=adapter['callbackBinding']['canonicalTargetRva'],
   actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
  components[name]=dict(nativeInputs=pins,capabilities={name:cap});programs[name]=cap
  proofs[name]=dict(source=source,pair=pair,adapter=adapter,typedRequests=typed);visiting.remove(name);return components[name]
 record(FORBID)
 cap=dict(schema=SCHEMA,valueType=FORBID,wireKind='forbid-phase-record',rootRecord=FORBID,records=programs,
  constantSourceProved=True,fullParamSourceProved=True,actualCallbackEqualsProvedChildRequired=True,
  liveFormatterSelectionObserved=False,runtimeValueEvaluationAdmitted=False,wholeOwnerAdmitted=False)
 return dict(currentParent=parent,referenceReader=reader,recordSources=proofs),cap


def derive_wire(image,pins,*,value_type):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.codecs.levelscript.current_action_nominal_param import validate_constant
 need('finite-own-nominal-domain',value_type in TYPES);_publication_gate(image,pins)
 proof,cap=_npc(image,pins)if value_type==NPC else _forbid(image,pins)
 validate_constant(cap,value_type);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(nativeInputs=pins,constantCapability=cap,proof=proof,parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
