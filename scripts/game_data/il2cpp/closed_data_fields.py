"""Narrow normal-path field flow from a proved closed generic data reference.

A concrete witness supplies the sole-reference layout, with either no declared
instance fields or an explicitly checked complete suffix. The incoming
instance must own the body, and its saved aliases must reach that exact data
slot before a named nongeneric field is read. Unknown instructions and partial
pointer writes erase provenance. This proves compiled flow, not live values.
"""
from __future__ import annotations
import re
from typing import Any
from .reference_layouts import (NativeReferenceContext, single_reference_generic_field,
                               closed_generic_reference_extent)
from .cmp_memory_reads import reads_cmp_memory_field


def normal_rows(body):
    """Follow one compiled fallthrough path, requiring exact local direct jumps.

    Conditional branches keep the fallthrough choice. Every followed jump is
    decoded from its complete instruction bytes and lands on an instruction
    boundary in the same selected body. Backward, external and indirect jumps
    terminate this selected path. This does not establish branch execution.
    """
    rows = body.rows
    addresses = []
    try:
        for row in rows:
            addresses.append(int(row['va'], 16))
        if len(set(addresses)) != len(addresses) or addresses != sorted(addresses): return
    except (KeyError, TypeError, ValueError): return
    by_address = {at: n for n, at in enumerate(addresses)}
    cursor = 0
    while cursor < len(rows):
        row = rows[cursor]; text = str(row.get('text') or '')
        yield row
        if text.startswith('ret'): return
        if text.startswith('jmp '):
            try:
                at = addresses[cursor]; raw = bytes.fromhex(row['bytes'])
                if len(raw) == 2 and raw[0] == 0xeb:
                    target = at + 2 + int.from_bytes(raw[1:], 'little', signed=True)
                elif len(raw) == 5 and raw[0] == 0xe9:
                    target = at + 5 + int.from_bytes(raw[1:], 'little', signed=True)
                else: return
                if (text != f'jmp 0x{target:x}' or target <= at
                        or not body.pointer <= target < body.pointer + body.size or target not in by_address): return
                cursor = by_address[target]
            except (KeyError, TypeError, ValueError): return
        else:
            cursor += 1


def check_closed_data_field(index: Any, body: Any, spec: dict[str, Any], *, forward: bool,
                            byte_argument: bool = False) -> str | None:
    from . import body_claims as claims
    try:
        witness = spec["witnessType"]
        if (body.symbol.rpartition(".")[0] != witness or index.names_of(body.pointer) != [body.symbol]
                or index.parameter_location(body.pointer, body.symbol, "this") != ("register", "rcx")):
            return "closed-data-field: unique incoming instance body ownership is missing"
        context = NativeReferenceContext(index.image, index=index)
        declarations = index.names_by_pointer.get(body.pointer) or []
        if len(declarations) != 1 or type(declarations[0].get("methodIndex")) is not int:
            return "closed-data-field: unique selected caller declaration is missing"
        caller = index.metadata.methods[declarations[0]["methodIndex"]]
        caller_return = index.pe.bytes_at_va(context.type_pointer(caller.return_type), 16)
        if caller.flags & 0x10 or len(caller_return) != 16 or caller_return[11] & 0x7f:
            return "closed-data-field: incoming instance ABI is not established"
        direct_return = caller_return[10] in {1,2,3,4,5,6,7,8,9,10,11,12,13,14,0x12,0x18,0x19,0x1d}
        if caller_return[10] == 0x11:
            return_type = context.type_name(caller.return_type)
            if context.is_enum(return_type):
                _, underlying, _ = context.field(return_type+"::value__")
                direct_return = underlying in {"int", "uint"}
        if not direct_return:
            return "closed-data-field: caller return could introduce an unproved hidden buffer"
        owner, separator, data_name = spec["dataField"].partition("::")
        if not separator: return "closed-data-field: qualified generic data field required"
        layout = single_reference_generic_field(context, owner=owner, field=data_name, witness=witness,
            concrete_instance_suffix=spec.get("concreteInstanceSuffix",False))
        value_owner, value_type, value_offset = context.field(spec["valueField"])
        if value_owner != layout["fieldType"]:
            return "closed-data-field: named value owner differs from the witnessed closed argument"
        reference = value_type in {"object", "string"} or value_type in index.types and not context.is_value_type(value_type)
        if 'closedGenericReferenceField' in spec:
            if spec['closedGenericReferenceField'] is not True:
                return 'closed-data-field: closed generic reference field requires explicit true selection'
            declarations = [f for f in index.metadata.fields_for(index.types[value_owner])
                            if index.metadata.string(f.name_index) == spec['valueField'].partition('::')[2]]
            if len(declarations) != 1:
                return 'closed-data-field: unique declared generic reference field is missing'
            proof = closed_generic_reference_extent(context, declarations[0].type_index)
            if proof['bytes'] != 8 or proof['type'] != value_type:
                return 'closed-data-field: closed generic reference extent differs'
            reference = True
        width = (64 if reference else 32 if value_type in {"int", "uint", "float"}
                 else 8 if value_type in {"bool", "byte"} else None)
        if context.is_enum(value_type):
            _, underlying, _ = context.field(value_type+"::value__")
            width = 32 if underlying in {"int", "uint"} else None
        if byte_argument and (not forward or width != 8):
            return "closed-data-field: byte argument mode requires a complete bool/byte field"
        if width is None or forward and not (reference or byte_argument):
            return "closed-data-field: only a full reference or named 32-bit/byte stored read is supported"
        data_offset = layout["fieldOffset"]
    except (ValueError, KeyError, IndexError, claims.ClaimError) as exc:
        return f"closed-data-field: layout/signature proof failed: {exc}"
    follow_jumps = spec.get('followNormalForwardJumps', False)
    if type(follow_jumps) is not bool:
        return 'closed-data-field: forward jump selection must be an explicit Boolean'
    def check_rows(selected_rows, *, local_edges=False):
        refs = {"rcx": "this"}; values: set[str] = set()
        volatile = {"rax", "rcx", "rdx", "r8", "r9", "r10", "r11"}
        for row in selected_rows:
            text = str(row.get("text") or "")
            if text.startswith("db"):
                refs.clear(); values.clear(); continue
            if not forward and any(origin == "data" and reads_cmp_memory_field(row,
                    base=register, offset=value_offset, width=width) for register, origin in refs.items()):
                return None
            if forward and re.fullmatch(r"call 0x[0-9a-f]+", text):
                pointer = int(text[7:], 16)
                if spec["call"] in index.names_of(pointer):
                    try:
                        kind, register = index.parameter_location(pointer, spec["call"], spec["parameter"])
                        # Reference forwarding excludes aggregate return ABI.
                        # Byte mode separately admits one instance bool/byte
                        # parameter with a void/bool return and no generic owner.
                        signatures = []
                        for named in index.names_by_pointer.get(pointer, []):
                            if f"{named.get('type')}.{named.get('method')}" != spec["call"]: continue
                            method = index.metadata.methods[named["methodIndex"]]
                            parameters = [p for p in index.metadata.parameters_for(method)
                                          if index.metadata.string(p.name_index) == spec["parameter"]]
                            if len(parameters) != 1: continue
                            raw = index.pe.bytes_at_va(context.type_pointer(parameters[0].type_index), 16)
                            result = index.pe.bytes_at_va(context.type_pointer(method.return_type), 16)
                            if byte_argument:
                                owner = index.types.get(str(named.get("type")))
                                signatures.append(len(raw) == len(result) == 16
                                    and owner is not None and not context.is_value_type(str(named.get("type")))
                                    and owner.generic_container_index < 0 and method.generic_container_index < 0
                                    and method.declaring_type == owner.index and not method.flags & 0x10
                                    and len(list(index.metadata.parameters_for(method))) == 1
                                    and raw[10] in {2,5} and not raw[11] & 0x7f
                                    and context.type_name(parameters[0].type_index) == value_type
                                    and result[10] in {1,2} and not result[11] & 0x7f)
                            else:
                                signatures.append(len(raw) == len(result) == 16 and raw[10] in {0x12,0x0e} and not raw[11]&0x7f
                                    and context.type_name(parameters[0].type_index) == value_type
                                    and not result[11] & 0x7f and result[10] in {1,2,8,9,12,13,14,0x12})
                        if kind == "register" and str(register) in values and signatures and all(signatures):
                            return None
                    except (ValueError, KeyError, IndexError, claims.ClaimError):
                        pass
            moved = re.fullmatch(r"mov (\w+), (\w+)", text)
            load = re.fullmatch(r"(mov|movzx) (\w+), \[(\w+)\+0x([0-9a-f]+)\]", text)
            established = False
            if moved:
                destination, source = moved.groups()
                root = claims._REGISTER_ROOT.get(destination)
                origin = refs.get(source) if destination == root and source == claims._REGISTER_ROOT.get(source) else None
                is_value = reference and source in values and destination == root
                if root:
                    refs.pop(root, None); values.discard(root)
                    if origin: refs[root] = origin
                    if is_value: values.add(root)
                    established = True
            elif load:
                operation, destination, source, offset_text = load.groups(); offset = int(offset_text, 16)
                root = claims._REGISTER_ROOT.get(destination); origin = refs.get(source)
                if root:
                    refs.pop(root, None); values.discard(root)
                    if origin == "this" and offset == data_offset and destination == root and operation == "mov":
                        refs[root] = "data"
                    elif origin == "data" and offset == value_offset:
                        full = destination == root if width == 64 else destination in {
                            "eax","ebx","ecx","edx","esi","edi","ebp",*(f"r{n}d" for n in range(8,16))}
                        if width == 8:
                            # Authenticate byte MOV/MOVZX separately: their text
                            # alone does not establish the memory operand's width.
                            raw = bytes.fromhex(str(row.get("bytes") or ""))
                            if raw and 0x40 <= raw[0] <= 0x4f:
                                rex, raw = raw[0], raw[1:]
                            else:
                                rex = 0
                            registers = ("rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
                                         *(f"r{n}" for n in range(8, 16)))
                            opcode_bytes = 2 if operation == "movzx" else 1
                            modrm = raw[opcode_bytes] if len(raw) > opcode_bytes else 0
                            mode = modrm >> 6
                            register_code = ((modrm >> 3) & 7) + (8 if rex & 4 else 0)
                            byte_registers = ("al", "cl", "dl", "bl",
                                              *(('spl','bpl','sil','dil') if rex else ('ah','ch','dh','bh')),
                                              *(f"r{n}b" for n in range(8, 16)))
                            complete_byte = (operation == "mov" and raw[:1] == b"\x8a"
                                             and destination == byte_registers[register_code])
                            extended_byte = full and operation == "movzx" and raw[:2] == b"\x0f\xb6"
                            full = ((complete_byte or extended_byte) and not rex & 8
                                    and (mode, len(raw)) in {(1, opcode_bytes + 2), (2, opcode_bytes + 5)}
                                    and modrm & 7 != 4
                                    and registers[(modrm & 7) + (8 if rex & 1 else 0)] == source
                                    and registers[register_code] == root
                                    and int.from_bytes(raw[opcode_bytes + 1:], "little", signed=True) == value_offset)
                        else:
                            full = full and operation == "mov"
                        if full:
                            if not forward: return None
                            values.add(root)
                    established = True
            if not established:
                for register in set(refs) | values:
                    if claims._writes_register(row, register):
                        refs.pop(register, None); values.discard(register)
            if text.startswith("call "):
                for register in volatile: refs.pop(register, None)
                values -= volatile
            if text.startswith("ret") or not local_edges and not follow_jumps and text.startswith("jmp "):
                refs.clear(); values.clear()
        action = f"reaches {spec.get('call')}.{spec.get('parameter')}" if forward else "is read"
        return f"closed-data-field: {spec['valueField']} never {action} through the proved incoming-instance data slot"

    local = spec.get('onAnyLocalCompiledPath', False)
    if type(local) is not bool:
        return 'closed-data-field: local compiled path selection must be an explicit Boolean'
    if local:
        from .compiled_paths import CompiledLocalPaths, diagnostic
        paths = CompiledLocalPaths(body)
        for program in paths:
            reason = check_rows(program, local_edges=True)
            if reason is None:
                return None
        action = f"reaches {spec.get('call')}.{spec.get('parameter')}" if forward else 'is read'
        return (f"closed-data-field: {spec['valueField']} never {action} on a checked local compiled path; "
                + diagnostic(paths.audit))
    return check_rows(normal_rows(body) if follow_jumps else body.rows)
