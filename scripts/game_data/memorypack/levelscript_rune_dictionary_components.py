"""Rune's raw16 entry framing and complete named reference-field transfer.

The projection retains ordered entry bits and padding. It grants no hash-map
contents, key uniqueness, duplicate semantics, live selection or Module root.
"""
import json

from scripts.game_data.memorypack import levelscript_rune_dictionary_sources as source
from scripts.game_data.memorypack import levelscript_rune_dictionary_programs as paths

SCHEMA='endfield.story-rune-dictionary-components.v1'
CAP_SCHEMA='endfield.story-rune-dictionary-capability.v1'
CAPABILITY=source.CAPABILITY
WIRE='story-rune-raw-pair16-dictionary'


def need(key,condition):
 if not condition:raise ValueError('storyRuneDictionary.'+key)


def norm(value):return json.loads(json.dumps(value))


def compose(actual,pins):
 from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 from scripts.game_data.memorypack.generated_called_advance_sources import advance_program
 cap=source.validate_component(actual,pins);p=actual['proof'];base=p['formatterRegistration']['pointer']-cap['sourceTargetRva']
 need('selected-image-base',type(base)is int and base>=1<<32)
 raw={role:regions(p[role]['windows'],[[at-base,h]for at,h in p[role]['regions']],base,'Rune-dictionary-'+role)
  for role in('source','header','pair','rawReader','add')}
 entry=p['formatterRegistration']['pointer'];programs=[paths.dictionary(raw['source'],entry,count=n)for n in(-1,0,1,2,3)]
 induction=prove_induction(programs,initial='33f6',increment='ffc6',comparison='3b742478',counter='esi',saved_count='immutable signed DWORD RSP+120',
  max_count=cap['countLimit'],mode_key='newDictionary',backedge_sites=programs[2]['backedgeSites'])
 need('all-five-source-paths-and-identical-induction',norm(programs)==p['programs']and norm(induction)==p['induction'])
 s={k:base+v for k,v in p['symbolRvas'].items()};offsets=p['readerOffsets']
 need('all-own-header-KV-raw16-and-Add-programs',norm(paths.header(raw['header'],s['header'],offsets))==p['headerProgram']
  and norm(paths.pair(raw['pair'],p['pairRegistration']['pointer']))==p['pairProgram']
  and norm(paths.raw_pair(raw['rawReader'],p['rawReaderRegistration']['pointer'],offsets))==p['rawReaderProgram']
  and norm(paths.add(raw['add'],s['add']))==p['addProgram'])
 advance=p['advanceSource'];ar=regions(advance['codeWindows'],[[at-base,h]for at,h in advance['sourceRegions']],base,'Rune-dictionary-Advance')
 proof=[advance_program(ar,base+advance['targetRva'],offsets,zero=z)for z in(False,True)]
 need('all-four-Reader-updates-and-owned-Advance-tail',advance.get('nativeInputs')==pins and norm(proof)==advance['programs']
  and p['rawReaderProgram']['advanceTargetVa']==base+advance['targetRva'])
 source.require_carrier(p['carrier']);pair=p['closedPairCarrier']
 need('own-constructed-value-pair-not-a-reference-specialization',pair.get('name')==source.PAIR_TYPE
  and bytes.fromhex(pair.get('rawHex',''))[10:12]==bytes((21,128))and pair.get('definition',{}).get('name')==source.PAIR
  and[(r.get('name'),bytes.fromhex(r.get('rawHex',''))[10:12])for r in pair.get('classArguments',[])]==[('ulong',bytes((11,128))),('int',bytes((8,128)))])
 projected=dict(schema=CAP_SCHEMA,name=CAPABILITY,typeName=source.TYPE,headerBytes=4,countLimit=cap['countLimit'],countRange=cap['countRange'],
  nullable=True,pairWireBytes=16,keyByteRange=[0,8],valueByteRange=[8,12],transportedPaddingByteRange=[12,16],
  keyType='ulong',valueType='int',keyRawKind=11,valueRawKind=8,individualKeyValueCallbacksUsed=False,
  rawBitsPreserved=True,paddingBytesPreserved=True,storedEntryFramingAdmitted=True,initiallyNullOutputRequired=True,
  actualTypedFormatterSelectionRequired=True,internalKVMethodInfoCompatibilityRequired=True,
  packableReaderMethodDefinition=cap['packableReaderMethodDefinition'],packableReaderTargetRva=cap['packableReaderTargetRva'],
  hashMapContentsAdmitted=False,duplicateSemanticsAdmitted=False,liveFormatterSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
 return dict(schema=SCHEMA,status='validated-conditional-story-rune-dictionary',nativeInputs=pins,capability=CAPABILITY,
  capabilities={CAPABILITY:projected},proof=actual,parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def validate_component(component,pins):
 need('own-composed-component',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
  and component.get('status')=='validated-conditional-story-rune-dictionary'and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
 fresh=compose(component['proof'],pins)
 need('all-and-only-own-capability',component.get('capability')==CAPABILITY and component.get('capabilities')==fresh['capabilities'])
 return fresh['capabilities'][CAPABILITY]


def bind_member(full,scope,read,pins,usage,component,capability=CAPABILITY):
 cap=validate_component(component,pins);index=read['memberIndex'];actual=component['proof']
 need('only-exact-Rune-dictionary-field',full.get('wrappedType')==source.PARENT and index==2
  and(read.get('fieldName'),read.get('declaredType'),read.get('kind'))==(source.FIELD,source.TYPE,'reference:'+source.TYPE)
  and full.get('schema')=='endfield.generated-concrete-reader-source.v1'and full.get('nativeInputs')==pins
  and full.get('completeSelectedCallerAdmitted')is True and full.get('sourceScope')==scope
  and full['orderedSourceReads'][index]==scope['events'][index]==read and capability==CAPABILITY)
 source.bind_request(pins,usage,read['sourceTargetRva'],actual)
 at,h=read['instruction'];code=bytes.fromhex(h)
 need('own-actual-ReadPackable-E8',len(code)==5 and code[0]==232 and at+5+int.from_bytes(code[1:],'little',signed=True)==cap['packableReaderTargetRva'])
 rich=scope['richProgram'];setter=scope['richSetters'][index];stores=[r for r in rich['fieldStores']if r['memberIndex']==index];flows=[r for r in rich['sources']if r['memberIndex']==index]
 need('whole-new-dictionary-RAX-to-named-field',rich.get('completeSelectedNormalProgram')is True and rich.get('selectedProgram')==scope.get('selectedProgram')
  and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='rax')]
  and len(stores)==1 and(stores[0].get('sourceOffset'),stores[0].get('storedBytes'))==(0,8)
  and stores[0]['instruction']in scope['selectedProgram']and full['setters'][index]==setter and setter.get('storedBytes')==8
  and setter.get('incomingValueStoredUnchanged')is True and setter.get('targetField')==source.PARENT+'::'+source.FIELD)
 at,h=stores[0]['instruction'];code=bytes.fromhex(h)
 need('actual-whole-named-setter-call',len(code)==5 and code[0]in(232,233)and at+5+int.from_bytes(code[1:],'little',signed=True)==setter['method'][3])
 programs=full['programs'];need('all-four-complete-parent-frames',len(programs)==4 and{(p.get('existing'),p.get('wrapperNull'))for p in programs}=={(n,f)for n in(False,True)for f in(False,True)}
  and all(p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in programs))
 return dict(fieldName=source.FIELD,typeName=source.TYPE,capability=CAPABILITY,readerMethodDefinition=cap['packableReaderMethodDefinition'],
  sourceTargetRva=cap['packableReaderTargetRva'],pairWireBytes=16,allFourParentFramesProved=True,hashMapContentsAdmitted=False)
