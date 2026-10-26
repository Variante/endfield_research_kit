"""Authenticate the selected mask reference Param, admitting only a null constant."""
import json
from scripts.game_data.memorypack.reference_param import derive_reference_parameter
from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param as primitive
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
LABEL='maskParam'
VALUE='Beyond.Gameplay.CommonMaskBlendData'


def null_mask_program(regions,entry,offsets,barrier):
 g=BytesPath(regions,entry);cur,rem,adv,used=(offsets[k] for k in ('currentPtr','bufferLength','advancedCount','consumed'))
 g.take('48895c2410','48896c2418','4889742420','57','4883ec30');at=g.at;raw=g.read(7)
 scalar.need(LABEL,'initializationGuard',(b'\x80\x3d',0),(raw[:2],raw[-1]));cell=at+7+int.from_bytes(raw[2:6],'little',signed=True)
 g.take('488bfa','488bd9');g.branch('0f84',False)
 g.take((b'\x83\x7b'+bytes((rem,1))).hex());g.branch('0f8c',False)
 g.take((b'\x48\x8b\x43'+bytes((cur,))).hex(),'0fb630',(b'\x8b\x6b'+bytes((rem,))).hex(),'83ed01');g.branch('0f88',False)
 g.take((b'\x48\xff\x43'+bytes((cur,))).hex(),(b'\xff\x43'+bytes((adv,))).hex(),(b'\xff\x43'+bytes((used,))).hex(),(b'\x89\x6b'+bytes((rem,))).hex(),'4080feff');g.branch('0f84',True)
 g.take('488bcf','48c70700000000');g.call(barrier);g.jump('eb',1)
 g.take('488b5c2448','488b6c2450','488b742458','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,initializationFlagCell=cell,wireBytes=1,returnedReference=0,readerAdvance=1,entryRspRestored=True,nonvolatileRegistersRestored=['rbx','rbp','rsi','rdi'],condition='Initialized metadata flag; valid disjoint original reader/output storage; at least one contiguous byte whose value is FF; counters and pointer can advance by one; normal reference-barrier ABI. Cold refill, malformed and positive object paths are excluded.')


def derive(image,pins,profile):
 parent,ctx,owned,calls=derive_reference_parameter(image,pins,profile,VALUE,reader_method='ReadValue');base=image.pe.image_base;md=image.metadata
 w,=[w for w in derive_from_image(image).values() if w.wrapped_type==VALUE];scalar.need(LABEL,'referenceMask',False,ctx.is_value_type(VALUE));scalar.need(LABEL,'maskHolder',(w.name,VALUE,16),ctx.field(w.name+'::__instance'))
 methods={md.string(m.name_index):m for m in md.methods_for(md.types[w.type_definition])};m=methods['Deserialize'];primitive.reader_abi(image,ctx,m,w);source=owned(image.method_pointer_va(m))
 at,encoded=parent['ownedMethods']['set___path__']['instructions'][7];barrier=base+at+5+int.from_bytes(bytes.fromhex(encoded)[1:],'little',signed=True);offsets=scalar.reader_offsets(image,LABEL)
 path=null_mask_program(source['regions'],source['pointer'],offsets,barrier)
 getter=methods['GetValue'];scalar.owned_method_abi(image,ctx,getter.index,w.type_definition,(VALUE,18,True),[],LABEL+'.getter');at=image.method_pointer_va(getter);raw=image.pe.bytes_at_va(at,5);scalar.need(LABEL,'referenceGetter',bytes.fromhex('488b4110c3'),raw)
 registration=profile['childRegistration'];composition=profile['childComposition'];validate_eager_wrap_registration(image,registration,label=LABEL+'.childRegistration');validate_registered_formatter_composition(image,composition,label=LABEL+'.childComposition')
 scalar.need(LABEL,'childOriginal',VALUE,registration['originalType']);scalar.need(LABEL,'childWrapper',w.name,registration['wrapperType']);scalar.need(LABEL,'childComposition',[VALUE],[r['originalType'] for r in composition['registrations']])
 forward=owned(base+composition['methods'][1][3]);fcalls=calls(forward);forwarding=prove_zero_wrapper_forwarder(forward['rows'],dict(metadataInit=fcalls[0],classInit=fcalls[1]),source['pointer'],label=LABEL+'.childForward')
 return json.loads(json.dumps(dict(parent=parent,childForwarding=forwarding,childWrapper=w.name,childMethod=[m.index,w.name,'Deserialize',source['pointer']-base],childWindows=source['windows'],nullMask=path,readerFieldOffsets=offsets,getter=[getter.index,w.name,'GetValue',at-base],getterBytes=raw.hex().upper(),evidenceBoundary=dict(direct='Typed four-member reference Param, selected complete reader and owned stores/factory/null output, two Int32 bindings and pooled path; generated CommonMaskBlendData buffered FF branch consumes one byte, advances all reader counters and clears the original reference.',conditional='Initialized coherent compatible generated Param and mask wrapper/formatter routes, matching initialized StringPool, sufficient contiguous input, disjoint valid storage and ordinary helper/allocation/barrier ABI.',unresolved=['all positive mask constants, including audio configuration and animation curves','live provider default/cache/override selection','cold refill or malformed paths','runtime mask, teleport or video execution']))))
