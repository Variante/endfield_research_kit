"""Current UInt32/reference dictionaries under an exact source witness.

The uint/object formatter owns the native byte program. A separately closed
parent supplies its actual UInt32/CLASS arguments, ReadPackable request and
target. Missing closed registration is retained as a selection condition;
neither a reference name nor a four-byte key establishes pointer sharing.
"""
import json

SCHEMA='endfield.uint-reference-dictionary-source.v1'


def require_carrier(carrier,*,value_type,value_index):
    if (not isinstance(carrier,dict)
            or carrier.get('name')!='System.Collections.Generic.Dictionary`2<uint,'+value_type+'>'
            or carrier.get('definition',{}).get('name')!='System.Collections.Generic.Dictionary`2'
            or not isinstance(carrier.get('classArguments'),list)or len(carrier['classArguments'])!=2
            or type(value_index)is not int or value_index<0):
        raise ValueError('uintReferenceDictionary.exact-closed-dictionary')
    key,value=carrier['classArguments']
    try:kr=bytes.fromhex(key['rawHex']);vr=bytes.fromhex(value['rawHex'])
    except(KeyError,TypeError,ValueError)as error:
        raise ValueError('uintReferenceDictionary.exact-owned-carrier-bytes')from error
    if (len(kr)!=16 or len(vr)!=16 or key.get('name')!='uint'or kr[10:12]!=b'\x09\x80'
            or value.get('name')!=value_type or vr[10:12]!=b'\x12\x00'
            or int.from_bytes(vr[:8],'little')!=value_index):
        raise ValueError('uintReferenceDictionary.UInt32-and-owned-CLASS-arguments')
    return dict(typeName=carrier['name'],keyType='uint',keyRawKind=9,keyValueType=True,
        valueType=value_type,valueRawKind=18,valueValueType=False)


def require_observations(observations,*,pointer,label):
    if not isinstance(observations,list):raise ValueError('uintReferenceDictionary.registration-observations:'+label)
    for row in observations:
        if not isinstance(row,dict)or row.get('pointer')!=pointer:
            raise ValueError('uintReferenceDictionary.contradictory-closed-source:'+label)
    return bool(observations)


def capability(*,type_name,value_type,count_limit,reader_definition,reader_target,closed_pointer_equivalence):
    if (type(count_limit)is not int or not 1<=count_limit<=16384
            or type(reader_definition)is not int or reader_definition<0
            or type(reader_target)is not int or reader_target<=0
            or type(closed_pointer_equivalence)is not bool
            or type_name!='System.Collections.Generic.Dictionary`2<uint,'+value_type+'>'):
        raise ValueError('uintReferenceDictionary.finite-capability-identity')
    return dict(typeName=type_name,keyType='uint',valueType=value_type,
        keyRawKind=9,keyValueType=True,valueRawKind=18,valueValueType=False,
        headerBytes=4,keyWireBytes=4,managedKeyBytes=4,managedValueBytes=8,
        countRange=[-1,count_limit],countLimit=count_limit,
        sourceWitnessClassArguments=['uint','object'],nullable=True,positiveCountsAdmitted=True,
        initiallyNullOutputRequired=True,actualCallbackEqualsCanonicalRequired=True,
        typedConstructorAndHelperCompatibilityRequired=True,
        actualKeyCallbackEqualsProvedUInt32Required=True,actualValueCallbackEqualsProvedChildRequired=True,
        unsignedKeySourceProved=True,closedPointerEquivalenceProved=closed_pointer_equivalence,
        actualCallbackSelectionObserved=False,providerFactorySelectionObserved=False,
        packableReaderMethodDefinition=reader_definition,packableReaderTargetRva=reader_target,
        valueGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def derive(image,pins,*,typed_request,call_target,value_type,count_limit=4096):
    from scripts.game_data import levelscript_interactive_native as native
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols,validate_claims
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack import word32_reference_dictionary_programs as programs
    need=lambda k,e,a:scalar.need('uintReferenceDictionary',k,e,a)
    _publication_gate(image,pins)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);entries=GenericEntries(image);cs=ContextSymbols(image)
    type_name='System.Collections.Generic.Dictionary`2<uint,'+value_type+'>'
    if type(count_limit)is not int or not 1<=count_limit<=16384:
        raise ValueError('uintReferenceDictionary.finite-count-limit')
    bind_typed_read(image,typed_request,method_name='ReadPackable',argument=type_name,kind=21,reference=True)
    argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
    carrier=cs.type(argument.type_pointer_va)
    identity=require_carrier(carrier,value_type=value_type,value_index=ctx.index.types[value_type].index)
    need('ordinary-CLASS-value',False,ctx.is_value_type(value_type))
    path=native.CONTRACT_PATH;raw=path.read_bytes();fact=json.loads(raw)
    need('source-witness-contract',(native.SCHEMA,'exact-current-build',pins),
        (fact.get('schema'),fact.get('status'),fact.get('nativeInputs')))
    fresh=native._validate_native(image,fact)
    validate_claims(fact['programs'],fresh,label='uintReferenceDictionary.current-witness-programs')
    validate_claims(fresh,fact['programs'],label='uintReferenceDictionary.complete-witness-declaration')
    need('actual-nominal-ReadPackable-target',base+fact['symbols']['packable'],call_target)
    selected=next(row for row in fact['entries']if row[0]=='uintDictionary')
    need('source-witness-arguments',(['uint','object'],[]),(selected[2],selected[3]))
    witness=entries.resolve(selected[1],selected[2],selected[3])
    body=owned(image,witness['pointer'])
    need('current-owned-witness-entry',base+fact['sources']['uintDictionary']['entryRva'],body['pointer'])
    s={k:base+v for k,v in fact['symbols'].items()}
    symbols=dict(s,indexed=s['context'],constructor=s['dictionaryConstructor'],
        keyDispatch=s['keyDispatcher'],valueDispatch=s['referenceDispatcher'])
    paths=[programs.program(body['regions'],body['pointer'],symbols,count=n)for n in(-1,0,1,2,3)]
    induction=programs.induction(paths,count_limit=count_limit)
    observations=entries.observe(selected[1],['uint',value_type],[])
    equivalent=require_observations(observations,pointer=witness['pointer'],label='Deserialize')
    # Missing closed ctor/Add rows do not establish those actual pointers.
    # The exact uint/object bodies and open contexts have just been freshly
    # proved; typed helper compatibility remains an outer selection condition.
    helper_observations={}
    for role,symbol in(('dictionaryConstructor','dictionaryConstructor'),('dictionaryAdd','add')):
        declaration=next(row for row in fact['entries']if row[0]==role)
        closed=entries.observe(declaration[1],['uint',value_type],[])
        require_observations(closed,pointer=s[symbol],label=role)
        helper_observations[role]=closed
    key=next(row for row in fact['entries']if row[0]=='uintCallback')
    need('exact-unsigned-callback-instantiation',(['uint'],[]),(key[2],key[3]))
    key_entry=entries.resolve(key[1],key[2],key[3])
    need('actual-owned-UInt32-callback',s['callback'],key_entry['pointer'])
    needed=('header','uintDispatch','uintCallback','keyProvider','valueProvider','readValue',
        'keyBackendForward','dictionaryConstructor','dictionaryAdd','barrier','dictionaryContext',
        'readValueContext','referenceCore')
    cap=capability(type_name=type_name,value_type=value_type,count_limit=count_limit,
        reader_definition=typed_request['methodSpec'][0],reader_target=call_target-base,
        closed_pointer_equivalence=equivalent)
    need('source-declaration-bookend',raw,path.read_bytes());_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-uint-reference-dictionary',
        nativeInputs=pins,typeName=type_name,typedRequest=typed_request,callTargetRva=call_target-base,
        closedCarrier=carrier,nominalIdentity=identity,sourceWitness=witness,
        sourceWitnessClassArguments=['uint','object'],closedRegistrationObservations=observations,
        closedHelperObservations=helper_observations,keyCallback=key_entry,
        sourceRegions=[dict(start=at,hex=data.hex())for at,data in body['regions']],
        sourceWindows=body['windows'],sourcePrograms=paths,loopInduction=induction,
        symbolRvas={k:v-base for k,v in symbols.items()},
        witnessProof={name:fresh[name]for name in needed},
        witnessSources={name:fact['sources'][name]for name in('uintDictionary','header','uintDispatch',
            'uintCallback','keyProvider','valueProvider','readValue','keyBackendForward',
            'dictionaryConstructor','dictionaryAdd','barrier')},
        dictionaryContext=fact['dictionaryContext'],capability=cap,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Fresh UInt32 callback, uint/object dictionary source, signed count/header and repeated key4/reference8/Add loop; separately closed UInt32/CLASS parent identity and actual ReadPackable target.',
            conditional='Initially null output; selected callback equals the proved uint/object source with coherent closed contexts and typed constructor/Add/provider compatibility, normal helpers and disabled collector. Each actual value callback must match its independently proved child.',
            unresolved='Live provider/formatter/helper selection and any missing closed pointer equivalence; value grammar and outer field/owner EOF.'))))
