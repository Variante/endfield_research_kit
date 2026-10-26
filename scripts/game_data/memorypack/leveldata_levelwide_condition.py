"""Explicit condition-scope selection for the finite LevelWide owner only."""


def extended(cap):
    from scripts.game_data.memorypack.leveldata_condition_global_var_sources import CAP_SCHEMA
    schema=cap.get('schema')if isinstance(cap,dict)else None
    if schema not in(None,CAP_SCHEMA):raise ValueError('levelwideCondition.unreviewed-condition-scope')
    return schema==CAP_SCHEMA


def validate(cap):
    if extended(cap):
        from scripts.game_data.codecs.leveldata.current_condition_global_var import validate_union
        validate_union(cap)
    else:
        from scripts.game_data.codecs.leveldata.current_condition import validate as original
        original(cap)


def bind_reference(pins,join,child,capability):
    cap=child.get('capabilities',{}).get(capability,{})
    if extended(cap):
        from scripts.game_data.memorypack.leveldata_condition_global_var_sources import bind_reference as selected
    else:
        from scripts.game_data.memorypack.leveldata_condition_components import bind_reference as selected
    return selected(pins,join,child,capability)


def read(reader,field,cap):
    """An opt-in child shares the proved base grammar, not its admission scope."""
    validate(cap);is_extended=extended(cap);selected=cap;global_cap=getattr(reader,'condition_cap',None)
    def semantic(value):return {key:item for key,item in value.items()if key!='parentBindings'}
    if isinstance(global_cap,dict):
        global_extended=extended(global_cap)
        if is_extended and not global_extended:
            if semantic(cap['baseCapability'])!=semantic(global_cap):
                raise ValueError('levelwideCondition.same-own-and-global-base-condition-grammar')
        else:
            if semantic(cap)!=semantic(global_cap):raise ValueError('levelwideCondition.same-own-and-global-condition-grammar')
            selected=global_cap
    if is_extended:
        from scripts.game_data.codecs.leveldata.current_condition_global_var import read_union
        state=getattr(reader,'_current_global_var_condition_budget',None)
        if state is not None:
            if semantic(state[0])!=semantic(selected):raise ValueError('levelwideCondition.same-global-var-condition-budget')
            selected=state[0]
        return read_union(reader,field,selected)
    from scripts.game_data.codecs.leveldata.current_condition import read as original
    state=getattr(reader,'_current_condition_budget',None)
    if state is not None:
        if semantic(state[0])!=semantic(selected):raise ValueError('levelwideCondition.same-condition-budget')
        selected=state[0]
    return original(reader,field,selected)
