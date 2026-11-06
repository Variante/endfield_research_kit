"""Current BaseComponentData transport, independent of concrete components.

Every native table case owns its cast, closed ReadPackable thunk, stored full
reference and return. A component name or metadata rank never assigns a tag.
The enclosing array and each selected concrete grammar remain separate.
"""
TYPE='Beyond.Gameplay.BaseComponentData'


def derive(image,pins):
    from scripts.game_data.memorypack.levelscript_game_condition_union_sources import derive_reference_transport
    return derive_reference_transport(image,pins,type_name=TYPE,
        schema='endfield.interactive-component-union-transport.v1',
        status='validated-conditional-interactive-component-transport',
        evidence_boundary=dict(exact='Complete current component table, own casts and closed reader contexts, full reference stores/returns, canonical base adapter and inherited getter/interface transfer.',
            conditional=__doc__,unresolved=['concrete component and collection grammars','enclosing Interactive root',
                'existing-output alternatives and live formatter/provider selection','runtime component behavior']))
