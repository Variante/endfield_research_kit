"""Interactive root's own R14-null locals and ready dictionary classes."""
from scripts.game_data.memorypack.interactive_dictionary_sources import TYPES,need
SCHEMA='endfield.interactive-static-out-parent.v1'
PARENT='Beyond.Gameplay.InteractiveTemplateData'
FIELDS={18:('propertyIdToKeyMap','Beyond.SerializeFieldDictionary`2<int,string>',104),
        19:('propertyKeyToIdMap','Beyond.SerializeFieldDictionary`2<string,int>',120),
        22:('templateVariant','Beyond.SerializeFieldDictionary`2<string,Beyond.Gameplay.Core.InteractiveTemplateVariant>',32)}
BUNDLE='Beyond.Gameplay.Core.SkillDataBundle'
ABILITY='Beyond.Gameplay.Core.AbilitySystemForIntData'
VARIANT='Beyond.Gameplay.Core.InteractiveTemplateVariant'
ROSTERS={PARENT:FIELDS,BUNDLE:{
    0:('activeSkillTypeOverrides','Beyond.SerializeFieldDictionary`2<string,Beyond.Gameplay.SkillType>',104),
    9:('defaultCmdMapping','Beyond.SerializeFieldDictionary`2<Beyond.Gameplay.Core.AbilitySystem+ComboController+BattleCommandType,string>',32)},
    ABILITY:{2:('bakedMeshPoints','Beyond.SerializeFieldDictionary`2<string,Beyond.Gameplay.Core.AbilitySystemData+BakedMeshPointList>',136),
        15:('extraShapesData','Beyond.SerializeFieldDictionary`2<Beyond.Gameplay.MountPoint,Beyond.Gameplay.BasicShapeData>',32),
        28:('preloadAbilityEntities','Beyond.SerializeFieldDictionary`2<string,int>',40),
        29:('preloadBattleCgIds','Beyond.SerializeFieldDictionary`2<string,int>',48),
        31:('skillCameraConfig','Beyond.SerializeFieldDictionary`2<string,Beyond.Gameplay.Core.SkillCameraConfig>',56)},
    VARIANT:{2:('componentDiffProperties','Beyond.SerializeFieldDictionary`2<string,Beyond.Gameplay.ParamListForGraph>',96)}}
REGISTERS={PARENT:('rbx','rdi','r14'),BUNDLE:('rdi','rbx','rbp'),ABILITY:('rdi','rbx','rbp'),VARIANT:('rdi','rsi','literal')}


def validate_literal_zero(row,item,base):
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    need('own-variant-whole-literal-null',item.get('zeroProfile')=='interactive-variant-literal-null'
        and item.get('displacement')==96 and item.get('entryRspOffset')==8
        and ec.site(row,base)==item.get('instruction')and ec.raw(row)==bytes.fromhex('48c744246000000000')
        and row['text']=='mov qword [rsp+0x60], 0x0')


def validate_zero(row,item,base):
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    if item.get('zeroProfile')=='interactive-variant-literal-null':return validate_literal_zero(row,item,base)
    proof=item.get('zeroSource',{});home=item['displacement']
    register={'interactive-r14-null':'r14','interactive-rbp-null':'rbp'}.get(item.get('zeroProfile'))
    encoded=bytes.fromhex('4889ac24')+home.to_bytes(4,'little')if home==136 and register=='rbp'else bytes.fromhex('4c897424'if register=='r14'else'48896c24')+bytes((home,))
    need('own-null-register-local',register is not None and home in(32,40,48,56,104,120,136)
        and ec.site(row,base)==item['instruction']and ec.raw(row)==encoded
        and proof.get('register')==register and type(proof.get('value'))is int and proof['value']==0
        and proof.get('zeroOnEveryOrdinaryPath')is True and ec.va(row)in proof.get('sites',[]))


def validate_guard(row,item,base):
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    if item.get('guardProfile')=='interactive-variant-ready-literal':
        need('own-variant-literal-class-state',item.get('zeroSource')is None and ec.site(row,base)==item['comparison']
            and ec.raw(row)==bytes.fromhex('83b9e000000000'))
        return
    proof=item['zeroSource']
    register=proof.get('register')
    need('own-null-class-state-compare',register in('r14','rbp')and ec.site(row,base)==item['comparison']
        and ec.raw(row)==bytes.fromhex('4439b1e0000000'if register=='r14'else'39a9e0000000')
        and type(proof.get('value'))is int and proof['value']==0
        and proof.get('zeroOnEveryOrdinaryPath')is True and ec.va(row)in proof.get('sites',[]))


def validate_setup(setup,events):
    selected=[e for e in events if e.get('mode')=='typed-static-out-reference']
    roster=ROSTERS.get(setup.get('parentType'),{})
    need('own-parent-and-field-roster',setup.get('schema')==SCHEMA and bool(roster)
        and [e['memberIndex']for e in selected]==list(roster)
        and all((e['fieldName'],e['declaredType'])==roster[e['memberIndex']][:2]for e in selected)
        and len(setup.get('initializedZeroLocals',[]))==len(setup.get('classGuards',[]))==len(roster)
        and setup.get('classCalls')==[]and setup.get('sourceFrameAlias')is None)
    return setup


def parent_setup(image,rows,path,events,header,*,base,parent_type):
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    from scripts.game_data.memorypack.generated_header_sources import _owned_zero_source
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    need('own-parent-registers',parent_type in REGISTERS and(header['readerRegister'],header['outputRegister'])==REGISTERS[parent_type][:2])
    register=REGISTERS[parent_type][2];fields=ROSTERS[parent_type]
    zeros=[];guards=[];graph=header.get('ordinaryZeroFamily');entry=None if register=='literal'else base+graph['entryRva']
    for e in [e for e in events if e.get('mode')=='typed-static-out-reference']:
        index=e['memberIndex'];need('finite-parent-dictionary-field',index in fields)
        name,typename,home=fields[index];need('own-field',(e['fieldName'],e['declaredType'])==(name,typename))
        position=next(i for i,r in enumerate(path)if ec.va(r)==base+e['context']['instructionRva'])
        call=next(i for i,r in enumerate(path)if ec.site(r,base)==e['instruction'])
        argument=ec.last_write(path,call,'rdx')
        address=bytes.fromhex('488d9424')+home.to_bytes(4,'little')if home==136 else bytes.fromhex('488d5424')+bytes((home,))
        need('exact-own-null-home-address',argument is not None and ec.raw(argument)==address)
        raw=bytes.fromhex('48c744246000000000')if register=='literal'else bytes.fromhex('4889ac24')+home.to_bytes(4,'little')if home==136 and register=='rbp'else bytes.fromhex('4c897424'if register=='r14'else'48896c24')+bytes((home,))
        found=[r for r in path[:call]if ec.raw(r)==raw]
        need('actual-own-null-reset',bool(found));zero=found[-1]
        proof=None if register=='literal'else _owned_zero_source(rows,entry,[ec.va(zero)],register,base,graph)
        item=dict(memberIndex=index,instruction=ec.site(zero,base),displacement=home,
            entryRspOffset=home-header['nullFrameBytes'],zeroSource=proof,
            zeroProfile='interactive-variant-literal-null'if register=='literal'else'interactive-'+register+'-null')
        validate_zero(zero,item,base);zeros.append(item)
        comparisons=[(i,r)for i,r in enumerate(path[:position])if ec.raw(r)==bytes.fromhex('83b9e000000000'if register=='literal'else'4439b1e0000000'if register=='r14'else'39a9e0000000')]
        need('own-nearest-ready-compare',bool(comparisons));ci,compare=comparisons[-1]
        load=ec.last_write(path,ci,'rcx');need('actual-closed-class-load',load is not None and ec.raw(load)[:3]==bytes.fromhex('488b0d'))
        usage=derive_typed_usage_context(image,ec.va(load)-base,label='interactiveDictionaryParent')
        need('own-selected-dictionary-class',usage.get('tag')==1 and usage.get('typeName')==typename)
        edge=path[ci+1];flow=control_transfer(edge)
        need('exact-ready-class-selected-edge',flow.get('kind')=='conditional'and flow.get('conditionCode')==(5 if register=='literal'else 4)
            and ec.va(path[ci+2])==(flow['target']if register=='literal'else ec.va(edge)+len(ec.raw(edge))))
        proof=None if register=='literal'else _owned_zero_source(rows,entry,[ec.va(compare)],register,base,graph)
        item=dict(load=ec.site(load,base),typedRequest=usage,comparison=ec.site(compare,base),zeroSource=proof,
            edge=ec.site(edge,base),selectedNextInstruction=ec.site(path[ci+2],base),
            **({'guardProfile':'interactive-variant-ready-literal'}if register=='literal'else{}))
        validate_guard(compare,item,base);guards.append(item)
    setup=dict(schema=SCHEMA,parentType=parent_type,initializedZeroLocals=zeros,classGuards=guards,classCalls=[],
        sourceFrameAlias=None,initializedClassStateObserved=False)
    return validate_setup(setup,events)
