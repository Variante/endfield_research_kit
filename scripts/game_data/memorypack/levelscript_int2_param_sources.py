"""Own Vector2Int Param warm source and canonical reference child.

The two Int32 axes, actual ReadUnmanaged qword and complete four-field wrapper
are independent proofs. No float-vector, scalar-eight-byte or enum alias is
used. Cold initialization/refill and runtime callback selection stay explicit.
"""
import hashlib,json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

VALUE='UnityEngine.Vector2Int'
TYPE='Beyond.Gameplay.Actions.Param`1<'+VALUE+'>'
SOURCE_SCHEMA='endfield.story-int2-param-source.v1'
SCHEMA='endfield.story-int2-param-components.v1'
CAPABILITY='story-condition-param:'+TYPE
LABEL='storyInt2Param'


def need(key,condition):
 if not condition:raise ValueError(LABEL+'.'+key)


def reader_program(regions,entry,*,existing,ff):
 from scripts.game_data.memorypack.param_setter_call_programs import reader_program as call_program
 program=call_program(regions,entry,existing=existing,ff=ff)
 for key in('constantStoredBytes','constantResultRegister','constantSetterArgumentRegister','constantWireGrammarAdmitted','nominalTypeAdmitted'):program.pop(key)
 program.update(constantWireBytes=8,constantRawInt32Axes=['x','y'])
 return program


def _record(image,target):
 end=image.body_index.extents[target];raw=image.pe.bytes_at_va(target,end-target);base=image.pe.image_base
 return dict(pointerRva=target-base,window=dict(startRva=target-base,endRva=end-base,sha256=hashlib.sha256(raw).hexdigest().upper()),
  instructions=[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()]for r in image.body_index._decode(target,end-target)])


def derive_source(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,primitive_param as primitive
 from scripts.game_data.memorypack import pooled_source_helper,generated_action_sources as actions,leveldata_int2_read_sources as int2
 from scripts.game_data.memorypack.wrapper_members import derive_from_image
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 wrappers=[w for w in derive_from_image(image).values()if w.wrapped_type==TYPE]
 need('one-exact-Int2-Param-wrapper',len(wrappers)==1);wrapper,=wrappers
 need('four-owned-exact-fields',[(m.name,m.declared_type)for m in wrapper.members]==[('constValue',VALUE),('idRef','int'),('paramSource','int'),('path','string')])
 need('own-closed-reference-holder',ctx.field(wrapper.name+'::__instance')==(wrapper.name,TYPE,16))
 methods={};bodies={};slots={};method_defs={}
 for name in('.ctor','CreateInstance','GetValue','Deserialize',*('set___'+m.name+'__'for m in wrapper.members)):
  found=[m for m in md.methods_for(md.types[wrapper.type_definition])if md.string(m.name_index)==name]
  need('one-owned-method:'+name,len(found)==1);method,=found;method_defs[name]=method;target=image.method_pointer_va(method)
  if name=='GetValue':
   body=pointer.leaf(image,target,['488B4110','C3']);record=dict(methodIndex=method.index,pointerRva=target-base,instructions=[[target-base,'488B4110'],[target-base+4,'C3']])
  else:
   body=pointer.owned(image,target);record=dict(methodIndex=method.index,**_record(image,target))
  bodies[name]=body;methods[name]=record
  if name=='Deserialize':primitive.reader_abi(image,ctx,method,wrapper)
  else:
   parameter={'constValue':(VALUE,17,False),'idRef':('int',8,False),'paramSource':('int',8,False),'path':('string',14,True)}
   scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,(TYPE,21,True)if name=='GetValue'else('void',1,False),
    [parameter[name[6:-2]]]if name.startswith('set___')else[],LABEL)
  if name.startswith('set___'):
   member=name[6:-2];rows=record['instructions'];nonnull=member=='path'and bytes.fromhex(rows[3][1])==b'\x75\x06'
   store=rows[(6 if nonnull else 4)if member=='path'else 6];slots[member]=bytes.fromhex(store[1])[-1]
   scalar.parameter_setter(image,rows,name=member,slot=slots[member],width=8,label=LABEL)
 occupied=[n for name,size in(('constValue',8),('idRef',4),('paramSource',4),('path',8))for n in range(slots[name],slots[name]+size)]
 need('whole-disjoint-named-field-effects',len(set(occupied))==24 and all(16<=x<128 for x in occupied))
 loads=[r for r in methods['.ctor']['instructions']if bytes.fromhex(r[1]).startswith(bytes.fromhex('488b0d'))]
 need('one-Original-typed-allocation',len(loads)==1);original_usage=derive_typed_usage_context(image,loads[0][0],label=LABEL+'.Original')
 need('own-original-closed-reference-allocation',original_usage.get('typeName')==TYPE)
 parameter=dict(methods=methods,ownedFieldSlots=slots,allocationContext=original_usage)
 scalar.allocation_bridge(image,ctx,parameter,LABEL)
 body=bodies['Deserialize'];entry=base+methods['Deserialize']['pointerRva']
 programs=[reader_program(body['regions'],entry,existing=existing,ff=ff)for existing,ff in((False,False),(True,False),(False,True),(True,True))]
 positive=[p for p in programs if not p['wrapperNull']];nulls=[p for p in programs if p['wrapperNull']]
 need('same-both-positive-source-identities',positive[0]['sourceCalls']==positive[1]['sourceCalls']and positive[0]['constantContext']==positive[1]['constantContext'])
 calls=positive[0]['sourceCalls'];need('same-owned-setters',all(calls['set'+name[0].upper()+name[1:]]==base+methods['set___'+name+'__']['pointerRva']for name in slots))
 allocation=positive[0]['allocation'];wrapper_usage=derive_typed_usage_context(image,allocation['instructionVa']-base,label=LABEL+'.wrapper')
 need('actual-wrapper-allocation-and-ctor',wrapper_usage.get('tag')==1 and wrapper_usage.get('typeName')==wrapper.name
  and allocation['constructorVa']==base+methods['.ctor']['pointerRva'])
 contexts,skipped=actions._contexts(image,body['rows']);need('one-actual-Int2-constant-context',len(contexts)==1);context,=contexts
 need('same-selected-nominal-constant-call',context.get('fullTypeName')==VALUE and context.get('register')=='rdx'
  and context.get('instructionRva')==positive[0]['constantContext']['instructionVa']-base)
 constant=int2.derive(image,pins,context=context,source_target=calls['constValue'])
 need('same-whole-RAX-source-and-named-field',constant.get('rawInt32Axes')==['x','y']and constant.get('wireBytes')==8
  and constant.get('managedBytes')==8 and constant.get('referenceLaneOffsets')==[]and constant.get('paddingByteRanges')==[])
 offsets=scalar.reader_offsets(image,LABEL);headers={p['headerTargetVa']for p in programs};need('one-whole-header',len(headers)==1)
 header=_record(image,next(iter(headers)));primitive.object_header_source(image,header,offsets)
 need('same-two-Int32-sources',calls['idRef']==calls['paramSource'])
 integer=_record(image,calls['idRef']);scalar.integer_source(image,integer,offsets,LABEL+'.integer')
 pool=pooled_source_helper.validate_on_image(image,calls['path'],pins)
 need('same-pool-index-tail',pool.get('wireEncoding')=='int32-pool-index')
 path_rows=methods['set___path__']['instructions'];tail=bytes.fromhex(path_rows[9 if bytes.fromhex(path_rows[3][1])==b'\x75\x06'else 7][1]);at=path_rows[9 if bytes.fromhex(path_rows[3][1])==b'\x75\x06'else 7][0]
 barrier=base+at+5+int.from_bytes(tail[1:],'little',signed=True)
 need('same-output-and-field-barrier',all(p['barrierTargetVa']==barrier for p in nulls)and positive[0]['barrierTargetVa']==barrier)
 for name in('.ctor','CreateInstance'):
  at,encoded=methods[name]['instructions'][-1];raw=bytes.fromhex(encoded)
  need('same-factory-reference-barrier',raw[0]==0xe9 and base+at+5+int.from_bytes(raw[1:],'little',signed=True)==barrier)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SOURCE_SCHEMA,status='proved-conditional-own-Int2-Param-source',nativeInputs=pins,typeName=TYPE,valueType=VALUE,
  wrapperName=wrapper.name,constantWireKind='int2-raw8',constantWireBytes=8,sourceAdmitted=True,canonicalAdapterAdmitted=False,
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,proof=dict(parameter=parameter,wrapperSourceFamily=image.unwind_index.family(entry-base),
   wrapperSourceWindows=body['windows'],wrapperSourceRegions=[[a-base,b.hex().upper()]for a,b in body['regions']],programs=programs,
   wrapperAllocation=wrapper_usage,constantSource=constant,constantContext=context,integerSource=integer,headerSource=header,
   pooledPath=pool,setterBodies={n:dict(b,**({'regions':[[a,raw.hex().upper()]for a,raw in b['regions']]}if 'regions'in b else{}))for n,b in bodies.items()},readerOffsets=offsets,barrierTargetRva=barrier-base,skippedRuntimeCells=skipped),
  evidenceBoundary=dict(exact='Own four-field Param, exact Int2 two-Int32 nominal/layout and actual typed qword read, complete four warm paths, named setters, typed Original/default idRef allocation and reference getter.',
   conditional='Own initialized metadata flags, sufficient buffered input, initialized matching pool, compatible typed zero-initialized allocation/calls and disabled reference barrier. Cold initialization/refill/runtime provider selection remain separate.',
   unresolved=['canonical adapter and ordinary parent request','whole containing owner/recursive graph/publication']))))


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack.levelscript_condition_param_sources import _reader,_reference_join,_capability
 from scripts.game_data.codecs.levelscript.current_condition_int2_param import validate,CAP_SCHEMA
 _publication_gate(image,pins);source=derive_source(image,pins);reader=_reader(image,pins);reference=_reference_join(image,pins,VALUE)
 need('same-whole-reference-getter',source['proof']['parameter']['methods']['GetValue']['methodIndex']==reference['getterMethodDefinition'])
 cap=_capability(VALUE,'int2-raw8',8,reader,reference['adapter']);cap.update(schema=CAP_SCHEMA,
  constantRawInt32Axes=['x','y'],constantValueEvaluationAdmitted=False)
 validate(cap);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,referenceReader=reader,
  owners=[dict(status='validated-conditional-Param-child',typeName=TYPE,valueType=VALUE,capability=cap,
   proof=dict(wrapperSource=source,**{k:v for k,v in reference.items()if k!='getterMethodDefinition'}),parentFieldAdmitted=False,wholeOwnerAdmitted=False)],
  capabilities={CAPABILITY:cap},parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
