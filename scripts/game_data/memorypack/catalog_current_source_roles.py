"""Fresh source fallback for current catalog roles absent from the active graph.

Complete general source programs come from their maintained reader. Dedicated
nominals use only their explicit maintained source owners and projection
algorithms. This supplies source roles, never a child grammar, historical tag,
current consumer, legacy decoder activation or catalog publication.
"""
import importlib

PREFIX='scripts.game_data.memorypack.'
VALUE_OWNERS={
    PREFIX+'skill_root_assign_pair_sources':'endfield.skill-root-assign-pair-source.v1',
    PREFIX+'skill_root_buff_id_sources':'endfield.skill-root-buff-id-source.v1',
    PREFIX+'skill_gameplay_tag_value_sources':'endfield.skill-gameplay-tag-value-source.v1',
    PREFIX+'skill_root_tag_query_sources':'endfield.skill-root-tag-query-source.v1',
    PREFIX+'skill_smart_target_value_sources':'endfield.skill-smart-target-wrapper-source.v1',
    PREFIX+'skill_impulse_envelope_sources':'endfield.impulse-envelope-wrapper-source.v1',
}
REFERENCE_OWNERS={
    PREFIX+'skill_blackboard_double_sources':'endfield.skill-blackboard-double-sources.v1',
    PREFIX+'skill_blackboard_int_sources':'endfield.skill-blackboard-int-sources.v1',
    PREFIX+'skill_blackboard_vector3_sources':'endfield.skill-blackboard-vector3-sources.v1',
    PREFIX+'skill_blackboard_buff_id_sources':'endfield.skill-blackboard-buff-id-sources.v1',
}


def need(check,condition,detail=None):
    if not condition:raise ValueError('catalogCurrentSourceRoles.'+check+':'+str(detail)[:900])


def derive_absent(image,pins,claims):
    """Freshly prove exactly the requested finite absent source owners."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import catalog_source_review as review
    from scripts.game_data.memorypack import catalog_dedicated_source_projections as values
    from scripts.game_data.memorypack import catalog_reference_domain_source_projections as references
    from scripts.game_data.memorypack import catalog_dropdown_source_projections as dropdowns
    from scripts.game_data.memorypack import catalog_selector_zero_source_projections as selectors
    from scripts.game_data.memorypack import catalog_record_domain_source_projections as records
    from scripts.game_data.memorypack import catalog_nominal_value_source_projections as nominal
    need('finite-distinct-source-selection',isinstance(claims,list)and 0<len(claims)<=1024
        and all(isinstance(r,dict)and isinstance(r.get('wrapperName'),str)and r['wrapperName']for r in claims)
        and len({r['wrapperName']for r in claims})==len(claims))
    _publication_gate(image,pins);wanted={r['wrapperName']:r for r in claims};out={}
    def add(row):
        name=row['wrapperName'];need('selected-distinct-current-source',name in wanted and name not in out,name)
        need('same-selected-source-native-inputs',row.get('nativeInputs')==pins,name)
        out[name]=dict(row,completeSelectedSourceAdmitted=True,nativeAttributionProved=True)
    general=[r['wrapperName']for r in claims if r.get('sourceClass')=='general']
    if general:
        from scripts.game_data.memorypack.generated_reader_sources import derive_many
        result=derive_many(image,pins,general)
        for row in result['owners']:
            need('complete-absent-general-reader',row.get('status')=='complete-reader-source-proved',
                dict(wrapperName=row.get('wrapperName'),reason=row.get('reason')))
            proof=row['proof'];name=proof.get('wrapperName');own=review.complete_sources(proof,pins)
            need('one-exact-absent-general-source',name in general and set(own)=={name});add(dict(own[name],nativeInputs=dict(pins)))
    dedicated=[r for r in claims if r.get('sourceClass')=='dedicated-domain']
    need('explicit-source-class',len(general)+len(dedicated)==len(claims))
    for claim in dedicated:
        name=claim['wrapperName'];module=claim.get('maintainedOwner')
        if module not in VALUE_OWNERS:continue
        owner=importlib.import_module(module);derive=getattr(owner,'derive_wrapper',None)or owner.derive
        source=derive(image,pins)
        need('same-finite-value-owner',source.get('schema')==VALUE_OWNERS[module]and source.get('wrapperName')==name,name)
        row=values.project(source,pins);need('known-dedicated-value-projection',row is not NotImplemented,name);add(row)
    ref=[r for r in dedicated if r.get('maintainedOwner')in REFERENCE_OWNERS]
    if ref:
        result=references.derive_current(image,pins,schemas=[REFERENCE_OWNERS[r['maintainedOwner']]for r in ref])
        for row in result['sources']:add(row)
    drop=[r for r in dedicated if r.get('maintainedOwner')in(PREFIX+'skill_dropdown_blackboard_sources',PREFIX+'skill_blowoff_priority_sources')]
    fresh_dropdown=None
    if drop:
        result=dropdowns.derive_current(image,pins,type_names=[r['wrappedType']for r in drop])
        for row in result['sources']:add(row)
        # This own source may also be the independently typed child of Pull.
        fresh_dropdown=next((s for s in result['fullCurrentOwnerSources']
            if s.get('schema')=='endfield.skill-dropdown-blackboard-sources.v1'
            and 'Beyond.Gameplay.Core.BlackboardSuperArmorValue'in s.get('records',{})),None)
    selected=[r for r in dedicated if r['wrapperName']in selectors.NAMES]
    if selected:
        result=selectors.derive_current(image,pins)
        names={r['wrapperName']for r in selected}
        for row in result['sources']:
            if row['wrapperName']in names:add(row)
    record_schemas={PREFIX+'skill_root_buff_find_sources':'endfield.skill-root-buff-find-source.v1',
        PREFIX+'skill_root_create_buff_input_sources':'endfield.skill-root-create-buff-input-source.v1'}
    record=[r for r in dedicated if r.get('maintainedOwner')in record_schemas]
    if record:
        result=records.derive_current(image,pins,schemas=[record_schemas[r['maintainedOwner']]for r in record])
        for row in result['sources']:add(row)
    for claim in dedicated:
        module=claim.get('maintainedOwner');name=claim['wrapperName']
        if module==PREFIX+'skill_global_buff_id_sources':
            owner=importlib.import_module(module);source=owner.derive(image,pins)
        elif module==PREFIX+'skill_pull_attenuation_sources':
            owner=importlib.import_module(module)
            if fresh_dropdown is None:
                from scripts.game_data.memorypack.skill_dropdown_blackboard_sources import derive
                fresh_dropdown=derive(image,pins,type_names=[owner.REFERENCE])
            source=owner._derive_wrapper(image,pins,fresh_dropdown)
        else:continue
        row=nominal.project(source,pins);need('known-finite-nominal-value-projection',row is not NotImplemented,name);add(row)
    need('all-and-only-requested-current-source-owners',set(out)==set(wanted),sorted(set(wanted)-set(out)))
    _publication_gate(image,pins)
    return dict(nativeInputs=dict(pins),sourceProgramSemanticsReproved=True,sources=[out[r['wrapperName']]for r in claims],
        currentConsumersAdmitted=False,catalogsActivated=0,legacyDecodersActivated=0,evidenceBoundary=__doc__)


def prover():
    from scripts.game_data.memorypack.catalog_current_roles_native import source_role_prover
    return source_role_prover(absent_source_prover=derive_absent)
