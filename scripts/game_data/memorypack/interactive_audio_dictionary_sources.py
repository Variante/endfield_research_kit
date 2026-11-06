"""Interactive Audio's own enum32/pooled-string-list dictionary source.

The actual closed parent and Int32-backed enum are independent from the
canonical int/object source witness. Compatible actual source, typed helpers
and callbacks remain conditions when a closed registration is absent. This
does not infer pointer sharing or grant the list/string grammar.
"""
import json

KEY='Beyond.Gameplay.Core.InteractiveAudioComponent+EAudioTriggerState'
VALUE='System.Collections.Generic.List`1<string>'
TYPE='System.Collections.Generic.Dictionary`2<'+KEY+','+VALUE+'>'
SCHEMA='endfield.interactive-audio-dictionary-source.v2'


def need(check,condition):
    if not condition:raise ValueError('interactiveAudioDictionary.'+check)


def induction(programs,*,count_limit=4096):
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    adapted=[]
    for p in programs:
        adapted.append(dict(p,countWitness=p['count'],elementCallbacks=max(p['count'],0)))
    one,=[p for p in adapted if p['countWitness']==1];rows=one['selectedBytes']
    edges=[rows[i+1][0]for i,(a,h)in enumerate(rows[:-1])if h=='443b7c2430'and rows[i+1][1]=='0f8c']
    need('one-actual-saved-counter-backedge',len(edges)==1)
    return prove_induction([p for p in adapted if p['countWitness']>=0],initial='4533ff',increment='41ffc7',
        comparison='443b7c2430',counter='r15d',saved_count='signed Int32 header stack48; counter saved stack64 across inline key use',
        max_count=count_limit,mode_key='newDictionary',backedge_sites=edges)


def require_carrier(image,carrier):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_pointer_extent
    from scripts.game_data.memorypack import scalar_param_native as scalar
    ctx=NativeReferenceContext(image);md=image.metadata
    need('own-exact-closed-dictionary',carrier.get('name')==TYPE
        and carrier.get('definition',{}).get('name')=='System.Collections.Generic.Dictionary`2'
        and len(carrier.get('classArguments',[]))==2)
    key,value=carrier['classArguments'];kr=bytes.fromhex(key.get('rawHex',''));vr=bytes.fromhex(value.get('rawHex',''))
    td=ctx.index.types[KEY]
    need('own-enum-value17-and-reference-list21',key.get('name')==KEY and ctx.is_enum(KEY)
        and len(kr)==len(vr)==16 and kr[10:12]==bytes((17,128))and int.from_bytes(kr[:8],'little')==td.index
        and value.get('name')==VALUE and vr[10:12]==bytes((21,0)))
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    need('own-signed-Int32-enum-backing',td.generic_container_index<0 and len(fields)==1
        and md.string(fields[0].name_index)=='value__'and ctx.type_name(fields[0].type_index)=='int')
    scalar.ordinary(image,ctx.type_pointer(fields[0].type_index),8,'interactiveAudioDictionary.enumBacking')
    need('own-closed-reference-list-argument',value.get('definition',{}).get('name')=='System.Collections.Generic.List`1'
        and len(value.get('classArguments',[]))==1 and value['classArguments'][0].get('name')=='string'
        and bytes.fromhex(value['classArguments'][0].get('rawHex',''))[10:12]==bytes((14,0)))
    return dict(typeName=TYPE,keyType=KEY,keyTypeDefinition=td.index,keyUnderlying='int',keyWireBytes=4,
        valueType=VALUE,valueReferenceExtent=closed_generic_reference_pointer_extent(ctx,value['typePointerVa']))


def derive(image,pins,*,typed_request,call_target,count_limit=4096,enum_source=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data import levelscript_interactive_native as native
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack import pointer_param as pointer,levelscript_interactive_sources as paths
    from scripts.game_data.memorypack import interactive_enum_sources as enums
    _publication_gate(image,pins);base=image.pe.image_base;entries=GenericEntries(image)
    need('bounded-count-limit',type(count_limit)is int and 3<=count_limit<=4096)
    validate_typed_usage_context(image,typed_request,label='interactiveAudioDictionary.actualParent')
    bind_typed_read(image,typed_request,method_name='ReadPackable',argument=TYPE,kind=21,reference=True)
    arg,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
    carrier=ContextSymbols(image).type(arg.type_pointer_va);nominal=require_carrier(image,carrier)
    path=native.CONTRACT_PATH;raw=path.read_bytes();fact=json.loads(raw)
    need('same-selected-witness-build',fact.get('schema')==native.SCHEMA and fact.get('status')=='exact-current-build'
        and fact.get('nativeInputs')==pins)
    witness_proof=native._validate_native(image,fact)
    need('same-actual-parent-ReadPackable',call_target==base+fact['symbols']['packable'])
    declaration,=[r for r in fact['entries']if r[0]=='intDictionary']
    need('separate-int-object-witness',declaration[2:]==[['int','object'],[]])
    registered=entries.resolve(declaration[1],declaration[2],declaration[3]);body=pointer.owned(image,registered['pointer'])
    need('exact-current-physical-source',body['pointer']==base+fact['sources']['intDictionary']['entryRva'])
    symbols={k:base+v for k,v in fact['symbols'].items()}
    programs=[paths.dictionary_i32_program(body['regions'],body['pointer'],symbols,fact['readerFields'],count=n,new=True)
        for n in(-1,0,1,2,3)]
    counted=induction(programs,count_limit=count_limit)
    if enum_source is None:enum_source=enums.derive(image,pins)
    enums.validate(enum_source,pins)
    callback=enum_source['capabilities']['skill-enum-callback:'+KEY]
    enum_programs=[paths.dictionary_i32_program(body['regions'],body['pointer'],symbols,fact['readerFields'],
        count=n,new=True,key_profile='enum')for n in(-1,0,1,2,3)]
    enum_counted=induction(enum_programs,count_limit=count_limit)
    need('exact-separately-derived-enum-secondary-callback',callback.get('typeName')==KEY
        and callback.get('nativeInputs')==pins and callback.get('wireBytes')==4
        and callback.get('callbackSlot')==5
        and all(p['keyCallback']==base+callback['callbackTargetRva']
            and p['primaryCallbackMatched']is False and p['secondaryCallbackMatched']is True
            for p in enum_programs if p['count']>0))
    observations=entries.observe(declaration[1],[KEY,VALUE],[])
    need('no-contradictory-closed-entry',all(r.get('pointer')==body['pointer']for r in observations))
    need('contract-bookend',raw==path.read_bytes());_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,typeName=TYPE,keyType=KEY,valueType=VALUE,
        typedRequest=typed_request,readerMethodDefinition=typed_request['methodSpec'][0],readerTargetRva=call_target-base,
        actualSourceProved=True,keyWireBytes=4,valueManagedBytes=8,headerBytes=4,countLimit=count_limit,
        keyCallbackJoined=True,keyCallback=callback,
        sourceWitnessClassArguments=['int','object'],closedRegistrationObservations=observations,
        closedPointerEquivalenceProved=bool(observations),valueGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(closedCarrier=carrier,nominalIdentity=nominal,witnessRegistration=registered,
            sourceWindows=body['windows'],sourceRegions=[[a-base,b.hex()]for a,b in body['regions']],
            programs=programs,induction=counted,enumPrograms=enum_programs,enumInduction=enum_counted,
            enumSource=enum_source,readerOffsets=fact['readerFields'],
            symbolRvas=fact['symbols'],witnessProof=witness_proof,dictionaryContext=fact['dictionaryContext']),
        evidenceBoundary=dict(exact='Own actual closed enum/list parent, signed Int32 backing, independently authenticated int/object byte witness and complete counted key4/reference8 source paths.',
            conditional=__doc__,unresolved=['independent value list/string callbacks','live provider/formatter/inflation selection',
                'enclosing parent field and whole-owner EOF','runtime audio playback']))))
