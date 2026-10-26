"""Current reference Param and selected adapter FF branch; positive child excluded."""
import hashlib,json
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.memorypack.reference_param import derive_reference_parameter
from scripts.game_data.memorypack.reference_adapter_sources import validate_reference_routes
from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
from scripts.game_data.memorypack.modelview_reference_sources import read_value


def derive(image,pins,fact,key):
    if key['nativeInputs']!=pins:raise ValueError('referenceNullParam.dependency-native-inputs')
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);value=fact['valueType'];profile=fact['parentProfile'];child=fact['childEager']
    parent,_,_,_=derive_reference_parameter(image,pins,profile,value,reader_method='ReadValue')
    init,=[m for m in md.methods_for(ctx.index.types['Beyond.MemoryPack.MemoryPackGeneratedInit_Gameplay_Beyond'])if md.string(m.name_index)=='InitEager'];ranges=[r['runtimeTriple'][:2]for r in image.unwind_index.family(image.method_pointer_va(init)-base)['ranges']]
    for flow in(profile['registration'],child):
        w=flow['window']
        if not any(a<=w['startRva']<w['endRva']<=z for a,z in ranges):raise ValueError('referenceNullParam.eager-owned-source')
        validate_eager_wrap_registration(image,flow,label='referenceNullParam.eager')
    if child['originalType']!=value or ctx.is_value_type(value)or ctx.is_value_type(child['wrapperType']):raise ValueError('referenceNullParam.reference-child')
    ctx.require_ordinary_kind(child['key']['typeIndex'],18)
    args=image.instantiations.resolve(child['constructor']['methodSpec'][1]).arguments
    if image.pe.bytes_at_va(args[1].type_pointer_va,16)[10:12]!=b'\x12\x00':raise ValueError('referenceNullParam.ordinary-wrapper-class')
    route=dict(key['referenceRoutes'],wrappers=[]);core=validate_reference_routes(image,route,[])
    site=parent['typedRead']['instructionRva'];at,raw=next((a,bytes.fromhex(b))for a,b in parent['parent']['instructions']if a>site and bytes.fromhex(b)[:1]==b'\xe8');target=base+at+5+int.from_bytes(raw[1:],'little',signed=True)
    windows=[];regions=[]
    for part in image.unwind_index.family(target-base)['ranges']:
        a,z=part['runtimeTriple'][:2];data=image.pe.bytes_at_va(base+a,z-a);windows.append(dict(startRva=a,endRva=z,sha256=hashlib.sha256(data).hexdigest().upper()));regions.append((base+a,data))
    contexts=[]
    for owner,name in(('MemoryPack.MemoryPackReader','ReadValue'),('MemoryPack.MemoryPackFormatterProvider','GetFormatter')):
        m,=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==name and m.parameter_count==0 and m.generic_container_index>=0];contexts.append(ContextSymbols(image).context(m.index,is_method=True))
    if contexts[0]['definition']!=parent['typedRead']['methodSpec'][0]:raise ValueError('referenceNullParam.caller-owned-context')
    reader=dict(entryRva=target-base,ownedWindows=windows,contexts=contexts)
    if reader!=fact['readValue']:raise ValueError('referenceNullParam.reviewed-complete-reader-source')
    typed=validate_read_value_context(image,*contexts,GenericEntries(image),fail=lambda k,e,a:(_ for _ in()).throw(ValueError('referenceNullParam.context:'+str((k,e,a))[:1000])))
    read=read_value(regions,target,{k:base+v for k,v in route['symbolRvas'].items()})
    return json.loads(json.dumps(dict(parent=parent,referenceCore=core,reader=read,typedContext=typed)))
