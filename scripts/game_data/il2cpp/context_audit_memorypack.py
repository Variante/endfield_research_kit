"""MemoryPack reader and BuffData consumer validations.

Moved verbatim out of ``context_audit``; that module owns the audit
contract and the report it assembles.

Each function returns pinned native windows plus a ``boundary`` string that is
the maintained statement of what the window proves. The wire-side rules they
establish, all ``direct`` conditional control flow of the selected build:

* ``wrapper_consumer`` / ``nested_reader_context`` -- the generated wrapper
  reader takes a one-byte fast-path header (``FF`` null, else the member
  count) and forwards the same reader to a ``ReadPackable<List<...>>``
  carrier; the nested body follows relative slot zero through ReadPackable
  -> ReadValue -> GetFormatter -> that MVAR. Each edge joins one ordinal-zero
  parameter owned by the preceding method; they are distinct records, not
  interchangeable MVAR identities, and the concrete argument propagates only
  conditionally on context inflation;
* ``list_formatter_candidate`` -- the registered ``ListFormatter`` shares the
  list instantiation and supplies one static Deserialize candidate. Its fast
  path takes a signed four-byte count and compares it, unscaled, with the
  remaining length. Header -1 clears the output; below -1 reaches an error
  helper only on the new-output path, while the existing-output path clears
  its length and skips the nonpositive loop. Maintained parsers keep
  rejecting negative counts regardless. The four-byte element output slot is
  not a serialized width;
* ``list_element_dispatch`` -- the element dispatcher reloads the object's
  class and takes its target/companion pair; the non-specialized branch calls
  the target with object, reader, output and companion; incoming RCX is not
  a caller-selected slot;
* ``list_element_shared_context`` -- the comparison target joins a shared
  GameplayTag/Object adapter candidate; never replace the loaded companion's
  context with that candidate's Object argument;
* ``list_element_null_probe`` -- the helper peeks for ``FF`` and only on a
  match consumes one byte, returns true and clears the output; the byte
  consumer's own boolean is not forwarded, and a non-match does not advance
  the cursor directly (ensure may still replace the segment);
* ``list_element_value_flow`` / ``adapter_conversion_context`` -- the non-FF
  path dispatches the formatter with the reader and a writable object slot,
  then converts the object through ``IMemoryPackDeSerializeWrapper<T0>``
  (adapter ordinal zero, distinct from the formatter query's ordinal one;
  the adjacent ``GetValue`` MethodSpec's metadata slot is zero) without
  forwarding the reader. The four-byte output is a converted result width,
  not serialized consumption;
* ``element_provider_state_flow`` -- the provider takes a companion, not the
  reader: method-context slot zero yields a type-derived lookup key and slot
  one the returned-object check; carrier table, formatter cache, generation
  and writeback paths are state-dependent. The class helper's identity return
  is conditional on an initialized flag;
* ``reader_construction`` / ``reader_cursor_consumers`` /
  ``serializer_return_consumers`` / ``resource_carrier_consumers`` -- reader
  state is built from a 24-byte descriptor or a 16-byte pointer/length
  carrier with zero consumption; getters name consumed and remaining roles;
  cold advance and ensure can replace the segment, so a pointer delta is not
  a source offset. Every reviewed caller returns, discards or forwards the
  consumed count; none compares it with a length, so cursor state is never an
  EOF test;
* ``skill_resource_context`` -- exact ``Core.SkillData`` arguments join
  ResourceManager MethodSpecs (not the same-named nested AI type); Object
  MethodSpecs are shared-code candidates, not observed sharing.

None of these establishes live provider or formatter selection, cache
contents, a fixed element width, source consumption, or EOF, and none
eliminates a SkillData terminal candidate.

Pinned values.  Every build-locked value these validations check or report --
method rows, instruction windows and bodies, call edges, MethodSpec, type,
instantiation and definition indices, tokens and switch data -- lives in
``contracts/il2cpp_context_audit_native.json`` under ``pins``, one section per
report key (``selectedBuffUnionRoutes`` for :func:`buff_union_routes`), bound
as ``pins`` at the top of each function.  Type and method names in checks,
structure offsets and element-type tags stay here because a client update
does not change them.
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
from pathlib import Path
from scripts.game_data.il2cpp.context import ContextError, GenericInstantiationTable, method_parameter_owner, type_image_owners, match_image_modules, method_spec_usage_index, generic_type_carrier, select_rgctx_range, unresolved_usage_index, rip_qword_load_target
from scripts.game_data.il2cpp.context import named_top_level_type
from scripts.game_data.il2cpp.context import method_pointer_indices, generic_method_candidates
from scripts.game_data.il2cpp.context import type_parameter_owner, rgctx_range_entries
from scripts.game_data.il2cpp.context import method_spec_record, usage_method_spec, relative_branch_target, method_token_pointer
from scripts.game_data.il2cpp.context_audit_common import AUDIT_PINS, CONSUMER_WINDOWS, require, sha


def serializer_return_consumers(pe, *, source):
    """Selected exact post-call windows, not exhaustive caller/EOF analysis."""
    pins=AUDIT_PINS['selectedSerializerReturnConsumers']
    edges=[]
    for rva,target in pins['edges']:
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'rawHex':raw.hex().upper(),'targetRva':target})
    windows=[]
    for rva,expected in pins['postCallWindows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'edges':edges,'postCallWindows':windows,
            'level':'direct selected consumer dataflow',
            'objectReturnWrapper':{'rva':pins['objectReturnWrapperRva'],
                                   'boundary':'Copies entry RDX 16-byte input, supplies a zero-initialized output slot to the reader-owning entry, then overwrites RAX with that output slot and returns. The returned consumed count in EAX is discarded without comparison in this entire wrapper.'},
            'stateMachineCallsites':[
                {'rva':pins['consumedForwardCallsiteRva'],'boundary':'Sign-extends returned consumed EAX into R8 and forwards it with ECX=0x20, R9D=1, RDX=the source object to another dispatcher. This is use of consumption, not an EOF comparison; the dispatched operation and source identity remain unresolved.'},
                {'rva':pins['consumedDiscardCallsiteRva'],'boundary':'Loads the local output result into RSI and prepares cleanup, discarding returned consumed EAX. Buffer-fill counts and completion branches elsewhere in this owner do not themselves establish equality with this parser consumption.'}],
            'boundary':'No claim that these are all callers, that SkillData selects any of them, or that successful object return certifies EOF. Initial authenticated logical-file identity and the actual selected formatter remain missing.'}


def module_methods(pe, md, modules, image_owners, selections, *, source, expected_image='MemoryPack.dll'):
    """Join each selected definition through its own owner/image/token identity."""
    selected=[]
    pointer_tables={}
    for index,type_name,name,expected in selections:
        require(0<=index<len(md.methods),True,source,index)
        method=md.methods[index]
        require(0<=method.declaring_type<len(md.types),True,source,index)
        owner=md.types[method.declaring_type]
        require(md.type_full_name(owner),type_name,source,index)
        require(md.string(method.name_index),name,source,index)
        image_name=md.string(md.images[image_owners[method.declaring_type]].name_index)
        require(image_name,expected_image,source,index)
        module=modules[image_name]
        if module not in pointer_tables:
            count=pe.u32_at_va(module+8)
            require(count<=1_000_000,True,source,module+8)
            base=pe.u64_at_va(module+16)
            pointer_tables[module]=(base,pe.bytes_at_va(base,count*8))
        base,pointers=pointer_tables[module]
        row=method_token_pointer(method.token,pointers,source=source,offset=base)
        require(row['pointerVa'],0 if expected is None else pe.image_base+expected,source,row['slotVa'])
        selected.append(dict(row,methodIndex=index,declaringType=type_name,name=name,image=image_name,moduleVa=module))
    return selected


def reader_construction(pe, md, modules, image_owners, *, source):
    """Exact method-token identities plus independently reviewed native bodies."""
    pins=AUDIT_PINS['selectedReaderConstruction']
    selected=module_methods(pe,md,modules,image_owners,
        [(index,'MemoryPack.MemoryPackReader',name,rva) for index,name,rva in
         pins['readerMethods']],source=source)
    getters=[]
    for rva,hex_bytes in pins['getterLeaves']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        getters.append({'rva':rva,'rawHex':raw.hex().upper(),'rangeKind':'bounded explicit-return leaf; no pdata extent'})
    edges=[]
    for rva,target in pins['edges']:
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'rawHex':raw.hex().upper(),'targetRva':target})
    return {'methods':selected,'getterLeaves':getters,'edges':edges,
            'level':'exact module/token identity; direct conditional native construction',
            'spanConstructor':{'rva':pins['spanConstructorRva'],'inputWindowBytes':16,'stateWindowBytes':0x58,
                               'boundary':'RDX points to a 16-byte carrier copied to reader+0x20. Its signed dword+8 is stored at reader+0x30 and sign-extended into +0x18; +0x38 and both +0x40/+0x44 counters are cleared. Nonzero carrier length selects its pointer for +0x50; zero selects null. The first 24 state bytes come from static storage. Input validity and allocation bounds are not checked by this constructor.'},
            'sequenceConstructor':{'rva':pins['sequenceConstructorRva'],'inputWindowBytes':24,
                                   'boundary':'RDX points to a 24-byte endpoint descriptor. Equal endpoints use the static descriptor in reader+0; otherwise the input descriptor is copied. First-segment and length helpers still receive the original input, supplying +0x20/+0x30, total +0x18 and cursor +0x50. Both counters are cleared. Static descriptor contents and multi-segment ABI remain unresolved.'},
            'accessors':{'consumedOffset':0x44,'totalLengthOffset':0x18,
                         'boundary':'get_Consumed returns the dword at +0x44; get_Remaining returns qword+0x18 minus sign-extended dword+0x44. This independently names these state roles, not serialized field meanings.'},
            'caller':{'rva':pins['callerRva'],'readerStackOffset':0x50,'returnedCounterStackOffset':0x94,
                      'boundary':'Copies the entry RDX 16-byte input, initializes a 0x58-byte stack reader, invokes the span constructor, dispatches with that reader, and returns its +0x44 counter after cleanup. The sequence caller similarly copies a constructed 0x58-byte state and returns +0x44. Neither reviewed owner compares that counter against original length. Caller selection for SkillData, initial file identity, and outer EOF enforcement remain unknown.'},
            'boundary':'A conditional source-length/consumed ABI exists, but no authenticated VFS allocation or observed SkillData invocation joins it. Do not prune terminal candidates.'}


def reader_cursor_consumers(pe, *, source):
    """Bound reviewed edges; caller authenticates complete selected native build."""
    pins=AUDIT_PINS['selectedReaderCursorConsumers']
    edges=[]
    for rva,opcode,target in pins['edges']:
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        actual=relative_branch_target(raw,pe.image_base+rva,source=source)
        require(raw[0],opcode,source,rva)
        require(actual,pe.image_base+target,source,rva)
        edges.append({'instructionRva':rva,'instructionHex':raw.hex().upper(),'targetRva':target})
    # This leaf has no pdata row: certify only its two explicit return paths,
    # not a guessed function extent or the following aligned function.
    leaf=pe.bytes_at_va(pe.image_base+pins['pointerLeafRva'],13)
    require(leaf,bytes.fromhex(pins['pointerLeafHex']),source,pins['pointerLeafRva'])
    return {'edges':edges,'pointerLeaf':{'rva':pins['pointerLeafRva'],'rawHex':leaf.hex().upper(),
                                       'rangeKind':'bounded instruction window; no pdata extent'},
            'level':'direct conditional native reader state transitions',
            'advance':{'rva':pins['advanceRva'],'normalReturn':True,'localCounterResetOffset':0x40,
                       'accumulatedCounterOffset':0x44,'cursorReplacementOffset':0x50,
                       'boundary':'The only normal return sets AL=1, resets +0x40, adds the signed-extended request via a 32-bit addition at +0x44, and replaces +0x30/+0x50 from helper outputs. Caller false-return fallback is not a second normal path in this pinned body. Helpers may throw; counter overflow and runtime descriptor validity are not certified.'},
            'ensure':{'rva':pins['ensureRva'],'sourceDescriptorPrefixBytes':24,
                      'boundary':'Uses +0x18 minus signed-extended +0x44 as a requested-length guard, resets +0x40 after a delegated 24-byte descriptor transformation, and selects an existing or copied segment before replacing +0x30/+0x50. The cursor can change allocations; a pointer delta is not an absolute source offset. The descriptor transform/copy/type-context helpers are not fully closed.'},
            'descriptorLength':{'rva':pins['descriptorLengthRva'],'prefixBytes':24,
                                'boundary':'For equal endpoint objects at +0/+8, masks bit 31 from the +0x10/+0x14 words and returns end minus start. Unequal endpoints use type-context conversions and object +0x28 values; their ABI remains conditional, not a certified source length.'},
            'nestedRead':{'rva':pins['nestedReadRva'],'readerRegister':'R15',
                          'boundary':'Entry RCX is saved in R15 and passed to dispatch as R8; the local output is returned after formatter dispatch. This body is another provider/dispatch layer, not the list count or element consumer. Its cold cache paths, live MethodInfo and selected list formatter are unresolved.'},
            'boundary':'No authenticated logical-file allocation, initial descriptor, complete helper ABI, final cursor or EOF join. Keep both terminal candidates.'}


def buff_tag76_read_order(pe,md,reg,table,modules,image_owners,*,source):
    """Current anonymous tag-76 profile; no live list formatter or field names."""
    pins=AUDIT_PINS['selectedBuffTag76ReadOrder']
    methods=module_methods(pe,md,modules,image_owners,
        pins['methods'],
        source=source,expected_image='MemoryPack.Beyond.dll')
    windows=[]
    for at,expected in pins['windows']:
        raw=bytes.fromhex(expected);require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    calls=[]
    for at,target in pins['orderedCalls']:
        raw=pe.bytes_at_va(pe.image_base+at,5);require(raw[:1],b'\xe8',source,at)
        require(relative_branch_target(raw,pe.image_base+at,source=source),pe.image_base+target,source,at)
        calls.append({'rva':at,'targetRva':target})
    at=pe.image_base+pins['nestedUsageLoadRva']
    cell=rip_qword_load_target(pe.bytes_at_va(at,7),at,source=source)
    require(cell,pe.image_base+pins['nestedUsageCellRva'],source,at)
    usage=pe.bytes_at_va(cell,8)
    require(method_spec_usage_index(usage,reg['methodSpecsCount'],source=source,offset=cell),pins['nestedMethodSpecIndex'],source,cell)
    va=int(reg['methodSpecs'],16)+pins['nestedMethodSpecIndex']*12;raw=pe.bytes_at_va(va,12)
    require(method_spec_record(raw,len(md.methods),reg['genericInstsCount'],source=source,offset=va),tuple(pins['nestedMethodSpecRecord']),source,va)
    instance=table.resolve(pins['nestedMethodSpecRecord'][2])
    require(len(instance.arguments),1,source)
    arg=instance.arguments[0];tr=bytes.fromhex(arg.raw_type_record_hex)
    require(tr,bytes.fromhex(pins['listTypeRecordHex']),source)
    cp=struct.unpack_from('<Q',tr)[0];cr=pe.bytes_at_va(cp,32)
    require(len(cr),32,source,cp)
    bp=struct.unpack_from('<Q',cr)[0]
    require(bp!=0,True,source,cp)
    carrier=generic_type_carrier(tr,cr,pe.bytes_at_va(bp,16),type_pointer=arg.type_pointer_va,type_count=len(md.types),source=source)
    require(carrier['baseDefinitionIndex'],pins['listDefinitionIndex'],source,bp)
    require(md.type_full_name(md.types[pins['listDefinitionIndex']]),'System.Collections.Generic.List`1',source)
    nested=table.resolve_pointer(carrier['classInstantiationPointerVa'])
    require(nested.index,pins['elementInstantiation'],source)
    require([a.raw_type_record_hex for a in nested.arguments],pins['elementArgumentRawTypes'],source)
    require(md.type_full_name(md.types[pins['elementDefinitionIndex']]),'Beyond.Blackboard+BlackboardString',source)
    return {'methods':methods,'windows':windows,'orderedCalls':calls,
        'nestedUsageCellVa':cell,'nestedUsageRawHex':usage.hex().upper(),
        'nestedMethodSpecIndex':pins['nestedMethodSpecIndex'],'nestedMethodSpecRawHex':raw.hex().upper(),
        'methodInstantiation':instance.as_dict(),'listCarrier':carrier,'elementInstantiation':nested.as_dict(),
        'level':'direct conditional consumer order; exact static nested type identity',
        'boundary':'Tag 76 routes to the current wrapper in selectedBuffUnionRoutes. Its member-five path reads one nonzero-normalized byte and three DWORDs before ReadPackable with List<BlackboardString>. The independently joined element reader takes member three, length-prefixed bytes, one normalized byte, then length-prefixed bytes. The length helper reads a signed DWORD: -1 returns null, zero takes an empty path, and positive length is forwarded unchanged to the byte consumer, which advances source/counters by that length after its decoder call. Payload bytes remain anonymous: encoding/cache contents, complete decoder parity, negative values below -1, live list formatter, concrete source carrier and final cursor/EOF are not proven. The maintained finite list profile is structural-only; neither managed names nor output-slot widths establish serialized order or gameplay meaning.'}


def buff_action_read_order(pe,md,reg,table,modules,image_owners,*,source,contract_path):
    """Selected action profile under audit()'s explicit native hash gate."""
    path=Path(contract_path)
    contract=json.loads(path.read_bytes())
    require(contract['schemaVersion'],1,path)
    methods=module_methods(pe,md,modules,image_owners,contract['methods'],
        source=source,expected_image='MemoryPack.Beyond.dll')
    for group in contract.get('methodGroups',[]):
        methods.extend(module_methods(pe,md,modules,image_owners,group['methods'],
            source=source,expected_image=group['image']))
    for row in contract['codeWindows']+contract.get('dataWindows',[]):
        start,end=row['startRva'],row['endRva']
        require(0<=start<end,True,path,start)
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        require(hashlib.sha256(raw).hexdigest().upper(),row['sha256'],source,start)
    for row in contract['nestedContexts']:
        at=pe.image_base+row['instructionRva']
        ins=pe.bytes_at_va(at,7)
        require(ins,bytes.fromhex(row['instructionHex']),source,at)
        cell=rip_qword_load_target(ins,at,source=source)
        require(cell,row['cellVa'],source,at)
        usage=pe.bytes_at_va(cell,8)
        require(usage,bytes.fromhex(row['usageRawHex']),source,cell)
        index=method_spec_usage_index(usage,reg['methodSpecsCount'],source=source,offset=cell)
        require(index,row['methodSpecIndex'],source,cell)
        va=int(reg['methodSpecs'],16)+index*12
        spec=method_spec_record(pe.bytes_at_va(va,12),len(md.methods),reg['genericInstsCount'],source=source,offset=va)
        require(spec,tuple(row['methodSpec']),source,va)
        instance=table.resolve(spec[2])
        require([a.raw_type_record_hex for a in instance.arguments],[row['argumentRawHex']],source,va)
        argument=bytes.fromhex(row['argumentRawHex'])
        if row.get('generic') is not None:
            require(argument[10],0x15,source,va)
            cp=struct.unpack_from('<Q',argument)[0]
            cr=pe.bytes_at_va(cp,32)
            require(cr,bytes.fromhex(row['generic']['carrierRawHex']),source,cp)
            bp=struct.unpack_from('<Q',cr)[0];br=pe.bytes_at_va(bp,16)
            require(br,bytes.fromhex(row['generic']['baseRawHex']),source,bp)
            carrier=generic_type_carrier(argument,cr,br,type_pointer=instance.arguments[0].type_pointer_va,
                type_count=len(md.types),source=source)
            require(carrier['baseDefinitionIndex'],row['typeDefinition'],source,bp)
            nested=table.resolve_pointer(carrier['classInstantiationPointerVa'])
            require(nested.index,row['generic']['elementInstantiationIndex'],source,cp)
            require([a.raw_type_record_hex for a in nested.arguments],row['generic']['elementArguments'],source,cp)
        else:
            kind=row.get('typeKind',0x12)
            require(kind in (0x11,0x12),True,path,va)
            require(argument[10],kind,source,va)
            require(struct.unpack_from('<Q',argument)[0],row['typeDefinition'],source,va)
        require(0<=row['typeDefinition']<len(md.types),True,source,va)
        require(md.type_full_name(md.types[row['typeDefinition']]),row['typeName'],source,va)
    verified_source_read_calls = verify_contract_source_read_calls(
        pe, contract, source=source)
    return {'contractPath':str(path),'contractSha256':sha(path),'methods':methods,
        'codeWindows':contract['codeWindows'],'dataWindows':contract.get('dataWindows',[]),'nestedContexts':contract['nestedContexts'],
        'anonymousReadOrder':contract['anonymousReadOrder'],
        'verifiedSourceReadCallSites':verified_source_read_calls,
        'level':'direct selected consumer order; exact static nested type joins; structural-only parser profile',
        'boundary':contract['boundary']}


def verify_contract_source_read_calls(pe, contract, *, source):
    """Verify contract-pinned direct source-reader calls against the selected PE."""
    rows = contract.get('sourceReadCallSites', [])
    if not isinstance(rows, list):
        raise ContextError(source, 0, 'sourceReadCallSites array', rows)
    if not rows:
        return []
    read_orders = contract.get('anonymousReadOrder')
    if not isinstance(read_orders, dict) or len(read_orders) != 1:
        raise ContextError(source, 0, 'one root member read-order for source callsites',
                           read_orders)
    root_key, root_order = next(iter(read_orders.items()))
    if not isinstance(root_order, list) or not re.search(r'member\d+$', root_key):
        raise ContextError(source, 0, 'root member-count key and read-order array',
                           [root_key, root_order])
    verified = []
    seen = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ContextError(source, index, f'source read callsite {index} object', row)
        member_index = row.get('memberIndex')
        read_type = row.get('readType')
        instruction_rva = row.get('callInstructionRva')
        target_rva = row.get('targetRva')
        if (type(member_index) is not int or not 0 <= member_index < len(root_order) or
                type(instruction_rva) is not int or type(target_rva) is not int or
                not isinstance(read_type, str)):
            raise ContextError(source, index,
                               f'source read callsite {index} bounded member/RVA fields', row)
        require(root_order[member_index], read_type, source, instruction_rva)
        if instruction_rva in seen:
            raise ContextError(source, instruction_rva,
                               'unique source read call instruction RVA', instruction_rva)
        seen.add(instruction_rva)
        raw = pe.bytes_at_va(pe.image_base + instruction_rva, 5)
        require(raw[:1], b'\xE8', source, instruction_rva)
        target = relative_branch_target(raw, pe.image_base + instruction_rva, source=source)
        require(target, pe.image_base + target_rva, source, instruction_rva)
        verified.append({
            'rootReadOrderKey': root_key,
            'memberIndex': member_index,
            'readType': read_type,
            'callInstructionRva': instruction_rva,
            'instructionByteLength': len(raw),
            'rawHex': raw.hex().upper(),
            'targetRva': target - pe.image_base,
            'classification': 'exact-build direct E8 source-reader call',
        })
    return verified


def buff_sequence_read_order(pe,md,modules,image_owners,*,source):
    """Selected member-three sequence: count, indirect elements, two bytes."""
    pins=AUDIT_PINS['selectedBuffSequenceReadOrder']
    methods=module_methods(pe,md,modules,image_owners,
        pins['methods'],
        source=source,expected_image='MemoryPack.Beyond.dll')
    windows=[]
    for at,expected in pins['windows']:
        raw=bytes.fromhex(expected);require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    root_methods=[row for row in methods if row.get('methodIndex')==pins['methods'][0][0]]
    require(len(root_methods),1,source,pins['rootRva'])
    require(root_methods[0].get('pointerVa')-pe.image_base,pins['rootRva'],source,pins['rootRva'])
    root_windows=[(start,end,digest) for start,end,digest in CONSUMER_WINDOWS
                  if start==pins['rootRva']]
    # The root body's extent and hash are the reviewed consumerWindows row.
    require(len(root_windows),1,source,pins['rootRva'])
    root_start,root_end,root_sha=root_windows[0]
    return {'methods':methods,'windows':windows,
        'rootCodeWindow':{'startRva':root_start,'endRva':root_end,'sha256':root_sha},
        'level':'direct conditional selected-consumer structure',
        'boundary':'Header FF clears the output; header 3 takes a signed DWORD count after the one-byte header. The fast count path compares total-minus-consumed with the count, not count times an element width. Count -1 skips elements; zero uses a separate empty-array helper. Positive counts call a provider-selected class+0x190 target with the same reader, an eight-byte array output slot and class+0x198 companion. Output-slot width is not serialized element width. Then two bytes are consumed and nonzero-normalized, writing object offsets 0x19 then 0x18. No semantic field names, live provider identity, negative-count allocation behavior, nested extent, authenticated source cursor or EOF are promoted. Maintained framing rejects counts below -1 conservatively.'}


def buff_ifelse_read_order(pe,md,reg,table,modules,image_owners,*,source):
    """Selected reader's member-eight fast path; no live dispatch or EOF claim."""
    pins=AUDIT_PINS['selectedBuffIfElseReadOrder']
    methods=module_methods(pe,md,modules,image_owners,
        pins['methods'],
        source=source,expected_image='MemoryPack.Beyond.dll')
    windows=[]
    for at,expected in pins['windows']:
        raw=bytes.fromhex(expected);require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    calls=[]
    for at,target,width in pins['orderedCalls']:
        raw=pe.bytes_at_va(pe.image_base+at,5);require(raw[:1],b'\xe8',source,at)
        require(relative_branch_target(raw,pe.image_base+at,source=source),pe.image_base+target,source,at)
        calls.append({'rva':at,'targetRva':target,'fastSerializedWidth':width})
    operands=[]
    for at in pins['nestedOperandLoads']:
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+at,7),pe.image_base+at,source=source)
        require(cell,pe.image_base+pins['nestedUsageCellRva'],source,at)
        raw=pe.bytes_at_va(cell,8)
        require(method_spec_usage_index(raw,reg['methodSpecsCount'],source=source,offset=cell),pins['nestedMethodSpecIndex'],source,cell)
        operands.append({'rva':at,'cellVa':cell,'usageRawHex':raw.hex().upper()})
    va=int(reg['methodSpecs'],16)+pins['nestedMethodSpecIndex']*12;raw=pe.bytes_at_va(va,12)
    require(method_spec_record(raw,len(md.methods),reg['genericInstsCount'],source=source,offset=va),
            tuple(pins['nestedMethodSpecRecord']),source,va)
    instance=table.resolve(pins['nestedMethodSpecRecord'][2])
    require([a.raw_type_record_hex for a in instance.arguments],pins['nestedArgumentRawTypes'],source)
    require(pins['nestedTypeDefinition']<len(md.types),True,source)
    require(md.type_full_name(md.types[pins['nestedTypeDefinition']]),'Beyond.Gameplay.Core.SequenceActionData',source)
    root_windows=[(start,end,digest) for start,end,digest in CONSUMER_WINDOWS
                  if start==pins['rootRva']]
    # The root body's extent and hash are the reviewed consumerWindows row.
    require(len(root_windows),1,source,pins['rootRva'])
    root_start,root_end,root_sha=root_windows[0]
    return {'methods':methods,'windows':windows,'orderedCalls':calls,'nestedOperands':operands,
        'nestedMethodSpecIndex':pins['nestedMethodSpecIndex'],'nestedMethodSpecRawHex':raw.hex().upper(),
        'nestedTypeDefinition':pins['nestedTypeDefinition'],
        'nestedTypeName':'Beyond.Gameplay.Core.SequenceActionData',
        'nestedInstantiation':instance.as_dict(),
        'rootCodeWindow':{'startRva':root_start,'endRva':root_end,
                          'sha256':root_sha},
        'level':'direct selected-consumer order and fast widths; exact nested static type argument',
        'boundary':'The token/module-joined formatter forwards RDX reader and R8 output to the static reader. After a one-byte member header, its header-eight branch passes the same reader to byte/nonzero normalization, three raw DWORD reads, a second byte/nonzero normalization, then three nested helper calls. The fast scalar prefix is 14 bytes after the header; no signedness or gameplay names are assigned. All three nested callsites use one MethodSpec with SequenceActionData as its type argument, not a proven live formatter. Header FF, reused-object preprocessing, allocation/init, other header values and segment-replacement paths are outside this fast-path claim. No nested serialized widths, complete record extent, concrete source cursor or EOF are established.'}


def buff_ifelse_forwarding(pe,md,reg,table,*,source):
    """Exact thunk contexts and conditional reuse flow, not nested field grammar."""
    pins=AUDIT_PINS['selectedBuffIfElseForwarding']
    windows=[]
    for at,expected in pins['windows']:
        raw=bytes.fromhex(expected);require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    rows=[]
    for at,index,definition,target in pins['contexts']:
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+at,7),pe.image_base+at,source=source)
        usage=pe.bytes_at_va(cell,8)
        require(method_spec_usage_index(usage,reg['methodSpecsCount'],source=source,offset=cell),index,source,cell)
        va=int(reg['methodSpecs'],16)+index*12;raw=pe.bytes_at_va(va,12)
        require(method_spec_record(raw,len(md.methods),reg['genericInstsCount'],source=source,offset=va),
                (definition,-1,pins['methodInstantiation']),source,va)
        rows.append({'thunkRva':at,'tailTargetRva':target,'usageCellVa':cell,'usageRawHex':usage.hex().upper(),
                     'methodSpecIndex':index,'methodSpecRawHex':raw.hex().upper(),'methodDefinition':definition})
    instance=table.resolve(pins['methodInstantiation'])
    require([a.raw_type_record_hex for a in instance.arguments],pins['instantiationArgumentRawTypes'],source)
    return {'windows':windows,'contexts':rows,'methodInstantiation':instance.as_dict(),
        'level':'direct conditional register flow; exact static MethodSpec/type argument identity',
        'boundary':'Both C9 branch thunks replace the callsite companion before tail transfer. Their different MethodSpecs have the same single IfElse wrapper argument, independently identified in selectedBuffUnionRoutes. Creation preserves RCX reader and replaces RDX; its target body is not promoted here. Reuse preserves RCX reader and RDX output-slot address, replaces R8, ensures companion+0x38 and forwards its first slot through a tail thunk. The next body takes that companion first slot to the separately reviewed provider, then, only for a non-null result, passes selector 5, provider object, unchanged reader and output slot to 0x3F300. These bodies do not directly read serialized fields. Live provider/formatter and concrete nested consumer ABI remain unresolved; no record length, field order, authenticated source cursor or EOF follows.'}


def buff_union_routes(pe,md,reg,modules,image_owners,*,source):
    """Selected current tag routes, not a replacement serialization schema."""
    pins=AUDIT_PINS['selectedBuffUnionRoutes']
    methods=module_methods(pe,md,modules,image_owners,pins['methods'],source=source,expected_image='MemoryPack.Beyond.dll')
    windows=[]
    for at,expected in pins['windows']:
        raw=bytes.fromhex(expected);require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    table_va=pe.image_base+pins['switchTableRva'];raw=pe.bytes_at_va(table_va,pins['switchEntryCount']*4)
    require(len(raw),pins['switchEntryCount']*4,source,table_va)
    targets=[r[0] for r in struct.iter_unpack('<I',raw)]
    rows=[]
    for tag,target,index,definition,suffix,init in pins['rows']:
        require(targets[tag],target,source,table_va+tag*4)
        operands=[]
        for at,usage_tag in ((target,1),)+(((init,2),) if init is not None else ()):
            ins=pe.bytes_at_va(pe.image_base+at,7)
            require(len(ins),7,source,pe.image_base+at)
            cell=pe.image_base+at+7+struct.unpack_from('<i',ins,3)[0]
            usage=pe.bytes_at_va(cell,8)
            found=unresolved_usage_index(usage,reg['typesCount'],tag=usage_tag,source=source,offset=cell)
            require(found,index,source,cell)
            pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
            record=pe.bytes_at_va(pointer,16);require(len(record),16,source,pointer)
            require(record[10],0x12,source,pointer+10)
            require(struct.unpack_from('<Q',record)[0],definition,source,pointer)
            require(definition<len(md.types),True,source,pointer)
            namespace='View' if tag==pins['viewNamespaceTag'] else 'Core'
            expected_name='Beyond.MemoryPack.Beyond_Gameplay_'+namespace+'_'+suffix+'ForMemoryPack'
            require(md.type_full_name(md.types[definition]),expected_name,source,pointer)
            operands.append({'instructionRva':at,'cellVa':cell,'usageRawHex':usage.hex().upper(),
                'usageTag':usage_tag,'registeredTypeIndex':index,'typePointerVa':pointer,'typeRawHex':record.hex().upper()})
        if len(operands)==2:require(operands[0]['typePointerVa'],operands[1]['typePointerVa'],source)
        rows.append({'tag':tag,'switchTargetRva':target,'typeDefinition':definition,'wrapperName':expected_name,'operands':operands})
    return {'methods':methods,'windows':windows,'switchTableRva':pins['switchTableRva'],'switchEntryCount':pins['switchEntryCount'],
        'switchTableSha256':hashlib.sha256(raw).hexdigest().upper(),'rows':rows,
        'level':'direct current native tag-to-wrapper routing; exact metadata identity',
        'boundary':'The token/module-joined reader calls the bounded tag helper then uses its ushort output in an unsigned <=0x19F switch. The helper fast path consumes one byte and directly returns tags below 0xFA. FA consumes two more bytes as a little-endian ushort with no lower-value restriction; its short-input path calls an external refill helper, not an in-body zero-result failure. FB..FF return false with zero tag output, skipping the AL=1 instruction; the dispatcher false path clears its output. The maintained finite parser retains FF null and leaves FB..FE unsupported. Segment replacement is not certified. Selected table entries reach exact type-usage operands, including current union364 to SpeedupAction. For C9 and C0, separate cctor callsites pass those literal tags alongside a helper result derived from the same registered type pointer (usage kind two versus branch kind one). Current C9 describes the IfElse wrapper; C0 describes GainCost, contradicting the legacy Buff reader C0 name. Tag 40 describes CheckDamageTag. This is not a blanket tag renumbering rule or proof of nested fields, actual object allocation, formatter execution, record extent or EOF. Do not alias C9 to the legacy C0 parser or promote existing labels for current bytes without the concrete nested consumer ABI.'}


def element_provider_state_flow(pe,*,source):
    """Selected state-dependent lookup path; enclosing bodies are gated by audit."""
    pins=AUDIT_PINS['selectedElementProviderStateFlow']
    windows=[]
    for at,expected in pins['windows']:
        raw=bytes.fromhex(expected)
        require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    return {'windows':windows,'level':'direct conditional state/return flow',
        'boundary':'The short class helper returns its input unchanged when bit zero at +0x138 is set; otherwise it tail-jumps to initialization, whose return cannot be replaced by the fast-path identity. The provider receives a companion, not a serialized reader. Companion method-context slot zero feeds a helper and its result+0x20 becomes a lookup key. A successful first-table lookup uses a 24-byte row index to load a qword carrier from a separate vector; a miss may construct and insert a carrier. A null context element can instead forward a null carrier to the next helper. That helper consults static-carrier+0x18 state, compares a hash and invokes a separate equality target before returning a matched node+0x18 value. Miss branches include conditional helper calls, allocations and publication through another helper; they are not equivalent to selecting the static registered candidate. The common return comes from the writable local slot. The caller checks the returned object against companion method-context slot one before returning it or entering an error path. These branches establish state dependence, not cache contents, helper success, concrete formatter identity, execution, serialized bytes or EOF. Hash/equality algorithms, all initialization and generation helper implementations, and live mutation ordering remain unresolved.'}


def adapter_conversion_context(pe,md,reg,table,entries,*,source):
    """Static interface carrier and slot identity; not a live conversion target."""
    pins=AUDIT_PINS['selectedAdapterConversionContext']
    require(len(entries),13,source)
    entry=entries[8]
    require((entry['relativeIndex'],entry['kindRaw']),(8,2),source,entry['entryVa'])
    index=pe.u32_at_va(entry['dataPointerVa'])
    require(index,pins['interfaceTypeIndex'],source,entry['dataPointerVa'])
    require(index<reg['typesCount'],True,source,entry['dataPointerVa'])
    pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
    require(pointer!=0,True,source)
    raw=pe.bytes_at_va(pointer,16);require(len(raw),16,source,pointer)
    require(raw[10],0x15,source,pointer+10)
    cp=struct.unpack_from('<Q',raw)[0];require(cp!=0,True,source,pointer)
    cr=pe.bytes_at_va(cp,32);require(len(cr),32,source,cp)
    bp=struct.unpack_from('<Q',cr)[0];require(bp!=0,True,source,cp)
    carrier=generic_type_carrier(raw,cr,pe.bytes_at_va(bp,16),type_pointer=pointer,
        type_count=len(md.types),source=source)
    require(carrier['baseDefinitionIndex'],pins['interfaceDefinition'],source,bp)
    interface=md.types[pins['interfaceDefinition']]
    require(md.type_full_name(interface),'Beyond.MemoryPack.IMemoryPackDeSerializeWrapper`1',source)
    inst=table.resolve_pointer(carrier['classInstantiationPointerVa'])
    require(inst.index,pins['interfaceInstantiation'],source,inst.record_va)
    require(len(inst.arguments),1,source,inst.record_va)
    arg=bytes.fromhex(inst.arguments[0].raw_type_record_hex)
    require(arg,bytes.fromhex(pins['interfaceArgumentRawType']),source,inst.record_va)
    owner=type_parameter_owner(md.buf,struct.unpack_from('<Q',arg)[0],
        [t.generic_container_index for t in md.types],source=source)
    require((owner['typeIndex'],owner['ordinal']),(pins['adapterDefinition'],0),source,owner['containerOffset'])
    method_entry=entries[9]
    require((method_entry['relativeIndex'],method_entry['kindRaw']),(9,3),source,method_entry['entryVa'])
    spec=pe.u32_at_va(method_entry['dataPointerVa'])
    require(spec,pins['methodSpecIndex'],source,method_entry['dataPointerVa'])
    require(spec<reg['methodSpecsCount'],True,source,method_entry['dataPointerVa'])
    spec_va=int(reg['methodSpecs'],16)+spec*12
    spec_raw=pe.bytes_at_va(spec_va,12)
    definition,ci,mi=method_spec_record(spec_raw,len(md.methods),reg['genericInstsCount'],source=source,offset=spec_va)
    require((definition,ci,mi),(pins['methodDefinition'],inst.index,-1),source,spec_va)
    require((interface.method_start,interface.method_count),(definition,1),source)
    method=md.methods[definition]
    require((method.declaring_type,method.slot,method.parameter_count,method.token),
        (pins['interfaceDefinition'],0,0,pins['methodToken']),source)
    require(md.string(method.name_index),'GetValue',source)
    return {'carrier':carrier,'interfaceEntry':entry,'methodEntry':method_entry,
        'instantiation':inst.as_dict(),'argumentOwner':owner,'methodSpecIndex':spec,
        'methodSpecRawHex':spec_raw.hex().upper(),'methodDefinition':definition,'methodSlot':method.slot,
        'level':'exact static carrier/VAR/MethodSpec and metadata slot identity',
        'boundary':'Adapter relative class slot eight describes IMemoryPackDeSerializeWrapper with the reciprocal adapter ordinal-zero VAR. Slot nine describes GetValue with the identical class-instantiation index; its independently decoded metadata slot is zero and it has no explicit parameters. This distinguishes the conversion interface argument T0 from the existing slot-four formatter query for T1; it does not by itself decode the method return type or implementation. The native helper requests interface slot zero, but does not read RGCTX slot nine directly. The static relationship does not prove inflated interface pointers, a live implementation, method body semantics, serialized order, source consumption or EOF. Do not substitute the shared-code Object candidate for the original companion context.'}


def list_element_value_flow(pe,*,source):
    """Ref-object dispatch followed by object conversion; not a DWORD byte read."""
    pins=AUDIT_PINS['selectedListElementValueFlow']
    windows=[]
    for at,expected in pins['windows']:
        raw=bytes.fromhex(expected)
        require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    bodies=[]
    for start,end,expected in pins['bodies']:
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        digest=hashlib.sha256(raw).hexdigest().upper();require(digest,expected,source,start)
        bodies.append({'rva':start,'byteLength':len(raw),'sha256':digest})
    return {'windows':windows,'bodies':bodies,'outputByteLength':4,
            'level':'direct conditional ref-object/output and interface-dispatch flow',
            'boundary':'The non-FF helper retains reader RCX, output RDX and companion R9, and saves incoming R8 in the stack qword later passed by address to formatter dispatch. Companion-derived class slots supply the provider query and conversion interface carrier. Dispatch receives the original reader plus that initialized writable object slot. A null resulting object yields EAX=0; otherwise the conversion helper receives slot number zero, a separately derived interface carrier and the resulting object. Its hit path compares exact pointers in 16-byte class interface records, adds the requested ushort slot to a record DWORD offset, sign-extends the 32-bit sum and addresses a target/companion pair at class+(sum+0x14)*16. Its miss path delegates pair resolution to another helper. The common path tail-jumps with RCX=object and RDX=the loaded companion; it does not pass the original reader to this conversion target. The outer helper writes returned EAX to its four-byte output. That width is therefore a converted result width, not proof of a serialized DWORD load or four-byte cursor advance. Pair bounds, interface/class initialization, provider and conversion identities, actual target selection, delegated byte consumption and EOF remain unresolved.'}


def list_element_shared_context(pe,table,reg,code,spec_records,methods_raw,*,source):
    """Selected code-context candidate; never overwrite a live companion context."""
    pins=AUDIT_PINS['selectedListElementSharedContext']
    inst=table.resolve(pins['classInstantiation'])
    require([a.raw_type_record_hex for a in inst.arguments],
            pins['classArgumentRawTypes'],source,inst.record_va)
    require(len(spec_records),reg['methodSpecsCount'],source)
    selected={i for i,row in enumerate(spec_records) if row==(pins['methodDefinition'],pins['classInstantiation'],-1)}
    require(sorted(selected),[pins['methodSpecIndex']],source)
    rows=generic_method_candidates(methods_raw,reg['genericMethodTableCount'],len(spec_records),selected,
        code['genericMethodPointersCount'],code['invokerPointersCount'],source=source,
        offset=int(reg['genericMethodTable'],16))
    for row in rows:
        slot=int(code['genericMethodPointers'],16)+row['indices'][0]*8
        row['methodPointerSlotVa']=slot;row['methodPointerVa']=pe.u64_at_va(slot)
    require([(r['methodSpecIndex'],r['methodPointerVa']) for r in rows],[(pins['methodSpecIndex'],pe.image_base+pins['codeCandidateRva'])],source)
    return {'classInstantiation':inst.as_dict(),'methodDefinition':pins['methodDefinition'],'methodSpecIndices':sorted(selected),
            'codeCandidates':rows,'level':'exact selected static MethodSpec/code-context relation',
            'boundary':'The selected MethodSpec of the previously module/token-joined GenericMemoryPackFormatter Deserialize definition has ordered GameplayTag-record and Object-record arguments and no method instantiation. Its bounded generic-method table entry joins the dispatcher comparison target. This is a shared-code candidate context, not the actual object class or loaded companion context. The companion class supplies the specialized branch RGCTX slots independently; substituting the shared Object argument into that context is invalid without separate evidence. Actual provider selection, companion inflation, element payload and EOF remain unresolved.'}


def list_element_null_probe(pe,*,source):
    """Conditional FF peek and one-byte consumption, not a terminal grammar."""
    pins=AUDIT_PINS['selectedListElementNullProbe']
    windows=[]
    for at,rawhex in pins['windows']:
        raw=bytes.fromhex(rawhex)
        require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'byteLength':len(raw),'rawHex':rawhex,'sha256':hashlib.sha256(raw).hexdigest().upper()})
    return {'windows':windows,'markerByte':255,'fastConsumedBytesOnMatch':1,
            'level':'direct conditional marker-peek and consumed-counter flow',
            'boundary':'The selected helper calls a peek routine that ensures one readable byte if needed, compares cursor[0] with 0xFF and returns the comparison without directly advancing cursor or counters. A false result returns immediately. A true result calls a byte consumer with the same reader and a local byte output, then returns true regardless of that consumer AL result. The consumer copies one byte out; its fast path advances cursor, local and consumed counters by one and decrements remaining by one. It returns byte!=0xFF, so the wrapper does not simply forward that boolean. Cold paths use the already reviewed ensure/advance routines; ensure may replace the segment, so absence of fast pointer increment does not imply unchanged allocation. The dispatcher true branch clears its DWORD output. This conditional FF handling does not identify a serialized union, prove the non-FF element width, guarantee source validity, or establish source/terminal/EOF consumption. The shared target identity does not prove this branch executes.'}


def list_element_dispatch(pe,*,source):
    """Object-selected target/companion ABI, not a selected element reader."""
    pins=AUDIT_PINS['selectedListElementDispatch']
    bodies=[]
    for start,end,expected in pins['bodies']:
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        digest=hashlib.sha256(raw).hexdigest().upper()
        require(digest,expected,source,start)
        bodies.append({'rva':start,'byteLength':len(raw),'sha256':digest})
    # Decode the actual RIP operand rather than infer a target from nearby names.
    at=pins['targetLoadRva'];raw=pe.bytes_at_va(pe.image_base+at,7)
    require(raw[:3],bytes.fromhex(pins['targetLoadPrefix']),source,at)
    require(len(raw),7,source,at)
    target=at+7+struct.unpack_from('<i',raw,3)[0]
    require(target,pins['specializedTargetRva'],source,at)
    return {'bodies':bodies,'targetPairOffsets':[0x190,0x198],'specializedTargetRva':target,
            'fallbackCallRva':pins['fallbackCallRva'],'level':'direct conditional object-target/companion ABI',
            'boundary':'Entry RDX is retained as the formatter object, R8 as the reader and R9 as the output pointer; incoming RCX is overwritten by the object class before the initialization helper call. The class is then reloaded and its +0x190 target and +0x198 companion are loaded as a pair. If the target differs from the exact RIP-derived comparison address, the cold branch performs an ordinary indirect CALL with RCX=object, RDX=reader, R8=output and R9=the loaded companion, then rejoins cleanup. It is not a tail jump, nor a companion inferred from declaration order. The equal-target path instead reads the loaded companion class RGCTX slots and calls another helper with the retained reader. A nonzero AL clears the output DWORD; the other path eventually forwards the retained reader/output, a helper-derived value and class slot three to another reader helper. These distinct branches do not certify which target the live object selects. Class initialization, actual target/companion identity and inflation, all delegated read widths/cursor changes and final EOF remain unresolved. No constant element byte width or terminal-candidate elimination follows.'}


def list_formatter_candidate(pe,md,modules,image_owners,reg,code,table,spec_records,methods_raw,*,source):
    """Concrete registered candidate, separate from active provider dispatch."""
    pins=AUDIT_PINS['selectedListFormatterCandidate']
    identities=module_methods(pe,md,modules,image_owners,
        pins['methods'],source=source)
    require(identities[0]['token'],pins['deserializeToken'],source)
    index=pins['registeredTypeIndex']
    require(index<reg['typesCount'],True,source)
    pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
    require(pointer!=0,True,source,int(reg['types'],16)+index*8)
    raw=pe.bytes_at_va(pointer,16);require(len(raw),16,source,pointer)
    require(raw[10],0x15,source,pointer)
    carrier_pointer=struct.unpack_from('<Q',raw)[0]
    require(carrier_pointer!=0,True,source,pointer)
    carrier_raw=pe.bytes_at_va(carrier_pointer,32);require(len(carrier_raw),32,source,carrier_pointer)
    base_pointer=struct.unpack_from('<Q',carrier_raw)[0]
    require(base_pointer!=0,True,source,carrier_pointer)
    base_raw=pe.bytes_at_va(base_pointer,16)
    carrier=generic_type_carrier(raw,carrier_raw,base_raw,type_pointer=pointer,type_count=len(md.types),source=source)
    require(carrier['baseDefinitionIndex'],pins['listFormatterDefinition'],source,base_pointer)
    require(md.methods[pins['methods'][0][0]].declaring_type,pins['listFormatterDefinition'],source)
    inst=table.resolve_pointer(carrier['classInstantiationPointerVa'])
    require(inst.index,pins['classInstantiation'],source,inst.record_va)
    require(len(inst.arguments),1,source,inst.record_va)
    require(inst.arguments[0].raw_type_record_hex,pins['elementArgumentRawType'],source,inst.record_va)
    # spec_records is the already bounded complete MethodSpec inventory from audit().
    require(len(spec_records),reg['methodSpecsCount'],source)
    selected={i for i,row in enumerate(spec_records) if row==(pins['methods'][0][0],pins['classInstantiation'],-1)}
    require(sorted(selected),[pins['methodSpecIndex']],source)
    candidates=generic_method_candidates(methods_raw,reg['genericMethodTableCount'],len(spec_records),selected,
        code['genericMethodPointersCount'],code['invokerPointersCount'],source=source,
        offset=int(reg['genericMethodTable'],16))
    for row in candidates:
        slot=int(code['genericMethodPointers'],16)+row['indices'][0]*8
        row['methodPointerSlotVa']=slot;row['methodPointerVa']=pe.u64_at_va(slot)
    require([(r['methodSpecIndex'],r['methodPointerVa']) for r in candidates],
            [(pins['methodSpecIndex'],pe.image_base+pins['codeCandidateRva'])],source)
    windows=[]
    for at,expected in pins['windows']:
        chunk=bytes.fromhex(expected)
        require(pe.bytes_at_va(pe.image_base+at,len(chunk)),chunk,source,at)
        windows.append({'rva':at,'rawHex':expected})
    range_failure_branch_rva=pins['rangeFailureBranchRva']
    range_failure_branch_raw=pe.bytes_at_va(pe.image_base+range_failure_branch_rva,6)
    require(range_failure_branch_raw,bytes.fromhex(pins['rangeFailureBranchHex']),source,
            range_failure_branch_rva)
    range_failure_target_rva=(range_failure_branch_rva+6+
                              struct.unpack_from('<i',range_failure_branch_raw,2)[0])
    require(range_failure_target_rva,pins['rangeFailureTargetRva'],source,range_failure_branch_rva)
    return {'methodIdentities':identities,'registeredTypeIndex':index,'typeCarrier':carrier,
            'classInstantiation':inst.as_dict(),'methodSpecIndices':sorted(selected),'codeCandidates':candidates,
            'windows':windows,'level':'exact static candidate identity; direct conditional header and loop flow',
            'fastHeaderGuard':{
                'countWidthBytes':4,
                'signedCount':True,
                'remainingBytesComparedToCount':True,
                'comparisonRva':pins['fastHeaderComparisonRva'],
                'comparisonRawHex':pins['fastHeaderComparisonHex'],
                'rangeFailureCondition':'remaining < signed count',
                'rangeFailureBranchRva':range_failure_branch_rva,
                'rangeFailureBranchRawHex':range_failure_branch_raw.hex().upper(),
                'rangeFailureTargetRva':range_failure_target_rva,
                'rangeFailureBodyRawHex':pins['rangeFailureBodyHex'],
                'boundary':'The four-byte signed count is compared with remaining bytes after the header. A signed remaining<count branch reaches a helper call followed by INT3 if the helper returns; it does not enter the normal positive-element loop.',
            },
            'boundary':'The registered ListFormatter type and Deserialize MethodSpec share the same one-argument instantiation as the previously joined List carrier. The complete selected MethodSpec/code-table join yields one static code candidate, not proof of provider selection. This body receives the reader in RDX, output-slot pointer in R8 and companion in R9. Its fast header path reads a signed DWORD, advances cursor and both counters by four, and compares total-minus-consumed with the sign-extended count without multiplying by an element width. Header -1 clears the output. With a null output, other negative counts reach a helper followed by INT3; with an existing output, the reviewed reuse branch instead increments object+0x1C, clears object+0x18 and reaches a loop guarded by count>0. Thus this body does not universally reject all counts below -1. Each positive iteration passes the same reader and a zeroed four-byte output slot to element dispatch, then forwards the output word to another helper and increments its loop index. A four-byte output slot does not prove four serialized bytes per element. Cold header paths call the separately reviewed ensure/advance helpers. Element formatter identity, helper effects, successful allocation/reuse, actual MethodInfo/provider selection, authenticated source span and final cursor/EOF remain unresolved. Keep both terminal grammars.'}


def nested_reader_context(pe, md, modules, image_owners, reg, table, *, source, metadata_source):
    """Slot-zero context chain: reciprocal parameters, never live substitution."""
    pins=AUDIT_PINS['selectedNestedReaderContext']
    methods=module_methods(pe,md,modules,image_owners,
        pins['methods'],source=source,
        expected_image='MemoryPack.dll')
    module=modules['MemoryPack.dll']
    require(pe.u32_at_va(module+0x40),pins['rgctxRangeCount'],source,module+0x40)
    require(pe.u32_at_va(module+0x50),pins['rgctxEntryCount'],source,module+0x50)
    range_va=pe.u64_at_va(module+0x48);entry_va=pe.u64_at_va(module+0x58)
    ranges=pe.bytes_at_va(range_va,pins['rgctxRangeCount']*12)
    require(len(ranges),pins['rgctxRangeCount']*12,source,range_va)
    containers=[m.generic_container_index for m in md.methods]
    rows=[]
    for definition,token,start,count,kind,index,next_definition,inst_index in pins['rows']:
        require(md.methods[definition].token,token,metadata_source,definition)
        require(select_rgctx_range(ranges,pins['rgctxEntryCount'],token,source=source,offset=range_va),(start,count),source,range_va)
        at=entry_va+start*16;raw=pe.bytes_at_va(at,16)
        require(len(raw),16,source,at)
        require(struct.unpack_from('<I',raw)[0],kind,source,at)
        payload=struct.unpack_from('<Q',raw,8)[0]
        encoded=pe.bytes_at_va(payload,4)
        require(encoded,struct.pack('<I',index),source,payload)
        row={'methodDefinition':definition,'token':token,'relativeSlot':0,'moduleEntryIndex':start,
             'entryVa':at,'entryRawHex':raw.hex().upper(),'index':index,'kind':kind}
        if kind==3:
            require(index<reg['methodSpecsCount'],True,source,payload)
            spec_at=int(reg['methodSpecs'],16)+index*12
            spec=pe.bytes_at_va(spec_at,12)
            parsed=method_spec_record(spec,len(md.methods),reg['genericInstsCount'],source=source,offset=spec_at)
            require(parsed,(next_definition,-1,inst_index),source,spec_at)
            inst=table.resolve(inst_index)
            require(len(inst.arguments),1,source,inst.record_va)
            argument=inst.arguments[0];type_at=argument.type_pointer_va
            type_raw=bytes.fromhex(argument.raw_type_record_hex)
            row.update({'methodSpecVa':spec_at,'methodSpecRawHex':spec.hex().upper(),
                        'nextMethodDefinition':next_definition,'methodInstantiation':inst.as_dict()})
        else:
            require(index<reg['typesCount'],True,source,payload)
            slot=int(reg['types'],16)+index*8
            pointer=pe.bytes_at_va(slot,8)
            require(len(pointer),8,source,slot)
            type_at=struct.unpack('<Q',pointer)[0]
            require(type_at!=0,True,source,slot)
            type_raw=pe.bytes_at_va(type_at,16)
        require(len(type_raw),16,source,type_at)
        require(type_raw[10],0x1E,source,type_at)
        owner=method_parameter_owner(md.buf,struct.unpack_from('<Q',type_raw)[0],containers,source=metadata_source)
        require((owner['methodIndex'],owner['ordinal']),(definition,0),metadata_source,owner['containerOffset'])
        row.update({'typePointerVa':type_at,'typeRawHex':type_raw.hex().upper(),'parameterOwner':owner})
        rows.append(row)
    windows=[]
    for at,expected in pins['windows']:
        raw=bytes.fromhex(expected)
        require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    return {'methods':methods,'rows':rows,'windows':windows,
            'level':'exact static token/MethodSpec/MVAR joins; direct conditional nested context reads',
            'boundary':'The selected nested body retains its incoming reader and follows MethodInfo+0x38 slot zero three times before deriving a provider key. The corresponding independently image/token-joined ranges identify ReadPackable to ReadValue, ReadValue to GetFormatter, then the GetFormatter MVAR type. Each method edge has one open method argument whose reciprocal owner is the preceding method and whose ordinal is zero; the final type is a distinct ordinal-zero parameter owned by GetFormatter itself. These are three different parameter records, not interchangeable raw identities. Conditional on ordinary context inflation from the previously authenticated ReadPackable<List<...>> call, this chain carries that same concrete argument through the intermediate contexts. All three generic definition ordinary-pointer slots are null; static ranges do not select a shared body. The body passes the retained reader and separate output slot to dispatch, but actual initialized MethodInfos, substitution, provider key/cache contents, list formatter, source length and final cursor remain unobserved. No list framing, element meaning or terminal uniqueness follows.'}


def wrapper_consumer(pe, md, modules, image_owners, reg, table, *, source):
    """Reviewed conditional wrapper path, not a source/EOF or dispatch receipt."""
    pins=AUDIT_PINS['selectedWrapperConsumer']
    instruction=pe.bytes_at_va(pe.image_base+pins['usageLoadRva'],7)
    require(instruction[:3],bytes.fromhex(pins['usageLoadPrefix']),source,pins['usageLoadRva'])
    cell=rip_qword_load_target(instruction,pe.image_base+pins['usageLoadRva'],source=source)
    initializer=pe.bytes_at_va(pe.image_base+pins['initializerLoadRva'],7)
    require(initializer[:3],bytes.fromhex(pins['initializerLoadPrefix']),source,pins['initializerLoadRva'])
    require(pe.image_base+(pins['initializerLoadRva']+7)+struct.unpack_from('<i',initializer,3)[0],cell,source,pins['initializerLoadRva'])
    records_base=int(reg['methodSpecs'],16)
    spec=usage_method_spec(pe.bytes_at_va(cell,8),pe.bytes_at_va(records_base,reg['methodSpecsCount']*12),
                          len(md.methods),reg['genericInstsCount'],source=source,
                          usage_offset=cell,records_offset=records_base)
    require((spec['index'],spec['definition'],spec['classInstantiationIndex'],spec['methodInstantiationIndex']),
            tuple(pins['methodSpec']),source,spec['va'])
    inst=table.resolve(spec['methodInstantiationIndex'])
    require(len(inst.arguments),1,source,inst.record_va)
    arg=inst.arguments[0]
    raw=bytes.fromhex(arg.raw_type_record_hex)
    carrier_raw=pe.bytes_at_va(struct.unpack_from('<Q',raw)[0],32)
    base_raw=pe.bytes_at_va(struct.unpack_from('<Q',carrier_raw)[0],16)
    carrier=generic_type_carrier(raw,carrier_raw,base_raw,type_pointer=arg.type_pointer_va,
                                 type_count=len(md.types),source=source)
    require(carrier['baseDefinitionIndex'],pins['listDefinitionIndex'],source)
    require(md.type_full_name(md.types[pins['listDefinitionIndex']]),'System.Collections.Generic.List`1',source)
    element_inst=table.resolve_pointer(carrier['classInstantiationPointerVa'])
    require(element_inst.index,pins['elementInstantiation'],source,element_inst.record_va)
    require(len(element_inst.arguments),1,source,element_inst.record_va)
    require(element_inst.arguments[0].raw_type_record_hex,pins['elementArgumentRawType'],source)
    call=pe.bytes_at_va(pe.image_base+pins['nestedCallRva'],5)
    require(call[0],0xE8,source,pins['nestedCallRva'])
    require(pe.image_base+(pins['nestedCallRva']+5)+struct.unpack_from('<i',call,1)[0],pe.image_base+pins['nestedCallTargetRva'],source,pins['nestedCallRva'])
    wrapper_methods=module_methods(pe,md,modules,image_owners,
        pins['methods'],
        source=source,expected_image='MemoryPack.Beyond.dll')
    code_windows=[]
    for rva,expected,role in pins['headerCodeWindows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        code_windows.append({'rva':rva,'rawHex':raw.hex().upper(),'role':role})
    return {'methodSpec':spec,'methodInstantiation':inst.as_dict(),
            'listCarrier':carrier,'elementInstantiation':element_inst.as_dict(),
            'methodIdentities':wrapper_methods,'headerCodeWindows':code_windows,
            'wrapperFraming':{
                'headerByteWidth':1,'acceptedNonNullHeaderByte':1,'nullHeaderByte':0xFF,
                'remainingOffset':0x30,'cursorOffset':0x50,
                'consumedCounterOffsets':[0x40,0x44],
                'nestedCallRva':pins['nestedCallRva'],
                'boundary':'The reviewed reader consumes exactly one header byte before the nested List<GameplayTag> read. Header 0xFF takes the null path; non-null header 1 reaches the nested read; other values leave the supported path. This is static wrapper code, not proof that the runtime provider selects it for the current file.',
            },
            'formatterEntryRva':pins['formatterEntryRva'],'readerEntryRva':pins['readerEntryRva'],'nestedCallRva':pins['nestedCallRva'],
            'level':'direct conditional consumer; exact static usage/type relation',
            'boundary':'The formatter forwards its reader unchanged to the wrapper reader. The fast path consumes one byte using remaining+0x30, cursor+0x50 and counters+0x40/+0x44. Header 0xFF clears the output; non-null header 1 reaches the nested call with the same reader and the recorded List instantiation. Other headers reach a helper then INT3. Cold ensure/advance transitions are described separately in selectedReaderCursorConsumers; their descriptor helpers are not fully closed. No list element layout, actual provider selection, authenticated source allocation, source extent or final cursor is established.'}


def resource_carrier_consumers(pe, *, source):
    """Reviewed native carrier/state path, separate from actual resource selection."""
    pins=AUDIT_PINS['selectedResourceCarrierConsumers']
    edges=[]
    for rva,target in pins['edges']:
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in pins['instructionWindows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    switch_targets=pins['switchTargets']
    switch=pe.bytes_at_va(pe.image_base+pins['switchDataRva'],4*len(switch_targets))
    require(switch,struct.pack(f'<{len(switch_targets)}I',*switch_targets),source,pins['switchDataRva'])
    return {'edges':edges,'instructionWindows':windows,
            'switchData':{'rva':pins['switchDataRva'],'rawHex':switch.hex().upper()},
            'level':'direct conditional native carrier/state consumption',
            'outer':{'rva':pins['outerRva'],'inputCarrierBytes':16,
                     'boundary':'Null MethodInfo+0x38 invokes initialization; non-null skips it. Rebuilds a 16-byte local from input qword+0 and dword+8, with last dword zero. Supplies the local, output slot, zero R8 and context slot 0 to the inner entry. Returned EAX is discarded; the output slot is returned after cleanup. No EOF comparison in this wrapper.'},
            'inner':{'rva':pins['innerRva'],'stateStackOffset':0x40,'counterOffset':0x44,
                     'boundary':'Inlines state construction: input carrier at state+0x20, dword length at +0x30, signed length at +0x18, zero +0x38/+0x40/+0x44, and pointer-or-null cursor at +0x50. State+0x48 comes from the thread-local storage/allocation path, not the plain constructor. Conditional non-null helper result reaches dispatch slot 5 with R8=&state and R9=output. Returns state dword+0x44 after cleanup, matching the independently identified consumed accessor offset. This is not a proof of helper success or input allocation validity.'},
            'boundary':'MethodSpec-based names and declared stream input are separately joined in selectedStreamSourceIdentity. Live contexts, complete upstream resource selection, path/hash, carrier allocation length and final authenticated-file cursor are not joined. The switch data is excluded from the code window. Both terminal layouts remain ambiguous.'}


def skill_resource_context(pe, md, modules, image_owners, table, reg, code,
                          spec_records, specs_raw, methods_raw, *, source):
    """Exact selected static relations; no live generic sharing or file receipt."""
    pins=AUDIT_PINS['selectedSkillResourceContext']
    identity=named_top_level_type(md.buf,b'Gameplay.Beyond.dll',b'Beyond.Gameplay.Core',
                                 b'SkillData',source=source)
    require(identity['typeDefinitionIndex'],pins['skillDataDefinition'],source)
    inst=table.resolve(pins['concreteInstantiation'])
    require(len(inst.arguments),1,source,inst.record_va)
    raw=bytes.fromhex(inst.arguments[0].raw_type_record_hex)
    require(raw,bytes.fromhex(pins['skillDataArgumentRawType']),source,inst.arguments[0].type_pointer_va)
    require(struct.unpack_from('<Q',raw)[0],identity['typeDefinitionIndex'],source)
    object_inst=table.resolve(pins['objectInstantiation'])
    require(len(object_inst.arguments),1,source,object_inst.record_va)
    require(object_inst.arguments[0].raw_type_record_hex,pins['objectArgumentRawType'],source)
    identities=module_methods(pe,md,modules,image_owners,
        pins['methods'],
        source=source,expected_image='Common.Beyond.dll')
    for row,token in zip(identities,pins['methodTokens']):
        require(row['token'],token,source,row['slotVa'])
    selected=[]
    for index,definition in pins['concreteMethodSpecs']:
        require(spec_records[index],(definition,-1,inst.index),source,int(reg['methodSpecs'],16)+index*12)
        selected.append({'index':index,'definition':definition,'classInstantiationIndex':-1,
                         'methodInstantiationIndex':inst.index,'rawHex':specs_raw[index*12:(index+1)*12].hex().upper()})
    matching={i for i,(definition,_,_) in enumerate(spec_records) if definition in (pins['methods'][0][0],pins['methods'][1][0])}
    candidates=generic_method_candidates(methods_raw,reg['genericMethodTableCount'],len(spec_records),
        matching,code['genericMethodPointersCount'],code['invokerPointersCount'],
        source=source,offset=int(reg['genericMethodTable'],16))
    for row in candidates:
        method,invoker,_=row['indices']
        row['methodPointerVa']=pe.u64_at_va(int(code['genericMethodPointers'],16)+method*8)
        row['invokerPointerVa']=pe.u64_at_va(int(code['invokerPointers'],16)+invoker*8)
        require(row['methodPointerVa']!=0 and row['invokerPointerVa']!=0,True,source,row['va'])
    # Pins validate the current complete candidate set, without selecting a live one.
    require([(r['methodSpecIndex'],r['methodPointerVa']) for r in candidates],
            [(pins['objectMethodSpecs'][0][0],pe.image_base+pins['objectCodeCandidateRva0']),(pins['objectMethodSpecs'][1][0],pe.image_base+pins['objectCodeCandidateRva1'])],source)
    for index,definition in pins['objectMethodSpecs']:
        require(spec_records[index],(definition,-1,object_inst.index),source,int(reg['methodSpecs'],16)+index*12)
    return {'typeIdentity':identity,'methodIdentities':identities,'concreteInstantiation':inst.as_dict(),
            'objectInstantiation':object_inst.as_dict(),'concreteMethodSpecs':selected,
            'sameDefinitionMethodSpecs':[{'index':i,'indices':list(spec_records[i]),
                                         'rawHex':specs_raw[i*12:(i+1)*12].hex().upper()} for i in sorted(matching)],
            'codeCandidates':candidates,
            'tableFraming':{'records':reg['genericMethodTableCount'],'byteLength':len(methods_raw),
                             'sha256':hashlib.sha256(methods_raw).hexdigest().upper(),
                             'boundary':'All 16-byte records and MethodSpec keys bounded; only selected triples decoded. Other triples remain opaque.'},
            'level':'exact static type/MethodSpec/code-table relations',
            'boundary':'Core.SkillData, not the same-named AI nested type. Generic definition module slots are null; code candidates come from the separate generic method table. Same-definition Object MethodSpecs do not establish actual sharing selection, method invocation, resource path/hash, reader ABI, consumed length or EOF. Preserve both terminal candidates.'}
