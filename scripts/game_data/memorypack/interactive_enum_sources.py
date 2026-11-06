"""Two exact Interactive enum nominals, separate from integer aliases.

The domain re-proves its own nominal callback selection and event-list source.
An actual parent request must bind that list separately; this supplies neither
an enclosing field transfer nor a whole Interactive grammar.
"""
from scripts.game_data.memorypack import enum_optin_native_sources as enums

DOMAIN='interactive-enums'
EVENT='Beyond.Gameplay.Core.EGameplayEvents'
AUDIO='Beyond.Gameplay.Core.InteractiveAudioComponent+EAudioTriggerState'
LIST='System.Collections.Generic.List`1<'+EVENT+'>'


def need(check,condition):
    if not condition:raise ValueError('interactiveEnums.'+check)


def validate(source,pins):
    from scripts.game_data.memorypack.nominal_enum_list_codec import require_capability
    need('own-explicit-selected-domain',source.get('schema')==enums.SCHEMA
        and source.get('status')=='validated-conditional-optin-enum-domain'
        and source.get('domain')==DOMAIN and source.get('nativeInputs')==pins
        and source.get('domainDeclaration')==dict(nominalEnums=sorted((EVENT,AUDIO)),
            collectionEnums=[EVENT],countLimit=4096)
        and source.get('defaultSkillDomainChanged')is False
        and source.get('parentFieldAdmitted')is False and source.get('wholeOwnerAdmitted')is False)
    caps=source.get('capabilities',{})
    need('exact-two-callbacks-and-event-list',set(caps)=={
        'skill-enum-callback:'+EVENT,'skill-enum-callback:'+AUDIO,'skill-enum-list:'+EVENT})
    for name in(EVENT,AUDIO):
        cap=caps['skill-enum-callback:'+name]
        need('independent-nominal-callback:'+name,cap.get('typeName')==name
            and cap.get('nativeInputs')==pins and cap.get('wireBytes')==4
            and cap.get('callbackSlot')==5 and cap.get('status')=='validated-conditional-callback'
            and cap.get('parentOrCollectionGrammarAdmitted')is False
            and cap.get('actualRuntimeSelectionObserved')is False
            and type(cap.get('callbackTargetRva'))is int and cap['callbackTargetRva']>0)
    require_capability(caps['skill-enum-list:'+EVENT],caps['skill-enum-callback:'+EVENT],
        name=EVENT,count_limit=4096,element_capability='skill-enum-callback:'+EVENT)
    return caps


def derive(image,pins):
    source=enums.derive(image,pins,domain=DOMAIN)
    validate(source,pins)
    return source


def bind_event_list(image,pins,read,source):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.unmanaged_enum_member_sources import bind_actual_call
    validate(source,pins)
    context=read.get('context',{})
    need('exact-actual-closed-list-read',read.get('declaredType')==LIST
        and read.get('kind')=='reference:'+LIST
        and (context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'),context.get('register'))
            ==('MemoryPack.MemoryPackReader','ReadPackable',LIST,'rdx'))
    usage=derive_typed_usage_context(image,context['instructionRva'],label='interactiveEnums.parent')
    need('same-fresh-actual-request',usage.get('methodSpec')==context.get('methodSpec')
        and usage.get('instructionHex')==context.get('instructionHex'))
    instruction=read['instruction'];image.check_instruction_windows([instruction],label='interactiveEnums.parentCall')
    target=image.pe.image_base+read['sourceTargetRva']
    actual=bind_actual_call(usage,instruction,source_target=target,base=image.pe.image_base)
    child=enums.bind_request(image,pins,source,typed_request=usage,call_target=target,enum_type=EVENT)
    return dict(typeName=LIST,fieldName=read['fieldName'],memberIndex=read['memberIndex'],
        typedRequest=usage,actualCall=actual,sourceBinding=child,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
