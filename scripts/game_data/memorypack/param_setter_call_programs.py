"""Finite four-field initialized Param call schedule, without value grammar.

The byte program proves a whole RAX result passed unchanged in RDX to its
named setter. That ABI supplies no nominal identity or serialized width.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(key,condition):
 if not condition:raise ValueError('paramSetterCallProgram.'+key)


def reader_program(regions,entry,*,existing,ff,constant_width=8):
 need('literal-four-path-choice',type(existing)is bool and type(ff)is bool)
 need('actual-constant-register-width',type(constant_width)is int and constant_width in(4,8))
 g=BytesPath(regions,entry)
 g.take('48895c2410','4889742418','57','4883ec20')
 flag=g.relative('803d')+1;g.take('00','488bda','488bf1');g.branch('75',True,1)
 g.take('488d542430','c644243000','488bce');header=g.relative('e8');g.take('84c0');g.branch('0f84',ff)
 allocation=None;calls={};context=None
 if ff:
  g.take('488bcb','48c70300000000');barrier=g.relative('e8')
 else:
  g.take('48833b00');g.branch('75',existing,1)
  if not existing:
   at=g.at;cell=g.relative('488b0d');allocator=g.relative('e8');allocation=dict(instructionVa=at,cellVa=cell,targetVa=allocator)
   g.take('488bf8','4885c0');g.branch('0f84',False)
   g.take('33d2','488bc8');constructor=g.relative('e8');allocation['constructorVa']=constructor
   g.take('488bcb','48893b');barrier=g.relative('e8')
  else:barrier=None
  g.take('807c243004');g.branch('0f85',False)
  at=g.at;cell=g.relative('488b15');context=dict(instructionVa=at,cellVa=cell)
  g.take('488bce','488b3b');calls['constValue']=g.relative('e8')
  g.take('4885ff');g.branch('74',False,1)
  g.take('4533c0','8bd0'if constant_width==4 else'488bd0','488bcf');calls['setConstValue']=g.relative('e8')
  for name in('idRef','paramSource'):
   g.take('488b3b','488bce');calls[name]=g.relative('e8');g.take('4885ff');g.branch('74',False,1)
   g.take('4533c0','8bd0','488bcf');calls['set'+name[0].upper()+name[1:]]=g.relative('e8')
  g.take('488b1b','488bce');calls['path']=g.relative('e8');g.take('4885db');g.branch('74',False,1)
  g.take('4533c0','488bd0','488bcb');calls['setPath']=g.relative('e8');g.jump('eb',1)
 g.take('488b5c2438','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,initializedFlagVa=flag,existing=existing,wrapperNull=ff,
  allocation=allocation,sourceCalls=calls,constantContext=context,headerTargetVa=header,barrierTargetVa=barrier,
  memberCount=4,headerWireBytes=1,nullOutputBytes=8,constantStoredBytes=constant_width,constantResultRegister='eax'if constant_width==4 else'rax',constantSetterArgumentRegister='edx'if constant_width==4 else'rdx',
  sameReaderAndOutput=True,constantWireGrammarAdmitted=False,nominalTypeAdmitted=False,entryRspRestored=True,allNonvolatilesRestored=True,
  frameBytes=40,savedEntryHomes=dict(rbx=[16,24],rsi=[24,32]),pushedNonvolatiles=['rdi'],normalReturn=True,
  initializedMetadataRequired=True,compatibleCallsRequired=True,childGrammarAdmitted=False)
