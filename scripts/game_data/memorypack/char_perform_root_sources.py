"""Exact initialized existing-owner field transfers; child semantics stay separate."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def _peek(g,n):return bytes(g.bytes.get(g.at+i,0) for i in range(n)).hex()
def _branch(g,condition,taken):
 opcode={'eq':('74','0f84'),'ne':('75','0f85'),'ge':('7d','0f8d'),'ns':('79','0f89')}[condition]
 if _peek(g,1)==opcode[0]:g.branch(opcode[0],taken,1)
 else:g.branch(opcode[1],taken)
def _cmp_zero(g,prefix):return g.relative(prefix)
def _store(g,prefix_short,prefix_long,offset):
 if 0<=offset<=127:g.take(prefix_short+offset.to_bytes(1,'little').hex())
 else:g.take(prefix_long+offset.to_bytes(4,'little').hex())
def _nonnull(g,register):
 g.take('4885db' if register=='rbx' else '4d85c0' if register=='r8' else '4885c9' if register=='rcx' else '4885c0');_branch(g,'eq',False)
def _setup(g,context):
 cells=[];seen=set()
 for _ in range(3 if context else 2):
  if _peek(g,3)=='488b15' and context and 'context' not in seen:cells.append(dict(instruction=g.at,cell=g.relative('488b15')));seen.add('context')
  elif _peek(g,3)=='498bcf' and 'reader' not in seen:g.take('498bcf');seen.add('reader')
  elif _peek(g,3)=='498b1e' and 'holder' not in seen:g.take('498b1e');seen.add('holder')
  else:raise ValueError('performRoot.sourceSetup')
 if seen!={'reader','holder',*(['context'] if context else [])}:raise ValueError('performRoot.sourceOrigins')
 return cells

def root_existing(regions,entry,fields,*,offsets,source_targets):
 if len(fields)!=28 or len({f['name'] for f in fields})!=28:raise ValueError('performRoot.fieldPlan')
 g=BytesPath(regions,entry);g.take('48895c2410','55','56','57','4154','4155','4156','4157','488d6c24d9','4881ec90000000','4533ed');imagebase=g.relative('4c8d25');init_flag=g.relative('44382d');g.take('4c8bf2','4c8bf9');_branch(g,'ne',True)
 cur,rem,advance,used=(offsets[k] for k in ('currentPtr','bufferLength','advancedCount','consumed'))
 g.take('41837f'+bytes((rem,1)).hex(),'4c896d67','4c896d7f');_branch(g,'ge',True)
 g.take('498b47'+bytes((cur,)).hex(),'0fb630','418b5f'+bytes((rem,)).hex(),'83eb01');_branch(g,'ns',True)
 g.take('49ff47'+bytes((cur,)).hex(),'41ff47'+bytes((advance,)).hex(),'41ff47'+bytes((used,)).hex(),'41895f'+bytes((rem,)).hex(),'4080feff');_branch(g,'eq',False)
 g.take('4d392e');_branch(g,'ne',True);g.take('4080fe1c');_branch(g,'ne',False)
 output=[];collector=None;float_prepared=False
 for index,field in enumerate(fields):
  mode=field['mode'];at=g.at;context=[];type_cell=None;stack=None
  if mode=='out8':
   type_cell=g.relative('488b0d');stack=0x67 if index==2 else 0x7f if index==25 else None
   if stack is None:raise ValueError('performRoot.outSlot')
   g.take('4c896d'+bytes((stack,)).hex(),'4439a9e0000000');_branch(g,'ne',True);context=[dict(instruction=g.at,cell=g.relative('4c8b05'))];g.take('488d55'+bytes((stack,)).hex(),'498bcf')
  elif float_prepared:
   if mode!='bool':raise ValueError('performRoot.floatSuccessor')
   float_prepared=False
  else:context=_setup(g,mode in ('reference','enum'))
  call=g.at;target=g.relative('e8')
  if field['source'] in source_targets and target!=source_targets[field['source']]:raise ValueError('performRoot.childTargetConsistency')
  source_targets[field['source']]=target;offset=field['offset'];flag_cell=None
  if mode=='out8':g.take('4d8b06');_nonnull(g,'r8');g.take('4d8b4010');_nonnull(g,'r8');flag_cell=_cmp_zero(g,'44392d');g.take('488b45'+bytes((stack,)).hex());_store(g,'498940','498980',offset)
  else:
   _nonnull(g,'rbx')
   if mode=='reference':g.take('4c8b4310');_nonnull(g,'r8');flag_cell=_cmp_zero(g,'44392d');_store(g,'498940','498980',offset)
   elif mode=='float':
    g.take('488b4310');_nonnull(g,'rax');g.take('498b1e','498bcf');_store(g,'f30f1140','f30f1180',offset);float_prepared=True
   elif mode in ('bool','enum'):
    g.take('488b4b10');_nonnull(g,'rcx');_store(g,'8841' if mode=='bool' else '8941','8881' if mode=='bool' else '8981',offset)
   else:raise ValueError('performRoot.fieldMode')
  if flag_cell is not None:
   if collector is None:collector=flag_cell
   if flag_cell!=collector:raise ValueError('performRoot.collectorFlagIdentity')
   _branch(g,'eq',True)
  output.append(dict(name=field['name'],mode=mode,fieldOffset=offset,sourceTarget=source_targets[field['source']],sourceCall=call,contextCells=context,typeCell=type_cell,temporarySlot=stack,selectedStart=at,selectedEnd=g.at))
 if float_prepared:raise ValueError('performRoot.danglingPreparedArguments')
 g.jump('eb',1);g.take('488b9c24d8000000','4881c490000000','415f','415e','415d','415c','5f','5e','5d','c3')
 return dict(fields=output,selectedBytes=g.seen,imageBaseReference=imagebase,initializerFlag=init_flag,collectorFlag=collector,memberCount=28,entryRspRestored=True,wholeOwnerAdmitted=False,evidenceBoundary=dict(direct='Complete selected buffered header and ordered child-call/unchanged field transfers with both separately initialized stack temporaries and full frame return.',conditional='Initialized metadata and selected dictionary classes; existing matching nonnull wrapper/original, sufficient contiguous input, disabled collector, valid disjoint storage, normal child/helper returns preserving Win64 nonvolatile registers.',unresolved=['typed contexts and reader/result ABI','all child wire grammars and provider selection','new-wrapper/default construction','enabled collector and cold refill/errors','complete source/corpus admission and runtime execution']))
