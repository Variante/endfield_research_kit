"""Exact Intro/Tail Opera value-array field joins, separate from CLASS arrays."""
import json

from scripts.game_data.memorypack import levelscript_opera_array_sources as arrays
from scripts.game_data.memorypack import levelscript_module_value_components as children

WIRE='story-module-opera-array'
CAPABILITY=children.OPERA_ARRAY
PARENTS=('Beyond.Gameplay.EncounterData+IntroPart','Beyond.Gameplay.EncounterData+TailPart')


def need(key,condition):
 if not condition:raise ValueError('storyOperaArrayComponents.'+key)


def norm(value):return json.loads(json.dumps(value))


def verify_source(actual,pins,element):
 from scripts.game_data.codecs.levelscript.current_module_values import validate_value
 from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 from scripts.game_data.memorypack import animation_state_array_sources as shared
 validate_value(element);p=actual.get('proof',{});layout=p.get('layout',{})
 need('exact-own-array-source-and-element',actual.get('schema')==arrays.SCHEMA and actual.get('nativeInputs')==pins
  and actual.get('status')=='validated-conditional-opera-value-array'and actual.get('elementType')==arrays.TYPE
  and actual.get('elementValueType')is True and actual.get('closedArrayType')==arrays.TYPE+'[]'
  and actual.get('elementManagedBytes')==16 and actual.get('elementWireBytes','missing')is None
  and actual.get('countRange')==[-1,4096]and actual.get('countLimit')==4096 and actual.get('nullable')is True
  and all(actual.get(k)is True for k in('positiveCountsAdmitted','initiallyNullArrayRequired','actualSourceProved'))
  and all(actual.get(k)is False for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted'))
  and element.get('typeName')==arrays.TYPE and layout.get('typeName')==arrays.TYPE
  and layout.get('typeDefinition')==element.get('originalTypeDefinition')and layout.get('managedBytes')==16
  and layout.get('referenceLaneOffsets')==[8]and layout.get('paddingByteRanges')==[[4,8]])
 first=p['returnProgram']['selectedBytes'][0][0];base=first-actual['arrayReaderTargetRva']
 raw={role:regions(p['sourceWindows'][role],[[a-base,h]for a,h in rows],base,'story-Opera-array-'+role)
  for role,rows in p['actualSourceRegions'].items()}
 symbols={k:base+v for k,v in p['symbolRvas'].items()};front=arrays.return_program(raw['front'],first)
 need('full-return-overload',norm(front)==p['returnProgram']and front.get('initiallyNullOutputProved')is True)
 paths=[arrays.byref_program(raw['byref'],front['byrefTargetVa'],count=n)for n in(-1,0,1,2,3)]
 need('all-five-owned-array-paths',norm(paths)==p['programs'])
 helpers=dict(header=shared.header_program(raw['header'],symbols['header'],p['readerOffsets']),
  index=arrays.index_program(raw['index'],symbols['index']),empty=arrays.empty_program(raw['empty'],symbols['empty'],symbols['context']),
  provider=arrays.provider_program(raw['provider'],symbols['provider']),dispatch=arrays.dispatch_program(raw['dispatch'],symbols['dispatch']))
 induction=prove_induction(paths[1:],initial='33f6',increment='ffc6',comparison='413bf6',counter='esi',saved_count='r14d',
  max_count=4096,mode_key='newArray',backedge_sites=[paths[-1]['actualBackedgeVa']])
 need('all-helpers-and-identical-induction',norm(helpers)==p['helperPrograms']and norm(induction)==p['induction'])
 usage=actual['typedRequest'];context=p['arrayContext'];decl=p['formatterDeclaration']
 need('exact-owned-overloads-and-callback-ABI',(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
  (6,'MemoryPack.MemoryPackReader','ReadArray',[],[arrays.TYPE])and usage['methodSpec'][0]==actual['arrayReaderMethodDefinition']
  and context.get('returnOverloadDefinition')==usage['methodSpec'][0]and context.get('readArrayOverloadsReciprocallyJoined')is True
  and context.get('emptyArrayTypeProviderAndDeserializeOwned')is True and context.get('formatterSlot')==decl.get('formatterSlot')==5
  and decl.get('abstractDeclaration')is True and decl.get('sameReaderByref')is True and decl.get('ownClassVAROutputByref')is True
  and decl.get('concreteCallbackBodyProved')is False)
 return base


def bind_member(source,scope,read,pins,usage,component,capability):
 from scripts.game_data.codecs.levelscript.current_module_values import validate_array
 need('same-complete-child-component',component.get('schema')==children.SCHEMA and component.get('status')=='validated-conditional-module-values'
  and component.get('nativeInputs')==pins and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False
  and capability==CAPABILITY)
 cap=component['capabilities'][CAPABILITY];validate_array(cap);name=source.get('wrappedType');index=read['memberIndex']
 need('only-own-Intro-or-Tail-field',name in PARENTS and read.get('fieldName')=='operaSegments')
 actual=scope.get('arraySources',{}).get(str(index),{});array=component['proof']['operaArrays'][name]
 value=component['proof']['values'][arrays.TYPE]
 parameters=children.parameter_array_capability(value,component['proof']['paramGraph'],pins)
 expected=children.value_capability(value,pins,parameters=parameters)
 need('same-fresh-actual-element-value-proof',expected==cap['elementCapability'])
 base=verify_source(array,pins,cap['elementCapability']);context=read.get('context',{});raw=bytes.fromhex(context.get('argumentRawHex',''))
 need('exact-own-value-array-member',read.get('mode')=='typed-value-array'and source.get('schema')=='endfield.generated-concrete-reader-source.v1'
  and source.get('nativeInputs')==pins and source.get('completeSelectedCallerAdmitted')is True and source.get('sourceScope')==scope
  and source.get('orderedSourceReads',[])[index]==read and scope['events'][index]==read
  and(read.get('declaredType'),read.get('kind'))==(arrays.TYPE+'[]','reference:'+arrays.TYPE+'[]')
  and(context.get('typeKind'),context.get('register'),context.get('methodName'),context.get('methodOwner'),context.get('fullTypeName'))==
   (17,'rdx','ReadArray','MemoryPack.MemoryPackReader',arrays.TYPE)
  and len(raw)==16 and raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==context.get('typeDefinition')==cap['elementCapability']['originalTypeDefinition']
  and tuple(context.get(k)for k in('instructionRva','instructionHex','methodSpec'))==tuple(usage.get(k)for k in('instructionRva','instructionHex','methodSpec'))
  and actual==array and array['typedRequest']==usage and read.get('sourceTargetRva')==cap['arrayReaderTargetRva'])
 at,h=read['instruction'];code=bytes.fromhex(h)
 need('actual-parent-E8-target',len(code)==5 and code[0]==232 and at+5+int.from_bytes(code[1:],'little',signed=True)==read['sourceTargetRva'])
 rich=scope['richProgram'];flows=[x for x in rich.get('sources',[])if x.get('memberIndex')==index];stores=[x for x in rich.get('fieldStores',[])if x.get('memberIndex')==index]
 setter=source['setters'][index]
 need('whole-array-RAX-to-named-field',rich.get('completeSelectedNormalProgram')is True and rich.get('selectedProgram')==scope.get('selectedProgram')
  and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='rax')]
  and len(stores)==1 and(stores[0].get('sourceOffset'),stores[0].get('storedBytes'))==(0,8)
  and stores[0].get('instruction')in scope['selectedProgram']and scope['richSetters'][index]==setter
  and setter.get('targetField')==name+'::operaSegments'and setter.get('storedBytes')==8 and setter.get('incomingValueStoredUnchanged')is True
  and setter.get('method',[None,None,None])[2]=='set___operaSegments__'and setter.get('codeWindows')
  and setter.get('profile')in('direct-base-holder-setter','cached-getter-setter','inline-coherent-cache-setter'))
 at,h=stores[0]['instruction'];code=bytes.fromhex(h)
 need('actual-complete-named-setter-call',len(code)==5 and code[0]in(232,233)
  and at+5+int.from_bytes(code[1:],'little',signed=True)==setter['method'][3])
 paths=source.get('programs',[])
 need('all-four-complete-parent-frames',len(paths)==4 and{(p.get('existing'),p.get('wrapperNull'))for p in paths}=={(n,f)for n in(False,True)for f in(False,True)}
  and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool and p.get('frame',{}).get('entryRspRestored')is True
   and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
 return dict(fieldName='operaSegments',typeName=arrays.TYPE+'[]',capability=CAPABILITY,
  readerMethodDefinition=cap['arrayReaderMethodDefinition'],sourceTargetRva=read['sourceTargetRva'],
  completeOwnArrayReferenceFieldTransfer=True,allFourParentFramesProved=True,elementCapability=children.VALUE_CAPS[arrays.TYPE],
  actualCallbackEqualsCanonicalRequired=True)
