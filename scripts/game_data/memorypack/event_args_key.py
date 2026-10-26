"""The initialized positive one-key wrapper paths, with an ordinary allocator/barrier ABI."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def child(regions,entry,symbols,*,allocated=False):
 g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','803d');g.read(4);g.take('00','488bda','488bf9');g.branch('74',False,1)
 g.take('488d542430','c644243000','488bcf');g.call(symbols['header']);g.take('84c0');g.branch('0f84',False)
 g.take('48833b00');g.branch('0f84',allocated);allocation=None
 if allocated:
  allocation=g.at;g.relative('488b0d');g.call(symbols['allocate']);g.take('4885c0');g.branch('0f84',False)
  g.take('33c9','48894810','488bcb','488903');g.call(symbols['barrier']);g.take('90');g.jump('e9')
 g.take('807c243001');g.branch('0f85',False);g.take('488b1b','488bcf');g.call(symbols['pool']);g.take('4885db');g.branch('74',False,1)
 g.take('488d4b10','488901','488b5c2438','4883c420','5f')
 if g.relative('e9')!=symbols['barrier']:raise ValueError('eventKey.tail-barrier')
 return dict(selectedBytes=g.seen,allocated=allocated,allocationUsageSite=allocation,memberCount=1,
  fieldOffset=16,readKind='int32-pool-index',valueTransfer='Pooled string RAX bits stored to the same wrapper +16; matching reference barrier destination in RCX.',
  stackRestored=True,condition='Initialized metadata, positive one-member header, valid disjoint reader/wrapper storage and normal nonthrowing allocator/barrier ABI. Null/malformed headers and live formatter selection are excluded.')
