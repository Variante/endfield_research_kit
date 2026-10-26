"""Current reference-adapter FF programs, with an exact AbilityActionData owner.

Only the registered ordinary reference pair and the selected canonical FF
route are composed. The abstract union wrapper is never instantiated or read
on this route. Reserved markers, positive unions, live formatter selection and
whole SkillData remain separate evidence requirements.
"""
from __future__ import annotations

import json

from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.il2cpp.context import type_parameter_owner
from scripts.game_data.il2cpp.formatter_composition import _vtable
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.memorypack import (
    buff_ec_profiles_native as ec, reference_adapter_sources as adapter,
    scalar_param_native as scalar,
)
from scripts.game_data.memorypack.buff_ptr_sources import _adapter_context
from scripts.game_data.memorypack.modelview_reference_sources import read_value
from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
from scripts.game_data.memorypack.reference_param_profile import derive_pair

LABEL='skillActionNullSource'
TYPE='Beyond.Gameplay.Core.AbilityAction+AbilityActionData'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack'
ADAPTER='Beyond.MemoryPack.GenericMemoryPackFormatter`2'
SAVED=['rbx','rbp','rsi','rdi','r12','r13','r14','r15']


def need(key,expected,actual):scalar.need(LABEL,key,expected,actual)


def null_programs(main_regions,main_entry,dispatch_regions,dispatch_entry,prepare):
    """Complete exact selected programs, including both normal return frames."""
    symbols=dict(main=main_entry,prepare=prepare)
    main=adapter.main(main_regions,main_entry,symbols,null=True)
    dispatch=adapter.dispatch(dispatch_regions,dispatch_entry,symbols,null=True)
    return dict(main=main,dispatch=dispatch,nullMarker=255,consumedBytes=1,
        outputBytes=8,clearedReferenceBits=64,nonvolatileRegistersRestored=SAVED,
        mainProviderCalls=0,dispatchProviderCalls=0,dispatchPrepareCalls=1,
        nullBeforeWrapperOrProvider=True,normalReturn=True,
        readerEffects=dict(currentPtr=1,bufferLength=-1,advancedCount=1,consumed=1),
        condition='Buffered FF, initialized adapter metadata, compatible stable disjoint Reader/output/frame; dispatcher selector low16=5 and callback equals registered canonical reference adapter, with normal noninterfering preparation.')


def _definition(image,owner,name):
    td=image.named_types[owner]
    method,=[m for m in image.metadata.methods_for(td) if image.metadata.string(m.name_index)==name]
    return method


def _owned(image,pointer):
    base=image.pe.image_base;family,windows,rows=ec.family(image,pointer-base)
    regions=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in windows]
    # Full families own/hash all bytes. Only selected programs are decoded by
    # the strict byte walkers below; unselected positive/cold paths may hold
    # unsupported decoder instructions and acquire no semantic admission.
    return dict(entryRva=pointer-base,family=family,codeWindows=windows,regions=regions,rows=rows)


def _call(source,offset):
    row,=[r for r in source['rows']if ec.va(r)==source['entryRva']+source['base']+offset]
    flow=control_transfer(row);need('directCall',('call',5),(flow['kind'],len(ec.raw(row))))
    return flow['target']


def _canonical_abi(image,ctx,method):
    owner=image.metadata.types[method.declaring_type]
    need('adapterInstanceVoidSlot5',(False,'void',5,2),
        (bool(method.flags&16),ctx.type_name(method.return_type),method.slot,method.parameter_count))
    scalar.ordinary(image,ctx.type_pointer(method.return_type),1,LABEL+'.void')
    _vtable(image,owner.index,5,method.index,LABEL)
    parameters=list(image.metadata.parameters_for(method));need('adapterParameterRows',2,len(parameters))
    reader,output=(image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)for p in parameters)
    need('readerByref',('MemoryPack.MemoryPackReader',b'\x11\x20',ctx.index.types['MemoryPack.MemoryPackReader'].index),
        (ctx.type_name(parameters[0].type_index),reader[10:12],int.from_bytes(reader[:8],'little')))
    need('referenceOutputByref',b'\x13\x20',output[10:12])
    parameter=type_parameter_owner(image.metadata.buf,int.from_bytes(output[:8],'little'),
        [t.generic_container_index for t in image.metadata.types],source=LABEL)
    need('outputOwnOriginalVAR',(owner.index,0),(parameter['typeIndex'],parameter['ordinal']))
    return dict(methodDefinition=method.index,declaringType=owner.index,slot=5,readerByrefRawHex=reader.hex().upper(),
        outputByrefRawHex=output.hex().upper(),outputParameter=parameter,referenceOutputBytes=8)


def derive_reference_null(image,pins,original_type,wrapper_name=None):
    """Prove one exact nominal CLASS pair and its conditional reference FF route.

    The caller joins its closed typed request and actual E8 target to the
    returned ReadValue definition/target. This helper does not infer a parent
    call, runtime MethodInfo or provider choice from the nominal name.
    """
    _publication_gate(image,pins)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);entries=GenericEntries(image)
    pair=derive_pair(image,original_type,wrapper_name)
    registration=pair['composition']['registrations'][0];wrapper_name=registration['wrapperType']
    need('selectedPair',(original_type,wrapper_name),(registration['originalType'],pair['registration']['wrapperType']))
    arguments=image.instantiations.resolve(registration['classInstantiation']).arguments
    need('closedPairArity',2,len(arguments));types=[]
    for name,argument in zip((original_type,wrapper_name),arguments):
        definitions=image.named_type_definitions.get(name,());need('uniqueNamedType:'+name,1,len(definitions))
        raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
        need('ordinaryClosedCLASS:'+name,(False,b'\x12\x00',definitions[0].index),
            (ctx.is_value_type(name),raw[10:12],int.from_bytes(raw[:8],'little')))
        types.append(dict(typeName=name,definition=definitions[0].index,flags=definitions[0].flags,rawTypeHex=raw.hex().upper()))
    method=_definition(image,ADAPTER,'Deserialize');abi=_canonical_abi(image,ctx,method)
    canonical=entries.resolve(method.index,['object','object'],[])
    observed=entries.observe(method.index,[original_type,wrapper_name],[])
    closed=entries.resolve(method.index,[original_type,wrapper_name],[])if observed else None
    if closed is not None:need('closedAdapterCanonicalPointer',canonical['pointer'],closed['pointer'])
    constructor=_definition(image,ADAPTER,'.ctor');ctor=entries.resolve(constructor.index,['object','object'],[])
    if pair['registration'].get('profile')=='inline-closed-adapter-constructor.v1':
        need('inlineConstructorCanonicalEntry',json.loads(json.dumps(ctor)),pair['registration']['canonicalConstructor'])
        need('inlineConstructorCallNotClaimed',False,pair['registration']['constructorCallExecuted'])
        need('inlineConstructorPointerAliasNotClaimed',False,pair['registration']['constructorPointerEqualityClaimed'])
    elif pair['registration'].get('profile')=='direct-closed-adapter-constructor.v1':
        need('directConstructorCanonicalEntry',json.loads(json.dumps(ctor)),pair['registration']['canonicalConstructor'])
        need('directConstructorCall',True,pair['registration']['constructorCallExecuted'])
        need('directConstructorActualEntry',ctor['pointer']-base,pair['registration']['actualCalls']['constructor'])
        need('directConstructorSourceJoin',True,pair['registration']['actualConstructorEqualsCanonical'])
    else:
        need('eagerConstructorCanonicalEntry',ctor['pointer']-base,pair['registration']['constructorThunk']['sharedTargetRva'])
    context,context_proof=_adapter_context(image,entries)
    clones=ec.clone_facts(image,pins);clone=clones['ReadValue']
    source=_owned(image,base+clone['targetRva']);source['base']=base
    symbols={role:_call(source,offset)for role,offset in (
        ('classFromType',142),('hash',199),('compare',246),('backend',438),
        ('indexed',455),('assignable',471),('dispatch',499))}
    need('actualReaderDispatch',clones['dispatchTarget'],symbols['dispatch'])
    reader_program=read_value(source['regions'],base+source['entryRva'],symbols)
    reader_method=image.metadata.methods[clone['equivalentMethod'][0]]
    reader_context=ContextSymbols(image).context(reader_method.index,is_method=True)
    provider=image.metadata.methods[reader_context['entries'][0]['methodSpec'][0]]
    provider_context=ContextSymbols(image).context(provider.index,is_method=True)
    reader_context_proof=validate_read_value_context(image,reader_context,provider_context,entries,fail=need)
    main=_owned(image,canonical['pointer']);dispatch=_owned(image,symbols['dispatch'])
    # The strict dispatch prefix below owns this direct E8. Unselected union
    # alternatives include indirect tail transfers and need no decoding here.
    dispatch['base']=base;prepare=_call(dispatch,35)
    paths=null_programs(main['regions'],canonical['pointer'],dispatch['regions'],symbols['dispatch'],prepare)
    offsets=scalar.reader_offsets(image,LABEL)
    need('readerOwnedOffsets',dict(currentPtr=80,bufferLength=48,advancedCount=64,consumed=68),offsets)
    windows={}
    for body in(main,dispatch,source):
        for window in body['codeWindows']:windows.setdefault((window['startRva'],window['endRva']),window)
    result=dict(schema='endfield.reference-adapter-null-source.v1',status='validated',nativeInputs=dict(pins),
        typeName=original_type,wrapperName=wrapper_name,typeDefinition=types[0]['definition'],contextTypeKind=18,nullAdmitted=True,
        nullMarker=255,consumedBytes=1,outputBytes=8,positiveAdmitted=False,reservedMarkersAdmitted=False,
        referenceReaderMethodDefinition=reader_method.index,referenceReaderTargetRva=clone['targetRva'],
        types=types,pair=pair,canonicalRegistration=canonical,constructorRegistration=ctor,canonicalAbi=abi,
        callbackBinding=dict(closedRegistrations=observed,closedRegistration=closed,
            canonicalTargetRva=canonical['pointer']-base,actualCallbackEqualsCanonicalRequired=True,
            closedPointerEquivalenceProved=closed is not None,
            runtimeCallbackSelectionObserved=False),
        adapterContext=context,adapterContextProof=context_proof,readerContext=reader_context,providerContext=provider_context,
        readerContextProof=reader_context_proof,readerProgram=reader_program,readerFamily=source['family'],
        mainFamily=main['family'],dispatchFamily=dispatch['family'],codeWindows=list(windows.values()),
        selectedPrograms=paths,dispatchTargetRva=symbols['dispatch']-base,prepareTargetRva=prepare-base,
        evidenceBoundary=dict(exact='Fresh eager nominal original/base-wrapper pair, ordinary reference type flags, owned generic context/byref ABI, metadata slot5 declaration, independently registered canonical erased-reference adapter entry, complete current families and selected FF programs. FF alone consumes one byte, updates all four Reader fields and clears the complete eight-byte reference; both adapter programs restore their frames/nonvolatiles before RET without wrapper/provider access. The eager constructor or reference kind alone supplies no closed Deserialize pointer equivalence.',
            conditional='Initialized coherent selected closed ReadValue/provider/adapter MethodInfos and matching canonical callback at selector5; sufficient stable disjoint Reader/source/output/frame and normal compatible helper/preparation/cache/lock/backend effects. The outer ReadValue selected transfer precedes the adapter; its provider/cache result and live runtime choice are conditional.',
            unresolved=['positive or reserved union markers','wrapper allocation or positive child grammar',
                'live formatter/cache/provider/default/override/inflation selection','refill and malformed paths','whole parent or root']))
    _publication_gate(image,pins)
    return json.loads(json.dumps(result))


def derive(image,pins):
    """The only action union admitted by this owner is AbilityActionData FF."""
    return derive_reference_null(image,pins,TYPE,WRAPPER)
