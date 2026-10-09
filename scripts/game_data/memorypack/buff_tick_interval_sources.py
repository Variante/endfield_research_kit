"""Current complete TickInterval caller/setter field flows, without admission.

Full owned native programs prove conditional return-register transfers to nine
metadata-owned Data fields, including inherited fields, cache refresh, FF and
the concrete formatter. Child wire/output composition and scheduling/effects
remain independent requirements. This module never decodes or admits a parent.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import _vtable
from scripts.game_data.il2cpp.reference_field_programs import (
    prove_reference_field_reader, prove_base_field_setter, prove_cached_field_setter,
    prove_cached_instance_getter)
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack.inherited_reference_sources import _ancestry
from scripts.game_data.memorypack.struct_output_sources import check_reader_ref_wrapper_abi
from scripts.game_data.memorypack.named_native_records import check_typed_context
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import skill_timeline_tick_interval as candidate

LABEL='buffTickIntervalSources'
SCHEMA='endfield.buff-tick-interval-source-flows-native-contract.v1'
CONTRACT_PATH=CONTRACTS_DIR/'buff_tick_interval_sources_native.json'


def _fail(check,expected,actual):
    error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL)
    error.args=(json.dumps(error.diagnostic,sort_keys=True),)
    raise error


def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if (c.get('scope')!='complete-conditional-caller-and-owned-field-flows-only'
            or c.get('candidateContract')!=candidate.CONTRACT_PATH.name
            or c.get('commonSymbolsContract')!='buff_selector_zero_finders_native.json'
            or tuple(m.get('fieldName') for m in c.get('fields',[]))!=candidate.FIELD_NAMES
            or [m.get('memberIndex') for m in c['fields']]!=list(range(len(candidate.FIELD_NAMES)))
            or [m.get('readKind') for m in c['fields']]!=list(candidate.READ_KINDS)):
        _fail('contract-shape','complete ordered source flows, without wire admission',c.get('scope'))
    return c


def _owned(image,index,body):
    image.validate_method_row(body['method'],label=LABEL)
    entry=image.pe.image_base+body['method'][3];end=index.extents.get(entry)
    if end is None:_fail('owned-extent','complete unwind-owned method',body['method'])
    spans=sorted(set([(entry,end)]+[(at,at+n) for at,n in index.chained_fragments.get(entry,())]))
    actual=[{'startRva':a-image.pe.image_base,'endRva':b-image.pe.image_base} for a,b in spans]
    if actual!=body['ownedPdataFragments']:_fail('complete-owned-fragments',body['ownedPdataFragments'],actual)
    merged=[]
    for a,b in spans:
        if merged and merged[-1][1]==a:merged[-1][1]=b
        else:merged.append([a,b])
    if [[w['startRva']+image.pe.image_base,w['endRva']+image.pe.image_base] for w in body['codeWindows']]!=merged:
        _fail('complete-owned-window-coverage',merged,body['codeWindows'])
    image.check_windows(body['codeWindows'],label=LABEL)
    return [index._decode(a,b-a) for a,b in merged]


def _validate_image(image,c):
    source=candidate._contract()
    common,_=read_reviewed_contract(CONTRACTS_DIR/c['commonSymbolsContract'],
        schema='endfield.buff-selector-zero-finders-native-contract.v2',status='exact-current-build',label=LABEL)
    if source['nativeInputs']!=c['nativeInputs'] or common['nativeInputs']!=c['nativeInputs']:
        _fail('dependency-build',c['nativeInputs'],[source['nativeInputs'],common['nativeInputs']])
    image.validate_dispatcher(source['dispatcher'],label=LABEL)
    wrappers=derive_from_image(image);wrapper=wrappers.get(c['wrapper']['typeDefinition'])
    if wrapper is None or wrapper.row()!=c['wrapper']:_fail('current-generated-wrapper',c['wrapper'],None if wrapper is None else wrapper.row())
    runtime=_ancestry(image,c['runtimeTypeDefinition']);ancestry=_ancestry(image,wrapper.type_definition)
    if runtime!=c['runtimeAncestry'] or ancestry!=c['wrapperAncestry']:_fail('current-runtime-and-wrapper-ancestry',[c['runtimeAncestry'],c['wrapperAncestry']],[runtime,ancestry])
    if (len(runtime)!=2 or len(ancestry)!=2 or wrapper.wrapped_type!=runtime[0]['name']
            or wrapper.wrapped_type!='Beyond.Gameplay.Core.TickIntervalAction+Data'):
        _fail('paired-concrete-and-inherited-owners','two corresponding Data/wrapper owners',runtime)
    selected=NativeReferenceContext(image);index=BodyIndex(image);base=image.pe.image_base
    root=selected.field(ancestry[-1]['name']+'::___instance');cache=selected.field(wrapper.name+'::__realInstance')
    if root[:2]!=(ancestry[-1]['name'],runtime[-1]['name']) or cache[:2]!=(wrapper.name,runtime[0]['name']):
        _fail('metadata-instance-and-cache-types',[runtime[-1]['name'],runtime[0]['name']],[root,cache])
    if root[2]!=c['instanceOffset'] or cache[2]!=c['cacheOffset']:_fail('metadata-instance-and-cache-layout',[c['instanceOffset'],c['cacheOffset']],[root,cache])
    bodies={name:_owned(image,index,body) for name,body in c['bodies'].items()}
    reader=c['bodies']['reader']['method'];getter=c['bodies']['getter']['method']
    if reader[1:3]!=[wrapper.name,'Deserialize'] or getter[1:3]!=[wrapper.name,'get___instance']:
        _fail('concrete-reader-and-getter-identities',wrapper.name,[reader,getter])
    check_reader_ref_wrapper_abi(image,{'readerMethod':reader,'wrapperTypeDefinition':wrapper.type_definition},fail=_fail)
    gm=image.metadata.methods[getter[0]]
    if gm.flags&0x10 or gm.parameter_count or selected.type_name(gm.return_type)!=wrapper.wrapped_type:
        _fail('concrete-getter-return-type',wrapper.wrapped_type,getter)
    symbols={name:base+rva for name,rva in c['symbols'].items() if name!='metadataUsageCount'}
    symbols['metadataUsageCount']=c['symbols']['metadataUsageCount']
    for name in ('metadataInit','classInit','header','allocate','barrier','nullThrow','getTypeFromHandle','invalidPropertyCount'):
        if c['symbols'][name]!=common['symbols'][name]:_fail('same-selected-common-entry',name,c['symbols'][name])
    for role,method_name in (('constructor','.ctor'),('onDeserialized','OnDeserialized')):
        method=c['bodies'][role]['method']
        if method[1:3]!=[wrapper.name,method_name] or method[3]!=c['symbols'][role]:_fail('concrete-lifecycle-entry',role,method)
    fields=[];setters=[]
    for ordinal,field in enumerate(c['fields']):
        matches=[(owner,f) for owner in runtime for f in owner['fields'] if f['name']==field['fieldName']]
        if len(matches)!=1:_fail('unique-current-owned-field',field['fieldName'],matches)
        owner,stored=matches[0];actual=selected.field(owner['name']+'::'+field['fieldName'])
        method=field['setterMethod'];image.validate_method_row(method,label=LABEL);metadata_method=image.metadata.methods[method[0]]
        parameters=image.metadata.parameters_for(metadata_method)
        wrapper_owner=ancestry[runtime.index(owner)]['name']
        if (actual!=(field['fieldOwner'],field['declaredType'],field['fieldOffset'])
                or stored['type']['name']!=field['declaredType'] or method[1:3]!=[wrapper_owner,'set___'+field['fieldName']+'__']
                or metadata_method.flags&0x10 or len(parameters)!=1 or selected.type_name(parameters[0].type_index)!=field['declaredType']
                or selected.type_name(metadata_method.return_type)!='void'):
            _fail('current-field-setter-ownership',field,actual)
        read=source['orderedSourceReads'][ordinal]
        if (field['readerEntryRva']!=read['sourceTargetRva'] or field['setterEntryRva']!=method[3]
                or field['sourceCallsiteRva']!=read['sourceCallsiteRva']):_fail('same-reviewed-source-call',read,field)
        fields.append({**field,'readerEntry':base+field['readerEntryRva'],'setterEntry':base+field['setterEntryRva']})
        programs=bodies[field['bodyKey']]
        if len(programs)!=1 or c['bodies'][field['bodyKey']]['method']!=method:_fail('complete-setter-body',method,programs)
        kwargs={'field_offset':actual[2],'mode':field['mode'],'symbols':{**symbols,'getter':base+getter[3]}}
        proof=(prove_base_field_setter(programs[0],instance_offset=root[2],**kwargs)
            if wrapper_owner==ancestry[-1]['name'] else prove_cached_field_setter(programs[0],**kwargs))
        setters.append({'fieldName':field['fieldName'],'fieldOwner':owner['name'],'declaredType':field['declaredType'],'proof':proof})
    if len(bodies['reader'])!=2 or len(bodies['getter'])!=2 or len(bodies['formatter'])!=1:
        _fail('reader-getter-formatter-fragments','complete primary/cold and formatter',[len(bodies[k]) for k in ('reader','getter','formatter')])
    caller=prove_reference_field_reader(*bodies['reader'],fields,symbols,label=LABEL+'.caller')
    for field,transfer in zip(c['fields'],caller['fieldTransfers'],strict=True):
        if int(transfer['sourceCall']['va'],16)-base!=field['sourceCallsiteRva']:_fail('original-source-callsite',field,transfer)
    context=source['nestedContexts'][0];check_typed_context(image,context,c['fields'][4]['declaredType'],label=LABEL,fail=_fail)
    if int(caller['fieldTransfers'][4]['contextLoad']['va'],16)-base!=context['instructionRva']:
        _fail('sequence-context-actual-load',context,caller['fieldTransfers'][4])
    getter_proof=prove_cached_instance_getter(*bodies['getter'],instance_offset=root[2],cache_offset=cache[2],symbols=symbols,label=LABEL+'.getter')
    formatter=c['bodies']['formatter']['method'];fm=image.metadata.methods[formatter[0]]
    if fm.slot!=5 or image.metadata.nested_parent_by_type_index.get(fm.declaring_type)!=wrapper.type_definition:
        _fail('same-wrapper-formatter-slot-five',wrapper.type_definition,formatter)
    _vtable(image,fm.declaring_type,5,fm.index,LABEL)
    forwarding=prove_zero_wrapper_forwarder(bodies['formatter'][0],symbols,base+reader[3],label=LABEL+'.formatter')
    routes,audit=load_action_routes(gameassembly=image.gameassembly,metadata=image.metadata_path)
    route=routes.get(candidate.TAG)
    if audit['status']!='validated' or route is None or route.wrapper_name!=wrapper.name or list(route.member_order)!=list(candidate.FIELD_NAMES):
        _fail('current-buff-action-route',wrapper.name,None if route is None else route.row())
    return {'fieldsForwardedToOwnedData':len(fields),'inheritedFields':len(runtime[-1]['fields']),
        'caller':caller,'setters':setters,'getter':getter_proof,'formatter':forwarding,
        'closedSequenceContextMetadataJoined':True,'currentConcreteMetadataSlotFiveJoined':True,
        'completeConditionalSourceOutputFlowsProved':True,'completeTickStoredGrammarAdmitted':False,
        'physicalChildHelperOutputCompositionProved':False,'runtimeSchedulingOrEffectsObserved':False}


def validate_current_native_contract(*,gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def matches():
        if not unity.is_file():return False
        with unity.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest().upper()==pins['UnityPlayer.dll']
    if not matches():return {'status':'mismatched' if unity.is_file() else 'missing','detail':'UnityPlayer.dll missing or mismatched','nativeInputs':pins}
    try:summary=_validate_image(open_native_image(gate.gameassembly,gate.metadata),c)
    except ValueError as error:
        if isinstance(error,CensusGateError):raise
        _fail('complete-owned-source-flow','current metadata, full original caller/setter/getter/formatter programs',str(error))
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not matches():
        return {'status':after.status if after.status!='validated' else 'mismatched','detail':'native inputs changed during source flow proof','nativeInputs':pins}
    return {'status':'validated','nativeInputs':pins,'summary':summary,'wholeActionAdmitted':False,
        'positiveListAdmitted':False,'wholeRootAdmitted':False,'runtimeMeaningExact':False,'evidenceBoundary':c['evidenceBoundary']}
