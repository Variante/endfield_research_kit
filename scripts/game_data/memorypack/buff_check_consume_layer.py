"""CheckConsumeBuffLayer storage using the independently owned BlackboardInt.

The comparison enum, integer operand and destination key remain unevaluated.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import buff_pick_target_action as integer
from scripts.game_data.memorypack import utf8_source_helper as strings
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader

LABEL='buffCheckConsumeLayer'
CONTRACT_PATH=CONTRACTS_DIR/'buff_check_consume_layer_native.json'
SCHEMA='endfield.buff-check-consume-layer-native-contract.v1'
RECORD='checkConsumeLayer'
ORDER=[('isEnable','byte'),('priorityLevel','scalar32'),('priorityOffset','scalar32'),
       ('serverActionIndex','scalar32'),('compareType','scalar32'),('num','scalar-payload'),('storeKey','byte-payload')]

def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if (set(c['records'])!={RECORD} or c['actionDispatch']!={'63':RECORD}
            or [(m['fieldName'],m['kind']) for m in c['records'][RECORD]['members']]!=ORDER
            or c['integerOwnerContract']!=integer.CONTRACT_PATH.name
            or c['stringSourceContract']!=strings.CONTRACT_PATH.name):
        raise ValueError(LABEL+'.contract-shape')
    return c

def supported_tags():return frozenset(map(int,_contract()['actionDispatch']))

def _members(c):return {RECORD:[{'fieldName':m['fieldName'],'kind':m['kind']} for m in c['records'][RECORD]['members']]}

def _integer_join(c,audit):
    child=integer._contract();record=child['records']['integer'];member=c['records'][RECORD]['members'][5]
    if (audit.get('status')!='validated' or audit.get('nativeInputs')!=c['nativeInputs']
            or child['nativeInputs']!=c['nativeInputs']
            or audit.get('integerMemberNames')!=list(integer.INTEGER_NAMES)
            or member['declaredType']!=record['runtimeTypeName']
            or c['integerReaderMethod']!=record['readerMethod']
            or c['integerRuntimeTypeDefinition']!=record['runtimeTypeDefinition']):
        raise ValueError(LABEL+'.independent-integer-join')

def validate_current_native_contract(*,children,gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    def empty(status,detail):return {'status':status,'detail':detail,'nativeInputs':pins,'recordMembers':{},'actionDispatch':{}}
    if gate.status!='validated':return empty(gate.status,gate.detail)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def match():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not match():return empty('mismatched' if unity.is_file() else 'missing','UnityPlayer.dll missing or mismatched')
    _integer_join(c,children.get('blackboardInt',{}))
    string=children['blackboardInt'].get('stringSource',{})
    if string.get('status')!='validated' or string.get('nativeInputs')!=pins:
        return empty(string.get('status','unresolved'),'string source native gate did not validate')
    image=open_native_image(gate.gameassembly,gate.metadata);record=c['records'][RECORD]
    path=CONTRACTS_DIR/record['sourceContract'];source=json.loads(path.read_bytes())
    buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,image.modules,image.owners,source=str(gate.gameassembly),contract_path=path)
    def fail(check,expected,actual,**details):
        raise ValueError(LABEL+'.'+check+':'+json.dumps({'source':str(path),'expected':str(expected)[:500],'actual':str(actual)[:500],'details':details}))
    proved=named.validate_named_records(image,source,c['records'],label=LABEL,fail=fail)
    context=next(x for x in source['nestedContexts'] if x['instructionRva']==record['members'][5]['sourceContextInstructionRva'])
    if context['typeDefinition']!=c['integerRuntimeTypeDefinition']:fail('integer-context-definition',c['integerRuntimeTypeDefinition'],context['typeDefinition'])
    if record['members'][-1]['sourceCall']['targetRva'] not in string['sourceHelpers']:
        fail('final-string-source',string['sourceHelpers'],record['members'][-1]['sourceCall'])
    routes,audit=load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata);route=routes.get(63)
    if (audit.get('status')!='validated' or route is None or route.status!='resolved'
            or route.wrapper_name!=record['wrapperTypeName']
            or list(route.member_order)!=[m['fieldName'] for m in record['members']]
            or list(route.member_declared_types)!=[m['declaredType'] for m in record['members']]):
        fail('current-route',record['wrapperTypeName'],None if route is None else route.row())
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not match():return empty(after.status if after.status!='validated' else 'mismatched','native inputs changed during validation')
    return {'status':'validated','nativeInputs':pins,'recordMembers':proved,'actionDispatch':c['actionDispatch'],
            'stringSource':string,'integerReaderMethod':c['integerReaderMethod'],'runtimeExecutionKnown':False,'evidenceBoundary':c['evidenceBoundary']}

def decode_action(data,*,source,digest,start,end,tag,native_validation):
    c=_contract();children=native_validation.get('children',{});audit=children.get('consumeLayer',{})
    if (native_validation.get('status')!='validated' or audit.get('status')!='validated'
            or native_validation.get('nativeInputs')!=c['nativeInputs'] or audit.get('nativeInputs')!=c['nativeInputs']
            or audit.get('recordMembers')!=_members(c) or audit.get('actionDispatch')!=c['actionDispatch']
            or audit.get('integerReaderMethod')!=c['integerReaderMethod'] or type(tag)is not int or tag!=63
            or not isinstance(data,bytes) or not source or not isinstance(digest,str)
            or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start)is not int or type(end)is not int or not 0<=start<end<=len(data)):
        raise ValueError(LABEL+'.decode:native-source-or-span')
    _integer_join(c,children.get('blackboardInt',{}))
    reader=Reader(data,source,end);reader.pos=start
    if data[start:start+1]!=bytes((63,)):raise ValueError(LABEL+'.physical-tag')
    if reader.nested_union_tag((63,),'check-consume-layer')!=63:raise ValueError(LABEL+'.physical-tag')
    fields=[];record=c['records'][RECORD]
    if reader.peek()==255:reader.take(1,'null-consume-layer')
    else:
        reader.header(7)
        for member in record['members']:
            a=reader.pos;kind=member['kind'];value={}
            if kind in ('byte','scalar32'):
                value['rawHex']=reader.take(1 if kind=='byte' else 4,member['fieldName']).hex().upper()
            elif kind=='scalar-payload':
                if end-reader.pos<5:raise ValueError(LABEL+'.integer-and-required-key-tail')
                bounded=Reader(data,source,end-4);bounded.pos=reader.pos;bounded.scalar_payload();reader.pos=bounded.pos
                value['child']=integer.decode_integer_value(data,source=source,digest=digest,start=a,end=reader.pos,native_validation=children['blackboardInt'])
            elif kind=='byte-payload':
                reader.byte_payload()
                value['child']=strings.decode_source_string(data,source=source,digest=digest,start=a,end=reader.pos,
                    source_helper_rva=member['sourceCall']['targetRva'],native_validation=audit['stringSource'])
            else:raise ValueError(LABEL+'.unsupported-kind')
            fields.append({'fieldName':member['fieldName'],'declaredType':member['declaredType'],'kind':kind,'start':a,'end':reader.pos,**value})
    if reader.pos!=end:raise ValueError(LABEL+'.required-action-end')
    return {'schema':'endfield.buff-check-consume-layer-action-receipt.v1','source':source,'logicalSha256':digest.upper(),
            'tag':tag,'typeName':record['runtimeTypeName'],'start':start,'end':end,'namedFields':fields,
            'isNull':not fields,'recursiveStoredSchemaExact':True,'wholeBuffDataExact':False,'runtimeExecutionKnown':False}
