"""Managed NodeBase ancestry through actual closed reference carriers.

Only metadata identity and reciprocal formal substitution are established.
Existing finite selections retain their output; structural roots use the
named Original's actual closed parent or a wrapper's declared cache carrier.
Open generic offsets, managed sizes, native closed-class identities, compiled
field effects, constructors and wire grammars remain separate obligations.
The enclosing owner authenticates its selected image before and after use.
"""
import struct

TYPES={
 'Beyond.Gameplay.Actions.SetListInt':('Beyond.Gameplay.Actions.SetList`1',['int']),
 'Beyond.Gameplay.Actions.GetLevelScriptPropertyGenericBool':('Beyond.Gameplay.Actions.GetLevelScriptPropertyGeneric`1',['bool']),
 'Beyond.Gameplay.Actions.ListAddValueBuff':('Beyond.Gameplay.Actions.ListAddValue`1',['Beyond.Gameplay.Core.BuffPtr']),
 'Beyond.Gameplay.Actions.ListRemoveInt':('Beyond.Gameplay.Actions.ListRemove`1',['int']),
 'Beyond.Gameplay.Actions.ListSetValueInt':('Beyond.Gameplay.Actions.ListSetValue`1',['int']),
 'Beyond.Gameplay.Actions.ListContainsEntityPtr':('Beyond.Gameplay.Actions.ListContains`1',['Beyond.Gameplay.Core.EntityPtr']),
 'Beyond.Gameplay.Actions.ListContainsString':('Beyond.Gameplay.Actions.ListContains`1',['string']),
 'Beyond.Gameplay.Actions.ListFindItemIndexEntityPtr':('Beyond.Gameplay.Actions.ListFindItemIndex`1',['Beyond.Gameplay.Core.EntityPtr']),
 'Beyond.Gameplay.Actions.ListGetLengthString':('Beyond.Gameplay.Actions.ListGetLength`1',['string']),
 'Beyond.Gameplay.Actions.ListMakeVector3':('Beyond.Gameplay.Actions.MakeList`1',['UnityEngine.Vector3']),
 'Beyond.Gameplay.Actions.ListGetRandomItemFloat':('Beyond.Gameplay.Actions.ListGetRandomItem`1',['float']),
 'Beyond.Gameplay.Actions.ListGetRandomItemVector3':('Beyond.Gameplay.Actions.ListGetRandomItem`1',['UnityEngine.Vector3']),
 'Beyond.Gameplay.Actions.ListGetValueGameplayTag':('Beyond.Gameplay.Actions.ListGetValue`1',['Beyond.Gameplay.Core.GameplayTag']),
}
SCHEMA='endfield.constructed-action-ancestry-sources.v1'
PRIMITIVES={2:'bool',3:'char',4:'sbyte',5:'byte',6:'short',7:'ushort',8:'int',9:'uint',10:'long',11:'ulong',12:'float',13:'double',14:'string',28:'object'}


def need(check,value):
 if not value:raise ValueError('constructedActionAncestry.'+check)


def _raw(symbol):
 raw=bytes.fromhex(symbol['rawHex']);need('ordinary-complete-type-record',len(raw)==16 and raw[11]in(0,128)
  and not int.from_bytes(raw[8:10],'little')&16)
 return raw


def resolve_symbol(symbol,*,owner_definition,arguments,definition,depth=0):
 """Substitute only a VAR reciprocally owned by this exact current definition."""
 need('bounded-parent-argument-graph',depth<16)
 raw=_raw(symbol);kind=raw[10];index=int.from_bytes(raw[:8],'little')
 if kind==19:
  owner=symbol['parameterOwner'];ordinal=owner['ordinal']
  need('same-reciprocal-formal-owner',owner.get('typeIndex')==owner_definition and owner.get('parameterIndex')==index
   and type(ordinal)is int and 0<=ordinal<len(arguments))
  return dict(arguments[ordinal],substitutedFormal=dict(parameterIndex=index,typeDefinition=owner_definition,ordinal=ordinal))
 need('method-formal-never-a-class-parent',kind!=30)
 if kind in PRIMITIVES:
  need('literal-primitive-argument',symbol['name']==PRIMITIVES[kind])
  return dict(name=symbol['name'],kind=kind,definitionTypeIndex=None,arguments=[])
 if kind==29:
  need('ordinary-reference-array',raw[11]==0)
  element=resolve_symbol(symbol['elementType'],owner_definition=owner_definition,arguments=arguments,
   definition=definition,depth=depth+1)
  return dict(name=element['name']+'[]',kind=29,definitionTypeIndex=None,arguments=[element])
 if kind in(17,18):
  td=definition(index);need('same-named-nongeneric-type',td['name']==symbol['name']and td['arity']==0)
  return dict(name=td['name'],kind=kind,definitionTypeIndex=index,arguments=[])
 need('actual-generic-instance-parent',kind==21)
 parent=symbol['definition'];record=_raw(parent)
 need('generic-definition-is-class',record[10]==18 and record[11]==0)
 td=definition(int.from_bytes(record[:8],'little'))
 need('exact-generic-definition-and-arity',td['name']==parent['name']and 1<=td['arity']<=64 and td['arity']==len(symbol['classArguments']))
 resolved=[resolve_symbol(a,owner_definition=owner_definition,arguments=arguments,definition=definition,depth=depth+1)
  for a in symbol['classArguments']]
 return dict(name=td['name']+'<'+','.join(a['name']for a in resolved)+'>',kind=21,
  definitionTypeIndex=td['index'],definitionName=td['name'],arguments=resolved)


def type_symbol(image,pointer,*,depth=0):
 """Expand actual SZARRAY elements; no array storage or grammar is inferred."""
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 need('bounded-actual-type-symbol',depth<16 and type(pointer)is int and pointer>0)
 value=ContextSymbols(image).type(pointer);raw=_raw(value)
 if raw[10]==29:
  need('ordinary-symbol-array',raw[11]==0)
  element=int.from_bytes(raw[:8],'little');need('nonnull-array-element',element>0)
  value=dict(value,elementType=type_symbol(image,element,depth=depth+1))
 elif raw[10]==21:
  value=dict(value,classArguments=[type_symbol(image,a['typePointerVa'],depth=depth+1)for a in value['classArguments']])
 return value


def definition(ctx,index):
 md=ctx.image.metadata
 need('bounded-definition-index',type(index)is int and 0<=index<len(md.types));td=md.types[index];arity=0;container=None
 if td.generic_container_index>=0:
  section=md.sections['genericContainers'];at=section.offset+td.generic_container_index*16
  need('owned-container-bounds',section.offset<=at<=section.offset+section.size-16)
  owner,arity,is_method,parameter=struct.unpack_from('<iiii',md.buf,at)
  need('owned-class-container',owner==index and is_method==0 and 1<=arity<=64 and parameter>=0)
  container=dict(owner=owner,count=arity,parameterStart=parameter,containerIndex=td.generic_container_index)
 return dict(index=index,name=md.type_full_name(td),arity=arity,container=container)


def has_closed_parent(ctx,type_name):
 """Classify an actual parent record only; this supplies no ancestry proof."""
 td=getattr(getattr(ctx,'index',None),'types',{}).get(type_name)
 if td is None or td.generic_container_index>=0 or td.parent_index<0:return False
 raw=ctx.image.pe.bytes_at_va(ctx.type_pointer(td.parent_index),16)
 return len(raw)==16 and raw[10:12]==bytes((21,0))and not int.from_bytes(raw[8:10],'little')&16


def has_closed_node_parent(ctx,type_name):
 """Only a complete non-Node walk falls back; metadata failures propagate."""
 if not has_closed_parent(ctx,type_name):return False
 try:derive(ctx,type_name)
 except ValueError as error:
  if str(error)=='constructedActionAncestry.actual-NodeBase-ancestor':return False
  raise
 return True


def _unique_definition(ctx,name,index):
 rows=ctx.image.named_type_definitions.get(name,())
 need('one-exact-structural-definition',len(rows)==1 and rows[0].index==index
  and ctx.image.metadata.type_full_name(ctx.image.metadata.types[index])==name)


def _walk(ctx,type_name,current,*,first_closed,expected_first=None,structural=False):
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.reference_layouts import closed_generic_reference_pointer_extent
 image=ctx.image;md=image.metadata;symbols=ContextSymbols(image);ancestors=[];edges=[];definitions={}
 for ordinal in range(32):
  need('acyclic-actual-ancestry',current['name']not in ancestors)
  ancestors.append(current['name']);td=md.types[current['definitionTypeIndex']];declaration=definition(ctx,td.index)
  definitions[current['name']]=declaration
  if td.parent_index<0:break
  pointer=ctx.type_pointer(td.parent_index);symbol=symbols.type(pointer)
  resolved=resolve_symbol(symbol,owner_definition=td.index,arguments=current['arguments'],definition=lambda index:definition(ctx,index))
  need('parent-is-reference-class',resolved['kind']in(18,21,28)and _raw(symbol)[11]==0)
  if ordinal==0 and first_closed:
   closed=closed_generic_reference_pointer_extent(ctx,pointer)
   if expected_first is not None:
    expected,args=expected_first
    need('exact-first-closed-parent',closed['definitionTypeIndex']==ctx.index.types[expected].index
     and closed['argumentTypes']==args and closed['type']==resolved['name'])
   else:
    need('same-actual-first-closed-parent',resolved['kind']==21 and closed['type']==resolved['name']
     and closed['definitionTypeIndex']==resolved['definitionTypeIndex']
     and closed['argumentTypes']==[a['name']for a in resolved['arguments']])
    _unique_definition(ctx,resolved['definitionName'],resolved['definitionTypeIndex'])
  edges.append(dict(owner=current['name'],ownerDefinition=td.index,declaredParentTypeIndex=td.parent_index,
   declaredParentPointer=pointer,declaredSymbol=symbol,resolvedParent=resolved,
   nativeClosedParentPointerClaimed=ordinal==0 and first_closed))
  if resolved['name']in('object','System.Object'):break
  need('resolved-parent-definition',type(resolved['definitionTypeIndex'])is int)
  current=resolved
 else:raise ValueError('constructedActionAncestry.excessive-parent-chain')
 need('actual-NodeBase-ancestor','Beyond.Gameplay.NodeBase'in ancestors)
 if structural:
  node=definitions['Beyond.Gameplay.NodeBase'];need('same-actual-NodeBase-role',
   node['index']==ctx.index.types['Beyond.Gameplay.NodeBase'].index and node['arity']==0)
  _unique_definition(ctx,'Beyond.Gameplay.NodeBase',node['index'])
 return dict(schema=SCHEMA,typeName=type_name,ancestry=ancestors,definitions=definitions,edges=edges,
  closedManagedAncestryProved=True,openGenericFieldOffsetsUsed=False,nativeClosedClassIdentityProved=False,
  fieldLayoutAdmitted=False,constructorEffectsAdmitted=False,wireGrammarAdmitted=False)


def derive(ctx,type_name):
 first=ctx.index.types[type_name];finite=type_name in TYPES
 need('one-nongeneric-reference-original',first.generic_container_index<0 and not ctx.is_value_type(type_name))
 if not finite:
  need('actual-closed-reference-parent-required',has_closed_parent(ctx,type_name))
  _unique_definition(ctx,type_name,first.index)
 current=dict(name=type_name,kind=18,definitionTypeIndex=first.index,arguments=[])
 result=_walk(ctx,type_name,current,first_closed=True,expected_first=TYPES.get(type_name),structural=not finite)
 if not finite:result['selectionMode']='actual-nongeneric-Original-closed-parent-NodeBase-ancestry'
 return result


def derive_closed(ctx,pointer):
 """Actual wrapper carrier root; no named closed TypeDef or field layout."""
 from scripts.game_data.il2cpp.reference_layouts import closed_generic_reference_pointer_extent
 closed=closed_generic_reference_pointer_extent(ctx,pointer);symbol=type_symbol(ctx.image,pointer)
 root=resolve_symbol(symbol,owner_definition=closed['definitionTypeIndex'],arguments=[],definition=lambda index:definition(ctx,index))
 need('exact-closed-Original-root',root['kind']==21 and root['name']==closed['type']
  and root['definitionTypeIndex']==closed['definitionTypeIndex']and[a['name']for a in root['arguments']]==closed['argumentTypes'])
 _unique_definition(ctx,root['definitionName'],root['definitionTypeIndex'])
 result=_walk(ctx,closed['type'],root,first_closed=False,structural=True)
 result.update(selectionMode='actual-wrapper-closed-reference-carrier-NodeBase-ancestry',
  initialTypePointer=pointer,initialClosedCarrier=closed,initialResolvedType=root)
 return result


def original_ancestry(ctx,type_name):return derive(ctx,type_name)['ancestry']
