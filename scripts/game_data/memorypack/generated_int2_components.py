"""Pure exact Int2 source/field compiler; nominal and wire proofs stay distinct."""
import hashlib
import json
from scripts.game_data.memorypack import leveldata_int2_read_sources as child
from scripts.game_data.memorypack.generated_int2_member_sources import check_layout,validate_event

LABEL='generatedInt2Components'


def need(key,condition):
 if not condition:raise ValueError(LABEL+'.'+key)


def norm(value):return json.loads(json.dumps(value))


def require_source(proof,context,source_target,*,base,pins):
 """Rebuild the actual qword source from every authenticated owned region."""
 need('same-current-native-inputs',proof.get('nativeInputs')==pins)
 bound=child.bind(context,source_target,proof,base=base)
 p=proof.get('proof',{});regions=p.get('actualSourceRegions',[]);windows=p.get('actualWindows',[])
 need('all-complete-source-regions',bool(windows)and len(regions)==len(windows)
  and len({at for at,h in regions})==len(regions))
 for at,h in regions:
  raw=bytes.fromhex(h);matches=[w for w in windows if w.get('startRva')==at and w.get('endRva',0)-at==len(raw)]
  need('exact-owned-source-window',type(at)is int and at>=0 and len(matches)==1
   and hashlib.sha256(raw).hexdigest().upper()==matches[0].get('sha256'))
 actual=child.program([(base+at,bytes.fromhex(h))for at,h in regions],source_target,p.get('readerOffsets',{}))
 need('complete-actual-source-byte-replay',norm(actual)==p.get('actualProgram'))
 request=p.get('typedRequest',{})
 need('same-actual-typed-request',request.get('tag')==6
  and(request.get('typeName'),request.get('methodName'),request.get('classArguments'),request.get('methodArguments'))==
      ('MemoryPack.MemoryPackReader','ReadUnmanaged',[],[child.TYPE])
  and request.get('methodSpec')==context.get('methodSpec')and request.get('instructionRva')==context.get('instructionRva')
  and request.get('instructionHex')==context.get('instructionHex'))
 return bound


def _compile_member(owner,scope,read,pins):
 index=read['memberIndex'];need('same-current-owned-event',type(index)is int and 0<=index<len(scope.get('events',[]))
  and owner.get('nativeInputs')==scope.get('nativeInputs')==pins and owner.get('sourceScope')==scope
  and owner.get('orderedSourceReads',[])[index]==scope['events'][index]==read)
 setter=owner['setters'][index];layout=validate_event(read,setter);value=scope.get('valueTypeSources',{}).get(str(index),{})
 typed=value.get('typedSource',{});actual=typed.get('proof',{}).get('actualProgram',{});selected=scope.get('selectedProgram',[])
 need('separate-own-nominal-source-and-wire',value.get('typeName')==child.TYPE and value.get('layout')==layout
  and value.get('actualSourceProved')is True and value.get('wireBytes')==8
  and value.get('resultAbi')=='register-value-to-owned-field'and value.get('sourceProgram')==actual
  and dict(typed.get('proof',{}).get('nominalLayout',{}),typeDefinition=typed.get('typeDefinition'))==layout)
 need('actual-source-entry-base',bool(actual.get('selectedBytes'))and type(typed.get('targetRva'))is int)
 base=actual['selectedBytes'][0][0]-typed['targetRva']
 need('literal-source-base',type(base)is int and base>=0)
 require_source(typed,read.get('context',{}),base+read['sourceTargetRva'],base=base,pins=pins)
 rich=scope.get('richProgram',{});flows=[x for x in rich.get('sources',[])if x.get('memberIndex')==index]
 stores=[x for x in rich.get('fieldStores',[])if x.get('memberIndex')==index]
 need('whole-register-source-to-field',rich.get('completeSelectedNormalProgram')is True and rich.get('selectedProgram')==selected
  and len(flows)==1 and flows[0]==dict(memberIndex=index,instruction=read['instruction'],resultAbi='rax')
  and len(stores)==1 and stores[0].get('sourceOffset')==0 and stores[0].get('storedBytes')==8
  and stores[0].get('instruction')in rich.get('actualCalls',[])and stores[0]['instruction']in selected
  and setter==scope.get('richSetters',[])[index]and setter.get('incomingValueStoredUnchanged')is True
  and setter.get('targetField')==owner['wrappedType']+'::'+read['fieldName'])
 at,h=stores[0]['instruction'];raw=bytes.fromhex(h)
 need('actual-whole-value-named-setter-call',len(raw)==5 and raw[0]==232
  and at+5+int.from_bytes(raw[1:],'little',signed=True)==setter['method'][3])
 need('owned-direct-setter-whole-program',setter.get('profile')=='direct-base-holder-setter'
  and setter.get('getter')is None and setter['program'].get('mode')=='qword-return'
  and setter['program'].get('completeOriginalProgram')is True
  and setter['program'].get('normalIncomingValueStoredUnchanged')is True
  and setter['program'].get('ordinaryFrameRestored')is True)
 rows=setter.get('ordinarySourceRows',[])
 need('complete-actual-named-setter-source',bool(rows))
 regions=setter.get('ordinarySourceRegions',[]);windows=setter.get('codeWindows',[])
 need('all-complete-named-setter-regions',bool(windows)and len(regions)==len(windows)
  and len({at for at,h in regions})==len(regions))
 owned={}
 for at,h in regions:
  raw=bytes.fromhex(h);matches=[w for w in windows if base+w.get('startRva',-base)==at and w.get('endRva',0)-w.get('startRva',0)==len(raw)]
  need('exact-named-setter-window-bytes',len(matches)==1 and hashlib.sha256(raw).hexdigest().upper()==matches[0].get('sha256'))
  for offset,byte in enumerate(raw):
   need('disjoint-named-setter-regions',at+offset not in owned);owned[at+offset]=byte
 decoded={}
 for row in rows:
  at=int(row['va'],16);raw=bytes.fromhex(row['bytes'])
  for offset,byte in enumerate(raw):
   need('same-complete-setter-decoded-bytes',at+offset not in decoded and owned.get(at+offset)==byte);decoded[at+offset]=byte
 need('every-named-setter-byte-decoded',decoded==owned)
 from scripts.game_data.memorypack.generated_member_sources import base_setter_program
 replay=base_setter_program(rows,holder=setter['program']['holderOffset'],field=setter['fieldOffset'],mode='qword-return',barrier=0)
 need('exact-replayed-whole-named-setter',norm(replay)==setter['program'])
 paths=owner.get('programs',[])
 need('all-four-complete-parent-frames',len(paths)==4 and{(p.get('existing'),p.get('wrapperNull'))for p in paths}==
  {(False,False),(True,False),(False,True),(True,True)}and all(p.get('frame',{}).get('entryRspRestored')is True
   and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
 return 'unity-vector2-int-raw8'


def compile_member(owner,scope,read,pins):
 try:return _compile_member(owner,scope,read,pins)
 except(ValueError,KeyError,IndexError,TypeError)as error:
  from scripts.game_data.memorypack.corpus_gate import CensusGateError
  failure=CensusGateError(LABEL+'.field',source=owner.get('wrapperName','unknown')+'::Deserialize',
   expected='Own two-Int32 layout, complete current qword source/Reader updates, exact named setter and full parent frames.',
   actual=dict(fieldName=read.get('fieldName'),memberIndex=read.get('memberIndex'),failedGate=str(error)[:700]))
  failure.diagnostic.update(validator=LABEL,nativeInputs=pins,sourceInstruction=read.get('instruction'))
  failure.args=(json.dumps(failure.diagnostic,ensure_ascii=False),);raise failure from error
