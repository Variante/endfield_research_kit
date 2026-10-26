"""Complete selected original-instance construction callers, with helper effects conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def factory(regions,entry,s,*,create=False):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','803d');flag=g.at+5+int.from_bytes(g.read(4),'little',signed=True);g.take('00','488bf9');g.branch('75' if create else '74',create,1)
 load=g.at;cell=g.relative('488b0d')
 if cell!=s['classCell']:raise ValueError('performFactory.typed-class-cell')
 g.call(s['allocation']);g.take('488bd8','4885c0');g.branch('75' if create else '74',create,1);g.take('33d2','488bcb' if create else '488bc8');g.call(s['constructor']);g.take('488d4f10','48895f10','488b5c2430','4883c420','5f')
 if g.relative('e9')!=s['barrier']:raise ValueError('performFactory.barrier-tail')
 return dict(selectedBytes=g.seen,initializerFlag=flag,classLoad=load,fieldOffset=16,constructorReceiver='same helper result saved in RBX',constructorCompanion=0,sameFullReferenceStored=True,entryRspRestored=True,normalReturn='tail to returning barrier with original caller stack',wholeOwnerAdmitted=False,condition='Initialized selected class/metadata, matching wrapper at incoming RCX, valid disjoint storage, fresh coherent typed allocation and normal original constructor/barrier returns preserving nonvolatile registers. Original constructor side effects, allocator/barrier implementation, cold metadata initialization and whole owner remain independent.')

def getter(regions,entry):
 g=BytesPath(regions,entry);g.take('488b4110','c3')
 return dict(selectedBytes=g.seen,fieldOffset=16,sameFullReferenceReturned=True,entryRspRestored=True,heapWrites=0,wholeOwnerAdmitted=False)
