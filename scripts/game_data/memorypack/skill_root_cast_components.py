"""CastData's exact named BlackboardDouble and CostData reference joins.

The selected current MC11/FF/new source supplies actual field order, unchanged
scalar stores, enum32 declarations and three separately typed ReadValue calls.
Both BlackboardDouble fields join the complete concrete lifecycle owner, and
CostData joins its own MC3/FF/new source, typed factories/getter and current
reference adapter. CostData's separately proved DamageUnit list parent is not
borrowed as CastData framing. Runtime selection/normal compatible helper effects
remain conditions; skill evaluation and enclosing root/EOF stay unresolved.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need,bind_read_value,reference_record_abi
from scripts.game_data.memorypack.skill_root_attribute_components import reference_cap

TYPE='Beyond.Gameplay.Core.CastData'
COST=TYPE+'+CostData'
CAPABILITY='skill-root-cast-data'
COST_CAP='skill-root-cost-data'


def cost_capability(pins,component,reference,order):
    need('same-cost-native-inputs',pins,component['nativeInputs'])
    need('fresh-cost-component-status','validated-conditional-components',component['status'])
    child=component['child'];need('exact-CostData-reference',(COST,3),(child['original'],child['memberCount']))
    need('exact-independent-CostData-fields',[(n,t,4)for n,t in
        (('atbValueThreshold','float'),('costType','Beyond.GEnums.CostType'),('costValue','float'))],
        [(f['name'],f['type'],f['wireBytes'])for f in child['fields']])
    need('complete-cost-selected-paths',[(False,False),(False,True),(True,False)],
        [(p['null'],p['newWrapper'])for p in child['programs']])
    need('literal-cost-path-switches',True,all(type(p[k])is bool for p in child['programs']for k in('null','newWrapper')))
    need('complete-cost-wire-and-return-programs',True,all(p.get('normalReturn')is True
        and p.get('unchangedFloat32Bits')is True and p.get('sameIncomingReader')is True
        and p.get('fieldWireBytes')==([]if p['null']else[4,4,4])
        and p.get('memberCount')==(None if p['null']else 3)for p in child['programs']))
    need('both-complete-cost-factories',['.ctor','CreateInstance'],[f['method']for f in child['factories']])
    need('typed-cost-factory-return',True,all(f['program'].get('allocatedOriginalStoredUnchanged')is True
        and f['program'].get('normalReturnViaBarrier')is True and f['program'].get('requiresNormallyReturningZeroedTypedAllocation')is True
        and type(f['program'].get('holderOffset'))is int and f['program']['holderOffset']==16 for f in child['factories']))
    need('same-CostData-reference-getter',child['getter']['entryRva'],reference['adapter']['getterMethod'][3])
    return reference_cap(dict(typeName=COST,wrapperName=child['wrapper'],memberCount=3),reference,order)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_root_record_sources import derive as record_sources
    from scripts.game_data.memorypack.skill_blackboard_double_sources import derive as double_source
    from scripts.game_data.memorypack import skill_cost_data_list_sources as cost_source
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.skill_root_children_codec import REFERENCE_RECORDS
    record=record_sources(image,pins,types=[TYPE])['records'][TYPE]
    reference=reference_record_abi(image,pins,record)
    double=double_source(image,pins)
    profile=cost_source.derive_profile(image);cost=cost_source.derive(image,pins,profile)
    child=cost['child'];wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==child['wrapper']]
    adapter=derive_adapter(image,pins,profile['child'],wrapper)
    csource=dict(adapter=adapter,**reference_reader_abi(image,pins))
    order=lambda name:[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in REFERENCE_RECORDS[name][1]]
    cost_cap=cost_capability(pins,cost,csource,order(COST_CAP))
    cost_component=dict(nativeInputs=pins,capabilities={COST_CAP:cost_cap})
    bindings=[]
    for join in record['requiredChildJoins']:
        component,cap=(cost_component,COST_CAP)if join['typeName']==COST else(double,'skill-blackboard-double')
        need('finite-Cast-reference-child',True,join['typeName']in(COST,'Beyond.Blackboard+BlackboardDouble'))
        bindings.append(bind_read_value(pins,join,component,cap))
    need('exact-three-Cast-reference-fields',['castDistance','costData','heightDiffLimit'],[b['fieldName']for b in bindings])
    caps=dict(double['capabilities']);caps[COST_CAP]=cost_cap;caps[CAPABILITY]=reference_cap(record,reference,order(CAPABILITY))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-cast-components.v1',nativeInputs=pins,
        status='validated-conditional-components',capabilities=caps,
        proof=dict(parent=record,parentReference=reference,blackboardDouble=double,costProfile=profile,
            costSource=cost,costReference=csource,referenceBindings=bindings),
        evidenceBoundary=dict(exact='Current MC11/FF/new Cast caller, own getter/factory/adapter and exact selected nominal ReadValue method/target joins for both BlackboardDouble and CostData with complete concrete child grammar.',
            conditional=__doc__,structuralOnly='Stored cast parameters and cost configuration.',unresolved=['runtime evaluation and provider choice','enclosing root/physical EOF']))))
