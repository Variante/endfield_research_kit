"""Finite initialized inline wrapper construction with independent roles.

The fresh lifecycle owns each nominal allocation, constructor, holder and cast
role. This slice proves their actual inline caller program through the output
store, while the caller must separately restore its entire original frame.
Metadata initialization and incompatible/enabled-collector paths stay closed.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

LABEL='generatedInlineConstructor'

def need(k,c,detail=None):
 if not c:raise ValueError(LABEL+'.'+k+':'+str(detail)[:700])

def _edge(g,*,zero):
 head=bytes(g.bytes.get(g.at+i,0)for i in range(2));near=head[0]==15;opcode=head[1]if near else head[0]
 need('literal-equality-edge',opcode in(132,133)if near else opcode in(116,117))
 taken=zero if opcode&15==4 else not zero
 return g.branch(('0f'if near else'')+format(opcode,'02x'),taken,4 if near else 1)

def _nonnull(g):
 at=g.at;head=bytes(g.bytes.get(at+i,0)for i in range(2));near=head[0]==15;opcode=head[1]if near else head[0]
 need('literal-nonnull-edge',opcode in(132,133)if near else opcode in(116,117))
 target=g.relative(('0f'if near else'')+format(opcode,'02x'),4 if near else 1);fall=g.at
 null=target if opcode&15==4 else fall;normal=fall if opcode&15==4 else target
 need('owned-nonreturning-null-call',g.bytes.get(null)==232 and g.bytes.get(null+5)==204)
 g.at=normal
 return dict(instructionVa=at,nullTargetVa=null,normalTargetVa=normal)

def program(regions,entry,*,initialized_flag,base_slot,cache_slot,allocator,original_constructor,predicate,disabled,
            wrapper='rdi',output='r14'):
 """Exact RDI-wrapper initialized construction with either owned output role."""
 need('explicit-current-inline-register-profile',(wrapper,output)in(('rdi','r14'),('rdi','rsi')),
     dict(wrapperRegister=wrapper,outputRegister=output))
 class_load,class_argument,output_store=(('488b35','488bd6','49893e')if output=='r14'else
     ('4c8b35','498bd6','48893e'))
 need('independent-current-role-inputs',all(type(v)is int and v>0 for v in(initialized_flag,allocator,original_constructor,predicate,disabled))
     and type(base_slot)is int and type(cache_slot)is int and 16<=base_slot<cache_slot<128)
 g=BytesPath(regions,entry);need('same-current-own-constructor-flag',flag(g,prefix='803d')==initialized_flag);_edge(g,zero=False)
 at=g.at;ancestor_cell=g.relative('488b0d');ancestor=dict(instructionVa=at,cellVa=ancestor_cell)
 g.take('83b9e000000000');_edge(g,zero=False)
 at=g.at;allocation_cell=g.relative('488b0d');allocation=dict(instructionVa=at,cellVa=allocation_cell);g.call(allocator)
 g.take('488bd8','4885c0');null=_nonnull(g);g.take('33d2','488bc8');constructor_call=g.at;g.call(original_constructor)
 b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex();stores=[];collectors=[]
 def collect():
  at=g.at;need('independently-current-DWORD-collector',flag(g,prefix='833d')==disabled);collectors.append(at)
 def store(raw,role,offset):
  at=g.at;g.take(raw);stores.append(dict(instructionVa=at,role=role,offset=offset,bytes=8,sameAllocatedReference=True))
 for slot in(cache_slot,base_slot):
  collect();store('48895f'+bytes((slot,)).hex(),'wrapper-holder',slot);_edge(g,zero=True)
 g.take('488b5f'+b);at=g.at;class_cell=g.relative(class_load);classes=[dict(instructionVa=at,cellVa=class_cell)]
 g.take('4885db');_edge(g,zero=False)
 predicate_sites=[]
 def compatible():
  g.take('488b0b',class_argument);predicate_sites.append(g.at);g.call(predicate);g.take('84c0');_edge(g,zero=False)
 compatible();store('48895f'+c,'typed-cache-after-compatible-predicate',cache_slot)
 at=g.at;second_cell=g.relative(class_load);classes.append(dict(instructionVa=at,cellVa=second_cell))
 need('both-current-exact-Original-class-cells',class_cell==second_cell==allocation_cell)
 compatible();g.jump('e9');collect();_edge(g,zero=True)
 collect();store(output_store,'parent-output',0);_edge(g,zero=True)
 return dict(selectedBytes=g.seen,selectedEnd=g.at,initializedFlag=initialized_flag,allocation=allocation,ancestorClass=ancestor,
     classUsages=classes,allocatorTarget=allocator,originalConstructorTarget=original_constructor,constructorCallVa=constructor_call,
     predicateTarget=predicate,predicateSites=predicate_sites,baseHolderOffset=base_slot,typedCacheOffset=cache_slot,
     wrapperRegister=wrapper,outputRegister=output,originalRegister='rbx',holderWrites=stores,collectorComparisons=collectors,
     ownedNullExit=null,completeSelectedConstructionFragment=True,sameFreshOriginalInBothHolders=True,sameFreshWrapperInOutput=True,
     callerFrameProved=False,childGrammarAdmitted=False,metadataInitializationAdmitted=False,enabledCollectorAdmitted=False,
     condition='Own metadata and ancestor class initialized, normal successful exact nominal allocation/Original constructor, both successful same-current-class assignability predicates and independently proved current collector disabled. Fresh wrapper/output/input and frame are disjoint. Whole caller frame and all field source/grammar remain independent; no live predicate/provider outcome or constructor execution is observed.')

def require_ready_ancestor(factory,ancestor,wrapper_name):
 """Match only independently typed readiness uses, never compatible ancestry."""
 ready_ancestors=[row for row in [factory.get('ancestorClass'),*factory.get('ancestorClasses',[])]if row is not None]
 need('same-independent-ready-ancestor-class',ancestor.get('tag')==1 and any(
     (ancestor.get('tag'),ancestor.get('typeName'))==(row.get('tag'),row.get('typeName'))for row in ready_ancestors),
     dict(wrapperName=wrapper_name,actualAncestor=ancestor,independentReadyAncestors=ready_ancestors,
          baseConstructorMethod=factory.get('baseConstructor',{}).get('method')))


def derive_fragment(image,pins,*,wrapper,lifecycle,rows,entry,wrapper_register,output_register,barrier,owned_partition=None):
 """Freshly join this inline fragment to the independently rederived lifecycle."""
 from scripts.game_data.memorypack import char_actor_inline_sources as actor
 if wrapper.wrapped_type==actor.TYPE:
  return actor.derive_fragment(image,pins,wrapper=wrapper,lifecycle=lifecycle,rows=rows,entry=entry,
      wrapper_register=wrapper_register,output_register=output_register,barrier=barrier)
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_member_sources as members,generated_lifecycle_sources as lives
 from scripts.game_data.memorypack import module_structure_models as holders,pointer_param as pointer,scalar_param_native as scalar
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 need('same-fresh-nominal-lifecycle',lifecycle.get('wrapperName')==wrapper.name and lifecycle.get('wrappedType')==wrapper.wrapped_type
     and lifecycle.get('typeDefinition')==wrapper.type_definition and not wrapper.wrapped_is_value_type)
 ctor=pointer.methods(image,wrapper)['.ctor'];selected=[f for f in lifecycle['factories']if f['method']==lives._method_row(image,ctor)]
 need('one-current-owned-wrapper-constructor',len(selected)==1);factory=selected[0];fp=factory['program']
 constant_inline=fp.get('originalConstructorCalled')is False and wrapper.wrapped_type in(
     'Beyond.Gameplay.Core.PullAction+Data','Beyond.Gameplay.Core.DisableNormalSkillWithUI+Data')
 need('independent-called-or-exact-inline-Original-defaults',fp.get('constructor')is True and(fp.get('originalConstructorCalled')is True or constant_inline)
     and isinstance(factory.get('originalConstructor'),dict)and fp.get('strictCast')is not None)
 original=factory['originalConstructor']['method'];om=md.methods[original[0]]
 need('own-current-noarg-original-constructor',original==lives._method_row(image,om)and original[1:3]==[wrapper.wrapped_type,'.ctor']
     and(constant_inline or original[3]+base==fp['originalConstructorTarget'])and om.generic_container_index<0)
 if constant_inline:
  defaults=factory['originalConstructor'];leaf=defaults.get('reachableLeaf',{})
  need('independently-complete-call-free-default-source',defaults.get('completeReachableEntryProgramProved')is True
      and leaf.get('normalReturn')is True and leaf.get('callFree')is True and leaf.get('stackUnchanged')is True
      and leaf.get('allNonvolatileRegistersUnchanged')is True and len(defaults.get('constantFieldStores',[]))==
      (3 if wrapper.wrapped_type=='Beyond.Gameplay.Core.PullAction+Data'else 2))
 scalar.owned_method_abi(image,ctx,om.index,om.declaring_type,('void',1,False),[],LABEL+'.OriginalCtor')
 cast=members._body(image,fp['strictCast']);predicates=[]
 for i,row in enumerate(cast['rows']):
  if members.ec.raw(row)[:1]==b'\xe8'and i and members.ec.raw(cast['rows'][i-1])==bytes.fromhex('488b09'):
   predicates.append(members.control_transfer(row)['target'])
 need('one-current-cast-predicate',len(predicates)==1)
 cast_program=holders.rolling_owned_strict_cast(cast['regions'],cast['pointer'],predicates[0])
 need('same-current-independent-cast-family',cast['windows']==factory['strictCast']['codeWindows']and cast_program==factory['strictCast']['program'])
 collector=_barrier(image,barrier);disabled=base+collector['result']['disabledFlagRva']
 if constant_inline:
  from scripts.game_data.memorypack.generated_inline_constant_constructor_sources import program as constant_program
  parsed=constant_program([(members.ec.va(r),members.ec.raw(r))for r in rows],entry,initialized_flag=fp['initializedFlag'],
      base_slot=lifecycle['baseHolder'][2],cache_slot=lifecycle['typedCache'][2],allocator=fp['allocationTarget'],
      predicate=predicates[0],disabled=disabled,constant_stores=factory['originalConstructor']['constantFieldStores'],
      wrapper=wrapper_register,output=output_register,original_type=wrapper.wrapped_type)
 elif(wrapper_register,output_register)in(('r15','rsi'),('r15','r14')):
  from scripts.game_data.memorypack.generated_header_sources import _owned_zero_source
  from scripts.game_data.memorypack.generated_r15_inline_constructor_sources import program as r15_program
  need('independent-complete-ordinary-constructor-graph',type(owned_partition)is dict and type(owned_partition.get('entryRva'))is int)
  zero=_owned_zero_source(rows,base+owned_partition['entryRva'],[entry],'rbx',base,owned_partition)
  parsed=r15_program([(members.ec.va(r),members.ec.raw(r))for r in rows],entry,initialized_flag=fp['initializedFlag'],
      base_slot=lifecycle['baseHolder'][2],cache_slot=lifecycle['typedCache'][2],allocator=fp['allocationTarget'],
      original_constructor=fp['originalConstructorTarget'],strict_cast=fp['strictCast'],disabled=disabled,
      wrapper=wrapper_register,output=output_register)
  parsed['entryZeroSource']=zero
 else:
  parsed=program([(members.ec.va(r),members.ec.raw(r))for r in rows],entry,initialized_flag=fp['initializedFlag'],
      base_slot=lifecycle['baseHolder'][2],cache_slot=lifecycle['typedCache'][2],allocator=fp['allocationTarget'],
      original_constructor=fp['originalConstructorTarget'],predicate=predicates[0],disabled=disabled,
      wrapper=wrapper_register,output=output_register)
 usage=derive_typed_usage_context(image,parsed['allocation']['instructionVa']-base,label=LABEL+'.OriginalAllocation')
 need('same-fresh-exact-Original-class',(usage['tag'],usage['typeName'])==(1,wrapper.wrapped_type))
 classes=[derive_typed_usage_context(image,c['instructionVa']-base,label=LABEL+'.InlineCastClass')for c in parsed['classUsages']]
 need('each-inline-cast-current-same-nominal-class',all((c['tag'],c['typeName'])==(1,wrapper.wrapped_type)for c in classes))
 ancestor=derive_typed_usage_context(image,parsed['ancestorClass']['instructionVa']-base,label=LABEL+'.AncestorClass')
 require_ready_ancestor(factory,ancestor,wrapper.name)
 fields=lives._holder_fields(image,ctx,wrapper.name,[parsed['typedCacheOffset'],parsed['baseHolderOffset']],lives._class_ancestry(ctx,wrapper.wrapped_type))
 from scripts.game_data.memorypack.generated_vector_member_sources import selected_rows
 selected=selected_rows(rows,parsed['selectedBytes'])
 _publication_gate(image,pins)
 return dict(schema='endfield.generated-inline-constructor-fragment.v1',nativeInputs=dict(pins),wrapperName=wrapper.name,wrappedType=wrapper.wrapped_type,
     wrapperConstructorMethod=factory['method'],
     program=parsed,originalAllocation=usage,castClasses=classes,ancestorClass=ancestor,ownedHolderFields=fields,
     originalConstructor=factory['originalConstructor'],strictCast=dict(family=cast['family'],codeWindows=cast['windows'],program=cast_program),collector=collector,
     selectedProgram=[members.ec.site(r,base)for r in selected],sameFreshWrapperInOutput=True,
     completeSelectedConstructionFragment=True,callerFrameProved=False,childGrammarAdmitted=False,wholeOwnerAdmitted=False)
