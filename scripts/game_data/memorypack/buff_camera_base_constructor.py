"""Static inherited ctor context and a folded registered closed return entry.

The complete ListFormatter class context names inherited constructor slot
seven and declared parent slot eight. Parent MemoryPackFormatter<List<T>> and
constructor argument pointers equal the List type tied to the reciprocal
ListFormatter parameter; this is static identity, not live slot population.
generic_entries retains folded aliases, null pointers and duplicate rows;
the strict resolver still refuses folded identity. The shared Object entry
starts RET 0: its closed program preserves flags/general registers, writes no
data and pops only the ordinary readable return address. Neither unique named
body nor physical extent beyond RET follows. The cold indirect target has not
been observed equal to this pointer. Inflation, runtime geometry/population,
other effects and positive camera list/root admission remain separate.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts
from . import buff_camera_list_constructor as constructor_owner
from .list_formatter_base_context import validate_list_formatter_base_context,validate_closed_zero_pop_return

CONTRACT_PATH=CONTRACTS_DIR/'buff_camera_base_constructor_native.json'
SCHEMA='endfield.buff-camera-base-constructor-native-contract.v1'
LABEL='buffCameraBaseConstructor'
def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'actualColdTargetMatchesEntryProved':False,
        'positiveListGrammarProved':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}


def _validate_image(image,c):
    def fail(check,expected,actual,**details):
        raise ValueError(json.dumps({'validator':LABEL,'check':check,'source':CONTRACT_PATH.as_posix(),
            'expected':str(expected)[:1000],'actual':str(actual)[:1000],'details':details}))
    ctor,_=read_reviewed_contract(CONTRACTS_DIR/c['constructorContract'],schema=constructor_owner.SCHEMA,status='exact-current-build',label=LABEL)
    if ctor['nativeInputs']!=c['nativeInputs']:fail('same-constructor-build',c['nativeInputs'],ctor['nativeInputs'])
    current_constructor=constructor_owner._validate_image(image,ctor)
    context=c['classContext'];validate_generic_contexts(image,[context],label=LABEL)
    if image.metadata.methods[ctor['sharedConstructor']['method'][0]].declaring_type!=context['definition']:
        fail('caller-constructor-class-context','same actual ListFormatter constructor owner',context['definition'])
    entries=GenericEntries(image)
    base_context=validate_list_formatter_base_context(image,context,entries,fail=fail)
    chosen=c['selectedObjectBaseConstructor']
    if chosen['methodDefinition']!=base_context['baseConstructorDefinition'] or chosen['classArguments']!=['object'] or chosen['methodArguments']!=[]:
        fail('base-object-observation-selection','independent inherited ctor with Object argument',chosen)
    observations=entries.observe(chosen['methodDefinition'],chosen['classArguments'],chosen['methodArguments'])
    if len(observations)!=1 or not observations[0]['pointer']:
        fail('one-observed-nonnull-base-row',1,len(observations))
    observed=observations[0]
    if (observed['methodSpecIndex']!=chosen['methodSpecIndex']
            or list(entries.specs[observed['methodSpecIndex']])!=chosen['methodSpec']
            or observed['registration']['indices']!=chosen['indices']
            or observed['pointer']-image.pe.image_base!=c['entryProgram']['startRva']):
        fail('selected-base-registration-row',chosen,observed)
    if observed['uniqueMethodDefinitionForPointer'] or chosen['methodDefinition'] not in observed['methodDefinitionIndices']:
        fail('folded-observation-boundary','multiple method definitions at this pointer',observed['methodDefinitionIndices'])
    try:entries.resolve(chosen['methodDefinition'],chosen['classArguments'],chosen['methodArguments'])
    except ValueError as error:
        if not str(error).startswith('generic entry: folded method definitions'):raise
    else:fail('strict-resolver-refusal','folded method definitions refused','accepted')
    program=c['entryProgram'];image.check_windows([program],label=LABEL)
    raw=image.pe.bytes_at_va(image.pe.image_base+program['startRva'],program['endRva']-program['startRva'])
    if raw.hex().upper()!=program['rawHex']:fail('entry-return-bytes',program['rawHex'],raw.hex())
    closed_return=validate_closed_zero_pop_return(raw)
    return {'staticBaseContext':base_context,'cameraConstructorControl':current_constructor,
        'observedBaseObjectRegistration':observed,'conditionalClosedEntryReturn':closed_return,
        'strictResolverStillRefusesFoldedIdentity':True,'runtimeSlotStrideProvedHere':False,
        'runtimeContextPopulationOrColdSelectionObserved':False}


def validate_current_native_contract(*,gameassembly:Path,metadata:Path):
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL);pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return _skip(gate.status,gate.detail,pins)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():
        if not unity.is_file():return False
        with unity.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches():return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll missing or mismatched',pins)
    summary=_validate_image(open_native_image(gate.gameassembly,gate.metadata),c)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not unity_matches():return _skip(after.status if after.status!='validated' else 'mismatched','Selected native inputs changed',pins)
    return {'status':'validated','nativeInputs':pins,'summary':summary,'actualColdTargetMatchesEntryProved':False,
        'positiveListGrammarProved':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'evidenceBoundary':c['evidenceBoundary']}
