"""Pure replay of the independent direct raw44 child; parent transfer is separate.

The five-member wrapper, its default output and any list formatter supply no
bytes or capabilities to this source check. Fresh selected-image derivation is
still required before an enclosing native owner may use the returned identity.
"""
import json

from scripts.game_data.memorypack import leveldata_trigger_shape_raw_sources as source


def need(check,condition):
 if not condition:raise ValueError('storyTriggerShapeRawComponents.'+check)


def same(left,right):
 encode=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
 return encode(left)==encode(right)


def transfer_program(regions,entry,*,hidden_rbp,argument_rbp,setter,path_factory=None):
 """Selected MissionArea RBP raw44-to-argument copy and exact named E8."""
 from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
 need('literal-bounded-disjoint-RBP-homes',type(hidden_rbp)is int and type(argument_rbp)is int
  and -128<=hidden_rbp<=87 and -128<=argument_rbp<=87
  and(hidden_rbp+44<=argument_rbp or argument_rbp+44<=hidden_rbp)
  and type(setter)is int and setter>0)
 need('callable-only-owned-path',path_factory is None or callable(path_factory))
 g=(BytesPath if path_factory is None else path_factory)(regions,entry)
 b=lambda offset:(offset&255).to_bytes(1,'little').hex()
 g.take('4885f6');g.branch('0f84',False)
 g.take('0f1045'+b(hidden_rbp),'8b45'+b(hidden_rbp+40),'4533c0','0f104d'+b(hidden_rbp+16),
  '488d55'+b(argument_rbp),'488bce','0f2945'+b(argument_rbp),'f20f1045'+b(hidden_rbp+32),
  'f20f1145'+b(argument_rbp+32),'0f294d'+b(argument_rbp+16),'8945'+b(argument_rbp+40))
 site=g.at;g.call(setter)
 return dict(selectedBytes=g.seen,typeName=source.TYPE,managedBytes=44,frameRegister='rbp',
  hiddenRbpRange=[hidden_rbp,hidden_rbp+44],argumentRbpRange=[argument_rbp,argument_rbp+44],
  copiedSlices=[[0,16],[16,16],[32,8],[40,4]],sourceRegisters=['xmm0','xmm1','xmm0','rax'],
  setterInstructionVa=site,setterTargetVa=setter,setterReceiver='unchanged wrapper rsi in rcx',
  setterValuePointer='whole disjoint argument44 in rdx',setterMethodInfoZero=True,
  completeBitsTransferredUnchanged=True,parentFrameRequired=True,nullExitIndependentSourceRequired=True,
  canonicalWrapperUsed=False,childGrammarAdmitted=False,parentFieldAdmitted=False)


def verify_source(component,pins):
 from scripts.game_data.memorypack.generated_called_advance_sources import advance_program
 from scripts.game_data.memorypack.leveldata_tracking_raw_sources import _owned_regions,bind_call
 need('same-exact-direct-raw44-child',component.get('schema')=='endfield.story-trigger-shape-raw44.v1'
  and component.get('status')=='validated-conditional-trigger-shape-raw44'and component.get('nativeInputs')==pins
  and component.get('typeName')==source.TYPE and component.get('capability')==source.CAP
  and all(type(component.get(k))is int and component[k]==44 for k in('wireBytes','managedBytes'))
  and component.get('resultAbi')=='hidden-local'and component.get('contextRegister')=='r8'
  and component.get('actualSourceProved')is True and component.get('actualCallbackSelectionRequired')is False
  and component.get('referenceLaneOffsets')==component.get('paddingByteRanges')==[]
  and all(component.get(k)is False for k in('objectHeaderRead','canonicalWrapperUsed','parentFieldAdmitted','wholeOwnerAdmitted'))
  and type(component.get('sourceTargetRva'))is int and component['sourceTargetRva']>0)
 proof=component.get('proof',{});program=proof.get('actualProgram',{});selected=program.get('selectedBytes',[])
 need('literal-actual-source-entry',bool(selected)and type(selected[0][0])is int)
 base=selected[0][0]-component['sourceTargetRva'];offsets=proof['readerOffsets']
 regions=_owned_regions(proof['actualSourceRegions'],proof['actualWindows'],base=base,label='TriggerShape-raw44')
 replay=source.program(regions,base+component['sourceTargetRva'],offsets)
 need('complete-owned-raw44-program',same(replay,program))
 usage=proof['typedRequest'];spec=usage.get('methodSpec',[])
 argument=bytes.fromhex(proof.get('argumentRawHex',''));returned=bytes.fromhex(proof.get('returnRawHex',''))
 container=proof.get('genericContainer',[]);parameter=proof.get('reciprocalParameter',{})
 need('exact-closed-R8-nominal-MethodSpec',
  (usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
   (6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],[source.TYPE])
  and isinstance(spec,(list,tuple))and len(spec)==3 and all(type(n)is int for n in spec)
  and spec[0]==component.get('readerMethodDefinition')and spec[1]==-1 and spec[2]>=0
  and len(argument)==16 and argument[10:12]==bytes((17,128))
  and len(container)==4 and all(type(n)is int for n in container)and list(container[:3])==[spec[0],1,1]
  and parameter.get('methodIndex')==spec[0]and type(parameter.get('ordinal'))is int and parameter['ordinal']==0
  and len(returned)==16 and returned[10:12]==bytes((30,0))and int.from_bytes(returned[:8],'little')==container[3]
  and bytes.fromhex(usage.get('instructionHex',''))[:3]==bytes.fromhex('4c8b05'))
 need('exact-independent-physical-fields',same(proof.get('fields'),list(source.FIELDS))
  and proof.get('enumBacking')==[source.ENUM,component.get('enumBacking'),16]
  and component.get('enumType')==source.ENUM and component.get('enumBacking')in('int','uint')
  and proof.get('vectorFields')==[[source.VECTOR,'float',16+4*i]for i in range(3)])
 caller=bind_call(usage,proof['actualCaller']['sourceInstruction'],source_target=base+component['sourceTargetRva'],base=base)
 need('exact-own-actual-E8',same(caller,proof['actualCaller']))
 advance=proof['advanceSource']
 need('same-owned-Advance-four-Reader-updates',advance.get('nativeInputs')==pins
  and type(advance.get('targetRva'))is int and base+advance['targetRva']==replay['advanceTargetVa']
  and advance.get('readerOffsets')==offsets and advance.get('registeredMethodIdentityClaimed')is False
  and all(advance.get(k)is True for k in('completeAdvanceProgramProved','allFourReaderUpdatesProved','entryRspRestored',
   'allNonvolatilesRestored','zeroCountReturnsWithoutMutation')))
 regions=_owned_regions(advance['sourceRegions'],advance['codeWindows'],base=base,label='TriggerShape-Advance')
 programs=[advance_program(regions,replay['advanceTargetVa'],offsets,zero=zero)for zero in(False,True)]
 need('both-complete-Advance-paths',same(programs,advance.get('programs')))
 return base


def _compile_member(owner,scope,read,pins):
 from scripts.game_data.memorypack.generated_outer_value_field_sources import setter_program,validate_event
 from scripts.game_data.memorypack.leveldata_tracking_raw_sources import _owned_regions
 from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
 index=read.get('memberIndex')
 need('finite-own-MissionArea-shape',type(index)is int and index==3
  and owner.get('wrappedType')=='Beyond.Gameplay.MissionAreaData'
  and owner.get('wrapperName')=='Beyond.MemoryPack.Beyond_Gameplay_MissionAreaDataForMemoryPack'
  and read.get('fieldName')=='shape'and read.get('declaredType')==source.TYPE)
 need('complete-current-four-path-caller',owner.get('schema')=='endfield.generated-concrete-reader-source.v1'
  and owner.get('nativeInputs')==scope.get('nativeInputs')==pins and same(owner.get('sourceScope'),scope)
  and owner.get('completeSelectedCallerAdmitted')is True and owner.get('childGrammarAdmitted')is False
  and owner.get('wholeOwnerAdmitted')is False and scope.get('sourceScopeAdmitted')is True
  and same(owner['orderedSourceReads'][index],read)and same(scope['events'][index],read)
  and read.get('kind')=='value44:'+source.TYPE and read.get('mode')=='typed-hidden-value'
  and read.get('resultAbi')=='hidden-local'and read.get('actualSourceProved')is True
  and type(read.get('wireBytes'))is int and read['wireBytes']==44)
 paths=owner.get('programs',[])
 need('four-whole-parent-return-frames',len(paths)==4 and all(type(p.get('existing'))is bool
  and type(p.get('wrapperNull'))is bool and p.get('frame',{}).get('entryRspRestored')is True
  and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
  and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})
 rich=scope.get('richProgram',{});selected=scope.get('selectedProgram',[])
 need('same-complete-rich-native-flow',rich.get('completeSelectedNormalProgram')is True
  and same(rich.get('selectedProgram'),selected))
 value=scope.get('valueTypeSources',{}).get(str(index),{});actual=value.get('typedSource',{});layout=value.get('layout',{})
 base=verify_source(actual,pins);proof=actual['proof'];context=read.get('context',{});request=proof['typedRequest']
 need('same-independent-raw44-source-and-layout',value.get('typeName')==source.TYPE
  and value.get('actualSourceProved')is True and type(value.get('wireBytes'))is int and value['wireBytes']==44
  and value.get('resultAbi')=='hidden-local-to-owned-field'and same(value.get('sourceProgram'),proof['actualProgram'])
  and same(read.get('nominalHiddenSource'),actual)and layout.get('typeName')==source.TYPE
  and type(layout.get('typeDefinition'))is int and layout['typeDefinition']>=0
  and int.from_bytes(bytes.fromhex(proof['argumentRawHex'])[:8],'little')==layout['typeDefinition']
  and type(layout.get('managedBytes'))is int and layout['managedBytes']==44
  and layout.get('boxedBytes')==60 and same(layout.get('fields'),list(source.FIELDS))
  and same(layout.get('vectorFields'),proof['vectorFields'])and same(layout.get('enumBacking'),proof['enumBacking'])
  and layout.get('referenceLaneOffsets')==layout.get('paddingByteRanges')==[]
  and layout.get('wireGrammarAdmitted')is False and layout.get('readerSourceAdmitted')is False
  and layout.get('parentFieldAdmitted')is False and read.get('sourceTargetRva')==actual['sourceTargetRva'])
 need('same-exact-actual-R8-request',context.get('register')=='r8'and context.get('typeKind')==17
  and context.get('fullTypeName')==source.TYPE and context.get('typeDefinition')==layout['typeDefinition']
  and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadUnmanaged'
  and all(same(context.get(k),request.get(k))for k in('instructionRva','instructionHex','methodSpec','methodSpecIndex','usageRawHex'))
  and context.get('argumentRawHex')==proof['argumentRawHex'])
 owned={}
 prologue=scope.get('headerProof',{}).get('prologue',[])
 need('same-actual-header-prologue-on-all-four-paths',bool(prologue)
  and all(same(p.get('selectedProgram',[])[:len(prologue)],prologue)for p in paths))
 for at,encoded in prologue+selected:
  need('literal-selected-parent-row',type(at)is int and type(encoded)is str)
  for offset,byte in enumerate(bytes.fromhex(encoded)):
   need('noncontradictory-selected-parent-bytes',at+offset not in owned or owned[at+offset]==byte)
   owned[at+offset]=byte
 def instruction(row):
  need('literal-owned-caller-instruction',isinstance(row,(list,tuple))and len(row)==2 and type(row[0])is int)
  at,encoded=row;raw=bytes.fromhex(encoded)
  need('same-caller-owned-bytes',bool(raw)and all(owned.get(at+i)==byte for i,byte in enumerate(raw)));return at,raw
 site,call=instruction(read['instruction']);instruction([context['instructionRva'],context['instructionHex']])
 need('actual-R8-load-and-source-E8',context['instructionRva']<site
  and bytes.fromhex(context['instructionHex'])[:3]==bytes.fromhex('4c8b05')and len(call)==5 and call[0]==232
  and site+5+int.from_bytes(call[1:],'little',signed=True)==actual['sourceTargetRva']
  and same(proof['actualCaller']['sourceInstruction'],read['instruction']))
 hidden=[r for r in rich.get('hiddenSourceLocals',[])if r.get('memberIndex')==index]
 copies=[r for r in rich.get('sourceLocalCopies',[])if r.get('memberIndex')==index]
 need('same-whole-hidden44-and-four-argument-slices',len(hidden)==1
  and type(hidden[0].get('displacement'))is int and type(hidden[0].get('bytes'))is int and hidden[0]['bytes']==44
  and same(hidden[0].get('sourceInstruction'),read['instruction'])and hidden[0].get('nominalTypeName')==source.TYPE
  and hidden[0].get('nominalTypeDefinition')==layout['typeDefinition']and len(copies)==4
  and all(type(r.get('displacement'))is int and type(r.get('sourceOffset'))is int and type(r.get('bytes'))is int
   and r.get('nominalTypeName')==source.TYPE and r.get('nominalTypeDefinition')==layout['typeDefinition']for r in copies)
  and sorted((r['sourceOffset'],r['bytes'])for r in copies)==[(0,16),(16,16),(32,8),(40,4)])
 ordered=sorted(copies,key=lambda r:r['sourceOffset']);hidden_at=hidden[0]['displacement'];argument_at=ordered[0]['displacement']
 frame_bytes=scope.get('headerProof',{}).get('nullFrameBytes');positive=[p for p in paths if p['wrapperNull']is False]
 need('disjoint-whole-owned-hidden-and-argument-homes',type(frame_bytes)is int and frame_bytes>=max(hidden_at,argument_at)+44
  and min(hidden_at,argument_at)>=32 and(hidden_at+44<=argument_at or argument_at+44<=hidden_at)
  and all(r['displacement']==argument_at+r['sourceOffset']for r in ordered)
  and all([hidden_at-frame_bytes,44]in p['frame'].get('hiddenSourceLocalHomes',[])for p in positive)
  and all(all([r['displacement']-frame_bytes,r['bytes']]in p['frame'].get('copiedSourceLocalHomes',[])for r in ordered)for p in positive))
 alias=positive[0]['frame'].get('sourceFrameAlias',{})
 need('exact-RAX-RBP-normalized-frame-alias',alias.get('profile')=='mission-trigger44-RAX-RBP-frame.v1'
  and alias.get('baseRegister')=='rbp'and type(alias.get('entryRspOffset'))is int
  and alias.get('currentRspBytes')==frame_bytes and type(alias.get('rspRelativeBaseOffset'))is int
  and alias['entryRspOffset']+frame_bytes==alias['rspRelativeBaseOffset']
  and all(same(p['frame'].get('sourceFrameAlias'),alias)for p in positive))
 entry_alias,raw=instruction(alias['entryRspAliasInstruction']);bp_alias,bp_raw=instruction(alias['baseAliasInstruction'])
 need('actual-entry-RAX-and-RBP-alias-bytes',raw==bytes.fromhex('488bc4')and len(bp_raw)==4
  and bp_raw[:3]==bytes.fromhex('488d68')and bp_alias>entry_alias
  and int.from_bytes(bp_raw[3:],'little',signed=True)==alias['entryRspOffset'])
 def rbp_home(row):
  address=row.get('frameAddress',{})
  need('exact-normalized-RBP-home',address.get('baseRegister')=='rbp'and type(address.get('displacement'))is int
   and address.get('rspDisplacement')==row['displacement']
   and address['displacement']+alias['rspRelativeBaseOffset']==row['displacement'])
  return address['displacement']
 hidden_rbp=rbp_home(hidden[0]);argument_rbp=rbp_home(ordered[0])
 need('whole-RBP-argument-slices',all(rbp_home(r)==argument_rbp+r['sourceOffset']for r in ordered))
 setter=owner['setters'][index];validate_event(read,setter);holder=setter.get('directHolder',{});life=owner['lifecycle']
 need('same-exact-named-direct-holder-setter',same(setter,scope['richSetters'][index])
  and setter.get('profile')=='direct-base-holder-setter'and setter.get('sourceProfile')=='direct-named-outer-raw-value-setter'
  and same(setter.get('nominalValueLayout'),layout)and setter.get('incomingValueStoredUnchanged')is True
  and setter.get('parameterTypeRecordHex')==proof['argumentRawHex']
  and setter.get('targetField')==owner['wrappedType']+'::shape'and setter['method'][1]==owner['wrapperName']
  and setter['member']['name']=='shape'and setter['member']['declaredType']==source.TYPE
  and setter['member']['methodIndex']==setter['method'][0]and type(setter['method'][0])is int
  and type(setter['method'][3])is int and type(setter.get('fieldOffset'))is int
  and life.get('directHolderMode')is True and life.get('typedCache')is None
  and same(life.get('baseHolder'),holder.get('field'))and holder.get('ownerTypeDefinition')==life.get('typeDefinition')
  and holder.get('field')==[owner['wrapperName'],owner['wrappedType'],16]
  and holder.get('inheritedFieldAliasUsed')is False and holder.get('openGenericOffsetUsed')is False
  and setter.get('getter')is None and setter.get('childGrammarAdmitted')is False and setter.get('factoryAdmitted')is False)
 regions=_owned_regions([(base+at,h)for at,h in setter['ordinarySourceRegions']],setter['codeWindows'],base=base,label='TriggerShape-named-setter')
 replay=setter_program(regions,base+setter['method'][3],type_name=source.TYPE,field=setter['fieldOffset'])
 need('whole-named-setter-copy-replayed',same(replay,setter['program']))
 transfer=transfer_program([(base+at,bytes.fromhex(h))for at,h in selected],base+site+5,
  hidden_rbp=hidden_rbp,argument_rbp=argument_rbp,setter=base+setter['method'][3],
  path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,scope['codeWindows'],base))
 stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index]
 sources=[r for r in rich.get('sources',[])if r.get('memberIndex')==index]
 need('one-whole44-owned-setter-call',len(stores)==len(sources)==1 and sources[0].get('resultAbi')=='hidden-local'
  and same(sources[0].get('instruction'),read['instruction'])and type(stores[0].get('storedBytes'))is int
  and stores[0]['storedBytes']==44 and type(stores[0].get('sourceOffset'))is int and stores[0]['sourceOffset']==0
  and stores[0]['instruction'][0]+base==transfer['setterInstructionVa'])
 instruction(stores[0]['instruction'])
 for row,register in zip(ordered,('xmm0','xmm1','xmm0','rax'),strict=True):
  at,_=instruction(row['storeInstruction'])
  need('owned-argument-copy-between-source-and-setter',site<at<stores[0]['instruction'][0]and row.get('sourceRegister')==register)
 return 'trigger-shape-raw44'


def compile_member(owner,scope,read,pins):
 try:return _compile_member(owner,scope,read,pins)
 except(ValueError,KeyError,IndexError,TypeError)as error:
  from scripts.game_data.memorypack.corpus_gate import CensusGateError
  failure=CensusGateError('storyTriggerShapeRawComponents.field',source=owner.get('wrapperName','unknown')+'::Deserialize',
   expected='Exact direct raw44 source/R8/E8, disjoint RBP hidden/argument homes, named whole setter and all four complete frames.',
   actual=dict(wrapperName=owner.get('wrapperName'),fieldName=read.get('fieldName'),memberIndex=read.get('memberIndex'),failedGate=str(error)[:1000]))
  failure.diagnostic.update(validator='storyTriggerShapeRawComponents',nativeInputs=pins,sourceInstruction=read.get('instruction'))
  failure.args=(json.dumps(failure.diagnostic,ensure_ascii=False),);raise failure from error
