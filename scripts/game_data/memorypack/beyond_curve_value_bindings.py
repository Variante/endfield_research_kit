"""Beyond curve16 parent transfer joined to its independent MC3/raw-key wire.

The complete caller owns each actual hidden local and named field. This finite
binder replays the full setter, exact normalized frame home and actual typed
ReadValue call before composing the separately proved Beyond curve child. It
admits no Unity curve, raw16 wire, enclosing record or runtime provider effect.
"""
import hashlib,json
from scripts.game_data.memorypack import beyond_curve_value_components as owner
from scripts.game_data.memorypack import generated_beyond_curve_field_sources as field

TYPE=field.TYPE
CAPABILITY=owner.CAPABILITY
SCHEMA='endfield.beyond-curve-parent-value-components.v1'


def need(check,condition):
    if not condition:raise ValueError('beyondCurveValueBindings.'+check)


def require_setter(setter):
    method=setter.get('method',[]);program=setter.get('program',{});selected=program.get('selectedBytes',[])
    need('own-named-setter-and-selected-path',len(method)==4 and all(type(method[i])is int for i in(0,3))
        and method[3]>0 and len(selected)>=2 and type(selected[0][0])is int)
    base=selected[0][0]-method[3];rows=setter.get('ordinarySourceRegions',[]);windows=setter.get('codeWindows',[])
    need('whole-unique-setter-regions',len(rows)==len(windows)>0 and len({a for a,h in rows})==len(rows))
    regions=[]
    for start,h in rows:
        raw=bytes.fromhex(h);matches=[w for w in windows if w.get('startRva')==start and w.get('endRva',0)-start==len(raw)
            and w.get('sha256','').upper()==hashlib.sha256(raw).hexdigest().upper()]
        need('whole-current-setter-window-hash',len(matches)==1);regions.append((base+start,raw))
    family=setter.get('sourceFamily',{})
    need('whole-owned-setter-family',family.get('schema')=='endfield.amd64-unwind-chain-family.v1'
        and family.get('selectedPrimaryRva')==method[3]
        and sorted(tuple(r['runtimeTriple'][:2])for r in family.get('ranges',[]))==sorted((w['startRva'],w['endRva'])for w in windows))
    by={a+i:b for a,raw in regions for i,b in enumerate(raw)};tail=selected[-2][0]
    need('actual-terminal-barrier-E9',selected[-2][1].lower()=='e9'and by.get(tail)==0xe9)
    barrier=tail+5+int.from_bytes(bytes(by[tail+i]for i in range(1,5)),'little',signed=True)
    getter=setter.get('getter');getter_target=base+getter['method'][3]if getter is not None else None
    actual=field.setter_program(regions,base+method[3],field=setter['fieldOffset'],barrier=barrier,getter=getter_target)
    need('complete-setter-byte-program-replayed',json.loads(json.dumps(actual))==program)
    if getter is None:
        holder=setter.get('directHolder',{})
        need('actual-literal-declared-holder',holder.get('fieldName')in('__instance','___instance')
            and holder.get('field')==[method[1],setter.get('targetField','').rsplit('::',1)[0],16]
            and holder.get('inheritedFieldAliasUsed')is False and holder.get('openGenericOffsetUsed')is False)
    return actual


def require_transfer(source,scope,read,pins):
    from scripts.game_data.memorypack.generated_managed_value_components import require_transfer as common_transfer
    transfer=common_transfer(source,scope,read,pins);index=read['memberIndex'];setter=source['setters'][index]
    field.validate_event(read,setter);require_setter(setter)
    need('own-field-layout',read['declaredType']==TYPE and setter['managedValueLayout'].get('fields')==[list(r)for r in field.FIELDS]
        and transfer['managedBytes']==16 and transfer['referenceLaneOffsets']==[0]and transfer['paddingByteRanges']==[])
    hidden=transfer['hiddenSourceLocal'];frame_bytes=scope.get('headerProof',{}).get('nullFrameBytes')
    need('literal-parent-hidden16-home',type(frame_bytes)is int and type(hidden.get('displacement'))is int
        and frame_bytes>=hidden['displacement']+16)
    expected=[hidden['displacement']-frame_bytes,16]
    need('exact-hidden16-home-in-both-positive-frames',all(expected in p['frame'].get('hiddenSourceLocalHomes',[])
        and all(type(n)is int for home in p['frame']['hiddenSourceLocalHomes']for n in home)
        for p in source['programs']if not p['wrapperNull']))
    need('explicit-source-local-copy-domain',[r for r in scope['richProgram'].get('sourceLocalCopies',[])if r.get('memberIndex')==index]==[])
    return transfer


def bind(source,scope,read,pins,usage,component,capability):
    need('own-independent-Beyond-wire-component',capability==CAPABILITY
        and component.get('schema')=='endfield.beyond-curve-value-components.v1'
        and component.get('status')=='validated-conditional-beyond-curve-value-components'and component.get('nativeInputs')==pins
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False
        and component.get('requiredExternalCapabilities',[])==[])
    value=component.get('proof',{}).get('value',{});caps=owner.compose(pins,value)
    need('whole-own-capability-shape',component.get('capabilities')==caps)
    transfer=require_transfer(source,scope,read,pins);actual=scope.get('managedValueSources',{}).get(str(read['memberIndex']),{})
    typed=value['proof']['typedSource'];context=read['context'];cap=caps[CAPABILITY]
    need('same-complete-actual-typed16-child-source',{k:v for k,v in actual.items()if k not in('referenceLaneOffsets','paddingByteRanges')}==typed
        and actual.get('referenceLaneOffsets')==[0]and actual.get('paddingByteRanges')==[]
        and actual.get('typeName')==TYPE and actual.get('nativeInputs')==pins and actual.get('providerSelectionObserved')is False
        and actual.get('proof',{}).get('typedRequest')==usage)
    argument=bytes.fromhex(context.get('argumentRawHex',''));load=bytes.fromhex(context.get('instructionHex',''))
    call_rva,encoded=read.get('instruction',[None,'']);call=bytes.fromhex(encoded)
    need('actual-ordinary-R8-context-and-E8-source',len(argument)==16 and argument[10:12]==bytes((17,128))
        and int.from_bytes(argument[:8],'little')==context.get('typeDefinition')
        and len(load)==7 and load[:3]==bytes.fromhex('4c8b05')
        and(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))==
            (usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec'))
        and[context.get('instructionRva'),context.get('instructionHex')]in scope.get('selectedProgram',[])
        and type(call_rva)is int and len(call)==5 and call[0]==0xe8
        and call_rva+5+int.from_bytes(call[1:],'little',signed=True)==read.get('sourceTargetRva')
        and actual.get('sourceTargetRva')==cap['valueSourceTargetRva']==read.get('sourceTargetRva')
        and actual.get('readerMethodDefinition')==cap['valueReaderMethodDefinition']==context.get('methodSpec',[None])[0]
        and tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE]))
    return dict(fieldName=read['fieldName'],typeName=TYPE,capability=CAPABILITY,readerMethodDefinition=actual['readerMethodDefinition'],
        sourceTargetRva=actual['sourceTargetRva'],managedValueTransfer=transfer,managedValueCapabilityShape=cap,
        ordinaryReferenceIdentityClaimed=False)


def derive(image,pins,*,parent_source,member_index):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.generated_managed_value_components import bind_member
    _publication_gate(image,pins);scope=parent_source['sourceScope'];read=parent_source['orderedSourceReads'][member_index]
    usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='beyondCurveValueBindings')
    child=owner.derive(image,pins,typed_request=usage,source_target=image.pe.image_base+read['sourceTargetRva'],count_limit=10000)
    binding=bind_member(parent_source,scope,read,pins,usage,child,CAPABILITY,binder=bind)
    _publication_gate(image,pins)
    return dict(schema=SCHEMA,status='validated-conditional-beyond-curve-parent-value-components',nativeInputs=pins,
        parentWrapper=parent_source['wrapperName'],binding=binding,capabilities=child['capabilities'],
        proof=dict(parentSource=parent_source,childComponent=child),parentFieldAdmitted=True,wholeOwnerAdmitted=False)
