"""Actual ordinal string predicates used by the Patrol range-radio consumer.

Both named string wrappers are independently selected from the current caller.
The actual shared byte comparator is replayed for every zero-through64 UTF16
length and each first unequal chunk. No culture, normalization or playback is
inferred; caller string identities and the ready comparison class stay conditions.
"""
import hashlib,json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as packets
from scripts.game_data.memorypack.leveldata_patrol_checkpoint_callee_programs import byte_equality_program

SCHEMA='endfield.story-patrol-radio-query-sources.v1'
MODES=('same-reference','left-null','right-null','different-length','content')


def need(check,condition):
 if not condition:raise ValueError('patrolRadioQuery.'+check)


def wrapper_program(regions,entry,*,inequality=False,mode='content'):
 need('literal-string-query-mode',type(inequality)is bool and mode in MODES);g=BytesPath(regions,entry)
 if inequality:g.take('4883ec28')
 g.take('483bca');g.branch('74',mode=='same-reference',1)
 if mode=='same-reference':g.take('b001');g.at=g.relative('eb',1)
 else:
  g.take('4885c9');g.branch('74',mode=='left-null',1)
  if mode!='left-null':
   g.take('4885d2');g.branch('74',mode=='right-null',1)
   if mode!='right-null':g.take('8b4210','394110');g.branch('74',mode=='content',1)
  if mode=='content':
   g.take('4c634110','4883c214','4d03c0','4883c114','4533c9');at=g.at;target=g.relative('e8'if inequality else'e9')
   if not inequality:
    return dict(selectedBytes=g.seen,mode=mode,inequality=False,compareCall=dict(instructionVa=at,targetVa=target),
     arguments=dict(rcx='unchanged first string+20',rdx='unchanged second string+20',r8='2*same nonnegative string.length',r9d=0),
     normalTail=True,entryRspUntouched=True,nonvolatilesUntouched=True,actualStringIdentityObserved=False)
  else:g.take('32c0')
 if inequality:g.take('3401','4883c428')
 g.take('c3')
 return dict(selectedBytes=g.seen,mode=mode,inequality=inequality,
  compareCall=dict(instructionVa=at,targetVa=target)if mode=='content'else None,
  arguments=dict(rcx='unchanged first string+20',rdx='unchanged second string+20',r8='2*same nonnegative string.length',r9d=0)if mode=='content'else None,
  result='logical inverse of exact byte equality'if mode=='content'and inequality else(mode=='same-reference')^inequality,
  normalReturn=True,entryRspRestored=True,nonvolatilesUntouched=True,actualStringIdentityObserved=False)


def _programs(p):
 base=p['imageBase'];h=p['helpers'];raw={k:packets.raw(v,base)for k,v in h.items()};out={}
 for role,inequality in(('queryFar',False),('queryNear',True)):
  out[role]=[wrapper_program(raw[role],base+h[role]['entryRva'],inequality=inequality,mode=m)for m in MODES]
 out['bytes']=[byte_equality_program(raw['compare'],base+h['compare']['entryRva'],count=n,mismatch=m)
  for n in range(0,129,2)for m in[None,*([*range(0,n-8,8),n-8]if n>=8 else range(n))]]
 return packets.norm(out)


def _leaf(image,at,inequality):
 raw=image.pe.bytes_at_va(at,128);programs=[wrapper_program([(at,raw)],at,inequality=inequality,mode=m)for m in MODES]
 selected={p+i for program in programs for p,h in program['selectedBytes']for i in range(len(bytes.fromhex(h)))}
 span=max(selected)+1-at;need('complete-selected-wrapper-byte-union',selected==set(range(at,at+span)))
 return packets.packet(image,at,span=span)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import leveldata_patrol_range_sources as parent
 _publication_gate(image,pins);source=parent.derive(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);h={};methods={}
 for role,name,inequality in(('queryFar','Equals',False),('queryNear','op_Inequality',True)):
  named=source['namedMethods'][role];method=image.metadata.methods[named[0]]
  need('actual-own-static-string-method',method.declaring_type==ctx.index.types['System.String'].index and image.metadata.string(method.name_index)==name
   and method.flags&16 and ctx.type_name(method.return_type)=='bool'and[ctx.type_name(p.type_index)for p in image.metadata.parameters_for(method)]==['string','string']
   and image.method_pointer_va(method)==base+named[3])
  methods[role]=dict(method=named,parameters=['string','string'],returnType='bool',static=True)
  h[role]=_leaf(image,base+named[3],inequality)
 far=wrapper_program(packets.raw(h['queryFar'],base),base+h['queryFar']['entryRva'])
 h['compare']=packets.packet(image,far['compareCall']['targetVa'])
 proof=dict(imageBase=base,rangeSource=source,helpers=h,methods=methods,stringFields={n:list(ctx.field('System.String::'+n))for n in('_stringLength','_firstChar')})
 proof['programs']=_programs(proof)
 site=next((at,h)for p in proof['programs']['bytes']for at,h in p['selectedBytes']if bytes.fromhex(h)[:3]==bytes.fromhex('488b0d'))[0]
 proof['comparisonClassUsage']=derive_typed_usage_context(image,site-base,label='patrolRadioQuery.actualComparisonClass')
 value=packets.norm(dict(schema=SCHEMA,status='validated-conditional-radio-string-query-sources',nativeInputs=pins,proof=proof,
  selectedRadioStringPredicatesAndByteEffectsProved=True,fullNullLengthPointerAndFramePathsProved=True,
  finiteUtf16LengthLimit=64,normalizationOrCultureApplied=False,actualStringOrCallbackSelectionObserved=False,
  runtimeInvocationObserved=False,playbackProved=False,
  conditions=['Compatible stable System.String inputs; same references, nulls and different lengths follow their own exact branches. Content comparisons require equal nonnegative lengths0..64 UTF16 code units, valid storage and the actual comparison class already initialized.',
   'Every byte in the actual two-byte UTF16 representation is compared, with no case fold or normalization. Every accepted length and first unequal actual chunk are independently replayed. Larger lengths and cold comparison-class initialization remain nonselected.',
   'The original consumer selects these actual named string method entries and preserves the input string references. Runtime controller/player/radio state, action dispatch and audio playback are not observed or granted.']))
 validate(value,pins);_publication_gate(image,pins);return value


def validate(value,pins):
 need('source-envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-radio-string-query-sources'and value.get('nativeInputs')==pins
  and value.get('finiteUtf16LengthLimit')==64 and all(value.get(k)is True for k in('selectedRadioStringPredicatesAndByteEffectsProved','fullNullLengthPointerAndFramePathsProved'))
  and all(value.get(k)is False for k in('normalizationOrCultureApplied','actualStringOrCallbackSelectionObserved','runtimeInvocationObserved','playbackProved')))
 p=value['proof'];base=p['imageBase'];source=p['rangeSource'];need('same-input-consumer',source['nativeInputs']==pins)
 need('exact-owned-helper-roles',set(p['helpers'])=={'queryFar','queryNear','compare'}and set(p['methods'])=={'queryFar','queryNear'})
 actual=_programs(p);need('all-wrapper-and-comparison-programs',actual==p['programs'])
 for role,name in(('queryFar','Equals'),('queryNear','op_Inequality')):
  m=p['methods'][role];need('actual-named-method-request:'+role,m['method']==source['namedMethods'][role]
   and m['method'][1:3]==['System.String',name]and m['parameters']==['string','string']and m['returnType']=='bool'and m['static']is True
   and m['method'][3]==p['helpers'][role]['entryRva'])
  need('same-complete-byte-comparison-target',actual[role][-1]['compareCall']['targetVa']==base+p['helpers']['compare']['entryRva'])
  selected={at+i for program in actual[role]for at,h in program['selectedBytes']for i in range(len(bytes.fromhex(h)))}
  rr=packets.raw(p['helpers'][role],base);need('all-and-only-declared-wrapper-span',len(rr)==1 and selected==set(range(rr[0][0],rr[0][0]+len(rr[0][1]))))
 need('own-string-length-and-char-fields',p['stringFields']==dict(_stringLength=['System.String','int',16],_firstChar=['System.String','char',20]))
 usage=p['comparisonClassUsage'];cell=next(v['readyClassCellVa']for v in actual['bytes']if v['readyClassCellVa']is not None)
 sites={at for path in actual['bytes']for at,h in path['selectedBytes']if bytes.fromhex(h)[:3]==bytes.fromhex('488b0d')}
 need('actual-ready-class-context-site',usage['instructionRva']+base in sites and usage['usageCellRva']+base==cell and usage['tag']==1)
 return value
