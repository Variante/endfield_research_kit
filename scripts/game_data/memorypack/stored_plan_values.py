"""Bit-preserving values for existing derived plans, at structuralOnly tier.

This executes no new inferred framing. Profile bodies require an explicit
source-bound reader supplied by the caller; native joins remain its obligation.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Any, Callable
from scripts.game_data.memorypack.buff_actions import Reader, Unsupported
from scripts.game_data.memorypack.derived_plans import DerivedPlanMixin, NULL_MARKER, WIDE_TAG_LEAD
from scripts.game_data.memorypack.derived_schema import FIXED, STRING, PROFILE, OBJECT, LIST, MAP, UNION, NULL_ONLY

SCHEMA = 'endfield.memorypack-stored-plan-values.v1'


def _require(ok: bool, detail: str) -> None:
    if not ok:
        raise ValueError('storedPlanValues:' + detail)


def fixed_node(raw: bytes, *, scalar: str | None = None) -> dict:
    _require(isinstance(raw, bytes) and bool(raw), 'nonempty-fixed-word')
    return {'kind': 'fixed', 'width': len(raw), 'scalar': scalar, 'rawHex': raw.hex().upper()}


def string_node(value: str | None) -> dict:
    payload = b'' if value is None else value.encode('utf-8', 'strict')
    return {'kind': 'string', 'byteLength': -1 if value is None else len(payload),
            'payloadHex': payload.hex().upper(), 'utf8Valid': True, 'utf8Value': value}


def object_node(members: list[dict], *, null: bool = False) -> dict:
    return {'kind': 'object', 'null': null, 'memberCount': None if null else len(members),
            'memberOrder': [m['fieldName'] for m in members], 'members': members}


class StoredPlanReader(DerivedPlanMixin, Reader):
    def __init__(self, *args, registry, profile_reader: Callable | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.plan_registry = registry
        self.profile_reader = profile_reader

    def read_stored_record(self, definition: int, depth: int = 0) -> dict:
        self._plan_depth_guard(depth)
        plan = self.plan_registry.plans.get(definition)
        if plan is None:
            raise Unsupported(self.source, self.pos, 'a planned wrapper', definition, 'unplanned')
        start = self.pos
        if self.peek() == NULL_MARKER:
            self.take(1, 'null-wrapper')
            node = object_node([], null=True)
        else:
            _require(len(plan) < WIDE_TAG_LEAD, 'object-member-count')
            self.header(len(plan))
            node = object_node([self.read_stored_member(member, depth + 1) for member in plan])
        return {**node, 'definition': definition, 'start': start, 'end': self.pos}

    def read_stored_member(self, member, depth: int) -> dict:
        self._plan_depth_guard(depth)
        start = self.pos
        kind = member.kind
        if kind == FIXED:
            _require(type(member.width) is int and member.width > 0, 'fixed-plan-width')
            node = fixed_node(self.take(member.width, member.name), scalar=member.scalar)
        elif kind == STRING:
            count = self.count(1, nullable=True)
            payload = self.take(max(0, count), member.name)
            try:
                value = None if count == -1 else payload.decode('utf-8', 'strict')
                valid = True
            except UnicodeDecodeError:
                value, valid = None, False
            node = {'kind': 'string', 'byteLength': count, 'payloadHex': payload.hex().upper(),
                    'utf8Valid': valid, 'utf8Value': value}
        elif kind == OBJECT:
            node = self.read_stored_record(member.ref, depth + 1)
        elif kind == NULL_ONLY:
            self.header(NULL_MARKER)
            node = {'kind': 'null-only'}
        elif kind == PROFILE:
            if not callable(self.profile_reader):
                raise Unsupported(self.source, self.pos, 'an explicit source-bound profile reader', member.profile, 'unbound-profile')
            node = self.profile_reader(self, member, depth)
            _require(encode_stored_node(node) == self.data[start:self.pos], 'profile-named-reencode')
        elif kind == LIST:
            _require(member.element is not None, 'list-element-plan')
            minimum = member.element.width if member.element.kind == FIXED and member.element.width else 1
            count = self.count(minimum, nullable=True)
            node = {'kind': 'list', 'count': count,
                    'elements': [self.read_stored_member(member.element, depth + 1)['value'] for _ in range(max(0, count))]}
        elif kind == MAP:
            headered = bool(member.header)
            null_object = headered and self.peek() == NULL_MARKER
            if headered:
                self.header(NULL_MARKER if null_object else 1)
            pair_size = member.pair_size or 0
            if null_object:
                count, entries = None, []
            elif pair_size:
                count = self.count(pair_size, nullable=True)
                entries = [fixed_node(self.take(pair_size, member.name + '.pair')) for _ in range(max(0, count))]
            else:
                _require(member.key is not None and member.value is not None, 'map-pair-plan')
                minimum = member.key.width if member.key.kind == FIXED and member.key.width else 1
                count = self.count(minimum, nullable=True)
                entries = [{'key': self.read_stored_member(member.key, depth + 1)['value'],
                            'value': self.read_stored_member(member.value, depth + 1)['value']} for _ in range(max(0, count))]
            node = {'kind': 'map', 'headered': headered, 'nullObject': null_object,
                    'pairSize': pair_size, 'count': count, 'entries': entries}
        elif kind == UNION:
            tags = self.plan_registry.union_tag_maps.get(member.ref)
            _require(tags is not None, 'union-plan')
            lead = self.peek()
            if lead == NULL_MARKER:
                self.take(1, 'null-union')
                node = {'kind': 'union', 'null': True}
            else:
                _require(lead <= WIDE_TAG_LEAD, 'union-marker')
                width = 3 if lead == WIDE_TAG_LEAD else 1
                tag = struct.unpack_from('<H', self.take(3, 'wide-union'), 1)[0] if width == 3 else self.take(1, 'union-tag')[0]
                definition = tags.get(tag)
                _require(definition is not None, 'union-subtype')
                node = {'kind': 'union', 'null': False, 'tag': tag, 'tagWidth': width,
                        'definition': definition, 'value': self.read_stored_record(definition, depth + 1)}
        else:
            raise Unsupported(self.source, self.pos, 'a known plan kind', kind, 'plan-kind')
        return {'fieldName': member.name, 'start': start, 'end': self.pos, 'value': node}


def encode_stored_node(node: dict, depth: int = 0) -> bytes:
    _require(type(depth) is int and 0 <= depth <= 256, 'encode-depth')
    kind = node['kind']
    encode = lambda child: encode_stored_node(child, depth + 1)
    if kind == 'fixed':
        raw = bytes.fromhex(node['rawHex'])
        _require(type(node['width']) is int and node['width'] > 0 and len(raw) == node['width'], 'fixed-word-width')
        return raw
    if kind == 'string':
        count, raw = node['byteLength'], bytes.fromhex(node['payloadHex'])
        _require(type(count) is int and -1 <= count <= 0x7fffffff and len(raw) == max(0, count), 'string-byte-count')
        if node.get('utf8Valid'):
            _require((None if count == -1 else raw.decode('utf-8', 'strict')) == node.get('utf8Value'), 'string-named-value')
        return struct.pack('<i', count) + raw
    if kind in ('object', 'struct'):
        members = node['members']
        names = [m['fieldName'] for m in members]
        _require(names == node['memberOrder'] and len(names) == len(set(names)), 'named-member-order')
        if kind == 'object':
            if node['null']:
                _require(not members and node['memberCount'] is None, 'null-object-members')
                return b'\xff'
            count = node['memberCount']
            _require(type(count) is int and 0 <= count < WIDE_TAG_LEAD and count == len(members), 'object-member-count')
            prefix = bytes((count,))
        else:
            prefix = b''
        return prefix + b''.join(encode(m['value']) for m in members)
    if kind == 'null-only':
        return b'\xff'
    if kind == 'list':
        count, elements = node['count'], node['elements']
        _require(type(count) is int and -1 <= count <= 0x7fffffff and len(elements) == max(0, count), 'list-count')
        return struct.pack('<i', count) + b''.join(encode(value) for value in elements)
    if kind == 'map':
        if node['nullObject']:
            _require(node['headered'] and node['count'] is None and not node['entries'], 'null-map-object')
            return b'\xff'
        count, entries = node['count'], node['entries']
        _require(type(count) is int and -1 <= count <= 0x7fffffff and len(entries) == max(0, count), 'map-count')
        prefix = (b'\x01' if node['headered'] else b'') + struct.pack('<i', count)
        if node['pairSize']:
            _require(type(node['pairSize']) is int and node['pairSize'] > 0, 'map-pair-size')
            _require(all(entry['kind'] == 'fixed' and entry['width'] == node['pairSize'] for entry in entries), 'map-pair-width')
            return prefix + b''.join(encode(entry) for entry in entries)
        return prefix + b''.join(encode(entry['key']) + encode(entry['value']) for entry in entries)
    if kind == 'union':
        if node['null']:
            return b'\xff'
        tag, width = node['tag'], node['tagWidth']
        _require(type(tag) is int and 0 <= tag <= 0xffff and width in (1, 3), 'union-tag')
        _require(width == 3 or tag < WIDE_TAG_LEAD, 'union-short-tag')
        prefix = bytes((tag,)) if width == 1 else b'\xfa' + struct.pack('<H', tag)
        return prefix + encode(node['value'])
    raise ValueError('storedPlanValues:unknown-encode-kind:' + str(kind))


def decode_stored_plan(data: bytes, *, source: str, digest: str, start: int, end: int,
                       definition: int, registry: Any, profile_reader: Callable | None = None) -> dict:
    _require(isinstance(data, bytes) and bool(source) and isinstance(digest, str)
             and hashlib.sha256(data).hexdigest().upper() == digest.upper()
             and type(start) is int and type(end) is int and 0 <= start < end <= len(data), 'authenticated-source-and-span')
    reader = StoredPlanReader(data, source, end, registry=registry, profile_reader=profile_reader)
    reader.pos = start
    node = reader.read_stored_record(definition)
    _require(reader.pos == end, 'complete-plan-end')
    _require(encode_stored_node(node) == data[start:end], 'named-plan-reencode')
    return {'schema': SCHEMA, 'source': source, 'logicalSha256': digest.upper(),
            'start': start, 'end': end, 'storedTree': node, 'namedFieldReencodeExact': True,
            'evidenceTier': 'structuralOnly', 'nativeBindingProved': False,
            'wholeRootAdmitted': False, 'runtimeExecutionKnown': False}
