"""Current plain-method metadata token and descriptor-slot source transfers.

The selected non-inflated class path derives its method record from the
actual class metadata methodStart plus the loop ordinal. It reads the token
from that same record and writes the unchanged DWORD into the current
descriptor's token field. The descriptor base is the exact pointer published
at that ordinal in the class method array; the source advances the descriptor
by88 bytes and both ordinal counters by one. Complete source/CFG/frame checks
retain the one actual self-recursive E8 under an explicit normal-return
condition. Recursion termination and recursive/opaque callee effects are not
inferred from its target.

The exact selected placeholder method records are independently joined to
the selected metadata section, declaring type and method range. This is a
source/representation claim: class method-count/layout/cache coherence,
valid disjoint allocated descriptor/array storage, stable metadata, normal
helper returns, initialized tables and the actual incoming MethodInfo and
closed generic context remain separate. No nominal enum formatter callback,
wire, parent or whole-owner grammar follows.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-plain-method-descriptor-paths.v1'
LABEL='enumPlainMethodDescriptorPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def record_program(regions,entry):
    g=BytesPath(regions,entry);fallback=g.relative('4c8d15')
    g.take('488b4668','8b4024','03c2','4898','48c1e005');header=g.relative('488b15')
    g.take('48636a30');metadata=g.relative('480305');g.take('4803e8','48634218','4c634d00')
    need('same-metadata-string-base',g.relative('480305')==metadata)
    g.take('4c03c8','48634508','83f8ff');g.branch('0f84',False)
    g.take('488bd0');registration=g.relative('488b05')
    g.take('488b4838','488b3cd1');token=g.at;g.take('448b6d14')
    return dict(selectedBytes=g.seen,entry=entry,tokenLoad=token,metadataHeaderCell=header,metadataBaseCell=metadata,
        metadataRegistrationCell=registration,methodSectionHeaderOffset=48,methodRecordBytes=32,
        classMetadataOffset=104,classMethodStartOffset=36,recordIndex='class metadata methodStart plus incoming ordinal EDX',
        currentRecordRegister='rbp',currentTokenRegister='r13d',tokenRecordOffset=20,
        returnTypeIndexOffset=8,returnTypeIndexMustNotBeMinusOne=True,registeredTypePointersOffset=56,
        fallbackMethodPointer=fallback)


def token_program(regions,entry):
    g=BytesPath(regions,entry);g.take('44896b28','48896b18')
    return dict(selectedBytes=g.seen,tokenStore=entry,tokenRegister='r13d',descriptorBase='rbx -32',
        tokenDescriptorOffset=72,tokenBytes=4,metadataRecordDescriptorOffset=56,
        recordSourceRegister='rbp',sameRecordAndTokenRequired=True)


def publication_program(regions,entry,*,loop_entry):
    g=BytesPath(regions,entry);g.take('488d4be0','488b8698000000','4c8b542438','4a890cd0',
        '4883c358','8b542430','ffc2','89542430','49ffc2','4c89542438','4c3b542448')
    need('same-actual-counted-record-backedge',g.relative('0f8c')==loop_entry)
    return dict(selectedBytes=g.seen,entry=entry,classMethodsOffset=152,descriptorBase='rbx -32',
        descriptorStride=88,arrayPointerStride=8,publicationSourceRegister='rcx',publicationCounterRegister='r10',
        publicationCounterStackOffset=56,metadataOrdinalStackOffset=48,methodCountStackOffset=72,
        descriptorStep=88,arrayCounterStep=1,metadataOrdinalStep=1,
        unchangedDescriptorBasePublished=True,wholeMethodSetupSemanticsProved=False)


def preserve_until(graph,rows,entry,origin,store,parents):
    """Preserve explicit nonvolatile origins on every path reaching the store."""
    from scripts.game_data.il2cpp.class_creation_control import _dominators
    from scripts.game_data.il2cpp.class_enum_fields_control import _no_register_write
    edges={int(a):{int(v)for v in values}for a,values in graph['edges'].items()};by={int(r['va'],16):r for r in rows}
    need('origin-dominates-selected-store',origin in _dominators(edges,entry)[store])
    pending=list(edges[origin]);reached=set()
    while pending:
        at=pending.pop()
        if at==store or at in reached:continue
        need('no-origin-reentry-before-store',at!=origin);reached.add(at);pending.extend(edges[at]-reached)
    reverse={a:set()for a in edges}
    for at,targets in edges.items():
        for target in targets:reverse[target].add(at)
    pending=[store];ancestors=set()
    while pending:
        at=pending.pop()
        if at not in ancestors:ancestors.add(at);pending.extend(reverse[at]-ancestors)
    selected=sorted(reached&ancestors)
    need('only-nonvolatile-preservation-claims',type(parents)is tuple and all(p in('rbx','rbp','rsi','rdi','r12','r13','r14','r15')for p in parents))
    for at in selected:
        for parent in parents:_no_register_write([by[at]],0,1,parent,calls_allowed=True)
    return dict(origin=origin,store=store,preservedRegisters=list(parents),checkedInstructionSites=selected,
        normalAbiPreservingCallsRequired=True,opaqueMemoryAndAliasEffectsProved=False)


def decode(mapper,data,entry):
    from scripts.game_data.il2cpp.text_source_instructions import decode_text_instruction
    from scripts.game_data.il2cpp.enum_metadata_phase_order import decode as initialization_decode
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            result=decode_text_instruction(raw,offset,at)
            return result if result is not None else mapper.decode_one_x64(raw,offset,at)
    return initialization_decode(Fallback(),data,entry)


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_method_key_construction import derive as key_source
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import complete_program
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.il2cpp.enum_class_field_paths import unique
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);prior=key_source(image,pins,**arguments)
    wrapper=owned(image,prior['proof']['definitionPrograms'][1]['methodSetupTarget'])
    call=unique(wrapper['regions'],bytes.fromhex('488d542430488bcbe8'))+len(bytes.fromhex('488d542430488bcb'))
    g=BytesPath(wrapper['regions'],call);inner=g.relative('e8');body=owned(image,inner);rows=[]
    for at,raw in body['regions']:rows+=checked_rows(decode(image.mapper,raw,at),raw,LABEL)
    rows.sort(key=lambda row:int(row['va'],16));recursive={}
    for row in rows:
        raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
        if len(raw)==5 and raw[0]==0xe8 and at+5+int.from_bytes(raw[1:],'little',signed=True)==inner:recursive[at]=inner
    need('one-exact-self-recursive-call',len(recursive)==1)
    graph,padding=complete_program(body['regions'],rows,inner,recursive_calls=recursive)
    site=unique(body['regions'],bytes.fromhex('488b46688b402403c2489848c1e005'))-7
    record=record_program(body['regions'],site)
    token=token_program(body['regions'],unique(body['regions'],bytes.fromhex('44896b2848896b18')))
    publication=publication_program(body['regions'],unique(body['regions'],bytes.fromhex('488d4be0488b8698000000')),loop_entry=site)
    preserved=preserve_until(graph,rows,inner,record['tokenLoad'],token['tokenStore'],('rbp','rbx','r13'))
    seed=prior['proof']['methodTableSeedSource'];selection=seed['proof']['argumentSeedSource']['proof']['methodSelectionSource']
    fixed=selection['proof']['primitiveNormalizerSource']['proof']['nameAndInternerSource']['proof']['internerSource']['proof']['placeholderTypeSource']['proof']['argumentKeySource']['proof']['normalizerSelection']['proof']['classFieldSource']['proof']['typeDataFixup']['proof']['fixup']
    need('same-actual-metadata-cells-and-selected-primary-registration',record['metadataBaseCell']==fixed['metadataBaseCell']
        and record['metadataHeaderCell']==fixed['metadataHeaderCell']
        and record['metadataRegistrationCell']==selection['proof']['registrationAliasPublication']['metadataRegistrationCell'])
    md=image.metadata;section=md.sections['methods'];need('same-selected-method-record-geometry',md.method_record_size==record['methodRecordBytes']
        and struct.unpack_from('<I',md.buf,record['methodSectionHeaderOffset'])[0]==section.offset)
    facts=[]
    for selected in seed['proof']['selectedStaticMethodRows']:
        method=md.methods[selected['methodDefinition']];raw=md.buf[section.offset+method.index*32:section.offset+(method.index+1)*32]
        name,declaring=struct.unpack_from('<ii',raw);token_value=struct.unpack_from('<I',raw,20)[0];td=md.types[declaring]
        need('same-exact-selected-plain-method-record',name==method.name_index and declaring==method.declaring_type
            and token_value==method.token and td.method_start<=method.index<td.method_start+td.method_count
            and md.type_full_name(td)==selected['formatterType'])
        facts.append(dict(methodDefinition=method.index,methodName=md.string(name),declaringType=selected['formatterType'],
            rawMethodRecordHex=raw.hex().upper(),token=token_value,metadataOrdinal=method.index-td.method_start,
            classMethodCount=td.method_count,actualInitializedDescriptorPointerIdentityProved=False))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(methodKeySource=prior,methodSetupCall=call,innerEntry=inner,innerWindows=body['windows'],innerCfg=graph,
            innerPadding=padding,recordSource=record,tokenStore=token,ordinalPublication=publication,
            tokenAndRecordPreservation=preserved,selectedPlainMethodRecords=facts),
        plainMetadataTokenAndDescriptorOrdinalTransfersProved=True,actualInitializedDescriptorPointerIdentityProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Complete current source partition/CFG/conditional normal recursion frames; actual methodStart/ordinal/record/token and descriptor array-slot transfer, independent static method records and metadata cells.',
            conditional=__doc__,structuralOnly='Plain MethodInfo token/record/ordinal representation.',
            unresolved=['descriptor allocation/count/layout/cache and opaque alias coherence','recursive termination/callee effects',
                'initialized interner/method table and actual nominal MethodInfo/RGCTX/callback','wire/parent/EOF']))))
