"""Conditional physical Sequence output join for the TickInterval field.

Reuses independently owned caller, ReadValue, concrete Sequence formatter and
array programs on one current native image. No named physical helper identity,
runtime provider/context selection, action callback cursor equality, complete
TickInterval wire grammar or enclosing action/list/root is claimed.
"""
from __future__ import annotations
import hashlib
import json
import struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import buff_tick_interval_sources as sources
from scripts.game_data.memorypack import buff_timeline_read_value as read_value
from scripts.game_data.memorypack import buff_sequence_array_source as arrays
from scripts.game_data.memorypack import buffered_owned_sources as buffered
from scripts.game_data.memorypack import setter_output_sources as setters
from scripts.game_data.memorypack import utf8_source_helper as strings
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_transfer

LABEL='buffTickIntervalComposition'
SCOPE='conditional-tick-source-helper-and-sequence-output-composition-only'


def _fail(check,expected,actual):
    error=CensusGateError(f'{LABEL}.{check}',source=sources.CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,scope=SCOPE)
    error.args=(json.dumps(error.diagnostic,sort_keys=True),)
    raise error


def _contracts():
    contracts={'source':sources._contract(),'candidate':sources.candidate._contract(),
        'readValue':read_value._contract(),'array':arrays._contract()}
    contracts['primitive'],_=read_reviewed_contract(CONTRACTS_DIR/'buff_pick_target_action_native.json',
        schema='endfield.buff-pick-target-action-native-contract.v1',status='exact-current-build',label=LABEL)
    contracts['single'],_=read_reviewed_contract(CONTRACTS_DIR/'buff_selector_postprocessors_native.json',
        schema='endfield.buff-selector-postprocessors-native-contract.v3',status='exact-current-build',label=LABEL)
    contracts['string']=strings._contract()
    pins=contracts['source']['nativeInputs']
    if any(c['nativeInputs']!=pins for c in contracts.values()):
        _fail('selected-dependency-build','all independently reviewed dependencies describe the same build',
            {name:c['nativeInputs'] for name,c in contracts.items()})
    return contracts


def _primitive_wire_profile(image,c):
    """Bind actual primitive callers to independently checked buffered sources."""
    primitive=c['primitive'];source=c['source'];fields=source['fields'];offsets=primitive['readerFieldsUnboxedOffsets']
    header=buffered.validate_object_header_source(image,primitive['objectHeader'],offsets,fail=_fail)
    if source['symbols']['header']!=primitive['objectHeader']['window']['startRva']:
        _fail('actual-parent-header-entry',primitive['objectHeader']['window']['startRva'],source['symbols']['header'])
    buffered.validate_int32_source(image,primitive['int32Source'],offsets,fail=_fail)
    setters.validate_primitive_source(image,{'codeWindows':[primitive['byteSource']['window']]},
        primitive['byteSource']['member'],fail=_fail)
    for f in fields:
        expected=(primitive['byteSource']['window']['startRva'] if f['readKind']=='bool-byte'
            else primitive['int32Source']['window']['startRva'] if f['readKind']=='scalar32' else None)
        if expected is not None and f['readerEntryRva']!=expected:
            _fail('actual-primitive-parent-callee',expected,f)
    singles=[(record,m) for record in c['single']['records'].values() for m in record['members']
        if m.get('primitiveSource',{}).get('mode')=='single-return']
    float_fields=[f for f in fields if f['readKind']=='float32-bits']
    if len(float_fields)!=1 or len(singles)!=1:
        _fail('one-current-single-source','one independently declared Single program and parent field',[len(singles),len(float_fields)])
    record,member=singles[0];field=float_fields[0]
    single_source=json.loads((CONTRACTS_DIR/record['sourceContract']).read_bytes())
    if (field['readerEntryRva']!=member['sourceCall']['targetRva']
            or field['declaredType']!='float' or field['mode']!='single-return'):
        _fail('actual-single-parent-callee',member['sourceCall'],field)
    if not any(w['startRva']==field['readerEntryRva'] for w in single_source['codeWindows']):
        _fail('owned-single-source-window',field['readerEntryRva'],
            [w['startRva'] for w in single_source['codeWindows']])
    setters.validate_primitive_source(image,single_source,member,fail=_fail)
    string_fields=[f for f in fields if f['readKind']=='byte-payload']
    if len(string_fields)!=1 or string_fields[0]['declaredType']!='string':
        _fail('one-current-string-field','one metadata-owned string field',string_fields)
    text=strings.validate_current_native_contract(gameassembly=image.gameassembly,metadata=image.metadata_path)
    if (text.get('status')!='validated' or text.get('nativeInputs')!=c['source']['nativeInputs']
            or string_fields[0]['readerEntryRva'] not in text.get('sourceHelpers',[])):
        _fail('actual-string-parent-callee','current independently checked UTF-8 helper',text)
    return {'objectHeader':header,'stringSource':text,
        'primitiveFields':[{'fieldName':f['fieldName'],'readKind':f['readKind'],
            'wireWidth':1 if f['readKind']=='bool-byte' else 4,
            'returnRegister':'al' if f['readKind']=='bool-byte' else 'xmm0' if f['readKind']=='float32-bits' else 'eax'}
            for f in fields if f['readKind'] in ('bool-byte','scalar32','float32-bits')],
        'samePhysicalPrimitiveHelpersAsOriginalParentProved':True,
        'selectedBufferedPrimitiveWireRepresentationsProved':True,
        'singleLow32BitSourceAndSetterTransferProved':True,
        'condition':'Current byref Reader layout, selected sufficiently buffered normal paths, valid disjoint stable source/frame and bounded counters; primitive refill/error effects and actual execution are not observed.'}


def derive_parent_join(c,source_result,transfer,array_result,*,image_base):
    """Join the actual complete caller transfer to the proved helper and child.

    The native context itself is authenticated independently by _validate_image.
    Supplied summaries must be the original current validator returns.
    """
    source=c['source'];candidate=c['candidate'];value=c['readValue']
    fields=[f for f in source['fields'] if f['fieldName']=='actionOnTick']
    if len(fields)!=1:_fail('one-current-sequence-field','one current actionOnTick field',fields)
    field=fields[0];ordinal=field['memberIndex']
    contexts=[row for row in candidate['nestedContexts'] if row['memberIndex']==ordinal]
    if (len(contexts)!=1 or field['mode']!='reference-return' or field['contextBefore'] is not True
            or field['declaredType']!='Beyond.Gameplay.Core.SequenceActionData'
            or contexts[0]['typeName']!=field['declaredType']
            or field['declaredType']!=array_result.get('originalType')
            or field['readerEntryRva']!=value['calledEntryRva']
            or value['programs']['readValue']['program'][0][0]!=value['calledEntryRva']
            or contexts[0]['methodSpec'][:2]!=[value['readValueContext']['definition'],-1]):
        _fail('actual-closed-child-and-physical-entry','same closed Sequence type and actual ReadValue entry',field)
    if (source_result.get('completeConditionalSourceOutputFlowsProved') is not True
            or source_result.get('currentConcreteMetadataSlotFiveJoined') is not True
            or source_result.get('fieldsForwardedToOwnedData')!=len(source['fields'])):
        _fail('complete-parent-source-output','current complete owned caller/setter/formatter flow',source_result)
    caller=source_result.get('caller',{});joins=caller.get('fieldTransfers',[])
    if (len(joins)!=len(source['fields']) or joins[ordinal].get('fieldName')!=field['fieldName']
            or joins[ordinal].get('mode')!=field['mode']
            or int(joins[ordinal]['sourceCall']['va'],16)-image_base!=field['sourceCallsiteRva']
            or int(joins[ordinal]['contextLoad']['va'],16)-image_base!=contexts[0]['instructionRva']):
        _fail('actual-original-parent-callsite','same independently checked source call and context load',field)
    if (transfer.get('entryRva')!=value['calledEntryRva']
            or transfer.get('sameReaderForwarded') is not True
            or transfer.get('sameLocalOutputReturned') is not True
            or transfer.get('zeroInitializedOutputBits')!=64
            or transfer.get('returnRegister')!='rax' or transfer.get('formatterSlot')!=5
            or transfer.get('completeReturnProved') is not True
            or transfer.get('directReaderCursorStores')!=0):
        _fail('complete-physical-child-return','same Reader, full reference output and complete return',transfer)
    if (array_result.get('originalType')!=field['declaredType']
            or array_result.get('elementType')!='Beyond.Gameplay.Core.AbilityAction+AbilityActionData'
            or array_result.get('physicalFormatterProviderReturn')!='proved-conditional'
            or array_result.get('completeSourcePrograms',{}).get('completeSelectedReturns') is not True):
        _fail('concrete-sequence-array-source','current complete independently proved selected Sequence paths',array_result)
    return {'fieldName':field['fieldName'],'memberIndex':ordinal,'declaredType':field['declaredType'],
        'ownedDataField':{'owner':field['fieldOwner'],'offset':field['fieldOffset']},
        'physicalReadValueEntryRva':value['calledEntryRva'],
        'completeConditionalSequenceResultToOwnedParentFieldProved':True,
        'sameReaderAndFullChildReferenceOutputReturned':True,
        'selectedSequenceArraySourcePathsProved':True,
        'sequenceActionCallbackCursorEqualityProved':False,'tickPrimitiveWireCompositionProved':False,
        'completeTickStoredGrammarAdmitted':False,'runtimeProviderOrContextSelectionObserved':False,
        'namedPhysicalHelperIdentity':'unresolved'}


def _validate_image(image,c):
    parent=sources._validate_image(image,c['source'])
    primitives=_primitive_wire_profile(image,c)
    # Array validation independently re-proves the shared ReadValue/context,
    # concrete Sequence adapter/getter and selected complete array programs.
    array=arrays._validate_image(image,c['array'])
    transfer=validate_read_value_transfer(image,c['readValue']['programs']['readValue'],
        c['readValue']['calls'],fail=_fail)
    join=derive_parent_join(c,parent,transfer,array,image_base=image.pe.image_base)
    field=c['source']['fields'][join['memberIndex']]
    context=next(row for row in c['candidate']['nestedContexts'] if row['memberIndex']==field['memberIndex'])
    cell,raw=image.nested_usage_cell(context,label=LABEL)
    spec_index=method_spec_usage_index(raw,image.registration['methodSpecsCount'],source=str(image.gameassembly),offset=cell)
    entries=GenericEntries(image);spec=entries.specs[spec_index]
    if list(spec)!=context['methodSpec'] or spec[0]!=c['readValue']['readValueContext']['definition']:
        _fail('actual-owned-read-value-definition',context,list(spec))
    method=image.metadata.methods[spec[0]]
    if (image.type_name(method.declaring_type)!='MemoryPack.MemoryPackReader'
            or image.metadata.string(method.name_index)!='ReadValue' or method.flags&0x10
            or method.parameter_count):_fail('owned-declared-read-value-overload','instance value-return Reader.ReadValue<T>()',spec)
    argument=image.instantiations.resolve(spec[2]).arguments
    if len(argument)!=1 or argument[0].raw_type_record_hex.upper()!=context['argumentRawHex'].upper():
        _fail('closed-current-sequence-argument',context,argument)
    argument_raw=bytes.fromhex(argument[0].raw_type_record_hex)
    if (len(argument_raw)!=16 or argument_raw[10:12]!=b'\x12\0'
            or int.from_bytes(argument_raw[:8],'little')!=context['typeDefinition']
            or image.type_name(context['typeDefinition'])!=field['declaredType']):
        _fail('closed-argument-current-definition',field['declaredType'],context)
    registrations=[list(row) for row in struct.iter_unpack('<iiii',entries.table) if row[0]==spec_index]
    return {'parentSource':parent,'primitiveWireProfile':primitives,'physicalReadValueTransfer':transfer,'sequenceArraySource':array,
        'parentSequenceJoin':join,'currentClosedUsage':{'methodDefinition':spec[0],'methodSpecIndex':spec_index,
            'typeDefinition':context['typeDefinition'],'compiledRegistrationRows':registrations,
            'actualClosedRuntimeInvocationObserved':False,'runtimeInflationObserved':False},
        'completeTickStoredGrammarAdmitted':False,'runtimeMeaningExact':False}


def validate_current_native_contract(*,gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contracts();pins=c['source']['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins,'scope':SCOPE}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def matches():
        if not unity.is_file():return False
        with unity.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest().upper()==pins['UnityPlayer.dll']
    if not matches():return {'status':'mismatched' if unity.is_file() else 'missing','detail':'UnityPlayer.dll missing or mismatched','nativeInputs':pins,'scope':SCOPE}
    try:summary=_validate_image(open_native_image(gate.gameassembly,gate.metadata),c)
    except (ValueError,KeyError,IndexError) as error:
        if isinstance(error,CensusGateError):raise
        _fail('complete-sequence-parent-composition','current owned caller, physical helper and concrete Sequence output join',str(error))
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not matches():
        return {'status':after.status if after.status!='validated' else 'mismatched','detail':'native inputs changed during Sequence composition','nativeInputs':pins,'scope':SCOPE}
    return {'status':'validated','nativeInputs':pins,'scope':SCOPE,'summary':summary,
        'wholeActionAdmitted':False,'positiveListAdmitted':False,'wholeRootAdmitted':False,'runtimeMeaningExact':False,
        'evidenceBoundary':{'direct':'Current complete conditional caller and owned setters carry the actual physical ReadValue output to the named Sequence field; same Reader, full reference return, current concrete Sequence adapter/getter and selected array paths are independently checked.',
            'conditional':'Compatible initialized closed contexts, normal ABI-preserving noninterfering calls, selected default formatter and matching concrete reference wrapper/output. Current registrations do not establish runtime context/provider choice or observed execution.',
            'unresolved':'Recursive action callback native cursor equality, complete TickInterval stored parent and enclosing positive list/root acceptance, actual tick scheduling/effects and named physical helper identity.'}}
