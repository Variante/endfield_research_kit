"""Current concrete Buff reference grammar, separate from its runtime fields.

The generated wrapper serializes only modifiedBBKeys. Its nominal registered
pair, canonical adapter, wrapper factory/reader/setter and pooled string-list
source are composed on one image. Live formatter selection and ordinary Buff
constructor effects remain explicit conditions.
"""
from __future__ import annotations
import json

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.memorypack import (
    pointer_param as pointer, primitive_param as primitive,
    pooled_string_list_sources as strings,
    scalar_param_native as scalar,
)
from scripts.game_data.memorypack.buff_ptr_sources import _call
from scripts.game_data.memorypack.reference_object_sources import derive_adapter
from scripts.game_data.memorypack.skill_action_null_source import derive_reference_null
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.memorypack.wrapper_members import derive_from_image

LABEL='buffObjectSource'
TYPE='Beyond.Gameplay.Core.Buff'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_BuffForMemoryPack'
LIST='System.Collections.Generic.List`1<string>'


def need(key,expected,actual):scalar.need(LABEL,key,expected,actual)


def reader_program(regions,entry,s,*,null=False,allocated=False):
    if type(null)is not bool or type(allocated)is not bool or null and allocated:
        raise ValueError(LABEL+'.reader-profile')
    g=BytesPath(regions,entry)
    g.take('48895c2410','4889742418','57','4883ec20');flag=g.relative('803d')+1
    g.take('00','488bda','488bf1');g.branch('75',True,1)
    g.take('488d542430','c644243000','488bce');g.call(s['header'])
    g.take('84c0');g.branch('0f84',null)
    allocation=None;typed=None
    if null:
        g.take('488bcb','48c70300000000');g.call(s['barrier'])
    else:
        g.take('48833b00');g.branch('75',not allocated,1)
        if allocated:
            allocation=g.at;cell=g.relative('488b0d');g.call(s['allocate'])
            g.take('488bf8','4885c0');g.branch('74',False,1)
            g.take('33d2','488bc8');g.call(s['constructor'])
            g.take('488bcb','48893b');g.call(s['barrier'])
        g.take('807c243001');g.branch('75',False,1)
        typed=g.at;g.relative('488b15');g.take('488bce','488b1b');g.call(s['read'])
        g.take('4885db');g.branch('75',True,1)
        g.take('4533c0','488bd0','488bcb');g.call(s['setter']);g.jump('eb',1)
    g.take('488b5c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,initializedFlagCell=flag,null=null,allocated=allocated,
        memberCount=None if null else 1,headerBytes=1,headerFalseMeans255=True,
        allocationUsageSite=allocation,typedReadUsageSite=typed,
        reader='incoming RCX preserved RSI',wrapperOutput='incoming RDX preserved RBX until read',
        fullReferenceResultToSetter=not null,outputClearedBytes=8 if null else 0,
        nonvolatilesRestored=['rbx','rsi','rdi'],normalReturn=True)


def factory_program(regions,entry,s):
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20');flag=g.relative('803d')+1
    g.take('00','488bf9');g.branch('75',True,1)
    usage=g.at;cell=g.relative('488b0d');g.call(s['allocate'])
    g.take('488bd8','4885c0');g.branch('75',True,1)
    g.take('33d2','488bcb');g.call(s['originalConstructor'])
    g.take('488d4f10','48895f10','488b5c2430','4883c420','5f')
    need('factory-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,initializedFlagCell=flag,originalClassCell=cell,
        originalAllocationUsageSite=usage,holderOffset=16,storedReferenceBits=64,
        normalReturnViaBarrier=True,originalConstructorEffectsProved=False)


def setter_program(regions,entry,field_offset,barrier):
    if type(field_offset)is not int or not 16<=field_offset<2**31:
        raise ValueError(LABEL+'.field-offset')
    g=BytesPath(regions,entry)
    g.take('4883ec28','488b4910','4885c9');g.branch('75',True,1)
    displacement=field_offset.to_bytes(4,'little').hex()
    g.take('488991'+displacement,'4881c1'+displacement,'4883c428')
    need('setter-barrier',barrier,g.relative('e9'))
    return dict(selectedBytes=g.seen,holderOffset=16,originalFieldOffset=field_offset,
        incomingRdxStoredUnchanged=True,storedReferenceBits=64,normalReturnViaBarrier=True)


def derive(image,pins):
    """Return a fresh exact component; the aggregate owns publication bookends."""
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    null=derive_reference_null(image,pins,TYPE,WRAPPER)
    wrapper,=[w for w in derive_from_image(image).values()if w.name==WRAPPER]
    need('one-serialized-member',[('modifiedBBKeys',LIST)],[(m.name,m.declared_type)for m in wrapper.members])
    need('reference-holder',(WRAPPER,TYPE,16),ctx.field(WRAPPER+'::__instance'))
    need('concrete-original',0,md.types[null['typeDefinition']].flags&0x80)
    mm=pointer.methods(image,wrapper);bodies={n:pointer.owned(image,image.method_pointer_va(mm[n]))
        for n in('Deserialize','.ctor','CreateInstance','set___modifiedBBKeys__')}
    primitive.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    getter=mm['GetValue'];scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,
        (TYPE,18,True),[],LABEL+'.getter')
    getter_proof=pointer.leaf(image,image.method_pointer_va(getter),['488B4110','C3'])
    for name in('.ctor','CreateInstance'):
        scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,('void',1,False),[],LABEL+'.factory')
    setter=mm['set___modifiedBBKeys__'];scalar.owned_method_abi(image,ctx,setter.index,
        wrapper.type_definition,('void',1,False),[(LIST,21,True)],LABEL+'.setter')
    field=ctx.field(TYPE+'::modifiedBBKeys');need('original-field-owner-and-type',(TYPE,LIST),field[:2])
    source=bodies['Deserialize'];s={role:_call(source,offset)for role,offset in(
        ('header',98),('allocate',124),('constructor',142),('barrier',153),('read',178),('setter',203))}
    need('own-constructor',image.method_pointer_va(mm['.ctor']),s['constructor'])
    need('own-setter',image.method_pointer_va(setter),s['setter'])
    programs=[reader_program(source['regions'],source['pointer'],s,**kw)
        for kw in({},dict(allocated=True),dict(null=True))]
    typed=derive_typed_usage_context(image,programs[0]['typedReadUsageSite']-base,label=LABEL+'.list')
    need('typed-list-call',('MemoryPack.MemoryPackReader','ReadPackable',[],[LIST]),
        tuple(typed[k]for k in('typeName','methodName','classArguments','methodArguments')))
    allocation=derive_typed_usage_context(image,programs[1]['allocationUsageSite']-base,label=LABEL+'.wrapper')
    need('allocated-wrapper',(1,WRAPPER),(allocation['tag'],allocation['typeName']))
    factories=[];original_ctor=None
    for name in('.ctor','CreateInstance'):
        body=bodies[name];actual=_call(body,72)
        if original_ctor is not None:need('same-original-constructor',original_ctor,actual)
        original_ctor=actual
        symbols=dict(s,originalConstructor=actual)
        proof=factory_program(body['regions'],body['pointer'],symbols)
        usage=derive_typed_usage_context(image,proof['originalAllocationUsageSite']-base,label=LABEL+'.original')
        need('factory-actual-original',(1,TYPE),(usage['tag'],usage['typeName']))
        factories.append(dict(method=name,program=proof,allocation=usage))
    constructors=[m for m in md.methods_for(md.types[null['typeDefinition']])
        if md.string(m.name_index)=='.ctor'and m.parameter_count==0]
    need('unique-original-constructor',1,len(constructors));ctor=constructors[0]
    scalar.owned_method_abi(image,ctx,ctor.index,ctor.declaring_type,('void',1,False),[],LABEL+'.BuffCtor')
    need('actual-original-constructor',image.method_pointer_va(ctor),original_ctor)
    stored=setter_program(bodies['set___modifiedBBKeys__']['regions'],image.method_pointer_va(setter),field[2],s['barrier'])
    header=vector_recorder(image)(s['header']-base)
    primitive.object_header_source(image,header,scalar.reader_offsets(image,LABEL))
    # The complete common canonical programs are re-proved. This new nominal
    # pair is separately joined to its own getter, slot5 forwarder and source.
    adapter_proof=derive_adapter(image,pins,null['pair'],wrapper)
    need('same-canonical-null-target',null['callbackBinding']['canonicalTargetRva'],adapter_proof['callbackBinding']['canonicalTargetRva'])
    listing=json.loads((CONTRACTS_DIR/'levelscript_pooled_string_list_native.json').read_bytes())
    need('string-list-build',pins,listing['nativeInputs']);list_proof=strings.validate_components(image,listing)
    list_role,=[p for p in listing['programs']if p['role']=='list']
    list_regions=[(base+w['startRva'],image.window_bytes(w))for w in list_role['windows']]
    list_offsets=scalar.reader_offsets(image,LABEL+'.list')
    list_offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    list_symbols={k:base+v for k,v in listing['listSymbols'].items()}
    list_programs=[strings.list_source(list_regions,base+list_role['entryRva'],list_offsets,list_symbols,
        count=count,new=new,grow=False)for new in(False,True)for count in range(4)]
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    induction=prove_induction(list_programs,initial='33f6',increment='ffc6',comparison='3b742468',
        counter='esi',saved_count='Signed count at caller RSP+104 is outside child ABI home/output/frame writes.')
    literal=listing['parent']['selectedPlan']
    for key in('tag','methodSpecIndex','methodSpec','typeName','methodName','classArguments','methodArguments'):
        need('same-closed-list-reader.'+key,literal['typedContext'][key],typed[key])
    need('actual-list-reader',base+literal['targetRva'],s['read'])
    Build(image,pins).prove_reader_clone_target(s['read'],'MemoryPack.MemoryPackReader.ReadPackable',result_abi='reference')
    return json.loads(json.dumps(dict(schema='endfield.buff-object-source.v1',nativeInputs=pins,typeName=TYPE,
        wrapperName=WRAPPER,memberCount=1,nullAdmitted=True,nullMarker=255,positiveAdmitted=True,listMaxCount=induction['maxCount'],
        referenceReaderMethodDefinition=null['referenceReaderMethodDefinition'],
        referenceReaderTargetRva=null['referenceReaderTargetRva'],referenceNull=null,
        adapter=adapter_proof,header=header,wrapperPrograms=programs,factories=factories,
        getter=getter_proof,setter=stored,originalField=field,typedListRead=typed,
        wrapperAllocation=allocation,symbolRvas={k:v-base for k,v in s.items()},
        sourceWindows={k:b['windows']for k,b in bodies.items()},listProof=list_proof,listPrograms=list_programs,countInduction=induction,
        wireFields=[dict(name='modifiedBBKeys',typeName=LIST,wireKind='pooled-string-list')],
        evidenceBoundary=dict(exact='Current concrete Buff eager pair and generated MC1 wrapper; complete normal existing/new/null wrapper programs, actual typed ReadPackable<List<string>>, named setter into Buff.modifiedBBKeys, holder/GetValue, factories, slot5 forwarder and interface conversion. Current pooled string-list source independently proves signed count, every selected element callback, stride8 reference stores and complete return.',
            conditional='Initialized coherent exact closed contexts, matching canonical adapters and wrapper/string callbacks, normal compatible helpers and Buff constructor/allocation/barriers, disabled collector, sufficient buffered disjoint storage and matching original StringPool. For reused lists prior count is zero and capacity sufficient; fresh capacity=count. Runtime provider/cache/default/override/inflation choice is unobserved.',
            unresolved=['Buff constructor effects/gameplay object identity','live provider selection','positive prior-size reused Clear effects','cold initialization/refill/malformed paths','whole enclosing owner']))))
