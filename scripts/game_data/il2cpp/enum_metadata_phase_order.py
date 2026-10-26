"""Actual metadata publication/type-fixup precedes argument seeding.

The selected metadata phase first calls the actual initializer and reaches
argument seeding only through its nonzero-result branch. The initializer's
exact nonnull path publishes the unchanged loader result to both metadata
base/header cells used by the independent type-fixup owner. Its actual
type-fixup-loop call dominates the literal success result and complete return.
Both complete source families have byte partitions, CFGs and normal frames;
unsigned multiplication decoding is reused from its existing owner.

This proves source order and same-cell transfer. The loader selecting the
chosen metadata, allocation success, normal opaque helper effects, no later
alias mutation and actual startup execution remain conditions. It does not
prove initialized interning/method tables, concrete formatter/MethodInfo
selection or enum wire/parent/whole-owner grammar.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-metadata-phase-order.v1'
LABEL='enumMetadataPhaseOrder'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def phase_prefix(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2418','4889742420','55','57','4156','488d6c24b9','4881ec90000000','33db')
    call=g.at;initializer=g.relative('e8');g.take('84c0');guard=g.at;g.branch('0f84',False)
    return dict(selectedBytes=g.seen,initializerCall=call,initializerTarget=initializer,
        successGuard=guard,nonzeroInitializerResultRequired=True,fallthrough=g.at,
        initializerExecutionObserved=False)


def initializer_prefix(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec28');loader=g.relative('e8');base=g.relative('488905')
    g.take('488bc8','4885c0');g.branch('0f84',False)
    g.take('486390ac000000');header=g.relative('488905')
    return dict(selectedBytes=g.seen,metadataLoaderTarget=loader,metadataBaseCell=base,
        metadataHeaderCell=header,bothCellsReceiveUnchangedActualLoaderResult=True,
        nonnullLoaderResultRequired=True,loadedBufferIdentityOrLaterAliasStabilityProved=False)


def success_program(regions,entry,*,type_loop):
    g=BytesPath(regions,entry);need('actual-success-type-loop-call',g.relative('e8')==type_loop)
    success=g.at;g.take('b001','4883c428','c3')
    return dict(selectedBytes=g.seen,typeLoopCall=entry,typeLoopTarget=type_loop,
        successFlagInstruction=success,returnedLowByte=1,entryRspRestored=True,normalReturn=True)


def require_order(graph,entry,first,second,check):
    from scripts.game_data.il2cpp.class_creation_control import _dominators
    edges={int(at):{int(v)for v in values}for at,values in graph['edges'].items()}
    need(check,entry in edges and first in edges and second in edges
        and first in _dominators(edges,entry)[second])


def decode(mapper,data,entry):
    from scripts.game_data.il2cpp.metadata_initialization_instructions import decode_unsigned_register_multiply
    from scripts.game_data.il2cpp.enum_initialization_instructions import decode_enum_initialization_instructions
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            row=decode_unsigned_register_multiply(raw,offset,at)
            return row if row is not None else mapper.decode_one_x64(raw,offset,at)
    return decode_enum_initialization_instructions(Fallback(),data,entry)


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import derive as seed_source,complete_program
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.il2cpp.enum_class_field_paths import unique
    _publication_gate(image,pins);prior=seed_source(image,pins,**arguments)
    selection=prior['proof']['methodSelectionSource'];publication=selection['proof']['registrationAliasPublication']
    at=publication['end'];g=BytesPath([(at,image.pe.bytes_at_va(at,19))],at)
    g.relative('488d05');g.relative('488905');phase=g.relative('e8');phase_body=owned(image,phase)
    phase_program=phase_prefix(phase_body['regions'],phase)
    fixup=selection['proof']['primitiveNormalizerSource']['proof']['nameAndInternerSource']['proof']['internerSource']['proof']['placeholderTypeSource']['proof']['argumentKeySource']['proof']['normalizerSelection']['proof']['classFieldSource']['proof']['typeDataFixup']
    initializer=owned(image,phase_program['initializerTarget']);rows=[]
    for at,raw in initializer['regions']:rows+=checked_rows(decode(image.mapper,raw,at),raw,LABEL)
    rows.sort(key=lambda row:int(row['va'],16));graph,padding=complete_program(initializer['regions'],rows,initializer['pointer'])
    prefix=initializer_prefix(initializer['regions'],initializer['pointer']);known=fixup['proof']['fixup']
    need('same-independently-proved-metadata-cells',prefix['metadataBaseCell']==known['metadataBaseCell']
        and prefix['metadataHeaderCell']==known['metadataHeaderCell'])
    loop=fixup['proof']['typeLoop']['selectedBytes'][0][0]
    flag=unique(initializer['regions'],bytes.fromhex('b0014883c428c3'))
    success=success_program(initializer['regions'],flag-5,type_loop=loop)
    require_order(graph,initializer['pointer'],success['typeLoopCall'],success['successFlagInstruction'],
        'type-loop-dominates-initializer-success')
    seed=prior['proof']['selectedSeedLoop']['entry']
    require_order(prior['proof']['metadataPhaseCfg'],phase,phase_program['initializerCall'],seed,
        'actual-initializer-call-dominates-argument-seed')
    require_order(prior['proof']['metadataPhaseCfg'],phase,phase_program['successGuard'],seed,
        'actual-nonzero-initializer-guard-dominates-argument-seed')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(argumentSeedSource=prior,phasePrefix=phase_program,initializerWindows=initializer['windows'],
            initializerCfg=graph,initializerPadding=padding,initializerPrefix=prefix,initializerSuccess=success),
        actualTypeFixupSuccessPrecedesArgumentSeedingProved=True,actualMetadataPublicationCellsJoined=True,
        loaderOutputIdentityOrExecutionObserved=False,initializedArgumentOrMethodTableIdentityProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Complete initializer instruction partition/CFG/normal frames, actual same-loader-result base/header publication, actual independently owned type-fixup loop and phase success-guard/dominance joins.',
            conditional=__doc__,structuralOnly='Metadata initialization and registration-seed source ordering.',
            unresolved=['selected loader output/file identity and allocation/helper effects','startup execution and later cache/alias changes',
                'initialized interner/method-table population','actual nominal provider/MethodInfo/callback','wire/parent/EOF']))))
