"""Authenticate current DataPair cells and the registered closed list copy.

Nongeneric field ownership, constructor stores, type-size records and the
closed return VAR join are independent of anonymous open-generic offsets.
Explicit selected-build and source gates bound all conditional claims.
"""
from __future__ import annotations
import json
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.context import type_parameter_owner
from scripts.game_data.memorypack import blackboard_pair_cells as program
from scripts.game_data.memorypack import inherited_reference_sources as types
from scripts.game_data.memorypack.closed_scalar_consumers import signature
from scripts.game_data.memorypack.wrapper_members import IL2CPP_OBJECT_HEADER
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _package_import_closure

LABEL='buffBlackboardPairList'
CONTRACT_PATH=CONTRACTS_DIR/'memorypack_blackboard_pair_list_native.json'
BARRIER_CONTRACT_PATH=CONTRACTS_DIR/'buff_timeline_source_wrappers_native.json'


def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.memorypack-blackboard-pair-list-native-contract.v1',status='exact-current-build',label=LABEL)
    if c.get('mode')!=program.MODE:raise ValueError(f'{LABEL}.contract:mode')
    return c


def _fail(check,expected,actual):
    error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,record='Beyond.Blackboard+DataPair',nativeInputs=_contract()['nativeInputs'])
    error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error


def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'wholeActionAdmitted':False,'wholeRootAdmitted':False}


def _owned(index,image,method,proof,fail):
    entry=image.pe.image_base+method[3]
    if entry not in index.extents:fail('pair-unwind-entry','actual registered entry with unwind extent',method)
    owned={(entry-image.pe.image_base,index.extents[entry]-image.pe.image_base)}
    owned.update((at-image.pe.image_base,at+size-image.pe.image_base) for at,size in index.chained_fragments.get(entry,()))
    for window in proof['codeWindows']:
        if (window['startRva'],window['endRva']) not in owned:
            fail('pair-unwind-owner','exact registered entry or chained unwind extent',window)


def _validate_identity(image,c,index,*,fail):
    pair=types._ancestry(image,c['pairTypeDefinition'])
    if pair!=c['pairAncestry'] or pair[0]['name']!='Beyond.Blackboard+DataPair':
        fail('pair-field-owner',c['pairAncestry'],pair)
    td=image.metadata.types[c['pairTypeDefinition']]
    if td.generic_container_index>=0 or pair[0]['parent']['name']!='System.ValueType':
        fail('pair-value-type','nongeneric DataPair inheriting ValueType',pair[0])
    fields=pair[0]['fields'];wanted={'key':(14,'string'),'valueDouble':(13,'double'),'valueStr':(14,'string'),'isDynamic':(2,'bool')}
    if (len(fields)!=4 or {f['name']:(f['type']['kind'],f['type']['name']) for f in fields}!=wanted
            or any(int.from_bytes(bytes.fromhex(f['type']['rawHex'])[8:10],'little')&0x10 for f in fields)):
        fail('pair-instance-fields',wanted,fields)
    cells=c['unboxedCells'];boxed=pair[0]['offsets']
    if set(cells)!=set(wanted) or any(type(v)is not int for v in cells.values()) or any(boxed[n]-cells[n]!=IL2CPP_OBJECT_HEADER for n in wanted):
        fail('pair-boxed-unboxed-correspondence','same object-header bias for every owned constructor cell',[boxed,cells])
    size_base=int(image.registration['typeDefinitionsSizes'],16)
    pointer=image.pe.u64_at_va(size_base+td.index*8);raw=image.pe.bytes_at_va(pointer,16)
    size=c['pairSizeRecord']
    if raw.hex().upper()!=size['rawHex'] or pointer-image.pe.image_base!=size['pointerRva']:
        fail('pair-type-size-record',size,[pointer-image.pe.image_base,raw.hex()])
    boxed_size,native_size=struct.unpack_from('<II',raw)
    if boxed_size-IL2CPP_OBJECT_HEADER!=c['unboxedSize'] or native_size!=c['unboxedSize']:
        fail('pair-type-size-correspondence','boxed size minus header equals registered native value size',[boxed_size,native_size,c['unboxedSize']])
    string=types._ancestry(image,c['stringLayout']['definition'])[0]
    if string!=c['stringLayout'] or string['name']!='System.String':fail('pair-string-owner',c['stringLayout'],string)
    lengths=[f for f in string['fields'] if f['name']=='_stringLength']
    if (len(lengths)!=1 or lengths[0]['type']['kind']!=8 or lengths[0]['type']['name']!='int'
            or int.from_bytes(bytes.fromhex(lengths[0]['type']['rawHex'])[8:10],'little')&0x10
            or string['offsets']['_stringLength']!=c['stringLengthOffset']):
        fail('pair-string-length','owned instance Int32 length field and actual offset',lengths)
    for name,parameters in [('numeric',[(14,'string',False),(13,'double',False),(2,'bool',False)]),
            ('string',[(14,'string',False),(14,'string',False),(2,'bool',False)]),
            ('copy',[(17,'Beyond.Blackboard+DataPair',False)])]:
        proof=c['constructors'][name];method=proof['method']
        if method[1:3]!=['Beyond.Blackboard+DataPair','.ctor']:fail('pair-constructor-name',name,method)
        signature(image,method,(1,'void'),parameters,static=False,fail=fail)
        _owned(index,image,method,proof,fail)
    numeric=c['numericPredicate'];method=numeric['method']
    if method[1:3]!=['Beyond.Blackboard+DataPair','get_isNumericValue']:fail('pair-numeric-name','actual owned numeric getter',method)
    signature(image,method,(2,'bool'),[],static=False,fail=fail)
    if set(numeric['paths'])!={'null','empty','nonempty'}:fail('pair-numeric-paths','all three selected normal returns',list(numeric['paths']))
    for proof in numeric['paths'].values():_owned(index,image,method,proof,fail)
    item=c['listItem'];method=item['method'];m=image.metadata.methods[method[0]]
    if (image.type_name(m.declaring_type)!='System.Collections.Generic.List`1' or image.metadata.string(m.name_index)!='get_Item'
            or method[1:3]!=['System.Collections.Generic.List`1','get_Item'] or m.flags&0x10 or m.generic_container_index>=0):
        fail('pair-list-definition','instance get_Item on type-generic List definition',method)
    result=types._type_row(image,m.return_type);parameters=[types._type_row(image,p.type_index) for p in image.metadata.parameters_for(m)]
    if result['kind']!=0x13 or bytes.fromhex(result['rawHex'])[11]&0x20 or [(p['kind'],p['name'],bool(bytes.fromhex(p['rawHex'])[11]&0x20)) for p in parameters]!=[(8,'int',False)]:
        fail('pair-list-signature','return type VAR and one ordinary Int32 parameter',[result,parameters])
    ordinal=type_parameter_owner(image.metadata.buf,int.from_bytes(bytes.fromhex(result['rawHex'])[:8],'little'),
        [t.generic_container_index for t in image.metadata.types],source=LABEL)
    if ordinal!=c['listReturnParameterOwner'] or ordinal['typeIndex']!=m.declaring_type or ordinal['ordinal']!=0:
        fail('pair-list-return-var','reciprocal List type parameter zero',ordinal)
    try:
        registered=json.loads(json.dumps(GenericEntries(image).resolve(m.index,['Beyond.Blackboard+DataPair'],[])))
    except ValueError as error:
        fail('pair-closed-list-registration','one unique current closed get_Item entry',str(error))
    if registered!=c['listRegistration'] or registered['pointer']!=image.pe.image_base+method[3]:
        fail('pair-closed-list-registration',c['listRegistration'],registered)
    arguments=registered['classInstantiation']['arguments']
    if len(arguments)!=1 or bytes.fromhex(arguments[0]['raw_type_record_hex'])[10]!=0x11 or int.from_bytes(bytes.fromhex(arguments[0]['raw_type_record_hex'])[:8],'little')!=td.index:
        fail('pair-closed-list-value-argument','same actual DataPair value type',arguments)
    board=types._ancestry(image,c['blackboardTypeDefinition'])
    if board!=c['blackboardAncestry'] or board[0]['name']!='Beyond.Blackboard':fail('pair-board-ancestry',c['blackboardAncestry'],board)
    parent=board[0]['parent']
    if parent['kind']!=0x15 or parent['definition']!=m.declaring_type or [a['name'] for a in parent['arguments']]!=['Beyond.Blackboard+DataPair']:
        fail('pair-board-closed-list','Blackboard directly inherits the selected List<DataPair>',parent)
    _owned(index,image,method,item,fail)
    return {'nongenericNamedFieldOwnershipProved':True,'commonBoxedToUnboxedBias':IL2CPP_OBJECT_HEADER,
        'boxedSize':boxed_size,'nativeValueSize':native_size,'closedListReturnType':'Beyond.Blackboard+DataPair',
        'reciprocalListReturnVarProved':True,'blackboardClosedListBaseProved':True,
        'runtimeClosedListReceiverObserved':False,'openGenericFieldOffsetsUsed':False}


def validate_current_native_contract(*,gameassembly: Path,metadata: Path) -> dict[str,Any]:
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return _skip(gate.status,gate.detail,pins)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file():return _skip('missing','UnityPlayer.dll missing beside selected native image',pins)
    if _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:return _skip('mismatched','Selected UnityPlayer.dll hash differs',pins)
    paths=set(_package_import_closure(Path(__file__)))|{CONTRACT_PATH,BARRIER_CONTRACT_PATH,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH}
    inputs={r['path']:r for r in (_fingerprint(p) for p in paths)}
    barrier,_=read_reviewed_contract(BARRIER_CONTRACT_PATH,schema='endfield.buff-timeline-source-wrappers-native-contract.v1',status='exact-current-build',label=LABEL)
    if barrier['nativeInputs']!=pins:return _skip('mismatched','Shared barrier declaration belongs to another build',pins)
    image=open_native_image(gate.gameassembly,gate.metadata);index=BodyIndex(image)
    barrier_proof=barrier['barrierProgram']
    # The physical barrier is a leaf without a pdata extent. Its authenticated
    # entry/JE/RET selected CFG and both constructor call targets establish
    # the complete disabled path; no unwind boundary or enabled path is claimed.
    identity=_validate_identity(image,c,index,fail=_fail)
    transfers=program.validate(image,c,barrier_proof,fail=_fail)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return _skip(after.status,after.detail,pins)
    if not unity.is_file() or _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:
        return _skip('missing' if not unity.is_file() else 'mismatched','Selected UnityPlayer.dll changed during validation',pins)
    for before in inputs.values():
        actual=_fingerprint(Path(before['path']))
        if actual!=before:_fail('source-drift',before,actual)
    return {'status':'validated','nativeInputs':pins,'identity':identity,'transfers':transfers,
        'boxedToUnboxedCellCorrespondenceProved':True,'closedListFieldFlowProved':True,
        'numericPredicateSelectedReturnsProved':True,'runtimeExecutionKnown':False,
        'wholeLookupControlFlowProved':False,'actualLookupFoundValueProved':False,
        'wholeActionAdmitted':False,'wholeRootAdmitted':False,
        'provenance':{'inputs':sorted(inputs.values(),key=lambda r:r['path'])},'evidenceBoundary':c['evidenceBoundary']}
