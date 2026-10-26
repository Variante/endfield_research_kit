"""Pure raw Bounds36 source/local/named-field binding, without wrapper aliases.

Fresh native owners supply the actual raw36 source and complete generated
caller. Canonical Bounds MC3/default/list capabilities have no role here.
All36 raw bits must cross disjoint hidden/argument locals and the exact own
setter, with every positive parent frame and all four parent returns proved.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import leveldata_tracking_raw_sources as raw_owner
from scripts.game_data.memorypack import leveldata_tracking_components as profiles
from scripts.game_data.memorypack.leveldata_tracking_value_sources import BOUNDS,SPECS


def need(check,condition):
 if not condition:raise ValueError('storyTrackingRawComponents.'+check)


def same(left,right):
 encode=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
 return encode(left)==encode(right)


def transfer_program(regions,entry,*,hidden_local,argument_local,setter,path_factory=None):
 """Actual RSI-wrapper, disjoint RSP hidden36/copy36, own setter E8 only."""
 need('literal-disjoint-small-stack-homes',type(hidden_local)is int and type(argument_local)is int
  and 32<=hidden_local<=95 and 32<=argument_local<=95 and argument_local%16==0
  and(hidden_local+36<=argument_local or argument_local+36<=hidden_local))
 need('callable-only-owned-path',path_factory is None or callable(path_factory))
 g=(BytesPath if path_factory is None else path_factory)(regions,entry);b=lambda n:bytes((n,)).hex()
 g.take('4885f6');g.branch('0f84',False)
 g.take('0f104424'+b(hidden_local),'8b4424'+b(hidden_local+32),'4533c0','0f104c24'+b(hidden_local+16),
  '488d5424'+b(argument_local),'488bce','0f294424'+b(argument_local),
  '0f294c24'+b(argument_local+16),'894424'+b(argument_local+32))
 site=g.at;g.call(setter)
 return dict(selectedBytes=g.seen,typeName=BOUNDS,managedBytes=36,hiddenLocal=[hidden_local,hidden_local+36],
  argumentLocal=[argument_local,argument_local+36],copiedSlices=[[0,16],[16,16],[32,4]],
  sourceRegisters=['xmm0','xmm1','rax'],wrapperRegister='rsi',setterReceiver='same wrapper RCX',
  setterValuePointer='same copied argument RDX',setterMethodInfoZero=True,setterInstructionVa=site,
  setterTargetVa=setter,completeBitsTransferredUnchanged=True,parentFrameRequired=True,
  nullExitIndependentSourceRequired=True,canonicalWrapperUsed=False,childGrammarAdmitted=False)


def _compile_member(source,scope,read,pins):
 from scripts.game_data.memorypack.generated_outer_value_field_sources import setter_program,validate_event
 index=read.get('memberIndex');need('literal-member-index',type(index)is int and 0<=index<len(source.get('orderedSourceReads',[])))
 need('complete-current-four-path-caller',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
  and source.get('nativeInputs')==scope.get('nativeInputs')==pins and source.get('sourceScope')==scope
  and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
  and source.get('wholeOwnerAdmitted')is False and scope.get('sourceScopeAdmitted')is True
  and same(source['orderedSourceReads'][index],read)and same(scope.get('events',[])[index],read)
  and read.get('kind')=='value36:'+BOUNDS and read.get('declaredType')==BOUNDS
  and read.get('mode')=='typed-hidden-value'and read.get('resultAbi')=='hidden-local'
  and type(read.get('wireBytes'))is int and read['wireBytes']==36 and read.get('actualSourceProved')is True)
 paths=source.get('programs',[])
 need('four-whole-parent-return-frames',len(paths)==4
  and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool
   and p.get('frame',{}).get('entryRspRestored')is True
   and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
  and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})
 positive=[p for p in paths if p['wrapperNull']is False];rich=scope.get('richProgram',{})
 need('same-complete-rich-native-flow',rich.get('completeSelectedNormalProgram')is True
  and same(rich.get('selectedProgram'),scope.get('selectedProgram')))
 value=scope.get('valueTypeSources',{}).get(str(index),{});actual=value.get('typedSource',{});layout=value.get('layout',{})
 base=raw_owner.verify(actual,pins);own=actual['proof']
 need('exact-own-raw36-layout-and-program',value.get('typeName')==BOUNDS and value.get('actualSourceProved')is True
  and type(value.get('wireBytes'))is int and value['wireBytes']==36 and value.get('resultAbi')=='hidden-local-to-owned-field'
  and same(layout,own.get('nominalLayout'))and layout.get('fields')==[list(row)for row in SPECS[BOUNDS]['fields']]
  and layout.get('managedBytes')==36 and layout.get('referenceLaneOffsets')==layout.get('paddingByteRanges')==[]
  and same(value.get('sourceProgram'),own.get('program'))and same(read.get('nominalHiddenSource'),actual)
  and read.get('sourceTargetRva')==actual['sourceTargetRva']and read.get('sourceContextMode')is None)
 profiles.bind_raw(read.get('context',{}),base+actual['sourceTargetRva'],actual,pins,base=base)
 selected=scope.get('selectedProgram',[]);owned={at+i:b for at,h in selected for i,b in enumerate(bytes.fromhex(h))}
 def instruction(row):
  need('literal-owned-caller-instruction',isinstance(row,(list,tuple))and len(row)==2 and type(row[0])is int)
  at,h=row;raw=bytes.fromhex(h);need('same-caller-owned-bytes',bool(raw)and all(owned.get(at+i)==b for i,b in enumerate(raw)));return at,raw
 site,call=instruction(read['instruction']);context=read['context'];instruction([context['instructionRva'],context['instructionHex']])
 need('actual-R8-load-and-source-E8',context['instructionRva']<site and bytes.fromhex(context['instructionHex'])[:3]==bytes.fromhex('4c8b05')
  and len(call)==5 and call[0]==232 and site+5+int.from_bytes(call[1:],'little',signed=True)==actual['sourceTargetRva'])
 hidden=[row for row in rich.get('hiddenSourceLocals',[])if row.get('memberIndex')==index]
 copies=[row for row in rich.get('sourceLocalCopies',[])if row.get('memberIndex')==index]
 frame_bytes=scope.get('headerProof',{}).get('nullFrameBytes')
 need('same-whole-hidden36-and-three-argument-slices',len(hidden)==1 and type(hidden[0].get('displacement'))is int
  and type(hidden[0].get('bytes'))is int and hidden[0]['bytes']==36 and same(hidden[0].get('sourceInstruction'),read['instruction'])
  and hidden[0].get('nominalTypeName')==BOUNDS and hidden[0].get('nominalTypeDefinition')==layout['typeDefinition']
  and len(copies)==3 and sorted((row.get('sourceOffset'),row.get('bytes'))for row in copies)==[(0,16),(16,16),(32,4)]
  and all(type(row.get('displacement'))is int and type(row.get('sourceOffset'))is int and type(row.get('bytes'))is int
   and row.get('nominalTypeName')==BOUNDS
   and row.get('nominalTypeDefinition')==layout['typeDefinition']for row in copies))
 ordered=sorted(copies,key=lambda row:row['sourceOffset']);hidden_at=hidden[0]['displacement'];argument_at=ordered[0]['displacement']
 need('whole-disjoint-owned-hidden-and-argument-homes',type(frame_bytes)is int and frame_bytes>=max(hidden_at,argument_at)+36
  and all(row['displacement']==argument_at+row['sourceOffset']for row in ordered)
  and all(any(type(at)is int and type(width)is int and(at,width)==(hidden_at-frame_bytes,36)
   for at,width in p['frame'].get('hiddenSourceLocalHomes',[]))for p in positive)
  and all(all(any(type(at)is int and type(width)is int and(at,width)==(row['displacement']-frame_bytes,row['bytes'])
   for at,width in p['frame'].get('copiedSourceLocalHomes',[]))for row in ordered)for p in positive))
 setter=source.get('setters',[])[index];validate_event(read,setter);holder=setter.get('directHolder',{})
 lifecycle=source.get('lifecycle',{})
 need('same-exact-named-direct-holder-setter',same(setter,scope.get('richSetters',[])[index])
  and setter.get('profile')=='direct-base-holder-setter'and setter.get('sourceProfile')=='direct-named-outer-raw-value-setter'
  and same(setter.get('nominalValueLayout'),layout)and setter.get('incomingValueStoredUnchanged')is True
  and setter.get('targetField')==source['wrappedType']+'::'+read['fieldName']
  and setter['method'][1]==source['wrapperName']and setter['member']['name']==read['fieldName']
  and setter['member']['declaredType']==BOUNDS and setter['member']['methodIndex']==setter['method'][0]
  and type(setter['method'][0])is int and type(setter['method'][3])is int
  and lifecycle.get('directHolderMode')is True and lifecycle.get('typedCache')is None
  and same(lifecycle.get('baseHolder'),holder.get('field'))
  and type(holder.get('ownerTypeDefinition'))is int and holder['ownerTypeDefinition']==lifecycle.get('typeDefinition')
  and holder.get('field')==[source['wrapperName'],source['wrappedType'],16]
  and holder.get('inheritedFieldAliasUsed')is False and holder.get('openGenericOffsetUsed')is False
  and setter.get('getter')is None and setter.get('childGrammarAdmitted')is False and setter.get('factoryAdmitted')is False)
 windows=setter.get('codeWindows',[]);regions=setter.get('ordinarySourceRegions',[])
 rr=raw_owner._owned_regions([(base+at,h)for at,h in regions],windows,base=base,label='tracking-named-setter')
 replay=setter_program(rr,base+setter['method'][3],type_name=BOUNDS,field=setter['fieldOffset'])
 need('whole-named-setter-copy-replayed',same(replay,setter.get('program')))
 from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
 transfer=transfer_program([(base+at,bytes.fromhex(h))for at,h in selected],base+site+5,
  hidden_local=hidden_at,argument_local=argument_at,setter=base+setter['method'][3],
  path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,scope.get('codeWindows',[]),base))
 stores=[row for row in rich.get('fieldStores',[])if row.get('memberIndex')==index]
 sources=[row for row in rich.get('sources',[])if row.get('memberIndex')==index]
 need('one-whole36-owned-setter-call',len(stores)==len(sources)==1 and sources[0].get('resultAbi')=='hidden-local'
  and same(sources[0].get('instruction'),read['instruction'])and type(stores[0].get('storedBytes'))is int
  and stores[0]['storedBytes']==36 and type(stores[0].get('sourceOffset'))is int and stores[0]['sourceOffset']==0
  and stores[0]['instruction'][0]+base==transfer['setterInstructionVa'])
 instruction(stores[0]['instruction'])
 for row,expected in zip(ordered,('xmm0','xmm1','rax'),strict=True):
  at,_=instruction(row['storeInstruction']);need('owned-argument-copy-between-source-and-setter',site<at<stores[0]['instruction'][0]and row.get('sourceRegister')==expected)
 return 'tracking-bounds-raw36'


def compile_member(source,scope,read,pins):
 try:return _compile_member(source,scope,read,pins)
 except(ValueError,KeyError,IndexError,TypeError)as error:
  from scripts.game_data.memorypack.corpus_gate import CensusGateError
  failure=CensusGateError('storyTrackingRawComponents.field',source=source.get('wrapperName','unknown')+'::Deserialize',
   expected='Exact own raw36 source/R8/E8, disjoint hidden/argument36, all copied bits/named setter and four complete frames.',
   actual=dict(wrapperName=source.get('wrapperName'),fieldName=read.get('fieldName'),memberIndex=read.get('memberIndex'),failedGate=str(error)[:1000]))
  failure.diagnostic.update(validator='storyTrackingRawComponents',nativeInputs=pins,sourceInstruction=read.get('instruction'))
  failure.args=(json.dumps(failure.diagnostic,ensure_ascii=False),);raise failure from error
