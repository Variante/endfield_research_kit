"""Replay Interactive dictionary source and its complete enclosing field join.

This joins framing only. Both nominal child grammars and callback selection
are still required by the eventual dictionary owner; no source-only result is
a public grammar or a whole-record admission.
"""
import json
from scripts.game_data.memorypack import interactive_dictionary_sources as source
from scripts.game_data.memorypack.generated_inline_record_components import _coverage


def need(check,condition):
    if not condition:raise ValueError('interactiveDictionaryComponents.'+check)


def norm(value):return json.loads(json.dumps(value))


def replay_source(actual,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    need('exact-owned-current-source',actual.get('schema')==source.SCHEMA
        and actual.get('nativeInputs')==pins and actual.get('typeName')in source.TYPES
        and actual.get('resultAbi')=='void-byref-reference8'and actual.get('referenceBytes')==8
        and actual.get('initiallyNullOutputRequired')is True and actual.get('keyGrammarAdmitted')is False
        and actual.get('valueGrammarAdmitted')is False and actual.get('parentFieldAdmitted')is False
        and actual.get('wholeOwnerAdmitted')is False)
    key,value=source.request_shape(actual.get('context',{}).get('typedRequest',{}));p=actual['proof']
    context=actual['context'];programs=p.get('programs',[])
    need('five-complete-source-paths',len(programs)==5 and bool(programs[0].get('selectedBytes'))
        and context.get('fullTypeName')==actual['typeName']==source.OWNER+'<'+key+','+value+'>'
        and context.get('contextMode')==source.MODE and context.get('resultAbi')==actual['resultAbi']
        and actual.get('readerMethodDefinition')==context.get('methodSpec',[None])[0])
    base=programs[0]['selectedBytes'][0][0]-actual['sourceTargetRva']
    need('literal-native-image-base',type(base)is int and base>=2**32)
    raw=regions(p['windows'],p['sourceRegions'],base,'interactive-dictionary')
    symbols,checked,induction=source.source_programs(raw,base+actual['sourceTargetRva'],p['readerOffsets'],key,value)
    need('every-owned-source-byte-loop-and-frame',norm(checked)==programs and norm(induction)==p.get('induction')
        and {k:v-base for k,v in symbols.items()}==p.get('symbolRvas')
        and all(path.get('entryRspRestored')is True
            and (path.get('countWitness')==-1 or path.get('initiallyNullOutputRequired')is True)for path in programs))
    return base,key,value


def bind_parent_source(owner,scope,read,pins,actual):
    """Authenticate the existing source's own typed call, null home and field."""
    from scripts.game_data.memorypack.interactive_dictionary_parent import ROSTERS,validate_setup
    base,key,value=replay_source(actual,pins);index=read.get('memberIndex');name=owner.get('wrappedType')
    need('finite-own-enclosing-field',name in ROSTERS and index in ROSTERS[name]
        and (read.get('fieldName'),read.get('declaredType'))==ROSTERS[name][index][:2]
        and owner.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and owner.get('nativeInputs')==scope.get('nativeInputs')==pins
        and owner.get('completeSelectedCallerAdmitted')is True and owner.get('childGrammarAdmitted')is False
        and owner.get('sourceScope')==scope and owner.get('orderedSourceReads',[])[index]==scope['events'][index]==read)
    setter=owner['setters'][index];context=source.validate_event(read,setter)
    need('same-fresh-parent-selected-source',scope.get('staticReferenceSources',{}).get(str(index))==actual
        and context==actual['context']and read.get('sourceTargetRva')==actual['sourceTargetRva'])
    at,h=read['instruction'];raw=bytes.fromhex(h)
    need('actual-source-E8',len(raw)==5 and raw[0]==232
        and at+5+int.from_bytes(raw[1:],'little',signed=True)==actual['sourceTargetRva'])
    rich=scope.get('richProgram',{});stores=[s for s in rich.get('fieldStores',[])if s.get('memberIndex')==index]
    parent_setup=rich.get('staticOutParentSetup',{})
    need('independent-complete-parent-null-and-class-setup',validate_setup(parent_setup,scope['events'])==parent_setup
        and parent_setup.get('parentType')==name)
    setup=[s for s in parent_setup.get('initializedZeroLocals',[])if s.get('memberIndex')==index]
    need('whole-reference-and-complete-parent-program',rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==scope.get('selectedProgram')
        and _coverage(stores,8,'sourceOffset','storedBytes')and len(setup)==1
        and setup[0].get('displacement')==ROSTERS[name][index][2]
        and setter.get('incomingValueStoredUnchanged')is True and setter.get('storedBytes')==8)
    paths=owner.get('programs',[])
    need('four-complete-enclosing-frames',len(paths)==4
        and {(p.get('existing'),p.get('wrapperNull'))for p in paths}=={(False,False),(False,True),(True,False),(True,True)}
        and all(p.get('frame',{}).get('entryRspRestored')is True and p.get('frame',{}).get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
    need('both-positive-frames-own-the-whole-null-home',all(any(
        z.get('instruction')==setup[0]['instruction']and z.get('displacement')==setup[0]['displacement']
        and z.get('entryRspOffset')==setup[0]['entryRspOffset']
        for z in p['frame'].get('initializedZeroLocalProofs',[]))for p in paths if p['wrapperNull']is False))
    return dict(typeName=actual['typeName'],fieldName=read['fieldName'],memberIndex=index,
        keyType=key,valueType=value,sourceTargetRva=actual['sourceTargetRva'],readerMethodDefinition=actual['readerMethodDefinition'],
        sourceInstruction=read['instruction'],typedRequest=context['typedRequest'],
        sourceAndParentJoined=True,childGrammarAdmitted=False,wholeOwnerAdmitted=False)
