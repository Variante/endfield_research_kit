"""Actual selected SimpleAssetLoader construction used by Patrol conversion.

Four normal source paths retain allocated dictionary/optional-helper objects,
copy the incoming enum bytes/DWORD, publish unchanged references and restore
the full frame. The three service-getter invocations keep independent results;
their Boolean selections are explicit. Allocation, nested constructors,
service getter effects and initialized MethodInfo/class state are conditions.
No live loader/asset, dictionary grammar or later TryLoad/Get effect follows.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-loader-constructor-source.v1'


def need(check,condition):
 if not condition:raise ValueError('storyPatrolLoader.'+check)


def enum_backing_kind(name,width):
 expected={(1,'byte'):5,(4,'int'):8,(4,'uint'):9}
 need('exact-enum-backing-for-actual-store:'+str((name,width)),(width,name)in expected)
 return expected[(width,name)]


def same_nominal_record(left,right):
 a=bytes.fromhex(left);b=bytes.fromhex(right)
 return len(a)==len(b)==16 and a[:8]==b[:8]and a[10:]==b[10:]


def program(regions,entry,*,selection):
 need('literal-service-selection',selection in('service-null','inner-null','ordinary','optional'))
 g=BytesPath(regions,entry);contexts=[];calls=[]
 def usage(role,prefix):
  at=g.at;cell=g.relative(prefix);contexts.append(dict(role=role,instructionVa=at,cellVa=cell))
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 g.take('48895c2408','48896c2410','4889742418','48897c2420','4156','4883ec20','488bd9','418bf1')
 usage('dictionary-allocation','488b0d');g.take('410fb6e8','440fb6f2');allocate=call('allocate-dictionary')
 g.take('488bf8','4885c0');g.branch('0f84',False);usage('dictionary-constructor','488b15');g.take('488bc8');call('construct-dictionary')
 g.take('488d4b');dictionary_field=int.from_bytes(g.read(1),'little');g.take('48897b')
 need('same-dictionary-field-address-and-store',g.read(1)==bytes((dictionary_field,)));barrier=call('publish-dictionary')
 g.take('448873');first=int.from_bytes(g.read(1),'little');g.take('40886b');second=int.from_bytes(g.read(1),'little')
 g.take('8973');third=int.from_bytes(g.read(1),'little')
 usage('service-getter','488b0d');service=call('service-getter');g.take('4885c0');g.branch('74',selection=='service-null',1)
 if selection!='service-null':
  usage('service-getter','488b0d');need('same-actual-service-getter',call('service-getter')==service)
  g.take('4885c0');g.branch('74',False,1);g.take('4883781000');g.branch('74',selection=='inner-null',1)
  if selection!='inner-null':
   usage('service-getter','488b0d');need('same-actual-service-getter',call('service-getter')==service)
   g.take('4885c0');g.branch('74',False,1);g.take('488b4010','4885c0');g.branch('74',False,1)
   g.take('80782d00');g.branch('0f85',selection=='optional')
   if selection=='optional':
    usage('optional-allocation','488b0d');need('same-selected-object-allocation-helper',call('allocate-optional')==allocate)
    g.take('488bf8','4885c0');g.branch('0f84',False);g.take('4533c0','33d2','488bc8');call('construct-optional')
    g.take('488d4b');optional_field=int.from_bytes(g.read(1),'little');g.take('48897b')
    need('same-optional-field-address-and-store',g.read(1)==bytes((optional_field,)))
    need('same-selected-optional-publication-barrier',call('publish-optional')==barrier);g.take('90');g.jump('e9')
   else:optional_field=None
  else:optional_field=None
 else:optional_field=None
 g.take('488b5c2430','488b6c2438','488b742440','488b7c2448','4883c420','415e','c3')
 need('distinct-nonoverlapping-source-selected-receiver-fields',len({dictionary_field,first,second,third})==4
  and all(16<=n<128 for n in(dictionary_field,first,second,third)))
 return dict(selectedBytes=g.seen,entry=entry,selection=selection,contexts=contexts,calls=calls,
  dictionaryFieldOffset=dictionary_field,optionalFieldOffset=optional_field,
  parameterTransfers=[dict(parameterIndex=0,argument='DL',bytes=1,fieldOffset=first),
   dict(parameterIndex=1,argument='R8B',bytes=1,fieldOffset=second),dict(parameterIndex=2,argument='R9D',bytes=4,fieldOffset=third)],
  serviceResultsAreIndependent=True,unprovedServiceIntermediateReferenceOffset=16,unprovedServiceFlagOffset=45,
  allocatedReferencesConstructedAndPublishedUnchanged=True,entryRspRestored=True,
  nonvolatilesRestored=['rbx','rbp','rsi','rdi','r14'],normalReturn=True,
  serviceGetterOrNestedConstructorEffectsProved=False,runtimeInvocationObserved=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import leveldata_patrol_constructor_sources as constructors,pointer_param as pointer,scalar_param_native as scalar
 _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
 parent=constructors.derive(image,pins);u=parent['proof']['actualTypedUsages']['loaderClass'];name=u['typeName'];td=ctx.index.types[name]
 ctor=md.methods[parent['proof']['actualTypedUsages']['loaderConstructor']['methodDefinition']]
 body=pointer.owned(image,image.method_pointer_va(ctor));programs=[program(body['regions'],body['pointer'],selection=s)for s in('service-null','inner-null','ordinary','optional')]
 need('same-exact-controller-allocated-concrete-constructor',body['pointer']==parent['proof']['programs'][constructors.CONTROLLER]['constructorTargetVa'])
 # Resolve each instruction-selected field through actual named ancestors.
 # No open generic offset or carrier layout is substituted.
 fields=[];ancestors=[];current=name
 while current and current not in ancestors:
  own=ctx.index.types[current];ancestors.append(current)
  for f in md.fields_for(own):
   if ctx.field_attributes(f.type_index)&16:continue
   field=list(ctx.field(current+'::'+md.string(f.name_index)))
   fields.append(dict(field=field,methodOwnerType=current,fieldIndex=f.index,typePointerVa=ctx.type_pointer(f.type_index),rawTypeHex=image.pe.bytes_at_va(ctx.type_pointer(f.type_index),16).hex().upper()))
  next_name=ctx.parent(current)
  if next_name=='object':
   scalar.ordinary(image,ctx.type_pointer(own.parent_index),28,SCHEMA+'.ObjectTerminal',reference=True);break
  need('actual-named-ordinary-loader-ancestor',not next_name or next_name in ctx.index.types);current=next_name
 def field_at(offset):
  matches=[f for f in fields if f['field'][2]==offset];need('one-own-instruction-selected-field:'+str(offset),len(matches)==1);return matches[0]
 parameters=list(md.parameters_for(ctor));parameter_fields=[]
 for transfer in programs[0]['parameterTransfers']:
  i=transfer['parameterIndex'];param=parameters[i];typ=ctx.type_name(param.type_index);enum=ctx.index.types[typ]
  scalar.ordinary(image,ctx.type_pointer(param.type_index),17,SCHEMA+'.enumParameter')
  backing,=[f for f in md.fields_for(enum)if not ctx.field_attributes(f.type_index)&16]
  backing_type=ctx.type_name(backing.type_index);kind=enum_backing_kind(backing_type,transfer['bytes'])
  need('own-parameter-enum-backing:'+typ,ctx.is_enum(typ)and md.string(backing.name_index)=='value__'
   and ctx.type_name(backing.type_index)==backing_type)
  scalar.ordinary(image,ctx.type_pointer(backing.type_index),kind,SCHEMA+'.enumBacking')
  f=field_at(transfer['fieldOffset']);need('same-actual-nominal-parameter-field:'+typ,f['field'][1]==typ
   and bytes.fromhex(f['rawTypeHex'])[10:12]==bytes((17,128))and int.from_bytes(bytes.fromhex(f['rawTypeHex'])[:8],'little')==enum.index)
  parameter_fields.append(dict(**transfer,field=f,enumTypeDefinition=enum.index,backingField=backing.index,backingType=backing_type))
 usages={};calls={}
 for p in programs:
  for c in p['contexts']:
   actual=derive_typed_usage_context(image,c['instructionVa']-base,label=SCHEMA+'.'+c['role'])
   if c['role']in usages:
    need('same-exact-repeated-service-context',all(actual[k]==usages[c['role']][k]for k in actual if k not in('instructionRva','instructionHex')))
   else:usages[c['role']]=actual
  for c in p['calls']:
   need('same-exact-repeated-helper-target:'+c['role'],c['role']not in calls or calls[c['role']]==c['targetVa']);calls[c['role']]=c['targetVa']
 need('same-independently-proved-disabled-collector',calls['publish-dictionary']==parent['proof']['programs'][constructors.CONTROLLER]['publicationTargetVa'])
 dictionary_field=field_at(programs[0]['dictionaryFieldOffset']);optional_field=field_at(programs[-1]['optionalFieldOffset'])
 for role,f in(('dictionary-allocation',dictionary_field),('optional-allocation',optional_field)):
  actual=usages[role];need('same-own-field-and-allocation-type:'+role,actual.get('tag')==1 and actual.get('typeName')==f['field'][1]
   and bytes.fromhex(actual['typeRawHex'])[10:12]in(bytes((18,0)),bytes((21,0)))and same_nominal_record(actual['typeRawHex'],f['rawTypeHex']))
 usage=usages['dictionary-constructor'];need('actual-dictionary-noarg-MethodSpec',usage.get('tag')==6 and usage.get('methodName')=='.ctor'
  and usage.get('methodArguments')==[]and usage.get('classArguments')and not md.methods[usage['methodSpec'][0]].parameter_count)
 getter=usages['service-getter'];need('actual-service-method-or-class-context',getter.get('tag')in(1,6))
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-loader-constructor-control-and-fields',nativeInputs=pins,
  proof=dict(controllerConstruction=parent,loaderTypeDefinition=td.index,constructorMethodDefinition=ctor.index,
   sourceWindows=body['windows'],sourceRegions=[[a,h.hex().upper()]for a,h in body['regions']],programs=programs,actualTypedUsages=usages,
   actualTargets={k:v-base for k,v in calls.items()},parameterFields=parameter_fields,ancestors=ancestors,dictionaryField=dictionary_field,optionalField=optional_field),
  completeSelectedLoaderConstructorControlAndFieldSourcesProved=True,loaderNestedConstructorEffectsProved=False,
  serviceGetterEffectsProved=False,actualLoaderAllocationObserved=False,actualAssetLookupEffectsProved=False,
  wholeConversionProved=False,runtimeInvocationObserved=False,playbackProved=False,
  evidenceBoundary=dict(exact='Complete actual constructor normal control/frames, independent service-result selections, incoming byte/Int32 enum stores and same-allocation dictionary/optional-reference publications.',
   conditional=__doc__,unresolved=['dictionary/optional constructor and service getter effects','actual allocation/state and enclosing asset methods','whole conversion/initializer/checkpoint/playback']))))
