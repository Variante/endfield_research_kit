"""Patrol Init's own warm class preparation and cached Int32/reference search."""
import json
from scripts.game_data.memorypack import leveldata_patrol_dictionary_lookup_programs as paths


def need(check,condition):
    if not condition:raise ValueError('PatrolInitLookup.'+check)


def norm(value):return json.loads(json.dumps(value))


def derive(image,pins,*,prepare,entity_table,try_get,config_usage):
    import hashlib
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack.leveldata_patrol_init_helper_sources import _packet
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    def span(at,size):
        raw=image.pe.bytes_at_va(at,size)
        return dict(entryRva=at-base,windows=[dict(startRva=at-base,endRva=at-base+size,sha256=hashlib.sha256(raw).hexdigest().upper())],
            regions=[[at-base,raw.hex().upper()]],boundary='declared-selected-source-span-no-physical-extent')
    def raw(packet):return [(base+a,bytes.fromhex(h))for a,h in packet['regions']]
    prefix=image.pe.bytes_at_va(prepare,9);need('literal-preparation-wrapper',prefix[:5]==bytes.fromhex('488b4978e9'))
    inner=prepare+9+int.from_bytes(prefix[5:],'little',signed=True)
    packets=dict(preparation=span(prepare,9),preparationInner=_packet(image,inner),entityTable=_packet(image,entity_table),tryGet=_packet(image,try_get))
    lookup_body=pointer.owned(image,try_get)
    find=next(control_transfer(r)['target']for r in lookup_body['rows']if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe8)
    packets['findEntry']=_packet(image,find);find_body=pointer.owned(image,find)
    comparer=next(control_transfer(r)['target']for r in find_body['rows']if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe8)
    packets['comparerThunk']=span(comparer,5)
    lea=next(r for r in find_body['rows']if bytes.fromhex(r['bytes'])[:3]==bytes.fromhex('488d05'))
    code=bytes.fromhex(lea['bytes']);equality=int(lea['va'],16)+7+int.from_bytes(code[3:],'little',signed=True)
    packets['equality']=span(equality,7)
    table_body=pointer.owned(image,entity_table)
    usage_row,=[r for r in table_body['rows']if bytes.fromhex(r['bytes'])[:3]==bytes.fromhex('4c8b0d')]
    table_usage=derive_typed_usage_context(image,int(usage_row['va'],16)-base,label='PatrolInitHelpers.entityTableTryGet')
    need('own-entity-table-Int32-reference-TryGet',table_usage['tag']==6 and table_usage['typeName']=='System.Collections.Generic.Dictionary`2'
        and table_usage['methodName']=='TryGetValue'and table_usage['methodArguments']==[]
        and len(table_usage['classArguments'])==2 and table_usage['classArguments'][0]=='int'
        and table_usage['methodSpec'][0]==config_usage['methodSpec'][0])
    class_args=image.instantiations.resolve(table_usage['methodSpec'][1]).arguments
    scalar.ordinary(image,class_args[0].type_pointer_va,8,'PatrolInitHelpers.tableKey')
    scalar.ordinary(image,class_args[1].type_pointer_va,18,'PatrolInitHelpers.tableValue',reference=True)
    def field_at(name,offset):
        found=[];trail=set()
        while name and name not in trail and name!='object':
            trail.add(name);td=ctx.index.types[name]
            for f in md.fields_for(td):
                if ctx.field_attributes(f.type_index)&16:continue
                fact=list(ctx.field(name+'::'+md.string(f.name_index)))
                if fact[2]==offset:found.append((f,fact,md.string(f.name_index)))
            name=ctx.parent(name)
        need('one-owned-selected-field-'+str(offset),len(found)==1);return found[0]
    rf,row,name=field_at(table_usage['classArguments'][1],64)
    scalar.ordinary(image,ctx.type_pointer(rf.type_index),18,'PatrolInitHelpers.rowConfig',reference=True)
    df,dictionary,dname=field_at(row[1],504)
    need('own-exact-cached-Config-dictionary',dictionary[1]=='System.Collections.Generic.Dictionary`2<int,Beyond.Gameplay.AI.Config.NpcPatrolData>')
    scalar.ordinary(image,ctx.type_pointer(df.type_index),21,'PatrolInitHelpers.cachedDictionary',reference=True)
    sym=dict(comparerGetterRva=comparer-base,findEntryRva=find-base,equalityRva=equality-base,preparationRva=prepare-base,
        preparationInnerRva=inner-base,tryGetRva=try_get-base,entityTableRva=entity_table-base)
    find_programs,induction=paths.find_paths(raw(packets['findEntry']),find,comparer_getter=comparer,prepare=prepare,equality=equality)
    programs=dict(preparation=[paths.preparation_program(raw(packets['preparation'])+raw(packets['preparationInner']),prepare,inner=inner,mode=m)for m in('initialized','being-initialized')],
        equality=paths.equality_program(raw(packets['equality']),equality),findEntry=find_programs,chainInduction=induction,
        tryGet=[paths.try_get_program(raw(packets['tryGet']),try_get,find=find,found=f)for f in(False,True)],
        entityTable=[paths.entity_table_program(raw(packets['entityTable']),entity_table,try_get=try_get,found=f,replacement_present=r)for r in(False,True)for f in(False,True)])
    need('entity-table-actual-shared-TryGet-context-and-call',all(p['contextInstructionVa']==base+table_usage['instructionRva']
        and p['contextCellVa']==base+table_usage['usageCellRva']for p in programs['entityTable']))
    result=norm(dict(packets=packets,symbolRvas=sym,programs=programs,entityTryGetUsage=table_usage,
        entityRowConfigField=dict(name=name,field=row),cachedConfigDictionaryField=dict(name=dname,field=dictionary),
        contextAndComparerSelectionConditional=True,actualClosedPointerEquivalenceClaimed=False))
    validate(result,pins,base=base,config_usage=config_usage);return result


def validate(source,pins,*,base,config_usage):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    packets=source['packets'];sym={k:base+v for k,v in source['symbolRvas'].items()};programs=source['programs']
    need('exact-own-helper-source-set',set(packets)=={'preparation','preparationInner','entityTable','tryGet','findEntry','comparerThunk','equality'}
        and source.get('contextAndComparerSelectionConditional')is True and source.get('actualClosedPointerEquivalenceClaimed')is False)
    raw={name:regions(p['windows'],p['regions'],base,'PatrolInit-'+name)for name,p in packets.items()}
    need('exact-selected-helper-entries',all(base+packets[name]['entryRva']==sym[key]for name,key in
        [('preparation','preparationRva'),('preparationInner','preparationInnerRva'),('entityTable','entityTableRva'),('tryGet','tryGetRva'),
         ('findEntry','findEntryRva'),('comparerThunk','comparerGetterRva'),('equality','equalityRva')]))
    need('both-ready-preparation-paths',norm([paths.preparation_program(raw['preparation']+raw['preparationInner'],sym['preparationRva'],inner=sym['preparationInnerRva'],mode=m)for m in('initialized','being-initialized')])==programs['preparation'])
    need('exact-current-Int32-equality-bytes',norm(paths.equality_program(raw['equality'],sym['equalityRva']))==programs['equality'])
    selected,certificate=paths.find_paths(raw['findEntry'],sym['findEntryRva'],comparer_getter=sym['comparerGetterRva'],prepare=sym['preparationRva'],equality=sym['equalityRva'])
    need('full-default-comparer-chain-and-mixed-probe-induction',norm(selected)==programs['findEntry']and norm(certificate)==programs['chainInduction'])
    need('both-exact-TryGet-reference-output-paths',norm([paths.try_get_program(raw['tryGet'],sym['tryGetRva'],find=sym['findEntryRva'],found=f)for f in(False,True)])==programs['tryGet'])
    table=[paths.entity_table_program(raw['entityTable'],sym['entityTableRva'],try_get=sym['tryGetRva'],found=f,replacement_present=r)for r in(False,True)for f in(False,True)]
    need('four-exact-entity-table-normal-paths',norm(table)==programs['entityTable'])
    usage=source['entityTryGetUsage'];row=source['entityRowConfigField'];dictionary=source['cachedConfigDictionaryField']
    need('own-table-row-Config-dictionary-field-chain',usage['typeName']=='System.Collections.Generic.Dictionary`2'and usage['methodName']=='TryGetValue'
        and usage['tag']==6 and usage['methodSpec'][0]==config_usage['methodSpec'][0]and usage['methodArguments']==[]
        and usage['classArguments'][0]=='int'and row['field'][0]==usage['classArguments'][1]and row['field'][2]==64
        and dictionary['field']==[row['field'][1],'System.Collections.Generic.Dictionary`2<int,Beyond.Gameplay.AI.Config.NpcPatrolData>',504]
        and all(p['contextInstructionVa']==base+usage['instructionRva']and p['contextCellVa']==base+usage['usageCellRva']for p in table))
    return dict(warmPreparationNoNonframeWritesProved=True,defaultInt32ReferenceDictionarySearchProved=True,
        finiteMixedCollisionChainLimit=4096,actualComparerSelectionObserved=False,wholeInitializerProved=False)
