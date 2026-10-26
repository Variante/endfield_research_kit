"""Finite current consumer projections omitted by generic catalog traversal.

Use the maintained wire owner's own capability validator for the generated
AssignPair, BuffId, GameplayTag and Query values. The separately owned raw4
GameplayTag array is deliberately outside this domain. Calculation children
come from the complete actual union routes, never a wrapper-name inventory.
These projections do not authenticate native inputs or admit any catalog.
"""
from types import SimpleNamespace

VALUE_DOMAINS=frozenset(('skill-root-assign-pair','skill-root-buff-id',
    'skill-root-gameplay-tag','skill-root-gameplay-tag-query'))


def _reader(caps):
    from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
    return RootChildrenReader(SimpleNamespace(operation=SimpleNamespace(child=lambda name:caps[name])))


def value_domain_complete(name,cap):
    """Return finite selected-value grammar evidence without changing its cap."""
    if name not in VALUE_DOMAINS or not isinstance(cap,dict):return False
    try:
        _reader({name:cap})._record_cap(name)
        return cap.get('callbackSelectionConditional')is True
    except(ValueError,KeyError,IndexError,TypeError):return False


def original_domain(name,cap,caps,path):
    """Project an exact Original only through its actual reached reader path."""
    if not value_domain_complete(name,cap):return None
    if name=='skill-root-gameplay-tag-query':
        if not(all(type(cap.get(key))is int and cap[key]>0 for key in('valueReaderMethodDefinition','valueDispatcherTargetRva'))
                and cap.get('ownConcreteGetterSemanticsProved')is True and cap.get('ownConcreteFactorySemanticsProved')is True):return None
    else:
        # A raw unmanaged Tag array reaches a different element capability.
        # Only the actual generated value-list edge can nominate these values.
        if len(path)<2 or path[-1]!=name:return None
        parent=caps.get(path[-2],{});typename=cap['typeName']
        if not(parent.get('elementCapability')==name and parent.get('elementType')==typename
                and parent.get('elementValueType')is True and parent.get('elementGrammarAdmitted')is True
                and parent.get('positiveCountsAdmitted')is True
                and parent.get('closedListType')=='System.Collections.Generic.List`1<'+typename+'>'
                and all(type(parent.get(key))is int and parent[key]>0 for key in('packableReaderMethodDefinition','packableReaderTargetRva'))):return None
    return cap['typeName']


def nested_programs(name,cap):
    """Expose every proved Calculation route as a conditional nested consumer."""
    if name!='damage-calculation-union' or not isinstance(cap,dict):return []
    if not(cap.get('typeName')=='Beyond.Gameplay.Core.CalculationBase'
            and cap.get('wholeGrammarAdmitted')is True and cap.get('baseGetterSemanticsProved')is True
            and cap.get('concreteChildGrammarsProved')is True and cap.get('ordinaryOriginalReadValueAdmitted')is True
            and cap.get('nullAdmitted')is True and type(cap.get('nullMarker'))is int and cap['nullMarker']==255
            and cap.get('extendedTagsAdmitted')is False and cap.get('reservedMarkersAdmitted')is False
            and cap.get('supportedShortTags')==list(range(6))
            and all(type(tag)is int for tag in cap['supportedShortTags'])):return []
    routes=cap.get('routes')
    if not(isinstance(routes,list)and len(routes)==6 and all(isinstance(r,dict)for r in routes)
            and [r.get('tag')for r in routes]==list(range(6))
            and all(type(r.get('tag'))is int for r in routes)):return []
    from scripts.game_data.memorypack.skill_damage_children_codec import DamageChildrenReader
    reader=DamageChildrenReader(None);out=[]
    try:
        for row in routes:
            reads=reader._program(row)
            if not(isinstance(row.get('wrapperName'),str)and row['wrapperName']
                    and isinstance(row.get('typeName'),str)and row['typeName']):return []
            out.append(dict(family='CalculationBase',tag=row['tag'],wrapperName=row['wrapperName'],
                memberCount=row['memberCount'],reads=reads))
    except(ValueError,KeyError,IndexError,TypeError):return []
    return out


def add_original(index,name,cap,caps,path,consumer):
    original=original_domain(name,cap,caps,path)
    if original is None:return
    index.setdefault('original:'+original,[]).append(dict(consumer,
        consumerKind='reachable-exact-generated-value-domain',typeName=original,
        actualOriginalReadAdmitted=True,finiteSelectedValueGrammarProved=True,
        wrapperIdentityFromIndependentSourceRequired=True))
