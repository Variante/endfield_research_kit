"""Exact OperaSegment VALUE17 array source, independent of element grammar.

The actual Reader returns a fresh array reference after calling its own byref
overload. Indexed element addresses have stride16 and data offset32, proved
separately from the nominal boxed layout. Neither managed16 nor an array count
supplies the OperaSegment MC2 callback, its ParamKeyValue array, or a parent.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.EncounterData+OperaSegment'
ENUM='Beyond.Gameplay.EncounterData+OperaType'
PARAMETERS='Beyond.Gameplay.ParamKeyValue[]'
SCHEMA='endfield.story-opera-value-array-source.v1'


def need(key,condition):
 if not condition:raise ValueError('storyOperaArray.'+key)


def return_program(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2408','57','4883ec20','48837a3800','488bda','488bf9');g.branch('75',True,1)
 g.take('4c8b4338','488d542438','48c744243800000000','488bcf','4d8b00')
 site=g.at;target=g.relative('e8');g.take('488b442438','488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,byrefCallInstructionVa=site,byrefTargetVa=target,
  initiallyNullOutputProved=True,arrayLocalEntryRspOffset=16,entryRspRestored=True,
  sameReader=True,unchangedArrayReferenceReturnedInRax=True,normalReturn=True)


def byref_program(regions,entry,*,count):
 need('literal-count-witness',type(count)is int and -1<=count<=3)
 g=BytesPath(regions,entry);symbols={};calls=[];callbacks=[];backedge=None;provider=None
 def call(role):
  site=g.at;target=g.relative('e8');need('same-helper:'+role,role not in symbols or symbols[role]==target)
  symbols[role]=target;calls.append(dict(role=role,instructionVa=site,targetVa=target))
 g.take('48895c2410','55','56','57','4883ec20','4983783800','498bd8','488bfa','488be9');g.branch('75',True,1)
 g.take('33f6','89742450','488d542450','488bcd');call('header');g.take('84c0');g.branch('0f85',count!=-1)
 if count==-1:g.take('488bcf','488937');call('barrier')
 else:
  g.take('4c89742440','448b742450','4585f6');g.branch('0f84',count==0)
  if count==0:
   g.take('488b4b38','488b4908');call('empty');g.take('488bcf','488907');call('barrier')
  else:
   # The actual return overload has just initialized this exact array local.
   g.take('483937');g.branch('74',True,1)
   g.take('488b4b38','ba02000000');call('context');g.take('498bd6','488bc8');call('allocate')
   g.take('488bcf','488907');call('barrier')
   site=g.at;cell=g.relative('488b0d');provider=dict(instructionVa=site,cellVa=cell)
   g.take('39b1e0000000');g.branch('75',True,1)
   g.take('488b4b38','488b4918');call('provider');g.take('488bd8','4585f6');g.branch('7e',False,1)
   loop=g.at
   for index in range(count):
    need('same-complete-loop-entry',g.at==loop)
    g.take('488b0f','4885c9');g.branch('74',False,1)
    g.take('4885db');g.branch('74',False,1)
    g.take('4863d6');call('index');g.take('4c8bc8','4c8bc5','488bd3')
    callbacks.append(g.at);call('dispatch')
    g.take('ffc6','413bf6');backedge=g.at;g.branch('7c',index+1<count,1)
   g.jump('eb',1)
  g.take('4c8b742440');g.jump('e9')
 g.take('488b5c2448','4883c420','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,countWitness=count,newArray=True,elementCallbackSites=callbacks,
  symbols=symbols,helperCalls=calls,actualBackedgeVa=backedge,providerClassUsage=provider,
  headerBytes=4,elementManagedBytes=16,elementWireBytes=None,initiallyNullArrayRequired=True,
  savedCount='r14d',index='esi',entryRspRestored=True,allIntegerNonvolatilesRestored=True,normalReturn=True,
  frame=dict(entryRspDelta=-56,shadowRspRange=[0,32],headerEntryHome=[24,28],
   savedEntryHomes=dict(rbx=[16,24],rbp=[-8,0],rsi=[-16,-8],rdi=[-24,-16]),
   positiveOnlyR14EntryHome=[8,16]),elementGrammarAdmitted=False)


def index_program(regions,entry):
 g=BytesPath(regions,entry);g.take('4883ec28','3b5118');g.branch('72',True,1)
 g.take('488d4202','48c1e004','4803c1','4883c428','c3')
 return dict(selectedBytes=g.seen,arrayDataOffset=32,elementManagedBytes=16,
  unsignedIndexWithinLengthRequired=True,normalReturn=True,entryRspRestored=True,
  result='incoming array RCX +32+16*zero-extended nonnegative EDX index')


def dispatch_program(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec20','488b0a','498bd9','498bf8','488bf2')
 prepare=g.relative('e8')
 g.take('4c8b0e','4c8bc3','488bd7','488bce','498b8190010000','4d8b8998010000',
  '488b5c2430','488b742438','4883c420','5f','48ffe0')
 return dict(selectedBytes=g.seen,prepareTargetVa=prepare,formatterSlot=5,
  callbackArguments=dict(rcx='same formatter',rdx='same Reader',r8='actual indexed OperaSegment16 output',r9='same selected slot MethodInfo'),
  normalTailCallback=True,entryRspRestored=True,canonicalCallbackEqualityRequiredForElementGrammar=True)


def empty_program(regions,entry,context):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','4883793800','488bd9');g.branch('75',True,1)
 g.take('488b4b38','33d2');g.call(context);g.take('83b8e000000000');g.branch('75',True,1)
 g.take('488b4b38','33d2');g.call(context);g.take('488b80b8000000','488b00','4883c420','5b','c3')
 return dict(selectedBytes=g.seen,ownedEmptyArrayMethodInfoRequired=True,normalReturn=True,entryRspRestored=True)


def provider_program(regions,entry):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','4883793800','488bf9');g.branch('75',True,1)
 g.take('488b5f38');type_site=g.at;type_cell=g.relative('488b0d');g.take('488b1b');ready=g.relative('e8')
 g.take('33d2','488bcb');handle=g.relative('e8');provider_site=g.at;provider_cell=g.relative('488b0d')
 g.take('488bd8');need('same-ready-class-helper',g.relative('e8')==ready)
 g.take('488bcb');backend=g.relative('e8');g.take('488b4f38','ba01000000','488bd8');context=g.relative('e8')
 g.take('488bd0','488bcb');cast=g.relative('e8');g.take('4885c0');g.branch('0f85',True)
 g.take('488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,typeClassInstructionVa=type_site,typeClassCellVa=type_cell,
  providerClassInstructionVa=provider_site,providerClassCellVa=provider_cell,
  helpers=dict(classReady=ready,typeHandle=handle,backend=backend,context=context,cast=cast),
  matchingNonnullBackendResultRequired=True,normalReturn=True,entryRspRestored=True,runtimeFormatterSelectionProved=False)


def layout(image,ctx):
 from scripts.game_data.memorypack import scalar_param_native as scalar
 md=image.metadata;td=ctx.index.types[TYPE]
 need('own-plain-value',ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)and ctx.parent(TYPE)=='System.ValueType'and td.generic_container_index<0)
 fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 actual=[(md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:])for f in fields]
 need('exact-whole-named-layout',actual==[('operaType',ENUM,16),('parameters',PARAMETERS,24)])
 scalar.ordinary(image,ctx.type_pointer(fields[0].type_index),17,'storyOperaArray.enum')
 scalar.ordinary(image,ctx.type_pointer(fields[1].type_index),29,'storyOperaArray.parameters',reference=True)
 backing=[f for f in md.fields_for(ctx.index.types[ENUM])if not ctx.field_attributes(f.type_index)&16]
 need('own-enum-Int32',ctx.is_enum(ENUM)and len(backing)==1
  and ctx.field(ENUM+'::'+md.string(backing[0].name_index))[1:]==('int',16))
 scalar.ordinary(image,ctx.type_pointer(backing[0].type_index),8,'storyOperaArray.enumBacking')
 need('bounded-size-row',0<=td.index<image.registration['typeDefinitionsSizesCount'])
 at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*td.index)
 boxed,native=image.pe.u32_at_va(at),image.pe.u32_at_va(at+4)
 need('boxed32-marshal-unavailable',boxed==32 and native==0xffffffff)
 return dict(typeName=TYPE,typeDefinition=td.index,managedBytes=16,boxedBytes=boxed,marshaledNativeBytes=native,
  fields=actual,referenceLaneOffsets=[8],paddingByteRanges=[[4,8]],paddingRangesAreStartEnd=True,
  marshaledSizeUsedForManagedWidth=False,wireGrammarAdmitted=False)


def derive(image,pins,*,typed_request,call_target,count_limit=4096):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,validate_generic_contexts,derive_typed_usage_context
 from scripts.game_data.memorypack.array_reference_sources import validate_read_array_context
 from scripts.game_data.memorypack.pointer_param import owned
 from scripts.game_data.memorypack import scalar_param_native as scalar,animation_state_array_sources as shared
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 need('finite-array-source-selection',type(call_target)is int and call_target>base and type(count_limit)is int and count_limit==4096)
 validate_typed_usage_context(image,typed_request,label='storyOperaArray')
 need('actual-sole-nominal-request',(typed_request.get('tag'),typed_request.get('typeName'),typed_request.get('methodName'),
  typed_request.get('classArguments'),typed_request.get('methodArguments'))==(6,'MemoryPack.MemoryPackReader','ReadArray',[],[TYPE]))
 need('literal-RDX-MethodInfo',len(bytes.fromhex(typed_request['instructionHex']))==7 and typed_request['instructionHex'].upper().startswith('488B15'))
 nominal=layout(image,ctx);argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
 raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
 need('own-full-value17-carrier',raw[10:12]==bytes.fromhex('1180')and int.from_bytes(raw[:8],'little')==nominal['typeDefinition'])
 front=owned(image,call_target);front_program=return_program(front['regions'],call_target)
 byref=owned(image,front_program['byrefTargetVa']);programs=[byref_program(byref['regions'],byref['pointer'],count=n)for n in(-1,0,1,2,3)]
 symbols={}
 for p in programs:
  for k,v in p['symbols'].items():need('coherent-source-helper:'+k,k not in symbols or symbols[k]==v);symbols[k]=v
 helpers={k:owned(image,symbols[k])for k in('header','empty','provider','index','dispatch')}
 offsets=scalar.reader_offsets(image,'storyOperaArray');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 helper_programs=dict(header=shared.header_program(helpers['header']['regions'],symbols['header'],offsets),
  index=index_program(helpers['index']['regions'],symbols['index']),empty=empty_program(helpers['empty']['regions'],symbols['empty'],symbols['context']),
  provider=provider_program(helpers['provider']['regions'],symbols['provider']),dispatch=dispatch_program(helpers['dispatch']['regions'],symbols['dispatch']))
 barrier=_fast_barrier(image,symbols['barrier'])
 sy=ContextSymbols(image);first=sy.context(typed_request['methodSpec'][0],is_method=True)
 second=sy.context(first['entries'][0]['methodSpec'][0],is_method=True)
 validate_generic_contexts(image,[first,second],label='storyOperaArray')
 fm=md.methods[second['entries'][5]['methodSpec'][0]]
 declaration=shared.formatter_declaration(image,ctx,fm,md.methods[first['definition']].declaring_type)
 context=validate_read_array_context(image,[first,second],typed_request,GenericEntries(image),argument.type_pointer_va,fm.index,
  fail=lambda k,e,a:need('context:'+k,e==a))
 classes=[]
 for role,site,expected in(('provider',programs[-1]['providerClassUsage']['instructionVa'],'MemoryPack.MemoryPackFormatterProvider'),
   ('System.Type',helper_programs['provider']['typeClassInstructionVa'],'System.Type')):
  usage=derive_typed_usage_context(image,site-base,label='storyOperaArray.'+role)
  need('actual-class:'+role,(usage['tag'],usage['typeName'])==(1,expected));classes.append(usage)
 induction=prove_induction([p for p in programs if p['countWitness']>=0],initial='33f6',increment='ffc6',comparison='413bf6',
  counter='esi',saved_count='r14d',max_count=count_limit,mode_key='newArray',backedge_sites=[programs[-1]['actualBackedgeVa']])
 _publication_gate(image,pins);sources=dict(front=front,byref=byref,**helpers)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-opera-value-array',nativeInputs=pins,
  elementType=TYPE,elementValueType=True,closedArrayType=TYPE+'[]',typedRequest=typed_request,
  arrayReaderMethodDefinition=typed_request['methodSpec'][0],arrayReaderTargetRva=call_target-base,
  countRange=[-1,count_limit],countLimit=count_limit,nullable=True,positiveCountsAdmitted=True,
  elementManagedBytes=16,elementWireBytes=None,initiallyNullArrayRequired=True,actualSourceProved=True,
  elementGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  proof=dict(layout=nominal,returnProgram=front_program,programs=programs,induction=induction,
   helperPrograms=helper_programs,barrier=barrier,ownedContexts=[first,second],arrayContext=context,
   formatterDeclaration=declaration,providerClasses=classes,readerOffsets=offsets,
   sourceWindows={k:v['windows']for k,v in sources.items()},
   actualSourceRegions={k:[[a,r.hex().upper()]for a,r in v['regions']]for k,v in sources.items()},
   symbolRvas={k:v-base for k,v in symbols.items()}),
  evidenceBoundary=dict(exact='Own OperaSegment value17 layout, reciprocal actual Reader overload/array/formatter contexts, full null/empty/positive source, separately indexed stride16, repeated slot5 output calls and whole selected frames.',
   conditional='Ready coherent inflated contexts and classes, normal exact typed helpers/allocation/provider/prepare/callback ABI, disabled collector and sufficiently buffered stable disjoint input/Reader/output/frame. Selected element callback must be independently proved; no canonical pointer alias is claimed.',
   unresolved=['OperaSegment MC2/canonical/default element grammar and ParamKeyValue array','actual parent local/store/frame and resource budget','runtime formatter selection','whole owner/physical EOF/publication']))))


def bind_call(context,source_target,component,pins,*,base):
 usage=component.get('typedRequest',{});raw=bytes.fromhex(context.get('argumentRawHex',''))
 need('own-complete-value-array-source',component.get('schema')==SCHEMA
  and component.get('status')=='validated-conditional-opera-value-array'and component.get('nativeInputs')==pins
  and component.get('actualSourceProved')is True and component.get('elementType')==TYPE
  and component.get('closedArrayType')==TYPE+'[]'and component.get('elementValueType')is True
  and component.get('elementManagedBytes')==16 and component.get('elementWireBytes')is None
  and component.get('initiallyNullArrayRequired')is True and component.get('countLimit')==4096
  and component.get('countRange')==[-1,4096]
  and all(component.get(k)is False for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
 need('exact-parent-closed-carrier',(context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'),context.get('register'),context.get('typeKind'))
  ==('MemoryPack.MemoryPackReader','ReadArray',TYPE,'rdx',17)and len(raw)==16 and raw[10:12]==bytes.fromhex('1180')
  and int.from_bytes(raw[:8],'little')==component['proof']['layout']['typeDefinition']==context.get('typeDefinition'))
 need('same-actual-context-and-call',(usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec'))
  ==(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))
  and component.get('arrayReaderMethodDefinition')==usage['methodSpec'][0]
  and type(base)is int and type(source_target)is int and source_target>base and component.get('arrayReaderTargetRva')==source_target-base)
 return dict(typeName=TYPE+'[]',elementType=TYPE,sourceTargetRva=source_target-base,
  readerMethodDefinition=usage['methodSpec'][0],mode='typed-value-array',parentLocalStoreFrameRequired=True,elementGrammarAdmitted=False)
