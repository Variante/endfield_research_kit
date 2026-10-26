"""Own Param<List<UInt64>> parent, zero local and independent raw64 loop.

String or Entity names/widths supply no UInt64 grammar. The exact primitive
carrier, owned raw8 callback, count-sized fresh storage and signed counter's
same-head backedge are proved by the current UInt64 collection owner. Ready
compatible provider/callback selection and disjoint normal helper effects
remain conditions; no containing action, live state or EOF is admitted.
"""
import json
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.memorypack import null_list_param,levelscript_collection_sources as lists

SCHEMA='endfield.levelscript-positive-ulong-list-sources.v1'
KIND='Param<List<ulong>>'
LIST='System.Collections.Generic.List`1<ulong>'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Actions_Param_System_Collections_Generic_List_ulong__ForMemoryPack'
LIMIT=4096


def need(check,condition):
 if not condition:raise ValueError('positiveUlongList.'+check)


def same(a,b):return json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True)


def validate(value,pins):
 need('identity',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-positive-ulong-list'
  and value.get('nativeInputs')==pins and value.get('codecKind')==KIND
  and type(value.get('countLimit'))is int and value['countLimit']==LIMIT
  and value.get('wholeOwnerAdmitted')is False and value.get('parentFieldAdmitted')is False)
 p=value['proof'];c=p['collection'];parent=p['parent'];u=parent['typedRead']
 expected=dict(schema='endfield.levelscript-uint64-list-component.v1',status='validated-conditional-uint64-list-component',
  typeName=LIST,elementType='ulong',countLimit=LIMIT,countRange=[-1,LIMIT],nullable=True,positiveCountsAdmitted=True,
  headerBytes=4,elementWireBytes=8,elementRawBits=64,rawBitsPreserved=True,initiallyNullOutputRequired=True,
  actualCallbackEqualsProvedChildRequired=True,runtimeProviderSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
 need('own-UInt64-capability',c.get('nativeInputs')==pins and all(type(c.get(k))is type(v)and c[k]==v for k,v in expected.items()))
 need('actual-Param-closed-request',p['wrapperName']==WRAPPER and tuple(u.get(k)for k in('typeName','methodName','classArguments','methodArguments'))
  ==('MemoryPack.MemoryPackReader','ReadPackable',[],[LIST])and same(c['typedRequest'],u)
  and c['packableReaderMethodDefinition']==u['methodSpec'][0]and c['packableReaderTargetRva']==p['sourceTargetRva'])
 child,=c['closedCarrier']['classArguments']
 need('exact-ordinary-unsigned64-element',child['name']=='ulong'and bytes.fromhex(child['rawHex'])[10:12]==b'\x0b\x80')
 source=c['proof'];need('own-complete-raw64-callback',source['formatter']['wireBytes']==8 and source['formatter']['resultBytes']==8
  and source['formatter']['rawBits']==64 and source['formatter']['normalReturn']is True)
 need('same-positive-callback-and-return',len(source['programs'])==3 and
  [r['countProfile']for r in source['programs']]==['null','zero','all-positive-Int32']
  and source['programs'][2]['callback']==source['elementEntry']['pointer']
  and all(r['normalReturn']is True and r['elementBytes']==8 and r['elementBitsPreserved']==64 for r in source['programs']))
 read=source['referenceSource']['source']
 need('actual-null-local-before-list',read['zeroLocalBits']==64 and read['formatterSlot']==5
  and read['callbackArguments']['output']=='same zero-initialized local8'and read['returnValue']=='complete same local8 to RAX')
 rows=parent['parent']['instructions'];at,h=rows[22];raw=bytes.fromhex(h)
 need('exact-parent-E8',len(raw)==5 and raw[0]==232 and rows[19][0]==u['instructionRva']
  and at+5+int.from_bytes(raw[1:],'little',signed=True)==p['sourceTargetRva'])
 return value


def derive(image,pins):
 path=CONTRACTS_DIR/'levelscript_null_list_param_native.json';raw=path.read_bytes();fact=json.loads(raw)
 need('reviewed-inputs',fact['nativeInputs']==pins)
 row,=[r for r in fact['components']if r['codecKind']==KIND]
 need('exact-legacy-parent',row['valueType']==LIST and row['collectionCounts']==[-1,0]
  and row['profile']['registration']['wrapperType']==WRAPPER)
 parent=null_list_param.derive(image,pins,row['profile'],LIST,collection_counts=[-1,0])
 validate_claims(row['proof'],parent,label='positiveUlongList.parent')
 validate_claims(parent,row['proof'],label='positiveUlongList.parentDeclaration')
 at,h=parent['parent']['instructions'][22];code=bytes.fromhex(h)
 need('parent-E8-opcode',len(code)==5 and code[0]==232)
 target=at+5+int.from_bytes(code[1:],'little',signed=True)
 collection=lists.derive_ulong_list_component(image,pins,typed_request=parent['typedRead'],call_target=image.pe.image_base+target,count_limit=LIMIT)
 result=dict(schema=SCHEMA,status='validated-conditional-positive-ulong-list',nativeInputs=dict(pins),codecKind=KIND,
  countLimit=LIMIT,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  proof=dict(wrapperName=WRAPPER,parent=parent,sourceTargetRva=target,collection=collection))
 validate(result,pins);need('contract-bookend',path.read_bytes()==raw);return result
