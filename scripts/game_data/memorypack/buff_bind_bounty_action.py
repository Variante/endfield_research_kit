"""BindBountyEnemy storage with an independently bounded BlackboardString.

Evidence and admission boundary:

Exact inherited byte/three-DWORD prefix is followed by independently typed
BlackboardString bountyKey. Short/extended physical tag encodings preserve
original spans; null parent/child and null/empty payloads differ. Arbitrary
payload bytes, including invalid UTF-8, stay raw. No bounty/enemy identity,
evaluated binding or whole-root admission follows from this child receipt.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import buff_blackboard_string_child_receipt as string
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader

LABEL='buffBindBountyAction'
CONTRACT_PATH=CONTRACTS_DIR/'buff_bind_bounty_action_native.json'
SCHEMA='endfield.buff-bind-bounty-action-native-contract.v1'
RECORD='bindBounty'
ORDER=[('isEnable','byte'),('priorityLevel','scalar32'),('priorityOffset','scalar32'),
       ('serverActionIndex','scalar32'),('bountyKey','blackboard-string-profile')]

def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if (set(c['records'])!={RECORD} or c['actionDispatch']!={'23':RECORD}
            or [(m['fieldName'],m['kind']) for m in c['records'][RECORD]['members']]!=ORDER
            or c['childSourceContract']!=string.CONTRACT_PATH.name
            or c['records'][RECORD]['members'][-1]['declaredType']!=string.STRING_TYPE):
        raise ValueError(LABEL+'.contract-shape')
    return c

def supported_tags():return frozenset(map(int,_contract()['actionDispatch']))
def _members(c):return {RECORD:[{'fieldName':m['fieldName'],'kind':m['kind']} for m in c['records'][RECORD]['members']]}
def _child(c,audit):
    if (audit.get('status')!='validated' or audit.get('nativeInputs')!=c['nativeInputs']
            or audit.get('selectedReadOrder')!=list(string.READ_ORDER)):
        raise ValueError(LABEL+'.independent-string-child')

def validate_current_native_contract(*,children,gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    def empty(status,detail):return {'status':status,'detail':detail,'nativeInputs':pins,'recordMembers':{},'actionDispatch':{}}
    if gate.status!='validated':return empty(gate.status,gate.detail)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def match():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not match():return empty('mismatched' if unity.is_file() else 'missing','UnityPlayer.dll missing or mismatched')
    _child(c,children.get('blackboardString',{}))
    image=open_native_image(gate.gameassembly,gate.metadata);record=c['records'][RECORD]
    path=CONTRACTS_DIR/record['sourceContract'];source=json.loads(path.read_bytes())
    buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,image.modules,image.owners,source=str(gate.gameassembly),contract_path=path, native_image=image)
    def fail(check,expected,actual,**details):
        raise ValueError(LABEL+'.'+check+':'+json.dumps({'source':str(path),'nativeInputs':pins,
            'expected':str(expected)[:500],'actual':str(actual)[:500],'details':details}))
    proved=named.validate_named_records(image,source,c['records'],label=LABEL,fail=fail)
    routes,audit=load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata);route=routes.get(23)
    if (audit.get('status')!='validated' or route is None or route.status!='resolved'
            or route.wrapper_name!=record['wrapperTypeName']
            or list(route.member_order)!=[m['fieldName'] for m in record['members']]
            or list(route.member_declared_types)!=[m['declaredType'] for m in record['members']]):
        fail('current-route',record['wrapperTypeName'],None if route is None else route.row())
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not match():return empty(after.status if after.status!='validated' else 'mismatched','native inputs changed during validation')
    return {'status':'validated','nativeInputs':pins,'recordMembers':proved,'actionDispatch':c['actionDispatch'],
            'runtimeExecutionKnown':False,'evidenceBoundary':c['evidenceBoundary']}

def decode_action(data,*,source,digest,start,end,tag,native_validation):
    c=_contract();children=native_validation.get('children',{});audit=children.get('bindBounty',{})
    if (native_validation.get('status')!='validated' or audit.get('status')!='validated'
            or native_validation.get('nativeInputs')!=c['nativeInputs'] or audit.get('nativeInputs')!=c['nativeInputs']
            or audit.get('recordMembers')!=_members(c) or audit.get('actionDispatch')!=c['actionDispatch']
            or type(tag)is not int or tag!=23 or not isinstance(data,bytes) or not source or not isinstance(digest,str)
            or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start)is not int or type(end)is not int or not 0<=start<end<=len(data)):
        raise ValueError(LABEL+'.decode:native-source-or-span')
    child_native=children.get('blackboardString',{});_child(c,child_native)
    reader=Reader(data,source,end);reader.pos=start
    if reader.nested_union_tag((23,),'bind-bounty-action')!=23:raise ValueError(LABEL+'.physical-tag')
    fields=[];record=c['records'][RECORD]
    if reader.peek()==255:reader.take(1,'null-bind-bounty-wrapper')
    else:
        reader.header(5)
        for member in record['members']:
            a=reader.pos;kind=member['kind'];value={}
            if kind in ('byte','scalar32'):
                value['rawHex']=reader.take(1 if kind=='byte' else 4,member['fieldName']).hex().upper()
            elif kind=='blackboard-string-profile':
                reader.paired_payload()
                child=string.decode_blackboard_string_value(data,source=source,logical_sha256=digest,
                    start=a,end=reader.pos,native_validation=child_native)
                if child.get('wholeStoredSpanExact')is not True or [child.get('start'),child.get('end')]!=[a,reader.pos]:
                    raise ValueError(LABEL+'.independent-child-span')
                value['child']={**child,'recursiveStoredSchemaExact':True}
            else:raise ValueError(LABEL+'.unsupported-kind')
            fields.append({'fieldName':member['fieldName'],'declaredType':member['declaredType'],'kind':kind,'start':a,'end':reader.pos,**value})
    if reader.pos!=end:raise ValueError(LABEL+'.required-action-end')
    return {'schema':'endfield.buff-bind-bounty-action-receipt.v1','source':source,'logicalSha256':digest.upper(),
            'tag':tag,'typeName':record['runtimeTypeName'],'start':start,'end':end,'namedFields':fields,
            'isNull':not fields,'recursiveStoredSchemaExact':True,'wholeBuffDataExact':False,'runtimeExecutionKnown':False}
