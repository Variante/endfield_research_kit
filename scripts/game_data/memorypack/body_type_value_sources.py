"""Exact BodyTypeDef managed32 source, separate from its MC3/pool wire.

The reviewed current char-perform source owns the positive canonical adapter,
ordinary factory/GetValue and complete hidden32 copies. This owner rechecks
those bytes and nominal contexts, adds the adapter's full default32 branch,
and binds a supplied actual ReadValue request without pointer aliases. Runtime
provider selection, helper effects, parent fields/frames and wire grammar stay
separate. In particular m_displayName is runtime-only, and both reference
lanes and all padding belong to the managed value rather than its wire.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.contracts import CONTRACTS_DIR

TYPE='Beyond.Gameplay.BodyTypeDef'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_BodyTypeDefForMemoryPack'
SCHEMA='endfield.body-type-value-source.v1'
CONTRACT_PATH=CONTRACTS_DIR/'char_interact_perform_sparse_native.json'
FIELDS=[('bodyType','Beyond.Gameplay.BodyType',16),('CustomName','string',24),
        ('CustomId','int',32),('m_displayName','string',40)]


def need(check,condition):
    if not condition:raise ValueError('bodyTypeValueSource.'+check)


def layout(image,ctx):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md=image.metadata;td=ctx.index.types[TYPE]
    need('nongeneric-value',ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)and td.generic_container_index<0)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    need('exact-declared-fields',[(md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:])for f in fields]==FIELDS)
    for field,kind in zip(fields,(17,14,8,14),strict=True):
        scalar.ordinary(image,ctx.type_pointer(field.type_index),kind,'bodyTypeValueSource.field',reference=kind==14)
    enum=ctx.index.types[FIELDS[0][1]];need('own-enum',ctx.is_enum(FIELDS[0][1]))
    backing,=[f for f in md.fields_for(enum)if not ctx.field_attributes(f.type_index)&16]
    need('one-byte-enum-backing',md.string(backing.name_index)=='value__'and ctx.type_name(backing.type_index)=='byte')
    scalar.ordinary(image,ctx.type_pointer(backing.type_index),5,'bodyTypeValueSource.enumBacking')
    size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    need('boxed48-managed32',(image.pe.u32_at_va(size),image.pe.u32_at_va(size+4))==(48,32))
    return dict(typeName=TYPE,typeDefinition=td.index,boxedBytes=48,managedBytes=32,
        fields=[list(row)for row in FIELDS],referenceLaneOffsets=[8,24],paddingByteRanges=[[1,7],[20,4]],
        serializedFieldNames=['bodyType','CustomId','CustomName'],runtimeOnlyFieldNames=['m_displayName'],wireGrammarAdmitted=False)


def adapter_default(regions,entry,s,*,dispatch=False):
    need('literal-dispatch-selection',type(dispatch)is bool);g=BytesPath(regions,entry)
    if dispatch:
        g.take('48895c2408','48896c2410','4889742418','57','4883ec20','488b0a','498be9','498bf0','488bda')
        g.call(s['prepare']);g.take('488b3b');need('same-canonical-adapter',g.relative('488d0d')==s['main'])
        g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False)
        g.relative('803d');g.take('00');g.branch('0f84',False)
    else:
        g.take('48896c2410','4889742418','57','4883ec20');g.relative('803d');g.take('00','498bf9','498be8','488bf2');g.branch('0f84',False)
    g.take('488b4720','488bce','488b90c0000000','488b12');g.call(s['readNull']);g.take('84c0');g.branch('0f85',True)
    g.take('0f57c0','0f114500','0f114510');g.jump('e9')
    if dispatch:g.take('488b5c2430')
    g.take('488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,defaultZeroBytes=32,completeOutputSlices=[[0,16],[16,16]],
        sameHiddenOutput=True,entryRspRestored=True,normalReturn=True,wireGrammarAdmitted=False)


def read_null_default(regions,entry,*,peek,header):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','c644243000');g.call(peek)
    g.take('84c0');g.branch('0f85',True);g.take('488d542430','488bcb');g.call(header);g.take('b001');g.jump('e9')
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,headerCalls=1,returnsTrue=True,sameReader=True,
        entryRspRestored=True,normalReturn=True,wireBytes=1,requiredPeekByte=255)


def derive(image,pins,*,typed_request=None,source_target=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import char_perform_action_joins as joins,pooled_source_helper
    from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
    from scripts.game_data.il2cpp.native_image import read_reviewed_contract
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_typed_usage_context
    _publication_gate(image,pins)
    fact,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.char-interact-perform-sparse-native.v4',
        status='conditional-current-build-wire',label='bodyTypeValueSource')
    need('selected-reviewed-contract-inputs',fact.get('nativeInputs')==pins)
    ctx=joins.NativeReferenceContext(image);nominal=layout(image,ctx);base=image.pe.image_base;md=image.metadata
    c=fact['loopActionsOne'];programs=c['programs'];proofs=[];loaded={};regions_by_role={}
    def load(role):
        p=programs[role];entry=base+p['entryRva'];windows=p['windows'];owned=sorted((w['startRva'],w['endRva'])for w in windows)
        if p['ownership']=='leaf':
            leaf=decode_closed_leaf_entry(image.mapper,image.pe.bytes_at_va(entry,512),entry)
            end=max(int(r['va'],16)+len(bytes.fromhex(r['bytes']))for r in leaf['rows'])
            joins.need('closed-leaf:'+role,[(entry-base,end-base)],owned)
        elif p['ownership']=='selected-return-prefix':joins.need('barrier-prefix:'+role,'wrapper:disabledBarrier',role)
        else:joins.need('complete-owned:'+role,sorted(tuple(r['runtimeTriple'][:2])for r in image.unwind_index.family(entry-base)['ranges']),owned)
        image.check_windows(windows,label='bodyTypeValueSource')
        regions=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in windows]
        loaded[role]=dict(entryRva=entry-base,windows=windows,ownership=p['ownership'])
        regions_by_role[role]=regions;return regions,entry
    def run(fn,role,*args,**kwargs):
        regions,entry=load(role);q=fn(regions,entry,*args,**kwargs);proofs.append(q);return q
    def method(t,n):
        found=[m for m in md.methods_for(ctx.index.types[t])if md.string(m.name_index)==n]
        joins.need('one-method:'+t+'::'+n,1,len(found));return found[0]
    def at(role):return base+programs[role]['entryRva']
    def method_role(t,n,role):
        m=method(t,n);joins.need('method-entry:'+role,image.method_pointer_va(m),at(role));return m
    def usage(site):return derive_typed_usage_context(image,site-base,label='bodyTypeValueSource')
    def typed(u,owner,name,ca,ma):joins.need('typed-call',(owner,name,ca,ma),(u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']))
    joins._values(image,pins,c,load,run,at,method,method_role,usage,typed,proofs)
    symbols={k:base+v for k,v in c['bodyValueSymbols'].items()}
    defaults=[run(adapter_default,role,symbols,dispatch=dispatch)for role,dispatch in
        (('value:main32',False),('value:valueDispatcher32',True))]
    default_null=run(read_null_default,'value:readNull',peek=at('value:peek'),header=base+c['bodyReadSymbols']['header'])
    pool=pooled_source_helper.validate_on_image(image,base+c['bodyReadSymbols']['string'],pins)
    need('both-or-no-actual-request',(typed_request is None)==(source_target is None))
    if typed_request is not None:
        validate_typed_usage_context(image,typed_request,label='bodyTypeValueSource.actual')
        need('exact-own-ReadValue-request',tuple(typed_request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
            ==(6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE])and typed_request.get('methodSpec',[None])[0]==c['readValueContext']['definition'])
        need('actual-owned-ReadValue-entry',type(source_target)is int and source_target==at('value:readValue32'))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-conditional-nominal-managed32-source',nativeInputs=pins,
        typeName=TYPE,wrapperName=WRAPPER,managedBytes=32,resultAbi='hidden-local',actualSourceProved=typed_request is not None,
        readerMethodDefinition=c['readValueContext']['definition'],sourceTargetRva=programs['value:readValue32']['entryRva'],
        referenceLaneOffsets=[8,24],paddingByteRanges=[[1,7],[20,4]],wireGrammarAdmitted=False,parentFieldAdmitted=False,
        wholeOwnerAdmitted=False,proof=dict(nominal=nominal,typedRequest=typed_request,positivePrograms=proofs,
            adapterDefaults=defaults,defaultNull=default_null,pool=pool,ownedPrograms=loaded,
            actualSourceRegions=[[a-base,b.hex().upper()]for a,b in regions_by_role['value:readValue32']],
            adapter=dict(readerMethodDefinition=c['readValueContext']['definition'],dispatcherTargetRva=programs['value:valueDispatcher32']['entryRva'])),
        evidenceBoundary=dict(exact='Current nominal32 fields, hidden32 reset/source/adapter/interface/getter copies and full FF/default32 return.',
            conditional=__doc__,unresolved=['live provider/helper effects','parent transfer and frame','MC3 wire capability and pool operation','whole owner and EOF']))))
