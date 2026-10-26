"""Independent current ActionMap Params missed by the legacy inline adapters.

Each source is freshly derived from the selected image. A null BuffPtr list
does not admit elements; the nominal enum remains distinct from primitive int.
Containing union requests, stores and frames are owned by the route validator.
"""
import json

from scripts.game_data.memorypack.levelscript_condition_param_sources import (
    PREFIX, CAP_PREFIX, need, _reader, _reference_join, _capability,
)

BUFF_LIST = 'System.Collections.Generic.List`1<Beyond.Gameplay.Core.BuffPtr>'
MODEL_VISIBLE = 'Beyond.Gameplay.View.ModelVisibleType'
BUFF_SCHEMA = 'endfield.story-action-null-buff-list-param.v1'
KINDS = ('Param<List<BuffPtr>>', 'Param<ModelVisibleType>')


def buff_list_null_program(regions, entry, *, header, barrier):
    """Own this List<BuffPtr> null return, including saved XMM6 and full frame.

    The selected path never reads its List context or calls an element. It
    assumes ready metadata and stable disjoint Reader, bytes, output and frame.
    No positive/empty list grammar is inferred from the hidden16 element type.
    """
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    g = BytesPath(regions, entry)
    g.take('488bc4', '48895808', '48897018', '48897820', '4154', '4156', '4157', '4883ec50')
    ready = g.relative('803d') + 1
    g.take('00', '498bd9', '0f2970d8', '498bf8', '4c8be2')
    g.branch('75', True, 1)
    g.take('0f57c0', 'c744247800000000', '488d542478', '498bcc', '0f11442420')
    g.call(header)
    g.take('84c0')
    g.branch('0f84', True)
    g.take('488bcf', '48c70700000000')
    g.call(barrier)
    g.take('0f28742440', '4c8d5c2450', '498b5b20', '498b7330', '498b7b38',
        '498be3', '415f', '415e', '415c', 'c3')
    return dict(selectedBytes=g.seen, collectionCount=-1, wireBytes=4,
        returnedReference=0, metadataReadyFlagVa=ready, outputBytes=8,
        elementCallbacks=0, typedListContextRead=False, entryRspRestored=True,
        allIntegerNonvolatilesRestored=True, xmmNonvolatilesRestored=['xmm6'],
        normalReturn=True, positiveCountsAdmitted=False)


def derive(image, pins, *, codec_kind):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    need('explicit-action-Param-domain', codec_kind in KINDS)
    _publication_gate(image, pins)
    if codec_kind == 'Param<ModelVisibleType>':
        from scripts.game_data.memorypack.levelscript_condition_enum_param_components import derive_many
        component = derive_many(image, pins, [PREFIX + MODEL_VISIBLE + '>'])
        name = CAP_PREFIX + PREFIX + MODEL_VISIBLE + '>'
        need('own-complete-ModelVisible-Param', name in component['capabilities'])
        result = dict(codecKind=codec_kind, capability=component['capabilities'][name], proof=component)
    else:
        from scripts.game_data.memorypack import pointer_param, utf8_source_helper
        from scripts.game_data.memorypack.current_reference_param_sources import derive_reference_parent
        from scripts.game_data.il2cpp.generic_entries import GenericEntries
        from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
        from scripts.game_data.levelscript_family_regenerate import Build
        from scripts.game_data.codecs.levelscript.current_action_params import validate_null_buff_capability
        source = derive_reference_parent(image, pins, value_type=BUFF_LIST, reader_method='ReadPackable')
        base = image.pe.image_base
        constant_target = source['programs'][0]['sourceCalls']['constValue']
        Build(image, pins).prove_named_target(constant_target, 'MemoryPack.MemoryPackReader',
            'ReadPackable', result_abi='reference')
        usage = source['typedRead']
        need('own-closed-Buff-list-constant-request', usage['methodArguments'] == [BUFF_LIST])
        ctx = NativeReferenceContext(image)
        owner = ctx.index.types['MemoryPack.Formatters.ListFormatter`1']
        method, = [m for m in image.metadata.methods_for(owner)
            if image.metadata.string(m.name_index) == 'Deserialize']
        entry = GenericEntries(image).resolve(method.index, ['Beyond.Gameplay.Core.BuffPtr'], [])
        body = pointer_param.owned(image, entry['pointer'])
        headers = utf8_source_helper._contract()
        need('same-Buff-list-header-inputs', headers['nativeInputs'] == pins)
        header_proof = utf8_source_helper._validate_native(image, headers)
        null_program = buff_list_null_program(body['regions'], body['pointer'],
            header=base + headers['bodies']['header']['entryRva'],
            barrier=base + source['barrierTargetRva'])
        reference = _reference_join(image, pins, BUFF_LIST)
        reader = _reader(image, pins)
        need('same-owned-Buff-list-Param-getter', source['ownedMethods']['GetValue']['pointerRva']
            == reference['getter']['entryRva'])
        need('own-null-Buff-list-source', null_program['collectionCount'] == -1
            and null_program['wireBytes'] == 4 and null_program['returnedReference'] == 0)
        cap = _capability(BUFF_LIST, 'null-buff-list', 4, reader, reference['adapter'])
        cap.update(schema=BUFF_SCHEMA, collectionCounts=[-1], positiveElementsAdmitted=False)
        validate_null_buff_capability(cap)
        result = dict(codecKind=codec_kind, capability=cap,
            proof=dict(source=source, reference=reference, reader=reader,
                listRegistration=entry, listWindows=body['windows'],
                listRegions=[[a, raw.hex().upper()] for a, raw in body['regions']],
                nullListProgram=null_program, headerSource=header_proof))
    _publication_gate(image, pins)
    return json.loads(json.dumps(result))
