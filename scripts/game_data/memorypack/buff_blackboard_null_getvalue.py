"""Selected initialized null-Blackboard GetValue with current static joins.

The stored closed MethodSpec is authenticated separately from the selected
return programs. Runtime class slots, initializer and logger effects remain
conditions; no live MethodInfo or executing receiver is supplied.
"""
from __future__ import annotations
import json
import struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import generic_method_candidates, unresolved_usage_index
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import _vtable
from scripts.game_data.memorypack import buff_blackboard_double_consumers as consumer_owner
from scripts.game_data.memorypack import blackboard_null_getvalue as control
from scripts.game_data.memorypack.closed_scalar_consumers import signature
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _package_import_closure

LABEL='buffBlackboardNullGetValue'
CONTRACT_PATH=CONTRACTS_DIR/'memorypack_blackboard_null_getvalue_native.json'


def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.memorypack-blackboard-null-getvalue-native-contract.v1',status='exact-current-build',label=LABEL)
    if c.get('mode')!=control.MODE:raise ValueError(LABEL+'.contract:mode')
    return c


def _fail(check,expected,actual):
    error=CensusGateError(LABEL+'.'+check,source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,record='Beyond.Blackboard+BlackboardDouble.GetValue')
    error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error


def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'wholeActionAdmitted':False,'wholeRootAdmitted':False}


def _direct_usage(image,c,*,fail):
    u=c['directUsage'];at=image.pe.image_base+u['usageCellRva']
    raw=image.pe.bytes_at_va(at,8)
    if raw.hex().upper()!=u['usageRawHex'] or u['usageCellRva']!=c['globalCells']['directUsage']:
        fail('null-public-static-usage-cell',u,raw.hex().upper())
    entries=GenericEntries(image)
    spec_index=unresolved_usage_index(raw,len(entries.specs),tag=6,source=str(image.gameassembly),offset=at)
    if spec_index!=u['methodSpecIndex'] or list(entries.specs[spec_index])!=u['methodSpec']:
        fail('null-public-static-method-spec',u,entries.specs[spec_index])
    definition,ci,mi=entries.specs[spec_index];method=c['methods']['getDirectValue']
    if method[:3]!=[definition,'Beyond.Blackboard+BlackboardParamBase`2','GetDirectValue']:
        fail('null-public-static-direct-definition','actual base GetDirectValue definition',method)
    image.validate_method_row(method[:3],label=LABEL)
    m=image.metadata.methods[definition]
    if m.flags&0x10 or image.metadata.parameters_for(m):
        fail('null-public-static-direct-parameters','instance method without explicit parameters',definition)
    cn,_=entries.arguments(ci);mn,_=entries.arguments(mi)
    if cn!=['float','double'] or mn!=[]:
        fail('null-public-static-closed-arguments',[['float','double'],[]],[cn,mn])
    rows=generic_method_candidates(entries.table,entries.meta['genericMethodTableCount'],len(entries.specs),{spec_index},
        entries.code['genericMethodPointersCount'],entries.code['invokerPointersCount'],source=str(image.gameassembly),offset=entries.table_base)
    actual=[{k:r[k] for k in ('tableIndex','methodSpecIndex','rawHex','indices')}|
        {'pointerRva':struct.unpack_from('<Q',entries.pointers,r['indices'][0]*8)[0]-image.pe.image_base} for r in rows]
    if len(actual)!=1 or actual!=u['registrations'] or actual[0]['pointerRva']!=method[3] or method[3]!=c['entries']['direct']:
        fail('null-public-static-closed-registration',u['registrations'],actual)


def _validate_image(image,c,dependency,declaration,*,fail):
    scalar='Beyond.Blackboard+BlackboardDouble';methods=c['methods']
    for role,owner,name,result,parameters,static in [
        ('public',scalar,'GetValue',(13,'double'),[(18,'Beyond.Blackboard',False)],False),
        ('patchCheck','IFix.WrappersManagerImpl','IsPatched',(2,'bool'),[(8,'int',False)],True),
        ('directLogError','Beyond.DLogger','LogError',(1,'void'),[(14,'string',False)],True)]:
        if methods[role][1:3]!=[owner,name]:fail('null-public-method-name',[owner,name],methods[role])
        signature(image,methods[role],result,parameters,static=static,fail=fail)
    cast=methods['castValue'];image.validate_method_row(cast,label=LABEL);m=image.metadata.methods[cast[0]]
    if m.declaring_type!=declaration['runtimeTypeDefinition'] or m.slot!=c['castSlot']:
        fail('null-public-cast-slot',[declaration['runtimeTypeDefinition'],c['castSlot']],[m.declaring_type,m.slot])
    _vtable(image,m.declaring_type,m.slot,m.index,LABEL)
    if c['entries']['public']!=methods['public'][3] or c['entries']['cast']!=c['entries']['castThunk']:
        fail('null-public-entry-identity','same actual public entry and shared cast tail',c['entries'])
    _direct_usage(image,c,fail=fail)
    index=BodyIndex(image);base=image.pe.image_base
    for role in ('public','direct','cast'):
        entry=base+c['entries'][role]
        if entry not in index.extents:fail('null-public-owned-entry',role,'missing actual unwind entry')
        owned={(entry-base,index.extents[entry]-base)}|{(at-base,at+size-base) for at,size in index.chained_fragments.get(entry,())}
        windows=c['ownedCodeWindows'][role]
        if {(w['startRva'],w['endRva']) for w in windows}!=owned or len(windows)!=len(owned):
            fail('null-public-all-owned-ranges',sorted(owned),windows)
        image.check_windows(windows,label=LABEL)
        for name,spec in control.specifications(dependency['consumerTransfer']['records']['tryKeyed']['selectorOffset'],c['castSlot']).items():
            program=c['programs'][name]
            if spec['owner']==role and (program['codeWindows']!=windows or program['entryRva']!=c['entries'][role]):
                fail('null-public-program-owner',[role,c['entries'][role],windows],program)
    flow=control.validate(image,c,dependency['consumerTransfer'],declaration,fail=fail)
    return {**flow,'onDiskClosedDirectRegistrationProved':True}


def validate_current_native_contract(*,gameassembly:Path,metadata:Path)->dict:
    paths=set(_package_import_closure(Path(__file__)))|{CONTRACT_PATH,consumer_owner.CONTRACT_PATH,
        consumer_owner.data.CONTRACT_PATH,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH}
    inputs={r['path']:r for r in (_fingerprint(p) for p in paths)}
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return _skip(gate.status,gate.detail,pins)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file():return _skip('missing','UnityPlayer.dll missing beside selected native image',pins)
    if _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:return _skip('mismatched','Selected UnityPlayer.dll differs',pins)
    declaration=consumer_owner._contract()
    if (declaration['nativeInputs']!=pins or c['methods']['castValue']!=declaration['records']['castValue']['method']
            or c['methods']['patchCheck']!=declaration['patchCheckMethod']):
        return _skip('mismatched','Dependency build or actual cast/patch definitions differ',pins)
    dependency=consumer_owner.validate_current_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
    if dependency['status']!='validated':return _skip(dependency['status'],'Concrete consumer not current: '+dependency.get('detail',''),pins)
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
    return {'status':'validated','nativeInputs':pins,'selectedNullBoardPublicReturn':flow,
        'selectedNullBoardPublicReturnComposed':True,'provenance':{'inputs':sorted(inputs.values(),key=lambda r:r['path'])},
        'evidenceBoundary':'conditional','actualNumericResultKnown':False,'publicGetValueAllNormalSelectionsProved':False,
        'actualRuntimeClassSlotValueKnown':False,'liveMethodInfoOrMutationEffectsProved':False,
        'runtimeExecutionKnown':False,'providerSelectionProved':False,'allDispatchAndFailureEffectsProved':False,
        'wholeActionAdmitted':False,'wholeRootAdmitted':False}
