"""ContinuousFindTarget named operands with checked direct and recursive joins."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack import named_native_records as named, direct_float_sources as floats
from scripts.game_data.memorypack import utf8_source_helper as strings
from scripts.game_data.memorypack import buff_find_target_action as selection
from scripts.game_data.memorypack import buff_direction_target_children as direction
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader

LABEL='buffContinuousFindTarget'
RECORD='continuousFindTarget'
TAG=138
CONTRACT_PATH=CONTRACTS_DIR/'buff_continuous_find_target_native.json'
FIELDS=('isEnable','priorityLevel','priorityOffset','serverActionIndex','advancedSelectorDirection',
    'center','centerContextKey','centerMountPoint','centerToGround','contextKey','selectorData',
    'selectorDirection','selectorOwner','selectorOwnerContextKey','target','targetGroupKey',
    'useAdvancedDirectionSetting','useCenterEntityMountPoint','findInterval')
KINDS=('byte','scalar32','scalar32','scalar32','direction','scalar32','byte-payload','scalar32',
    'byte','byte-payload','selector','scalar32','scalar32','byte-payload','scalar32','byte-payload',
    'byte','byte','raw-float32-bits')


def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.buff-continuous-find-target-native-contract.v1',status='exact-current-build',label=LABEL)
    r=c['records'].get(RECORD,{})
    if (set(c['records'])!={RECORD} or c['actionDispatch']!={str(TAG):RECORD}
            or tuple(m['fieldName'] for m in r['members'])!=FIELDS
            or tuple(m['kind'] for m in r['members'])!=KINDS
            or c['stringSourceContract']!=strings.CONTRACT_PATH.name or not c.get('sourceWindows')
            or r['members'][4]['declaredType']!=selection.direction.DIRECTION_TYPE
            or r['members'][10]['declaredType']!=selection.selector.SELECTOR_TYPE):
        raise ValueError(LABEL+'.contract-shape')
    return c


def supported_tags():return frozenset((TAG,))
def _members(c):return {RECORD:[{'fieldName':m['fieldName'],'kind':m['kind']} for m in c['records'][RECORD]['members']]}


def _string(c,audit):
    s=strings._contract()
    if (audit.get('status')!='validated' or audit.get('nativeInputs')!=c['nativeInputs']
            or audit.get('sourceHelpers')!=s['sourceHelpers'] or audit.get('wireEncoding')!=s['wireEncoding']):
        raise ValueError(LABEL+'.independent-string-source')


def validate_current_native_contract(*,children,string_native=None,gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    def empty(status,detail):return {'status':status,'detail':detail,'nativeInputs':pins,'recordMembers':{},'actionDispatch':{}}
    if gate.status!='validated':return empty(gate.status,gate.detail)
    unity=gate.gameassembly.parent/'UnityPlayer.dll'
    def match():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not match():return empty('mismatched' if unity.is_file() else 'missing','UnityPlayer.dll missing or mismatched')
    string=children.get('blackboardInt',{}).get('stringSource',{}) if string_native is None else string_native
    _string(c,string)
    for name in ('direction','selector'):
        child=children.get(name,{})
        if child.get('status')!='validated' or child.get('nativeInputs')!=pins:
            raise ValueError(LABEL+'.independent-child:'+name)
    image=open_native_image(gate.gameassembly,gate.metadata);record=c['records'][RECORD]
    path=CONTRACTS_DIR/record['sourceContract'];source=json.loads(path.read_bytes())
    buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,image.modules,image.owners,source=str(gate.gameassembly),contract_path=path)
    source['codeWindows'].extend(c['sourceWindows'])
    def fail(check,expected,actual,**details):
        raise ValueError(LABEL+'.'+check+':'+json.dumps({'source':str(path),'nativeInputs':pins,
            'expected':str(expected)[:700],'actual':str(actual)[:700],'details':details}))
    transfer=floats.validate_direct_float_source(image,source,record,record['members'][-1],fail=fail)
    proved=named.validate_named_records(image,source,c['records'],label=LABEL,fail=fail)
    for member in record['members']:
        if member['kind']=='byte-payload' and (member['declaredType']!='string' or member['sourceCall']['targetRva'] not in string['sourceHelpers']):
            fail('string-source',string['sourceHelpers'],member['sourceCall'],field=member['fieldName'])
    routes,audit=load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata);route=routes.get(TAG)
    if (audit.get('status')!='validated' or route is None or route.status!='resolved'
            or route.wrapper_name!=record['wrapperTypeName'] or route.inherited_member_count!=record['inheritedMemberCount']
            or list(route.member_order)!=list(FIELDS)
            or list(route.member_declared_types)!=[m['declaredType'] for m in record['members']]):
        fail('current-route',record['wrapperTypeName'],None if route is None else route.row())
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not match():return empty(after.status if after.status!='validated' else 'mismatched','native inputs changed during validation')
    return {'status':'validated','nativeInputs':pins,'recordMembers':proved,'actionDispatch':c['actionDispatch'],
        'stringSource':string,'directFloatTransfer':transfer,'runtimeExecutionKnown':False,'evidenceBoundary':c['evidenceBoundary']}


def decode_action(data,*,source,digest,start,end,tag,native_validation,target_decoder=None,depth=0):
    c=_contract();children=native_validation.get('children',{});audit=children.get(RECORD,{})
    if (native_validation.get('status')!='validated' or audit.get('status')!='validated'
            or native_validation.get('nativeInputs')!=c['nativeInputs'] or audit.get('nativeInputs')!=c['nativeInputs']
            or audit.get('recordMembers')!=_members(c) or audit.get('actionDispatch')!=c['actionDispatch']
            or audit.get('directFloatTransfer',{}).get('storedFloatTransferProved') is not True
            or type(tag)is not int or tag!=TAG or not isinstance(data,bytes) or not source or not isinstance(digest,str)
            or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start)is not int or type(end)is not int or not 0<=start<end<=len(data)):
        raise ValueError(LABEL+'.decode:native-source-or-span')
    _string(c,audit.get('stringSource',{}))
    for name in ('direction','selector'):
        if children.get(name,{}).get('status')!='validated' or children[name].get('nativeInputs')!=c['nativeInputs']:
            raise ValueError(LABEL+'.decode:independent-child:'+name)
    reader=Reader(data,source,end);reader.pos=start
    if reader.nested_union_tag((TAG,),'continuous-find-target')!=TAG:raise ValueError(LABEL+'.physical-tag')
    members=c['records'][RECORD]['members'];fields=[]
    minimum=lambda m:4 if m['kind'] in ('scalar32','raw-float32-bits','byte-payload') else 1
    if reader.peek()==255:reader.take(1,'null-continuous-find-target-wrapper')
    else:
        reader.header(len(members))
        for n,member in enumerate(members):
            a=reader.pos;kind=member['kind'];value={}
            if kind in ('byte','scalar32','raw-float32-bits'):
                value['rawHex']=reader.take(1 if kind=='byte' else 4,member['fieldName']).hex().upper()
            elif kind=='byte-payload':
                reader.byte_payload(reserve=sum(minimum(m) for m in members[n+1:]))
                value['child']=strings.decode_source_string(data,source=source,digest=digest,start=a,end=reader.pos,
                    source_helper_rva=member['sourceCall']['targetRva'],native_validation=audit['stringSource'])
            elif kind=='direction':
                reader.direction_profile()
                value['child']=direction.decode_direction(data,source=source,digest=digest,start=a,end=reader.pos,
                    children=children,target_decoder=target_decoder,depth=depth)
            elif kind=='selector':
                reader.selector_profile()
                if data[a:reader.pos]==b'\xff':
                    value['child']={'start':a,'end':reader.pos,'status':'exact-null','recursiveStoredSchemaExact':True}
                else:
                    value['child']=selection.decode_selector(data,source,digest,a,reader.pos,children,
                        target_decoder=target_decoder,depth=depth)
            else:raise ValueError(LABEL+'.unsupported-kind')
            if kind in ('direction','selector') and value['child'].get('recursiveStoredSchemaExact')is not True:
                raise ValueError(LABEL+'.recursive-child-incomplete')
            fields.append({'fieldName':member['fieldName'],'declaredType':member['declaredType'],'kind':kind,
                'start':a,'end':reader.pos,**value})
    if reader.pos!=end:raise ValueError(LABEL+'.required-action-end')
    return {'schema':'endfield.buff-continuous-find-target-receipt.v1','source':source,'logicalSha256':digest.upper(),
        'tag':tag,'typeName':c['records'][RECORD]['runtimeTypeName'],'start':start,'end':end,'namedFields':fields,
        'isNull':not fields,'recursiveStoredSchemaExact':True,'wholeBuffDataExact':False,'runtimeExecutionKnown':False}
