"""Named stored archery-chip keys/flags; runtime effects remain unevaluated."""
from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack import named_native_records as named,utf8_source_helper as strings
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader

LABEL='buffArcheryChipAction'
CONTRACT_PATH=CONTRACTS_DIR/'buff_archery_chip_action_native.json'
SCHEMA='endfield.buff-archery-chip-action-native-contract.v1'
RECORD='archeryChip'
FIELDS=('isEnable','priorityLevel','priorityOffset','serverActionIndex','extraArrowKey','extraRicochetKey',
    'hasMachineGunFeatureKey','isRapidFireArrowKey','needSaveHasMachineGunFeature','needSaveProjectileID',
    'needSaveRemainBounceCount','needSaveSkillTrajectoryType','needSaveSplitCountKey','projectileIDKey',
    'remainBounceCountKey','saveAffix','skillTrajectoryTypeKey','splitCountKey')
KINDS=('byte','scalar32','scalar32','scalar32')+('nullable-byte-payload',)*4+('byte',)*5+('nullable-byte-payload',)*2+('byte',)+('nullable-byte-payload',)*2

def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if (set(c['records'])!={RECORD} or c['actionDispatch']!={'398':RECORD}
            or tuple(m['fieldName'] for m in c['records'][RECORD]['members'])!=FIELDS
            or tuple(m['kind'] for m in c['records'][RECORD]['members'])!=KINDS
            or c['stringSourceContract']!=strings.CONTRACT_PATH.name):
        raise ValueError(LABEL+'.contract-shape')
    return c

def supported_tags():return frozenset(map(int,_contract()['actionDispatch']))
def _members(c):return {RECORD:[{'fieldName':m['fieldName'],'kind':m['kind']} for m in c['records'][RECORD]['members']]}
def _string(c,audit):
    s=strings._contract()
    if (audit.get('status')!='validated' or audit.get('nativeInputs')!=c['nativeInputs']
            or audit.get('sourceHelpers')!=s['sourceHelpers'] or audit.get('wireEncoding')!=s['wireEncoding']):
        raise ValueError(LABEL+'.independent-string-source')

def validate_current_native_contract(*,children,gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    def empty(status,detail):return {'status':status,'detail':detail,'nativeInputs':pins,'recordMembers':{},'actionDispatch':{}}
    if gate.status!='validated':return empty(gate.status,gate.detail)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def match():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not match():return empty('mismatched' if unity.is_file() else 'missing','UnityPlayer.dll missing or mismatched')
    string=children.get('blackboardInt',{}).get('stringSource',{});_string(c,string)
    image=open_native_image(gate.gameassembly,gate.metadata);record=c['records'][RECORD]
    path=CONTRACTS_DIR/record['sourceContract'];source=json.loads(path.read_bytes())
    buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,image.modules,image.owners,source=str(gate.gameassembly),contract_path=path)
    def fail(check,expected,actual,**details):
        raise ValueError(LABEL+'.'+check+':'+json.dumps({'source':str(path),'nativeInputs':pins,'expected':str(expected)[:500],'actual':str(actual)[:500],'details':details}))
    proved=named.validate_named_records(image,source,c['records'],label=LABEL,fail=fail)
    for member in record['members']:
        if member['kind']=='nullable-byte-payload' and (member['declaredType']!='string' or member['sourceCall']['targetRva'] not in string['sourceHelpers']):
            fail('string-source',string['sourceHelpers'],member['sourceCall'],field=member['fieldName'])
    routes,audit=load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata);route=routes.get(398)
    if (audit.get('status')!='validated' or route is None or route.status!='resolved'
            or route.wrapper_name!=record['wrapperTypeName']
            or list(route.member_order)!=[m['fieldName'] for m in record['members']]
            or list(route.member_declared_types)!=[m['declaredType'] for m in record['members']]):
        fail('current-route',record['wrapperTypeName'],None if route is None else route.row())
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not match():return empty(after.status if after.status!='validated' else 'mismatched','native inputs changed during validation')
    return {'status':'validated','nativeInputs':pins,'recordMembers':proved,'actionDispatch':c['actionDispatch'],'stringSource':string,
            'runtimeExecutionKnown':False,'evidenceBoundary':c['evidenceBoundary']}

def decode_action(data,*,source,digest,start,end,tag,native_validation):
    c=_contract();audit=native_validation.get('children',{}).get('archeryChip',{})
    if (native_validation.get('status')!='validated' or audit.get('status')!='validated'
            or native_validation.get('nativeInputs')!=c['nativeInputs'] or audit.get('nativeInputs')!=c['nativeInputs']
            or audit.get('recordMembers')!=_members(c) or audit.get('actionDispatch')!=c['actionDispatch']
            or type(tag)is not int or tag!=398 or not isinstance(data,bytes) or not source or not isinstance(digest,str)
            or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start)is not int or type(end)is not int or not 0<=start<end<=len(data)):
        raise ValueError(LABEL+'.decode:native-source-or-span')
    _string(c,audit.get('stringSource',{}))
    if data[start:start+3]!=b'\xfa'+struct.pack('<H',398):raise ValueError(LABEL+'.physical-tag')
    reader=Reader(data,source,end);reader.pos=start
    if reader.nested_union_tag((398,),'archery-chip-action')!=398:raise ValueError(LABEL+'.physical-tag')
    members=c['records'][RECORD]['members'];fields=[]
    minimum=lambda m:4 if m['kind'] in ('nullable-byte-payload','scalar32') else 1
    if reader.peek()==255:reader.take(1,'null-archery-chip-wrapper')
    else:
        reader.header(18)
        for n,member in enumerate(members):
            a=reader.pos;kind=member['kind'];value={}
            if kind in ('byte','scalar32'):
                value['rawHex']=reader.take(1 if kind=='byte' else 4,member['fieldName']).hex().upper()
            elif kind=='nullable-byte-payload':
                reader.byte_payload(reserve=sum(minimum(m) for m in members[n+1:]))
                value['child']=strings.decode_source_string(data,source=source,digest=digest,start=a,end=reader.pos,
                    source_helper_rva=member['sourceCall']['targetRva'],native_validation=audit['stringSource'])
            else:raise ValueError(LABEL+'.unsupported-kind')
            fields.append({'fieldName':member['fieldName'],'declaredType':member['declaredType'],'kind':kind,'start':a,'end':reader.pos,**value})
    if reader.pos!=end:raise ValueError(LABEL+'.required-action-end')
    return {'schema':'endfield.buff-archery-chip-action-receipt.v1','source':source,'logicalSha256':digest.upper(),
            'tag':tag,'typeName':c['records'][RECORD]['runtimeTypeName'],'start':start,'end':end,'namedFields':fields,
            'isNull':not fields,'recursiveStoredSchemaExact':True,'wholeBuffDataExact':False,'runtimeExecutionKnown':False}
