"""The two Tianshizhuang closed LangKey16 fields and independent MC1 child.

The caller's hidden16/two string references and nonserialized rawText remain
separate from MC1/pool-index wire bytes. No nominal sibling, pointer alias or
runtime provider choice is admitted by this finite helper.
"""
import json
from scripts.game_data.memorypack import generated_module_value_forwarder_sources as forwarder
from scripts.game_data.memorypack import leveldata_lang_key_components as child_owner

TYPE='Beyond.LangKey'
PARENT='Beyond.Gameplay.TianshizhuangData'
FIELDS=('activateOption','finishOption')
CAP=child_owner.CAP


def need(check,condition):
    if not condition:raise ValueError('moduleLangKeyBindings.'+check)
def norm(value):return json.loads(json.dumps(value))
def owns_member(parent,name,nominal):return parent==PARENT and name in FIELDS and nominal==TYPE


def require_source(actual,read,pins,usage):
    from scripts.game_data.memorypack.generated_vector3_source import forwarder_program
    from scripts.game_data.memorypack.leveldata_tracking_raw_sources import _owned_regions
    need('own-finite-closed-LangKey-source',actual.get('schema')==forwarder.SCHEMA
        and actual.get('status')=='proved-conditional-owned-Module-ReadValue-forwarder'
        and actual.get('typeName')==read.get('declaredType')==TYPE and actual.get('nativeInputs')==pins
        and read.get('context')is None
        and actual.get('sourceContextMode')==actual.get('contextMode')==read.get('sourceContextMode')=='owned-closed-forwarder'
        and actual.get('managedBytes')==read.get('managedBytes')==16
        and actual.get('resultAbi')==read.get('resultAbi')=='hidden-local'
        and actual.get('sourceTargetRva')==read.get('sourceTargetRva')
        and actual.get('actualSourceProved')is True and actual.get('pointerAliasClaimed')is False
        and all(actual.get(k)is False for k in('wireGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    p=actual['proof'];nested=p['nestedSource'];context=p['internalContext'];forwarder.context_shape(context,TYPE)
    need('own-independent-MC1-and-hidden16-child',nested.get('schema')=='endfield.story-lang-key-value-source.v1'
        and nested.get('status')=='validated-conditional-source'and nested.get('nativeInputs')==pins
        and nested.get('typeName')==TYPE and nested.get('managedBytes')==16 and nested.get('resultAbi')=='hidden-local'
        and nested.get('referenceLaneOffsets')==[0,8]and nested.get('actualSourceProved')is True
        and nested.get('wireGrammarAdmitted')is False and p['typedRequest']==nested['proof']['typedRequest']==usage
        and nested['readerMethodDefinition']==actual['readerMethodDefinition']==usage['methodSpec'][0]
        and nested['proof']['dedicatedLayout']==dict(parentMemberCount=4,keyMemberCount=1,keyName='key',
            stringEncoding='int32-pool-index',managedKeyBytes=16,serializedPositiveKeyBytes=5,
            wholeOwnerAdmitted=False,nonserializedRawText=True))
    need('same-actual-internal-ReadValue-MethodInfo',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
        (6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE])
        and all(context[k]==usage[k]for k in('instructionRva','instructionHex','methodSpec')))
    base=p['forwarderProgram']['selectedBytes'][0][0]-actual['sourceTargetRva']
    regions=_owned_regions(p['actualSourceRegions'],p['actualWindows'],base=base,label='Module-LangKey-forwarder')
    program=forwarder_program(regions,base+actual['sourceTargetRva']);raw=bytes.fromhex(context['instructionHex'])
    need('whole-forwarder-program-and-own-internal-E8',norm(program)==p['forwarderProgram']
        and program['nestedTargetVa']==base+nested['sourceTargetRva']
        and program['contextInstructionVa']==base+context['instructionRva']
        and p['actualFamily'].get('selectedPrimaryRva')==actual['sourceTargetRva']
        and len(raw)==7 and raw[:3]==bytes.fromhex('4c8b05')
        and base+context['instructionRva']+7+int.from_bytes(raw[3:],'little',signed=True)
            ==context['cellVa']==base+usage['usageCellRva'])
    return nested,base


def component(actual,pins):
    read=dict(declaredType=TYPE,managedBytes=16,resultAbi='hidden-local',context=None,
        sourceContextMode='owned-closed-forwarder',sourceTargetRva=actual.get('sourceTargetRva'))
    nested,_=require_source(actual,read,pins,actual['proof']['typedRequest'])
    from scripts.game_data.codecs.leveldata.current_lang_key import validate
    cap=child_owner._capability(nested);validate(cap)
    return dict(schema='endfield.story-lang-key-component.v1',nativeInputs=pins,capabilities={CAP:cap},
        proof=dict(readSource=nested),parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def _setter(parent,setter,base,barrier):
    from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
    from scripts.game_data.memorypack.generated_member_sources import coherent_getter_program
    from scripts.game_data.memorypack.generated_managed_value_sources import setter_program
    getter=setter.get('getter')or{};life=parent['lifecycle'];method=getter.get('method',[])
    need('same-own-cached-getter-and-whole16-setter',setter.get('profile')=='cached-getter-setter'
        and getter==life.get('coherentGetter')and len(method)==4 and method[1]==parent['wrapperName']
        and getter.get('coherentNonNullSamePointerReturn')is True
        and getter.get('baseHolder')==life.get('baseHolder')and getter.get('typedCache')==life.get('typedCache')
        and getter['typedCache'][:2]==[parent['wrapperName'],PARENT])
    rows=[(a,bytes.fromhex(h))for a,h in getter['program']['selectedBytes']];candidates=[]
    for mode in('rbx','rdi'):
        try:candidates.append(coherent_getter_program(rows,base+method[3],base_slot=getter['baseHolder'][2],
            cache_slot=getter['typedCache'][2],mode=mode,path_factory=lambda regions,entry:
                _owned_setter_trace(regions,entry,getter['codeWindows'],base)))
        except(ValueError,KeyError,IndexError):pass
    need('one-replayed-own-coherent-getter',len(candidates)==1 and norm(candidates[0])==getter['program'])
    p=setter['program'];rows=[(a,bytes.fromhex(h))for a,h in p['selectedBytes']]
    _owned_setter_trace(rows,base+setter['method'][3],setter['codeWindows'],base)
    # The taken nonnull branch and every selected instruction have actual
    # bytes; the separate source owner authenticates the full method windows.
    need('whole-selected-two-reference-setter-replayed',norm(setter_program(rows,base+setter['method'][3],
        field=setter['fieldOffset'],managed_bytes=16,reference_lane_offsets=[0,8],
        getter=base+method[3],barrier=barrier))==p)


def bind(parent,scope,read,pins,usage,child,capability):
    from scripts.game_data.memorypack.generated_managed_value_components import require_transfer
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    i=read.get('memberIndex')
    need('finite-own-parent',owns_member(parent.get('wrappedType'),read.get('fieldName'),read.get('declaredType'))
        and type(i)is int and i in(2,4))
    actual=scope['managedValueSources'][str(i)];nested,base=require_source(actual,read,pins,usage)
    need('same-independent-child',capability==CAP and child==component(actual,pins))
    transfer=require_transfer(parent,scope,read,pins,source_context=actual['proof']['internalContext'])
    setter=parent['setters'][i];layout=setter['managedValueLayout']
    _setter(parent,setter,base,base+nested['proof']['sourceSymbols']['barrier'])
    need('exact-own-two-reference-layout',layout.get('fields')==[['key','string',16,14],['<rawText>k__BackingField','string',24,14]]
        and layout.get('referenceLaneOffsets')==[0,8]and layout.get('paddingByteRanges')==[]
        and layout.get('typeDefinition')==actual['proof']['internalContext']['typeDefinition']
        and setter['program'].get('barrierReferenceLaneOffset')==0)
    raw=bytes.fromhex(read['instruction'][1]);rich=scope['richProgram'];selected=scope['selectedProgram']
    need('actual-own-outer-E8',len(raw)==5 and raw[0]==232
        and read['instruction'][0]+5+int.from_bytes(raw[1:],'little',signed=True)==actual['sourceTargetRva'])
    g=BytesPath([(base+a,bytes.fromhex(h))for a,h in selected],base+read['instruction'][0]+5)
    g.take('4885f6');null=g.relative('0f84')
    need('own-source-null-exit',any(a==null-base and len(bytes.fromhex(h))==5 and bytes.fromhex(h)[0]==232 for a,h in rich['ownedNullExits']))
    g.take('0f1000','4533c0','488d55e7','488bce');copy=[g.at-base,'F30F7F45E7'];g.take(copy[1])
    store=[g.at-base,next(h for a,h in selected if base+a==g.at)];g.call(base+setter['method'][3])
    need('whole-self-copy-and-named16-store',
        [r for r in rich['fieldStores']if r['memberIndex']==i]==[dict(memberIndex=i,instruction=store,sourceOffset=0,storedBytes=16)])
    hidden,=[r for r in rich['hiddenSourceLocals']if r['memberIndex']==i]
    copied,=[r for r in rich['sourceLocalCopies']if r.get('memberIndex')==i]
    need('same-nominal-RBP-hidden-and-copy16',hidden.get('displacement')==copied.get('displacement')==48
        and hidden.get('bytes')==copied.get('bytes')==16 and hidden.get('sourceInstruction')==read['instruction']
        and hidden.get('nominalTypeName')==copied.get('nominalTypeName')==TYPE
        and hidden.get('nominalTypeDefinition')==copied.get('nominalTypeDefinition')==layout['typeDefinition']
        and copied.get('sourceOffset')==0 and copied.get('sourceRegister')=='xmm0'and copied.get('storeInstruction')==copy
        and hidden.get('frameAddress')==copied.get('frameAddress')==dict(baseRegister='rbp',displacement=-25,rspDisplacement=48))
    frame_bytes=scope['headerProof']['nullFrameBytes'];fragment=selected[selected.index(read['instruction']):selected.index(store)+1]
    # This MOVDQU writes the same hidden home. The source frame therefore
    # retains one hidden16 lifetime rather than inventing a second copy home.
    need('all-positive-frames-own-same-whole-copy',all(p['selectedProgram'][p['selectedProgram'].index(read['instruction']):
        p['selectedProgram'].index(store)+1]==fragment and[48-frame_bytes,16]in p['frame']['hiddenSourceLocalHomes']
        for p in parent['programs']if not p['wrapperNull']))
    return dict(fieldName=read['fieldName'],typeName=TYPE,capability=CAP,
        readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=read['sourceTargetRva'],
        managedBytes=16,referenceLaneOffsets=[0,8],wireMemberCount=1,positiveWireBytes=5,nullWireBytes=1,
        nonserializedRawText=True,completeFieldTransferAndFrameProved=True,managedValueTransfer=transfer,
        actualCallbackEqualsProvedChildRequired=True,wholeOwnerAdmitted=False)
