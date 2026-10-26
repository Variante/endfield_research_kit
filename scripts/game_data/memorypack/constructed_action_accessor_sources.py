"""Closed generic NodeBase accessors, offsets from compiled effects.

Managed ancestry and formal field identities are independent of physical
offsets. No open generic field offset/size is read; each destination comes
from its complete named setter and is joined to that exact declaration.
The structural fallback starts from the actual declaring wrapper cache
carrier and requires reciprocal managed ancestry to the exact NodeBase role.
"""
import json,re
from scripts.game_data.memorypack import constructed_action_ancestry_sources as ancestry

BASE_WRAPPERS={
 'Beyond.MemoryPack.Beyond_Gameplay_Actions_SetList_int_ForMemoryPack':'Beyond.Gameplay.Actions.SetListInt',
 'Beyond.MemoryPack.Beyond_Gameplay_Actions_GetLevelScriptPropertyGeneric_bool_ForMemoryPack':'Beyond.Gameplay.Actions.GetLevelScriptPropertyGenericBool',
}
FIELDS={'Beyond.Gameplay.Actions.SetListInt':{'_key','_value'},
 'Beyond.Gameplay.Actions.GetLevelScriptPropertyGenericBool':{'_path','_target'}}
LABEL='constructedActionAccessor'


def need(check,value):
 if not value:raise ValueError(LABEL+'.'+check)


def selected_owner(wrappers,declaring_wrapper,*,image=None):
 """Select a proved NodeBase carrier; selection itself grants no accessor."""
 if declaring_wrapper in BASE_WRAPPERS:return BASE_WRAPPERS[declaring_wrapper]
 wrapper=wrappers.get(declaring_wrapper)
 if wrapper is None:return None
 matched=[name for name,(definition,args)in ancestry.TYPES.items()
  if wrapper.wrapped_type==definition+'<'+','.join(args)+'>']
 need('one-finite-closed-base-owner',len(matched)<=1)
 if matched:return matched[0]
 if image is None or not hasattr(image,'metadata')or not hasattr(image,'pe'):return None
 try:return _structural_root(image,wrappers,declaring_wrapper)['typeName']
 except(ValueError,KeyError,IndexError,TypeError):return None


def _structural_root(image,wrappers,declaring_wrapper):
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 wrapper=wrappers[declaring_wrapper];ctx=NativeReferenceContext(image);md=image.metadata
 need('nongeneric-reference-declaring-wrapper',not wrapper.wrapped_is_value_type
  and md.types[wrapper.type_definition].generic_container_index<0)
 fields=[f for f in md.fields_for(md.types[wrapper.type_definition])
  if md.string(f.name_index)=='__realInstance'and not ctx.field_attributes(f.type_index)&16]
 need('one-actual-closed-wrapper-cache',len(fields)==1)
 chain=ancestry.derive_closed(ctx,ctx.type_pointer(fields[0].type_index))
 need('same-actual-closed-wrapper-Original',chain['typeName']==wrapper.wrapped_type)
 return chain


def _named_wrappers(image):
 from scripts.game_data.memorypack.wrapper_members import derive_from_image
 values=list(derive_from_image(image).values());wrappers={w.name:w for w in values}
 need('unique-current-wrapper-names',len(wrappers)==len(values))
 return wrappers


def same_closed_reference(left,right):
 """Separate declaration attributes from one exact closed class carrier."""
 if not all(left.get(k)==right.get(k)for k in('type','bytes','definitionTypeIndex','definitionTypeRecordHex','argumentTypes')):return False
 a=bytes.fromhex(left.get('declaredTypeRecordHex',''));b=bytes.fromhex(right.get('declaredTypeRecordHex',''))
 return(len(a)==len(b)==16 and a[:8]==b[:8]and a[10:]==b[10:]
  and a[10:12]==b[10:12]==bytes((21,0))and not int.from_bytes(a[8:10],'little')&16
  and not int.from_bytes(b[8:10],'little')&16)


def derive(image,pins,*,type_name=None,declaring_wrapper=None):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_pointer_extent
 from scripts.game_data.il2cpp.reference_field_programs import prove_cached_field_setter
 from scripts.game_data.memorypack import generated_member_sources as members,pointer_param as pointer,scalar_param_native as scalar
 _publication_gate(image,pins);need('one-selected-accessor-root',(type_name is None)!=(declaring_wrapper is None))
 base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;wrappers=_named_wrappers(image)
 if declaring_wrapper is None:
  need('finite-owner',type_name in ancestry.TYPES);chain=ancestry.derive(ctx,type_name)
  wrapper,=[w for w in wrappers.values()if w.wrapped_type==type_name]
  base_wrapper=wrappers[ctx.parent(wrapper.name)];need('actual-finite-base-wrapper',selected_owner(wrappers,base_wrapper.name)==type_name)
  parent=chain['edges'][0]['resolvedParent'];closed=closed_generic_reference_pointer_extent(ctx,ctx.type_pointer(ctx.index.types[type_name].parent_index))
 else:
  chain=_structural_root(image,wrappers,declaring_wrapper);base_wrapper=wrappers[declaring_wrapper];wrapper=base_wrapper
  parent=chain['initialResolvedType'];closed=chain['initialClosedCarrier'];type_name=closed['type']
 need('same-closed-original',base_wrapper.wrapped_type==closed['type']==parent['name']and not base_wrapper.wrapped_is_value_type)
 cache=ctx.field(base_wrapper.name+'::__realInstance');need('own-closed-cache',cache[:2]==(base_wrapper.name,closed['type']))
 cache_field,=[f for f in md.fields_for(md.types[base_wrapper.type_definition])if md.string(f.name_index)=='__realInstance']
 cache_carrier=closed_generic_reference_pointer_extent(ctx,ctx.type_pointer(cache_field.type_index))
 need('same-closed-cache-carrier',all(cache_carrier[k]==closed[k]for k in('type','definitionTypeIndex','definitionTypeRecordHex','argumentTypes')))
 base_holders=[];name=ctx.parent(base_wrapper.name);seen=set()
 while name not in('','object','System.Object'):
  need('bounded-wrapper-chain',name not in seen and len(seen)<16);seen.add(name)
  for field in md.fields_for(ctx.index.types[name]):
   if md.string(field.name_index)in('___instance','__instance')and not ctx.field_attributes(field.type_index)&16:
    scalar.ordinary(image,ctx.type_pointer(field.type_index),18,LABEL+'.baseHolder',reference=True)
    base_holders.append(ctx.field(name+'::'+md.string(field.name_index)))
  name=ctx.parent(name)
 need('one-managed-compatible-base-holder',len(base_holders)==1 and base_holders[0][1]in chain['ancestry']and base_holders[0][2]==16)
 getter=pointer.methods(image,base_wrapper)['get___instance']
 scalar.owned_method_abi(image,ctx,getter.index,base_wrapper.type_definition,(closed['type'],21,True),[],LABEL+'.getter')
 returned=closed_generic_reference_pointer_extent(ctx,ctx.type_pointer(getter.return_type))
 need('same-actual-closed-getter-result',same_closed_reference(returned,closed))
 body=members._body(image,image.method_pointer_va(getter),pins=pins);programs=[]
 for mode in('rbx','rdi'):
  try:programs.append(members.coherent_getter_program(body['regions'],body['pointer'],base_slot=16,cache_slot=cache[2],mode=mode))
  except(ValueError,KeyError,IndexError):pass
 need('one-complete-coherent-getter',len(programs)==1)
 barrier_calls=[members.control_transfer(r)['target']for i,r in enumerate(body['rows'])if i and
  body['rows'][i-1]['text']in(f'lea rcx, [rbx+0x{cache[2]:x}]',f'lea rcx, [rdi+0x{cache[2]:x}]')and members.control_transfer(r)['kind']=='call']
 need('one-own-disabled-barrier',len(barrier_calls)==1);barrier=barrier_calls[0]
 refresh=members._getter_refresh(image,body,base_slot=16,cache_slot=cache[2],original=closed['type'],barrier=barrier)
 refresh_carriers=[]
 for item in refresh['programs']:
  for usage in item['classUsages']:
   carrier=closed_generic_reference_pointer_extent(ctx,ctx.type_pointer(usage['typeIndex']))
   need('same-actual-closed-refresh-class',usage['typeRawHex']==carrier['declaredTypeRecordHex']
    and same_closed_reference(carrier,closed))
   refresh_carriers.append(dict(usage=usage,closedReference=carrier))
 fields={md.string(f.name_index):f for f in md.fields_for(md.types[closed['definitionTypeIndex']])if not ctx.field_attributes(f.type_index)&16}
 selected=[m for m in wrapper.members if m.declaring_wrapper==base_wrapper.name]
 need('complete-owned-reference-fields',0<len(selected)<=32 and len({m.name for m in selected})==len(selected)
  and set(fields)=={m.name for m in selected})
 if type_name in FIELDS:need('existing-exact-owned-field-domain',set(fields)==FIELDS[type_name])
 records=[];occupied=set()
 for member in selected:
  field=fields[member.name];formal=ancestry.type_symbol(image,ctx.type_pointer(field.type_index))
  resolved=ancestry.resolve_symbol(formal,owner_definition=closed['definitionTypeIndex'],arguments=parent['arguments'],definition=lambda i:ancestry.definition(ctx,i))
  need('same-resolved-field-declaration',resolved['name']==member.declared_type and resolved['kind']in(21,29))
  method=md.methods[member.method_index];parameter,=md.parameters_for(method)
  scalar.owned_method_abi(image,ctx,method.index,base_wrapper.type_definition,('void',1,False),[(member.declared_type,resolved['kind'],True)],LABEL+'.setter')
  need('nongeneric-named-setter',method.generic_container_index<0)
  parameter_pointer=ctx.type_pointer(parameter.type_index)
  if resolved['kind']==21:
   parameter_carrier=closed_generic_reference_pointer_extent(ctx,parameter_pointer)
   need('same-closed-setter-argument',parameter_carrier['type']==resolved['name'])
  else:
   array=ancestry.type_symbol(image,parameter_pointer)
   actual=ancestry.resolve_symbol(array,owner_definition=closed['definitionTypeIndex'],arguments=[],definition=lambda i:ancestry.definition(ctx,i))
   raw_array=bytes.fromhex(array['rawHex'])
   element=closed_generic_reference_pointer_extent(ctx,int.from_bytes(raw_array[:8],'little'))
   need('same-exact-reference-array-argument',actual['name']==resolved['name']and actual['kind']==29
    and element['type']+'[]'==resolved['name'])
   parameter_carrier=dict(type=actual['name'],bytes=8,kind=29,elementReference=element,elementGrammarAdmitted=False)
  native=members._body(image,image.method_pointer_va(method),pins=pins);rows=native['rows']
  offsets=[int(m[1],16)for r in rows if(m:=re.fullmatch(r'mov \[rax\+0x([0-9a-f]+)\], rbx',r['text']))]
  need('one-observed-complete-ref8-store',len(offsets)==1);offset=offsets[0]
  calls=[members.control_transfer(r)['target']for r in rows if members.control_transfer(r)['kind']=='call']
  nulls=[n for n in calls if n!=body['pointer']]
  need('exact-own-getter-and-null-exit',calls.count(body['pointer'])==1 and len(nulls)==1)
  program=prove_cached_field_setter(rows,field_offset=offset,mode='reference-return',symbols=dict(getter=body['pointer'],nullThrow=nulls[0],barrier=barrier))
  span=set(range(offset,offset+8));need('two-disjoint-field-effects',offset>=16 and not occupied&span);occupied|=span
  records.append(dict(member=member.row(),declaredField=dict(ownerDefinition=ancestry.definition(ctx,closed['definitionTypeIndex'])['name'],name=member.name,
   typeName=resolved['name'],formalType=formal,substitutedType=resolved),method=[method.index,base_wrapper.name,md.string(method.name_index),native['pointer']-base],
   fieldOffset=offset,storedBytes=8,parameterTypeRecordHex=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16).hex().upper(),
   family=native['family'],codeWindows=native['windows'],program=program))
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.constructed-action-accessor-effects.v1',nativeInputs=pins,typeName=type_name,
  status='validated-conditional-closed-accessors',ancestry=chain,closedParent=closed,holderCarrier=cache_carrier,baseWrapperName=base_wrapper.name,
  baseHolder=base_holders[0],typedCache=cache,getter=dict(method=[getter.index,base_wrapper.name,'get___instance',body['pointer']-base],
   family=body['family'],codeWindows=body['windows'],program=programs[0],compatibleRefresh=refresh,
   returnedClosedReference=returned,refreshClassReferences=refresh_carriers),accessors=records,
  barrierTargetRva=barrier-base,openGenericFieldOffsetsUsed=False,nativeClosedFieldLayoutAdmitted=False,wholeOwnerAdmitted=False)))


def derive_setter(image,pins,member,wrappers,barrier,getter_cache):
 type_name=selected_owner(wrappers,member.declaring_wrapper,image=image)
 need('finite-declaring-wrapper',type_name is not None)
 key=('constructed-action-accessors',member.declaring_wrapper)
 if key not in getter_cache:
  getter_cache[key]=derive(image,pins,**(dict(type_name=type_name)if type_name in ancestry.TYPES else dict(declaring_wrapper=member.declaring_wrapper)))
 effects=getter_cache[key]
 need('same-fresh-cached-accessor-domain',effects.get('schema')=='endfield.constructed-action-accessor-effects.v1'
  and effects.get('status')=='validated-conditional-closed-accessors'and effects.get('nativeInputs')==pins
  and effects.get('typeName')==type_name and effects.get('baseWrapperName')==member.declaring_wrapper
  and effects.get('openGenericFieldOffsetsUsed')is False and effects.get('nativeClosedFieldLayoutAdmitted')is False)
 record,=[r for r in effects['accessors']if r['member']==member.row()]
 need('same-closed-declaration-and-ref8-effect',record['declaredField']['typeName']==member.declared_type
  and record['declaredField']['name']==member.name and record['storedBytes']==8)
 need('same-selected-disabled-barrier',effects['barrierTargetRva']==barrier)
 getter=dict(effects['getter'],baseHolder=effects['baseHolder'],typedCache=effects['typedCache'],coherentNonNullSamePointerReturn=True,
  refreshAdmitted=True,closedReferenceCarrier=effects['holderCarrier'],closedParent=effects['closedParent'])
 return dict(method=record['method'],member=member.row(),targetField=effects['closedParent']['type']+'::'+member.name,
  fieldOffset=record['fieldOffset'],storedBytes=8,parameterTypeRecordHex=record['parameterTypeRecordHex'],sourceFamily=record['family'],
  codeWindows=record['codeWindows'],profile='cached-getter-setter',program=record['program'],getter=getter,
  incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False,closedFieldDeclaration=record['declaredField'],
  closedReferenceCarrier=effects['closedParent'],fieldOffsetSource='complete actual compiled named reference setter',
  nativeClosedMetadataFieldOffsetsAdmitted=False,openGenericFieldOffsetUsed=False)
