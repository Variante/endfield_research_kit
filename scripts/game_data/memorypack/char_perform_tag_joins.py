"""Re-prove the current one-element GameplayTag list and value-wrapper route."""
import hashlib,json,struct
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition,validate_generic_contexts
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
from scripts.game_data.memorypack.list_reference_sources import validate_list_element_context
from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
from scripts.game_data.memorypack.reference_conversion_sources import validate_conversion_context
from scripts.game_data.memorypack import primitive_param,scalar_param_native as scalar,char_perform_tag_sources as source
from scripts.game_data.memorypack.vector_layout import vector_recorder

def fail(k,e,a):
 if e!=a:raise ValueError(f'charPerformTagList.{k}:expected={str(e)[:240]}:actual={str(a)[:240]}')

def validate_one(image,pins,claim):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image);symbols=ContextSymbols(image);build=Build(image,pins);programs={};results=[]
 fail('grammar',dict(elementType='Beyond.Gameplay.Core.GameplayTag',memberCount=1,field='tagId',elementWireBytes=5,allowedCounts=[-1,0,1]),claim['grammar'])
 def owned(role,p):
  windows=[];regions=[];rows=[]
  for r in image.unwind_index.family(p-base)['ranges']:
   a,z=r['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,z-a);windows.append(dict(startRva=a,endRva=z,sha256=hashlib.sha256(raw).hexdigest().upper()));regions.append((base+a,raw));rows+=image.body_index._decode(base+a,z-a)
  programs[role]=dict(entryRva=p-base,windows=windows);fail('owned-source:'+role,claim['programs'][role],programs[role]);return regions,rows
 def target(regions,prefix):
  pattern=bytes.fromhex(prefix)+b'\xe8';found=[]
  for at,raw in regions:
   for i in range(len(raw)-len(pattern)-4+1):
    if raw[i:i+len(pattern)]==pattern:
     call=at+i+len(pattern)-1;found.append(call+5+int.from_bytes(raw[i+len(pattern):i+len(pattern)+4],'little',signed=True))
  fail('unique-callee:'+prefix,1,len(set(found)));return found[0]
 def method(owner,name):
  found=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==name];fail('unique-method:'+owner+'.'+name,1,len(found));return found[0]
 tag='Beyond.Gameplay.Core.GameplayTag';w,=[w for w in build.wrappers.values()if w.wrapped_type==tag];fail('tag-field',(tag,'int',16),ctx.field(tag+'::tagId'));fail('value',True,ctx.is_value_type(tag));fail('wrapper-field',(w.name,tag,16),ctx.field(w.name+'::__instance'));fail('member',[('tagId','int','scalar32')],[(m.name,m.declared_type,m.kind)for m in w.members]);sizep=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+ctx.index.types[tag].index*8);size=image.pe.bytes_at_va(sizep,16);fail('tag-boxed-size',20,int.from_bytes(size[:4],'little'))
 lm=method('MemoryPack.Formatters.ListFormatter`1','Deserialize');listreg=ge.resolve(lm.index,[tag],[]);lp=listreg['pointer'];lr,lrows=owned('tagList',lp);offsets=scalar.reader_offsets(image,'tagList');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 s=dict(indexed=target(lr,'488b4d2033d2488b89c0000000'),arrayAllocate=target(lr,'488bd6488bc8'),barrier=target(lr,'488d4b1048894310'),provider=target(lr,'488b4520488b88c0000000488b4918'),dispatcher=target(lr,'4c8d4c24584c8bc7498bd7'),add=target(lr,'488b45208bd3498bcd4c8b80c00000004d8b4030'))
 alloc,=[int(r['va'],16)-5 for r in lrows if bytes.fromhex(r['bytes'])==bytes.fromhex('488bd8')];raw=image.pe.bytes_at_va(alloc,5);fail('allocation-call-opcode',232,raw[0]);s['allocate']=alloc+5+int.from_bytes(raw[1:],'little',signed=True)
 for new in(True,False):results.append(dict(role='listOne',proof=source.list_one(lr,lp,offsets,s,new=new)))
 ar,arows=owned('add',s['add']);results.append(dict(role='add',proof=source.add(ar,s['add'])))
 lf=symbols.context(lm.declaring_type);lc=symbols.context(ctx.index.types['System.Collections.Generic.List`1'].index);validate_generic_contexts(image,[lf,lc],label='tagList');validate_list_element_context(image,lf,ge,fail=fail);validate_capacity_constructor_context(image,lf,lc,ge,fail=fail)
 # Actual compiler-selected direct Add body is proved above under its caller's exact owned slot6 MethodInfo.
 # A differently registered closed Add entry is not presumed equal or used as this wire proof.
 adapter=ctx.index.types['Beyond.MemoryPack.GenericMemoryPackFormatter`2'];entries={n:ge.resolve(method('Beyond.MemoryPack.GenericMemoryPackFormatter`2',n).index,[tag,'object'],[])for n in('Deserialize','DeserializeNotNull','ReadIsNull')};vp=entries['Deserialize']['pointer'];vr,vrows=owned('valueAdapter',vp);np=entries['DeserializeNotNull']['pointer'];nr,nrows=owned('valueNotNull',np);rp=entries['ReadIsNull']['pointer'];rr,_=owned('readNull',rp);dr,drows=owned('valueDispatcher',s['dispatcher']);prepare=target(dr,'488bda');nn=dict(context=target(nr,'488b4f20'),hotProvider=target(nr,'488b88c0000000488b4920'),dispatch=target(nr,'b9050000004c8d4c24404c8bc3488bd0'),indexed=target(nr,'ba08000000488b88c0000000'),conversion=target(nr,'488bd033c94c8bc3'))
 v=dict(main=vp,notNull=np,prepare=prepare,readNull=target(vr,'488b4720488bce488b90c0000000488b12'),typeHandle=target(vr,'33d2488bcb'),isValueType=target(vr,'33d2488bc8'),factory=target(vr,'488b4720488b88c0000000488b4958'));fail('actualReadNull',rp,v['readNull']);fail('actualNotNull',np,target(vr,'488b4f204c8bc0498bd64c8b89c0000000488bce4d8b4918'));fail('sameIndexed',s['indexed'],nn['indexed'])
 results.extend((dict(role='adapter',proof=source.adapter(vr,vp,v)),dict(role='matchedAdapter',proof=source.adapter(dr,s['dispatcher'],v,dispatch=True)),dict(role='notNull',proof=source.not_null(nr,np,nn)),dict(role='readNullPositive',proof=source.read_null_positive(rr,rp,target(rr,'488bd9c644243000')))))
 peek=target(rr,'488bd9c644243000');pr,_=owned('peek',peek);results.append(dict(role='peek',proof=source.peek_null(pr,peek,offsets)))
 comp=claim['composition'];validate_registered_formatter_composition(image,comp,label='tagList');face,=comp['interfaces'];td=ctx.index.types[w.name];sec=md.sections['interfaceOffsets'];at=sec.offset+td.interface_offsets_start*8;pairs=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8]));ordinal=pairs.index((face['interfaceTypeIndex'],face['interfaceOffset']));cr,crows=owned('conversion',nn['conversion']);results.append(dict(role='conversion',proof=source.conversion(cr,nn['conversion'],prepare,ordinal=ordinal)))
 gm=method(w.name,'GetValue');gp=image.method_pointer_va(gm);scalar.owned_method_abi(image,ctx,gm.index,td.index,(tag,17,False),[],'tagGetter');fail('getter-DWORD','8b4110c3',image.pe.bytes_at_va(gp,4).hex());programs['getter']=dict(entryRva=gp-base,windows=[dict(startRva=gp-base,endRva=gp-base+4,sha256=hashlib.sha256(image.pe.bytes_at_va(gp,4)).hexdigest().upper())],closedLeaf=True)
 rm=method(w.name,'Deserialize');wp=image.method_pointer_va(rm);wr,wrows=owned('wrapper',wp);primitive_param.reader_abi(image,ctx,rm,w);ws=dict(header=target(wr,'488d542430c644243000488bcf'),integer=target(wr,'488b1b488bcf'),allocate=s['allocate'],barrier=s['barrier'])
 for new in(True,False):results.append(dict(role='wrapper',proof=source.wrapper(wr,wp,ws,new=new)))
 primitive_param.object_header_source(image,vector_recorder(image)(ws['header']-base,fragments=True),offsets);scalar.integer_source(image,vector_recorder(image)(ws['integer']-base,fragments=True),offsets,'tagId',width=4)
 fw=md.methods[face['formatterDeserializeMethodIndex']];fp=image.method_pointer_va(fw);fr,frows=owned('wrapperForwarder',fp);calls=[int(r['va'],16)+5+int.from_bytes(bytes.fromhex(r['bytes'])[1:],'little',signed=True)for r in frows if bytes.fromhex(r['bytes'])[:1]==b'\xe8'];fail('forwarder-two-helpers',2,len(set(calls)));prove_zero_wrapper_forwarder(frows,dict(metadataInit=calls[0],classInit=calls[1]),wp);ds,dsrows=owned('wrapperDispatcher',nn['dispatch']);results.append(dict(role='wrapperSlot5',proof=deserialize_slot(ds,nn['dispatch'],prepare=prepare,callback=fp)))
 # The physical DWORD source is bound to the current declared value and Reader/output ABIs.
 sec=md.sections['genericContainers'];owner,count,is_method,start=struct.unpack_from('<iiii',md.buf,sec.offset+adapter.generic_container_index*16);fail('adapter-container',(adapter.index,2,0),(owner,count,is_method))
 for name,static,kinds in(('Deserialize',False,[(17,32,None),(19,32,start)]),('DeserializeNotNull',True,[(17,32,None),(19,32,start),(19,0,start+1)]),('ReadIsNull',True,[(17,32,None)])):
  m=method('Beyond.MemoryPack.GenericMemoryPackFormatter`2',name);fail('canonical-method-static:'+name,static,bool(m.flags&16));fail('canonical-method-return:'+name,'bool'if name=='ReadIsNull'else'void',ctx.type_name(m.return_type));ps=list(md.parameters_for(m));fail('canonical-arity:'+name,len(kinds),len(ps))
  for p,(kind,flags,var)in zip(ps,kinds,strict=True):
   raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16);fail('canonical-parameter-ABI:'+name,(kind,flags),(raw[10],raw[11]&127))
   if var is not None:fail('canonical-owned-VAR:'+name,var,int.from_bytes(raw[:8],'little'))
   else:fail('canonical-Reader-type:'+name,'MemoryPack.MemoryPackReader',ctx.type_name(p.type_index))
 ac=symbols.context(adapter.index);validate_generic_contexts(image,[ac],label='tagValue');validate_conversion_context(image,ac,ge,fail=fail)
 slots={r['relativeSlot']:r for r in ac['entries']}
 for slot,owner,name,ords in((0,ac['typeName'],'ReadIsNull',[0,1]),(3,ac['typeName'],'DeserializeNotNull',[0,1]),(11,'System.Activator','CreateInstance',[1])):
  r=slots[slot];args=r['methodArguments']if slot==11 else r['classArguments'];fail('adapter-slot',(owner,name),(r['typeName'],r['methodName']));fail('adapter-owned-VARs',[(adapter.index,n)for n in ords],[(a['parameterOwner']['typeIndex'],a['parameterOwner']['ordinal'])for a in args])
 fail('complete-source-domain',claim['programs'],programs)
 fail('list-registration',claim['listRegistration'],json.loads(json.dumps(listreg)))
 fail('canonical-value-registrations',claim['canonicalEntries'],json.loads(json.dumps(entries)))
 fail('owned-list-contexts',claim['listContexts'],[lf,lc]);fail('owned-adapter-context',claim['adapterContext'],ac)
 return dict(grammar=claim['grammar'],programs=len(results),helpers=dict(context=nn['context'],indexed=nn['indexed'],hotProvider=nn['hotProvider'],prepare=prepare,dispatch=nn['dispatch']),normalReturn=True,liveProviderSelectionProved=False)
