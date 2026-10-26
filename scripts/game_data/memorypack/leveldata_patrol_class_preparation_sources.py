"""Caller-independent selected preparation wrapper and normal return sources.

Only the actual nine-byte wrapper span is declared. Its tail target has its
own full native-owned family. The two program modes select literal descriptor
flag predicates; their labels do not assign meanings to those descriptor bits.
No generic no-unwind fallback, cold setup or live class selection is admitted.
"""
import hashlib,json
from scripts.game_data.memorypack import leveldata_patrol_dictionary_lookup_programs as paths

SCHEMA='endfield.patrol-class-preparation-source.v1'


def need(check,condition):
    if not condition:raise ValueError('patrolClassPreparation.'+check)


def norm(value):return json.loads(json.dumps(value))


def derive(image,pins,*,target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);base=image.pe.image_base
    need('actual-selected-pointer',type(target)is int and target>base)
    prefix=image.pe.bytes_at_va(target,9);need('exact-descriptor-wrapper-and-tail',prefix[:5]==bytes.fromhex('488b4978e9'))
    inner=target+9+int.from_bytes(prefix[5:],'little',signed=True);body=owned(image,inner)
    wrapper=dict(entryRva=target-base,windows=[dict(startRva=target-base,endRva=target-base+9,sha256=hashlib.sha256(prefix).hexdigest().upper())],
        regions=[[target-base,prefix.hex().upper()]],boundary='actual-selected-nine-byte-span-no-physical-extent')
    selected=dict(entryRva=inner-base,windows=body['windows'],regions=[[a-base,b.hex().upper()]for a,b in body['regions']],boundary='complete-native-owned-family')
    raw=[(target,prefix),*body['regions']]
    programs=[paths.preparation_program(raw,target,inner=inner,mode=mode)for mode in('initialized','being-initialized')]
    result=norm(dict(schema=SCHEMA,status='validated-conditional-selected-preparation-source',nativeInputs=pins,
        actualEntryRva=target-base,proof=dict(imageBase=base,wrapper=wrapper,inner=selected,programs=programs),
        selectedNormalPreparationNoNonframeWritesProved=True,physicalWrapperExtentProved=False,
        coldPreparationEffectsProved=False,runtimeClassSelectionObserved=False,runtimeInvocationObserved=False,
        conditions=['Valid compatible stable incoming class and descriptor pointer; the selected literal descriptor flag predicate already holds.',
            'Disjoint valid stack and object/descriptor storage; no concurrent mutation. Full normal frame/nonvolatile restoration is proved, while volatile registers may change.',
            'No claim that either descriptor flag was initialized, that a live class was selected, or that cold setup executed.']))
    validate(result,pins);_publication_gate(image,pins);return result


def validate(component,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    need('own-source-envelope',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-selected-preparation-source'
        and type(component.get('actualEntryRva'))is int and component['actualEntryRva']>0
        and component.get('selectedNormalPreparationNoNonframeWritesProved')is True
        and all(component.get(k)is False for k in('physicalWrapperExtentProved','coldPreparationEffectsProved','runtimeClassSelectionObserved','runtimeInvocationObserved')))
    p=component['proof'];base=p['imageBase'];need('selected-image-base',type(base)is int and base>=1<<32)
    wrapper=p['wrapper'];inner=p['inner'];need('exact-wrapper-entry-and-declared-span',wrapper['entryRva']==component['actualEntryRva']
        and len(wrapper['windows'])==len(wrapper['regions'])==1 and wrapper['windows'][0]['endRva']-wrapper['windows'][0]['startRva']==9)
    raw=regions(wrapper['windows'],wrapper['regions'],base,'classPrepare-wrapper')+regions(inner['windows'],inner['regions'],base,'classPrepare-inner')
    programs=[paths.preparation_program(raw,base+wrapper['entryRva'],inner=base+inner['entryRva'],mode=mode)for mode in('initialized','being-initialized')]
    need('both-exact-selected-return-programs',norm(programs)==p['programs'])
    return dict(actualEntryRva=component['actualEntryRva'],selectedNormalPreparationNoNonframeWritesProved=True,
        coldPreparationEffectsProved=False,runtimeClassSelectionObserved=False,runtimeInvocationObserved=False)
