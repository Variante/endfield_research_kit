"""Exact reference-valued Param parent composed with its own raw12 Vector3 list.

The legacy declaration remains null-only. Its fresh whole parent proves the
MC4/FF wrapper and signed bindings; the independent closed list owns buffered
raw12 elements, full12 stores and bounded induction. Ready compatible provider
selection, count-sized allocation and sufficient disjoint storage remain
conditions. This grants no enclosing action or runtime invocation.
"""
import json
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.memorypack import null_list_param,leveldata_vector3_list_sources as vectors
from scripts.game_data.memorypack.counted_loop_sources import prove_induction

SCHEMA='endfield.levelscript-positive-vector3-list-sources.v1'
KIND='Param<List<Vector3>>'
LIMIT=4096
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Actions_Param_System_Collections_Generic_List_UnityEngine_Vector3__ForMemoryPack'


def need(check,condition):
 if not condition:raise ValueError('positiveVector3List.'+check)


def same(a,b):return json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True)


def validate(value,pins):
 need('identity',value.get('schema')==SCHEMA and value.get('nativeInputs')==pins
  and value.get('status')=='validated-conditional-positive-vector3-list')
 need('bounded-domain',type(value.get('countLimit'))is int and value['countLimit']==LIMIT
  and value.get('codecKind')==KIND and value.get('elementWireBytes')==12
  and value.get('parentFieldAdmitted')is False and value.get('wholeOwnerAdmitted')is False)
 p=value['proof'];c=p['collection'];cap=c['capability'];ctx=c['proof']['context'];parent=p['parent']
 need('own-nominal-list',c.get('nativeInputs')==pins and c.get('schema')=='endfield.story-vector3-list-component.v1'
  and c.get('status')=='validated-conditional-vector3-list'
  and all(type(cap.get(k))is type(v)and cap[k]==v for k,v in dict(typeName=vectors.LIST,elementType=vectors.TYPE,
   capability=vectors.CAP,countLimit=LIMIT,countRange=[-1,LIMIT],elementWireBytes=12,managedElementBytes=12,
   elementRecordHeaderBytes=0,positiveCountsAdmitted=True,initiallyNullListRequired=True,finiteFloatProfile=True).items()))
 need('own-raw12-callback-and-layout',c['proof']['layout']==[['float',16],['float',20],['float',24]]
  and c['proof']['callback']['wireBytes']==12 and c['proof']['callback']['outputBytes']==12
  and c['proof']['callback']['rawSourceSlices']==[[0,8],[8,4]]
  and all(p['selectedCallback']==c['proof']['callbackRegistration']['pointer']for p in c['proof']['listPrograms']if p['countWitness']>0))
 need('own-count-induction',same(c['proof']['induction'],prove_induction(c['proof']['listPrograms'],initial='4533e4',
  increment='41ffc4',comparison='453be5',counter='r12d',saved_count='r13d',max_count=LIMIT)))
 usage=parent['typedRead']
 need('exact-Param-parent',p['wrapperName']==WRAPPER and tuple(usage.get(k)for k in
  ('typeName','methodName','classArguments','methodArguments'))==('MemoryPack.MemoryPackReader','ReadPackable',[],[vectors.LIST]))
 need('same-actual-closed-request',same(ctx['typedRequest'],usage)and ctx['closedListType']==vectors.LIST
  and ctx['callTargetRva']==p['sourceTargetRva']==cap['packableReaderTargetRva']
  and cap['packableReaderMethodDefinition']==usage['methodSpec'][0])
 read=ctx['referenceSource']['source']
 need('fresh-null-local-before-list',read['zeroLocalBits']==64 and read['formatterSlot']==5
  and read['callbackArguments']['output']=='same zero-initialized local8'
  and read['returnValue']=='complete same local8 to RAX')
 rows=parent['parent']['instructions'];at,encoded=rows[22];raw=bytes.fromhex(encoded)
 need('actual-parent-E8',len(raw)==5 and raw[0]==232
  and at+5+int.from_bytes(raw[1:],'little',signed=True)==p['sourceTargetRva']
  and rows[19][0]==usage['instructionRva'])
 return value


def derive(image,pins):
 path=CONTRACTS_DIR/'levelscript_null_list_param_native.json';raw=path.read_bytes();fact=json.loads(raw)
 need('reviewed-selected-inputs',fact['nativeInputs']==pins)
 row,=[r for r in fact['components']if r['codecKind']==KIND]
 need('exact-legacy-domain',row['valueType']==vectors.LIST and row['collectionCounts']==[-1]
  and row['profile']['registration']['wrapperType']==WRAPPER)
 parent=null_list_param.derive(image,pins,row['profile'],row['valueType'],collection_counts=[-1])
 validate_claims(row['proof'],parent,label='positiveVector3List.parent')
 validate_claims(parent,row['proof'],label='positiveVector3List.parentDeclaration')
 at,encoded=parent['parent']['instructions'][22];code=bytes.fromhex(encoded)
 need('parent-E8-opcode',len(code)==5 and code[0]==232)
 target=at+5+int.from_bytes(code[1:],'little',signed=True)
 collection=vectors.derive(image,pins,typed_request=parent['typedRead'],call_target=image.pe.image_base+target)
 result=dict(schema=SCHEMA,status='validated-conditional-positive-vector3-list',nativeInputs=dict(pins),
  codecKind=KIND,countLimit=LIMIT,elementWireBytes=12,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  proof=dict(wrapperName=WRAPPER,parent=parent,sourceTargetRva=target,collection=collection))
 validate(result,pins);need('contract-bookend',path.read_bytes()==raw)
 return result
