"""Own CharWetSquad constructor defaults, separate from its serialized fields."""
import hashlib,json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.Core.CharInteractPerform.CharWetSquadActionData'
VECTOR='UnityEngine.Vector3'
SCHEMA='endfield.char-wet-constructor-source.v1'


def need(check,condition):
    if not condition:raise ValueError('charWetConstructor.'+check)


def program(data,entry,fields):
    need('bounded-owned-leaf',isinstance(data,bytes)and 0<len(data)<=128 and set(fields)=={'offset','radius','intensity','actorIndex'})
    offset,radius,intensity,actor=(fields[n][2]for n in('offset','radius','intensity','actorIndex'))
    need('positive-disjoint-field-slices',all(type(n)is int and 16<=n<2**31-16 for n in(offset,radius,intensity,actor))
        and 16<=actor<128 and len({offset+i for i in range(12)}|{radius+i for i in range(4)}|{intensity+i for i in range(4)}|{actor+i for i in range(4)})==24)
    g=BytesPath([(entry,data)],entry);g.take('0f57d2','0f57c0','c781'+radius.to_bytes(4,'little').hex()+'0000a040',
        '0f14c2','33d2','f20f1181'+offset.to_bytes(4,'little').hex(),
        'f30f1191'+(offset+8).to_bytes(4,'little').hex(),'c781'+intensity.to_bytes(4,'little').hex()+'0000803f',
        'c741'+bytes((actor,)).hex()+'ffffffff')
    target=g.relative('e9')
    return dict(selectedBytes=g.seen,programBytes=g.at-entry,baseConstructorTargetVa=target,
        defaults=[dict(fieldName='offset',bytes=12,rawHex='00'*12),dict(fieldName='radius',bytes=4,rawHex='0000a040'),
            dict(fieldName='intensity',bytes=4,rawHex='0000803f'),dict(fieldName='actorIndex',bytes=4,rawHex='ffffffff')],
        sameReceiverRcx=True,methodInfoEdxZero=True,stackUnchanged=True,allIntegerNonvolatilesUnchanged=True,
        normalReturnViaOwnedBaseConstructor=True,wireGrammarAdmitted=False)


def derive_original(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar,generated_lifecycle_sources as lifecycle
    from scripts.game_data.memorypack.generated_vector_member_sources import layout
    _publication_gate(image,pins);ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base
    td=ctx.index.types[TYPE];need('own-nongeneric-reference',not ctx.is_value_type(TYPE)and td.generic_container_index<0)
    method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='.ctor'and m.parameter_count==0]
    scalar.owned_method_abi(image,ctx,method.index,td.index,('void',1,False),[],'charWetConstructor.ctor')
    fields={};owners=lifecycle._class_ancestry(ctx,TYPE)
    for owner in owners:
        for f in md.fields_for(ctx.index.types[owner]):
            if ctx.field_attributes(f.type_index)&16:continue
            name=md.string(f.name_index)
            if name not in('offset','radius','intensity','actorIndex'):continue
            need('one-owned-named-default-field',name not in fields)
            fact=ctx.field(owner+'::'+name);expected=VECTOR if name=='offset'else'int'if name=='actorIndex'else'float'
            need('own-default-field-type',fact[1]==expected)
            scalar.ordinary(image,ctx.type_pointer(f.type_index),17 if name=='offset'else 8 if name=='actorIndex'else 12,'charWetConstructor.field')
            fields[name]=list(fact)
    at=image.method_pointer_va(method);raw=image.pe.bytes_at_va(at,128);proof=program(raw,at,fields)
    targets=[(owner,m)for owner in owners[1:]for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)=='.ctor'
        and m.parameter_count==0 and image.method_pointer_va(m)==proof['baseConstructorTargetVa']]
    need('one-actual-owned-ancestor-constructor-tail',len(targets)==1);owner,parent=targets[0]
    scalar.owned_method_abi(image,ctx,parent.index,parent.declaring_type,('void',1,False),[],'charWetConstructor.base')
    delegated=lifecycle._original_constructor(image,ctx,parent,owner,pins=pins)
    size=proof['programBytes'];window=dict(startRva=at-base,endRva=at-base+size,sha256=hashlib.sha256(raw[:size]).hexdigest().upper())
    _publication_gate(image,pins)
    result=dict(schema=SCHEMA,status='validated',nativeInputs=pins,originalType=TYPE,
        method=[method.index,TYPE,'.ctor',at-base],fields=fields,vectorLayout=layout(image,ctx,VECTOR),program=proof,
        sourceHex=raw[:size].hex(),codeWindows=[window],delegatedConstructor=delegated,
        completeReachableEntryProgramProved=True,physicalFunctionExtentProved=False,normalConstructorReturnRequired=True,
        constructorInvocationObserved=False,wireGrammarAdmitted=False,wrapperFactoryAdmitted=False)
    return json.loads(json.dumps(result))


def verify(actual,pins):
    need('own-current-constructor',actual.get('schema')==SCHEMA and actual.get('status')=='validated'
        and actual.get('nativeInputs')==pins and actual.get('originalType')==TYPE
        and actual.get('method',[None,None,None])[1:3]==[TYPE,'.ctor']
        and actual.get('wireGrammarAdmitted')is False and actual.get('wrapperFactoryAdmitted')is False)
    p=actual['program'];selected=p.get('selectedBytes',[]);need('owned-entry',bool(selected));entry=selected[0][0]
    raw=bytes.fromhex(actual['sourceHex']);need('whole-program',json.loads(json.dumps(program(raw,entry,actual['fields'])))==p)
    window,=actual['codeWindows'];need('exact-owned-window',window['endRva']-window['startRva']==len(raw)
        and window['startRva']==actual['method'][3]and hashlib.sha256(raw).hexdigest().upper()==window['sha256'])
    parent=actual['delegatedConstructor'];need('same-actual-ancestor-tail',parent['method'][3]+entry-actual['method'][3]==p['baseConstructorTargetVa']
        and parent['method'][1]!=TYPE and parent.get('normalConstructorReturnRequired')is True)
    return True
