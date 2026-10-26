"""Read finite compiled ActionMap records without inferring child grammars.

This pure cursor consumes capabilities. Only the private operation gateway
authenticates their native source. Raw bits and the legacy field projection
are both retained; neither establishes runtime selection or execution.
"""
import math
import struct

from scripts.game_data.memorypack.levelscript_action_param_registry import codec_for_schema as _ordinary_param_codec
from scripts.game_data.codecs.levelscript.param_graph import Reader

SCHEMA = 'endfield.generated-actionmap-route-capability.v1'
OPERATIONS = frozenset(('bool-byte', 'byte', 'scalar32', 'scalar64-bits',
                       'float32-bits', 'float64-bits', 'byte-payload', 'condition-param', 'actionmap-param-output', 'actionmap-param-array'))


def _param_codec(schema):
    from scripts.game_data.memorypack.levelscript_vector_param_array_sources import SCHEMA as ARRAY
    if schema == ARRAY:
        from scripts.game_data.codecs.levelscript import current_vector_param_array
        return current_vector_param_array
    from scripts.game_data.memorypack.levelscript_action_output_components import SCHEMA as OUTPUT
    if schema == OUTPUT:
        from scripts.game_data.codecs.levelscript import current_action_output_param
        return current_action_output_param
    return _ordinary_param_codec(schema)


def need(check, condition):
    if not condition:
        raise ValueError('currentGeneratedActionRoute.' + check)


def validate(cap):
    need('finite-owned-route', isinstance(cap, dict) and cap.get('schema') == SCHEMA
         and cap.get('family') in ('ActionBase', 'GetterBase', 'ActionHeader')
         and type(cap.get('tag')) is int and 0 <= cap['tag'] <= 65535
         and all(type(cap.get(k)) is str and cap[k] for k in ('wrapperName', 'typeName'))
         and type(cap.get('memberCount')) is int and 0 <= cap['memberCount'] < 250
         and all(cap.get(k) is True for k in ('nullAdmitted', 'positiveAdmitted',
             'wholeRecordGrammarAdmitted', 'selectedCurrentUnionCaseProved'))
         and all(cap.get(k) is False for k in ('liveFormatterSelectionObserved',
             'runtimeExecutionAdmitted', 'wholeOwnerAdmitted')))
    fields = cap.get('fields'); program = cap.get('program'); params = cap.get('params')
    need('complete-owned-program', isinstance(fields, list) and isinstance(program, dict)
         and isinstance(params, dict) and len(params) <= 256)
    reads = program.get('reads')
    need('complete-ordered-field-reads', isinstance(reads, list)
         and len(reads) == len(fields) == cap['memberCount'] == program.get('memberCount')
         and [f.get('memberIndex') for f in fields] == list(range(len(fields)))
         and all(type(f.get('memberIndex')) is int and type(f.get('fieldName')) is str
                 and f['fieldName'] and type(f.get('declaredType')) is str for f in fields)
         and len({f['fieldName'].lstrip('_') for f in fields}) == len(fields)
         and [(f['memberIndex'], f['fieldName']) for f in fields] ==
             [(r.get('memberIndex'), r.get('fieldName')) for r in reads])
    required = set(); used = set(); joined = []
    for declaration, read in zip(fields, reads, strict=True):
        kind = read.get('kind'); child = read.get('childCapability')
        need('finite-source-operation', kind in OPERATIONS)
        if kind in ('condition-param', 'actionmap-param-output', 'actionmap-param-array'):
            component = params.get(child)
            need('same-independent-Param-child', isinstance(component, dict)
                 and isinstance(component.get('capability'), dict)
                 and component['capability'].get('closedArrayType' if kind == 'actionmap-param-array' else 'typeName') == declaration['declaredType'])
            _param_codec(component.get('componentSchema')).validate(component['capability'])
            from scripts.game_data.memorypack.levelscript_vector_param_array_sources import SCHEMA as ARRAY_SCHEMA,CAPABILITY as ARRAY_CAPABILITY,TYPE as ARRAY_TYPE
            need('distinct-owned-vector-Param-array-operation',
                 (component.get('componentSchema') == ARRAY_SCHEMA) is (kind == 'actionmap-param-array')
                 and (kind != 'actionmap-param-array' or (child == ARRAY_CAPABILITY and declaration['declaredType'] == ARRAY_TYPE)))
            from scripts.game_data.codecs.levelscript.current_action_output_param import SCHEMA as OUTPUT_CAP
            need('distinct-Output-and-constant-Param-operations',
                 (component['capability'].get('schema') == OUTPUT_CAP) is (kind == 'actionmap-param-output'))
            required.add(child); used.add(child); joined.append((declaration, read, component['capability']))
        elif kind == 'byte-payload':
            need('own-pooled-field', declaration['declaredType'] == 'string' and child == 'byte-payload')
            required.add(child)
        else:
            need('atomic-operation-has-no-child', child is None)
    need('exact-owned-child-set', used == set(params)
         and program.get('requiredCapabilities') == sorted(required))
    bindings = program.get('childBindings')
    need('complete-own-child-bindings', isinstance(bindings, list) and len(bindings) == len(joined)
         and all(isinstance(b, dict) for b in bindings))
    for binding, (declaration, read, child) in zip(bindings, joined, strict=True):
        need('exact-parent-Param-binding',
             (binding.get('fieldName'), binding.get('typeName'), binding.get('capability')) ==
                 (declaration['fieldName'], declaration['declaredType'], read['childCapability'])
             and type(binding.get('readerMethodDefinition')) is int
             and type(binding.get('sourceTargetRva')) is int
             and (binding['readerMethodDefinition'], binding['sourceTargetRva']) ==
                 (child['readerMethodDefinition'], child['sourceTargetRva'])
             and binding.get('sourceReferenceKind') == 21 and binding.get('referenceOutputBytes') == 8
             and all(binding.get(k) is True for k in ('closedCarrierProved',
                 'actualCallbackEqualsProvedChildRequired', 'parentArgumentLocalStoreFrameRequired'))
             and binding.get('parentFieldAdmitted') is False)
    return cap


def _float(reader, field, width):
    at = reader.offset; reader.need(width, field)
    raw = bytes(reader.data[at:at+width]); reader.offset += width
    value = struct.unpack('<f' if width == 4 else '<d', raw)[0]
    return dict(value=value if math.isfinite(value) else None, rawHex=raw.hex().upper(), finite=math.isfinite(value))


def read_record(reader, field, cap):
    validate(cap)
    start = reader.offset; marker = reader.number('<B', field+'.memberCount')
    if marker == 255:
        return None
    if marker != cap['memberCount']:
        raise ValueError(f'{field}:member-count,offset={start},expected={cap["memberCount"]},actual={marker}')
    values = {}; spans = {}
    for declaration, operation in zip(cap['fields'], cap['program']['reads'], strict=True):
        name = declaration['fieldName']; path = field+'.'+name; at = reader.offset; kind = operation['kind']
        if kind == 'bool-byte':
            byte = reader.number('<B', path); value = dict(value=bool(byte), rawByte=byte)
        elif kind == 'byte':
            value = reader.number('<B', path)
        elif kind in ('scalar32', 'scalar64-bits'):
            bits = reader.number('<I' if kind == 'scalar32' else '<Q', path)
            value = dict(unsignedBits=bits, rawHex=bits.to_bytes(4 if kind == 'scalar32' else 8, 'little').hex().upper())
        elif kind in ('float32-bits', 'float64-bits'):
            value = _float(reader, path, 4 if kind == 'float32-bits' else 8)
        elif kind == 'byte-payload':
            value = reader.string(path)
        else:
            component = cap['params'][operation['childCapability']]
            value = _param_codec(component['componentSchema']).read(reader, path, component['capability'])
        values[name] = value; spans[name] = [at, reader.offset]
    return dict(startOffset=start, endOffset=reader.offset, fields=values, fieldRanges=spans)


def _legacy_param(value):
    if value is None:
        return None
    constant = value['constValue']
    if isinstance(constant, dict) and set(constant) == {'value', 'rawByte'}:
        constant = constant['value']
    elif isinstance(constant, dict) and set(constant) == {'rawHex', 'values', 'finite'}:
        constant = constant['values'][0] if len(constant['values']) == 1 else list(constant['values'])
    return dict(value=constant, idRef=value['idRef'], paramSource=value['paramSource'], path=value['path'])


def decode(data, offset, *, field, capability, strings):
    """Pure capability cursor; this function grants no native admission."""
    cap = validate(capability); reader = Reader(data, offset, strings, field); start = offset
    tag = reader.number('<B', field+'.tag')
    if tag == 250:
        tag = reader.number('<H', field+'.wideTag')
    elif tag >= 250:
        raise ValueError(f'{field}:reserved-union-marker,offset={start},actual={tag}')
    need('exact-selected-current-union-tag', tag == cap['tag'])
    raw = read_record(reader, field+'.record', cap); fields = {}; spans = {}; types = {}
    if raw is not None:
        for declaration, operation in zip(cap['fields'], cap['program']['reads'], strict=True):
            source = declaration['fieldName']; name = source.lstrip('_'); kind = operation['kind']; value = raw['fields'][source]
            if kind == 'condition-param':
                value = _legacy_param(value)
            elif kind == 'actionmap-param-array':
                value = None if value is None else [_legacy_param(item) for item in value]
            elif kind == 'bool-byte':
                value = value['value']
            elif kind in ('scalar32', 'scalar64-bits'):
                bits = value['unsignedBits']; width = 4 if kind == 'scalar32' else 8
                value = bits if declaration['declaredType'] in ('uint', 'ulong') else int.from_bytes(bits.to_bytes(width, 'little'), 'little', signed=True)
            elif kind in ('float32-bits', 'float64-bits'):
                value = value['value']
            fields[name] = value; spans[name] = raw['fieldRanges'][source]; types[name] = declaration['declaredType']
    return dict(sourceOffset=start, endOffset=reader.offset, unionTag=tag,
                memberCount=255 if raw is None else cap['memberCount'], wrapperName=cap['wrapperName'],
                fields=None if raw is None else fields, fieldRanges=spans, fieldTypes=types,
                currentRouteValue=raw), reader.offset
