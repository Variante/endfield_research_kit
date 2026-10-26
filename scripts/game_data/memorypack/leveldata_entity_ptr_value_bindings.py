"""Exact GroupSlot EntityPtr40 field join, preserving its opaque runtime tail.

This finite domain bypasses the ordinary managed8/16 reference-map gate. It
requires the complete source, independent stored-value child, all forty copied
bits, the selected barrier at value offset24 and every enclosing return frame.
"""
import json

from scripts.game_data.memorypack import leveldata_entity_ptr_components as owner
from scripts.game_data.memorypack import leveldata_entity_ptr_value_sources as value
from scripts.game_data.memorypack import generated_entity_ptr_field_sources as field

TYPE=value.TYPE
CAPABILITY=owner.CAP


def need(check,condition):
 if not condition:raise ValueError('storyEntityPtrValueBindings.'+check)


def same(left,right):
 encode=lambda obj:json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False)
 return encode(left)==encode(right)


def require_setter(setter):
 method=setter.get('method',[]);program=setter.get('program',{});selected=program.get('selectedBytes',[])
 need('literal-owned-setter-method',len(method)==4 and all(type(method[i])is int for i in(0,3))and bool(selected))
 base=selected[0][0]-method[3];rows=setter.get('ordinarySourceRegions',[]);windows=setter.get('codeWindows',[])
 from scripts.game_data.memorypack.leveldata_tracking_raw_sources import _owned_regions
 regions=_owned_regions([(base+a,h)for a,h in rows],windows,base=base,label='EntityPtr-setter')
 family=setter.get('sourceFamily',{})
 need('whole-owned-setter-family',family.get('schema')=='endfield.amd64-unwind-chain-family.v1'
  and family.get('selectedPrimaryRva')==method[3]
  and sorted(tuple(r['runtimeTriple'][:2])for r in family.get('ranges',[]))==sorted((w['startRva'],w['endRva'])for w in windows))
 replay=field.setter_program(regions,base+method[3],field=setter['fieldOffset'],barrier=program['barrierTargetVa'])
 need('whole-setter-byte-program-replayed',same(replay,program))
 holder=setter.get('directHolder',{})
 need('own-direct-holder-without-ancestry-alias',holder.get('field')==[method[1],setter.get('targetField','').rsplit('::',1)[0],16]
  and holder.get('inheritedFieldAliasUsed')is False and holder.get('openGenericOffsetUsed')is False)
 return base


def _read_source(actual,pins):
 from scripts.game_data.memorypack.leveldata_tracking_raw_sources import _owned_regions
 need('own-fresh-hidden40-source',actual.get('schema')=='endfield.story-entity-ptr-value-source.v1'
  and actual.get('status')=='validated-conditional-source'and actual.get('nativeInputs')==pins
  and actual.get('actualSourceProved')is True and actual.get('resultAbi')=='hidden-local'
  and actual.get('wireGrammarAdmitted')is False and type(actual.get('sourceTargetRva'))is int)
 own=actual['proof'];selected=own['actualProgram']['selectedBytes'];base=selected[0][0]-actual['sourceTargetRva']
 regions=_owned_regions(own['actualSourceRegions'],own['actualWindows'],base=base,label='EntityPtr-ReadValue')
 calls=[]
 for index,(at,h)in enumerate(selected[:-1]):
  if h.lower()!='e8':continue
  next_at,hexed=selected[index+1];encoded=bytes.fromhex(hexed)
  need('complete-owned-hidden40-call',next_at==at+1 and len(encoded)==4)
  calls.append(at+5+int.from_bytes(encoded,'little',signed=True))
 actual_paths=[p for p in own.get('adapter',{}).get('paths',[])if p.get('profile')=='actual-slot-match']
 need('two-selected-provider-dispatch-calls',len(calls)==2 and len(actual_paths)==3
  and all(p.get('selectedInstructions')and p['selectedInstructions'][0]==calls[1]for p in actual_paths))
 replay=value.read_program(regions,base+actual['sourceTargetRva'],provider=calls[0],dispatch=calls[1])
 need('whole-hidden40-source-replayed',same(replay,own['actualProgram']))
 return base


def _field_program(scope,read,setter,base):
 from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
 from scripts.game_data.memorypack.generated_member_sources import _displacement
 rows=scope['selectedProgram'];regions=[(base+a,bytes.fromhex(h))for a,h in rows]
 g=_owned_setter_trace(regions,base+read['instruction'][0]+5,scope['codeWindows'],base)
 g.take('4885f6');g.branch('0f84',False);g.take('488b4e10','4885c9');g.branch('0f84',False)
 g.take('0f10442420','0f104c2430');stores=[]
 for offset,size,prefix in((0,16,'0f1141'),(16,16,'0f1149'),(32,8,'f20f1141')):
  if offset==16:g.take('f20f10442440')
  at=g.at;raw=_displacement(prefix,setter['fieldOffset']+offset);g.take(raw)
  stores.append(dict(instruction=[at-base,raw.upper()],sourceOffset=offset,storedBytes=size,memberIndex=read['memberIndex']))
 address=setter['fieldOffset']+24
 g.take('4883c1'+bytes((address,)).hex()if address<128 else'4881c1'+address.to_bytes(4,'little').hex())
 g.call(setter['program']['barrierTargetVa'])
 return stores


def bind(source,scope,read,pins,usage,component,capability):
 index=read.get('memberIndex');need('complete-finite-GroupSlot-parent',
  source.get('schema')=='endfield.generated-concrete-reader-source.v1'
  and source.get('wrappedType')=='Beyond.Gameplay.EnemyGroupSlot'and read.get('fieldName')=='entityPtr'
  and source.get('nativeInputs')==scope.get('nativeInputs')==component.get('nativeInputs')==pins
  and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
  and source.get('wholeOwnerAdmitted')is False and source.get('sourceScope')==scope
  and type(index)is int and 0<=index<len(source.get('orderedSourceReads',[]))
  and same(source['orderedSourceReads'][index],read)and same(scope.get('events'),source['orderedSourceReads']))
 need('separate-exact-wire-child',capability==CAPABILITY
  and component.get('schema')=='endfield.story-entity-ptr-value-component.v1'
  and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
 actual=scope.get('managedValueSources',{}).get(str(index),{});child=component.get('proof',{}).get('readSource',{})
 need('same-fresh-child-and-capability',same(actual,child)and same(component.get('capabilities'),{CAPABILITY:owner.capability(child)}))
 base=_read_source(actual,pins);context=read.get('context',{});argument=bytes.fromhex(context.get('argumentRawHex',''))
 need('exact-opaque40-event',read.get('kind')=='managed:'+TYPE and read.get('declaredType')==TYPE
  and read.get('mode')=='typed-managed-value'and read.get('resultAbi')=='hidden-local'
  and type(read.get('managedBytes'))is int and read['managedBytes']==40 and'wireBytes'not in read
  and read.get('actualSourceProved')is True and read.get('sourceContextMode')is None)
 setter=source['setters'][index];field.validate_event(read,setter);need('same-whole-owned-setter',same(setter,scope['richSetters'][index]))
 need('same-own-setter-and-child-layout',same(setter.get('managedValueLayout'),child['proof']['layout'])
  and require_setter(setter)==base and setter.get('incomingValueStoredUnchanged')is True
  and setter.get('childGrammarAdmitted')is False and setter.get('factoryAdmitted')is False
  and setter['method'][0]==setter['member'].get('methodIndex')and setter['method'][1]==source.get('wrapperName')
  and setter['member'].get('declaringWrapper')==setter['method'][1]and setter['member'].get('name')=='entityPtr'
  and setter['member'].get('declaredType')==TYPE and type(setter.get('fieldOffset'))is int and setter['fieldOffset']>=16
  and setter['method'][2]=='set___entityPtr__'and setter['targetField']==source['wrappedType']+'::entityPtr'
  and setter['program']['barrierTargetVa']==base+child['proof']['layout']['runtimeOnlyObjectPtr']['barrierTargetRva'])
 load=bytes.fromhex(context.get('instructionHex',''));call_rva,encoded=read['instruction'];call=bytes.fromhex(encoded)
 need('exact-actual-nominal-R8-ReadValue-E8',same(usage,child['proof']['typedRequest'])
  and(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
   (6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE])
  and same(context.get('methodSpec'),usage.get('methodSpec'))and context.get('instructionRva')==usage.get('instructionRva')
  and context.get('instructionHex')==usage.get('instructionHex')and len(load)==7 and load[:3]==bytes.fromhex('4c8b05')
  and len(argument)==16 and argument[10:12]==bytes((17,128))
  and int.from_bytes(argument[:8],'little')==child['proof']['layout']['typeDefinition']==context.get('typeDefinition')
  and[context.get('instructionRva'),context.get('instructionHex')]in scope.get('selectedProgram',[])
  and read['instruction']in scope.get('selectedProgram',[])
  and base+context['instructionRva']+7+int.from_bytes(load[3:],'little',signed=True)==context.get('cellVa')
   ==base+usage.get('usageCellRva',-1)
  and type(call_rva)is int and len(call)==5 and call[0]==232
  and call_rva+5+int.from_bytes(call[1:],'little',signed=True)==read['sourceTargetRva']==child['sourceTargetRva']
  and child['readerMethodDefinition']==usage['methodSpec'][0])
 rich=scope.get('richProgram',{});need('complete-rich-field-path',rich.get('completeSelectedNormalProgram')is True
  and rich.get('childGrammarAdmitted')is False and rich.get('wholeOwnerAdmitted')is False
  and same(rich.get('selectedProgram'),scope['selectedProgram']))
 sources=[r for r in rich.get('sources',[])if r.get('memberIndex')==index]
 need('one-actual-owned-hidden40-source',len(sources)==1 and same(sources[0].get('instruction'),read['instruction'])
  and sources[0].get('resultAbi')=='hidden-local')
 stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index]
 need('all40-bit-stores-and-selected-barrier-replayed',same(stores,_field_program(scope,read,setter,base)))
 hidden=[r for r in rich.get('hiddenSourceLocals',[])if r.get('memberIndex')==index]
 need('own-exact-hidden40-local',len(hidden)==1 and type(hidden[0].get('displacement'))is int
  and hidden[0]['displacement']==32 and type(hidden[0].get('bytes'))is int and hidden[0]['bytes']==40
  and same(hidden[0].get('sourceInstruction'),read['instruction'])and hidden[0].get('nominalTypeName')==TYPE
  and hidden[0].get('nominalTypeDefinition')==context['typeDefinition']
  and hidden[0].get('opaqueRuntimeStorageRanges')==[[24,40]]and hidden[0].get('selectedBarrierValueOffsets')==[24]
  and hidden[0].get('runtimeReferenceLayoutAdmitted')is False and hidden[0].get('completeRuntimePaddingMapAdmitted')is False
  and'referenceLaneOffsets'not in hidden[0]
  and[r for r in rich.get('sourceLocalCopies',[])if r.get('memberIndex')==index]==[])
 paths=source.get('programs',[]);frame_bytes=scope.get('headerProof',{}).get('nullFrameBytes')
 need('four-complete-frames-and-owned-hidden40-home',len(paths)==4 and type(frame_bytes)is int and frame_bytes>=72
  and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool
   and p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
  and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)}
  and all([32-frame_bytes,40]in p['frame'].get('hiddenSourceLocalHomes',[])for p in paths if not p['wrapperNull']))
 return dict(fieldName=read['fieldName'],typeName=TYPE,capability=capability,readerMethodDefinition=usage['methodSpec'][0],
  sourceTargetRva=read['sourceTargetRva'],managedValueCapabilityShape=component['capabilities'][capability],
  storedBytes=40,managedBytes=40,selectedBarrierValueOffsets=[24],knownPaddingByteRanges=[[1,8],[20,24]],opaqueRuntimeStorageRanges=[[24,40]],
  runtimeReferenceLayoutAdmitted=False,completeRuntimePaddingMapAdmitted=False,
  actualCallbackEqualsProvedChildRequired=True,completeFieldTransferAndFrameProved=True,
  ordinaryReferenceIdentityClaimed=False,wholeOwnerAdmitted=False)
