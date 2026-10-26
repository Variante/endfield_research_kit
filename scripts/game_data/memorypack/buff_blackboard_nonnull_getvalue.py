"""Current matching-Try nonnull public GetValue and static logger identities.

The logger's stored string/string MethodSpec has no AOT registration row. Its
actual call target is independently registered for object/object under the
same definition; no live context or logger effect follows from that join.
"""
from __future__ import annotations
import json
import struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import generic_method_candidates,unresolved_usage_index,method_parameter_owner
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import _vtable
from scripts.game_data.memorypack import buff_blackboard_double_lookup as lookup_owner
from scripts.game_data.memorypack import blackboard_nonnull_getvalue as control
from scripts.game_data.memorypack.closed_scalar_consumers import signature
from scripts.game_data.memorypack.inherited_reference_sources import _type_row
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError,_fingerprint,_package_import_closure

LABEL='buffBlackboardNonNullGetValue'
CONTRACT_PATH=CONTRACTS_DIR/'memorypack_blackboard_nonnull_getvalue_native.json'

def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.memorypack-blackboard-nonnull-getvalue-native-contract.v1',status='exact-current-build',label=LABEL)
    if c.get('mode')!=control.MODE:raise ValueError(LABEL+'.contract:mode')
    return c

def _fail(check,expected,actual):
    error=CensusGateError(LABEL+'.'+check,source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,record='Beyond.Blackboard+BlackboardDouble.GetValue')
    error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error

def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'wholeActionAdmitted':False,'wholeRootAdmitted':False}

def _logger(image,c,*,fail):
    method=c['methods']['missingLogger']
    if method[1:3]!=['Beyond.DLogger','LogError']:fail('nonnull-public-logger-definition','actual DLogger.LogError',method)
    image.validate_method_row(method[:3],label=LABEL);m=image.metadata.methods[method[0]]
    types=[_type_row(image,m.return_type)]+[_type_row(image,p.type_index) for p in image.metadata.parameters_for(m)]
    expected=[(1,'void'),(17,'Beyond.ELogChannel'),(14,'string')]
    if (not m.flags&0x10 or m.generic_container_index<0 or len(types)!=5
            or [(r['kind'],r['name']) for r in types[:3]]!=expected
            or any(bytes.fromhex(r['rawHex'])[11]&0x20 for r in types)):
        fail('nonnull-public-logger-signature','static void(channel, string, owned MVAR0, owned MVAR1)',types)
    containers=[m.generic_container_index for m in image.metadata.methods]
    for ordinal,r in enumerate(types[3:]):
        if r['kind']!=30:fail('nonnull-public-logger-mvar',ordinal,r)
        index=int.from_bytes(bytes.fromhex(r['rawHex'])[:8],'little')
        identity=method_parameter_owner(image.metadata.buf,index,containers,source=LABEL)
        if (identity['methodIndex']!=method[0] or identity['ordinal']!=ordinal
                or list(struct.unpack_from('<iiii',bytes.fromhex(identity['containerRawHex'])))[:3]!=[method[0],2,1]):
            fail('nonnull-public-logger-mvar-owner',[method[0],ordinal],identity)
    entries=GenericEntries(image);u=c['loggerContextUsage'];cell=image.pe.image_base+u['usageCellRva']
    raw=image.pe.bytes_at_va(cell,8)
    if raw.hex().upper()!=u['usageRawHex'] or u['usageCellRva']!=c['globalCells']['loggerContext']:
        fail('nonnull-public-logger-usage-cell',u,raw.hex().upper())
    index=unresolved_usage_index(raw,len(entries.specs),tag=6,source=str(image.gameassembly),offset=cell)
    if index!=u['methodSpecIndex'] or list(entries.specs[index])!=u['methodSpec'] or entries.specs[index][0]!=method[0]:
        fail('nonnull-public-logger-usage-spec',u,entries.specs[index])
    _,ci,mi=entries.specs[index];cn,_=entries.arguments(ci);mn,_=entries.arguments(mi)
    if cn!=[] or mn!=['string','string']:fail('nonnull-public-logger-stored-arguments',[[],['string','string']],[cn,mn])
    rows=generic_method_candidates(entries.table,entries.meta['genericMethodTableCount'],len(entries.specs),{index},
        entries.code['genericMethodPointersCount'],entries.code['invokerPointersCount'],source=str(image.gameassembly),offset=entries.table_base)
    if rows:fail('nonnull-public-logger-stored-unregistered','no AOT row for this stored context spec',rows)
    physical=entries.resolve(method[0],[],['object','object']);declared=c['loggerPhysicalRegistration']
    actual={'methodSpecIndex':physical['methodSpecIndex'],'methodSpec':list(entries.specs[physical['methodSpecIndex']]),
        'registration':{k:physical['registration'][k] for k in ('tableIndex','methodSpecIndex','rawHex','indices')},
        'pointerRva':physical['pointer']-image.pe.image_base,'methodDefinitionIndices':physical['methodDefinitionIndices']}
    if actual!=declared or actual['pointerRva']!=method[3]:fail('nonnull-public-logger-physical-registration',declared,actual)

def _validate_image(image,c,dependency,declaration,*,fail):
    methods=c['methods']
    for role,owner,name,result,params,static in [
        ('public','Beyond.Blackboard+BlackboardDouble','GetValue',(13,'double'),[(18,'Beyond.Blackboard',False)],False),
        ('patchCheck','IFix.WrappersManagerImpl','IsPatched',(2,'bool'),[(8,'int',False)],True),
        ('dumpToString','Beyond.Blackboard','DumpToString',(14,'string'),[],False)]:
        if methods[role][1:3]!=[owner,name]:fail('nonnull-public-method-name',[owner,name],methods[role])
        signature(image,methods[role],result,params,static=static,fail=fail)
    image.validate_method_row(methods['tryValue'],label=LABEL);m=image.metadata.methods[methods['tryValue'][0]]
    if m.declaring_type!=declaration['runtimeTypeDefinition'] or m.slot!=c['trySlot']:
        fail('nonnull-public-try-slot',[declaration['runtimeTypeDefinition'],c['trySlot']],[m.declaring_type,m.slot])
    _vtable(image,m.declaring_type,m.slot,m.index,LABEL)
    if c['entries']['public']!=methods['public'][3] or c['entries']['try']!=methods['tryThunk'][3]:
        fail('nonnull-public-entry-identity','same actual public/helper entries',c['entries'])
    _logger(image,c,fail=fail)
    index=BodyIndex(image);base=image.pe.image_base;fields=dependency['dependencyProofs']['consumer']['consumerTransfer']
    cells={'blackboardKey':fields['records']['tryKeyed']['keyOffset'],'useBlackboardKey':fields['records']['tryKeyed']['selectorOffset'],
        'value':fields['records']['tryDirect']['valueOffset']}
    specs=control.specifications(cells,c['dispatchLimits'],c['trySlot'])
    for role in ('public','try'):
        entry=base+c['entries'][role]
        if entry not in index.extents:fail('nonnull-public-owned-entry',role,'missing actual unwind entry')
        owned={(entry-base,index.extents[entry]-base)}|{(at-base,at+size-base) for at,size in index.chained_fragments.get(entry,())}
        windows=c['ownedCodeWindows'][role]
        if {(w['startRva'],w['endRva']) for w in windows}!=owned or len(windows)!=len(owned):
            fail('nonnull-public-all-owned-ranges',sorted(owned),windows)
        image.check_windows(windows,label=LABEL)
        for name,spec in specs.items():
            if spec['owner']==role and c['programs'][name]['codeWindows']!=windows:
                fail('nonnull-public-program-owner',role,c['programs'][name])
    flow=control.validate(image,c,fields,dependency['dependencyProofs']['lookup']['selectedManagedLookup'],dependency['selectedKeyedLookupRelation'],fail=fail)
    return {**flow,'storedLoggerStringContextHasNoRegisteredAotRowProved':True,
        'sameLoggerDefinitionObjectObjectPhysicalRegistrationProved':True,'storedAndPhysicalLoggerMethodSpecsEqual':False}

def validate_current_native_contract(*,gameassembly:Path,metadata:Path)->dict:
    paths=set(_package_import_closure(Path(__file__)))|{CONTRACT_PATH,lookup_owner.consumer_owner.CONTRACT_PATH,
        lookup_owner.lookup_owner.CONTRACT_PATH,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH}
    inputs={r['path']:r for r in (_fingerprint(p) for p in paths)}
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return _skip(gate.status,gate.detail,pins)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file():return _skip('missing','UnityPlayer.dll missing beside selected native image',pins)
    if _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:return _skip('mismatched','Selected UnityPlayer.dll differs',pins)
    declaration=lookup_owner.consumer_owner._contract()
    if (declaration['nativeInputs']!=pins or c['methods']['tryValue']!=declaration['records']['tryValue']['method']
            or c['methods']['patchCheck']!=declaration['patchCheckMethod'] or c['methods']['numberLookup']!=declaration['numberLookupMethod']):
        return _skip('mismatched','Dependency build or actual Try/patch/lookup definitions differ',pins)
    dependency=lookup_owner.validate_current_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
    if dependency['status']!='validated':return _skip(dependency['status'],'Keyed relation not current: '+dependency.get('detail',''),pins)
    if dependency['nativeInputs']!=pins:return _skip('mismatched','Dependency belongs to another native build',pins)
    for before in dependency['provenance']['inputs']:
        current=_fingerprint(Path(before['path']))
        if current!=before or inputs.setdefault(before['path'],before)!=before:_fail('dependency-source-drift',before,current)
    image=open_native_image(gate.gameassembly,gate.metadata);flow=_validate_image(image,c,dependency,declaration,fail=_fail)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return _skip(after.status,after.detail,pins)
    if not unity.is_file() or _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:
        return _skip('missing' if not unity.is_file() else 'mismatched','Selected UnityPlayer.dll changed',pins)
    for before in inputs.values():
        actual=_fingerprint(Path(before['path']))
        if actual!=before:_fail('source-drift',before,actual)
    return {'status':'validated','nativeInputs':pins,'selectedNonNullBoardPublicReturn':flow,
        'selectedNonNullBoardPublicReturnComposed':True,'provenance':{'inputs':sorted(inputs.values(),key=lambda r:r['path'])},
        'evidenceBoundary':'conditional','actualNumericResultKnown':False,'publicGetValueAllNormalSelectionsProved':False,
        'actualRuntimeClassSlotValueKnown':False,'liveLoggerContextOrMutationEffectsProved':False,'runtimeExecutionKnown':False,
        'providerSelectionProved':False,'allDispatchAndFailureEffectsProved':False,'wholeActionAdmitted':False,'wholeRootAdmitted':False}
