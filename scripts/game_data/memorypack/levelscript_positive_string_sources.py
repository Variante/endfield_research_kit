"""Finite positive STRING list sources with their own actual parent requests.

The existing reviewed declarations remain their original witness domains.
Fresh strict list/callback sources and count induction supply this separate
bounded capability; a reference stride never supplies the element wire codec.
"""
import json
import copy

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.memorypack import skill_pooled_string_list_sources as strings
from scripts.game_data.memorypack import reference_list_induction_sources as induction

SCHEMA='endfield.levelscript-positive-string-list-sources.v1'
LIMIT=4096
KINDS=('List<string>','Param<List<string>>')
NPC='Beyond.Gameplay.Core.NpcRuntimeProxyData'
NPC_FIELD='npcGamePlayDataKeyList'


def need(check,condition):
 if not condition:raise ValueError('positiveStringList.'+check)


def same(a,b):
 return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))


def _finish(component,pins,kind,parent):
 result=dict(schema=SCHEMA,status='validated-conditional-positive-string-list',nativeInputs=dict(pins),
  codecKind=kind,countLimit=LIMIT,wireCountBytes=4,elementWireBytes=4,
  stringEncoding='int32-pool-index',positiveCountsAdmitted=True,
  wholeOwnerAdmitted=False,parentFieldAdmitted=False,
  proof=dict(collection=component,parent=parent))
 validate(result,pins);return result


def validate(value,pins):
 need('schema-and-selected-inputs',value.get('schema')==SCHEMA and value.get('nativeInputs')==pins
  and value.get('status')=='validated-conditional-positive-string-list')
 need('finite-kind',value.get('codecKind')in(*KINDS,'NpcRuntimeProxyData.'+NPC_FIELD))
 need('bounded-wire',type(value.get('countLimit'))is int and value['countLimit']==LIMIT
  and value.get('wireCountBytes')==4 and value.get('elementWireBytes')==4
  and value.get('stringEncoding')=='int32-pool-index'and value.get('positiveCountsAdmitted')is True
  and value.get('wholeOwnerAdmitted')is False and value.get('parentFieldAdmitted')is False)
 c=value['proof']['collection'];p=c['proof'];listing=p['listComponent']
 need('own-full-string-capability',c.get('nativeInputs')==pins and set(c.get('capabilities',{}))=={strings.CAPABILITY}
  and same(c['capabilities'][strings.CAPABILITY],strings.capability(listing,p['stringCallback']))
  and c.get('requiredExternalCapabilities')==['byte-payload'])
 need('own-count-induction',same(induction._certificate(listing['witnessComponent'],count_limit=LIMIT)['induction'],listing['induction'])
  and listing['countRange']==[-1,LIMIT])
 parent=value['proof']['parent'];w=listing['witnessComponent']
 expected_wrapper={'List<string>':'Beyond.MemoryPack.Beyond_Gameplay_Actions_SwitchStringForMemoryPack',
  'Param<List<string>>':'Beyond.MemoryPack.Beyond_Gameplay_Actions_Param_System_Collections_Generic_List_string__ForMemoryPack',
  'NpcRuntimeProxyData.'+NPC_FIELD:'Beyond.MemoryPack.Beyond_Gameplay_Core_NpcRuntimeProxyDataForMemoryPack'}[value['codecKind']]
 need('finite-parent-wrapper',parent.get('wrapperName')==expected_wrapper)
 if value['codecKind']=='List<string>':need('literal-parent-field',parent.get('fieldName')=='_caseValueList')
 if value['codecKind'].startswith('NpcRuntimeProxyData.'):need('NPC-parent-field',parent.get('fieldName')==NPC_FIELD)
 u=parent['typedRequest']
 need('exact-parent-ReadPackable',tuple(u.get(k)for k in('typeName','methodName','classArguments','methodArguments'))
  ==('MemoryPack.MemoryPackReader','ReadPackable',[],[strings.LIST]))
 need('actual-parent-source-join',same(parent['typedRequest'],w['typedRequest'])
  and parent['sourceTargetRva']==w['callTargetRva']and parent['closedListType']==strings.LIST)
 return value


def _component(image,pins,usage,target,kind,**parent):
 c=strings.derive(image,pins,typed_request=usage,call_target=image.pe.image_base+target,count_limit=LIMIT)
 return _finish(c,pins,kind,dict(typedRequest=usage,sourceTargetRva=target,closedListType=strings.LIST,**parent))


def derive(image,pins,*,codec_kind):
 from scripts.game_data.memorypack import pooled_string_list_sources as pooled,null_list_param
 need('finite-kind',codec_kind in KINDS)
 path=CONTRACTS_DIR/'levelscript_pooled_string_list_native.json';raw=path.read_bytes();fact=json.loads(raw)
 need('reviewed-string-inputs',fact['nativeInputs']==pins)
 pooled.validate_components(image,fact)
 if codec_kind=='List<string>':
  parent=fact['parent'];read=parent['selectedPlan'];usage=read['typedContext'];target=read['targetRva']
  binding=dict(wrapperName=parent['wrapperName'],fieldName=parent['field'],parentSource=parent)
 else:
  route=CONTRACTS_DIR/'levelscript_null_list_param_native.json';route_raw=route.read_bytes();routes=json.loads(route_raw)
  need('reviewed-param-inputs',routes['nativeInputs']==pins)
  row,=[r for r in routes['components']if r['codecKind']==codec_kind]
  actual=null_list_param.derive(image,pins,row['profile'],row['valueType'],collection_counts=row['collectionCounts'])
  validate_claims(row['proof'],actual,label='positiveStringList.parent')
  validate_claims(actual,row['proof'],label='positiveStringList.parentDeclaration')
  usage=actual['typedRead'];at,encoded=actual['parent']['instructions'][22];code=bytes.fromhex(encoded)
  need('actual-param-E8',len(code)==5 and code[0]==232)
  target=at+5+int.from_bytes(code[1:],'little',signed=True)
  binding=dict(wrapperName=row['profile']['registration']['wrapperType'],parentSource=actual)
  need('param-contract-bookend',route.read_bytes()==route_raw)
 result=_component(image,pins,usage,target,codec_kind,**binding)
 need('string-contract-bookend',path.read_bytes()==raw)
 return result


def derive_npc(image,pins,fact):
 """The caller has independently validated the complete NPC source contract."""
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 parent,=[p for p in fact['collections']['parents']if p['original']==NPC]
 field,=[f for f in parent['fields']if f['member']['name']==NPC_FIELD]
 need('exact-owned-NPC-field',NativeReferenceContext(image).field(NPC+'::'+NPC_FIELD)[1]==strings.LIST)
 source=parent['source'];image.check_windows(source['windows'],label='positiveStringList.NPCparent')
 base=image.pe.image_base;at=field['callRva'];raw=image.pe.bytes_at_va(base+at,5)
 need('actual-NPC-E8',raw[0]==232 and at+5+int.from_bytes(raw[1:],'little',signed=True)==field['targetRva'])
 usage=derive_typed_usage_context(image,field['usage']['instructionRva'],label='positiveStringList.NPCrequest')
 need('same-NPC-closed-MethodSpec',all(same(usage[k],field['usage'][k])for k in
  ('methodSpec','instructionRva','instructionHex','methodArguments','classArguments','typeName','methodName')))
 return _component(image,pins,usage,field['targetRva'],'NpcRuntimeProxyData.'+NPC_FIELD,
  wrapperName=parent['wrapper'],fieldName=NPC_FIELD,parentSource=source)


def compose_npc_plan(plan,component,pins):
 validate(component,pins)
 need('NPC-only-positive-scope',component['codecKind']=='NpcRuntimeProxyData.'+NPC_FIELD
  and component['proof']['parent']['fieldName']==NPC_FIELD)
 result=copy.deepcopy(plan);field,=[r for r in result['root']if r['name']==NPC_FIELD]
 need('NPC-previous-null-only-field',field.get('type')==strings.LIST and field.get('wire')=='items'
  and field.get('countLimit')==-1 and field.get('element')=={'wire':'unproved'})
 field.update(countLimit=LIMIT,element=dict(wire='pool'),positiveSourceSchema=SCHEMA)
 return result
