"""Compose existing independent Param owners below Interactive readers.

Names select a finite source owner; they never grant a wire grammar. Every
returned capability has freshly proved its own closed carrier, canonical
adapter and concrete source. Containing fields, arrays and unions remain
separate obligations. No source census or saved diagnostic is an input.
"""
from scripts.game_data.memorypack import levelscript_condition_param_sources as primitive
from scripts.game_data.memorypack import levelscript_condition_enum_param_components as enums
from scripts.game_data.memorypack import levelscript_condition_storage_param_components as storage
from scripts.game_data.memorypack import levelscript_action_dedicated_param_components as dedicated
from scripts.game_data.memorypack import levelscript_action_output_components as output
from scripts.game_data.memorypack import levelscript_condition_list_param_components as lists

SCHEMA = 'endfield.interactive-parameter-sources.v1'


def need(check, condition, detail=''):
    if not condition:
        raise ValueError('interactiveParamSource.' + check + ':' + str(detail)[:1600])


def derive(image, pins, *, parameter_types):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    names = list(parameter_types)
    need('finite-distinct-explicit-selection', 0 < len(names) <= 128
         and len(set(names)) == len(names) and all(type(n) is str for n in names))
    _publication_gate(image, pins)
    ctx = NativeReferenceContext(image)
    groups = {key: [] for key in ('primitive', 'enum', 'storage', 'dedicated', 'list', 'output', 'special')}
    for name in names:
        if name.startswith(output.PREFIX) and name.endswith('>'):
            groups['output'].append(name)
            continue
        need('own-Param-or-output-nominal', name.startswith(primitive.PREFIX) and name.endswith('>'), name)
        value = name[len(primitive.PREFIX):-1]
        if value in primitive.PRIMITIVES: kind = 'primitive'
        elif ctx.is_enum(value): kind = 'enum'
        elif value in storage.TYPES: kind = 'storage'
        elif value in dedicated.SPECS: kind = 'dedicated'
        elif value in tuple(lists.LIST + element + '>' for element in lists.ELEMENTS): kind = 'list'
        elif value in ('Beyond.Gameplay.View.CameraControlState',
                       'Beyond.Gameplay.View.CameraControlStateInitialParam',
                       'Beyond.Gameplay.Core.ScriptTaskPtr',
                       'Beyond.Gameplay.Core.SplinePtr',
                       'Beyond.Gameplay.Core.AirWallPtr',
                       'Beyond.ObjectPtr`1<Beyond.Gameplay.Core.GlobalBuff>',
                       'System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>'): kind = 'special'
        else: raise ValueError('interactiveParamSource.unsupported-constant:' + value)
        groups[kind].append(name)
    components = {}; capabilities = {}
    for kind, selected in groups.items():
        if not selected: continue
        values = [name[len(primitive.PREFIX):-1] for name in selected]
        if kind == 'primitive': component = primitive.derive_many(image, pins, values)
        elif kind == 'enum': component = enums.derive_many(image, pins, selected)
        elif kind == 'storage': component = storage.derive_many(image, pins, values)
        elif kind == 'dedicated': component = dedicated.derive_many(image, pins, parameter_types=selected)
        elif kind == 'list': component = lists.derive_many(image, pins, element_types=[
            value[len('System.Collections.Generic.List`1<'):-1] for value in values])
        elif kind == 'output': component = output.derive_many(image, pins, parameter_types=selected)
        else:
            for name, value in zip(selected, values, strict=True):
                cap, proof = _special(image, pins, value)
                capabilities[name] = cap; components[name] = proof
            continue
        owners = {owner['typeName']: owner for owner in component['owners']}
        need('one-source-per-request', set(owners) == set(selected), kind)
        for name in selected:
            owner = owners[name]; cap = owner.get('capability')
            need('complete-independent-source', isinstance(cap, dict)
                 and cap.get('typeName') == name and cap.get('closedCarrierProved') is True
                 and cap.get('nullAdmitted') is True and cap.get('positiveAdmitted') is True,
                 dict(typeName=name, status=owner.get('status'), reason=owner.get('reason')))
            capabilities[name] = cap
        components[kind] = component
    need('all-requested-children-proved', set(capabilities) == set(names))
    _publication_gate(image, pins)
    return dict(schema=SCHEMA, nativeInputs=pins, capabilities=capabilities,
                proofs=components, containingFieldsAdmitted=False, runtimeEvaluationProved=False)


def _special(image, pins, value):
    if value == 'Beyond.ObjectPtr`1<Beyond.Gameplay.Core.GlobalBuff>':
        from scripts.game_data.memorypack import levelscript_global_buff_param_sources as owner
        from scripts.game_data.codecs.levelscript.current_global_buff_param import validate
        proof = owner.derive(image, pins)
        cap = proof['capabilities'][owner.CAPABILITY]
        validate(cap)
        need('own-GlobalBuff-Param-source', proof['nativeInputs'] == pins and cap['valueType'] == value)
        return cap, proof
    if value == 'Beyond.Gameplay.Core.AirWallPtr':
        import json
        from scripts.game_data import levelscript_airwall_ptr_param_native as owner
        from scripts.game_data.memorypack import airwall_ptr_param
        from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
        from scripts.game_data.codecs.levelscript.current_airwall_param import validate
        path = owner.CONTRACT_PATH
        raw = path.read_bytes(); fact = json.loads(raw)
        need('own-AirWall-reviewed-source', set(fact) == {'schema','status','nativeInputs','codecKind','profile','proof'}
             and fact['schema'] == 'endfield.levelscript-airwall-ptr-param-native.v1'
             and fact['status'] == 'conditional-current-build-wire'
             and fact['codecKind'] == 'Param<AirWallPtr>' and fact['nativeInputs'] == pins)
        actual = airwall_ptr_param.derive(image, pins, fact['profile'])
        validate_claims(fact['proof'], actual, label='interactiveParamSource.AirWall.source')
        validate_claims(actual, fact['proof'], label='interactiveParamSource.AirWall.declaration')
        need('own-AirWall-raw24', actual['rawSize'] == 24 and actual['boxedSize'] == 40)
        reference = primitive._reference_join(image, pins, value)
        reader = primitive._reader(image, pins)
        cap = primitive._capability(value, 'airwall-raw24', 24, reader, reference['adapter'])
        cap.update(constantFields=actual['valueFields'], rawValueBitsPreserved=True,
                   runtimeAirWallResolutionProved=False)
        validate(cap)
        need('AirWall-contract-bookend', path.read_bytes() == raw)
        return cap, dict(nativeInputs=pins, reviewedSource=fact, actualSource=actual,
                         canonicalReference=reference, referenceReader=reader)
    if value == 'Beyond.Gameplay.Core.SplinePtr':
        from scripts.game_data.memorypack import levelscript_action_spline_param_sources as spline
        proof = spline.derive(image, pins)
        return proof['capability'], proof
    if value == 'Beyond.Gameplay.Core.ScriptTaskPtr':
        from scripts.game_data.memorypack import levelscript_script_task_param_sources as task
        from scripts.game_data.codecs.levelscript.current_condition_script_task_param import validate
        proof = task.derive(image, pins)
        cap = proof['capabilities'][task.CAPABILITY]
        validate(cap)
        need('own-ScriptTask-Param-source', proof['nativeInputs'] == pins and cap['valueType'] == value)
        return cap, proof
    if value == 'Beyond.Gameplay.View.CameraControlStateInitialParam':
        from scripts.game_data import levelscript_camera_initial_param_native as camera
        from scripts.game_data.codecs.levelscript.current_camera_initial_param import validate
        path = camera.DEFAULT_CONTRACT
        raw = path.read_bytes(); fact = camera._contract(path)
        need('selected-camera-initial-contract', fact['nativeInputs'] == pins)
        fields = camera._validate_native(image, fact)
        reference = primitive._reference_join(image, pins, value)
        reader = primitive._reader(image, pins)
        cap = primitive._capability(value, 'camera-initial-raw24', 24, reader, reference['adapter'])
        cap.update(constantFields=fields, rawValueBitsPreserved=True, runtimeCameraExecutionProved=False)
        validate(cap)
        need('camera-initial-contract-bookend', path.read_bytes() == raw)
        return cap, dict(nativeInputs=pins, reviewedSource=fact, canonicalReference=reference, referenceReader=reader)
    if value == 'System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>':
        from scripts.game_data.memorypack import levelscript_gameplay_tag_list_param_sources as tags
        proof = tags.derive(image, pins)
        cap = proof['capabilities'][tags.CAPABILITY]
        need('own-positive-generated-tag-list', cap.get('typeName') == tags.TYPE
             and cap.get('positiveCountsAdmitted') is True and cap.get('exactOwnNominalsProved') is True)
        return cap, proof
    import json
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data import levelscript_camera_state_param_native as camera
    path = CONTRACTS_DIR / 'levelscript_camera_state_param_native.json'
    raw = path.read_bytes(); fact = camera._contract(path)
    need('selected-camera-contract', fact['nativeInputs'] == pins)
    width = camera._validate_native(image, fact)
    reference = primitive._reference_join(image, pins, value)
    reader = primitive._reader(image, pins)
    cap = primitive._capability(value, 'reference-null-only', width, reader, reference['adapter'])
    cap.update(constantMarker=255, positiveConstantAdmitted=False,
               actualCallbackEqualsProvedChildRequired=True)
    need('camera-constant-exact-FF-and-contract-bookend', width == 1 and path.read_bytes() == raw)
    return cap, dict(nativeInputs=pins, reviewedSource=fact, canonicalReference=reference,
                     referenceReader=reader, cameraPositiveConstantAdmitted=False)
