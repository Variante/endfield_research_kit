"""Finite Char ordinary record/custom-curve children and whole parent stores."""
import struct

CURVE='UnityEngine.AnimationCurve'
TRANSFORM='Beyond.Gameplay.TransformDesc'
NPC='Beyond.NPC.Ability.NPCMontageBasicDesc'
SCHEMA='endfield.char-interact-unity-curve-components.v1'
CAPABILITY='char-unity-animation-curve'
WIRE=CAPABILITY


def need(check,condition):
    if not condition:raise ValueError('charReferenceRecords.'+check)


def derive_curve(image,pins):
    from scripts.game_data.memorypack.skill_animation_curve_sources import derive,CAPABILITY as selected
    native=derive(image,pins,count_limit=10000)
    need('fresh-own-custom-Unity-source',native.get('nativeInputs')==pins)
    return dict(schema=SCHEMA,status='validated-conditional-char-unity-curve',nativeInputs=pins,
        capability=CAPABILITY,capabilities={CAPABILITY:dict(native['capabilities'][selected],
            originalTypeDefinition=image.named_types[CURVE].index)},requiredExternalCapabilities=[],
        proof=dict(source=native),parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def validate_curve(component,pins):
    from scripts.game_data.memorypack.skill_animation_curve_codec import require_capability
    from scripts.game_data.memorypack.skill_animation_curve_sources import CAPABILITY as selected,SCHEMA as native_schema
    need('own-whole-custom-Unity-curve',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-char-unity-curve'and component.get('capability')==CAPABILITY
        and component.get('requiredExternalCapabilities')==[]and component.get('parentFieldAdmitted')is False
        and component.get('wholeOwnerAdmitted')is False)
    native=component['proof']['source'];cap=require_capability(component['capabilities'][CAPABILITY])
    need('same-independent-fresh-custom-source',native.get('schema')==native_schema and native.get('nativeInputs')==pins
        and native.get('status')=='validated-conditional-unity-animation-curve'
        and type(cap.get('originalTypeDefinition'))is int and cap['originalTypeDefinition']>0
        and dict(cap,originalTypeDefinition=None)==dict(native['capabilities'][selected],originalTypeDefinition=None)
        and set(component['capabilities'])=={CAPABILITY})
    return {k:component[k]for k in('capability','capabilities','requiredExternalCapabilities')}


def _child(component,pins,capability,name):
    if name==CURVE:
        own=validate_curve(component,pins);need('own-Unity-curve-key',capability==own['capability'])
    elif name==TRANSFORM:
        from scripts.game_data.memorypack import animation_transform_desc_components as transform
        from scripts.game_data.memorypack.animation_transform_desc_codec import require_capability
        need('own-ordinary-Transform-source',component.get('schema')==transform.SCHEMA and component.get('nativeInputs')==pins
            and component.get('status')=='validated-conditional-transform-desc-components'and capability==transform.CAPABILITY
            and component.get('requiredExternalCapabilities')==[]and component.get('parentFieldAdmitted')is False
            and component.get('wholeOwnerAdmitted')is False and set(component.get('capabilities',{}))=={capability})
        cap=require_capability(component['capabilities'][capability],ordinary=True);p=component['proof'];source=p['source']
        composed=transform.compose(source,pins);adapter=p['adapter'];reference=p['referenceReaders']
        need('same-complete-Transform-source-adapter-and-reader',component.get('compiled')==composed['compiled']
            and adapter.get('nativeInputs')==pins and adapter.get('typeName')==TRANSFORM and adapter.get('pair')==p['pair']
            and adapter.get('getterMethod')==source['lifecycle']['GetValue']['method']
            and adapter.get('pairForwarder',{}).get('readerMethod')==source['method']
            and all(cap.get(k)==reference.get(k)for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')))
    else:
        from scripts.game_data.memorypack.char_record_components import validate_component
        need('own-finite-NPC-record-reference',name==NPC)
        own=validate_component(component,pins);need('own-NPC-record-key',capability==own['capability'])
    cap=component['capabilities'][capability]
    need('same-nominal-whole-ordinary-reference',cap.get('typeName')==name and cap.get('wholeGrammarAdmitted')is True
        and cap.get('ordinaryOriginalReadValueAdmitted')is True and type(cap.get('originalTypeDefinition'))is int)
    return cap


def bind_member(parent,scope,read,pins,usage,component,capability):
    name=read.get('declaredType');need('finite-own-reference-family',name in(CURVE,TRANSFORM,NPC))
    cap=_child(component,pins,capability,name);context=read.get('context',{});raw=bytes.fromhex(context.get('argumentRawHex',''))
    need('actual-own-CLASS18-context-and-reader',parent.get('wrappedType','').startswith('Beyond.Gameplay.Core.CharInteractPerform.')
        and len(raw)==16 and raw[10:12]==bytes((18,0))and int.from_bytes(raw[:8],'little')==cap['originalTypeDefinition']
        and context.get('register')=='rdx'and context.get('typeKind')==18
        and(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))==
            (usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec')))
    load=bytes.fromhex(context.get('instructionHex',''));site,encoded=read.get('instruction',[None,'']);encoded=bytes.fromhex(encoded)
    need('actual-owned-ordinary-context-and-E8',context.get('methodOwner')=='MemoryPack.MemoryPackReader'
        and context.get('methodName')=='ReadValue'and context.get('fullTypeName')==name
        and len(load)==7 and load[:3]==bytes.fromhex('488b15')
        and[context.get('instructionRva'),context.get('instructionHex')]in scope.get('selectedProgram',[])
        and usage.get('tag')==6 and len(encoded)==5 and encoded[0]==232 and type(site)is int
        and site+5+int.from_bytes(encoded[1:],'little',signed=True)==read.get('sourceTargetRva'))
    from scripts.game_data.memorypack.char_reference_field_bindings import require_transfer
    from scripts.game_data.memorypack.skill_root_child_bindings import bind_read_value
    transfer=require_transfer(parent,scope,read,pins)
    binding=bind_read_value(pins,dict(fieldName=read['fieldName'],typeName=name,typedRequest=usage,
        sourceTargetRva=read['sourceTargetRva']),component,capability)
    return dict(binding,parentTransfer=transfer)


def require_capability(capability,cap):
    from scripts.game_data.memorypack.skill_animation_curve_codec import require_capability as curve
    need('own-custom-Unity-wire-key',capability==CAPABILITY and type(cap.get('originalTypeDefinition'))is int)
    return curve(cap)


def read(reader,capability,*,depth=0,budget=None):
    from scripts.game_data.memorypack.skill_animation_curve_codec import read_curve
    need('bounded-depth',type(depth)is int and 0<=depth<64)
    cap=require_capability(capability,reader.operation.child(capability));start=reader.pos;marker=reader.peek()
    need('own-Unity-MC3-or-null',marker in(3,255));count=0
    if marker!=255:
        need('complete-owned-Unity-prefix',start+13<=reader.limit);count=struct.unpack_from('<i',reader.data,start+9)[0]
        need('bounded-Unity-key-count',-1<=count<=cap['countLimit'])
        need('complete-Unity-key-data',start+13+28*max(count,0)<=reader.limit)
    budget=dict(remaining=16384)if budget is None else budget
    need('shared-budget-before-consumption',type(budget)is dict and set(budget)=={'remaining'}and type(budget['remaining'])is int
        and 1+max(count,0)<=budget['remaining']<=16384)
    budget['remaining']-=1+max(count,0);read_curve(reader,capability)
    return reader.records[-1]
