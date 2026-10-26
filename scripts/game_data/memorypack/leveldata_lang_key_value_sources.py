"""Actual LangKey ReadValue ABI joined to its dedicated two-reference source.

This component does not replace LangKey with a generic managed16 profile.
The reviewed nominal owner proves its two string lanes, concrete wrapper and
GetValue, canonical value adapter and full selected hidden16 reader clone.
Each enclosing caller still owns its actual E8, local16, field/setter/frame
and separate wire-child capability. No runtime provider choice is observed.
"""
import json

from scripts.game_data.memorypack import scalar_param_native as scalar

TYPE='Beyond.LangKey'
LABEL='storyLangKeyValueSource'


def derive_read_value(image,pins,*,typed_request,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data import levelscript_nominal_key_param_native as native
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    need=lambda k,e,a:scalar.need(LABEL,k,e,a)
    _publication_gate(image,pins);base=image.pe.image_base
    need('literal-selected-source-target',True,type(source_target)is int and source_target>base)
    path=native.CONTRACT_PATH;raw=path.read_bytes();fact=json.loads(raw)
    need('dedicated-two-reference-contract',(native.SCHEMA,'exact-current-build',['Param<LangKey>'],pins),
        (fact.get('schema'),fact.get('status'),fact.get('codecKinds'),fact.get('nativeInputs')))
    need('dedicated-layout',dict(parentMemberCount=4,keyMemberCount=1,keyName='key',stringEncoding='int32-pool-index',
        managedKeyBytes=16,serializedPositiveKeyBytes=5,wholeOwnerAdmitted=False,nonserializedRawText=True),fact['layout'])
    dependencies=[CONTRACTS_DIR/name for name in('memorypack_reader_clones_native.json','memorypack_pooled_string_reader_native.json')]
    before=[p.read_bytes()for p in dependencies]
    validate_typed_usage_context(image,typed_request,label=LABEL+'.actualCaller')
    binding=bind_typed_read(image,typed_request,method_name='ReadValue',argument=TYPE,kind=17)
    raw_argument=image.pe.bytes_at_va(binding['argumentPointer'],16)
    need('exact-nominal-value-kind',b'\x11\x80',raw_argument[10:12])
    need('same-actual-ReadValue-definition',fact['typedValueUsage']['methodSpec'][0],typed_request['methodSpec'][0])
    need('same-actual-hidden16-source',base+fact['symbols']['value16'],source_target)
    native._validate_native(image,fact)
    _publication_gate(image,pins)
    need('dedicated-declaration-bookend',raw,path.read_bytes())
    need('reader-pool-dependency-bookend',before,[p.read_bytes()for p in dependencies])
    return json.loads(json.dumps(dict(schema='endfield.story-lang-key-value-source.v1',status='validated-conditional-source',
        nativeInputs=pins,typeName=TYPE,managedBytes=16,resultAbi='hidden-local',
        readerMethodDefinition=typed_request['methodSpec'][0],sourceTargetRva=source_target-base,
        actualSourceProved=True,referenceLaneOffsets=[0,8],wireGrammarAdmitted=False,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,actualCallbackEqualsProvedChildRequired=True,
        proof=dict(typedRequest=typed_request,typedReadBinding=binding,sourceContract=path.name,
            dedicatedLayout=fact['layout'],actualSourceTargetRva=fact['symbols']['value16'],
            methods=fact['methods'],programs=fact['programs'],compositions=fact['compositions'],
            wideEntries=fact['wideEntries'],adapterContext=fact['adapterContext'],
            interfaceOrdinal=fact['interfaceOrdinal'],sourceSymbols=fact['symbols'],adapterSymbols=fact['wideSymbols']),
        evidenceBoundary=dict(exact='Fresh actual ReadValue<LangKey> MethodSpec, exact value17/128 carrier, dedicated nominal two-reference managed16 source and complete current reviewed hidden16 source/adapter/GetValue joins.',
            conditional=__doc__,unresolved=['actual enclosing local/setter/frame','independent enclosing wire-child admission',
                'live provider/override/default selection','whole owner/physical EOF']))))
