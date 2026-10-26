"""Current selected reference-list wire loop; no concrete provider selection claim."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
def flag(g,prefix='803d'):
 # RIP-relative CMP resolves from the complete instruction, including imm8.
 cell=g.relative(prefix)+1;g.take('00');return cell


def list_source(regions,entry,offsets,symbols,*,count=1,new=True,grow=False,count_limit=3):
 if type(count_limit)is not int or not 0<=count_limit<=256 or type(count)is not int or not -1<=count<=count_limit:raise ValueError('referenceList.witness-count')
 g=BytesPath(regions,entry);cur,rem,adv,used,total=(bytes((offsets[n],)).hex() for n in ('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
 g.take('4053','55','4155','4156','4157','4883ec30','837a'+rem+'04','4d8bf9','4d8bf0','48c744242000000000','4c8bea');g.branch('7d',True,1)
 g.take('498b45'+cur,'8b28','896c2468','418b5d'+rem,'83c3fc');g.branch('79',True,1)
 g.take('498345'+cur+'04','418345'+adv+'04','418345'+used+'04','41895d'+rem,'496345'+used,'498b4d'+total,'482bc8','4863c5','483bc8');g.branch('0f8c',False);g.take('83fdff','0f95c0','84c0');g.branch('0f84',count==-1)
 collectors=[];calls=[]
 if count==-1:
  collectors.append(flag(g,'833d'));g.take('49c70600000000');g.branch('74',True,1)
 else:
  g.take('4889742460','48897c2470','4c89642478','49833e00');g.relative('488d35');g.take('498b4720');g.branch('74',new,1)
  if new:
   g.take('488b88c0000000','488b01','f6803801000001');g.branch('75',True,1);g.take('488bc8');g.call(symbols['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False)
   g.take('498b4f20','488b91c0000000','488b4a08','4883792000');g.branch('75',True,1);g.take('498b4720','488b88c0000000','488b7908','85ed');g.branch('0f88',False);g.take('488b4720','488b80c0000000');g.branch('0f84',count==0)
   if count:
    g.take('488b4008','f6803801000001');g.branch('75',True,1);g.take('488bd5','488bc8');g.call(symbols['arrayAllocate']);collectors.append(flag(g,'833d'));g.take('48894310');g.branch('0f84',True)
   else:
    g.take('488b00','f6803801000001');g.branch('75',True,1);g.take('83b8e000000000');g.branch('75',True,1);g.take('488b4720','488b88c0000000','488b01','f6803801000001');g.branch('75',True,1);collectors.append(flag(g,'833d'));g.take('488b80b8000000','488b08','48894b10');g.branch('74',True,1)
   collectors.append(flag(g,'833d'));g.take('49891e');g.branch('74',True,1)
  else:
   g.take('488b90c0000000','498b1e','488b4210','4883782000');g.branch('75',True,1);g.take('498b4720','488bcb','488b90c0000000','488b5210');g.call(symbols['clear']);g.jump('e9')
  provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1);g.take('498b4720','488b88c0000000','488b4918');g.call(symbols['provider']);g.take('33f6','4c8be0','85ed');g.branch('0f8e',count==0)
  if count:
   g.take('90');loop=g.at
   for i in range(count):
    if g.at!=loop:raise ValueError('referenceList.same-loop-entry')
    g.take('48c744242000000000','4d85e4');g.branch('0f84',False);g.take('498b0c24');g.call(symbols['prepare']);g.take('4d8b0c24','4c8d442420','498bd5','498bcc','498b8190010000','4d8b8998010000');calls.append(g.at);g.take('ffd0','498b1e','488b6c2420','4885db');g.branch('0f84',False)
    g.take('498b4720','488b88c0000000','488b4130','4883782000');g.branch('75',True,1);g.take('498b4720','488b5310','488b88c0000000','488b7930','ff431c','48634b18','4885d2');g.branch('0f84',False);g.take('3b4a18');g.branch('72',not grow,1)
    if grow:
     g.take('488b4720','4c8b80c0000000','498b4058','4883782000');g.branch('75',True,1);g.take('488b4720','488bd5','488bcb','4c8b80c0000000','4d8b4058');g.call(symbols['grow']);g.jump('eb',1)
    else:
     g.take('8d4101','894318','3b4a18');g.branch('0f83',False);collectors.append(flag(g,'833d'));g.take('48896cca20');g.branch('74',True,1)
    g.take('ffc6','3b742468');g.branch('0f8c',i+1<count)
  g.take('488b7c2470','4c8b642478','488b742460')
 g.take('4883c430','415f','415e','415d','5d','5b','c3')
 if len(set(collectors))>1:raise ValueError('referenceList.shared-disabled-collector')
 return dict(selectedBytes=g.seen,countWitness=count,newList=new,elementCallbackSites=calls,headerBytes=4,callbackAbi=dict(reader='r13',output='rsp+32',receiver='r12',methodInfoSlot=408,callbackSlot=400),growthDelegate=grow,arrayReferenceStride=8,initialElementOutput=0,normalReturn=True,disabledCollectorCells=collectors,wholeOwnerAdmitted=False)


def pooled_string(regions,entry,symbols,*,mode='lookup'):
 if mode not in('lookup','null','empty'):raise ValueError('pooledStringFormatter.mode')
 g=BytesPath(regions,entry);g.take('48895c2420','57','4883ec20');flag(g);g.take('498bf8','488bda');g.branch('75',True,1)
 if g.relative('488b05')!=symbols['pool']:raise ValueError('pooledStringFormatter.pool-cell')
 g.take('4889742440','488b88b8000000','48833900');g.branch('0f84',False);g.take('48896c2430','837b3004');g.branch('7d',True,1)
 g.take('488b4350','8b30','8b6b30','83c5fc');g.branch('79',True,1);g.take('4883435004','83434004','83434404','896b30','488b6c2430','83fefe');g.branch('74',mode=='null',1)
 if mode=='null':g.take('33c0');g.jump('eb',1)
 else:
  g.take('83feff');g.branch('74',mode=='empty',1)
  if mode=='empty':
   if g.relative('488b05')!=symbols['empty']:raise ValueError('pooledStringFormatter.empty-cell')
   g.jump('eb',1)
  else:
   if g.relative('488b05')!=symbols['pool']:raise ValueError('pooledStringFormatter.same-pool-cell')
   g.take('488b88b8000000','488b19','4885db');g.branch('74',False,1);g.take('4533c0','8bd6','488bcb');g.call(symbols['lookup']);g.jump('eb',1)
 collector=flag(g,'833d');g.take('488907');g.branch('74',True,1);g.take('488b742440','488b5c2448','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,mode=mode,wireBytes=4,outputBytes=8,reader='incoming RDX',output='incoming R8',signedIndex='ESI',disabledCollectorCell=collector,normalReturn=True,condition='Initialized matching nonnull StringPool, buffered disjoint Reader and output, mode -2/-1/nonnegative respectively, normal pool lookup, disabled collector; pool-absent inline UTF8, refill/error and live formatter selection excluded.')

"""Initialized local typed formatter registration transfer; no execution claim."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def local_registration(regions,entry,s):
 g=BytesPath(regions,entry)
 if g.relative('488b0d')!=s['formatterCell']:raise ValueError('stringList.registration-formatter-class')
 g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False);flag=g.relative('443825');g.branch('0f85',True)
 provider=g.relative('488b0d');g.take('4439a1e0000000');g.branch('75',True,1)
 if g.relative('488b15')!=s['registrationCell']:raise ValueError('stringList.registration-method-info')
 g.take('488bcf');g.call(s['forceRegister']);return dict(selectedBytes=g.seen,metadataReadyFlag=flag,providerClassCell=provider,formatter='unchanged fresh allocator RAX preserved in nonvolatile RDI',registrationContext='actual closed ForceRegister<string> MethodSpec',condition='Control reaches this owned local block with R12 zero and initialization flag set; matching typed allocation returns exact class normally; class/provider ready, normal Win64 callees. Complete initializer reachability, execution, dictionary state and live selection remain separate.')

def force_register(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','48837a3800','488bda','488bf1');g.branch('75',True,1)
 provider=g.relative('488b05');g.take('83b8e000000000');g.branch('75',True,1);type_cell=g.relative('488b0d');g.take('488b80b8000000','488b5b38','83b9e000000000','488b7818','488b1b');g.branch('75',True,1);g.take('33d2','488bcb');g.call(s['typeFromHandle']);g.take('4885ff');g.branch('75',True,1)
 cell=g.relative('4c8b0d');g.take('4c8bc6','488bd0','488bcf','488b5c2430','488b742438','4883c420','5f')
 if g.relative('e9')!=s['setItem']:raise ValueError('stringList.force-register-dictionary-tail')
 return dict(selectedBytes=g.seen,providerClassCell=provider,typeClassCell=type_cell,setItemCell=cell,dictionaryStaticOffset=24,originalTypeContextSlot=0,formatter='unchanged incoming RCX through RSI to R8',key='TypeFromHandle of own method context slot0',output='same dictionary receiver+type key+incoming formatter reach set_Item with its exact MethodInfo',condition='Initialized method/provider/Type contexts and nonnull matching formatter dictionary, normal TypeFromHandle and tail ABI. Dictionary write effects/contents, initializer execution and live formatter selection remain separate.')

def dictionary_set_item(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2418','55','57','4156','4883ec40','48c744246800000000','498be9','4d8bf0','488bda','488bf9','4885d2');g.branch('0f84',False)
 g.take('4889742460','488b7118','4885f6');g.branch('0f84',False);g.take('498b4920','ba0c000000','488b89c0000000');g.call(s['indexed']);g.take('488bd0','b901000000','4c8bcb','4c8bc6');g.call(s['hash'])
 g.take('488b4d20','8bf0','488b91c0000000','488b4a78','4883792000');g.branch('0f84',False);g.take('488b4d20','4d8bce','448bc6','488b91c0000000','488bcf','488b4278','488bd3','4889442438','488d442468','4889442430','c644242801','c644242001');g.call(s['tryAddInternal'])
 g.take('488b742460','488b5c2470','4883c440','415e','5f','5d','c3');return dict(selectedBytes=g.seen,receiver='unchanged incoming RCX via RDI',key='unchanged incoming RDX via RBX',value='unchanged incoming R8 via R14',contextSlot=15,updateIfExists=True,acquireLock=True,normalReturn=True,condition='Nonnull key/comparer and ready coherent closed dictionary contexts; normal hash and TryAddInternal/update return. Internal mutation, equality, dictionary contents and runtime execution remain conditional.')

"""Own a literal reference-list caller, cached getter and exact field transfer."""
from scripts.game_data.memorypack.record_sources import ordered_record
from scripts.game_data.il2cpp.reference_field_programs import reader_setup,prove_cached_field_setter
from scripts.game_data.memorypack.scalar_param_native import owned_method_abi,ordinary
from scripts.game_data.memorypack.wrapper_members import INSTANCE_FIELD_NAMES
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.string_source_instructions import decode_string_source_instructions
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data.il2cpp.zero_wrapper_programs import _flag,_init,_exact,_rip
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def cached_list_getter(regions,entry,*,base_slot,cache_slot,cast,barrier,metadata_init,refresh='empty'):
 if refresh not in('empty','different','coherent'):raise ValueError('stringList.cache-path')
 b=bytes((base_slot,)).hex();c=bytes((cache_slot,)).hex();g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');g.relative('803d');g.take('00','488bf9');g.branch('75',True,1);g.take('48837f'+c+'00');g.branch('74',refresh=='empty',1)
 if refresh!='empty':g.take('488b47'+b,'483947'+c);g.branch('74',refresh=='coherent',1)
 cell=None
 if refresh!='coherent':
  g.take('488b5f'+b);cell=g.relative('488b15');g.take('488bcb');g.call(cast);g.take('488947'+c,'488bcb');second=g.relative('488b15');g.call(cast);g.take('488d4f'+c);g.call(barrier)
  if cell!=second:raise ValueError('stringList.distinct-cast-context')
 g.take('488b47'+c,'488b5c2430','4883c420','5f','c3');return dict(selectedBytes=g.seen,castCellVA=cell,baseSlot=base_slot,cacheSlot=cache_slot,path=refresh,condition='Initialized metadata, stable typed heap, normally returning compatible cast and barrier; coherent existing cache or successful refresh. Predicate and execution remain conditional.')


def compatible_list_cast(regions,entry,assignable,*,null=False):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','4885c9');g.branch('74',null,1)
 if null:g.take('33c0')
 else:g.take('488b09');g.call(assignable);g.take('33c9','84c0','480f44d9','488bc3')
 g.take('4883c420','5b','c3');return dict(selectedBytes=g.seen,null=null,conditionalUnchangedCompatibleReference=True,predicateOutcomeProved=False)


def parent_field(build,wrapper_name,field):
 image=build.image;md=image.metadata;ctx=NativeReferenceContext(image);base=image.pe.image_base;w=build.wrappers[wrapper_name];member,=[m for m in w.members if m.name==field]
 if(member.kind,member.declared_type)!=('list','System.Collections.Generic.List`1<string>'):raise ValueError('stringList.parent-declaration')
 def source(pointer):
  regions=[(base+p['runtimeTriple'][0],image.pe.bytes_at_va(base+p['runtimeTriple'][0],p['runtimeTriple'][1]-p['runtimeTriple'][0]))for p in image.unwind_index.family(pointer-base)['ranges']]
  rows=[z for at,raw in regions for z in decode_string_source_instructions(image.mapper,raw,at)];return regions,rows
 fact=ordered_record(build,dict(wrapperName=w.name,typeName=w.wrapped_type,fields=[[m.name,m.declared_type]for m in w.members]));plan,=[r for r in fact['orderedReads']if r['field']==field];body=image.body_index.body(w.name,'Deserialize');_,rows=source(body.pointer);read,=[r for r in rows if int(r['va'],16)-base==plan['readRva']];n,reader,holder,receiver=reader_setup(rows,read);transfer=rows[n+1:n+6]
 if [r['text']for r in transfer]!=[f'test {receiver}, {receiver}',transfer[1]['text'],'xor r8d, r8d','mov rdx, rax',f'mov rcx, {receiver}']:raise ValueError('stringList.parent-unchanged-reference')
 raw=bytes.fromhex(transfer[1]['bytes'])
 if not(len(raw)==2 and raw[0]==0x74 or len(raw)==6 and raw[:2]==b'\x0f\x84'):raise ValueError('stringList.parent-nonnull-guard')
 if int(rows[n+6]['va'],16)-base!=plan['transferRva']:raise ValueError('stringList.parent-setter-call')
 target=ctx.field(w.wrapped_type+'::'+field);holders=[f for f in md.fields_for(md.types[w.type_definition])if md.string(f.name_index)in INSTANCE_FIELD_NAMES and not ctx.field_attributes(f.type_index)&16 and ctx.type_name(f.type_index)==w.wrapped_type]
 if len(holders)!=1:raise ValueError('stringList.parent-unique-owned-holder')
 held=ctx.field(w.name+'::'+md.string(holders[0].name_index));ordinary(image,ctx.type_pointer(holders[0].type_index),18,'stringList.original-holder',reference=True)
 if target[:2]!=(w.wrapped_type,member.declared_type)or held[:2]!=(w.name,w.wrapped_type)or not 16<=held[2]<128 or ctx.is_value_type(w.wrapped_type):raise ValueError('stringList.parent-owned-field')
 chain=[];current=ctx.parent(w.name);bases=[]
 while current in ctx.index.types and len(chain)<16:
  chain.append(current)
  for f in md.fields_for(ctx.index.types[current]):
   if md.string(f.name_index)=='__instance'and not ctx.field_attributes(f.type_index)&16:
    ordinary(image,ctx.type_pointer(f.type_index),18,'stringList.base-instance',reference=True);bases.append(ctx.field(current+'::__instance'))
  current=ctx.parent(current)
 if len(bases)!=1:raise ValueError('stringList.parent-unique-base-instance')
 inherited=bases[0]
 original=w.wrapped_type;original_chain=[]
 while original!=inherited[1]and original in ctx.index.types and len(original_chain)<16:
  original=ctx.parent(original);original_chain.append(original)
 if original!=inherited[1]or not 16<=inherited[2]<128 or inherited[2]==held[2]:raise ValueError('stringList.parent-base-layout')
 method=md.methods[member.method_index];owned_method_abi(image,ctx,method.index,method.declaring_type,('void',1,False),[(member.declared_type,21,True)],'stringList.setter');pointer=image.method_pointer_va(method);_,setter_rows=source(pointer);getter,=[m for m in md.methods_for(md.types[w.type_definition])if md.string(m.name_index)=='get___instance'];owned_method_abi(image,ctx,getter.index,getter.declaring_type,(w.wrapped_type,18,True),[],'stringList.getter');gp=image.method_pointer_va(getter);getter_regions,gr=source(gp)
 def direct(r):
  if bytes.fromhex(r['bytes'])[:1]!=b'\xe8':raise ValueError('stringList.direct-call')
  return control_transfer(r)['target']
 cast=direct(gr[17]);barrier=direct(gr[23]);getter_symbols=dict(base_slot=inherited[2],cache_slot=held[2],cast=cast,barrier=barrier,metadata_init=direct(gr[7]));gp_results=[cached_list_getter(getter_regions,gp,**getter_symbols,refresh=mode)for mode in('empty','different','coherent')];gp_result=gp_results[0];usage=derive_typed_usage_context(image,int(gr[15]['va'],16)-base,label='stringList.getter-cast')
 if (usage['tag'],usage['typeName'],base+usage['usageCellRva'])!=(1,w.wrapped_type,gp_result['castCellVA']):raise ValueError('stringList.getter-typed-cast')
 cr,cast_rows=source(cast);calls=[r for r in cast_rows if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
 if len(calls)!=1:raise ValueError('stringList.cast-predicate')
 cast_proofs=[compatible_list_cast(cr,cast,direct(calls[0]),null=null)for null in(False,True)];setter_proof=prove_cached_field_setter(setter_rows,field_offset=target[2],mode='reference-return',symbols=dict(getter=gp,nullThrow=direct(setter_rows[7]),barrier=barrier));build.prove_reader_clone_target(base+plan['targetRva'],'MemoryPack.MemoryPackReader.ReadPackable',result_abi='reference')
 return dict(wrapperName=w.name,typeName=w.wrapped_type,field=field,sourcePlan=fact,selectedPlan=plan,originalField=list(target),wrapperHolder=list(held),inheritedHolder=list(inherited),ancestorChain=chain,originalAncestorChain=original_chain,sourceArguments=dict(reader=reader,holder=holder,receiver=receiver),setterMethod=[method.index,w.name,md.string(method.name_index),pointer-base],getterMethod=[getter.index,w.name,'get___instance',gp-base],getterSymbols={k:(v-base if k in('cast','barrier','metadata_init')else v)for k,v in getter_symbols.items()},getterProofs=gp_results,getterCastUsage=usage,castEntryRva=cast-base,castPredicateRva=direct(calls[0])-base,castProofs=cast_proofs,setterProof=setter_proof)


"""Fresh typed joins for a conditional literal pooled string-list source."""
import json,struct
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts,validate_typed_usage_context,_vtable
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.memorypack import scalar_param_native as scalar,pooled_source_helper,int_list_sources
from scripts.game_data.memorypack.list_reference_sources import validate_list_element_context
from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets

def validate_components(image,fact):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);entries=GenericEntries(image);programs={};regions={}
 def fail(k,e,a):raise ValueError(f'pooledStringList.{k}:expected={str(e)[:220]}:actual={str(a)[:220]}')
 def need(k,e,a):
  if e!=a:fail(k,e,a)
 for r in fact['programs']:
  expected=sorted(tuple(p['runtimeTriple'][:2])for p in image.unwind_index.family(r['entryRva'])['ranges']);need('owned-'+r['role'],expected,sorted((p['startRva'],p['endRva'])for p in r['windows']));image.check_windows(r['windows'],label='pooledStringList');programs[r['role']]=r;regions[r['role']]=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in r['windows']]
 def args(role):return regions[role],base+programs[role]['entryRva']
 for row in fact['methods']:image.validate_method_row(row,label='pooledStringList')
 offsets=scalar.reader_offsets(image,'pooledStringList');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16;need('reader-owned-fields',dict(currentPtr=80,bufferLength=48,advancedCount=64,consumed=68,totalLength=24),offsets)
 contexts=fact['contexts'];validate_generic_contexts(image,contexts,label='pooledStringList');lf,ls,force,provider,dictionary=contexts
 need('context-owners',[('MemoryPack.Formatters.ListFormatter`1',None),('System.Collections.Generic.List`1',None),('MemoryPack.MemoryPackFormatterProvider','ForceRegister'),('MemoryPack.MemoryPackFormatterProvider','GetFormatter'),('System.Collections.Concurrent.ConcurrentDictionary`2',None)],[(c['typeName'],c['methodName'])for c in contexts])
 validate_list_element_context(image,lf,entries,fail=fail);validate_capacity_constructor_context(image,lf,ls,entries,fail=fail);validate_list_formatter_base_context(image,lf,entries,fail=fail)
 entry=fact['listEntry'];need('canonical-list-registration',entry['registration'],json.loads(json.dumps(entries.resolve(entry['definition'],['object'],[]))));need('list-entry',programs['list']['entryRva'],entry['registration']['pointer']-base);need('absent-string-list-registration',[],entries.observe(entry['definition'],['string'],[]))
 lm=md.methods[entry['definition']];need('list-method',('MemoryPack.Formatters.ListFormatter`1','Deserialize',False,5,2),(image.type_name(lm.declaring_type),md.string(lm.name_index),bool(lm.flags&16),lm.slot,lm.parameter_count));_vtable(image,lm.declaring_type,5,lm.index,'pooledStringList')
 for p,name,kind in zip(md.parameters_for(lm),('MemoryPack.MemoryPackReader',ctx.type_name(list(md.parameters_for(lm))[1].type_index)),(17,21),strict=True):
  raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16);need('list-byref-ABI',(kind,32),(raw[10],raw[11]))
 need('list-void','void',ctx.type_name(lm.return_type))
 strings=validate_string_components(image,fact)
 s={k:base+v for k,v in fact['listSymbols'].items()};paths=[list_source(*args('list'),offsets,s,count=count,new=new,grow=grow)for count in(-1,0,1,2,3)for new in(False,True)for grow in(False,True)]
 td=ctx.index.types['MemoryPack.MemoryPackFormatterProvider']
 factory=fact['factory'];image.check_windows(factory['windows'],label='pooledStringList');image.check_instruction_windows(factory['instructions'],label='pooledStringList');image.check_instruction_windows(factory['receiverInstructions'],label='pooledStringList')
 for u in factory['usages']:validate_typed_usage_context(image,u,label='pooledStringList')
 need('open-list-factory',['System.Collections.Generic.List`1','MemoryPack.Formatters.ListFormatter`1'],[u['typeName']for u in factory['usages'][:2]]);region=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in factory['windows']];mapped=int_list_sources.factory_pair(region,base+factory['entryRva'],type_handle=base+factory['typeHandleRva'],add=base+factory['addRva']);need('factory-context-cells',[base+u['usageCellRva']for u in factory['usages']],[mapped[k]for k in('keyTypeCell','valueTypeCell','addMethodInfoCell')])
 fu=factory['usages'][2];need('factory-dictionary-add',('System.Collections.Generic.Dictionary`2','Add',['System.Type','System.Type'],[]),(fu['typeName'],fu['methodName'],fu['classArguments'],fu['methodArguments']));need('factory-actual-add',base+factory['addRva'],entries.resolve(fu['methodSpec'][0],['object','object'],[])['pointer'])
 from scripts.game_data.il2cpp.consumer_instructions import decode_consumer_instructions
 receiver=factory['receiverInstructions'];start=receiver[0][0];raw=b''.join(bytes.fromhex(r[1])for r in receiver);need('factory-receiver-contiguous',raw,image.pe.bytes_at_va(base+start,len(raw)));int_list_sources.factory_receiver(decode_consumer_instructions(image.mapper,raw,base+start));u=fact['factoryReceiverUsage'];validate_typed_usage_context(image,u,label='pooledStringList');need('factory-static-owner','MemoryPack.MemoryPackFormatterProvider',u['typeName']);need('factory-static-load',receiver[-3][0],u['instructionRva'])
 collection,=[f for f in md.fields_for(td)if md.string(f.name_index)=='CollectionFormatters'];need('collection-factory-field',('System.Collections.Generic.Dictionary`2<System.Type,System.Type>',True,8),(ctx.type_name(collection.type_index),bool(ctx.field_attributes(collection.type_index)&16),runtime_type_field_offsets(md,image.pe,image.registration,td.index)['CollectionFormatters']))
 build=Build(image,fact['nativeInputs']);parent=parent_field(build,fact['parent']['wrapperName'],fact['parent']['field']);need('actual-typed-parent-source',fact['parent'],json.loads(json.dumps(parent)))
 return dict(selectedPrograms=len(paths)+strings['selectedPrograms'],wireCountBytes=4,wireElementBytes=4,elementManagedBytes=8,nullCount=-1,closedStringRegistrationPresent=False,liveProviderSelectionProved=False,wholeOwnerAdmitted=False)


def validate_string_components(image,fact):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);entries=GenericEntries(image);programs={};regions={}
 def fail(k,e,a):raise ValueError(f'pooledStringCallback.{k}:expected={str(e)[:220]}:actual={str(a)[:220]}')
 def need(k,e,a):
  if e!=a:fail(k,e,a)
 for r in fact['programs']:
  if r['role']not in('string','initializer','register','setItem','backend'):continue
  expected=sorted(tuple(p['runtimeTriple'][:2])for p in image.unwind_index.family(r['entryRva'])['ranges']);need('owned-'+r['role'],expected,sorted((p['startRva'],p['endRva'])for p in r['windows']));image.check_windows(r['windows'],label='pooledStringCallback');programs[r['role']]=r;regions[r['role']]=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in r['windows']]
 def args(role):return regions[role],base+programs[role]['entryRva']
 force,provider,dictionary=fact['contexts'][2:];validate_generic_contexts(image,[force,provider,dictionary],label='pooledStringCallback');paths=[]
 need('context-owners',[('MemoryPack.MemoryPackFormatterProvider','ForceRegister'),('MemoryPack.MemoryPackFormatterProvider','GetFormatter'),('System.Collections.Concurrent.ConcurrentDictionary`2',None)],[(c['typeName'],c['methodName'])for c in(force,provider,dictionary)])
 ps={e['relativeSlot']:e for e in provider['entries']};need('provider-context-slots',[0,1],sorted(ps));need('provider-own-MVAR',provider['definition'],ps[0]['type']['parameterOwner']['methodIndex']);need('provider-formatter-own-MVAR',provider['definition'],ps[1]['type']['classArguments'][0]['parameterOwner']['methodIndex'])
 pool_raw=(CONTRACTS_DIR/'memorypack_pooled_string_reader_native.json').read_bytes();pool=json.loads(pool_raw);pooled_source_helper.validate_on_image(image,base+pool['targetRva'],fact['nativeInputs']);symbols=dict(pool=base+pool['inlineSymbols']['pool'],empty=base+pool['inlineSymbols']['empty'],lookup=base+pool['lookupRva']);paths.extend(pooled_string(*args('string'),symbols,mode=mode)for mode in('lookup','empty','null'))
 owner=ctx.index.types['MemoryPack.BeyondStringFormatter'];need('closed-string-parent','MemoryPack.MemoryPackFormatter`1<string>',ctx.parent('MemoryPack.BeyondStringFormatter'));need('formatter-reference',False,ctx.is_value_type('MemoryPack.BeyondStringFormatter'));sm,=[m for m in md.methods_for(owner)if md.string(m.name_index)=='Deserialize'];need('string-source-entry',base+programs['string']['entryRva'],image.method_pointer_va(sm));need('string-slot-ABI',(5,False,2,'void'),(sm.slot,bool(sm.flags&16),sm.parameter_count,ctx.type_name(sm.return_type)));_vtable(image,owner.index,5,sm.index,'pooledStringList')
 for p,name,kind in zip(md.parameters_for(sm),('MemoryPack.MemoryPackReader','string'),(17,14),strict=True):
  raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16);need('string-byref-parameter',(name,kind,32),(ctx.type_name(p.type_index),raw[10],raw[11]))
 # Actual closed MethodInfo is supplied by owned native code; folded aliases remain observations.
 alloc=fact['allocationUsage'];usage=fact['registrationUsage'];validate_typed_usage_context(image,alloc,label='pooledStringList');validate_typed_usage_context(image,usage,label='pooledStringList');need('allocated-type',('MemoryPack.BeyondStringFormatter',1),(alloc['typeName'],alloc['tag']));need('actual-closed-registration',('MemoryPack.MemoryPackFormatterProvider','ForceRegister',[],['string']),(usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments']));need('absent-closed-register-entry',[],entries.observe(usage['methodSpec'][0],[],['string']))
 observation=fact['forceObservation'];need('folded-registration-observation',observation,json.loads(json.dumps(entries.observe(usage['methodSpec'][0],[],['object']))));need('observed-register-source',[base+programs['register']['entryRva']],[r['pointer']for r in observation]);aliases=observation[0]['methodDefinitionIndices'];need('folded-register-owners',['MemoryPack.MemoryPackFormatterProvider']*2,[image.type_name(md.methods[i].declaring_type)for i in aliases]);need('explicit-folded-aliases',['ForceRegister','Register'],sorted(md.string(md.methods[i].name_index)for i in aliases))
 slot,=force['entries'];need('register-context',('ForceRegister',True,0,1,usage['methodSpec'][0],0),(force['methodName'],force['isMethod'],slot['relativeSlot'],slot['kind'],slot['type']['parameterOwner']['methodIndex'],slot['type']['parameterOwner']['ordinal']))
 reg={k:base+v for k,v in fact['registerSymbols'].items()};need('allocation-load',alloc['instructionRva'],fact['localEntryRva']);local=local_registration(regions['initializer'],base+fact['localEntryRva'],reg);registered=force_register(*args('register'),reg);paths.extend((local,registered,dictionary_set_item(*args('setItem'),reg)))
 pu=fact['providerUsage'];validate_typed_usage_context(image,pu,label='pooledStringList');need('typed-provider-class','MemoryPack.MemoryPackFormatterProvider',pu['typeName']);need('actual-provider-class-cell',base+pu['usageCellRva'],registered['providerClassCell'])
 need('own-allocation-method-cells',(base+alloc['usageCellRva'],base+usage['usageCellRva']),(reg['formatterCell'],reg['registrationCell']));need('provider-cell-join',local['providerClassCell'],registered['providerClassCell'])
 actual=usage['methodSpec'][0];rm=md.methods[actual];need('ForceRegister-signature',('void',True,1),(ctx.type_name(rm.return_type),bool(rm.flags&16),rm.parameter_count));arg,=md.parameters_for(rm);raw=image.pe.bytes_at_va(ctx.type_pointer(arg.type_index),16);need('register-formatter-generic-kind',(21,0),(raw[10],raw[11]));arg_type=ctx.type_name(arg.type_index);need('register-formatter-type',f"MemoryPack.MemoryPackFormatter`1<{slot['typeName']}>",arg_type)
 du=fact['dictionaryUsage'];validate_typed_usage_context(image,du,label='pooledStringList');need('typed-dictionary-setter',('System.Collections.Concurrent.ConcurrentDictionary`2','set_Item',['System.Type','MemoryPack.IMemoryPackFormatter'],[]),(du['typeName'],du['methodName'],du['classArguments'],du['methodArguments']));need('actual-dictionary-context-cell',base+du['usageCellRva'],registered['setItemCell'])
 ds={e['relativeSlot']:e for e in dictionary['entries']};helper=ds[15];need('dictionary-update-helper',('System.Collections.Concurrent.ConcurrentDictionary`2','TryAddInternal'),(helper['typeName'],helper['methodName']));need('dictionary-owned-VARs',[0,1],[a['parameterOwner']['ordinal']for a in helper['classArguments']]);need('dictionary-owned-VAR-container',[dictionary['definition']]*2,[a['parameterOwner']['typeIndex']for a in helper['classArguments']]);update=md.methods[helper['methodSpec'][0]];params=list(md.parameters_for(update));need('actual-update-flags',['updateIfExists','acquireLock'],[md.string(params[i].name_index)for i in(3,4)])
 named=fact['providerField'];td=ctx.index.types['MemoryPack.MemoryPackFormatterProvider'];field,=[f for f in md.fields_for(td)if md.string(f.name_index)=='formatters'];need('provider-field',('System.Collections.Concurrent.ConcurrentDictionary`2<System.Type,MemoryPack.IMemoryPackFormatter>',True,24),(ctx.type_name(field.type_index),bool(ctx.field_attributes(field.type_index)&16),runtime_type_field_offsets(md,image.pe,image.registration,td.index)['formatters']));need('reviewed-provider-field','formatters',named)
 calls={k:base+v for k,v in fact['backendCalls'].items()};backend=int_list_sources.backend(*args('backend'),calls);need('same-static-provider-dictionary',registered['providerClassCell'],backend['providerClassCell']);bu=fact['backendUsage'];validate_typed_usage_context(image,bu,label='pooledStringList');need('typed-dictionary-lookup',('TryGetValue',du['classArguments']),(bu['methodName'],bu['classArguments']));need('backend-method-cell',base+bu['usageCellRva'],backend['methodInfoCell'])
 need('pool-contract-bookend',pool_raw,(CONTRACTS_DIR/'memorypack_pooled_string_reader_native.json').read_bytes())
 return dict(selectedPrograms=len(paths),stringFormatterSlot=5,wireBytes=4,managedReferenceBytes=8,liveProviderSelectionProved=False,wholeOwnerAdmitted=False)
