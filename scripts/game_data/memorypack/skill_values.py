"""Named stored SkillData values joined to the active current native grammar.

The generated wrapper plan supplies declared types, never admission. The
current operation supplies each actual union assignment and ordered field
program; its independent complete raw replay supplies field extents and EOF.
"""
from __future__ import annotations

import struct

from scripts.game_data.memorypack.derived_values import ValueReader
from scripts.game_data.memorypack.derived_schema import PROFILE
from scripts.game_data.memorypack.skill_root_components import root_reads
from scripts.game_data.memorypack.skill_animation_curve_codec import require_capability
from scripts.game_data.memorypack.stored_value_layouts import StoredValueLayouts
from scripts.game_data.skill_timeline_current_sequence_native import prepared_current_sequence

PREFIX = 'Beyond.Gameplay.Core.'
# These names join the explicit reads in CurrentSequenceReader's separately
# authenticated root/group/timeline/sequence implementations. No new framing.
FINITE_ORDERS = {
    PREFIX+'SkillData': ['actionGroupData', *[r['fieldName'] for r in root_reads()]],
    PREFIX+'ActionGroupData': ['passiveEventActions','timelineActions'],
    PREFIX+'SequenceActionData': ['actionData','onlyExecuteWhenSourceIsGuard','onlyExecuteWhenSourceIsMainChar'],
    PREFIX+'TimelineAction+TimelineActionData': ['_endFrame','_sequenceActionData','_startFrame','forceSyncAnimData'],
    PREFIX+'TimelineAction+ForceSyncAnimData': ['forceSync','montageName','playbackSpeed','targetFrame'],
}
FAMILIES = {'AbilityActionData': PREFIX+'AbilityAction+AbilityActionData',
            'SelectorFinder': PREFIX+'Selector+Finder+Data',
            'SelectorValidator': PREFIX+'Selector+Validator+Data',
            'SelectorPostProcessor': PREFIX+'Selector+PostProcessor+Data'}


def need(check, condition, detail=''):
    if not condition:
        raise ValueError('skillValues.' + check + ':' + str(detail)[:1000])


class SkillValueSchema:
    ROOT_COUNT = 49
    ROOT_EXACT_FLAG = 'wholeSkillDataExact'

    def __init__(self, *, operation, registry, image):
        self.operation = prepared_current_sequence(operation)
        proof = self.operation.proof
        self.registry = registry
        self.orders = dict(FINITE_ORDERS)
        self.unions = {}
        self.layouts = StoredValueLayouts(image)
        self.types = set()
        self.curve = require_capability(self.operation.child('curve-profile'))
        def visit(value):
            if isinstance(value, dict):
                name = value.get('typeName', value.get('wrappedType'))
                reads = value.get('orderedReads', value.get('reads'))
                if name and isinstance(reads, list) and all('fieldName' in r for r in reads):
                    order = [r['fieldName'] for r in reads]
                    previous = self.orders.setdefault(name, order)
                    need('one-native-field-order', previous == order, name)
                for child in value.values(): visit(child)
            elif isinstance(value, list):
                for child in value: visit(child)
        visit(proof['capabilities']); visit(proof['programs'])
        for program in proof['programs']:
            base = FAMILIES[program['family']]
            self.unions.setdefault(base, {})[program['tag']] = program['wrappedType']
        for cap in proof['capabilities'].values():
            if 'routes' in cap:
                self.unions[cap['typeName']] = {
                    r['tag']: r.get('wrappedType', r.get('typeName')) for r in cap['routes']}

    def decode(self, raw, *, definition, source, receipt, on_decoded=None):
        self.operation._active()
        need('complete-independent-native-root', receipt.get(self.ROOT_EXACT_FLAG) is True
             and receipt.get('parserCursor') == receipt.get('hardLimit') == len(raw)
             and receipt.get('stopReason') is None, source)
        reader = SkillValueReader(raw, source, registry=self.registry,
                                  strings=self.operation.strings, schema=self)
        value = reader.read_record(definition)
        need('physical-EOF', reader.pos == len(raw), source)
        need('complete-root-field-count', isinstance(value, dict) and len(value) == self.ROOT_COUNT, source)
        need('native-root-field-extents', reader.objects[(0, len(raw))]['fields'] == [
            {k:r[k] for k in ('fieldName','start','end')} for r in receipt['rootFields']], source)
        checked = self.ROOT_COUNT
        for record in receipt['records']:
            fields = record.get('fields')
            if not fields: continue
            span = (record['start'], record['end'])
            obj = reader.objects.get(span)
            # Some codecs record an enclosing union rather than its wrapper.
            if obj is None and raw[span[0]] != 255:
                width = 3 if raw[span[0]] == 250 else 1
                obj = reader.objects.get((span[0] + width, span[1]))
            need('native-child-object-extent', obj is not None, (source, record['kind'],span))
            need('native-child-field-extents', obj['fields'] == [
                {k:r[k] for k in ('fieldName','start','end')} for r in fields], (source,record['kind'],span))
            checked += len(fields)
        # The current reader must account for every byte independently of the
        # named value plan. Its range partition cannot skip headers or tails.
        cursor = 0
        for part in receipt['byteRanges']:
            need('native-byte-partition', part['start'] == cursor and part['end'] > cursor, source)
            cursor = part['end']
        need('native-byte-partition-EOF', cursor == len(raw), source)
        if on_decoded is not None:
            on_decoded(reader, value)
        return value, dict(wholeSchemaExact=True, physicalEOF=True,
            nativeFieldExtentsChecked=checked, namedObjectCount=len(reader.objects),
            scalarValuesDecoded=reader.scalars, curveCount=reader.curves,
            namedTypeCount=len(reader.types), unionAssignmentsChecked=reader.unions,
            sourceIdAndPhysicalEofProved=True, rawValueBitsPreserved=True,
            runtimeExecutionProved=False)


class SkillValueReader(ValueReader):
    def __init__(self, *args, schema, **kwargs):
        super().__init__(*args, **kwargs)
        self.schema = schema
        self.objects = {}; self.types=set(); self.scalars=0; self.curves=0; self.unions=0

    def _value_object(self, definition, depth):
        self._plan_depth_guard(depth)
        name = self.plan_registry.wrapped_names[definition]
        start = self.pos
        if self.peek() == 255:
            self.take(1, 'null-wrapper'); return None
        members = self.plan_registry.plans[definition]
        need('source-owned-field-order', self.schema.orders.get(name) == [m.name for m in members],
             (self.source, start, name, self.schema.orders.get(name), [m.name for m in members]))
        self.header(len(members)); result={}; fields=[]
        for member in members:
            at=self.pos; result[member.name]=self._value_member(member,depth+1)
            fields.append(dict(fieldName=member.name,start=at,end=self.pos))
        self.objects[(start,self.pos)] = dict(typeName=name,fields=fields,value=result)
        self.types.add(name); self.schema.types.add(name)
        return result

    def _value_fixed(self, member):
        raw = self.take(member.width or 0, 'typed:' + str(member.declared_type))
        need('declared-scalar-type', bool(member.declared_type), member.name)
        self.scalars += 1
        return self.schema.layouts.read(member.declared_type, raw)

    def _value_member(self, member, depth):
        if member.kind != PROFILE:
            return super()._value_member(member, depth)
        self._plan_depth_guard(depth)
        need('only-source-owned-custom-profile', member.profile == 'curve_profile'
             and member.declared_type == 'UnityEngine.AnimationCurve', member.name)
        cap=self.schema.curve; self.curves += 1
        if self.peek()==255:
            self.take(1,'null-unity-curve'); return None
        self.header(3)
        pre=struct.unpack('<i',self.take(4,'preWrapMode'))[0]
        post=struct.unpack('<i',self.take(4,'postWrapMode'))[0]
        count=self.count(28,nullable=True)
        need('source-owned-curve-count', -1<=count<=cap['countLimit'], count)
        keys=[]
        for _ in range(max(0,count)):
            keys.append({field['fieldName']:self.schema.layouts.read(field['declaredType'],
                self.take(4,field['fieldName'])) for field in cap['keyframeFields']})
            self.scalars += len(cap['keyframeFields'])
        return dict(preWrapMode=pre,postWrapMode=post,keys=None if count==-1 else keys)

    def _value_union(self, base, depth):
        start=self.pos
        value=super()._value_union(base,depth)
        if value is not None:
            name=self.plan_registry.wrapped_names[base]
            expected=self.schema.unions.get(name,{}).get(value['$tag'])
            need('actual-native-union-assignment',expected==value['$type'],
                 (self.source,start,name,value['$tag'],expected,value['$type']))
            self.unions += 1
        return value

    def _value_map(self, member, depth):
        if not member.pair_size:
            return super()._value_map(member,depth)
        need('typed-unmanaged-pair', member.key is not None and member.value is not None
             and member.value_offset == member.key.width
             and member.pair_size == member.key.width + member.value.width, member.name)
        if member.header:
            if self.peek()==255:
                self.take(1,'null-map');return None
            self.header(1)
        count=self.count(member.pair_size,nullable=True)
        if count<0:return None
        return [dict(key=self._value_fixed(member.key),value=self._value_fixed(member.value)) for _ in range(count)]
