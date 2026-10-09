"""Derive a narrowly bounded closed generic reference slot from selected types.

Open generic field offsets and sizes are placeholders. A concrete subclass
can witness a sole reference field only when the non-generic base has no
trailing padding and the selected prefix adds exactly one Win64 pointer.
Declared instance fields require an explicit, completely occupied suffix proof.
The caller authenticates the selected NativeImage before and after preparation.
"""
from __future__ import annotations

import struct
from types import SimpleNamespace
from typing import Any
from .protocol import runtime_type_name, runtime_type_field_offsets


class NativeReferenceContext:
    """Selected metadata relationships needed by reference-layout proofs.

    This view never substitutes an open generic's offset or size. An optional
    existing index supplies only its named type table, without re-indexing
    native method bodies or importing a capture entry point.
    """
    def __init__(self, image: Any, *, index: Any = None):
        self.image = image
        self.index = index if index is not None else SimpleNamespace(types={
            image.metadata.type_full_name(td): td for td in image.metadata.types})

    def type_pointer(self, index: int) -> int:
        registration = self.image.registration
        if type(index) is not int or not 0 <= index < registration["typesCount"]:
            raise ValueError("reference layout: declared type index outside selected table")
        pointer = self.image.pe.u64_at_va(int(registration["types"], 16) + index * 8)
        if not pointer: raise ValueError("reference layout: missing declared native type")
        return pointer

    def type_name(self, index: int) -> str:
        return runtime_type_name(self.image.pe, self.image.metadata, self.type_pointer(index))

    def parent(self, name: str) -> str:
        td = self.index.types.get(name)
        if td is None and "<" in name and name.endswith(">"):
            td = self.index.types.get(name.split("<", 1)[0])
            if td is not None and td.generic_container_index < 0: td = None
        parent = self.type_name(td.parent_index) if td is not None and td.parent_index >= 0 else ""
        return "" if "VAR[" in parent else parent

    def is_enum(self, name: str) -> bool:
        return self.parent(name) == "System.Enum"

    def is_value_type(self, name: str) -> bool:
        return self.parent(name) in {"System.Enum", "System.ValueType"}

    def field_attributes(self, index: int) -> int:
        return int.from_bytes(self.image.pe.bytes_at_va(self.type_pointer(index)+8, 2), "little")

    def field(self, qualified: str) -> tuple[str, str, int]:
        owner, separator, name = qualified.partition("::")
        td = self.index.types.get(owner)
        if not separator or td is None or td.generic_container_index >= 0:
            raise ValueError(f"reference layout: field requires a named nongeneric owner: {qualified}")
        fields = [f for f in self.image.metadata.fields_for(td) if self.image.metadata.string(f.name_index) == name]
        if len(fields) != 1 or self.field_attributes(fields[0].type_index) & 0x10:
            raise ValueError(f"reference layout: missing, duplicate or static field: {qualified}")
        offsets = runtime_type_field_offsets(self.image.metadata, self.image.pe, self.image.registration, td.index)
        return owner, self.type_name(fields[0].type_index), offsets[name]


def closed_generic_reference_extent(selected, type_index):
    image=selected.image;pe=image.pe;metadata=image.metadata
    pointer=selected.type_pointer(type_index);raw=pe.bytes_at_va(pointer,16)
    if len(raw)!=16 or raw[10]!=0x15 or raw[11]!=0 or int.from_bytes(raw[8:10],'little')&0x10:
        raise ValueError('closed generic reference extent: undecorated reference instantiation required')
    generic=int.from_bytes(raw[:8],'little');carrier=pe.bytes_at_va(generic,16)
    if len(carrier)!=16:raise ValueError('closed generic reference extent: incomplete generic carrier')
    definition_pointer,inst_pointer=struct.unpack('<QQ',carrier)
    definition_raw=pe.bytes_at_va(definition_pointer,16)
    if len(definition_raw)!=16 or definition_raw[10]!=0x12 or definition_raw[11]!=0:
        raise ValueError('closed generic reference extent: reference class definition required')
    definition_index=int.from_bytes(definition_raw[:8],'little')
    if not 0<=definition_index<len(metadata.types):raise ValueError('closed generic reference extent: definition index outside metadata')
    definition=metadata.types[definition_index];definition_name=metadata.type_full_name(definition)
    if definition.generic_container_index<0 or selected.is_value_type(definition_name):
        raise ValueError('closed generic reference extent: selected generic reference definition required')
    section=metadata.sections['genericContainers'];at=section.offset+definition.generic_container_index*16
    if not section.offset<=at<=section.offset+section.size-16:
        raise ValueError('closed generic reference extent: generic container outside metadata')
    owner,count,is_method,parameter=struct.unpack_from('<iiii',metadata.buf,at)
    inst=pe.bytes_at_va(inst_pointer,16)
    if len(inst)!=16:raise ValueError('closed generic reference extent: incomplete argument carrier')
    argc,argv=struct.unpack('<QQ',inst)
    if owner!=definition_index or is_method!=0 or not 1<=count<=64 or parameter<0 or argc!=count or not argv:
        raise ValueError('closed generic reference extent: generic owner or arity differs')
    argument_pointers=[pe.u64_at_va(argv+n*8) for n in range(count)]
    argument_names=[runtime_type_name(pe,metadata,p) for p in argument_pointers]
    markers=('<generic-','<recursive-','<type-','<runtime-')
    if any(not p or not name or name.startswith('<') or any(marker in name for marker in markers)
           or 'VAR[' in name or 'MVAR[' in name for p,name in zip(argument_pointers,argument_names)):
        raise ValueError('closed generic reference extent: unresolved argument')
    expected=definition_name+'<'+','.join(argument_names)+'>'
    if selected.type_name(type_index)!=expected:
        raise ValueError('closed generic reference extent: declared closed identity differs')
    return {'bytes':8,'type':expected,'definitionTypeIndex':definition_index,
            'declaredTypeRecordHex':raw.hex().upper(),'definitionTypeRecordHex':definition_raw.hex().upper(),
            'argumentTypes':argument_names,'evidence':'selected generic reference representation; argument storage does not determine pointer width'}


def check_closed_reference_layout(index: Any, body: Any, spec: dict[str, Any]) -> str | None:
    """Prove selected storage layout without claiming any field read or value."""
    try:
        if (not isinstance(spec, dict) or set(spec) not in ({"witnessType", "dataField"},{"witnessType", "dataField","concreteInstanceSuffix"})
                or any(not isinstance(spec[key], str) or not spec[key] for key in ("witnessType","dataField"))
                or "concreteInstanceSuffix" in spec and spec["concreteInstanceSuffix"] is not True):
            return "closed-reference-layout: named witness and generic field required"
        witness = spec["witnessType"]
        if body.symbol.rpartition(".")[0] != witness or index.names_of(body.pointer) != [body.symbol]:
            return "closed-reference-layout: unique named witness body ownership is missing"
        owner, separator, field = spec["dataField"].partition("::")
        if not separator or not owner or not field:
            return "closed-reference-layout: qualified generic field required"
        single_reference_generic_field(NativeReferenceContext(index.image, index=index),
            owner=owner, field=field, witness=witness,concrete_instance_suffix=spec.get("concreteInstanceSuffix",False))
    except (ValueError, KeyError, IndexError) as exc:
        return f"closed-reference-layout: selected layout proof failed: {exc}"
    return None


def single_reference_generic_field(selected: Any, *, owner: str, field: str,
                                   witness: str, concrete_instance_suffix: bool=False) -> dict[str, Any]:
    label = f"closed reference layout: {owner}::{field} witnessed by {witness}"

    def fail(reason: str) -> None:
        raise ValueError(f"{label}: {reason}")

    if type(concrete_instance_suffix) is not bool:
        fail("instance suffix selection must be an explicit Boolean")

    definition, separator, arguments = owner.partition("<")
    argument = arguments[:-1] if arguments.endswith(">") else ""
    if not separator or not definition.endswith("`1") or not argument or any(c in argument for c in "<>,[]"):
        fail("requires one closed named reference argument")
    types = selected.index.types
    td, concrete, arg_td = types.get(definition), types.get(witness), types.get(argument)
    if (td is None or concrete is None or arg_td is None or selected.is_value_type(argument)
            or arg_td.generic_container_index >= 0 or arg_td.flags & 0x20):
        fail("argument and concrete witness must be named reference classes")
    if (selected.is_value_type(owner) or selected.is_value_type(witness)
            or td.flags & 0x18 == 0x10 or concrete.flags & 0x18 == 0x10
            or not td.bitfield & 0x800 or not concrete.bitfield & 0x800
            or td.field_count != 1
            or concrete.generic_container_index >= 0 or td.generic_container_index < 0
            or selected.parent(witness) != owner):
        fail("requires an immediate concrete subclass and a default-sized sole-field generic base")
    metadata = selected.image.metadata
    concrete_fields = list(metadata.fields_for(concrete))
    if len(concrete_fields) != concrete.field_count:
        fail("concrete declared-field count differs from selected metadata")
    static_fields = [];instance_fields=[]
    for member in concrete_fields:
        attributes = selected.field_attributes(member.type_index)
        if not attributes & 0x10:
            if not concrete_instance_suffix:fail("concrete witness declares an instance field")
            instance_fields.append(member);continue
        static_fields.append({"field": metadata.string(member.name_index),
            "type": selected.type_name(member.type_index), "attributes": attributes})
    section = metadata.sections["genericContainers"]
    offset = section.offset + td.generic_container_index * 16
    if not section.offset <= offset <= section.offset + section.size - 16:
        fail("generic container outside selected metadata")
    generic_owner, count, is_method, parameter = struct.unpack_from("<iiii", metadata.buf, offset)
    if (generic_owner, count, is_method) != (td.index, 1, 0) or parameter < 0:
        fail("generic container identity or arity drift")
    fields = list(metadata.fields_for(td))
    if (len(fields) != 1 or metadata.string(fields[0].name_index) != field
            or selected.type_name(fields[0].type_index) != f"VAR[{parameter}]"
            or selected.field_attributes(fields[0].type_index) & 0x10):
        fail("sole declared instance field must be the selected type parameter")
    base = selected.parent(owner)
    base_td = types.get(base)
    if (base_td is None or base_td.generic_container_index >= 0 or selected.is_value_type(base)
            or base_td.flags & 0x18 == 0x10 or not base_td.bitfield & 0x800):
        fail("requires a default-sized non-generic reference base")

    def size_row(name: str, definition: Any) -> tuple[int, dict[str, Any]]:
        registration, pe = selected.image.registration, selected.image.pe
        if not 0 <= definition.index < int(registration["typeDefinitionsSizesCount"]):
            fail(f"type size index outside selected table: {name}")
        table = int(registration["typeDefinitionsSizes"], 16)
        pointer = pe.u64_at_va(table + definition.index * 8)
        if not pointer:
            fail(f"missing selected type size: {name}")
        raw = pe.bytes_at_va(pointer, 16)
        if len(raw) != 16:
            fail(f"incomplete selected type size: {name}")
        size = int.from_bytes(raw[:4], "little")
        if not 16 <= size <= 4096 or size % 8:
            fail(f"invalid selected reference instance size: {name}:{size}")
        return size, {"type": name, "typeDefinitionIndex": definition.index,
                      "sizeRowAddress": f"0x{pointer:x}", "sizeRowBytes": raw.hex(), "instanceBytes": size}

    base_size, base_proof = size_row(base, base_td)
    witness_size, witness_proof = size_row(witness, concrete)
    suffix=[]
    if concrete_instance_suffix:
        if not instance_fields:fail("explicit instance suffix requires selected declared instance fields")
        primitive_widths={"bool":1,"byte":1,"sbyte":1,"short":2,"ushort":2,"int":4,"uint":4,"long":8,"ulong":8,"float":4,"double":8}
        for member in instance_fields:
            name=metadata.string(member.name_index)
            qualified=witness+"::"+name
            member_owner,member_type,member_offset=selected.field(qualified)
            width=primitive_widths.get(member_type)
            if width is None and selected.is_enum(member_type):
                _,underlying,_=selected.field(member_type+"::value__");width=primitive_widths.get(underlying)
            if width is None and (member_type in {"object","string"} or member_type in types and not selected.is_value_type(member_type)):
                width=8
            reference_proof = None
            if width is None and '<' in member_type:
                try:
                    reference_proof = closed_generic_reference_extent(selected, member.type_index)
                except ValueError as exc:
                    fail(f"unproved concrete suffix field extent: {qualified}: {exc}")
                width = reference_proof['bytes']
            if member_owner!=witness or width is None or type(member_offset) is not int:
                fail(f"unproved concrete suffix field extent: {qualified}")
            suffix.append({"field":qualified,"type":member_type,"offset":member_offset,"bytes":width})
            if reference_proof is not None:
                suffix[-1]["referenceRepresentation"] = reference_proof
        end=base_size+8
        for item in sorted(suffix,key=lambda item:item["offset"]):
            if item["offset"]!=end or item["offset"]+item["bytes"]>witness_size:
                fail("concrete suffix has a gap, overlap or wrong one-reference prefix")
            end+=item["bytes"]
        if end!=witness_size:fail("concrete suffix has trailing padding or unproved extent")
    elif witness_size != base_size + 8:
        fail("concrete instance size does not add exactly one reference")
    extents = []
    current, seen = base, set()
    while current and current != "object" and current != "System.Object":
        if current in seen or len(seen) >= 64:
            fail("base ancestry cycle or bound exceeded")
        seen.add(current)
        current_td = types.get(current)
        if current_td is None or current_td.generic_container_index >= 0:
            fail("base ancestry contains an unresolved generic type")
        for member in metadata.fields_for(current_td):
            if selected.field_attributes(member.type_index) & 0x10:
                continue
            name = metadata.string(member.name_index)
            _, member_type, member_offset = selected.field(f"{current}::{name}")
            widths = {"bool": 1, "byte": 1, "sbyte": 1, "short": 2, "ushort": 2,
                      "int": 4, "uint": 4, "long": 8, "ulong": 8, "float": 4, "double": 8}
            width = widths.get(member_type)
            if width is None and selected.is_enum(member_type):
                _, underlying, _ = selected.field(f"{member_type}::value__")
                width = widths.get(underlying)
            if width is None and (member_type in {"object", "string"}
                    or member_type in types and not selected.is_value_type(member_type)):
                width = 8
            if width is None or not 16 <= member_offset < member_offset + width <= base_size:
                fail(f"unproved base field extent: {current}::{name}")
            extents.append({"field": f"{current}::{name}", "type": member_type,
                            "offset": member_offset, "bytes": width})
        current = selected.parent(current)
    if max((item["offset"] + item["bytes"] for item in extents), default=16) != base_size:
        fail("non-generic base has trailing padding or unproved extent")
    return {"definition": definition, "closedType": owner, "field": field,
            "fieldType": argument, "fieldOffset": base_size, "fieldBytes": 8,
            "concreteWitness": witness_proof, "concreteStaticFields": static_fields,"concreteInstanceSuffix":suffix,
            "nonGenericBase": base_proof, "baseFieldExtents": extents,
            "evidence": "selected closed parent identity, sole instance VAR field, non-generic base without trailing padding and exactly one-reference prefix, witnessed by an instance-fieldless concrete subclass or an explicitly proved complete concrete field suffix",
            "runtimeTypeObserved": False, "fieldValueObserved": False}
