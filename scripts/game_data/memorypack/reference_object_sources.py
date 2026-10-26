"""Compose one selected reference pair with current canonical positive adapters.

The caller proves its original/wrapper grammar and GetValue semantics. This
component owns generic adapter/context/slot5/forwarder/conversion selection;
no concrete field layout follows from reference kind or a registered name.
"""
import copy
import json
import struct

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import pointer_param as pointer,reference_adapter_sources as adapter,scalar_param_native as scalar


def derive_adapter(image,pins,pair,wrapper,*,forwarder_prover=None,conversion_prover=None,wrapper_callback_prover=None):
    """Return the conditional positive reference adapter join for an exact pair.

    `pair` is the current registration/composition declaration (derive_pair).
    `wrapper` is the same uniquely selected generated wrapper inventory row.
    Optional forwarder_prover(image,pair,wrapper) supplies a dedicated exact
    owned-program proof for a different generated forwarder profile. A callable
    is required; a saved/prevalidated declaration is never accepted instead.
    The caller must prove GetValue's complete returned reference semantics;
    this helper verifies only its exact metadata ABI and actual call target.
    Optional conversion_prover(image,pair,wrapper,conversion,symbols,ordinal)
    proves a distinct selected optimized conversion from fresh owned source;
    it never replaces the nominal GetValue/interface metadata checks here.
    Optional wrapper_callback_prover(image,pair,wrapper,dispatch,symbols)
    proves an actual optimized wrapper slot path from owned dispatch bytes.
    """
    need=lambda k,e,a:scalar.need('referenceObjectSource',k,e,a)
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    original=wrapper.wrapped_type;name=wrapper.name
    need('nominal-reference-types',(False,False),(ctx.is_value_type(original),ctx.is_value_type(name)))
    model=json.loads((CONTRACTS_DIR/'model_view_state_controller_native.json').read_bytes())
    need('reference-source-build',pins,model['nativeInputs'])
    routes=copy.deepcopy(model['referenceRoutes']);routes['wrappers']=[]
    common=adapter.validate_reference_routes(image,routes,[])
    symbols={k:base+v for k,v in routes['symbolRvas'].items()}
    validate_eager_wrap_registration(image,pair['registration'],label='referenceObjectSource.pair')
    validate_registered_formatter_composition(image,pair['composition'],label='referenceObjectSource.pair')
    need('selected-pair',(original,name),(pair['registration']['originalType'],pair['registration']['wrapperType']))
    need('selected-composition',[(original,name)],[(r['originalType'],r['wrapperType'])for r in pair['composition']['registrations']])
    if forwarder_prover is not None and not callable(forwarder_prover):
        raise ValueError('referenceObjectSource.forwarder-prover-must-be-callable')
    if conversion_prover is not None and not callable(conversion_prover):
        raise ValueError('referenceObjectSource.conversion-prover-must-be-callable')
    if wrapper_callback_prover is not None and not callable(wrapper_callback_prover):
        raise ValueError('referenceObjectSource.wrapper-callback-prover-must-be-callable')
    forwarding=(pointer.registered_pair(image,pair,wrapper,label='referenceObjectSource.pair')
        if forwarder_prover is None else forwarder_prover(image,pair,wrapper))
    face,=pair['composition']['interfaces'];td=md.types[wrapper.type_definition]
    methods=pointer.methods(image,wrapper);getter=methods['GetValue']
    reader=methods.get('Deserialize');fm=md.methods[face['formatterDeserializeMethodIndex']]
    if reader is None and forwarder_prover is None:
        raise ValueError('referenceObjectSource.default-profile-requires-static-reader')
    need('selected-forwarder-owner',face['formatterDefinition'],fm.declaring_type)
    need('selected-forwarder-name','Deserialize',md.string(fm.name_index))
    reader_methods=[(fm,False)]+([]if reader is None else[(reader,True)])
    for method,static in reader_methods:
        parameters=list(md.parameters_for(method))
        need('forwarder-void-static-arity',(static,'void',2),(bool(method.flags&16),ctx.type_name(method.return_type),len(parameters)))
        scalar.ordinary(image,ctx.type_pointer(method.return_type),1,'referenceObjectSource.void')
        for p,expected,kind in zip(parameters,('MemoryPack.MemoryPackReader',name),(17,18),strict=True):
            raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)
            need('forwarder-owned-byrefs',(expected,bytes((kind,32))),(ctx.type_name(p.type_index),raw[10:12]))
    raw=image.pe.bytes_at_va(ctx.type_pointer(getter.return_type),16)
    need('reference-return-kind',True,raw[10]in(18,21))
    scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,
        (original,raw[10],True),[],'referenceObjectSource.GetValue')
    sec=md.sections['interfaceOffsets'];start=sec.offset+td.interface_offsets_start*8
    faces=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
    ordinal=faces.index((face['interfaceTypeIndex'],face['interfaceOffset']))
    conversion=pointer.owned(image,symbols['conversion']);dispatch=pointer.owned(image,symbols['dispatch'])
    convert=(adapter.conversion(conversion['regions'],symbols['conversion'],base+routes['conversionPrepareRva'],
        image.method_pointer_va(getter),ordinal=ordinal)if conversion_prover is None else
        conversion_prover(image,pair,wrapper,conversion,dict(symbols,conversionPrepare=base+routes['conversionPrepareRva']),ordinal))
    callback=(deserialize_slot(dispatch['regions'],symbols['dispatch'],prepare=symbols['prepare'],
        callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))if wrapper_callback_prover is None else
        wrapper_callback_prover(image,pair,wrapper,dispatch,symbols))
    entries=GenericEntries(image)
    constructor,=[m for m in md.methods_for(ctx.index.types['Beyond.MemoryPack.GenericMemoryPackFormatter`2'])
        if md.string(m.name_index)=='.ctor']
    ctor=entries.resolve(constructor.index,['object','object'],[])
    if pair['registration'].get('profile')=='inline-closed-adapter-constructor.v1':
        need('inline-constructor-canonical-entry',json.loads(json.dumps(ctor)),pair['registration']['canonicalConstructor'])
        need('inline-constructor-not-a-call',False,pair['registration']['constructorCallExecuted'])
        need('inline-constructor-not-pointer-alias',False,pair['registration']['constructorPointerEqualityClaimed'])
    elif pair['registration'].get('profile')in('direct-closed-adapter-constructor.v1','direct-adapter-explicit-static-checks.v1',
            'direct-reference-adapter-nonnull-skip-static-checks.v1',
            'direct-constructed-reference-adapter-nonnull-skip-static-checks.v1','direct-adapter-key-in-rcx-single-static-check.v1',
            'direct-reference-adapter-late-rbx-save.v1'):
        need('direct-constructor-canonical-entry',json.loads(json.dumps(ctor)),pair['registration']['canonicalConstructor'])
        need('direct-constructor-call',True,pair['registration']['constructorCallExecuted'])
        need('direct-constructor-actual-entry',ctor['pointer']-base,pair['registration']['actualCalls']['constructor'])
        need('direct-constructor-source-join',True,pair['registration']['actualConstructorEqualsCanonical'])
    else:
        need('explicit-legacy-constructor-profile',True,pair['registration'].get('profile')in(None,'stack-adapter-explicit-static-checks.v1'))
        need('owned-legacy-constructor-thunk',True,isinstance(pair['registration'].get('constructorThunk'),dict)
            and type(pair['registration']['constructorThunk'].get('sharedTargetRva'))is int)
        need('eager-constructor-canonical-entry',ctor['pointer']-base,pair['registration']['constructorThunk']['sharedTargetRva'])
    definition=routes['canonicalEntries']['Deserialize']['definition']
    observed=entries.observe(definition,[original,name],[])
    closed=entries.resolve(definition,[original,name],[])if observed else None
    if closed is not None:need('closed-canonical-target',symbols['main'],closed['pointer'])
    return json.loads(json.dumps(dict(schema='endfield.reference-object-adapter-source.v1',nativeInputs=pins,
        typeName=original,wrapperName=name,pair=pair,pairForwarder=forwarding,
        canonicalRoutes=routes,canonicalPrograms=common,interfaceOrdinal=ordinal,
        getterMethod=[getter.index,name,'GetValue',image.method_pointer_va(getter)-base],
        getterReturnedReferenceSemanticsProved=False,conversion=convert,wrapperCallback=callback,
        constructorRegistration=ctor,callbackBinding=dict(closedRegistrations=observed,closedRegistration=closed,
            canonicalTargetRva=symbols['main']-base,closedPointerEquivalenceProved=closed is not None,
            actualCallbackEqualsCanonicalRequired=True,runtimeSelectionObserved=False),
        condition='Initialized coherent nominal closed adapter/wrapper/interface MethodInfos and actual canonical callback plus selected wrapper callback; matching ready first cache probes, normal compatible helpers and source-disjoint effects. Caller must prove own GetValue semantics and positive wrapper grammar. No live provider/default/cache/override/inflation choice follows.')))
