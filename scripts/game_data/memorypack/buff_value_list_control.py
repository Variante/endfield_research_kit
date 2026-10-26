"""Independent integer value-list control beside current DamageType type joins.

An integer compiled witness does not supply a missing concrete DamageType
registration or prove a live provider choice. No stored action/root is admitted.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.context import type_parameter_owner
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory
from .core import CONTRACTS_DIR
from . import buff_camera_usp_damage_source as source_owner
from .list_reference_sources import validate_list_element_context
from .value_list_sources import validate_buffered_dword_output_formatter, validate_buffered_dword_output_list

LABEL='buffValueListControl'
SCHEMA='endfield.buff-value-list-control-native-contract.v1'
SCOPE='independent-int-value-list-selected-normal-control-only'
CONTRACT_PATH=CONTRACTS_DIR/'buff_value_list_control_native.json'


def _fail(check,expected,actual):
    raise ValueError(json.dumps({'validator':LABEL,'check':check,'source':CONTRACT_PATH.as_posix(),
        'expected':str(expected)[:1024],'actual':str(actual)[:1024]}))


def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if c.get('scope')!=SCOPE or set(c['dependencies'])!={'sourceRegistration','listContext'}:
        _fail('scope','independent integer witness with separate source dependencies',c.get('scope'))
    return c


def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'scope':SCOPE,'nativeInputs':pins,
        'positiveStoredGrammarAdmitted':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}


def _non_byref_int32(raw):
    # Other native type flags are independent of the byref bit.
    return len(raw)==16 and raw[10]==0x08 and not raw[11]&0x20


def _signature(image,row,selected,*,element_kind):
    image.validate_method_row(row[:3],label=LABEL)
    method=image.metadata.methods[row[0]];parameters=image.metadata.parameters_for(method)
    if method.flags&0x10 or selected.type_name(method.return_type)!='void' or len(parameters)!=2:
        _fail('deserialize-signature','instance void with two byrefs',row)
    first=image.pe.bytes_at_va(selected.type_pointer(parameters[0].type_index),16)
    second=image.pe.bytes_at_va(selected.type_pointer(parameters[1].type_index),16)
    if not first[11]&0x20 or selected.type_name(parameters[0].type_index)!='MemoryPack.MemoryPackReader' or not second[11]&0x20 or second[10]!=element_kind:
        _fail('deserialize-parameters','same Reader and owned List/VAR output by reference',[first.hex(),second.hex()])
    return method,second


def _validate_image(image,c,source):
    pins=c['nativeInputs'];selected=NativeReferenceContext(image);entries=GenericEntries(image)
    dependency,_=read_reviewed_contract(CONTRACTS_DIR/c['dependencies']['listContext'],
        schema='endfield.buff-timeline-static-composition-native-contract.v1',status='exact-current-build',label=LABEL)
    if dependency['nativeInputs']!=pins or c['dependencies']['sourceRegistration']!=source_owner.CONTRACT_PATH.name:
        _fail('dependency-build','same selected build and reviewed source owner',c['dependencies'])
    contexts=[r for r in dependency['composition']['genericContexts']
        if r['typeName']=='MemoryPack.Formatters.ListFormatter`1' and not r['isMethod']]
    if len(contexts)!=1:_fail('list-owned-context','one complete ListFormatter class context',contexts)
    context=contexts[0];validate_generic_contexts(image,contexts,label=LABEL)
    owned_context=validate_list_element_context(image,context,entries,fail=_fail)
    table_rva,image_size,table=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(table,lambda at,size:image.pe.bytes_at_va(image.pe.image_base+at,size),
        table_rva=table_rva,image_size=image_size)
    registrations={};ownership={}
    for key,definition in (('listEntry','MemoryPack.Formatters.ListFormatter`1'),
            ('elementEntry','MemoryPack.Formatters.UnmanagedFormatter`1')):
        row=c[key]
        if row['method'][1:3]!=[definition,'Deserialize'] or row['classArguments']!=['int'] or row['methodArguments']!=[]:
            _fail('independent-int-selection',definition,row['method'])
        actual=entries.resolve(row['method'][0],row['classArguments'],row['methodArguments'])
        if json.loads(json.dumps(actual))!=row['registration'] or actual['pointer']-image.pe.image_base!=row['method'][3]:
            _fail('independent-compiled-entry',row['registration'],actual)
        family=unwind.family(row['method'][3])
        if json.loads(json.dumps(family))!=row['unwindFamily']:
            _fail('complete-unwind-parent-triples',row['unwindFamily'],family)
        windows=row['codeWindows'] if key=='listEntry' else row['proof']['codeWindows']
        spans={(w['startRva'],w['endRva']) for w in windows}
        if len(spans)!=len(windows) or spans!={(r['runtimeTriple'][0],r['runtimeTriple'][1]) for r in family['ranges']}:
            _fail('complete-unwind-window-membership','all exact current parent-chain ranges',sorted(spans))
        image.check_windows(windows,label=LABEL)
        instance=image.instantiations.resolve(actual['classInstantiation']['index'])
        if len(instance.arguments)!=1 or not _non_byref_int32(image.pe.bytes_at_va(instance.arguments[0].type_pointer_va,16)):
            _fail('compiled-witness-argument','actual non-byref System.Int32',actual['classInstantiation'])
        registrations[key]=actual;ownership[key]=family
    lm,list_parameter=_signature(image,c['listEntry']['method'],selected,element_kind=0x15)
    if lm.declaring_type!=context['definition']:_fail('same-list-context-owner',context['definition'],lm.declaring_type)
    slot=next(r for r in context['entries'] if r['relativeSlot']==0)
    if list_parameter[:8]!=image.pe.bytes_at_va(selected.type_pointer(slot['index']),16)[:8]:
        _fail('owned-list-output','same owned List<VAR0> carrier',list_parameter.hex())
    em,element_parameter=_signature(image,c['elementEntry']['method'],selected,element_kind=0x13)
    owner=image.metadata.types[em.declaring_type];section=image.metadata.sections['genericContainers']
    at=section.offset+owner.generic_container_index*16
    if owner.generic_container_index<0 or not section.offset<=at<=section.offset+section.size-16:
        _fail('unmanaged-class-container','owned class parameter',owner.generic_container_index)
    definition,count,is_method,start=struct.unpack_from('<iiii',image.metadata.buf,at)
    parameter=type_parameter_owner(image.metadata.buf,start,[t.generic_container_index for t in image.metadata.types],source=LABEL)
    if ((definition,count,is_method)!=(owner.index,1,0) or parameter['typeIndex']!=owner.index
            or parameter['ordinal']!=0 or int.from_bytes(element_parameter[:8],'little')!=start):
        _fail('unmanaged-owned-output-var','same reciprocal class VAR0',[definition,count,is_method,start,parameter])
    offsets=c['readerFieldsUnboxedOffsets']
    if offsets!={k:selected.field('MemoryPack.MemoryPackReader::'+k)[2]-16 for k in offsets}:
        _fail('reader-fields','current named unboxed metadata fields',offsets)
    windows=c['listEntry']['codeWindows']
    if any(p['codeWindows']!=windows or p['program'][0][0]!=c['listEntry']['method'][3] for p in c['programs'].values()):
        _fail('list-program-entry-and-windows','same independently registered complete unwind family',c['programs'])
    if c['elementEntry']['proof']['program'][0][0]!=c['elementEntry']['method'][3]:
        _fail('element-program-entry',c['elementEntry']['method'][3],c['elementEntry']['proof']['program'][0])
    loop=validate_buffered_dword_output_list(image,c['programs'],offsets,fail=_fail)
    scalar=validate_buffered_dword_output_formatter(image,c['elementEntry']['proof'],offsets,fail=_fail)
    actual=source['formatterRegistrations'];requested=actual['damageTypeList']['elementType']
    if actual['damageTypeList']['elementTypePointerVa']!=actual['damageTypeValue']['elementTypePointerVa']:
        _fail('same-current-source-element','list and independent scalar source share actual element pointer',actual)
    gaps=[]
    for key in ('listEntry','elementEntry'):
        row=c[key]
        try:entry=entries.resolve(row['method'][0],[requested],[])
        except ValueError as error:
            if str(error)!='generic entry: expected one non-null registered instantiation, matched 0':raise
            gaps.append({'formatter':row['method'][1],'requestedElement':requested,
                'status':'missing-independent-compiled-registration','detail':str(error)})
        else:
            gaps.append({'formatter':row['method'][1],'requestedElement':requested,
                'status':'independent-registration-inspected-selection-still-unresolved','entry':entry})
    return {'ownedListElementContext':owned_context,'independentCompiledRegistrations':registrations,
        'unwindFamilies':ownership,'listControl':loop,'integerElementSource':scalar,
        'sourceElementType':requested,'sourceElementTypePointerVa':actual['damageTypeList']['elementTypePointerVa'],
        'sourceListAndScalarRegistrationKeyJoinProved':True,'concreteCompiledEntryInspections':gaps,
        'integerWitnessComposedAsDamageType':False,'runtimeProviderObserved':False}


def validate_current_native_contract(*,gameassembly:Path,metadata:Path):
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return _skip(gate.status,gate.detail,pins)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches():return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll missing or mismatched',pins)
    source=source_owner.validate_current_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
    if source['status']!='validated' or source['nativeInputs']!=pins:
        return _skip(source['status'] if source['status']!='validated' else 'mismatched','Current source registration dependency was not validated on the selected build',pins)
    summary=_validate_image(open_native_image(gate.gameassembly,gate.metadata),c,source)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not unity_matches():
        return _skip(after.status if after.status!='validated' else 'mismatched','Native inputs changed during value-list validation',pins)
    return {'status':'validated','scope':SCOPE,'nativeInputs':pins,'summary':summary,
        'actualSourceRegistrationReturn':source,'positiveStoredGrammarAdmitted':False,
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'evidenceBoundary':c['evidenceBoundary']}
