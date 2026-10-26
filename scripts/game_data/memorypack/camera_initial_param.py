"""Prove the selected camera initial-state Param and its raw managed value."""
import hashlib,json
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_registered_formatter_composition
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param as primitive,pooled_source_helper
LABEL='cameraInitialParam'
VALUE='Beyond.Gameplay.View.CameraControlStateInitialParam'


def parent_program(regions,entry,offsets,slots,targets,*,null=False,allocate=False):
 g=BytesPath(regions,entry)
 g.take('48895c2418','57','4883ec30');scalar.need(LABEL,'initializedFlag',targets['initFlag'],g.relative('803d')+1);g.take('00')
 g.take('488bfa','488bd9');g.branch('0f84',False)
 g.take('488d542440','c644244000','488bcb');g.call(targets['header']);g.take('84c0');g.branch('0f84',null)
 if null:
  g.take('488bcf','48c70700000000');g.call(targets['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4889742448','48833f00');g.branch('0f84',allocate)
  if allocate:
   cell=g.relative('488b0d');scalar.need(LABEL,'allocationCell',targets['wrapperCell'],cell)
   g.call(targets['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False)
   g.take('33d2','488bc8');g.call(targets['ctor']);g.take('488bcf','488937');g.call(targets['barrier']);g.take('90');g.jump('e9')
  cur,rem=(offsets[n] for n in ('currentPtr','bufferLength'))
  g.take('0fb6742440','4080fe04');g.branch('0f85',False)
  g.take('837b'+bytes((rem,24)).hex(),'488b37');g.branch('0f8c',False)
  g.take('488b43'+bytes((cur,)).hex(),'ba18000000','488bcb','0f1000','0f11442420','f20f104010','f20f11442440');g.call(targets['advance'])
  g.take('4885f6');g.branch('0f84',False);g.take('488b4610','4885c0');g.branch('74',False,1)
  slot=slots['constValue'];g.take('0f10442420','488bcb','0f1140'+bytes((slot,)).hex(),'f20f10442440','f20f1140'+bytes((slot+16,)).hex(),'488b37');g.call(targets['integer'])
  g.take('4885f6');g.branch('74',False,1);g.take('4533c0','8bd0','488bce');g.call(targets['idSetter'])
  g.take('488b37','488bcb');g.call(targets['integer']);g.take('4885f6');g.branch('74',False,1);g.take('4533c0','8bd0','488bce');g.call(targets['sourceSetter'])
  g.take('488b3f','488bcb');g.call(targets['path']);g.take('4885ff');g.branch('74',False,1);g.take('4533c0','488bd0','488bcf');g.call(targets['pathSetter']);g.take('488b742448')
 g.take('488b5c2450','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,wireBytes=1 if null else 37,constantBytes=0 if null else 24)


def derive(image,pins,profile):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);wrappers=derive_from_image(image)
 wrapped='Beyond.Gameplay.Actions.Param`1<'+VALUE+'>';w,=[x for x in wrappers.values() if x.wrapped_type==wrapped]
 scalar.need(LABEL,'members',[('constValue',VALUE),('idRef','int'),('paramSource','int'),('path','string')],[(m.name,m.declared_type) for m in w.members])
 scalar.need(LABEL,'holder',(w.name,wrapped,16),ctx.field(w.name+'::__instance'))
 definition=ctx.index.types[VALUE];fields=[]
 scalar.need(LABEL,'valueType',True,ctx.is_value_type(VALUE))
 for f in md.fields_for(definition):
  if ctx.field_attributes(f.type_index)&16:continue
  name=md.string(f.name_index);kind=ctx.type_name(f.type_index);offset=ctx.field(VALUE+'::'+name)[2]-16
  scalar.need(LABEL,'fieldKind',True,kind in ('bool','float'));scalar.ordinary(image,ctx.type_pointer(f.type_index),2 if kind=='bool' else 12,LABEL+'.field')
  fields.append([name,kind,offset])
 scalar.need(LABEL,'reviewedFields',profile['fields'],fields)
 sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+definition.index*8)
 scalar.need(LABEL,'managedValueBytes',24,image.pe.u32_at_va(sizes)-16)
 occupied=[b for _,kind,at in fields for b in range(at,at+(1 if kind=='bool' else 4))]
 scalar.need(LABEL,'disjointValueFields',True,len(set(occupied))==len(occupied) and all(0<=x<24 for x in occupied))
 methods={md.string(m.name_index):m for m in md.methods_for(md.types[w.type_definition])};record=vector_recorder(image)
 def named(name):
  m=methods[name];at=image.method_pointer_va(m);end=at+5 if name=='GetValue' else image.body_index.extents[at];raw=image.pe.bytes_at_va(at,end-at)
  return dict(methodIndex=m.index,pointerRva=at-base,window=dict(startRva=at-base,endRva=end-base,sha256=hashlib.sha256(raw).hexdigest().upper()),instructions=[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in image.body_index._decode(at,end-at)])
 own={n:named(n) for n in ('.ctor','CreateInstance','GetValue','set___constValue__','set___idRef__','set___paramSource__','set___path__')};slots={}
 for n in ('idRef','paramSource','path'):
  m=own['set___'+n+'__'];rows=m['instructions'];slot=bytes.fromhex(rows[4 if n=='path' else 6][1])[-1];slots[n]=slot
  scalar.owned_method_abi(image,ctx,m['methodIndex'],w.type_definition,('void',1,False),[('string',14,True) if n=='path' else ('int',8,False)],LABEL+'.setter')
  scalar.parameter_setter(image,rows,name=n,slot=slot,width=4,label=LABEL+'.'+n)
 setter=own['set___constValue__'];rows=setter['instructions'];slot=bytes.fromhex(rows[8][1])[-1];slots['constValue']=slot
 scalar.owned_method_abi(image,ctx,setter['methodIndex'],w.type_definition,('void',1,False),[(VALUE,17,False)],LABEL+'.constantSetter')
 scalar.program(image,rows,[bytes.fromhex(x) if x else None for x in ('4883ec28','488b4110','4885c0','7506',None,'cc','0f1002','f20f104a10','0f1140'+bytes((slot,)).hex(),'f20f1148'+bytes((slot+16,)).hex(),'4883c428','c3')],LABEL+'.constantSetter')
 scalar.need(LABEL,'ownedSlots',True,len(set(b for n,size in (('constValue',24),('idRef',4),('paramSource',4),('path',8)) for b in range(slots[n],slots[n]+size)))==40)
 scalar.program(image,own['GetValue']['instructions'],[bytes.fromhex('488b4110'),bytes.fromhex('c3')],LABEL+'.getter')
 for n in ('.ctor','CreateInstance','GetValue'):scalar.owned_method_abi(image,ctx,own[n]['methodIndex'],w.type_definition,(wrapped,21,True) if n=='GetValue' else ('void',1,False),[],LABEL+'.'+n)
 load,=[r for r in own['.ctor']['instructions'] if bytes.fromhex(r[1])[:3]==bytes.fromhex('488b0d')];allocation=derive_typed_usage_context(image,load[0],label=LABEL)
 scalar.need(LABEL,'allocationType',wrapped,allocation['typeName']);scalar.allocation_bridge(image,ctx,dict(methods=own,ownedFieldSlots=slots,allocationContext=allocation),LABEL)
 at=image.method_pointer_va(methods['Deserialize']);primitive.reader_abi(image,ctx,methods['Deserialize'],w)
 windows=[];regions=[];allrows=[]
 for part in image.unwind_index.family(at-base)['ranges']:
  a,b=part['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,b-a);regions.append((base+a,raw));windows.append(dict(startRva=a,endRva=b,sha256=hashlib.sha256(raw).hexdigest().upper()));allrows+=image.body_index._decode(base+a,b-a)
 end=at
 for start,raw in sorted(regions):
  if start==end:end=start+len(raw)
 main=sorted([r for r in allrows if at<=int(r['va'],16)<end],key=lambda r:int(r['va'],16));calls=[control_transfer(r)['target'] for r in main if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe8]
 scalar.need(LABEL,'mainCalls',13,len(calls))
 header,advance,integer,idsetter,integer2,sourcesetter,path,pathsetter,error,*initializers=calls
 scalar.need(LABEL,'sameInteger',integer,integer2)
 targets=dict(header=header,advance=advance,integer=integer,idSetter=idsetter,sourceSetter=sourcesetter,path=path,pathSetter=pathsetter,initFlag=at+17+int.from_bytes(image.pe.bytes_at_va(at+12,4),'little',signed=True),barrier=base+allocation_bridge_target(own),wrapperCell=0,allocate=0,ctor=base+own['.ctor']['pointerRva'])
 for n,key in (('idRef','idSetter'),('paramSource','sourceSetter'),('path','pathSetter')):scalar.need(LABEL,'namedSetter',base+own['set___'+n+'__']['pointerRva'],targets[key])
 allocrows=[r for r in allrows if bytes.fromhex(r['bytes'])[:3]==bytes.fromhex('488b0d')]
 wrapperload=next(r for r in allocrows if derive_typed_usage_context(image,int(r['va'],16)-base,label=LABEL).get('typeName')==w.name)
 usage=derive_typed_usage_context(image,int(wrapperload['va'],16)-base,label=LABEL);targets['wrapperCell']=base+usage['usageCellRva'];n=allrows.index(wrapperload);targets['allocate']=control_transfer(allrows[n+1])['target']
 offsets=scalar.reader_offsets(image,LABEL);headerproof=record(header-base);primitive.object_header_source(image,headerproof,offsets);advanceproof=record(advance-base,fragments=True);scalar.advance_source(image,advanceproof,offsets,LABEL+'.advance');integerproof=record(integer-base);scalar.integer_source(image,integerproof,offsets,LABEL+'.integer');pool=pooled_source_helper.validate_on_image(image,path,pins)
 paths=[parent_program(regions,at,offsets,slots,targets,**options) for options in ({},{'allocate':True},{'null':True})]
 registration=profile['registration'];composition=profile['composition'];validate_eager_wrap_registration(image,registration,label=LABEL+'.registration');validate_registered_formatter_composition(image,composition,label=LABEL+'.composition')
 scalar.need(LABEL,'registeredType',wrapped,registration['originalType']);scalar.need(LABEL,'compositionType',[wrapped],[r['originalType'] for r in composition['registrations']])
 formatter=composition['methods'][1];f=record(formatter[3],fragments=True);frows=image.body_index._decode(base+f['window']['startRva'],f['window']['endRva']-f['window']['startRva']);fcalls=[control_transfer(r)['target'] for r in frows if bytes.fromhex(r['bytes'])[:1]==b'\xe8'];forward=prove_zero_wrapper_forwarder(frows,dict(metadataInit=fcalls[0],classInit=fcalls[1]),at,label=LABEL+'.forward')
 return json.loads(json.dumps(dict(fields=fields,managedSize=24,marshalledSize=image.pe.u32_at_va(sizes+4),ownedMethods=own,allocation=allocation,slots=slots,readerWindows=windows,paths=paths,targets=targets,readerFieldOffsets=offsets,header=headerproof,advance=advanceproof,integer=integerproof,pooledPath=pool,forwarding=forward,evidenceBoundary=dict(direct='Selected generated four-member Param copies the complete managed 24-byte camera initial value, including padding, with two Int32 bindings and a pooled path; parent null and allocating routes are proved.',conditional='Initialized coherent generated wrapper and formatter route, matching initialized StringPool, disjoint valid storage, sufficient contiguous input and ordinary helper/allocation/barrier ABI.',unresolved=['live provider default/cache/override selection','cold refill and malformed paths','runtime camera execution']))))


def allocation_bridge_target(own):
 rva,encoded=own['.ctor']['instructions'][14];raw=bytes.fromhex(encoded)
 scalar.need(LABEL,'barrierTail',0xe9,raw[0]);return rva+5+int.from_bytes(raw[1:],'little',signed=True)
