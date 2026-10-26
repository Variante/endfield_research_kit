"""Own constructed Nullable<Single> raw8 source and complete member compiler.

Its kind21 value carrier, HasValue byte, padding and Single bits are explicit.
Neither ordinary managed kind17 nor Int64 supplies its grammar or result ABI.
"""
import hashlib,json
from scripts.game_data.memorypack import leveldata_nullable_float_sources as child

LABEL='generatedNullableValueComponents'


def need(key,condition):
 if not condition:raise ValueError(LABEL+'.'+key)


def norm(value):return json.loads(json.dumps(value))


def require_source(native,pins,context,source_rva):
 cap=native.get('capability',{});p=native.get('proof',{});usage=p.get('typedRequest',{})
 need('own-current-constructed-source',native.get('schema')=='endfield.story-nullable-single-source.v1'
  and native.get('status')=='validated-conditional-source'and native.get('nativeInputs')==pins and native.get('typeName')==child.TYPE
  and cap.get('typeName')==child.TYPE and cap.get('capability')==child.CAP and cap.get('concreteTypeKind')==21
  and cap.get('valueCarrier')is True and cap.get('managedBytes')==cap.get('wireBytes')==8 and cap.get('headerBytes')==0
  and cap.get('resultAbi')=='rax-managed-value'and cap.get('sourceTargetRva')==source_rva
  and cap.get('actualSourceProved')is True and cap.get('wireGrammarAdmitted')is True and cap.get('rawBitsPreserved')is True
  and cap.get('hasValueByteOffset')==0 and cap.get('singleBitsByteOffset')==4 and cap.get('paddingByteRanges')==[[1,3]]
  and cap.get('hasValueByteNormalized')is False and cap.get('nullHeaderAdmitted')is False
  and cap.get('actualCallbackEqualsProvedChildRequired')is True and cap.get('runtimeProviderSelectionObserved')is False)
 raw=bytes.fromhex(context.get('argumentRawHex',''))
 need('own-actual-RDX-constructed-request',len(raw)==16 and raw[10:12]==bytes((21,128))and context.get('register')=='rdx'
  and(context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'),context.get('typeKind'))==
    ('MemoryPack.MemoryPackReader','ReadValue',child.TYPE,21)
  and(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))==
    (usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec'))
  and(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
    (6,'MemoryPack.MemoryPackReader','ReadValue',[],[child.TYPE])
  and cap.get('readerMethodDefinition')==usage.get('methodSpec',[None])[0])
 program=p.get('actualReadValue',{});chunks=program.get('selectedBytes',[])
 need('literal-actual-source-entry',bool(chunks)and type(source_rva)is int and source_rva>0)
 base=chunks[0][0]-source_rva;need('literal-source-base',type(base)is int and base>=0)
 regions={}
 for name in('actual','raw8','callbackPrefix'):
  windows=p.get('sourceWindows',{}).get(name,[]);items=p.get('sourceRegions',{}).get(name,[])
  if name=='callbackPrefix':
   need('bounded-callback-prefix-window',isinstance(windows,dict)and windows.get('physicalExtentProved')is False)
   windows=[windows]
  need('all-owned-'+name+'-regions',bool(windows)and len(items)==len(windows)and len({a for a,h in items})==len(items))
  for at,h in items:
   raw=bytes.fromhex(h);matches=[w for w in windows if w.get('startRva')==at and w.get('endRva',0)-at==len(raw)]
   need('exact-'+name+'-window-hash',len(matches)==1 and hashlib.sha256(raw).hexdigest().upper()==matches[0].get('sha256'))
  regions[name]=[(base+a,bytes.fromhex(h))for a,h in items]
 symbols={k:base+v for k,v in p['sourceSymbolsRva'].items()}
 replay=child.read_value_program(regions['actual'],base+source_rva,symbols)
 need('complete-actual-ReadValue-to-RAX-byte-replay',norm(replay)==program)
 replay=child.raw8_program(regions['raw8'],symbols['raw8'],p['readerOffsets'])
 need('complete-actual-raw8-Reader-and-frame-replay',norm(replay)==p.get('raw8'))
 replay=child.callback_program(regions['callbackPrefix'],symbols['callback'],symbols['raw8'])
 need('exact-owned-callback-normal-tail',norm(replay)==p.get('canonicalCallback')and replay.get('physicalFunctionExtentProved')is False)
 return base


def _compile_member(owner,scope,read,pins):
 index=read['memberIndex'];need('same-complete-owned-event',type(index)is int and 0<=index<len(scope.get('events',[]))
  and owner.get('nativeInputs')==scope.get('nativeInputs')==pins and owner.get('sourceScope')==scope
  and owner.get('orderedSourceReads',[])[index]==scope['events'][index]==read
  and read.get('kind')=='constructed:'+child.TYPE and read.get('declaredType')==child.TYPE
  and read.get('mode')=='typed-constructed-value'and read.get('resultAbi')=='rax'and read.get('actualSourceProved')is True
  and read.get('managedBytes')==8 and read.get('concreteTypeKind')==21 and read.get('referenceLaneOffsets')==[]
  and read.get('paddingByteRanges')==[[1,3]])
 actual=scope.get('constructedValueSources',{}).get(str(index),{});native=actual.get('proof',{}).get('nativeSource',{})
 need('own-separate-source-wrapper',actual.get('nativeInputs')==pins and actual.get('typeName')==child.TYPE
  and actual.get('concreteTypeKind')==21 and actual.get('valueCarrier')is True and actual.get('managedBytes')==8
  and actual.get('resultAbi')=='rax-managed-value'and actual.get('actualSourceProved')is True
  and actual.get('referenceLaneOffsets')==[]and actual.get('paddingByteRanges')==[[1,3]]
  and actual.get('sourceTargetRva')==read['sourceTargetRva']
  and actual.get('proof',{}).get('typedRequest')==native.get('proof',{}).get('typedRequest'))
 base=require_source(native,pins,read.get('context',{}),read['sourceTargetRva'])
 setter=owner['setters'][index];layout=setter.get('constructedValueLayout',{});field=setter.get('fieldValueLayout',{});life=owner.get('lifecycle',{})
 need('independent-nominal-field-and-parameter',setter==scope.get('richSetters',[])[index]
  and setter.get('profile')=='inline-coherent-constructed-value-setter'and setter.get('storedBytes')==8
  and setter.get('incomingValueStoredUnchanged')is True and setter.get('nativeInputs')==pins
  and setter.get('targetField')==owner['wrappedType']+'::'+read['fieldName']
  and bytes.fromhex(setter.get('parameterTypeRecordHex',''))[10:12]==bytes((21,128))
  and layout.get('typeName')==field.get('typeName')==child.TYPE and layout.get('concreteTypeKind')==21
  and layout.get('valueCarrier')is True and layout.get('managedBytes')==8 and layout.get('referenceLaneOffsets')==[]
  and layout.get('paddingByteRanges')==[[1,3]]and layout.get('hasValueByteOffset')==0 and layout.get('singleBitsByteOffset')==4
  and layout.get('selectedCarrier',{}).get('definition')==field.get('selectedCarrier',{}).get('definition')
  and layout.get('selectedCarrier',{}).get('classArguments')==field.get('selectedCarrier',{}).get('classArguments'))
 getter=setter.get('getter',{});program=setter.get('program',{});body=program.get('selectedBytes',[])
 need('same-owned-current-coherent-cache',getter.get('baseHolder')==life.get('baseHolder')and getter.get('typedCache')==life.get('typedCache')
  and getter.get('coherentNonNullSamePointerReturn')is True and program.get('wholeInputBitsStoredUnchanged')is True
  and program.get('paddingBitsPreserved')is True and bool(body)and body[0][0]==base+setter['method'][3])
 from scripts.game_data.memorypack.generated_nullable_value_sources import setter_program
 from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
 replay=setter_program([(a,bytes.fromhex(h))for a,h in body],base+setter['method'][3],field=setter['fieldOffset'],
  base_slot=life['baseHolder'][2],cache_slot=life['typedCache'][2],
  path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,setter['codeWindows'],base))
 need('whole-current-named-setter-byte-replay',norm(replay)==program)
 rich=scope.get('richProgram',{});flows=[x for x in rich.get('sources',[])if x.get('memberIndex')==index]
 stores=[x for x in rich.get('fieldStores',[])if x.get('memberIndex')==index]
 need('whole-RAX8-to-named-field',rich.get('completeSelectedNormalProgram')is True and rich.get('selectedProgram')==scope.get('selectedProgram')
  and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='rax')]
  and len(stores)==1 and(stores[0].get('sourceOffset'),stores[0].get('storedBytes'))==(0,8)
  and stores[0]['instruction']in rich.get('actualCalls',[])and stores[0]['instruction']in scope['selectedProgram'])
 at,h=stores[0]['instruction'];raw=bytes.fromhex(h)
 need('actual-own-full-qword-setter-call',len(raw)==5 and raw[0]==232 and at+5+int.from_bytes(raw[1:],'little',signed=True)==setter['method'][3])
 paths=owner.get('programs',[])
 need('all-four-complete-parent-frames',len(paths)==4 and{(p.get('existing'),p.get('wrapperNull'))for p in paths}==
  {(False,False),(True,False),(False,True),(True,True)}and all(p.get('frame',{}).get('entryRspRestored')is True
   and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
 return 'nullable-single-raw8'


def compile_member(owner,scope,read,pins):
 try:return _compile_member(owner,scope,read,pins)
 except(ValueError,KeyError,IndexError,TypeError)as error:
  from scripts.game_data.memorypack.corpus_gate import CensusGateError
  failure=CensusGateError(LABEL+'.field',source=owner.get('wrapperName','unknown')+'::Deserialize',
   expected='Own constructed Nullable<Single> source, raw8/padding/HasValue ABI, complete named setter and all caller frames.',
   actual=dict(fieldName=read.get('fieldName'),memberIndex=read.get('memberIndex'),failedGate=str(error)[:900]))
  failure.diagnostic.update(validator=LABEL,nativeInputs=pins,sourceInstruction=read.get('instruction'))
  failure.args=(json.dumps(failure.diagnostic,ensure_ascii=False),);raise failure from error
