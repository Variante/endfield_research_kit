"""Exact buffered Vector3/Quaternion field transfers in generated readers.

The selected bytes establish twelve or sixteen consumed bytes. Independent
current nominal fields/layout and named setter ABI establish which value owns
those bits. No managed size alone establishes a read or a wire grammar.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import generated_member_sources as members

LABEL='generatedVectorMemberSource'
def need(k,condition,detail=None):
 if not condition:raise ValueError(LABEL+'.'+k+':'+str(detail)[:700])
def peek(g,n=1):return bytes(g.bytes.get(g.at+i,0)for i in range(n))
def branch(g,cc,truth):
 prefix=peek(g,1).hex();long=prefix=='0f'
 opcode=peek(g,2)[1]if long else int(prefix,16)
 need('exact-conditional',opcode&15 in cc and(long and opcode>>4==8 or not long and opcode>>4==7))
 g.branch('0f'+format(opcode,'02x')if long else prefix,truth(opcode&15),4 if long else 1)
def nonnull(g):branch(g,(4,5),lambda c:c==5)
def source_update(g,width):
 g.take('8b6b30','83c5'+(-width&255).to_bytes(1,'little').hex());branch(g,(8,9),lambda c:c==9)
 w=bytes((width,)).hex();g.take('48834350'+w,'834340'+w,'834344'+w,'896b30')
def getter_guard(g,getter):
 g.take('4885f6');nonnull(g);g.take('33d2','488bce');g.call(getter);g.take('4885c0');nonnull(g)
def scalar_field(prefix,field):return members._displacement(prefix,field)

def setter_program(regions,entry,*,getter,field,width,path_factory=None):
 need('finite-blittable-width',type(width)is int and width in(12,16))
 need('callable-only-path-factory',path_factory is None or callable(path_factory))
 g=(BytesPath if path_factory is None else path_factory)(regions,entry);g.take('4053','4883ec20','488bda','33d2');g.call(getter)
 destination_alias=peek(g,3)==bytes.fromhex('488bc8')
 if destination_alias:
  need('exact-delayed-load-vector12-domain',width==12);g.take('488bc8')
 g.take('4885c0');nonnull(g)
 if destination_alias:g.take('f20f1003',scalar_field('f20f1140',field),'8b4308',scalar_field('8941',field+8))
 elif width==12:g.take('f20f1003','8b4b08',scalar_field('f20f1140',field),scalar_field('8948',field+8))
 else:g.take('0f1003',scalar_field('0f1140',field))
 g.take('4883c420','5b','c3')
 return dict(selectedBytes=g.seen,storedBytes=width,incomingValuePointer='rdx preserved rbx',
  getterReceiver='incoming rcx with zero edx',fullValueStoredUnchanged=True,normalFrameAndReturn=True)

def base_vector2_setter_program(regions,entry,*,holder,field):
 """Byvalue RDX8 spilled whole, then both Single lanes stored unchanged."""
 g=BytesPath(regions,entry);g.take('4883ec28',scalar_field('488b41',holder),'4889542430','4885c0')
 branch_site=g.at;prefix=peek(g);long=prefix==b'\x0f';opcode=peek(g,2)[1]if long else prefix[0]
 need('Vector2-setter-null-guard',opcode&15 in(4,5)and(long and opcode>>4==8 or not long and opcode>>4==7))
 target=g.relative('0f'+format(opcode,'02x')if long else prefix.hex(),4 if long else 1);fallthrough=g.at
 null=target if opcode&15==4 else fallthrough;normal=target if opcode&15==5 else fallthrough
 need('Vector2-owned-null-exit',g.bytes.get(null)==0xe8 and g.bytes.get(null+5)==0xcc)
 null_bytes=bytes(g.bytes.get(null+i,0)for i in range(5));g.at=normal
 g.take('f30f10442430','f30f104c2434',scalar_field('f30f1140',field),scalar_field('f30f1148',field+4),'4883c428','c3')
 return dict(selectedBytes=g.seen,holderOffset=holder,storedBytes=8,sourceRegister='rdx',sourceLocal=dict(displacement=48,bytes=8,entryRelativeOffset=8),
  sourceLanes=[dict(offset=0,bytes=4),dict(offset=4,bytes=4)],ownedNullExit=dict(instructionVa=null,bytes=null_bytes.hex(),terminal='CC'),
  completeSourceBitsStoredUnchanged=True,normalFrameAndReturn=True)

def base_vector_setter_program(regions,entry,*,holder,field,width):
 """Finite direct hidden-pointer stores, independently nominally laid out."""
 need('direct-vector12-or16-source',type(width)is int and width in(12,16))
 g=BytesPath(regions,entry);g.take('4883ec28',scalar_field('4c8b41'if width==12 else'488b41',holder),'4d85c0'if width==12 else'4885c0')
 prefix=peek(g);long=prefix==b'\x0f';opcode=peek(g,2)[1]if long else prefix[0]
 need('direct-vector-owned-null-guard',opcode&15 in(4,5)and(long and opcode>>4==8 or not long and opcode>>4==7))
 target=g.relative('0f'+format(opcode,'02x')if long else prefix.hex(),4 if long else 1);fall=g.at
 null=target if opcode&15==4 else fall;normal=target if opcode&15==5 else fall
 need('direct-vector-owned-null-exit',g.bytes.get(null)==232 and g.bytes.get(null+5)==204);g.at=normal
 if width==12:g.take('f20f1002','8b4208',scalar_field('f2410f1140',field),scalar_field('418940',field+8))
 else:g.take('0f1002',scalar_field('0f1140',field))
 g.take('4883c428','c3')
 return dict(selectedBytes=g.seen,holderOffset=holder,storedBytes=width,sourceRegister='rdx',destinationRegister='r8'if width==12 else'rax',sourceSlices=[[0,8],[8,4]]if width==12 else[[0,16]],
  ownedNullExit=dict(instructionVa=null,terminal='CC'),completeSourceBitsStoredUnchanged=True,normalFrameAndReturn=True)

def inline_source(g,*,width,getter,field):
 """Current split8+4/unaligned16 source, spill, counters and owned field."""
 need('finite-inline-width',width in(12,16));start=len(g.seen);w=bytes((width,)).hex()
 g.take('837b30'+w,'488b37');branch(g,(12,13),lambda c:c==13);g.take('488b4350')
 if width==12:g.take('f20f1000','448b7008');local=g.at;g.take('f20f11442458');local_slot=88;local_bytes=8
 else:g.take('0f1000');local=g.at;g.take('0f11442420');local_slot=32;local_bytes=16
 source_update(g,width);source_end=len(g.seen);getter_guard(g,getter)
 if width==12:g.take('f20f10442458',scalar_field('f20f1140',field),scalar_field('448970',field+8))
 else:g.take('0f10442420','488bcb',scalar_field('0f1140',field))
 return dict(selectedBytes=g.seen[start:],sourceBytes=g.seen[start:source_end],wireBytes=width,storedBytes=width,
  sourceLocal=dict(displacement=local_slot,bytes=local_bytes,storeInstructionVa=local),
  fullValueBitsStoredUnchanged=True,readerRegister='rbx',outputRegister='rdi',getterTarget=getter)

def mixed_program(regions,entry,*,getter,fields,reference,bool_source,barrier):
 """Full mixed Vector3/Quaternion/reference/Boolean count-to-RET profile."""
 need('four-named-fields',len(fields)==4);g=BytesPath(regions,entry);g.take('4080fd04');branch(g,(4,5),lambda c:c==4)
 values=[inline_source(g,width=w,getter=getter,field=f)for w,f in zip((12,16),fields)]
 context_site=g.at;context_cell=g.relative('488b15');g.take('488b37');reference_site=g.at;g.call(reference)
 g.take('488be8');getter_guard(g,getter);g.take(scalar_field('488d48',fields[2]),scalar_field('488968',fields[2]));g.call(barrier)
 g.take('488b3f','488bcb');bool_site=g.at;g.call(bool_source);g.take('0fb6d8','4885ff');nonnull(g)
 g.take('33d2','488bcf');g.call(getter);g.take('4885c0');nonnull(g);g.take('4c8b742450',scalar_field('8858',fields[3]),'488b5c2460','4883c430','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,inlineValues=values,referenceContext=dict(site=context_site,cell=context_cell),referenceCall=reference_site,
  booleanCall=bool_site,sourceLocals=[v['sourceLocal']for v in values],completeSelectedNormalProgram=True,
  childGrammarAdmitted=False,wholeOwnerAdmitted=False)

def layout(image,ctx,type_name):
 """Current finite named layout; a separate source program owns wire width."""
 from scripts.game_data.memorypack import scalar_param_native as scalar
 axes={'UnityEngine.Vector3':('x','y','z'),'UnityEngine.Quaternion':('x','y','z','w')}
 need('finite-nominal-layout',type_name in axes);td=ctx.index.types[type_name];md=image.metadata
 need('nongeneric-current-value',ctx.is_value_type(type_name)and td.generic_container_index<0)
 fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 actual=[(md.string(f.name_index),*ctx.field(type_name+'::'+md.string(f.name_index))[1:])for f in fields]
 expected=[(n,'float',16+4*i)for i,n in enumerate(axes[type_name])];need('actual-owned-float-fields',actual==expected,actual)
 for f in fields:scalar.ordinary(image,ctx.type_pointer(f.type_index),12,LABEL+'.layout')
 need('current-size-table-index',0<=td.index<image.registration['typeDefinitionsSizesCount'])
 pointer=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8);width=4*len(fields)
 need('actual-current-sizes',(image.pe.u32_at_va(pointer),image.pe.u32_at_va(pointer+4))==(16+width,width))
 return dict(typeName=type_name,typeDefinition=td.index,fields=actual,managedBytes=width,wireReadAdmitted=False)


def selected_rows(rows,selected):
 """Join every parsed byte back to its complete decoded instruction."""
 by={members.ec.va(r):r for r in rows};data={};order=[]
 for at,h in selected:
  for i,b in enumerate(bytes.fromhex(h)):
   need('selected-byte-not-repeated',at+i not in data);data[at+i]=b
  if at in by:order.append(at)
 result=[];covered=set()
 for at in order:
  r=by[at];raw=members.ec.raw(r);need('complete-current-selected-instruction',all(data.get(at+i)==b for i,b in enumerate(raw)))
  result.append(r);covered.update(range(at,at+len(raw)))
 need('every-parsed-byte-has-instruction-role',covered==set(data))
 return result


def derive_scope(image,pins,wrapper,targets,barrier,claim,enums,method,family,windows,rows,header_proof,header):
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_action_sources as actions
 ec=members.ec;base=image.pe.image_base;ctx=NativeReferenceContext(image);kinds=claim['anonymousReadOrder']
 if not(len(kinds)==4 and kinds[:2]==['value12:UnityEngine.Vector3','value16:UnityEngine.Quaternion']and kinds[2].startswith('reference:')and kinds[3]=='byte'):
  from scripts.game_data.memorypack.generated_mixed_reader_sources import derive_scope as mixed_scope
  return mixed_scope(image,pins,wrapper,targets,barrier,claim,enums,method,family,windows,rows,header_proof,header)
 need('exact-profile-caller-registers',(header_proof['readerRegister'],header_proof['outputRegister'])==('rbx','rdi'))
 inventory={w.name:w for w in image.memorypack_wrappers.values()};cache={}
 setters=[members._derive_setter(image,m,inventory,barrier,cache,pins=pins)for m in wrapper.members]
 getters={s['getter']['method'][3]for s in setters if s.get('getter')is not None}
 need('one-owned-current-field-getter',len(getters)==1 and all(s.get('getter')is not None for s in setters));getter=base+next(iter(getters))
 contexts,skipped=actions._contexts(image,rows);need('one-actual-reference-source-context',len(contexts)==1,contexts);context=contexts[0]
 need('actual-reader-reference-nominal',context['methodOwner']=='MemoryPack.MemoryPackReader'and context['methodName']in('ReadValue','ReadPackable')and context['register']=='rdx'and context['typeKind']in(18,21)and not bytes.fromhex(context['argumentRawHex'])[11]&128 and context['fullTypeName']==wrapper.members[2].declared_type)
 reference=base+targets[context['methodName']]['targetRva'];regions=[(base+w['startRva'],image.window_bytes(w))for w in windows]
 parsed=mixed_program(regions,ec.va(header),getter=getter,fields=[s['fieldOffset']for s in setters],reference=reference,bool_source=targets['bool'],barrier=base+barrier)
 need('actual-source-methodinfo-load',parsed['referenceContext']['site']==base+context['instructionRva'])
 path=selected_rows(rows,parsed['selectedBytes']);by={ec.va(r):r for r in rows};events=[];values={}
 for n,(member,kind,setter)in enumerate(zip(wrapper.members,kinds,setters,strict=True)):
  if n<2:
   v=parsed['inlineValues'][n];entry=v['selectedBytes'][0][0];type_layout=layout(image,ctx,member.declared_type)
   need('independent-nominal-setter-and-source-bits',setter['storedBytes']==v['wireBytes']==type_layout['managedBytes'])
   event=dict(memberIndex=n,fieldName=member.name,declaredType=member.declared_type,kind=kind,instruction=ec.site(by[entry],base),mode='buffered-inline-value',wireBytes=v['wireBytes'])
   values[str(n)]=dict(typeName=member.declared_type,layout=type_layout,sourceProgram=v,actualSourceProved=True,wireBytes=v['wireBytes'],resultAbi='inline-bits-to-owned-field')
  else:
   entry=parsed['referenceCall'if n==2 else'booleanCall'];event=dict(memberIndex=n,fieldName=member.name,declaredType=member.declared_type,kind=kind,instruction=ec.site(by[entry],base),sourceTargetRva=(reference if n==2 else targets['bool'])-base)
   if n==2:event['context']=context
   else:event['wireBytes']=1
  events.append(event)
 locals_=[]
 for local in parsed['sourceLocals']:
  r=by[local['storeInstructionVa']];locals_.append(dict(displacement=local['displacement'],bytes=local['bytes'],storeInstruction=ec.site(r,base)))
 selected=[ec.site(r,base)for r in path]
 rich=dict(selectedProgram=selected,completeSelectedNormalProgram=True,sourceLocalValues=locals_,childGrammarAdmitted=False,wholeOwnerAdmitted=False)
 requirement=dict(memberIndex=2,fieldName=wrapper.members[2].name,typeName=wrapper.members[2].declared_type,readMethod=context['methodName'],methodDefinition=context['methodSpec'][0],sourceTargetRva=reference-base,context=context,positiveGrammarAdmitted=False)
 return dict(schema='endfield.generated-action-source-scope.v2',nativeInputs=dict(pins),wrapperName=wrapper.name,wrappedType=wrapper.wrapped_type,memberCount=4,claim=claim,method=method,family=family,codeWindows=windows,headerProof=header_proof,
  enumBackings=enums,contexts=contexts,skippedRuntimeCells=skipped,events=events,childRequirements=[requirement],richSetters=setters,richProgram=rich,selectedProgram=selected,
  primitiveSources={'3':targets['_primitiveCache'][('bool',targets['bool'])]},valueTypeSources=values,completeSourceProgram=parsed,
  sourceScopeAdmitted=True,wholeWrapperAdmitted=False,positiveGrammarAdmitted=False,
  evidenceBoundary='Complete current mixed Vector3/Quaternion/reference/Boolean read-to-field program. Each raw value is proved by exact bytes/counters/spills/store plus independent current nominal layout and hidden-pointer setter. Caller entry/frame/lifecycle and reference child remain independent; live callback/helper effects are conditional.')
