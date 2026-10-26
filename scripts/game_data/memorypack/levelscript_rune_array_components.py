"""Rune's exact Int32 and raw Boolean arrays, with a count bound of 64.

Each source retains its actual closed MethodInfo, helper bodies and parent
call. The Boolean forwarder and one-byte storage are separate from the
Int32 clone and four-byte multiplication. Neither is a reference array.
"""
import json

from scripts.game_data.memorypack import module_unmanaged_array_sources as source

SCHEMA='endfield.story-rune-array-components.v1'
WIRE='story-module-primitive-array64'
OWNER='Beyond.Gameplay.RunePuzzleData'
MEMBERS={3:('backIndex','int'),6:('forbidTransitMasks','int'),7:('forwardIndex','int'),
 8:('initAnchorPointMatch','bool'),9:('initOccupiedIndex','bool'),10:('leftIndex','int'),
 11:('rightIndex','int'),14:('runeTypeMap','int'),15:('slidePriorityIndexList','int'),16:('slideTargetIndexMap','int')}


def need(check,condition):
 if not condition:raise ValueError('storyRuneArray.'+check)


def norm(value):return json.loads(json.dumps(value))


def key(element):
 need('two-explicit-primitive-elements',element in('int','bool'))
 return 'story-module-'+('int32'if element=='int'else'boolean8')+'-array64'


def _rows(raw,windows,rows,base,label):
 need(label+'-complete-owned-row-partition',all(b''.join(bytes.fromhex(r['bytes'])for r in rows
  if base+w['startRva']<=int(r['va'],16)<base+w['endRva'])==data for w,(_,data)in zip(windows,raw,strict=True)))


def compose(actual,pins,*,offsets,advance,copy,header=None):
 from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
 from scripts.game_data.memorypack.generated_called_advance_sources import advance_program
 from scripts.game_data.il2cpp.bounded_copy_sources import prove_bounded_copy
 from scripts.game_data.il2cpp.string_source_programs import prove_collection_header
 from scripts.game_data.memorypack import npc_array_sources as arrays
 element=actual.get('elementType');capability=key(element);boolean=element=='bool';width=1 if boolean else 4
 need('own-complete-primitive-source',actual.get('schema')=='endfield.module-unmanaged-array-source.v1'
  and actual.get('status')=='validated-conditional-source'and actual.get('nativeInputs')==pins
  and actual.get('typeName')==element+'[]'and actual.get('headerBytes')==4 and actual.get('elementWireBytes')==width
  and type(actual.get('countLimit'))is int and actual['countLimit']==64 and actual.get('collectionCounts')==[-1,0]
  and actual.get('resultRegister')=='rax'and all(actual.get(k)is True for k in('positiveCountsAdmitted','rawBitsPreserved',
   'completeBufferedSourceProved','entryRspRestored','allNonvolatilesRestored'))
  and all(actual.get(k)is False for k in('elementCallbackUsed','booleanNormalizationClaimed','parentFieldAdmitted','wholeOwnerAdmitted')))
 p=actual['proof'];paths=p['programs'];entry=(paths[0]if boolean else paths[0]['program'])['selectedBytes'][0][0]
 caller_entry=(p['forwarder']['selectedBytes'][0][0]if boolean else entry);base=caller_entry-actual['targetRva']
 need('selected-image-and-distinct-Reader-offsets',type(base)is int and base>=1<<32
  and set(offsets)=={'currentPtr','bufferLength','advancedCount','consumed','totalLength'}
  and all(type(v)is int and 0<=v<128 for v in offsets.values())and len(set(offsets.values()))==5)
 raw=regions(p['sourceWindows'],[[a-base,h]for a,h in p['sourceRegions']],base,'Rune-'+element+'-bulk')
 caller=regions(p['callerSourceWindows'],[[a-base,h]for a,h in p['callerSourceRegions']],base,'Rune-'+element+'-caller')
 symbols={k:base+v for k,v in p['symbolRvas'].items()}
 if boolean:
  forward=source.boolean_forwarder(caller,caller_entry)
  need('own-Boolean-forwarder-and-Dangerous-target',norm(forward)==p['forwarder']and forward['dangerousTargetVa']==entry)
  parsed=[source.boolean_program(raw,entry,offsets,symbols,count=n)for n in(-1,0,1)]
 else:
  need('actual-Int32-clone-not-an-invented-forwarder',raw==caller and p['forwarder']is None)
  parsed=[source.int32_program(raw,entry,offsets,symbols,count=n)for n in(-1,0,1)]
 need('all-three-complete-buffered-paths',norm(parsed)==paths)
 helpers={k:regions(v['windows'],[[a-base,h]for a,h in v['regions']],base,'Rune-'+element+'-'+k)for k,v in p['helperBodies'].items()}
 expected=dict(empty=source.empty_program(helpers['empty'],symbols['empty'],symbols,element_type=element))
 if boolean:
  expected.update(allocate=source.boolean_allocate(helpers['allocate'],symbols['allocate'],symbols),
   dataReference=source.boolean_data_reference(helpers['dataReference'],symbols['dataReference'],symbols),
   getReference=source.boolean_get_reference(helpers['getReference'],symbols['getReference']),
   asSpan=source.boolean_as_span(helpers['asSpan'],symbols['asSpan'],symbols),
   spanConstructor=source.boolean_span_constructor(helpers['spanConstructor'],symbols['spanConstructor']))
  need('own-full-Boolean-header-source',isinstance(header,dict))
  hr=regions(header['windows'],header['regions'],base,'Rune-Boolean-header');rows=header['rows'];_rows(hr,header['windows'],rows,base,'header')
  first=next(w for w in header['windows']if base+w['startRva']==symbols['header'])
  primary=[r for r in rows if base+first['startRva']<=int(r['va'],16)<base+first['endRva']]
  cold=[r for r in rows if r not in primary];hs={k:base+v for k,v in header['symbolRvas'].items()}
  need('same-complete-signed-count-header',norm(prove_collection_header(primary,cold,offsets,hs))==p['collectionHeader'])
 else:
  need('Int32-header-is-inline',header is None and p['collectionHeader']is None)
  expected.update(allocate=arrays.int_allocate(helpers['allocate'],symbols['allocate'],symbols),
   dataReference=arrays.int_data_reference(helpers['dataReference'],symbols['dataReference'],symbols),
   asSpan=arrays.array_as_span(helpers['asSpan'],symbols['asSpan'],symbols),
   spanConstructor=arrays.array_span_constructor(helpers['spanConstructor'],symbols['spanConstructor']))
 need('all-owned-typed-helper-programs',norm(expected)==p['helpers'])
 ar=regions(advance['windows'],advance['regions'],base,'Rune-Advance')
 advanced=[advance_program(ar,symbols['advance'],offsets,zero=z)for z in(False,True)]
 need('four-Reader-updates-and-zero-path',norm(advanced)==norm(advance['programs']))
 cr=regions(copy['windows'],copy['regions'],base,'Rune-copy');_rows(cr,copy['windows'],copy['rows'],base,'copy')
 tables={t['startRva']:bytes.fromhex(t['raw'])for t in copy['tables']}
 copied=prove_bounded_copy(cr,symbols['copy'],rows=copy['rows'],tables=tables,image_base=base)
 need('complete-raw-copy-with-sufficient-bound',norm(copied)==p['copy']and copied['maxBytes']>=64*width)
 request=p['context']['typedRequest'];call=p['actualCall'];encoded=bytes.fromhex(call['sourceInstruction'][1])
 need('own-exact-actual-closed-request-and-E8',tuple(request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
  (6,'MemoryPack.MemoryPackReader','ReadUnmanagedArray',[],[element])and request['methodSpec'][0]==actual['readerMethodDefinition']
  and len(encoded)==5 and encoded[0]==232 and call['sourceInstruction'][0]+5+int.from_bytes(encoded[1:],'little',signed=True)==actual['targetRva'])
 cap=dict(typeName=element+'[]',elementType=element,headerBytes=4,elementWireBytes=width,countLimit=64,countRange=[-1,64],nullable=True,
  positiveCountsAdmitted=True,rawBitsPreserved=True,booleanNormalizationClaimed=False,wholeGrammarAdmitted=True,elementCallbackUsed=False,
  readerMethodDefinition=actual['readerMethodDefinition'],sourceTargetRva=actual['targetRva'],parentFieldAdmitted=False,wholeOwnerAdmitted=False)
 return dict(schema=SCHEMA,status='validated-conditional-story-rune-array',nativeInputs=pins,capability=capability,capabilities={capability:cap},
  requiredExternalCapabilities=[],proof=dict(arraySource=actual,readerOffsets=offsets,advanceSource=advance,copySource=copy,headerSource=header),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def validate_component(component,pins):
 need('exact-own-component',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
  and component.get('status')=='validated-conditional-story-rune-array'and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
 p=component['proof'];checked=compose(p['arraySource'],pins,offsets=p['readerOffsets'],advance=p['advanceSource'],copy=p['copySource'],header=p['headerSource'])
 need('exact-only-owned-capability',all(component.get(k)==checked[k]for k in('capability','capabilities','requiredExternalCapabilities')))
 return dict(capability=checked['capability'],capabilities=checked['capabilities'],requiredExternalCapabilities=[])


def derive(image,pins,*,typed_request,call_target,source_instruction,element_type):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack.pointer_param import owned
 from scripts.game_data.memorypack import scalar_param_native as scalar
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack.generated_called_advance_sources import advance_program
 from scripts.game_data.il2cpp.memory_moves import decode_memory_move_instructions
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
 from scripts.game_data.contracts import CONTRACTS_DIR
 _publication_gate(image,pins);base=image.pe.image_base
 actual=source.derive(image,pins,typed_request=typed_request,call_target=call_target,source_instruction=source_instruction,element_type=element_type,count_limit=64)
 offsets=scalar.reader_offsets(image,'storyRuneArray');offsets['totalLength']=NativeReferenceContext(image).field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 symbols={k:base+v for k,v in actual['proof']['symbolRvas'].items()};body=owned(image,symbols['advance'])
 advance=dict(windows=body['windows'],regions=[[a-base,b.hex()]for a,b in body['regions']],
  programs=[advance_program(body['regions'],body['pointer'],offsets,zero=z)for z in(False,True)])
 fact=json.loads((CONTRACTS_DIR/'memory_copy_bounded_native.json').read_bytes());need('selected-copy-inputs-and-target',fact['nativeInputs']==pins and base+fact['entryRva']==symbols['copy'])
 rows=[];values=[]
 for w in fact['ownedWindows']:
  raw=image.window_bytes(w);values.append([w['startRva'],raw.hex()]);rows+=decode_memory_move_instructions(image.mapper,raw,base+w['startRva'])
 copy=dict(windows=fact['ownedWindows'],regions=values,rows=rows,tables=fact['tables']);header=None
 if element_type=='bool':
  body=owned(image,symbols['header']);rows=[]
  for at,raw in body['regions']:rows+=decode_type_data_initialization_instructions(image.mapper,raw,at)
  first,= [w for w in body['windows']if base+w['startRva']==symbols['header']]
  cold=[r for r in rows if not base+first['startRva']<=int(r['va'],16)<base+first['endRva']]
  calls=[control_transfer(r)['target']for r in cold if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
  need('exact-three-owned-header-cold-calls',len(calls)==3)
  header=dict(windows=body['windows'],regions=[[a-base,b.hex()]for a,b in body['regions']],rows=rows,
   symbolRvas={k:v-base for k,v in zip(('getNextSpan','advanceFallback','insufficient'),calls,strict=True)})
 result=norm(compose(actual,pins,offsets=offsets,advance=advance,copy=copy,header=header));_publication_gate(image,pins);return result


def bind_member(full,scope,read,pins,usage,component,capability):
 own=validate_component(component,pins);index=read['memberIndex'];actual=component['proof']['arraySource'];element=actual['elementType']
 need('only-exact-Rune-array-fields',full.get('wrappedType')==OWNER and MEMBERS.get(index)==(read.get('fieldName'),element)
  and read.get('declaredType')==element+'[]'and read.get('mode')=='typed-unmanaged-primitive-array')
 need('same-complete-parent-and-ordered-read',full.get('schema')=='endfield.generated-concrete-reader-source.v1'and full.get('nativeInputs')==pins
  and full.get('completeSelectedCallerAdmitted')is True and full.get('sourceScope')==scope
  and full['orderedSourceReads'][index]==scope['events'][index]==read)
 need('same-actual-child-source',scope['arraySources'][str(index)]==actual)
 need('same-actual-typed-request-and-capability',usage==actual['proof']['context']['typedRequest']and capability==own['capability'])
 setter=scope['richSetters'][index];source.bind_member(actual,read['context'],read,setter,pins,owner=OWNER)
 rich=scope['richProgram'];stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index];flows=[r for r in rich.get('sources',[])if r.get('memberIndex')==index]
 need('whole-RAX-array-reference-to-own-named-field',rich.get('completeSelectedNormalProgram')is True and rich.get('selectedProgram')==scope.get('selectedProgram')
  and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='rax')]
  and len(stores)==1 and(stores[0].get('sourceOffset'),stores[0].get('storedBytes'))==(0,8)
  and stores[0]['instruction']in scope['selectedProgram']and full['setters'][index]==setter
  and setter.get('incomingValueStoredUnchanged')is True and setter.get('targetField')==OWNER+'::'+read['fieldName'])
 at,h=stores[0]['instruction'];raw=bytes.fromhex(h)
 need('actual-complete-owned-setter-call',len(raw)==5 and raw[0]in(232,233)and at+5+int.from_bytes(raw[1:],'little',signed=True)==setter['method'][3])
 paths=full['programs'];need('all-four-complete-Rune-frames',len(paths)==4
  and{(p.get('existing'),p.get('wrapperNull'))for p in paths}=={(n,f)for n in(False,True)for f in(False,True)}
  and all(p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
 return dict(fieldName=read['fieldName'],typeName=element+'[]',capability=capability,readerMethodDefinition=actual['readerMethodDefinition'],
  sourceTargetRva=actual['targetRva'],allFourParentFramesProved=True,rawBooleanBitsPreserved=element=='bool')
