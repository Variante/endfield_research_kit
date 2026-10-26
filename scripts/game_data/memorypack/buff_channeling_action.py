"""Channeling stored fields and independently owned sequence/target children."""
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack import named_native_records as named,buff_sequence as sequence
from scripts.game_data.memorypack import buff_target_settings_child_receipt as target
from scripts.game_data.memorypack.mixed_action_output_sources import validate_mixed_action_outputs
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader,SEQUENCE_RECURSION_LIMIT

LABEL='buffChannelingAction'
CONTRACT_PATH=CONTRACTS_DIR/'buff_channeling_action_native.json'
ORDER=[('isEnable','byte'),('priorityLevel','scalar32'),('priorityOffset','scalar32'),('serverActionIndex','scalar32'),
       ('actionOnTick','sequence'),('executeEachFrame','byte'),('maxCountPerTarget','scalar32'),
       ('targetSettings','target-profile'),('targetTriggerInterval','raw4'),('triggerInterval','raw4')]

def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.buff-channeling-action-native-contract.v1',status='exact-current-build',label=LABEL)
    if (set(c['records'])!={'channeling'} or c['actionDispatch']!={'47':'channeling'}
        or [(m['fieldName'],m['kind']) for m in c['records']['channeling']['members']]!=ORDER
        or c['sequenceSourceContract']!=sequence.CONTRACT_PATH.name or c['targetSourceContract']!=target.modify.SOURCE_CONTRACT.name
        or c['records']['channeling']['members'][4]['declaredType']!=sequence.TYPE_NAME
        or c['records']['channeling']['members'][7]['declaredType']!=target.TARGET_TYPE):
        raise ValueError(LABEL+'.contract-shape')
    return c

def supported_tags():return frozenset(map(int,_contract()['actionDispatch']))
def _members(c):return {k:[{'fieldName':m['fieldName'],'kind':m['kind']} for m in r['members']] for k,r in c['records'].items()}

def _children(c,children):
    for name in ('target','sequence'):
        proof=children.get(name,{})
        if proof.get('status')!='validated' or proof.get('nativeInputs')!=c['nativeInputs']:
            raise ValueError(LABEL+'.independent-child:'+name)
    seq=children['sequence']
    if seq.get('typeName')!=sequence.TYPE_NAME or seq.get('readOrder')!=sequence.READ_ORDER:
        raise ValueError(LABEL+'.sequence-source-type')
    if len(children['target'].get('targetMemberNames',[]))!=13:
        raise ValueError(LABEL+'.target-source-shape')

def validate_current_native_contract(*,children,gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contract();pins=c['nativeInputs']
    def empty(status,detail):return {'status':status,'detail':detail,'nativeInputs':pins,'recordMembers':{},'actionDispatch':{}}
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return empty(gate.status,gate.detail)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def match():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not match():return empty('mismatched' if unity.is_file() else 'missing','UnityPlayer.dll missing or mismatched')
    _children(c,children)
    image=open_native_image(gate.gameassembly,gate.metadata);record=c['records']['channeling']
    path=CONTRACTS_DIR/record['sourceContract'];source=json.loads(path.read_bytes())
    buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,image.modules,image.owners,source=str(gate.gameassembly),contract_path=path, native_image=image)
    source['codeWindows'].extend(c['sourceWindows'])
    def fail(check,expected,actual,**details):raise ValueError(LABEL+'.'+check+':'+json.dumps({'source':str(path),'expected':str(expected)[:700],'actual':str(actual)[:700],'details':details}))
    output=validate_mixed_action_outputs(image,source,record,fail=fail)
    proved=named.validate_named_records(image,source,c['records'],label=LABEL,fail=fail)
    routes,audit=load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata);route=routes.get(47)
    if (audit.get('status')!='validated' or route is None or route.status!='resolved' or route.wrapper_name!=record['wrapperTypeName']
        or list(route.member_order)!=[m['fieldName'] for m in record['members']]
        or list(route.member_declared_types)!=[m['declaredType'] for m in record['members']]):
        fail('current-route',record['wrapperTypeName'],None if route is None else route.row())
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return empty(after.status,after.detail)
    if not match():return empty('mismatched' if unity.is_file() else 'missing','UnityPlayer.dll changed during validation')
    return {'status':'validated','nativeInputs':pins,'recordMembers':proved,'actionDispatch':c['actionDispatch'],
        'outputProof':output,'runtimeExecutionKnown':False,'evidenceBoundary':c['evidenceBoundary']}

def decode_action(data,*,source,digest,start,end,tag,native_validation,target_decoder,depth=0):
    c=_contract();children=native_validation.get('children',{});audit=children.get('channeling',{})
    if (native_validation.get('status')!='validated' or audit.get('status')!='validated'
        or native_validation.get('nativeInputs')!=c['nativeInputs'] or audit.get('nativeInputs')!=c['nativeInputs']
        or audit.get('recordMembers')!=_members(c) or audit.get('actionDispatch')!=c['actionDispatch']
        or type(tag)is not int or tag!=47 or type(depth)is not int or not 0<=depth<=SEQUENCE_RECURSION_LIMIT
        or not isinstance(data,bytes) or not source or not isinstance(digest,str) or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
        or type(start)is not int or type(end)is not int or not 0<=start<end<=len(data)):
        raise ValueError(LABEL+'.decode:native-source-or-span')
    _children(c,children);reader=Reader(data,source,end);reader.pos=start;fields=[]
    if reader.nested_union_tag((47,),'channeling-action')!=47:raise ValueError(LABEL+'.physical-tag')
    if reader.peek()==255:reader.take(1,'null-channeling-wrapper')
    else:
        reader.header(10)
        for member in c['records']['channeling']['members']:
            a=reader.pos;kind=member['kind'];value={}
            if kind in ('byte','scalar32','raw4'):
                value['rawHex']=reader.take(1 if kind=='byte' else 4,member['fieldName']).hex().upper()
            elif kind=='sequence':
                child=sequence.decode_value(data,source,digest,a,end,native_validation,depth+1,require_end=False)
                if child.get('recursiveStoredSchemaExact')is not True or child.get('start')!=a or not a<child.get('end',a)<=end:
                    raise ValueError(LABEL+'.sequence-child-span')
                reader.pos=child['end'];value['child']=child
            elif kind=='target-profile':
                reader.target_profile();span={'start':a,'end':reader.pos,'typeName':target.TARGET_TYPE}
                child=({'start':a,'end':reader.pos,'typeName':target.TARGET_TYPE,'recursiveStoredSchemaExact':True,'isNull':True}
                    if data[a:reader.pos]==b'\xff' else target_decoder(data,source,digest,span,children))
                if child.get('recursiveStoredSchemaExact')is not True or [child.get('start'),child.get('end')]!=[a,reader.pos]:
                    raise ValueError(LABEL+'.target-child-span')
                value['child']=child
            else:raise ValueError(LABEL+'.unsupported-kind')
            fields.append({'fieldName':member['fieldName'],'declaredType':member['declaredType'],'kind':kind,'start':a,'end':reader.pos,**value})
    if reader.pos!=end:raise ValueError(LABEL+'.required-action-end')
    return {'schema':'endfield.buff-channeling-action-receipt.v1','source':source,'logicalSha256':digest.upper(),
        'tag':tag,'typeName':c['records']['channeling']['runtimeTypeName'],'start':start,'end':end,'namedFields':fields,
        'isNull':not fields,'recursiveStoredSchemaExact':True,'wholeBuffDataExact':False,'runtimeExecutionKnown':False}
