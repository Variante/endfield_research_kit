"""Own static-out gait dictionary, independently selected nominal callbacks.

The wire subset uses authored header one and nonnegative bounded counts. The
native source only distinguishes FF from non-FF; no native header-one check is
claimed. Entries retain serialized order and duplicates. Runtime provider and
MethodInfo compatibility, fresh null output and normal helper returns remain
conditions, and this component grants no enclosing action or Skill admission.
"""
import hashlib,json

from scripts.game_data.memorypack import skill_gait_dictionary_sources as source
from scripts.game_data.memorypack import skill_gait_dictionary_callbacks as callbacks

SCHEMA='endfield.skill-gait-dictionary-component.v1'
CAPABILITY=source.CAPABILITY
WIRE='gait-single-dictionary-profile'


def need(key,condition):
 if not condition:raise ValueError('skillGaitDictionaryComponent.'+key)


def regions(windows,raw_regions,base,label):
 need(label+'-full-window-bijection',bool(windows)and len(windows)==len(raw_regions)
  and len({a for a,h in raw_regions})==len(raw_regions))
 result=[]
 for at,h in raw_regions:
  raw=bytes.fromhex(h);matches=[w for w in windows if w.get('startRva')==at and w.get('endRva',0)-at==len(raw)]
  need(label+'-exact-window',len(matches)==1 and hashlib.sha256(raw).hexdigest().upper()==matches[0].get('sha256'))
  result.append((base+at,raw))
 return result


def replay_source(actual,pins,base):
 need('own-static-source',actual.get('schema')=='endfield.skill-gait-dictionary-source.v1'
  and actual.get('status')=='validated-conditional-static-out-source'and actual.get('nativeInputs')==pins
  and(actual.get('typeName'),actual.get('keyType'),actual.get('valueType'))==(source.TYPE,source.KEY,'float')
  and actual.get('resultAbi')=='void-byref-reference8'and actual.get('referenceBytes')==8
  and actual.get('actualSourceProved')is True and actual.get('closedPointerEquivalenceProved')is False
  and actual.get('wireGrammarAdmitted')is False and actual.get('wholeOwnerAdmitted')is False)
 p=actual['proof'];raw=regions(p['actualWindows'],p['actualSourceRegions'],base,'static-source')
 symbols={k:base+v for k,v in p['symbolRvas'].items()}
 programs=[source.paths.program(raw,base+actual['sourceTargetRva'],p['readerOffsets'],symbols,count=n)for n in(-1,0,1,2,3)]
 need('whole-static-source-byte-replay',json.loads(json.dumps(programs))==p['programs'])
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 induction=prove_induction(programs[1:],initial='418bef',increment='ffc5',comparison='413bee',counter='ebp',saved_count='R14D',
  max_count=4096,mode_key='newDictionary',backedge_sites=programs[2]['backedgeSites'])
 need('whole-static-source-count-induction',json.loads(json.dumps(induction))==p['induction'])


def compose(pins,actual,single,enum,key_dispatch):
 """Pure exact composition; fresh derive supplies every source independently."""
 callbacks.replay_single(single,pins);registration=single['proof']['registration'];base=registration['pointer']-single['callbackTargetRva']
 replay_source(actual,pins,base);p=actual['proof'];cap=enum.get('capability',{})
 need('own-nominal-enum-callback',enum.get('schema')=='endfield.enum-nominal-callback-sources.v1'
  and enum.get('status')=='validated-conditional-callback-sources'and enum.get('nativeInputs')==pins
  and cap.get('nativeInputs')==pins and cap.get('status')=='validated-conditional-callback'
  and cap.get('typeName')==source.KEY and type(cap.get('typeDefinition'))is int
  and cap.get('wireBytes')==4 and cap.get('callbackSlot')==5 and cap.get('readerByref')is True and cap.get('outputByref')is True
  and cap.get('actualRuntimeSelectionObserved')is False and cap.get('unconditionalCallbackSelectionProved')is False
  and cap.get('parentOrCollectionGrammarAdmitted')is False and len(cap.get('conditions',[]))==6
  and all(isinstance(c,str)and c for c in cap['conditions']))
 need('actual-owned-Single-dispatch',single['sourceTargetRva']==p['symbolRvas']['valueDispatch'])
 dispatch=p['helpers']['keyDispatch'];rows=dispatch['rows']
 calls=[r for r in rows if bytes.fromhex(r['bytes'])[:1]==b'\xe8'];need('actual-key-dispatch-preparation',bool(calls))
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 prepare=control_transfer(calls[0])['target']
 raw_regions=[]
 # Helpers retain every decoded row, not a selected trace or inferred extent.
 for window in dispatch['windows']:
  at=window['startRva'];end=window['endRva'];selected=[r for r in rows if base+at<=int(str(r['va']),16)<base+end]
  need('complete-key-dispatch-decoded-rows',bool(selected))
  cursor=base+at;raw=b''
  for row in selected:
   need('contiguous-key-dispatch-rows',int(str(row['va']),16)==cursor);data=bytes.fromhex(row['bytes']);raw+=data;cursor+=len(data)
  need('complete-key-dispatch-window',cursor==base+end);raw_regions.append([at,raw.hex()])
 raw=regions(dispatch['windows'],raw_regions,base,'key-dispatch')
 checked=callbacks.dispatch_program(raw,base+p['symbolRvas']['keyDispatch'],p['readerOffsets'],
  prepare=prepare,callback=base+cap['callbackTargetRva'],kind='enum')
 need('whole-key-dispatch-byte-replay',json.loads(json.dumps(checked))==key_dispatch)
 context=actual['context'];need('exact-own-static-request',context.get('typedRequest',{}).get('classArguments')==[source.KEY,'float']
  and context['typedRequest'].get('methodArguments')==[]and context['typedRequest'].get('typeName')==source.OWNER
  and context['typedRequest'].get('methodName')=='DeserializeV2')
 return dict(typeName=source.TYPE,keyType=source.KEY,valueType='float',resultAbi='void-byref-reference8',referenceBytes=8,
  staticReaderMethodDefinition=actual['readerMethodDefinition'],staticReaderTargetRva=actual['sourceTargetRva'],
  wholeGrammarAdmitted=True,staticOutReferenceAdmitted=True,ordinaryOriginalReadValueAdmitted=False,
  nullable=True,nullMarker=255,positiveHeader=1,nativePositiveHeaderOneEnforced=False,countLimit=4096,
  countEncoding='signed-int32',minimumCount=0,keyWireBytes=4,valueWireBytes=4,
  keyTypeDefinition=cap['typeDefinition'],keyCallback=cap,singleCallbackTargetRva=single['callbackTargetRva'],
  orderedEntriesPreserved=True,duplicateKeysPreserved=True,numericConversion=False,
  initiallyNullOutputRequired=True,actualRuntimeSelectionObserved=False,
  conditions=cap['conditions']+[single['evidenceBoundary']['conditional'],actual['evidenceBoundary']['conditional'],__doc__])


def derive(image,pins,*,context,source_target,callback_children=None):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.enum_nominal_callback_sources import derive as derive_enum
 from scripts.game_data.memorypack import pointer_param as pointer
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 _publication_gate(image,pins);actual=source.derive(image,pins,context=context,source_target=source_target);base=image.pe.image_base
 if callback_children is None:
  single=callbacks.derive_single(image,pins,call_target=base+actual['proof']['symbolRvas']['valueDispatch'])
  enum=derive_enum(image,pins,type_name=source.KEY)
 else:single,enum=callback_children
 target=base+actual['proof']['symbolRvas']['keyDispatch'];owned=pointer.owned(image,target)
 calls=[r for r in owned['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'];need('actual-key-prepare',bool(calls))
 dispatch=callbacks.dispatch_program(owned['regions'],target,actual['proof']['readerOffsets'],
  prepare=control_transfer(calls[0])['target'],callback=base+enum['capability']['callbackTargetRva'],kind='enum')
 dispatch=json.loads(json.dumps(dispatch));cap=compose(pins,actual,single,enum,dispatch)
 result=dict(schema=SCHEMA,status='validated-conditional-static-out-dictionary',nativeInputs=dict(pins),
  capabilities={CAPABILITY:cap},proof=dict(source=actual,single=single,enum=enum,keyDispatch=dispatch),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Independent own static source, nominal enum and Single callbacks, actual dispatches and bounded counted wire subset.',conditional=__doc__))
 _publication_gate(image,pins);return json.loads(json.dumps(result))
