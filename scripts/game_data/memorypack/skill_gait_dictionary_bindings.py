"""Own static-reference local, reset, named setter and all parent frames."""
from scripts.game_data.memorypack import skill_gait_dictionary_components as component
from scripts.game_data.memorypack import skill_gait_dictionary_sources as source


def need(key,condition):
 if not condition:raise ValueError('skillGaitDictionaryBinding.'+key)


def bind(owner,scope,read,pins,usage,child,capability):
 index=read.get('memberIndex');need('own-finite-component',capability==source.CAPABILITY
  and child.get('schema')==component.SCHEMA and child.get('status')=='validated-conditional-static-out-dictionary'
  and child.get('nativeInputs')==pins and child.get('parentFieldAdmitted')is False and child.get('wholeOwnerAdmitted')is False)
 p=child['proof'];cap=component.compose(pins,p['source'],p['single'],p['enum'],p['keyDispatch'])
 need('exact-independent-wire-capability',child.get('capabilities')=={capability:cap})
 need('complete-current-parent',owner.get('schema')=='endfield.generated-concrete-reader-source.v1'
  and owner.get('nativeInputs')==scope.get('nativeInputs')==pins and owner.get('sourceScope')==scope
  and owner.get('completeSelectedCallerAdmitted')is True and owner.get('childGrammarAdmitted')is False
  and owner.get('wholeOwnerAdmitted')is False and type(index)is int and 0<=index<len(owner['orderedSourceReads'])
  and owner['orderedSourceReads'][index]==read and scope.get('events')==owner['orderedSourceReads'])
 setter=owner['setters'][index];context=source.validate_event(read,setter)
 actual=scope.get('staticReferenceSources',{}).get(str(index),{})
 need('same-fresh-independent-static-source',actual==p['source'] and actual.get('context')==context
  and actual.get('sourceTargetRva')==read.get('sourceTargetRva')==cap['staticReaderTargetRva']
  and actual.get('readerMethodDefinition')==cap['staticReaderMethodDefinition']==usage.get('methodSpec',[None])[0]
  and context.get('typedRequest')==usage)
 site,h=read['instruction'];raw=bytes.fromhex(h)
 need('actual-static-E8',len(raw)==5 and raw[0]==232 and site+5+int.from_bytes(raw[1:],'little',signed=True)==cap['staticReaderTargetRva'])
 need('same-fresh-named-setter',scope['richSetters'][index]==setter and setter.get('incomingValueStoredUnchanged')is True
  and setter.get('targetField')==owner['wrappedType']+'::'+read['fieldName'] and setter.get('storedBytes')==8
  and setter.get('member',{}).get('name')==read['fieldName']and setter['member'].get('declaredType')==source.TYPE
  and setter['method'][2]=='set___'+read['fieldName']+'__'and setter['method'][0]==setter['member']['methodIndex'])
 rich=scope['richProgram'];selected=scope['selectedProgram'];flows=[f for f in rich['sources']if f['memberIndex']==index]
 stores=[s for s in rich['fieldStores']if s['memberIndex']==index]
 need('whole-static-local-to-field-flow',rich.get('completeSelectedNormalProgram')is True and rich['selectedProgram']==selected
  and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='out-reference-local')]
  and len(stores)==1 and(stores[0]['sourceOffset'],stores[0]['storedBytes'])==(0,8)
  and stores[0]['instruction']in selected and read['instruction']in selected)
 locals_=[x for x in rich['hiddenSourceLocals']if x['memberIndex']==index]
 need('exact-owned-static-reference-local',len(locals_)==1 and locals_[0].get('bytes')==8
  and locals_[0].get('sourceAbi')=='void-byref-reference8'and locals_[0].get('nominalTypeName')==source.TYPE
  and locals_[0].get('nominalTypeDefinition')==context['typeDefinition']and locals_[0].get('initiallyZeroLocalRequired')is True
  and locals_[0].get('sourceInstruction')==read['instruction'])
 local=locals_[0];setup=rich.get('staticOutParentSetup',{});zeros=[z for z in setup.get('initializedZeroLocals',[])if z['displacement']==local['displacement']]
 need('actual-owned-class-guard-and-fresh-null-reset',setup.get('typeName')==source.TYPE and len(zeros)==1
  and zeros[0]in rich['initializedZeroLocals']and zeros[0]['instruction']in selected
  and selected.index(zeros[0]['instruction'])<selected.index(read['instruction'])
  and zeros[0].get('zeroSource',{}).get('zeroOnEveryOrdinaryPath')is True
  and setup.get('classGuard',{}).get('typedRequest',{}).get('typeName')==source.TYPE
  and setup.get('initializedClassStateObserved')is False)
 paths=owner['programs'];need('four-complete-parent-frames',len(paths)==4
  and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)}
  and all(p['frame'].get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
 for path in paths:
  if path['wrapperNull']:continue
  frame=path['frame'];lifetimes=[x for x in frame.get('hiddenSourceLocalLifetimes',[])if x['memberIndex']==index]
  need('protected-eight-byte-reference-through-final-setter',len(lifetimes)==1 and lifetimes[0]['bytes']==8
   and lifetimes[0]['displacement']==local['displacement']and lifetimes[0]['sourceInstruction']==read['instruction']
   and lifetimes[0]['fieldStores']==stores and lifetimes[0]['liveThroughInstruction']==stores[0]['instruction']
   and any(z.get('displacement')==local['displacement']for z in frame.get('initializedZeroLocalProofs',[])))
 return dict(fieldName=read['fieldName'],typeName=source.TYPE,capability=capability,
  readerMethodDefinition=cap['staticReaderMethodDefinition'],sourceTargetRva=cap['staticReaderTargetRva'],
  staticReferenceCapabilityShape=cap,ordinaryReferenceIdentityClaimed=False,
  staticReferenceTransfer=dict(sourceAbi='void-byref-reference8',wholeReferenceBytes=8,
   sourceLocal=local,fieldStores=stores,completeFieldTransferAndFrameProved=True))
