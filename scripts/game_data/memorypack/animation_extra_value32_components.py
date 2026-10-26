"""Two own managed32 callbacks joined to their distinct generated wire.

State's MC3 writes interruptType, performId and stateHash; stateName remains
zero on a fresh value. PlayEffect's MC6 writes three strings and three bools.
The canonical callback, complete wrapper paths and individual named setters
are independently replayed. Managed padding is never counted as wire.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import animation_extra_value32_sources as canonical

SCHEMA='endfield.animation-extra-value32-components.v1'
STATE,PLAY=canonical.STATE,canonical.PLAY
PLANS={STATE:[('interruptType',canonical.FIELDS[STATE][3][1]),('performId','string'),('stateHash','int')],
    PLAY:[('effectName','string'),('eventName','string'),('followPosition','bool'),('followRotation','bool'),('stopWithState','bool'),('targetBonePath','string')]}


def need(check,condition):
    if not condition:raise ValueError('animationExtraValue32Components.'+check)


def norm(value):return json.loads(json.dumps(value))
def key(name):need('finite-value32',name in PLANS);return 'animation-extra-record:'+name


def wrapper_program(regions,entry,*,type_name,new=False,null=False):
    need('literal-own-path',type_name in PLANS and type(new)is bool and type(null)is bool and not(new and null))
    play=type_name==PLAY;g=BytesPath(regions,entry);symbols={};calls=[];requests=[];allocation=None
    def call(role):
        at=g.at;t=g.relative('e8');need('same-own-helper:'+role,role not in symbols or symbols[role]==t)
        symbols[role]=t;calls.append(dict(role=role,instructionVa=at,targetVa=t))
    g.take('48895c2410','4889742418','57','4883ec20');flag=g.relative('803d')
    g.take('00','488bda','488bf9');g.branch('75',True,1)
    g.take('488d542430','c644243000','488bcf');call('header');g.take('84c0');g.branch('0f84',null)
    if null:g.take('488bcb','48c70300000000');call('barrier')
    else:
        g.take('48833b00');g.branch('75',not new,1)
        if new:
            at=g.at;cell=g.relative('488b0d');call('allocate');g.take('4885c0');g.branch('0f84'if play else'74',False,1 if not play else 4)
            g.take('0f57c0','488bcb','0f114010','0f114020','488903');call('barrier')
            allocation=dict(instructionVa=at,cellVa=cell,zeroedManagedBytes=32)
        g.take('807c2430'+('06'if play else'03'));g.branch('0f85'if play else'75',False,4 if play else 1)
        if not play:
            at=g.at;cell=g.relative('488b15');g.take('488bcf','488b33');call('int32')
            requests.append(dict(instructionVa=at,cellVa=cell,sourceTargetVa=symbols['int32']))
            g.take('4885f6');g.branch('74',False,1);g.take('894628','488bcf','488b33');call('pool')
            g.take('4885f6');g.branch('74',False,1)
            g.take('4533c0','488bd0','488bce');call('setter:performId')
            g.take('488b1b','488bcf');call('int32');g.take('4885db');g.branch('74',False,1);g.take('894318');g.jump('eb',1)
        else:
            for name,guard in(('effectName','0f84'),('eventName','74')):
                g.take('488b33','488bcf');call('pool');g.take('4885f6');g.branch(guard,False,4 if guard=='0f84'else 1)
                g.take('4533c0','488bd0','488bce');call('setter:'+name)
            g.take('488b33','488bcf');call('bool');g.take('4885f6');g.branch('74',False,1);g.take('884628')
            for offset in('29','2a'):
                g.take('488bcf','488b33');call('bool');g.take('4885f6');g.branch('74',False,1);g.take('8846'+offset)
            g.take('488bcf','488b1b');call('pool');g.take('4885db');g.branch('74',False,1)
            g.take('4533c0','488bd0','488bcb');call('setter:targetBonePath');g.jump('eb',1)
    g.take('488b5c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,typeName=type_name,newWrapper=new,wrapperNull=null,metadataReadyFlagVa=flag,
        symbols=symbols,sourceCalls=calls,typedRequests=requests,allocation=allocation,
        memberCount=None if null else len(PLANS[type_name]),managedBytes=32,
        positiveWireBytes=None if null else(16 if play else 13),allIntegerNonvolatilesRestored=True,
        entryRspRestored=True,normalReturn=True)


def string_setter_program(regions,entry,*,offset):
    need('literal-own-string-field-offset',offset in(16,24,32));g=BytesPath(regions,entry)
    if offset==16:g.take('4883c110','488911')
    else:g.take('488951'+bytes((offset,)).hex(),'4883c1'+bytes((offset,)).hex())
    target=g.relative('e9')
    return dict(selectedBytes=g.seen,fieldOffset=offset,fullReferenceBitsStored=True,selectedBarrierValueOffset=offset-16,
        barrierTargetVa=target,tailTransfer=True,entryRspRestored=True)


def bool_program(regions,entry,offsets):
    c,r,a,u=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','8379'+r+'01','488bd9');g.branch('0f8c',False)
    g.take('488b43'+c,'0fb630','8b7b'+r,'83ef01');g.branch('0f88',False)
    g.take('48ff43'+c,'ff43'+a,'ff43'+u,'897b'+r,'488b5c2430','4084f6','488b742438','0f95c0','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=1,boolNormalized=True,normalReturn=True,entryRspRestored=True)


def compose(actual,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.shader_property_value_components import enum_program
    from scripts.game_data.animation_current_native import pool_capability
    need('own-native-value32-wire',actual.get('schema')==SCHEMA and actual.get('nativeInputs')==pins
        and actual.get('status')=='validated-conditional-extra-value32-wire-source'
        and actual.get('typeName')in PLANS and actual.get('parentFieldAdmitted')is False and actual.get('wholeOwnerAdmitted')is False)
    name=actual['typeName'];p=actual['proof'];cb=p['canonical'];identity=canonical.verify(cb,pins);base=p['base']
    need('same-own-wrapper-and-callback',identity['typeName']==name and p['method'][1:3]==[identity['wrapperName'],'Deserialize']
        and p['method']==cb['proof']['forwarding']['readerMethod']and p['members']==[list(v)for v in PLANS[name]])
    raw={k:regions(p['sourceWindows'][k],v,base,'extra-value32-wire-'+k)for k,v in p['sourceRegions'].items()}
    paths=[wrapper_program(raw['wrapper'],base+p['method'][3],type_name=name,**case)for case in({},dict(new=True),dict(null=True))]
    need('all-three-complete-own-wrapper-paths',norm(paths)==p['wrapperPaths'])
    symbols=paths[0]['symbols'];need('same-own-object-header',symbols['header']==base+cb['proof']['symbolRvas']['header'])
    for row in p['setters']:
        field=row['fieldName'];offset=next(o for n,t,o in canonical.FIELDS[name]if n==field)
        need('own-complete-named-string-setter',row['method'][1:3]==[identity['wrapperName'],'set___'+field+'__']
            and base+row['method'][3]==symbols['setter:'+field]
            and norm(string_setter_program([(a,bytes.fromhex(h))for a,h in row['program']['selectedBytes']],base+row['method'][3],offset=offset))==row['program']
            and row['program']['barrierTargetVa']==base+p['barrierTargetRva'])
    need('all-and-only-own-named-string-setters',[r['fieldName']for r in p['setters']]==(['performId']if name==STATE else['effectName','eventName','targetBonePath']))
    offsets=cb['proof']['readerOffsets']
    if name==STATE:
        selected=enum_program(raw['int32'],symbols['int32'],offsets)
        def flatten(v,origin=0):return[(a-origin+i,b)for a,h in v for i,b in enumerate(bytes.fromhex(h))]
        need('complete-own-raw-int32-reader',flatten(selected,base)==flatten(p['primitive']['selectedProgram'])and p['primitive']['wireBytes']==4)
        request,=p['requests'];event,=paths[0]['typedRequests'];usage=request['typedRequest']
        need('own-literal-interrupt-enum-context',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
            ==(6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],[PLANS[STATE][0][1]])
            and usage['instructionRva']==event['instructionVa']-base and request['sourceTargetVa']==symbols['int32'])
    else:need('complete-own-normalized-bool-reader',norm(bool_program(raw['bool'],symbols['bool'],offsets))==p['primitive'])
    pool=pool_capability(p['pool'],pins);need('actual-pooled-wire-source',pool['sourceTargetRva']==symbols['pool']-base)
    cap=dict(**identity,memberCount=len(PLANS[name]),orderedFieldNames=[n for n,t in PLANS[name]],wireFields=[list(v)for v in PLANS[name]],
        valueStorageKind='value32',wholeGrammarAdmitted=True,ordinaryOriginalCallbackAdmitted=True,ordinaryOriginalReadValueAdmitted=False,
        nullable=True,nullMarker=255,nullWireBytes=1,nullReturnsDefaultValue=True,positiveWireBytes=16 if name==PLAY else 13,
        serializedFieldNames=[n for n,t in PLANS[name]],nonserializedFieldNames=['stateName']if name==STATE else[],
        requiredChildCapabilities={'byte-payload':pool},actualContainingRouteAdmitted=False,runtimeAnimationProved=False)
    cap['wireGrammarAdmitted']=True
    return dict(capability=key(name),capabilities={key(name):cap},requiredExternalCapabilities=['byte-payload'])


def validate_component(component,pins):
    need('own-composed-value32',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-extra-value32-components')
    checked=compose(component['proof']['source'],pins);need('all-and-only-owned-capabilities',all(component.get(k)==v for k,v in checked.items()))
    return checked


def derive(image,pins,*,type_name):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,generated_primitive_sources as primitive,pooled_source_helper
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    _publication_gate(image,pins);need('finite-own-value32',type_name in PLANS);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    cb=canonical.derive(image,pins,type_name=type_name);canonical.verify(cb,pins)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==canonical.WRAPPERS[type_name]]
    need('own-generated-wire-members',[(m.name,m.declared_type)for m in wrapper.members]==PLANS[type_name])
    mm=pointer.methods(image,wrapper);method=cb['proof']['forwarding']['readerMethod'];sources={'wrapper':pointer.owned(image,base+method[3])}
    paths=[wrapper_program(sources['wrapper']['regions'],base+method[3],type_name=type_name,**case)for case in({},dict(new=True),dict(null=True))]
    symbols=paths[0]['symbols'];usage=derive_typed_usage_context(image,paths[1]['allocation']['instructionVa']-base,label='extraValue32.allocate')
    need('own-wrapper-allocation',usage.get('tag')==1 and usage.get('typeName')==wrapper.name)
    setters=[]
    for member in wrapper.members:
        typ=member.declared_type;method_def=image.metadata.methods[member.method_index]
        scalar.owned_method_abi(image,ctx,method_def.index,wrapper.type_definition,('void',1,False),[(typ,14 if typ=='string'else 2 if typ=='bool'else 17 if ctx.is_enum(typ)else 8,typ=='string')],'extraValue32.setter')
        if typ!='string':continue
        at=image.method_pointer_va(method_def);need('actual-named-setter-call',at==symbols['setter:'+member.name])
        offset=ctx.field(type_name+'::'+member.name)[2];program=string_setter_program([(at,image.pe.bytes_at_va(at,32))],at,offset=offset)
        setters.append(dict(fieldName=member.name,method=[method_def.index,wrapper.name,'set___'+member.name+'__',at-base],program=program))
    barrier_target=setters[0]['program']['barrierTargetVa'];barrier=_fast_barrier(image,barrier_target)
    need('same-allocation-null-and-string-barrier',all(r['program']['barrierTargetVa']==barrier_target for r in setters)
        and paths[1]['symbols']['barrier']==paths[2]['symbols']['barrier']==barrier_target)
    role='int32'if type_name==STATE else'bool';sources[role]=pointer.owned(image,symbols[role]);offsets=cb['proof']['readerOffsets']
    prim=primitive.derive(image,symbols[role],role,offsets)if role=='int32'else bool_program(sources[role]['regions'],symbols[role],offsets)
    requests=[]
    for event in paths[0]['typedRequests']:
        usage=derive_typed_usage_context(image,event['instructionVa']-base,label='extraValue32.interrupt')
        binding=bind_typed_read(image,usage,method_name='ReadUnmanaged',argument=PLANS[STATE][0][1],kind=17)
        requests.append(dict(typedRequest=usage,typedBinding=binding,sourceTargetVa=event['sourceTargetVa']))
    pool=pooled_source_helper.validate_on_image(image,symbols['pool'],pins);_publication_gate(image,pins)
    actual=norm(dict(schema=SCHEMA,status='validated-conditional-extra-value32-wire-source',nativeInputs=pins,typeName=type_name,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,proof=dict(base=base,canonical=cb,method=method,members=PLANS[type_name],
            wrapperPaths=paths,setters=setters,barrier=barrier,barrierTargetRva=barrier_target-base,primitive=prim,requests=requests,pool=pool,
            sourceWindows={k:v['windows']for k,v in sources.items()},sourceRegions={k:[[a-base,r.hex()]for a,r in v['regions']]for k,v in sources.items()})))
    checked=compose(actual,pins)
    return dict(schema=SCHEMA,status='validated-conditional-extra-value32-components',nativeInputs=pins,**checked,
        proof=dict(source=actual),parentFieldAdmitted=False,wholeOwnerAdmitted=False)
