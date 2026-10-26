"""Pure exact scalar arithmetic leaves used by an actual byte-hash caller.

No algorithm name, metadata alias, physical method extent or current input is
selected here. The enclosing owner supplies actual call targets, authenticates
the declared complete normal spans and joins the returned arithmetic effects.
"""
from .formatter_value_paths import BytesPath

def need(check,condition):
 if not condition:raise ValueError('byteHashArithmetic.'+check)

def multiply128_program(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2408','448bc9','4c8bd1','8bc2','4c8bda','4c0fafc8','8bc1','49c1e920','49c1eb20',
  '490fafc3','480fafca','4c03c8','49c1ea20','8bda','490fafda','4d0fafd3','8bc3','4c03c8','48c1eb20',
  '49c1e920','488bc1','4d03ca','4c03cb','488b5c2408','4d8908','c3')
 b=1<<32
 return dict(selectedBytes=g.seen,entry=entry,nextInstructionVa=g.at,normalReturn=True,
  inputs={'rcx':'a unsigned64','rdx':'b unsigned64','r8':'valid disjoint high64 output'},
  returnsLow64OfUnsignedProduct=True,writesHigh64OfUnsignedProduct=True,outputWriteBytes=8,
  proof=dict(limbBits=32,limbBase=b,maximumIntermediate=(b-1)**2+(b-2)+(b-1),
   intermediateCannotOverflow64=(b-1)**2+(b-2)+(b-1)<1<<64,
   identity='a=a0+B*a1; b=b0+B*b1; p00=a0*b0; p01=a0*b1; p10=a1*b0; p11=a1*b1. high64=p11+(p10>>32)+((p01+(p00>>32)+(p10&0xffffffff))>>32); low64=(a*b)&0xffffffffffffffff.',
   exactForEveryUnsigned64InputPair=True),opaqueCalls=0,otherNonframeWrites=0,entryRspUnchanged=True,rbxRestored=True)

def avalanche_program(regions,entry,*,kind='one-multiply'):
 need('finite-arithmetic-profile',kind in('one-multiply','two-multiply'))
 g=BytesPath(regions,entry);constants=[]
 if kind=='one-multiply':
  g.take('48b8');constants.append(int.from_bytes(g.read(8),'little'));g.take('488bd1','48c1ea25','4833d1','480fafd0',
   '488bc2','48c1e820','4833c2','c3')
  effect='x=((input^(input>>37))*c0) mod2^64; result=x^(x>>32)'
 else:
  g.take('488bc1','48c1e821','4833c1','48b9');constants.append(int.from_bytes(g.read(8),'little'))
  g.take('480fafc1','488bc8','48c1e91d','4833c8','48b8');constants.append(int.from_bytes(g.read(8),'little'))
  g.take('480fafc8','488bc1','48c1e820','4833c1','c3')
  effect='x=((input^(input>>33))*c0) mod2^64; y=((x^(x>>29))*c1) mod2^64; result=y^(y>>32)'
 return dict(selectedBytes=g.seen,entry=entry,nextInstructionVa=g.at,kind=kind,constants=constants,arithmeticEffect=effect,
  allMultiplicationModuloBits=64,normalReturn=True,entryRspAndNonvolatilesUnchanged=True,opaqueCalls=0,nonframeWrites=0)

def four_to_eight_program(regions,entry):
 g=BytesPath(regions,entry);g.take('4c8bc9','488bc1','48c1e031','4c8bc1','49c1e90f','4c0bc8','49c1e828',
  '488bc1','48c1e018','4c0bc0','48b8');constant=int.from_bytes(g.read(8),'little')
 g.take('4d33c8','4c33c9','4c0fafc8','498bc9','48c1e923','4803ca','4933c9','480fafc8','488bc1','48c1e81c','4833c1','c3')
 return dict(selectedBytes=g.seen,entry=entry,nextInstructionVa=g.at,constant=constant,
  arithmeticEffect='x=((rol64(word,49)^rol64(word,24)^word)*c) mod2^64; y=(((x>>35)+length)^x)*c mod2^64; result=y^(y>>28)',
  rotationAmounts=[49,24],lengthArgument='incoming RDX',normalReturn=True,entryRspAndNonvolatilesUnchanged=True,opaqueCalls=0,nonframeWrites=0)

def mix_sixteen_program(regions,entry):
 g=BytesPath(regions,entry);g.take('4c894c2420','4883ec28','4c8b5208','488bc1','4d2bd0','48c744244800000000',
  '4c335108','4533c9','488b0a','498bd2','4903c8','4c8d442448','483308')
 at=g.at;target=g.relative('e8');g.take('4833442448','4883c428','c3')
 return dict(selectedBytes=g.seen,entry=entry,nextInstructionVa=g.at,multiplyCall={'instructionVa':at,'targetVa':target},
  arithmeticEffect='fold128((secret0+seed mod2^64)^input0,(secret8-seed mod2^64)^input8); fold128=low64(a*b)^high64(a*b)',
  sourceReadBytes=16,secretReadBytes=16,seedArgument='incoming R8',actualCalledArithmeticChildRequired=True,
  entryRspRestored=True,allNonvolatilesUnchanged=True,normalReturn=True)

def nine_to_fifteen_program(regions,entry):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','498b7820','488bf2','49337818',
  '498b5830','4903f9','49335828','483339','492bd9','48335c11f8','488bcf','488bd3')
 at=g.at;target=g.relative('e8');g.take('480fcf','488d0c03','4803cf','4803ce','488b5c2430','488b742438','4883c420','5f')
 tail=g.at;avalanche=g.relative('e9')
 return dict(selectedBytes=g.seen,entry=entry,nextInstructionVa=g.at,foldMultiplyCall={'instructionVa':at,'targetVa':target},
  avalancheTail={'instructionVa':tail,'targetVa':avalanche},lengthArgument='incoming RDX',
  arithmeticEffect='a=first8^((secret24^secret32)+seed); b=last8^((secret40^secret48)-seed); result=avalanche64(length+bswap64(a)+b+fold128(a,b)) with64-bit modular sums',
  readRanges=['[0,8)','[length-8,length)'],secretByteExtentRequired=56,actualCalledArithmeticChildRequired=True,
  entryRspRestored=True,nonvolatilesRestored=['rbx','rsi','rdi'],normalTail=True)

def fold128_program(regions,entry):
 g=BytesPath(regions,entry);g.take('4c89442418','4883ec28','4533c9','48c744244000000000','4c8d442440')
 at=g.at;target=g.relative('e8');g.take('4833442440','4883c428','c3')
 return dict(selectedBytes=g.seen,entry=entry,nextInstructionVa=g.at,multiplyCall={'instructionVa':at,'targetVa':target},
  arithmeticEffect='low64(a*b)^high64(a*b)',actualCalledArithmeticChildRequired=True,
  entryRspRestored=True,allNonvolatilesUnchanged=True,normalReturn=True)
