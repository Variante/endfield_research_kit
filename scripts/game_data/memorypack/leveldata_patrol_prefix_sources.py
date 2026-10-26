"""Actual comparison-five string-prefix path and selected ASCII span effects.

The actual path prefix is independently read from its metadata literal. This
owner follows the current jump-table entry and actual two callees. Under the
ready, non-replacement ASCII comparison domain it proves prefix equality,
including both direct and folded character arms, without culture, Unicode or
live string identity claims. Other comparison domains remain independent.
"""
import json
import hashlib
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-prefix-source.v1'

def need(check,condition):
 if not condition:raise ValueError('storyPatrolPrefix.'+check)

def prefix_program(regions,entry,*,case_target,same=False,short=False,equal=True):
 need('finite-prefix-case',all(type(v)is bool for v in(same,short,equal))and not(same and short))
 g=BytesPath(regions,entry);g.take('4053','57','4883ec58','488bda','488bf9','4885d2');g.branch('0f84',False)
 g.take('483bca');g.branch('0f84',same)
 call=None;table=None;classes=[];validator=None
 if same:
  g.take('33d2','418bc8');at=g.at;target=g.relative('e8');validator=dict(instructionVa=at,targetVa=target)
  g.take('b001','4883c458','5f','5b','c3')
 else:
  g.take('837a1000');g.branch('0f84',False)
  g.take('4c89742450','48896c2470','4889b42480000000');imagebase=g.relative('4c8d35')
  g.take('4585c0');g.branch('0f84',False);g.take('4183f805');g.branch('0f87',False)
  g.take('4963c0','418b8c86');table=imagebase+int.from_bytes(g.read(4),'little',signed=True);g.take('4903ce','ffe1');g.at=case_target
  g.take('8b4210','394710');g.branch('7c',short,1)
  if short:g.take('32c0');g.at=g.relative('e9')
  else:
   at=g.at;cell=g.relative('488b0d');classes.append(dict(instructionVa=at,cellVa=cell))
   g.take('8be8','83b9e000000000');g.branch('75',True,1)
   g.take('33f6','4c8bcb','4889742430','448bc5','896c2428','33d2','488bcf','89742420')
   at=g.at;target=g.relative('e8');call=dict(instructionVa=at,targetVa=target)
   g.take('85c0','0f94c0');g.at=g.relative('e9')
  g.take('488bb42480000000','488b6c2470','4c8b742450','4883c458','5f','5b','c3')
 return dict(selectedBytes=g.seen,entry=entry,comparisonArgumentRequired=5,sameString=same,inputShorterThanPrefix=short,
  selectedSpanComparisonZeroRequired=equal,prefixResult=same or(not short and equal),jumpTableVa=table,caseTargetVa=None if same else case_target,
  classUsages=classes,spanCall=call,comparisonValidatorCall=validator,prefixRequiredNonnullAndNonempty=True,
  spanArguments=dict(rcx='incoming input string',edx=0,r8d='prefix length',r9='same prefix string',stack5=0,stack6='prefix length',stack7=0),
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,spanEffectsProved=False)

def span_program(regions,entry):
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','48897c2420','4156','4883ec60',
  '4863f2','498bd9');ready=g.relative('0fb615');g.take('418be8','488bf9','84d2');g.branch('0f84',False)
 g.take('4533f6','0f29742450','0f297c2440','4885ff');g.branch('0f84',False)
 g.take('3b7710');g.branch('0f87',False);g.take('8b4710','2bc6','3be8');g.branch('0f87',False)
 g.take('488d4e0a','448974242c','488d0c4f','896c2428','48894c2420','0f287c2420','84d2');g.branch('0f84',False)
 g.take('4885db');g.branch('0f84',False);g.take('48638c2490000000','3b4b10');g.branch('0f87',False)
 g.take('8b4310','8b942498000000','2bc1','3bd0');g.branch('0f87',False)
 g.take('4883c10a','448974242c','89542428','488d0c4b','48894c2420','0f28742420')
 use=g.at;cls=g.relative('488b0d');g.take('4439b1e0000000');g.branch('74',False,1)
 g.take('4533c0','660f7f742420','488d542420','660f7f7c2430','488d4c2430');site=g.at;target=g.relative('e8')
 g.take('0f287c2440','4c8d5c2460','498b5b10','498b6b18','498b7320','498b7b28','0f28742450','498be3','415e','c3')
 return dict(selectedBytes=g.seen,entry=entry,readyFlagVa=ready,classUsageInstructionVa=use,classCellVa=cls,
  compareCall=dict(instructionVa=site,targetVa=target),sourceStringStartsRequiredZero=True,
  bothSliceLengthsRequiredEqualToPrefixLength=True,validStringBoundsRequired=True,
  slicePointerOffsets=20,sliceLengthOffset=8,sliceLocalHomes=[[32,48],[48,64]],
  returnsActualComparisonEaxUnchanged=True,entryRspRestored=True,allNonvolatilesAndXmm6Xmm7Restored=True,normalReturn=True)

def ascii_program(regions,entry,*,folded=(),mismatch=False):
 need('finite-character-witness',isinstance(folded,(list,tuple))and 0<=len(folded)<=5 and all(type(v)is bool for v in folded)
  and type(mismatch)is bool and(len(folded)==5 or mismatch))
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4156','4157','4883ec50','8b5908','488be9')
 cls=g.relative('488b0d');g.take('4c8bf2','8b7a08','83b9e000000000');g.branch('0f84',False)
 context=g.relative('488b0d');g.take('3bdf','0f4fdf','448bfb','4883793800');g.branch('0f84',False)
 g.take('4883793800','0f104500','0f11442430');g.branch('0f84',False)
 ascii_cls=g.relative('488b0d');g.take('410f1006','488b7c2430','83b9e000000000','0f11442440','488b742440');g.branch('0f84',False)
 flag=(g.relative('803d')+1);g.take('00');g.branch('0f84',False)
 need('same-ascii-class',g.relative('488b0d')==ascii_cls);g.take('83b9e000000000');g.branch('0f84',False)
 need('same-ascii-class-reload',g.relative('488b05')==ascii_cls);g.take('488b88b8000000','803900');g.branch('0f85',False)
 g.take('41b87f000000','85db');head=g.at;arms=[]
 for index,fold in enumerate([*folded,*([True]if mismatch else[]) ]):
  begin=len(g.seen);g.branch('74',False,1);g.take('90','66443907');g.branch('77',False,1)
  g.take('66443906');g.branch('77',False,1);g.take('0fb70f','0fb716','3bca');g.branch('75',fold,1)
  if fold:
   g.take('8d419f','83f819','448d49e0','440f47c9','8d429f','83f819','8d4ae0','0f47ca','443bc9')
   g.branch('74',not(mismatch and index==len(folded)),1)
   if mismatch and index==len(folded):g.take('442bc9','418bc1');g.at=g.relative('eb',1);break
  g.take('b8ffffffff','4883c602','4883c702','03d8');back=g.relative('eb',1);need('same-ascii-forward-loop',back==head);g.at=back
  arms.append(dict(folded=fold,selectedBytes=g.seen[begin:]))
 if not mismatch:
  g.branch('74',True,1);g.take('8b6d08','458b7608','85db');g.branch('0f85',False);g.take('412bee','8bc5')
 g.take('488b5c2470','488b6c2478','488bb42480000000','4883c450','415f','415e','5f','c3')
 return dict(selectedBytes=g.seen,entry=entry,foldedEqualPrefix=list(folded),finalFoldedMismatch=mismatch,
  classCellVa=cls,contextCellVa=context,asciiClassCellVa=ascii_cls,metadataReadyFlagVa=flag,
  selectedRuntimeStaticByteRequiredZero=True,bothSpanLengthsRequired=5,allConsumedCodeUnitsRequiredAscii=True,
  loopEntryVa=head,forwardArms=arms,codeUnitBytes=2,remainingCountStep=-1,pointerStepBytes=2,
  equalResultRequired=not mismatch,returnsZeroIffFoldedPrefixEqual=True,
  opaqueCalls=0,nonframeMemoryWrites=0,entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True)

def fold_proof():
 for a in range(128):
  for b in range(128):
   folded_a=a-32 if 0<=(a-97)&0xffffffff<=25 else a
   folded_b=b-32 if 0<=(b-97)&0xffffffff<=25 else b
   need('complete-ascii-cmov-fold',((a==b)or folded_a==folded_b)==(chr(a).upper()==chr(b).upper()))
 return dict(asciiPairsChecked=128*128,fold='ASCII a..z subtract32; other ASCII unchanged',allAsciiPairsProved=True,
  loopInvariant='At the loop head after k equal comparisons, both pointers advanced2*k and remaining=5-k. Raw-equal or folded-equal arms each advance exactly once; a folded mismatch returns a nonzero signed difference. At5, equal lengths return0.',
  boundedFiveCodeUnitPrefixComparisonProved=True,unicodeOrCultureComparisonProved=False)

def validator_program(regions,entry):
 g=BytesPath(regions,entry);g.take('4883ec28','83f905');g.branch('0f87',False);g.take('4883c428','c3')
 return dict(selectedBytes=g.seen,entry=entry,unsignedArgumentInZeroThroughFiveRequired=True,opaqueCalls=0,
  nonframeMemoryWrites=0,entryRspRestored=True,normalReturn=True)

def _ascii_programs(regions,entry):
 # All equal-arm choices and a mismatch after every possible prior arm choice.
 from itertools import product
 return [ascii_program(regions,entry,folded=list(f),mismatch=False)for f in product((False,True),repeat=5)]+[
  ascii_program(regions,entry,folded=list(f),mismatch=True)for n in range(5)for f in product((False,True),repeat=n)]

def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import leveldata_patrol_hash_sources as parent,pointer_param as pointer
 _publication_gate(image,pins);base=image.pe.image_base;source=parent.derive(image,pins)
 packet=source['proof']['pathSource']['proof']['children']['prefix'];entry=base+packet['entryRva'];body=pointer.owned(image,entry)
 raw=image.pe.bytes_at_va(entry,100);need('actual-indexed-comparison-table',raw[88:92]==bytes.fromhex('418b8c86'))
 table_rva=int.from_bytes(raw[92:96],'little',signed=True);table=image.pe.bytes_at_va(base+table_rva,24)
 target=base+int.from_bytes(table[20:24],'little',signed=True)
 prefixes=[prefix_program(body['regions'],entry,case_target=target,same=a,short=b,equal=c)for a,b,c in
  ((True,False,True),(False,True,False),(False,False,True),(False,False,False))]
 packets={'prefix':dict(entryRva=entry-base,sourceWindows=body['windows'],sourceRegions=[[a,b.hex()]for a,b in body['regions']])}
 for role,call in(('validator',prefixes[0]['comparisonValidatorCall']),('span',prefixes[2]['spanCall'])):
  b=pointer.owned(image,call['targetVa']);packets[role]=dict(entryRva=b['pointer']-base,sourceWindows=b['windows'],sourceRegions=[[a,h.hex()]for a,h in b['regions']])
 regions=lambda p:[(a,bytes.fromhex(h))for a,h in p['sourceRegions']]
 span=span_program(regions(packets['span']),base+packets['span']['entryRva'])
 b=pointer.owned(image,span['compareCall']['targetVa']);packets['ascii']=dict(entryRva=b['pointer']-base,sourceWindows=b['windows'],sourceRegions=[[a,h.hex()]for a,h in b['regions']])
 ascii_programs=_ascii_programs(regions(packets['ascii']),base+packets['ascii']['entryRva'])
 classes={}
 for name,sites in(('prefix',prefixes[2]['classUsages']),('span',[dict(instructionVa=span['classUsageInstructionVa'])])):
  for site in sites:
   u=derive_typed_usage_context(image,site['instructionVa']-base,label='storyPatrolPrefix.'+name);need('actual-ready-class-usage',u.get('tag')==1)
   classes[name]=u
 result=json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-ascii-prefix-source',nativeInputs=pins,
  proof=dict(imageBase=base,hashSource=source,packets=packets,comparisonTable=dict(rva=table_rva,rawHex=table.hex().upper()),
   programs=dict(prefix=prefixes,span=span,ascii=ascii_programs,validator=validator_program(regions(packets['validator']),base+packets['validator']['entryRva'])),
   actualClassUsages=classes,asciiFoldAndLoop=fold_proof()),selectedComparisonFivePrefixSourceProved=True,
  selectedFiveAsciiCodeUnitFoldEffectsProved=True,unicodeOrCultureComparisonProved=False,
  runtimeInvocationObserved=False,liveStringOrContextIdentityObserved=False,playbackProved=False,
  conditions=['Same actual ready class/context and valid disjoint string/span storage; comparison argument5, actual nonnull/nonempty five-code-unit prefix.',
   'For the selected span comparison, both first-five slices contain only ASCII code units and the actual ASCII runtime flag selects the proved loop. Other Unicode/culture paths are ungranted.'])))
 validate(result,pins);_publication_gate(image,pins);return result

def validate(source,pins):
 need('same-source-envelope',source.get('schema')==SCHEMA and source.get('status')=='validated-conditional-ascii-prefix-source'
  and source.get('nativeInputs')==pins and all(source.get(k)is True for k in('selectedComparisonFivePrefixSourceProved','selectedFiveAsciiCodeUnitFoldEffectsProved'))
  and all(source.get(k)is False for k in('unicodeOrCultureComparisonProved','runtimeInvocationObserved','liveStringOrContextIdentityObserved','playbackProved')))
 p=source['proof'];base=p['imageBase'];packets=p['packets'];programs=p['programs']
 need('exact-finite-packet-set',set(packets)==set(programs)=={'prefix','span','ascii','validator'})
 for role,packet in packets.items():
  windows=packet['sourceWindows'];regions=packet['sourceRegions'];need('same-owned-window-set',bool(windows)and len(windows)==len(regions))
  for w,(a,h)in zip(windows,regions):
   raw=bytes.fromhex(h);need('full-owned-byte-authentication',w==dict(startRva=a-base,endRva=a-base+len(raw),sha256=hashlib.sha256(raw).hexdigest().upper()))
 table=p['comparisonTable'];raw=bytes.fromhex(table['rawHex']);need('exact-six-case-table',len(raw)==24)
 case_target=base+int.from_bytes(raw[20:24],'little',signed=True);regions=lambda role:[(a,bytes.fromhex(h))for a,h in packets[role]['sourceRegions']]
 en=lambda role:base+packets[role]['entryRva']
 actual=dict(prefix=[prefix_program(regions('prefix'),en('prefix'),case_target=case_target,same=a,short=b,equal=c)for a,b,c in
  ((True,False,True),(False,True,False),(False,False,True),(False,False,False))],span=span_program(regions('span'),en('span')),
  ascii=_ascii_programs(regions('ascii'),en('ascii')),validator=validator_program(regions('validator'),en('validator')))
 need('every-selected-prefix-span-ascii-program-replays',json.loads(json.dumps(actual))==programs and p['asciiFoldAndLoop']==fold_proof())
 need('actual-comparison-table-and-call-seams',all(row['jumpTableVa']==base+table['rva']for row in actual['prefix']if row['jumpTableVa']is not None)
  and actual['prefix'][0]['comparisonValidatorCall']['targetVa']==en('validator')and actual['prefix'][2]['spanCall']['targetVa']==en('span')
  and actual['span']['compareCall']['targetVa']==en('ascii'))
 parent=p['hashSource'];need('same-native-parent-and-prefix',parent['nativeInputs']==pins and
  parent['proof']['pathSource']['proof']['children']['prefix']['entryRva']==packets['prefix']['entryRva']and
  parent['proof']['pathSource']['proof']['prefixString'].get('value')=='data/')
 for role,site,cell in(('prefix',actual['prefix'][2]['classUsages'][0]['instructionVa'],actual['prefix'][2]['classUsages'][0]['cellVa']),
  ('span',actual['span']['classUsageInstructionVa'],actual['span']['classCellVa'])):
  u=p['actualClassUsages'][role];need('actual-own-ready-class:'+role,u['tag']==1 and u['instructionRva']==site-base and u['usageCellRva']==cell-base)
 return dict(selectedComparisonFivePrefixSourceProved=True,selectedFiveAsciiCodeUnitFoldEffectsProved=True,
  unicodeOrCultureComparisonProved=False,runtimeInvocationObserved=False)
