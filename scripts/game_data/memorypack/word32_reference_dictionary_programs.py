"""Exact selected word32/reference dictionary bytes; no nominal key admission.

This profile accepts only fresh outputs and four bounded loop witnesses.
Owning native modules independently prove signedness/nominal key callbacks,
contexts, reference child, actual parent, header and typed helper effects.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def program(regions,entry,symbols,*,count,path_factory=None):
 if type(count)is not int or count not in(-1,0,1,2,3):raise ValueError('word32Dictionary.literal-count-witness')
 if path_factory is not None and not callable(path_factory):raise ValueError('word32Dictionary.callable-only-owned-path')
 g=(BytesPath if path_factory is None else path_factory)(regions,entry);s=symbols
 g.take('488bc4','53','55','56','57','4154','4883ec50','4c8be2','33ed','488bf1','8968a8','498bcc','896810','488d50a8','488968b0','498bd9','498bf8')
 g.call(s['header']);g.take('84c0');g.branch('0f84',count==-1);backedges=[];key_sites=[];value_sites=[];add_sites=[]
 if count==-1:
  g.take('488bcf','48892f');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4c89b42490000000','4c89ac2480000000','4c89bc2498000000','448b742420','48392f');g.branch('0f85',False)
  g.take('488b4b20','ba03000000','4c8b7e10','488b89c0000000');g.call(s['indexed'])
  g.take('488bc8');g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False)
  g.take('488b4b20','488b91c0000000','488b4a20','48396920');g.branch('0f84',False)
  g.take('488b4320','4d8bc7','418bd6','488bce','4c8b88c0000000','4d8b4920');g.call(s['constructor'])
  g.take('488bcf','488937');g.call(s['barrier']);g.relative('488b0d');g.take('39a9e0000000');g.branch('0f84',False)
  g.take('488b4320','488b88c0000000','488b4930');g.call(s['keyProvider'])
  g.take('488b4b20','488bf0','488b89c0000000','488b4938');g.call(s['valueProvider'])
  g.take('4c8bf8','4585f6');g.branch('7f',count>0,1)
  loop=g.at
  for index in range(count):
   if g.at!=loop:raise ValueError('word32Dictionary.same-loop-entry')
   g.take('488b4b20','488b91c0000000','488b4a40','4883793800');g.branch('0f84',False)
   g.take('0f57c0','0f11442438','33c0','89842488000000','4889442428','4885f6');g.branch('0f84',False)
   g.take('4c8d8c2488000000','4d8bc4','488bd6');key_sites.append(g.at);g.call(s['keyDispatch'])
   g.take('4d85ff');g.branch('74',False,1);g.take('b905000000','4c8d4c2428','4d8bc4','498bd7')
   value_sites.append(g.at);g.call(s['valueDispatch'])
   g.take('8b842488000000','4c8b2f','89442420','488b442428','4889442430','4d85ed');g.branch('74',False,1)
   g.take('488b4320','488b88c0000000','488b4148','4883782000');g.branch('0f84',False)
   g.take('488b4320','498bcd','4c8b442430','8b542420','4c8b88c0000000','4d8b4948')
   add_sites.append(g.at);g.call(s['add']);g.take('ffc5','413bee');edge=g.at
   target=g.relative('0f8c')
   if target!=loop:raise ValueError('word32Dictionary.exact-owned-backedge')
   backedges.append(edge)
   if index+1<count:g.at=target
   else:g.jump('e9')
  g.take('4c8bac2480000000','4c8bbc2498000000','4c8bb42490000000')
 g.take('4883c450','415c','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,countWitness=count,newDictionary=True,headerBytes=4,
  keyOutputBytes=4,valueOutputBytes=8,elementCallbacks=max(count,0),keyCallbackSites=key_sites,
  valueCallbackSites=value_sites,addSites=add_sites,backedgeSites=sorted(set(backedges)),
  sameReaderRegister='r12',sameOutputRegister='rdi',counter='ebp',savedCount='r14d',
  keyOutput='zeroDWORD stack136 -> DWORD stack32 -> EDX',valueOutput='zeroQWORD stack40 -> stack48 -> R8',
  keySignednessProved=False,keyNominalTypeProved=False,keyWireGrammarAdmitted=False,
  valueWireGrammarAdmitted=False,initiallyNullOutputRequired=True,
  normalReturn=True,wholeOwnerAdmitted=False,
  condition='Exact buffered word32/reference source, fresh output, initialized coherent typed contexts and matching independently proved key/reference callbacks. Normal successful header, typed allocation/constructor/Add/provider/barrier and Win64 nonvolatile effects are independent conditions. No closed pointer alias or nominal key/child grammar follows.')


def induction(programs,*,count_limit=4096):
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 positive=[p for p in programs if p.get('countWitness')in(0,1,2,3)]
 one,=[p for p in positive if p['countWitness']==1]
 return prove_induction(positive,initial='33ed',increment='ffc5',comparison='413bee',
  counter='ebp',saved_count='immutable R14D copied once from signed Int32 header output at stack32',
  max_count=count_limit,mode_key='newDictionary',backedge_sites=one['backedgeSites'])
