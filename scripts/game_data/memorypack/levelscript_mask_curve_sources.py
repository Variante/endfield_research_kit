"""CommonMask's own typed curve call joined to the current Unity formatter.

The existing mask contract proves its complete positive caller and reference
Param, including the exact curve source/store. Only its old curve child was
FF-only. This explicit composition leaves that contract and default scope
unchanged and requires the independently proved Unity custom formatter.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA = 'endfield.levelscript-mask-curve-components.v1'
CAPABILITY = 'story-actionmap-mask-param'
TYPE = 'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.CommonMaskBlendData>'


def need(check, condition):
    if not condition:
        raise ValueError('maskCurve.' + check)


def curve_call_program(regions, entry):
    """Actual RDX MethodInfo, same Reader RBX and current wrapper RSI."""
    g = BytesPath(regions, entry)
    cell = g.relative('488b15')
    g.take('488bcb', '488b37')
    site = g.at
    target = g.relative('e8')
    return dict(selectedBytes=g.seen, usageCellVa=cell, sourceInstructionVa=site,
                sourceTargetVa=target, sameReaderRbx=True, currentWrapperRsi=True)


def derive(image, pins, *, count_limit=4096):
    from scripts.game_data import levelscript_mask_param_native as legacy
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import skill_animation_curve_sources as curve
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.codecs.levelscript.current_mask_curve_param import validate
    _publication_gate(image, pins)
    path = legacy.DEFAULT_CONTRACT
    before = path.read_bytes()
    fact = legacy._contract(path)
    need('same-mask-source-native-inputs', fact['nativeInputs'] == pins)
    old = legacy._validate_native(image, fact)
    child = curve.derive(image, pins, count_limit=count_limit)
    curve_cap = child['capabilities'][curve.CAPABILITY]
    requests = [row for row in fact['positive']['usageContexts']
                if row.get('tag') == 6 and row.get('methodArguments') == [curve.TYPE]]
    need('one-owned-mask-curve-request', len(requests) == 1)
    usage = derive_typed_usage_context(image, requests[0]['instructionRva'], label='maskCurve.actualRequest')
    need('same-fresh-mask-curve-request', usage == requests[0])
    body = owned(image, image.pe.image_base + fact['positive']['programs']['mask']['entryRva'])
    call = curve_call_program(body['regions'], image.pe.image_base + usage['instructionRva'])
    need('own-ordinary-curve-ReadValue', (usage['typeName'], usage['methodName'], usage['classArguments'], usage['methodArguments'])
         == ('MemoryPack.MemoryPackReader', 'ReadValue', [], [curve.TYPE])
         and usage['methodSpec'][0] == curve_cap['referenceReaderMethodDefinition']
         and call['sourceTargetVa'] - image.pe.image_base == curve_cap['referenceReaderTargetRva']
         and call['usageCellVa'] - image.pe.image_base == usage['usageCellRva'])
    cap = dict(schema='endfield.levelscript-mask-curve-capability.v1', typeName=TYPE,
               memberCount=4, maskMemberCount=6, fieldOrder=['constValue', 'idRef', 'paramSource', 'path'],
               maskFieldOrder=['audioBlackScreenBehaviour', 'curve', 'fadeInDuration', 'fadeOutDuration', 'maskType', 'useCurve'],
               audioRawBytes=16, audioFields=old['audioFields'], curveCapability=curve_cap,
               positiveMaskAndCurveAdmitted=True, curveNullOnly=False, pathEncoding='int32-pool-index',
               rawBooleanBytePreserved=True, rawFloatBitsPreserved=True,
               actualCurveCallbackEqualsProvedChildRequired=True, liveFormatterSelectionObserved=False,
               runtimeMaskExecutionProved=False, wholeOwnerAdmitted=False)
    validate(cap)
    need('mask-contract-bookend', path.read_bytes() == before)
    _publication_gate(image, pins)
    return json.loads(json.dumps(dict(schema=SCHEMA, status='validated-conditional-mask-curve-components', nativeInputs=pins,
        capabilities={CAPABILITY: cap}, proof=dict(maskContract=path.name, maskSource=fact,
            curveSource=child, actualCurveRequest=usage, actualCurveCall=call,
            maskWindows=body['windows'], maskRegions=[[a, b.hex().upper()] for a, b in body['regions']]),
        parentFieldAdmitted=False, wholeOwnerAdmitted=False)))
